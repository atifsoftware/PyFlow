import socket
import time
import sys

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "db"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 3306
    timeout = 60  # max wait time in seconds
    start_time = time.time()

    print(f"Waiting for database connection at {host}:{port}...", flush=True)

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((host, port))
                print("Database is ready! Connecting now...", flush=True)
                sys.exit(0)
        except (socket.error, socket.timeout):
            if time.time() - start_time > timeout:
                print(f"Error: Database connection timed out after {timeout} seconds.", file=sys.stderr, flush=True)
                sys.exit(1)
            time.sleep(1)

if __name__ == "__main__":
    main()
