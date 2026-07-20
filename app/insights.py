import json
import time
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verificar_autenticacao
from app.config import get_db
from app.models import (
    Categoria,
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
            "Provedor de IA nao configurado.\n\n"
            "Acesse o Painel de Controle (icone de engrenagem no cabecalho) "
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
        return f"Provedor '{provider}' nao suportado. Use: OpenAI, Anthropic, Gemini ou DeepSeek."


def _call_openai(prompt: str, api_key: str) -> str:
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
                        "content": "Voce e um assistente especializado em financas pessoais e investimentos. Responda em portugues do Brasil de forma clara e concisa.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 3000,
                "temperature": 0.7,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erro ao chamar OpenAI: {str(e)}"


def _call_anthropic(prompt: str, api_key: str) -> str:
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
                "max_tokens": 3000,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Voce e um assistente especializado em financas pessoais e investimentos. Responda em portugues do Brasil de forma clara e concisa.\n\n{prompt}",
                    }
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except Exception as e:
        return f"Erro ao chamar Anthropic: {str(e)}"


def _call_gemini(prompt: str, api_key: str) -> str:
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"Voce e um assistente especializado em financas pessoais e investimentos. Responda em portugues do Brasil de forma clara e concisa.\n\n{prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 3000,
                    "temperature": 0.7,
                },
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Erro ao chamar Gemini: {str(e)}"


def _call_deepseek(prompt: str, api_key: str) -> str:
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
                        "content": "Voce e um assistente especializado em financas pessoais e investimentos. Responda em portugues do Brasil de forma clara e concisa.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 3000,
                "temperature": 0.7,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erro ao chamar DeepSeek: {str(e)}"


def _build_financial_prompt(db: Session, user: User, ano: Optional[int] = None) -> str:
    """Monta o prompt de analise financeira com os dados do usuario.

    Regras temporais:
    - Meses passados: considera apenas efetivados (pago=True)
    - Meses futuros: considera apenas previstos (pago=False)
    - Mes atual: considera ambos (efetivado + previsto)
    """
    if not ano:
        ano = datetime.now().year

    transacoes = (
        db.query(Transacao)
        .filter(Transacao.owner_id == user.id, Transacao.ano == ano)
        .order_by(Transacao.mes, Transacao.item)
        .all()
    )

    if not transacoes:
        return "Nenhuma movimentacao financeira encontrada para gerar insights."

    now = datetime.now()
    mes_atual = now.month if now.year == ano else 12

    linhas_tabela = []
    meses_agregados = {}
    categorias_despesa = {}
    categorias_todas = {}
    total_receitas = 0.0
    total_remuneracao = 0.0
    total_despesas = 0.0
    total_investimentos = 0.0
    total_reservas = 0.0

    for t in transacoes:
        if t.mes < mes_atual:
            if not t.pago:
                continue
            status = "Efetivado"
        elif t.mes > mes_atual:
            if t.pago:
                continue
            status = "Previsto"
        else:
            status = "Efetivado" if t.pago else "Previsto"

        valor = t.valor or 0.0
        tipo = t.tipo.lower()

        linhas_tabela.append(
            f"| {t.mes:02d}/{ano} | {t.item[:40]:40s} | {t.categoria[:30]:30s} | {t.tipo[:15]:15s} | R${valor:>10.2f} | {status:11s} |"
        )

        chave_mes = t.mes
        if chave_mes not in meses_agregados:
            meses_agregados[chave_mes] = {"receita": 0.0, "despesa": 0.0, "investimento": 0.0, "reserva": 0.0}
        if tipo in meses_agregados[chave_mes]:
            meses_agregados[chave_mes][tipo] += valor

        if tipo == "despesa" and t.categoria:
            categorias_despesa[t.categoria] = categorias_despesa.get(t.categoria, 0.0) + valor

        if t.categoria:
            chave_cat = f"{t.tipo}:{t.categoria}"
            categorias_todas[chave_cat] = categorias_todas.get(chave_cat, 0.0) + valor

        if tipo == "receita":
            total_receitas += valor
            if t.categoria and t.categoria.strip().lower() == "remuneração":
                total_remuneracao += valor
        elif tipo == "despesa":
            total_despesas += valor
        elif tipo == "investimento":
            total_investimentos += valor
        elif tipo == "reserva":
            total_reservas += valor

    resumo_meses = []
    for mes in range(1, 13):
        if mes in meses_agregados:
            m = meses_agregados[mes]
            saldo = m["receita"] - m["despesa"] - m["investimento"] - m["reserva"]
            indicador = "ATUAL" if mes == mes_atual else ("PASSADO" if mes < mes_atual else "FUTURO")
            resumo_meses.append(
                f"| {indicador:10s} | {mes:02d}/{ano} | Receita=R${m['receita']:>10.2f} | Despesa=R${m['despesa']:>10.2f} | Investimento=R${m['investimento']:>10.2f} | Reserva=R${m['reserva']:>10.2f} | Saldo=R${saldo:>10.2f} |"
            )

    categorias_cadastradas = db.query(Categoria).filter(Categoria.owner_id == user.id).all()
    mapa_metas = {c.nome.lower(): c.valor for c in categorias_cadastradas}

    base_calculo = total_remuneracao if total_remuneracao > 0 else total_receitas

    linhas_metas = []
    for cat_nome, cat_valor in sorted(categorias_despesa.items(), key=lambda x: -x[1]):
        meta = mapa_metas.get(cat_nome.lower(), 0.0)
        pct_receita = (cat_valor / base_calculo * 100) if base_calculo > 0 else 0.0
        if meta > 0:
            desvio = pct_receita - meta
            alerta = "ACIMA DA META" if desvio > 0 else "DENTRO DA META"
            linhas_metas.append(
                f"| {cat_nome:30s} | Gasto R${cat_valor:>10.2f} | {pct_receita:>5.1f}% da Receita | Meta: {meta:.1f}% | Desvio: {desvio:+.1f}pp | {alerta:20s} |"
            )
        else:
            linhas_metas.append(
                f"| {cat_nome:30s} | Gasto R${cat_valor:>10.2f} | {pct_receita:>5.1f}% da Receita | Meta: --- | --- | --- |"
            )

    texto_metas = ""
    if linhas_metas:
        texto_metas = (
            "\nAnalise de Metas por Categoria de Despesa (% sobre a Remuneracao):\n"
            "| Categoria                       | Valor Gasto       | % Remuneracao | Meta   | Desvio   | Status                |\n"
            "|---------------------------------|-------------------|-------------|--------|----------|-----------------------|\n"
            + "\n".join(linhas_metas)
            + "\n"
        )

    top_receitas = sorted(
        [(k.split(":")[1], v) for k, v in categorias_todas.items() if k.startswith("receita:")],
        key=lambda x: -x[1]
    )[:3]
    top_despesas = sorted(categorias_despesa.items(), key=lambda x: -x[1])[:5]

    texto_receitas = ", ".join([f"{cat}=R${v:.2f}" for cat, v in top_receitas]) if top_receitas else "Nenhuma"
    texto_despesas = ", ".join([f"{cat}=R${v:.2f}" for cat, v in top_despesas]) if top_despesas else "Nenhuma"

    saldo_anual = total_receitas - total_despesas - total_investimentos - total_reservas
    base_calculo = total_remuneracao if total_remuneracao > 0 else total_receitas
    taxa_poupanca = ((base_calculo - total_despesas) / base_calculo * 100) if base_calculo > 0 else 0.0
    taxa_investimento = (total_investimentos / base_calculo * 100) if base_calculo > 0 else 0.0

    prompt = (
        "Voce e um planejador financeiro pessoal altamente capacitado. "
        "Analise os dados financeiros do usuario e gere insights profundos, praticos e acionaveis.\n\n"
        f"DADOS DO ANO {ano}:\n\n"
        "Totais Acumulados do Ano:\n"
        "| Indicador               | Valor           |\n"
        "|-------------------------|-----------------|\n"
        f"| Receita Total           | R${total_receitas:>10.2f} |\n"
        f"| Remuneracao Total       | R${total_remuneracao:>10.2f} |\n"
        f"| Despesa Total           | R${total_despesas:>10.2f} |\n"
        f"| Investimento Total      | R${total_investimentos:>10.2f} |\n"
        f"| Reserva Total           | R${total_reservas:>10.2f} |\n"
        f"| Saldo Liquido Anual     | R${saldo_anual:>10.2f} |\n"
        f"| Taxa de Poupanca (sobre Remuneracao) | {taxa_poupanca:>9.2f}% |\n"
        f"| Taxa de Investimento (sobre Remuneracao) | {taxa_investimento:>9.2f}% |\n\n"
        f"Resumo por Mes (Efetivado/Previsto):\n"
        "| Indicador   | Mes      | Receita         | Despesa         | Investimento     | Reserva          | Saldo            |\n"
        "|-------------|----------|-----------------|-----------------|------------------|------------------|------------------|\n"
        + "\n".join(resumo_meses)
        + f"\n\n"
        f"Top 3 Fontes de Receita:\n{texto_receitas}\n\n"
        f"Top 5 Categorias de Despesa:\n{texto_despesas}\n\n"
        + texto_metas
        + "\n"
        "TABELA DETALHADA DE LANCAMENTOS:\n"
        "Abaixo estao todos os lancamentos considerados na analise (ja filtrados pelas regras temporais: "
        "meses passados mostram apenas efetivados, meses futuros mostram apenas previstos, mes atual mostra ambos).\n\n"
        "| Mes     | Item                                      | Categoria                     | Tipo            | Valor         | Status       |\n"
        "|---------|-------------------------------------------|-------------------------------|-----------------|---------------|--------------|\n"
        + "\n".join(linhas_tabela)
        + "\n\n"
        "DIRETRIZES DA ANALISE:\n"
        "Com base EXCLUSIVAMENTE nos dados reais fornecidos acima, produza uma analise estruturada:\n\n"
        "1. Diagnostico da Saude Financeira: Analise o balanco receitas vs despesas vs investimentos. "
        "O usuario esta gastando mais do que ganha? A taxa de poupanca esta saudavel? "
        "Use valores CONCRETOS dos dados fornecidos (nao invente valores).\n\n"
        "2. Tendencias e Riscos: Identifique tendencias reais nos dados. "
        "Ha crescimento de despesas? Alguma categoria consome percentual excessivo? "
        "Destaque valores EXATOS das categorias problematicas.\n\n"
        "3. Analise de Metas: Compare os gastos reais com as metas configuradas. "
        "Aponte quais categorias estao dentro ou fora da meta, usando os percentuais fornecidos.\n\n"
        "4. Recomendacoes Praticas: 3-4 acoes concretas baseadas nos dados. "
        "Sugira cortes em categorias especificas com valores faceis, "
        "proponha metas de investimento, ou estrategias para equilibrar o orcamento.\n\n"
        "IMPORTANTE:\n"
        "- As porcentagens de gastos e metas sao calculadas SOBRE a Remuneracao (categoria de receita), nao sobre a Receita Total\n"
        "- Exemplo: se a Remuneracao foi R$ 10.000 e a despesa com Alimentacao foi R$ 2.000, entao o gasto representa 20% da Remuneracao\n"
        "- Baseie-se APENAS nos numeros fornecidos acima\n"
        "- NAO invente valores, meses ou categorias que nao estao na tabela\n"
        "- NAO use negrito, italico, hashtags ou qualquer formato de marcacao\n"
        "- NAO use codigo markdown ou HTML\n"
        "- Use apenas texto simples, paragrafos e quebras de linha naturais\n"
        "- Use hifen simples (-) para listar itens\n"
        "- A analise deve refletir EXATAMENTE o que os dados mostram\n"
        "- Responda EM PORTUGUES DO BRASIL\n"
        "- Sua resposta deve ser APENAS o texto da analise, sem nenhuma formatacao especial"
    )
    return prompt


def _build_investment_prompt(db: Session, user: User) -> str:
    """Monta o prompt de analise de investimentos com os dados do usuario."""
    ativos = (
        db.query(InvestmentAsset)
        .filter(InvestmentAsset.owner_id == user.id)
        .all()
    )

    if not ativos:
        return "Nenhum ativo de investimento encontrado para gerar insights."

    detalhes_ativos = []
    total_mercado = 0.0
    total_custo = 0.0

    for a in ativos:
        qtd = a.quantity or 0
        preco_compra = a.purchase_price or 0.0
        custo_total = qtd * preco_compra
        total_custo += custo_total

        preco_atual = _fetch_quote(a.ticker)
        if preco_atual is None or preco_atual <= 0:
            preco_atual = preco_compra

        valor_mercado = qtd * preco_atual
        total_mercado += valor_mercado

        detalhes_ativos.append({
            "ticker": a.ticker,
            "company": a.company,
            "quantity": qtd,
            "purchase_price": preco_compra,
            "current_price": preco_atual,
            "market_value": valor_mercado,
            "target": a.target or 0.0,
            "sector": a.sector or "Nao informado",
            "group": a.group or "Nao informado"
        })

    linhas_ativos = []
    for d in detalhes_ativos:
        pct_atual = (d["market_value"] / total_mercado * 100) if total_mercado > 0 else 0.0
        desvio = pct_atual - d["target"]
        linhas_ativos.append(
            f"- Ativo: {d['ticker']} ({d['company']}) | Grupo: {d['group']} | Setor: {d['sector']}\n"
            f"  Qtd: {d['quantity']} cotas | PM: R${d['purchase_price']:.2f} | Preco Atual: R${d['current_price']:.2f}\n"
            f"  Vl. Atual: R${d['market_value']:.2f} | Part. Atual: {pct_atual:.2f}% | Meta: {d['target']:.2f}% | Desvio: {desvio:+.2f}%"
        )

    txs = (
        db.query(InvestmentTransaction)
        .filter(InvestmentTransaction.owner_id == user.id)
        .order_by(InvestmentTransaction.id.desc())
        .limit(10)
        .all()
    )
    tx_text = ""
    if txs:
        tx_text = "\nUltimas transacoes de compra realizadas:\n" + "\n".join(
            [f"- {tx.ticker}: {tx.quantity} cotas a R${tx.purchase_price:.2f}" for tx in txs]
        )

    yield_pct = ((total_mercado / total_custo - 1) * 100) if total_custo > 0 else 0.0

    prompt = (
        "Voce e um assistente especializado em investimentos de renda variavel focado em balanceamento de ativos (Asset Allocation) na B3.\n"
        "Analise a carteira de investimentos abaixo e forneca insights praticos e objetivos.\n\n"
        f"DADOS DA CARTEIRA:\n"
        f"- Valor Total de Mercado atual: R${total_mercado:.2f}\n"
        f"- Custo Total de Aquisicao: R${total_custo:.2f}\n"
        f"- Rendimento da Carteira: {yield_pct:+.2f}%\n\n"
        "Composicao dos Ativos (com metas de balanceamento e desvios):\n"
        + "\n".join(linhas_ativos)
        + tx_text
        + "\n\n"
        "DIRETRIZES IMPORTANTES PARA A ANALISE:\n"
        "1. Esta carteira e focada em BALANCEAMENTO DE ATIVOS DA B3 (acoes, FIIs, ETFs, etc.).\n"
        "2. NUNCA fale sobre renda fixa (como Selic, Tesouro Direto, CDB, LCI, LCA ou poupanca). O foco do usuario para essa carteira e estritamente renda variavel e rebalanceamento dela.\n"
        "3. Identifique quais ativos estao mais subalocados (com maior desvio negativo, ou seja, onde a Alocacao Atual esta abaixo da Meta) e sugira prioriza-los nos proximos aportes para ajudar a reequilibrar a carteira.\n"
        "4. A analise deve ser pratica, objetiva, livre de jargoes desnecessarios, organizada em topicos claros e em texto simples (sem markdown, sem negrito, sem asteriscos).\n\n"
        "ESTRUTURA DA RESPOSTA (em texto simples, sem formatacao):\n"
        "1. Analise de Alocacao: Resumo de como os ativos estao distribuidos em comparacao com as metas estabelecidas.\n"
        "2. Sugestao para os Proximos Aportes: Indique claramente quais ativos devem ser priorizados nos proximos aportes com base nos desvios negativos, justificando de forma simples.\n"
        "3. Riscos e Concentracao: Aponte se ha algum ativo muito sobrealocado (desvio positivo alto) ou concentracao excessiva em algum setor/grupo.\n"
        "4. Recomendacoes Praticas: Acoes de rebalanceamento inteligentes (priorizar aportes nos subalocados em vez de vender ativos, minimizando custos fiscais).\n\n"
        "IMPORTANTE:\n"
        "- NAO use negrito, italico, hashtags ou qualquer formato markdown\n"
        "- Use apenas texto simples com quebras de linha\n"
        "- Use hifen simples (-) para listar itens\n"
        "- Responda EM PORTUGUES DO BRASIL"
    )
    return prompt


# --- Cotacao para o prompt de investimentos (mesma logica do investments.py) ---

_quote_cache = {}
_cache_expiry = {}
CACHE_TTL = 3600


def _quote_candidates(symbol):
    clean = symbol.strip().upper()
    candidates = [clean]
    if not clean.endswith(".SA"):
        candidates.append(f"{clean}.SA")
    if clean.endswith("F.SA"):
        candidates.append(clean.replace("F.SA", ".SA"))
    elif clean.endswith("F"):
        candidates.append(f"{clean[:-1]}.SA")
    unique = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _fetch_quote(symbol: str) -> Optional[float]:
    symbol = symbol.upper()
    now = time.time()
    expiry = _cache_expiry.get(symbol)
    if expiry and now < expiry and symbol in _quote_cache:
        return _quote_cache[symbol]

    for candidate in _quote_candidates(symbol):
        try:
            import yfinance as yf
            ticker = yf.Ticker(candidate)
            price = None
            try:
                price = ticker.fast_info.get("last_price")
            except Exception:
                price = None

            if price is None or float(price) <= 0:
                history = ticker.history(period="1d")
                if history is not None and not history.empty:
                    price = history["Close"].iloc[-1]

            if price is not None and float(price) > 0:
                value = round(float(price), 2)
                _quote_cache[symbol] = value
                _cache_expiry[symbol] = now + CACHE_TTL
                return value
        except Exception:
            continue

    return None


# --- Endpoints ---


class InsightResponse(BaseModel):
    id: int
    content: str
    created_at: str


@router.get("/financial", response_model=InsightResponse)
def get_financial_insight(
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Retorna o ultimo insight financeiro gerado."""
    user = _get_user(db, username)
    query = db.query(FinancialInsight).filter(FinancialInsight.owner_id == user.id)
    if ano:
        query = query.filter(FinancialInsight.ano == ano)
    insight = (
        query.order_by(FinancialInsight.created_at.desc())
        .first()
    )
    if not insight:
        return InsightResponse(
            id=-1,
            content="Nenhum insight gerado ainda. Clique em 'Gerar Insights' para comecar.",
            created_at="",
        )
    return InsightResponse(
        id=insight.id,
        content=insight.content,
        created_at=insight.created_at.isoformat(),
    )


@router.post("/financial/generate", response_model=InsightResponse)
def generate_financial_insight(
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Gera um novo insight financeiro usando IA."""
    user = _get_user(db, username)
    prompt = _build_financial_prompt(db, user, ano=ano)
    content = _call_ai(prompt, user.ai_provider, user.api_key)

    insight = FinancialInsight(content=content, owner_id=user.id, ano=ano)
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return InsightResponse(
        id=insight.id,
        content=insight.content,
        created_at=insight.created_at.isoformat(),
    )


@router.get("/investment", response_model=InsightResponse)
def get_investment_insight(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Retorna o ultimo insight de investimentos gerado."""
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
            content="Nenhum insight gerado ainda. Clique em 'Gerar Insights' para comecar.",
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
