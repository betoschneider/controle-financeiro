from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verificar_autenticacao
from app.config import get_db
from app.models import Transacao, User

router = APIRouter(prefix="/api/transactions", tags=["Transações"])


class TransacaoCreate(BaseModel):
    ano: int
    mes: int
    item: str
    tipo: str
    categoria: str
    valor: float
    pago: bool


class TransacaoResponse(TransacaoCreate):
    id: int

    class Config:
        from_attributes = True


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_transacoes_por_ano(db: Session, ano: int, username: Optional[str]) -> List[Transacao]:
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []
    return db.query(Transacao).filter(
        Transacao.ano == ano,
        Transacao.owner_id == user.id,
    ).all()


def bulk_save_transacoes_por_ano(
    db: Session, ano: int, transacoes_in: List[TransacaoCreate], username: Optional[str]
) -> List[Transacao]:
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []

    db.query(Transacao).filter(
        Transacao.ano == ano,
        Transacao.owner_id == user.id,
    ).delete()

    novas_transacoes = []
    for tx in transacoes_in:
        if tx.item.strip() or tx.tipo.strip() or tx.categoria.strip():
            db_tx = Transacao(
                ano=ano,
                mes=tx.mes,
                item=tx.item.strip(),
                tipo=tx.tipo.strip(),
                categoria=tx.categoria.strip(),
                valor=tx.valor,
                pago=tx.pago,
                owner_id=user.id,
            )
            novas_transacoes.append(db_tx)

    db.add_all(novas_transacoes)
    db.commit()
    return novas_transacoes


@router.get("/anos", response_model=List[int])
def listar_anos_existentes(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    user = get_user_by_username(db, username)
    if not user:
        return []
    anos_tuples = db.query(Transacao.ano).filter(
        Transacao.owner_id == user.id
    ).distinct().all()
    anos = [a[0] for a in anos_tuples if a[0] is not None]
    return sorted(list(set(anos)))


@router.get("", response_model=List[TransacaoResponse])
def listar_transacoes(
    ano: int,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    transacoes = get_transacoes_por_ano(db, ano, username)

    ano_atual_sistema = datetime.now().year
    if not transacoes and ano > ano_atual_sistema:
        fechamento_ano_anterior = [
            tx for tx in get_transacoes_por_ano(db, ano - 1, username)
            if tx.mes == 12
        ]
        dummy_id = -1
        for tx in fechamento_ano_anterior:
            transacoes.append(
                Transacao(
                    id=dummy_id,
                    ano=ano,
                    mes=1,
                    item=tx.item,
                    tipo=tx.tipo,
                    categoria=tx.categoria,
                    valor=tx.valor,
                    pago=False,
                )
            )
            dummy_id -= 1

    return transacoes


@router.post("/bulk-save", response_model=List[TransacaoResponse])
def salvar_transacoes(
    ano: int,
    transacoes: List[TransacaoCreate],
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    return bulk_save_transacoes_por_ano(db, ano, transacoes, username)


@router.get("/download")
def download_csv(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    import csv
    import io

    user = get_user_by_username(db, username)
    transacoes = []
    if user:
        transacoes = db.query(Transacao).filter(Transacao.owner_id == user.id).order_by(
            Transacao.ano.desc(),
            Transacao.mes.asc(),
            Transacao.tipo,
            Transacao.categoria,
            Transacao.item,
        ).all()

    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Data", "Item", "Tipo", "Categoria", "Valor", "Pago"])

    for tx in transacoes:
        data_str = f"01/{tx.mes:02d}/{tx.ano}"
        pago_str = "True" if tx.pago else "False"
        writer.writerow([data_str, tx.item, tx.tipo, tx.categoria, tx.valor, pago_str])

    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=transacoes.csv"
    return response


@router.post("/upload")
def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    import csv
    import io

    contents = file.file.read()
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded = contents.decode("latin1")
        except Exception:
            raise HTTPException(status_code=400, detail="Não foi possível decodificar o arquivo.")

    stream = io.StringIO(decoded)
    try:
        reader = csv.DictReader(stream)
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de CSV inválido.")

    headers = reader.fieldnames
    if not headers or not all(h in headers for h in ["Data", "Item", "Tipo", "Categoria", "Valor", "Pago"]):
        raise HTTPException(
            status_code=400,
            detail="Cabeçalhos inválidos. O CSV deve conter: Data,Item,Tipo,Categoria,Valor,Pago",
        )

    novas_transacoes = []
    try:
        for idx, row in enumerate(reader):
            data_str = row["Data"].strip()
            try:
                dt = datetime.strptime(data_str, "%d/%m/%Y")
            except ValueError:
                try:
                    dt = datetime.strptime(data_str, "%Y-%m-%d")
                except ValueError:
                    try:
                        dt = datetime.strptime(data_str, "%d-%m-%Y")
                    except ValueError:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Formato de data inválido na linha {idx + 2}: {data_str}. Use DD/MM/YYYY.",
                        )

            try:
                valor = float(row["Valor"].strip())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Valor inválido na linha {idx + 2}: {row['Valor']}")

            pago_str = row["Pago"].strip().lower()
            pago = pago_str in ["true", "1", "t", "yes", "y", "pago", "efetivado"]

            item = row["Item"].strip()
            tipo = row["Tipo"].strip()
            categoria = row["Categoria"].strip()

            if item or tipo or categoria:
                novas_transacoes.append(
                    Transacao(
                        ano=dt.year,
                        mes=dt.month,
                        item=item,
                        tipo=tipo,
                        categoria=categoria,
                        valor=valor,
                        pago=pago,
                    )
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar CSV: {str(e)}")

    user = get_user_by_username(db, username)
    if user:
        db.query(Transacao).filter(Transacao.owner_id == user.id).delete()
        for tx in novas_transacoes:
            tx.owner_id = user.id
        db.add_all(novas_transacoes)
    db.commit()

    return {
        "success": True,
        "count": len(novas_transacoes),
        "message": f"{len(novas_transacoes)} lançamentos importados com sucesso.",
    }
