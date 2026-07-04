#!/usr/bin/env python3
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

DB_PATH = Path("data/controle_financeiro.db")
REQUIRED_TABLES = {"users", "transacoes", "investment_assets"}


def main() -> None:
    if not DB_PATH.exists():
        print("DB não existe; nenhum stamp necessário.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
    has_version_table = cur.fetchone() is not None

    if not has_version_table:
        existing_tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if REQUIRED_TABLES.issubset(existing_tables):
            if "audit_logs" in existing_tables:
                cur.execute("DROP TABLE IF EXISTS audit_logs")
                conn.commit()
                print("Removida tabela legacy audit_logs antes do stamp.")
            conn.close()
            config = Config("alembic.ini")
            command.stamp(config, "head")
            print("Stamp head aplicado em DB existente sem alembic_version.")
            return
        conn.close()
        print("DB existente não parece estar com o schema completo; stamp ignorado.")
        return

    cur.execute("SELECT count(*) FROM alembic_version")
    version_count = cur.fetchone()[0]
    if version_count == 0:
        existing_tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if REQUIRED_TABLES.issubset(existing_tables):
            if "audit_logs" in existing_tables:
                cur.execute("DROP TABLE IF EXISTS audit_logs")
                conn.commit()
                print("Removida tabela legacy audit_logs antes do stamp.")
            conn.close()
            config = Config("alembic.ini")
            command.stamp(config, "head")
            print("Stamp head aplicado em DB existente com alembic_version vazio.")
            return
        conn.close()
        print("alembic_version existe, mas DB não parece estar com o schema completo; stamp ignorado.")
        return

    conn.close()
    print("alembic_version já contém um revision; nada a fazer.")


if __name__ == "__main__":
    main()
