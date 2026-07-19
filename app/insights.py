import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verificar_autenticacao
from app.config import get_db
from app.models import (
    FinancialInsight,
    InvestmentAsset,
    InvestmentInsight,
    InvestmentTransaction,
    Transacao,
    User,
)
from app.transactions import get_user_by_username

router = APIRouter(prefix="/api/insights", tags=["Insights"])


def _get_user(db: Session, username: str) -> User:
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return user


def _call_ai(prompt: str, provider: Optional[str], api_key: Optional[str]) -> str:
    """Chama a API do provedor de IA selecionado e retorna o texto gerado."""
    if not provider or not api_key:
        return (
            "⚠️ **Provedor de IA não configurado.**\n\n"
            "Acesse o **Painel de Controle** (ícone de engrenagem no cabeçalho) "
            "para configurar seu provedor de IA e chave de API antes de gerar insights."
        )

    provider = provider.lower()

    if provider == "openai":
        return _call_openai(prompt, api_key)
    elif provider == "anthropic":
        return _call_anthropic(prompt, api_key)
    elif provider == "gemini":
        return _call_gemini(prompt, api_key)
    elif provider == "deepseek":
        return _call_deepseek(prompt, api_key)
    else:
        return f"Provedor '{provider}' não suportado. Use: OpenAI, Anthropic, Gemini ou DeepSeek."


def _call_openai(prompt: str, api_key: str) -> str:
    import httpx

    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é um assistente especializado em finanças pessoais e investimentos. "
                        "Responda em português do Brasil de forma clara e concisa.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1000,
                "temperature": 0.7,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erro ao chamar OpenAI: {str(e)}"


def _call_anthropic(prompt: str, api_key: str) -> str:
    import httpx

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Você é um assistente especializado em finanças pessoais e investimentos. Responda em português do Brasil de forma clara e concisa.\n\n{prompt}",
                    }
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except Exception as e:
        return f"Erro ao chamar Anthropic: {str(e)}"


def _call_gemini(prompt: str, api_key: str) -> str:
    import httpx

    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"Você é um assistente especializado em finanças pessoais e investimentos. Responda em português do Brasil de forma clara e concisa.\n\n{prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 1000,
                    "temperature": 0.7,
                },
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Erro ao chamar Gemini: {str(e)}"


def _call_deepseek(prompt: str, api_key: str) -> str:
    import httpx

    try:
        resp = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é um assistente especializado em finanças pessoais e investimentos. "
                        "Responda em português do Brasil de forma clara e concisa.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1000,
                "temperature": 0.7,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erro ao chamar DeepSeek: {str(e)}"


def _build_financial_prompt(db: Session, user: User) -> str:
    """Monta o prompt de análise financeira com os dados do usuário."""
    transacoes = (
        db.query(Transacao)
        .filter(Transacao.owner_id == user.id)
        .order_by(Transacao.ano.desc(), Transacao.mes.desc())
        .limit(100)
        .all()
    )

    if not transacoes:
        return "Nenhuma movimentação financeira encontrada para gerar insights."

    # Agrupa por ano/mês
    meses = {}
    for t in transacoes:
        chave = f"{t.ano}-{t.mes:02d}"
        if chave not in meses:
            meses[chave] = {"receita": 0, "despesa": 0, "investimento": 0, "reserva": 0}
        tipo = t.tipo.lower()
        if tipo in meses[chave]:
            meses[chave][tipo] += t.valor or 0

    resumo_meses = []
    for chave in sorted(meses.keys())[-6:]:  # Últimos 6 meses
        m = meses[chave]
        saldo = m["receita"] - m["despesa"] - m["investimento"]
        resumo_meses.append(
            f"- {chave}: Receita=R${m['receita']:.2f}, Despesa=R${m['despesa']:.2f}, "
            f"Investimento=R${m['investimento']:.2f}, Saldo=R${saldo:.2f}"
        )

    # Categorias mais frequentes
    categorias = {}
    for t in transacoes:
        if t.categoria:
            categorias[t.categoria] = categorias.get(t.categoria, 0) + (t.valor or 0)
    top_categorias = sorted(categorias.items(), key=lambda x: -x[1])[:5]
    cat_text = ", ".join([f"{cat}=R${v:.2f}" for cat, v in top_categorias])

    prompt = (
        "Analise os dados financeiros abaixo e gere insights práticos e objetivos.\n\n"
        f"**Resumo dos últimos meses:**\n"
        + "\n".join(resumo_meses)
        + f"\n\n**Top 5 categorias por valor:**\n{cat_text}"
        + "\n\nCom base nesses dados, forneça:\n"
        "1. **Diagnóstico**: Como está a saúde financeira?\n"
        "2. **Riscos**: Quais pontos merecem atenção?\n"
        "3. **Recomendações**: Sugestões práticas para melhorar.\n"
        "Seja direto e use tópicos."
    )
    return prompt


def _build_investment_prompt(db: Session, user: User) -> str:
    """Monta o prompt de análise de investimentos com os dados do usuário."""
    ativos = (
        db.query(InvestmentAsset)
        .filter(InvestmentAsset.owner_id == user.id)
        .all()
    )

    if not ativos:
        return "Nenhum ativo de investimento encontrado para gerar insights."

    linhas = []
    total = 0
    for a in ativos:
        qtd = a.quantity or 0
        preco = a.purchase_price or 0
        valor_total = qtd * preco
        total += valor_total
        meta = a.target or 0
        linhas.append(
            f"- {a.ticker} ({a.company}): {qtd} cotas, Preço médio=R${preco:.2f}, "
            f"Valor total=R${valor_total:.2f}, Meta={meta:.1f}%"
        )

    # Transações recentes
    txs = (
        db.query(InvestmentTransaction)
        .filter(InvestmentTransaction.owner_id == user.id)
        .order_by(InvestmentTransaction.id.desc())
        .limit(10)
        .all()
    )
    tx_text = ""
    if txs:
        tx_text = "\n**Últimas transações:**\n" + "\n".join(
            [f"- {tx.ticker}: {tx.quantity} cotas a R${tx.purchase_price:.2f}" for tx in txs]
        )

    prompt = (
        "Analise a carteira de investimentos abaixo e gere insights práticos.\n\n"
        f"**Carteira (valor total: R${total:.2f}):**\n"
        + "\n".join(linhas)
        + tx_text
        + "\n\nCom base nesses dados, forneça:\n"
        "1. **Diversificação**: A carteira está bem diversificada?\n"
        "2. **Alocação**: Os percentuais estão alinhados com as metas?\n"
        "3. **Riscos**: Há concentração excessiva em algum ativo/setor?\n"
        "4. **Recomendações**: Sugestões práticas para rebalanceamento.\n"
        "Seja direto e use tópicos."
    )
    return prompt


# --- Endpoints de Insights Financeiros ---


class InsightResponse(BaseModel):
    id: int
    content: str
    created_at: str


@router.get("/financial", response_model=InsightResponse)
def get_financial_insight(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Retorna o último insight financeiro gerado."""
    user = _get_user(db, username)
    insight = (
        db.query(FinancialInsight)
        .filter(FinancialInsight.owner_id == user.id)
        .order_by(FinancialInsight.created_at.desc())
        .first()
    )
    if not insight:
        return InsightResponse(
            id=-1,
            content="Nenhum insight gerado ainda. Clique em 'Gerar Insights' para começar.",
            created_at="",
        )
    return InsightResponse(
        id=insight.id,
        content=insight.content,
        created_at=insight.created_at.isoformat(),
    )


@router.post("/financial/generate", response_model=InsightResponse)
def generate_financial_insight(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Gera um novo insight financeiro usando IA."""
    user = _get_user(db, username)
    prompt = _build_financial_prompt(db, user)
    content = _call_ai(prompt, user.ai_provider, user.api_key)

    insight = FinancialInsight(content=content, owner_id=user.id)
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return InsightResponse(
        id=insight.id,
        content=insight.content,
        created_at=insight.created_at.isoformat(),
    )


# --- Endpoints de Insights de Investimentos ---


@router.get("/investment", response_model=InsightResponse)
def get_investment_insight(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Retorna o último insight de investimentos gerado."""
    user = _get_user(db, username)
    insight = (
        db.query(InvestmentInsight)
        .filter(InvestmentInsight.owner_id == user.id)
        .order_by(InvestmentInsight.created_at.desc())
        .first()
    )
    if not insight:
        return InsightResponse(
            id=-1,
            content="Nenhum insight gerado ainda. Clique em 'Gerar Insights' para começar.",
            created_at="",
        )
    return InsightResponse(
        id=insight.id,
        content=insight.content,
        created_at=insight.created_at.isoformat(),
    )


@router.post("/investment/generate", response_model=InsightResponse)
def generate_investment_insight(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Gera um novo insight de investimentos usando IA."""
    user = _get_user(db, username)
    prompt = _build_investment_prompt(db, user)
    content = _call_ai(prompt, user.ai_provider, user.api_key)

    insight = InvestmentInsight(content=content, owner_id=user.id)
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return InsightResponse(
        id=insight.id,
        content=insight.content,
        created_at=insight.created_at.isoformat(),
    )
