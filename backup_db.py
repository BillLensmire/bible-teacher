#!/usr/bin/env python3
"""
Backup the remote PostgreSQL database, copy it locally, and restore to the local DB.

Requires:
    - SSH key-based access to the remote host (passwordless login)
    - pg_dump and psql (or pg_restore) available locally
    - Environment variables configured in .env file

Usage:
    python backup_db.py
    python backup_db.py --no-restore   # only download backup
    python backup_db.py --backup-file backups/my_backup.sql  # restore from existing file
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / "backups"

# Remote DB configuration
REMOTE_HOST = os.environ.get("REMOTE_HOST")
REMOTE_USER = os.environ.get("REMOTE_USER")
REMOTE_DB_NAME = os.environ.get("REMOTE_DB_NAME", os.environ.get("DB_NAME"))
REMOTE_DB_USER = os.environ.get("REMOTE_DB_USER", os.environ.get("DB_USER"))
REMOTE_DB_PASSWORD = os.environ.get("REMOTE_DB_PASSWORD", os.environ.get("DB_PASSWORD", ""))
REMOTE_DB_HOST = os.environ.get("REMOTE_DB_HOST", "localhost")
REMOTE_DB_PORT = os.environ.get("REMOTE_DB_PORT", "5432")

# Local DB configuration (reuses existing Django DB env vars)
LOCAL_DB_NAME = os.environ.get("DB_NAME", "bibleteacher")
LOCAL_DB_USER = os.environ.get("DB_USER", "bibleuser")
LOCAL_DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
LOCAL_DB_HOST = os.environ.get("DB_HOST", "localhost")
LOCAL_DB_PORT = os.environ.get("DB_PORT", "5432")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def run_cmd(cmd: list[str], env: dict | None = None, **kwargs) -> subprocess.CompletedProcess:
    """Run a shell command and raise on failure."""
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(cmd, capture_output=True, text=True, env=merged_env, **kwargs)
    if result.returncode != 0:
        log(f"Command failed: {' '.join(cmd)}")
        log(f"stderr: {result.stderr}")
        raise RuntimeError(f"Command failed with return code {result.returncode}")
    return result


def build_ssh_prefix() -> list[str]:
    """Build the SSH command prefix for remote execution."""
    if not REMOTE_HOST:
        raise RuntimeError("REMOTE_HOST environment variable is required.")
    user_part = f"{REMOTE_USER}@" if REMOTE_USER else ""
    return ["ssh", f"{user_part}{REMOTE_HOST}"]


def remote_dump(local_path: Path) -> None:
    """Run pg_dump on the remote host and write the SQL to a local file."""
    log("Starting remote pg_dump...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    ssh_cmd = build_ssh_prefix()
    pg_dump = "pg_dump"
    remote_cmd = (
        f"PGPASSWORD='{REMOTE_DB_PASSWORD}' {pg_dump} "
        f"--host={REMOTE_DB_HOST} "
        f"--port={REMOTE_DB_PORT} "
        f"--username={REMOTE_DB_USER} "
        f"--dbname={REMOTE_DB_NAME} "
        f"--no-owner --no-privileges --clean --if-exists"
    )

    full_cmd = ssh_cmd + [remote_cmd]
    log(f"Running: {' '.join(full_cmd)}")

    with open(local_path, "w") as f:
        result = subprocess.run(full_cmd, stdout=f, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        log(f"Remote pg_dump failed:\n{result.stderr}")
        raise RuntimeError("Remote pg_dump failed")
    log(f"Remote dump saved to {local_path}")


def restore_local(sql_path: Path) -> None:
    """Restore the given SQL file to the local PostgreSQL database."""
    log(f"Restoring to local DB '{LOCAL_DB_NAME}'...")

    env = os.environ.copy()
    if LOCAL_DB_PASSWORD:
        env["PGPASSWORD"] = LOCAL_DB_PASSWORD

    # Recreate the database to ensure a clean restore
    log("Recreating local database...")
    drop_cmd = [
        "dropdb",
        "--host", LOCAL_DB_HOST,
        "--port", LOCAL_DB_PORT,
        "--username", LOCAL_DB_USER,
        "--if-exists",
        LOCAL_DB_NAME,
    ]
    run_cmd(drop_cmd, env=env)

    create_cmd = [
        "createdb",
        "--host", LOCAL_DB_HOST,
        "--port", LOCAL_DB_PORT,
        "--username", LOCAL_DB_USER,
        LOCAL_DB_NAME,
    ]
    run_cmd(create_cmd, env=env)

    restore_cmd = [
        "psql",
        "--host", LOCAL_DB_HOST,
        "--port", LOCAL_DB_PORT,
        "--username", LOCAL_DB_USER,
        "--dbname", LOCAL_DB_NAME,
        "--file", str(sql_path),
    ]
    log(f"Running: {' '.join(restore_cmd)}")
    run_cmd(restore_cmd, env=env)
    log("Local restore complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup remote DB and restore locally")
    parser.add_argument(
        "--no-restore",
        action="store_true",
        help="Only download the backup; do not restore to local DB",
    )
    parser.add_argument(
        "--backup-file",
        type=Path,
        help="Restore from an existing local backup file instead of dumping from remote",
    )
    args = parser.parse_args()

    if args.backup_file:
        sql_path = args.backup_file.resolve()
        if not sql_path.exists():
            log(f"Backup file not found: {sql_path}")
            sys.exit(1)
        restore_local(sql_path)
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sql_path = BACKUP_DIR / f"{REMOTE_DB_NAME}_{timestamp}.sql"

    remote_dump(sql_path)

    if args.no_restore:
        log("Backup downloaded. Skipping restore.")
        sys.exit(0)

    restore_local(sql_path)
    log("Done.")


if __name__ == "__main__":
    main()
