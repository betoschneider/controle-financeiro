import os
import sys
from pathlib import Path
import pandas as pd

# Adiciona o diretório raiz do projeto ao sys.path para importar os módulos locais
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from backend.app.database import SessionLocal, engine, Base
from backend.app.models import Transacao

def importar_dados():
    # Garante que as tabelas estejam criadas no banco de dados
    Base.metadata.create_all(bind=engine)
    
    # Caminho do CSV original
    csv_origem = Path("/home/beto/projetos/controle-financeiro/csv/2026.csv")
    if not csv_origem.exists():
        csv_origem = Path("/home/beto/projetos/controle-financeiro/2026.csv")
        
    if not csv_origem.exists():
        print(f"ERRO: Arquivo CSV de origem não foi encontrado.")
        return

    print(f"Lendo dados de {csv_origem}...")
    df = pd.read_csv(csv_origem)
    
    # Valida colunas
    colunas_esperadas = {'Data', 'Item', 'Tipo', 'Categoria', 'Valor', 'Pago'}
    if not colunas_esperadas.issubset(df.columns):
        print(f"ERRO: O CSV não possui as colunas esperadas: {colunas_esperadas}")
        return

    db = SessionLocal()
    try:
        # Limpa dados existentes do ano 2026 para evitar duplicidade
        db.query(Transacao).filter(Transacao.ano == 2026).delete()
        
        registros_salvos = 0
        for _, row in df.iterrows():
            item_nome = str(row['Item']).strip()
            tipo_nome = str(row['Tipo']).strip()
            categoria_nome = str(row['Categoria']).strip()
            
            # Se for uma linha vazia, pula
            if not item_nome and not tipo_nome and not categoria_nome:
                continue
                
            # Extrai o mês e o ano da data (formato DD/MM/AAAA)
            partes_data = str(row['Data']).split('/')
            if len(partes_data) != 3:
                # Caso a data esteja em outro formato, pula ou tenta converter
                continue
                
            mes = int(partes_data[1])
            ano = int(partes_data[2])
            
            valor = float(row['Valor']) if not pd.isna(row['Valor']) else 0.0
            pago = bool(row['Pago']) if not pd.isna(row['Pago']) else False
            
            db_tx = Transacao(
                ano=ano,
                mes=mes,
                item=item_nome,
                tipo=tipo_nome,
                categoria=categoria_nome,
                valor=valor,
                pago=pago
            )
            db.add(db_tx)
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
