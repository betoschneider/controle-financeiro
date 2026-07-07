from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verificar_autenticacao
from app.config import get_db
from app.models import Categoria, Tipo, User
from app.transactions import get_user_by_username

router = APIRouter(prefix="/api/settings", tags=["Configurações"])


# --- Schemas ---

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


# --- Helper functions ---

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


# --- Tipos Endpoints ---

@router.get("/tipos", response_model=List[TipoResponse])
def listar_tipos(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    seed_default_tipos(db)
    tipos = db.query(Tipo).order_by(Tipo.id).all()
    return tipos


@router.post("/tipos", response_model=TipoResponse)
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


@router.put("/tipos/{tipo_id}", response_model=TipoResponse)
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


@router.delete("/tipos/{tipo_id}")
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
        from app.models import Transacao
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

@router.get("/categorias", response_model=List[CategoriaResponse])
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


@router.post("/categorias", response_model=CategoriaResponse)
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


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
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


@router.delete("/categorias/{categoria_id}")
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
    from app.models import Transacao
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
