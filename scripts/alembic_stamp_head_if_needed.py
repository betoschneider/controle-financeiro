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

    cur.execute("SELECT version_num FROM alembic_version")
    row = cur.fetchone()
    if row:
        current_revision = row[0]
        # Se o banco existente referencia migrações antigas que não existem mais,
        # limpa o alembic_version e faz stamp para a head atual
        from alembic.script import ScriptDirectory
        config = Config("alembic.ini")
        script = ScriptDirectory.from_config(config)
        head_revision = script.get_current_head()

        if current_revision != head_revision:
            cur.execute("DELETE FROM alembic_version")
            conn.commit()
            conn.close()
            command.stamp(config, "head")
            print(f"Stamp head aplicado: revisão antiga '{current_revision}' substituída por '{head_revision}'.")
            return

        conn.close()
        print("alembic_version já está na revisão head; nada a fazer.")
        return

    # alembic_version table exists but is empty
    existing_tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if REQUIRED_TABLES.issubset(existing_tables):
        conn.close()
        config = Config("alembic.ini")
        command.stamp(config, "head")
        print("Stamp head aplicado em DB existente com alembic_version vazio.")
        return
    conn.close()
    print("alembic_version existe, mas DB não parece estar com o schema completo; stamp ignorado.")


if __name__ == "__main__":
    main()
