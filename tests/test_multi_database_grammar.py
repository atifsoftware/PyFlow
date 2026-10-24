"""
tests/test_multi_database_grammar.py
====================================
Comprehensive tests for PyFlow's Multi-Database Engine & Grammar Architecture.
Tests SQL compilers (Grammar), Schema Grammar, multi-connection registry, and cross-database model querying.
"""

import unittest
from core.database import Database, DatabaseManager, QueryError
from core.database.grammar.mysql_grammar import MySqlGrammar
from core.database.grammar.postgres_grammar import PostgresGrammar
from core.database.grammar.sqlite_grammar import SqliteGrammar
from core.database.schema.mysql_schema_grammar import MySqlSchemaGrammar
from core.database.schema.postgres_schema_grammar import PostgresSchemaGrammar
from core.database.schema.sqlite_schema_grammar import SqliteSchemaGrammar
from core.query_builder import QueryBuilder
from core.model import Model


class TestModelA(Model):
    table = "test_items_a"
    connection = "db_alpha"
    fillable = ["name", "value"]


class TestModelB(Model):
    table = "test_items_b"
    connection = "db_beta"
    fillable = ["title", "count"]


class MultiDatabaseGrammarTest(unittest.TestCase):

    def setUp(self):
        Database.manager().purge()
        # Configure multiple active connections
        self.config = {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": ":memory:",
                },
                "db_alpha": {
                    "driver": "sqlite",
                    "database": ":memory:",
                },
                "db_beta": {
                    "driver": "sqlite",
                    "database": ":memory:",
                },
                "mysql": {
                    "driver": "mysql",
                    "host": "127.0.0.1",
                    "port": 3306,
                    "database": "mock_mysql",
                    "user": "root",
                    "password": "",
                },
                "pgsql": {
                    "driver": "postgresql",
                    "host": "127.0.0.1",
                    "port": 5432,
                    "database": "mock_pgsql",
                    "user": "postgres",
                    "password": "",
                }
            }
        }
        Database.init(self.config)

    def tearDown(self):
        Database.manager().purge()

    # ──────────────────────────────────────────────────────── Grammar Tests
    def test_mysql_grammar_wrapping_and_placeholders(self):
        grammar = MySqlGrammar()
        self.assertEqual(grammar.wrap_value("users"), "`users`")
        self.assertEqual(grammar.wrap("users.email"), "`users`.`email`")
        self.assertEqual(grammar.wrap("users u"), "`users` `u`")
        self.assertEqual(grammar.wrap("id as user_id"), "`id` AS `user_id`")
        self.assertEqual(grammar.placeholder, "%s")

    def test_postgres_grammar_wrapping_and_placeholders(self):
        grammar = PostgresGrammar()
        self.assertEqual(grammar.wrap_value("orders"), '"orders"')
        self.assertEqual(grammar.wrap("orders.total"), '"orders"."total"')
        self.assertEqual(grammar.wrap("total as order_total"), '"total" AS "order_total"')
        self.assertEqual(grammar.placeholder, "%s")

    def test_sqlite_grammar_wrapping_and_placeholders(self):
        grammar = SqliteGrammar()
        self.assertEqual(grammar.wrap_value("items"), '"items"')
        self.assertEqual(grammar.wrap("items.price"), '"items"."price"')
        self.assertEqual(grammar.placeholder, "?")

    def test_grammar_date_and_json_dialects(self):
        mysql = MySqlGrammar()
        postgres = PostgresGrammar()
        sqlite = SqliteGrammar()

        # Date compilation
        self.assertEqual(mysql.compile_where_date("created_at", "="), "DATE(created_at) = %s")
        self.assertEqual(postgres.compile_where_date("created_at", "="), "created_at::date = %s")
        self.assertEqual(sqlite.compile_where_date("created_at", "="), "date(created_at) = ?")

        # Date parts
        self.assertEqual(mysql.compile_where_date_func("birthdate", "year", "="), "YEAR(birthdate) = %s")
        self.assertEqual(postgres.compile_where_date_func("birthdate", "year", "="), "EXTRACT(YEAR FROM birthdate) = %s")
        self.assertEqual(sqlite.compile_where_date_func("birthdate", "year", "="), "strftime('%Y', birthdate) = ?")

        # JSON queries
        self.assertEqual(mysql.compile_where_json_contains("meta"), "JSON_CONTAINS(meta, %s, %s)")
        self.assertEqual(postgres.compile_where_json_contains("meta"), "meta::jsonb @> %s::jsonb")

    def test_schema_grammars(self):
        mysql_schema = MySqlSchemaGrammar()
        postgres_schema = PostgresSchemaGrammar()
        sqlite_schema = SqliteSchemaGrammar()

        self.assertEqual(mysql_schema.wrap_table("users"), "`users`")
        self.assertEqual(postgres_schema.wrap_table("users"), '"users"')
        self.assertEqual(sqlite_schema.wrap_table("users"), '"users"')

        self.assertEqual(mysql_schema.compile_drop("users"), "DROP TABLE `users`")
        self.assertEqual(postgres_schema.compile_drop("users"), 'DROP TABLE "users"')
        self.assertEqual(sqlite_schema.compile_drop("users"), 'DROP TABLE "users"')

    # ────────────────────────────────────────────── DatabaseManager Registry
    def test_database_manager_connections(self):
        default_conn = Database.connection()
        self.assertEqual(default_conn.driver, "sqlite")

        alpha_conn = Database.connection("db_alpha")
        beta_conn = Database.connection("db_beta")
        self.assertIsNot(alpha_conn, beta_conn)
        self.assertEqual(alpha_conn.name, "db_alpha")
        self.assertEqual(beta_conn.name, "db_beta")

    # ────────────────────────────── Simultaneous Multi-Database Querying
    def test_simultaneous_multi_database_execution(self):
        # Create different tables in db_alpha and db_beta
        alpha = Database.connection("db_alpha")
        beta = Database.connection("db_beta")

        alpha.execute("CREATE TABLE test_items_a (id INTEGER PRIMARY KEY, name TEXT, value INT)")
        beta.execute("CREATE TABLE test_items_b (id INTEGER PRIMARY KEY, title TEXT, count INT)")

        # Insert records into alpha
        alpha.execute("INSERT INTO test_items_a (name, value) VALUES (?, ?)", ("Alpha One", 100))
        alpha.execute("INSERT INTO test_items_a (name, value) VALUES (?, ?)", ("Alpha Two", 200))
        alpha.commit()

        # Insert records into beta
        beta.execute("INSERT INTO test_items_b (title, count) VALUES (?, ?)", ("Beta Item", 555))
        beta.commit()

        # Query using QueryBuilder on each connection
        qb_alpha = QueryBuilder("test_items_a", connection=alpha)
        rows_a = qb_alpha.get()
        self.assertEqual(len(rows_a), 2)
        self.assertEqual(rows_a[0]["name"], "Alpha One")

        qb_beta = QueryBuilder("test_items_b", connection=beta)
        rows_b = qb_beta.get()
        self.assertEqual(len(rows_b), 1)
        self.assertEqual(rows_b[0]["title"], "Beta Item")

        # Verify cross-isolation: test_items_b does not exist in db_alpha
        with self.assertRaises(QueryError):
            QueryBuilder("test_items_b", connection=alpha).get()

    # ─────────────────────────────────────── Model Multi-Database Binding
    def test_model_multi_database_binding(self):
        alpha = Database.connection("db_alpha")
        beta = Database.connection("db_beta")

        alpha.execute("CREATE TABLE test_items_a (id INTEGER PRIMARY KEY, name TEXT, value INT, created_at TEXT, updated_at TEXT)")
        beta.execute("CREATE TABLE test_items_b (id INTEGER PRIMARY KEY, title TEXT, count INT, created_at TEXT, updated_at TEXT)")

        # Create records using Model
        item_a = TestModelA.create({"name": "Model Item A", "value": 42})
        self.assertIsNotNone(item_a.id)
        self.assertEqual(item_a.name, "Model Item A")

        item_b = TestModelB.create({"title": "Model Item B", "count": 99})
        self.assertIsNotNone(item_b.id)
        self.assertEqual(item_b.title, "Model Item B")

        # Read back from respective databases
        found_a = TestModelA.find(item_a.id)
        found_b = TestModelB.find(item_b.id)
        self.assertEqual(found_a.value, 42)
        self.assertEqual(found_b.count, 99)

        # Verify records count per connection
        self.assertEqual(TestModelA.query().count(), 1)
        self.assertEqual(TestModelB.query().count(), 1)

    # ───────────────────────────── Transactions on Specific Connections
    def test_connection_specific_transactions(self):
        alpha = Database.connection("db_alpha")
        alpha.execute("CREATE TABLE test_items_a (id INTEGER PRIMARY KEY, name TEXT, value INT)")

        # Test rollback on specific connection
        try:
            with alpha.transaction():
                alpha.execute("INSERT INTO test_items_a (name, value) VALUES (?, ?)", ("Tx Rollback", 1))
                raise ValueError("Force rollback")
        except ValueError:
            pass

        rows = QueryBuilder("test_items_a", connection=alpha).get()
        self.assertEqual(len(rows), 0)

        # Test commit on specific connection
        with alpha.transaction():
            alpha.execute("INSERT INTO test_items_a (name, value) VALUES (?, ?)", ("Tx Commit", 2))

        rows = QueryBuilder("test_items_a", connection=alpha).get()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Tx Commit")


if __name__ == "__main__":
    unittest.main()
