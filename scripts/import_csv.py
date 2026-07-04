import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.config import Base, SessionLocal, engine
from app.models import Transacao


def importar_dados():
    Base.metadata.create_all(bind=engine)

    csv_origem = Path("/home/beto/projetos/controle-financeiro/csv/2026.csv")
    if not csv_origem.exists():
        csv_origem = Path("/home/beto/projetos/controle-financeiro/2026.csv")

    if not csv_origem.exists():
        print("ERRO: Arquivo CSV de origem não foi encontrado.")
        return

    print(f"Lendo dados de {csv_origem}...")
    df = pd.read_csv(csv_origem)

    colunas_esperadas = {"Data", "Item", "Tipo", "Categoria", "Valor", "Pago"}
    if not colunas_esperadas.issubset(df.columns):
        print(f"ERRO: O CSV não possui as colunas esperadas: {colunas_esperadas}")
        return

    db = SessionLocal()
    try:
        db.query(Transacao).filter(Transacao.ano == 2026).delete()

        registros_salvos = 0
        for _, row in df.iterrows():
            item_nome = str(row["Item"]).strip()
            tipo_nome = str(row["Tipo"]).strip()
            categoria_nome = str(row["Categoria"]).strip()

            if not item_nome and not tipo_nome and not categoria_nome:
                continue

            partes_data = str(row["Data"]).split("/")
            if len(partes_data) != 3:
                continue

            mes = int(partes_data[1])
            ano = int(partes_data[2])
            valor = float(row["Valor"]) if not pd.isna(row["Valor"]) else 0.0
            pago = bool(row["Pago"]) if not pd.isna(row["Pago"]) else False

            db.add(Transacao(
                ano=ano,
                mes=mes,
                item=item_nome,
                tipo=tipo_nome,
                categoria=categoria_nome,
                valor=valor,
                pago=pago,
            ))
            registros_salvos += 1

        db.commit()
        print(f"Sucesso! {registros_salvos} transações importadas com sucesso para o banco de dados.")

    except Exception as e:
        db.rollback()
        print(f"ERRO ao importar dados: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    importar_dados()
