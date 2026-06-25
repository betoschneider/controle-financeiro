const yahooFinance = require('yahoo-finance2').default;

const cache = new Map();
const TTL_MS = 5 * 60 * 1000;

async function quote(symbol) {
  const key = String(symbol || '').toUpperCase();
  const now = Date.now();
  const cached = cache.get(key);

  if (cached && now - cached.timestamp < TTL_MS) {
    return cached.quote;
  }

  const result = await yahooFinance.quote(key).catch(() => null);
  const quoteData = {
    symbol: key,
    price: Number(result?.regularMarketPrice || result?.postMarketPrice || 0),
    currency: result?.currency || 'BRL',
    shortName: result?.shortName || key,
  };

  cache.set(key, { quote: quoteData, timestamp: now });
  return quoteData;
}

module.exports = { quote };
