import csv
import time
from datetime import datetime
from io import StringIO
from typing import List, Optional

import yfinance as yf
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verificar_autenticacao
from app.config import QUOTE_CACHE_TTL, get_db
from app.models import InvestmentAsset, InvestmentTransaction
from app.transactions import get_user_by_username

router = APIRouter(prefix="/api/investments", tags=["Investimentos"])

_quote_cache = {}
_cache_expiry = {}
CACHE_TTL = QUOTE_CACHE_TTL


class InvestmentPurchase(BaseModel):
    ticker: str
    quantity: int
    purchase_price: float = 0.0


class InvestmentContributionRequest(BaseModel):
    purchases: List[InvestmentPurchase]


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


def _ensure_purchase_price(db: Session, asset: InvestmentAsset) -> None:
    """Se o ativo não tiver preço de compra, busca a cotação atual e grava."""
    if asset.purchase_price is not None:
        return
    price = _fetch_quote(asset.ticker)
    if price is not None and price > 0:
        asset.purchase_price = price
        db.commit()


def list_investments(db: Session, username: Optional[str]) -> List[InvestmentAsset]:
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []
    return db.query(InvestmentAsset).filter(InvestmentAsset.owner_id == user.id).all()


def delete_all_investments(db: Session, username: Optional[str]) -> int:
    if not username:
        return 0
    user = get_user_by_username(db, username)
    if not user:
        return 0
    # Também limpa transações do usuário
    db.query(InvestmentTransaction).filter(InvestmentTransaction.owner_id == user.id).delete()
    cnt = db.query(InvestmentAsset).filter(InvestmentAsset.owner_id == user.id).delete()
    db.commit()
    return cnt


def bulk_create_investments(db: Session, assets: List[dict], username: Optional[str]) -> List[InvestmentAsset]:
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []
    created = []
    for asset in assets:
        ia = InvestmentAsset(
            company=(asset.get("company") or "").strip(),
            ticker=(asset.get("ticker") or "").strip(),
            quantity=int(asset.get("quantity") or 0),
            purchase_price=float(asset["purchase_price"]) if asset.get("purchase_price") not in (None, "") else None,
            target=float(asset.get("target")) if asset.get("target") not in (None, "") else None,
            sector=(asset.get("sector") or "").strip(),
            group=(asset.get("group") or "").strip(),
            owner_id=user.id,
        )
        db.add(ia)
        created.append(ia)
    db.commit()
    return created


def update_investment_quantities(db: Session, username: Optional[str], purchases: List[dict]) -> List[InvestmentAsset]:
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []

    updated = []
    for purchase in purchases:
        ticker = (purchase.get("ticker") or "").strip()
        quantity = int(purchase.get("quantity") or 0)
        purchase_price = float(purchase.get("purchase_price") or 0)
        if not ticker or quantity <= 0:
            continue

        asset = db.query(InvestmentAsset).filter(
            InvestmentAsset.owner_id == user.id,
            InvestmentAsset.ticker == ticker,
        ).first()
        if asset:
            old_qty = int(asset.quantity or 0)
            old_price = asset.purchase_price
            asset.quantity = old_qty + quantity

            # Atualiza preço médio ponderado
            if purchase_price > 0:
                if old_price is not None and old_price > 0 and old_qty > 0:
                    asset.purchase_price = round(
                        (old_qty * old_price + quantity * purchase_price) / (old_qty + quantity), 2
                    )
                else:
                    asset.purchase_price = purchase_price

            # Grava transação de compra
            if purchase_price > 0:
                tx = InvestmentTransaction(
                    ticker=ticker,
                    quantity=quantity,
                    purchase_price=purchase_price,
                    owner_id=user.id,
                )
                db.add(tx)

            updated.append(asset)

    db.commit()
    for asset in updated:
        db.refresh(asset)
    return updated


def _parse_float(value, default=0.0):
    if value in (None, ""):
        return default
    try:
        return float(str(value).strip().replace("%", "").replace(",", "."))
    except ValueError:
        return default


def _parse_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(float(str(value).strip().replace(",", ".")))
    except ValueError:
        return default


def _investment_payload(items, db=None):
    enriched = []
    total_cost = 0.0
    for item in items:
        price = _fetch_quote(item.ticker) or 0.0
        total = round((item.quantity or 0) * price, 2)

        # Garante que o ativo tenha preço de compra (se não tiver, usa a cotação atual)
        purchase_price = item.purchase_price
        if purchase_price is None and price > 0:
            purchase_price = price
            # Persiste no banco se tivermos uma sessão
            if db is not None:
                item.purchase_price = price
                db.commit()

        cost = round((item.quantity or 0) * (purchase_price or 0), 2)
        total_cost += cost

        enriched.append({
            "id": item.id,
            "company": item.company,
            "ticker": item.ticker,
            "quantity": item.quantity,
            "purchase_price": purchase_price,
            "target": item.target or 0.0,
            "sector": item.sector or "",
            "group": item.group or "",
            "price": price,
            "total": total,
            "cost": cost,
        })

    portfolio_total = sum(item["total"] for item in enriched)
    for item in enriched:
        current_percent = (item["total"] / portfolio_total * 100) if portfolio_total else 0.0
        item["current_percent"] = round(current_percent, 2)
        item["deviation"] = round(current_percent - item["target"], 2)

    enriched.sort(key=lambda item: item["deviation"])
    target_sum = round(sum(item["target"] for item in enriched), 2)

    # Rendimento total da carteira
    portfolio_yield = None
    if total_cost > 0 and portfolio_total > 0:
        portfolio_yield = round((portfolio_total / total_cost - 1) * 100, 2)

    return {
        "assets": enriched,
        "metrics": {
            "portfolio_total": round(portfolio_total, 2),
            "asset_count": len(enriched),
            "target_sum": target_sum,
            "negative_deviation_count": len([item for item in enriched if item["deviation"] < 0]),
            "total_cost": round(total_cost, 2),
            "portfolio_yield": portfolio_yield,
        },
        "last_updated": datetime.now().isoformat(),
    }


@router.get("")
def get_investments(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    items = list_investments(db, username)
    return [
        {
            "id": i.id,
            "company": i.company,
            "ticker": i.ticker,
            "quantity": i.quantity,
            "purchase_price": i.purchase_price,
            "target": i.target,
            "sector": i.sector,
            "group": i.group,
        }
        for i in items
    ]


@router.get("/portfolio")
def get_investment_portfolio(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    items = list_investments(db, username)

    # Antes de montar o payload, garante que todo ativo sem preço de compra receba a cotação atual
    for item in items:
        if item.purchase_price is None:
            _ensure_purchase_price(db, item)

    return _investment_payload(items, db)


@router.get("/yield-details")
def get_investment_yield_details(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Retorna detalhes de rendimento por ativo para exibição na tabela de Gerenciar Carteira."""
    items = list_investments(db, username)
    result = []
    for item in items:
        price = _fetch_quote(item.ticker) or 0.0

        # Garante preço de compra
        purchase_price = item.purchase_price
        if purchase_price is None and price > 0:
            purchase_price = price
            item.purchase_price = price
            db.commit()

        avg_price = purchase_price or 0
        cost = round((item.quantity or 0) * avg_price, 2)
        current_value = round((item.quantity or 0) * price, 2)
        yield_pct = None
        if cost > 0:
            yield_pct = round((current_value / cost - 1) * 100, 2)

        result.append({
            "ticker": item.ticker,
            "company": item.company,
            "quantity": item.quantity,
            "avg_purchase_price": avg_price,
            "current_price": price,
            "cost": cost,
            "current_value": current_value,
            "yield_percent": yield_pct,
        })

    return result


@router.post("/contribution")
def apply_investment_contribution(
    req: InvestmentContributionRequest,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    purchases = [
        {
            "ticker": item.ticker.strip(),
            "quantity": item.quantity,
            "purchase_price": item.purchase_price,
        }
        for item in req.purchases
        if item.ticker.strip() and item.quantity > 0
    ]
    if not purchases:
        raise HTTPException(status_code=400, detail="Nenhuma compra válida foi informada.")

    updated = update_investment_quantities(db, username, purchases)
    return {"success": True, "updated": len(updated), "message": "Aporte confirmado com sucesso."}


@router.post("/upload")
def upload_investments(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(StringIO(content))
    required = {"Empresa", "Ativo", "Quantidade", "Meta", "Ramo", "Grupo"}
    headers = set(reader.fieldnames or [])
    if not required.issubset(headers) and not {"company", "ticker", "quantity", "target", "sector", "group"}.issubset(headers):
        raise HTTPException(
            status_code=400,
            detail="Cabeçalhos inválidos. Use Empresa,Ativo,Quantidade,Meta,Ramo,Grupo.",
        )

    assets = []
    for row in reader:
        ticker = (row.get("Ativo") or row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        assets.append({
            "company": row.get("Empresa") or row.get("company") or "",
            "ticker": ticker,
            "quantity": _parse_int(row.get("Quantidade") or row.get("quantity")),
            "purchase_price": _parse_float(row.get("PrecoCompra") or row.get("purchase_price")),
            "target": _parse_float(row.get("Meta") or row.get("target")),
            "sector": row.get("Ramo") or row.get("sector") or "",
            "group": row.get("Grupo") or row.get("group") or "",
        })

    delete_all_investments(db, username)
    created = bulk_create_investments(db, assets, username)
    return {"message": f"{len(created)} ativos importados."}


@router.get("/download")
def download_investments(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    items = list_investments(db, username)
    si = StringIO()
    fieldnames = ["Empresa", "Ativo", "Quantidade", "PrecoCompra", "Meta", "Ramo", "Grupo"]
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for item in items:
        writer.writerow({
            "Empresa": item.company,
            "Ativo": item.ticker,
            "Quantidade": item.quantity,
            "PrecoCompra": item.purchase_price if item.purchase_price is not None else "",
            "Meta": item.target if item.target is not None else "",
            "Ramo": item.sector or "",
            "Grupo": item.group or "",
        })
    output = si.getvalue()
    return StreamingResponse(
        StringIO(output),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=carteira.csv"},
    )
