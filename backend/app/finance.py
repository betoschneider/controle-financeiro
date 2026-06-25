import time
import yfinance as yf

# Simple TTL cache for quotes
class QuoteCache:
    def __init__(self, ttl=300):
        self.ttl = ttl
        self._store = {}

    def get(self, symbol):
        rec = self._store.get(symbol.upper())
        if not rec:
            return None
        ts, val = rec
        if time.time() - ts > self.ttl:
            del self._store[symbol.upper()]
            return None
        return val

    def set(self, symbol, value):
        self._store[symbol.upper()] = (time.time(), value)


_quote_cache = QuoteCache(ttl=3600)

def get_quote(symbol):
    symbol = symbol.upper()
    cached = _quote_cache.get(symbol)
    if cached is not None:
        return cached

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
                _quote_cache.set(symbol, value)
                return value
        except Exception:
            continue

    return None


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
