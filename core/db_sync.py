import sqlite3
import pymysql
import json
import time

class DBSchemaComparer:
    @classmethod
    def compare_mysql(cls, host, user, password, src_db, tgt_db, port=3306):
        """Compare two MySQL databases schema and return differences and SQL upgrade scripts"""
        conn = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        try:
            cursor = conn.cursor()
            
            # Verify databases exist
            cursor.execute("SHOW DATABASES")
            all_dbs = [row["Database"] for row in cursor.fetchall()]
            if src_db not in all_dbs:
                raise ValueError(f"Source database '{src_db}' does not exist.")
            if tgt_db not in all_dbs:
                raise ValueError(f"Target database '{tgt_db}' does not exist.")

            # 1. Missing tables
            cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (src_db,))
            src_tables = [row["TABLE_NAME"] for row in cursor.fetchall()]
            
            cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (tgt_db,))
            tgt_tables = [row["TABLE_NAME"] for row in cursor.fetchall()]

            missing_tables = sorted(list(set(src_tables) - set(tgt_tables)))
            missing_tables_data = []
            generated_sql = ""

            for table in missing_tables:
                cursor.execute(f"SHOW CREATE TABLE `{src_db}`.`{table}`")
                res = cursor.fetchone()
                create_sql = res["Create Table"] if res else ""
                # Replace back source db prefix if any or just output
                missing_tables_data.append({
                    "name": table,
                    "create_sql": create_sql
                })
                generated_sql += f"-- Create Table: {table} (Missing in Target)\n"
                generated_sql += create_sql + ";\n\n"

            # 2. Column Differences
            in_placeholder = ""
            params = [tgt_db, src_db]
            if missing_tables:
                placeholders = ",".join(["%s"] * len(missing_tables))
                in_placeholder = f"AND c1.TABLE_NAME NOT IN ({placeholders})"
                params.extend(missing_tables)

            diff_sql = f"""
                SELECT 
                    c1.TABLE_NAME, 
                    c1.COLUMN_NAME, 
                    c1.COLUMN_TYPE AS local_type, 
                    c2.COLUMN_TYPE AS online_type,
                    c1.IS_NULLABLE AS local_nullable,
                    c2.IS_NULLABLE AS online_nullable,
                    c1.COLUMN_DEFAULT AS local_default,
                    c2.COLUMN_DEFAULT AS online_default,
                    c1.ORDINAL_POSITION,
                    c1.EXTRA,
                    CASE 
                        WHEN c2.COLUMN_NAME IS NULL THEN 'Missing Column'
                        WHEN c1.COLUMN_TYPE != c2.COLUMN_TYPE THEN 'Type Mismatch'
                        WHEN c1.IS_NULLABLE != c2.IS_NULLABLE THEN 'Nullability Mismatch'
                        WHEN COALESCE(c1.COLUMN_DEFAULT, 'NULL_SENTINEL') != COALESCE(c2.COLUMN_DEFAULT, 'NULL_SENTINEL') THEN 'Default Value Mismatch'
                        ELSE 'Other Mismatch'
                    END AS DifferenceType
                FROM 
                    information_schema.COLUMNS c1
                LEFT JOIN 
                    information_schema.COLUMNS c2 
                    ON c1.TABLE_NAME = c2.TABLE_NAME 
                    AND c1.COLUMN_NAME = c2.COLUMN_NAME 
                    AND c2.TABLE_SCHEMA = %s
                WHERE 
                    c1.TABLE_SCHEMA = %s
                    {in_placeholder}
                    AND (
                        c2.COLUMN_NAME IS NULL 
                        OR c1.COLUMN_TYPE != c2.COLUMN_TYPE 
                        OR c1.IS_NULLABLE != c2.IS_NULLABLE
                        OR COALESCE(c1.COLUMN_DEFAULT, 'NULL_SENTINEL') != COALESCE(c2.COLUMN_DEFAULT, 'NULL_SENTINEL')
                    )
                ORDER BY 
                    c1.TABLE_NAME, c1.ORDINAL_POSITION
            """
            cursor.execute(diff_sql, params)
            diffs = cursor.fetchall()

            # 3. Generate ALTER statements
            table_alters = {}
            for diff in diffs:
                tbl = diff["TABLE_NAME"]
                col = diff["COLUMN_NAME"]
                diff_type = diff["DifferenceType"]
                col_type = diff["local_type"]
                nullable = "NULL" if diff["local_nullable"] == "YES" else "NOT NULL"
                
                default = ""
                if diff["local_default"] is not None:
                    ld = diff["local_default"]
                    if ld.upper() in ("CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP()"):
                        default = " DEFAULT CURRENT_TIMESTAMP"
                    else:
                        default = f" DEFAULT '{ld}'"
                elif diff["local_nullable"] == "YES":
                    default = " DEFAULT NULL"

                extra = f" {diff['EXTRA']}" if diff["EXTRA"] else ""

                if diff_type == "Missing Column":
                    # Position AFTER
                    pos_sql = """
                        SELECT COLUMN_NAME FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND ORDINAL_POSITION = %s
                    """
                    cursor.execute(pos_sql, (src_db, tbl, int(diff["ORDINAL_POSITION"]) - 1))
                    prev_col_row = cursor.fetchone()
                    position = f" AFTER `{prev_col_row['COLUMN_NAME']}`" if prev_col_row else " FIRST"
                    
                    statement = f"ADD COLUMN `{col}` {col_type} {nullable}{default}{extra}{position}"
                else:
                    statement = f"MODIFY COLUMN `{col}` {col_type} {nullable}{default}{extra}"

                if tbl not in table_alters:
                    table_alters[tbl] = []
                table_alters[tbl].append(statement)

            if table_alters:
                generated_sql += "-- Alter Statements to synchronize target schema\n"
                for tbl, alters in table_alters.items():
                    generated_sql += f"ALTER TABLE `{tbl}`\n  " + ",\n  ".join(alters) + ";\n\n"

            return {
                "status": "success",
                "summary": {
                    "total_tables": len(src_tables),
                    "missing_tables_count": len(missing_tables),
                    "mismatched_columns_count": len(diffs)
                },
                "missing_tables": missing_tables_data,
                "column_differences": diffs,
                "generated_sql": generated_sql.strip()
            }
        finally:
            conn.close()

    @classmethod
    def compare_sqlite(cls, src_path, tgt_path):
        """Compare two SQLite databases and return upgrade statements"""
        src_conn = sqlite3.connect(src_path)
        tgt_conn = sqlite3.connect(tgt_path)
        
        try:
            src_cursor = src_conn.cursor()
            tgt_cursor = tgt_conn.cursor()

            # 1. Fetch tables
            src_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            src_tables = [row[0] for row in src_cursor.fetchall()]
            
            tgt_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tgt_tables = [row[0] for row in tgt_cursor.fetchall()]

            missing_tables = sorted(list(set(src_tables) - set(tgt_tables)))
            missing_tables_data = []
            generated_sql = ""

            for table in missing_tables:
                src_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
                row = src_cursor.fetchone()
                create_sql = row[0] if row else ""
                missing_tables_data.append({
                    "name": table,
                    "create_sql": create_sql
                })
                generated_sql += f"-- Create Table: {table} (Missing in Target)\n"
                generated_sql += create_sql + ";\n\n"

            # 2. Compare Columns
            diffs = []
            common_tables = list(set(src_tables) & set(tgt_tables) - set(missing_tables))
            
            for table in sorted(common_tables):
                # Fetch target columns
                tgt_cursor.execute(f"PRAGMA table_info(`{table}`)")
                tgt_cols = {row[1]: {
                    "type": row[2], 
                    "notnull": row[3], 
                    "dflt_value": row[4]
                } for row in tgt_cursor.fetchall()}

                # Fetch source columns
                src_cursor.execute(f"PRAGMA table_info(`{table}`)")
                src_cols_list = src_cursor.fetchall()

                for row in src_cols_list:
                    col_name = row[1]
                    col_type = row[2]
                    notnull = row[3]
                    dflt_value = row[4]

                    local_nullable = "NO" if notnull else "YES"
                    local_default = dflt_value

                    if col_name not in tgt_cols:
                        # Missing Column
                        diffs.append({
                            "TABLE_NAME": table,
                            "COLUMN_NAME": col_name,
                            "local_type": col_type,
                            "online_type": None,
                            "local_nullable": local_nullable,
                            "online_nullable": None,
                            "local_default": local_default,
                            "online_default": None,
                            "DifferenceType": "Missing Column"
                        })
                    else:
                        tgt_col = tgt_cols[col_name]
                        online_nullable = "NO" if tgt_col["notnull"] else "YES"
                        
                        type_mismatch = col_type.lower() != tgt_col["type"].lower()
                        null_mismatch = local_nullable != online_nullable
                        default_mismatch = str(local_default) != str(tgt_col["dflt_value"])

                        if type_mismatch or null_mismatch or default_mismatch:
                            diff_type = "Type Mismatch" if type_mismatch else ("Nullability Mismatch" if null_mismatch else "Default Value Mismatch")
                            diffs.append({
                                "TABLE_NAME": table,
                                "COLUMN_NAME": col_name,
                                "local_type": col_type,
                                "online_type": tgt_col["type"],
                                "local_nullable": local_nullable,
                                "online_nullable": online_nullable,
                                "local_default": local_default,
                                "online_default": tgt_col["dflt_value"],
                                "DifferenceType": diff_type
                            })

            # 3. Generate Alter statements for SQLite
            # SQLite does not support MODIFY COLUMN or ADD COLUMN with position details.
            # We output ALTER TABLE ADD COLUMN for missing columns, and warning comments for mismatches.
            alter_statements = []
            for diff in diffs:
                tbl = diff["TABLE_NAME"]
                col = diff["COLUMN_NAME"]
                diff_type = diff["DifferenceType"]
                col_type = diff["local_type"]
                notnull_clause = " NOT NULL" if diff["local_nullable"] == "NO" else ""
                default_clause = f" DEFAULT {diff['local_default']}" if diff["local_default"] is not None else ""

                if diff_type == "Missing Column":
                    alter_statements.append(f"ALTER TABLE `{tbl}` ADD COLUMN `{col}` {col_type}{notnull_clause}{default_clause};")
                else:
                    alter_statements.append(
                        f"\n-- WARNING: SQLite does not support MODIFY COLUMN directly.\n"
                        f"-- Column '{col}' in table '{tbl}' has '{diff_type}'.\n"
                        f"-- Requires rebuild table. Standard steps:\n"
                        f"--   CREATE TABLE `{tbl}_temp` (...);\n"
                        f"--   INSERT INTO `{tbl}_temp` SELECT ... FROM `{tbl}`;\n"
                        f"--   DROP TABLE `{tbl}`;\n"
                        f"--   ALTER TABLE `{tbl}_temp` RENAME TO `{tbl}`;\n"
                    )

            if alter_statements:
                generated_sql += "-- Alter Statements to synchronize SQLite schema\n"
                generated_sql += "\n".join(alter_statements) + "\n"

            return {
                "status": "success",
                "summary": {
                    "total_tables": len(src_tables),
                    "missing_tables_count": len(missing_tables),
                    "mismatched_columns_count": len(diffs)
                },
                "missing_tables": missing_tables_data,
                "column_differences": diffs,
                "generated_sql": generated_sql.strip()
            }
        finally:
            src_conn.close()
            tgt_conn.close()
