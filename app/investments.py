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
from app.models import InvestmentAsset, User
from app.transactions import get_user_by_username

router = APIRouter(prefix="/api/investments", tags=["Investimentos"])

_quote_cache = {}
_cache_expiry = {}
CACHE_TTL = QUOTE_CACHE_TTL


class InvestmentPurchase(BaseModel):
    ticker: str
    quantity: int


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
        if not ticker or quantity <= 0:
            continue

        asset = db.query(InvestmentAsset).filter(
            InvestmentAsset.owner_id == user.id,
            InvestmentAsset.ticker == ticker,
        ).first()
        if asset:
            asset.quantity = int(asset.quantity or 0) + quantity
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


def _investment_payload(items):
    enriched = []
    for item in items:
        price = _fetch_quote(item.ticker) or 0.0
        total = round((item.quantity or 0) * price, 2)
        enriched.append({
            "id": item.id,
            "company": item.company,
            "ticker": item.ticker,
            "quantity": item.quantity,
            "target": item.target or 0.0,
            "sector": item.sector or "",
            "group": item.group or "",
            "price": price,
            "total": total,
        })

    portfolio_total = sum(item["total"] for item in enriched)
    for item in enriched:
        current_percent = (item["total"] / portfolio_total * 100) if portfolio_total else 0.0
        item["current_percent"] = round(current_percent, 2)
        item["deviation"] = round(current_percent - item["target"], 2)

    enriched.sort(key=lambda item: item["deviation"])
    target_sum = round(sum(item["target"] for item in enriched), 2)
    return {
        "assets": enriched,
        "metrics": {
            "portfolio_total": round(portfolio_total, 2),
            "asset_count": len(enriched),
            "target_sum": target_sum,
            "negative_deviation_count": len([item for item in enriched if item["deviation"] < 0]),
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
    return _investment_payload(items)


@router.post("/contribution")
def apply_investment_contribution(
    req: InvestmentContributionRequest,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    purchases = [
        {"ticker": item.ticker.strip(), "quantity": item.quantity}
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
    fieldnames = ["Empresa", "Ativo", "Quantidade", "Meta", "Ramo", "Grupo"]
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for item in items:
        writer.writerow({
            "Empresa": item.company,
            "Ativo": item.ticker,
            "Quantidade": item.quantity,
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
