from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verificar_autenticacao
from app.config import get_db
from app.models import Categoria, Tipo, Transacao, User

router = APIRouter(prefix="/api/transactions", tags=["Transações"])
settings_router = APIRouter(prefix="/api/settings", tags=["Configurações"])


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


# --- Schemas para Settings (tipos e categorias) ---

class TipoCreate(BaseModel):
    nome: str


class TipoResponse(BaseModel):
    id: int
    nome: str
    is_protegido: bool

    class Config:
        from_attributes = True


class CategoriaCreate(BaseModel):
    nome: str
    valor: float = 0.0
    tipo_id: int


class CategoriaResponse(BaseModel):
    id: int
    nome: str
    valor: float
    tipo_id: int
    owner_id: Optional[int] = None
    is_protegido: bool
    tipo_nome: Optional[str] = None

    class Config:
        from_attributes = True


def seed_default_tipos(db: Session) -> None:
    """Cria os tipos padrão 'Receita' e 'Despesa' se não existirem."""
    tipos_existentes = {t.nome for t in db.query(Tipo).all()}
    default_tipos = [
        {"nome": "Receita", "is_protegido": True},
        {"nome": "Despesa", "is_protegido": True},
    ]
    for tp in default_tipos:
        if tp["nome"] not in tipos_existentes:
            db.add(Tipo(nome=tp["nome"], is_protegido=tp["is_protegido"]))
    db.commit()


def seed_default_categoria(db: Session, user: User) -> None:
    """Cria a categoria padrão 'Remuneração' para um novo usuário se não existir."""
    tipo_receita = db.query(Tipo).filter(Tipo.nome == "Receita").first()
    if not tipo_receita:
        return
    existente = db.query(Categoria).filter(
        Categoria.nome == "Remuneração",
        Categoria.owner_id == user.id,
    ).first()
    if not existente:
        db.add(Categoria(
            nome="Remuneração",
            valor=0.0,
            tipo_id=tipo_receita.id,
            owner_id=user.id,
            is_protegido=True,
        ))
        db.commit()


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
        # Carregar tipos existentes
        tipos_existentes = {t.nome.strip().lower(): t for t in db.query(Tipo).all()}

        # Carregar categorias existentes do usuário
        categorias_existentes = {
            c.nome.strip().lower(): c
            for c in db.query(Categoria).filter(Categoria.owner_id == user.id).all()
        }

        # Iterar sobre novas transações para criar tipos e categorias que faltam
        for tx in novas_transacoes:
            tipo_nome = tx.tipo.strip()
            cat_nome = tx.categoria.strip()

            if not tipo_nome or not cat_nome:
                continue

            tipo_lower = tipo_nome.lower()
            cat_lower = cat_nome.lower()

            # Garantir existência do Tipo
            if tipo_lower not in tipos_existentes:
                novo_tipo = Tipo(nome=tipo_nome, is_protegido=False)
                db.add(novo_tipo)
                db.commit()
                db.refresh(novo_tipo)
                tipos_existentes[tipo_lower] = novo_tipo

            tipo_obj = tipos_existentes[tipo_lower]

            # Garantir existência da Categoria (com valor float default 0.0)
            if cat_lower not in categorias_existentes:
                nova_cat = Categoria(
                    nome=cat_nome,
                    valor=0.0,
                    tipo_id=tipo_obj.id,
                    owner_id=user.id,
                    is_protegido=False
                )
                db.add(nova_cat)
                db.commit()
                db.refresh(nova_cat)
                categorias_existentes[cat_lower] = nova_cat

        # Salvar as transações
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


# --- Dashboard Endpoints ---


@router.get("/dashboard/categoria-comparativo")
def get_categoria_comparativo(
    ano: int,
    mes: Optional[str] = "Ano Completo",
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """
    Gráfico de comportamento de categorias:
    Mostra para cada categoria (onde tipo != 'Receita'):
      - Percentual que representa do total de Remuneração
      - Desvio da meta (coluna Valor da tabela Categorias)
    """
    from collections import defaultdict

    user = get_user_by_username(db, username)
    if not user:
        return {"categories": [], "remuneracao_total": 0, "meta_total": 0}

    # Carrega transações filtradas por ano (e mês se não for "Ano Completo")
    query = db.query(Transacao).filter(
        Transacao.ano == ano,
        Transacao.owner_id == user.id,
    )
    if mes and mes != "Ano Completo":
        mapa_meses = {
            "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
            "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12
        }
        mes_num = mapa_meses.get(mes)
        if mes_num:
            query = query.filter(Transacao.mes == mes_num)

    transacoes = query.all()

    # Carrega categorias cadastradas do usuário com suas metas
    categorias_cadastradas = db.query(Categoria).filter(
        Categoria.owner_id == user.id
    ).all()
    mapa_metas = {cat.nome.lower(): cat.valor for cat in categorias_cadastradas}

    # Soma os valores das categorias do tipo não-Receita
    categorias_nao_receita = defaultdict(float)
    remuneracao_total = 0.0

    for t in transacoes:
        valor = float(t.valor or 0)
        if t.tipo.strip().lower() != "receita":
            cat_key = t.categoria.strip() or "Sem Categoria"
            categorias_nao_receita[cat_key] += valor
        elif t.categoria.strip().lower() == "remuneração":
            remuneracao_total += valor

    result_data = []
    meta_total = sum(mapa_metas.values())

    for cat_nome, cat_valor in sorted(categorias_nao_receita.items(), key=lambda x: x[1], reverse=True):
        meta = mapa_metas.get(cat_nome.lower(), 0.0)

        # Representação da categoria em % do total de Remuneração
        if remuneracao_total > 0:
            valor_percentual_remuneracao = (cat_valor / remuneracao_total) * 100
        else:
            valor_percentual_remuneracao = 0.0

        # Desvio do planejado (percentual da meta)
        # Ex: meta = 10%, valor_percentual_remuneracao = 13%.
        # Desvio = ((13 - 10) / 10) * 100 = 30%.
        if meta > 0:
            desvio = ((valor_percentual_remuneracao - meta) / meta) * 100
        else:
            desvio = 0.0

        result_data.append({
            "categoria": cat_nome,
            "valor": round(cat_valor, 2),
            "percentual_nao_receita": 0.0, # Mantido para evitar quebra de contratos de API antigos
            "valor_percentual_remuneracao": round(valor_percentual_remuneracao, 2),
            "meta": round(meta, 2),
            "desvio": round(desvio, 2),
            "desvio_percentual": round(desvio, 2),
        })

    return {
        "categories": result_data,
        "remuneracao_total": round(remuneracao_total, 2),
        "total_nao_receita": round(sum(categorias_nao_receita.values()), 2),
        "meta_total": round(meta_total, 2),
    }


@router.get("/dropdown-data")
def get_dropdown_data(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """
    Retorna os tipos e categorias para alimentar os dropdowns da tabela de lançamentos.
    """
    user = get_user_by_username(db, username)
    if not user:
        return {"tipos": [], "categorias": []}

    # Garantir que tipos padrão existam
    seed_default_tipos(db)
    seed_default_categoria(db, user)

    tipos = db.query(Tipo).order_by(Tipo.id).all()
    categorias = db.query(Categoria).filter(
        Categoria.owner_id == user.id
    ).order_by(Categoria.id).all()

    return {
        "tipos": [{"id": t.id, "nome": t.nome} for t in tipos],
        "categorias": [
            {
                "id": c.id,
                "nome": c.nome,
                "tipo_id": c.tipo_id,
                "tipo_nome": next((t.nome for t in tipos if t.id == c.tipo_id), None),
            }
            for c in categorias
        ],
    }


# =============================================================================
# Settings Routes (tipos e categorias) - migradas de app/settings.py
# =============================================================================


# --- Tipos Endpoints ---

@settings_router.get("/tipos", response_model=List[TipoResponse])
def listar_tipos(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    seed_default_tipos(db)
    tipos = db.query(Tipo).order_by(Tipo.id).all()
    return tipos


@settings_router.post("/tipos", response_model=TipoResponse)
def criar_tipo(
    tipo_in: TipoCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    nome_stripped = tipo_in.nome.strip()
    if not nome_stripped:
        raise HTTPException(status_code=400, detail="Nome do tipo não pode estar vazio.")

    existente = db.query(Tipo).filter(Tipo.nome == nome_stripped).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Tipo '{nome_stripped}' já existe.")

    tipo = Tipo(nome=nome_stripped, is_protegido=False)
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


@settings_router.put("/tipos/{tipo_id}", response_model=TipoResponse)
def atualizar_tipo(
    tipo_id: int,
    tipo_in: TipoCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    tipo = db.query(Tipo).filter(Tipo.id == tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo não encontrado.")
    if tipo.is_protegido:
        raise HTTPException(status_code=403, detail="Tipos padrão não podem ser alterados.")

    nome_stripped = tipo_in.nome.strip()
    if not nome_stripped:
        raise HTTPException(status_code=400, detail="Nome do tipo não pode estar vazio.")

    conflito = db.query(Tipo).filter(Tipo.nome == nome_stripped, Tipo.id != tipo_id).first()
    if conflito:
        raise HTTPException(status_code=400, detail=f"Tipo '{nome_stripped}' já existe.")

    tipo.nome = nome_stripped
    db.commit()
    db.refresh(tipo)
    return tipo


@settings_router.delete("/tipos/{tipo_id}")
def remover_tipo(
    tipo_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    tipo = db.query(Tipo).filter(Tipo.id == tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo não encontrado.")
    if tipo.is_protegido:
        raise HTTPException(status_code=403, detail="Tipos padrão não podem ser removidos.")

    # Verificar se há categorias vinculadas a este tipo
    categorias_count = db.query(Categoria).filter(Categoria.tipo_id == tipo_id).count()
    if categorias_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível remover o tipo '{tipo.nome}' pois existem {categorias_count} categorias vinculadas a ele.",
        )

    # Verificar se há transações usando este tipo
    user = get_user_by_username(db, username)
    if user:
        transacoes_count = db.query(Transacao).filter(
            Transacao.owner_id == user.id,
            Transacao.tipo == tipo.nome,
        ).count()
        if transacoes_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível remover o tipo '{tipo.nome}' pois existem {transacoes_count} lançamentos usando este tipo.",
            )

    db.delete(tipo)
    db.commit()
    return {"success": True, "message": f"Tipo '{tipo.nome}' removido."}


# --- Categorias Endpoints ---

@settings_router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    user = get_user_by_username(db, username)
    if not user:
        return []

    seed_default_tipos(db)
    seed_default_categoria(db, user)

    categorias = db.query(Categoria).filter(Categoria.owner_id == user.id).order_by(Categoria.id).all()

    # Join com tipos para retornar nome do tipo
    result = []
    for cat in categorias:
        tipo = db.query(Tipo).filter(Tipo.id == cat.tipo_id).first()
        cat_dict = {
            "id": cat.id,
            "nome": cat.nome,
            "valor": cat.valor,
            "tipo_id": cat.tipo_id,
            "owner_id": cat.owner_id,
            "is_protegido": cat.is_protegido,
            "tipo_nome": tipo.nome if tipo else None,
        }
        result.append(CategoriaResponse(**cat_dict))
    return result


@settings_router.post("/categorias", response_model=CategoriaResponse)
def criar_categoria(
    cat_in: CategoriaCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    nome_stripped = cat_in.nome.strip()
    if not nome_stripped:
        raise HTTPException(status_code=400, detail="Nome da categoria não pode estar vazio.")

    # Verificar se tipo existe
    tipo = db.query(Tipo).filter(Tipo.id == cat_in.tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo informado não encontrado.")

    # Verificar duplicata para o mesmo usuário
    existente = db.query(Categoria).filter(
        Categoria.nome == nome_stripped,
        Categoria.owner_id == user.id,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Categoria '{nome_stripped}' já existe para este usuário.")

    categoria = Categoria(
        nome=nome_stripped,
        valor=cat_in.valor,
        tipo_id=cat_in.tipo_id,
        owner_id=user.id,
        is_protegido=False,
    )
    db.add(categoria)
    db.commit()
    db.refresh(categoria)

    return CategoriaResponse(
        id=categoria.id,
        nome=categoria.nome,
        valor=categoria.valor,
        tipo_id=categoria.tipo_id,
        owner_id=categoria.owner_id,
        is_protegido=categoria.is_protegido,
        tipo_nome=tipo.nome,
    )


@settings_router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    cat_in: CategoriaCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    categoria = db.query(Categoria).filter(
        Categoria.id == categoria_id,
        Categoria.owner_id == user.id,
    ).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    if categoria.is_protegido:
        raise HTTPException(status_code=403, detail="Categoria padrão não pode ser alterada.")

    nome_stripped = cat_in.nome.strip()
    if not nome_stripped:
        raise HTTPException(status_code=400, detail="Nome da categoria não pode estar vazio.")

    # Verificar se tipo existe
    tipo = db.query(Tipo).filter(Tipo.id == cat_in.tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo informado não encontrado.")

    # Verificar duplicata
    conflito = db.query(Categoria).filter(
        Categoria.nome == nome_stripped,
        Categoria.owner_id == user.id,
        Categoria.id != categoria_id,
    ).first()
    if conflito:
        raise HTTPException(status_code=400, detail=f"Categoria '{nome_stripped}' já existe.")

    categoria.nome = nome_stripped
    categoria.valor = cat_in.valor
    categoria.tipo_id = cat_in.tipo_id
    db.commit()
    db.refresh(categoria)

    return CategoriaResponse(
        id=categoria.id,
        nome=categoria.nome,
        valor=categoria.valor,
        tipo_id=categoria.tipo_id,
        owner_id=categoria.owner_id,
        is_protegido=categoria.is_protegido,
        tipo_nome=tipo.nome,
    )


@settings_router.delete("/categorias/{categoria_id}")
def remover_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    categoria = db.query(Categoria).filter(
        Categoria.id == categoria_id,
        Categoria.owner_id == user.id,
    ).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    if categoria.is_protegido:
        raise HTTPException(status_code=403, detail="Categoria padrão 'Remuneração' não pode ser removida.")

    # Verificar se há transações usando esta categoria
    transacoes_count = db.query(Transacao).filter(
        Transacao.owner_id == user.id,
        Transacao.categoria == categoria.nome,
    ).count()
    if transacoes_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível remover a categoria '{categoria.nome}' pois existem {transacoes_count} lançamentos usando esta categoria.",
        )

    db.delete(categoria)
    db.commit()
    return {"success": True, "message": f"Categoria '{categoria.nome}' removida."}
