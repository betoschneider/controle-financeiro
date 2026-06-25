const express = require('express');
const router = express.Router();
const investRepo = require('../models/CarteiraInvestimento');
const { quote } = require('../utils/yahooFinanceCache');

function calculateAsset(asset, currentPrice) {
  const valorTotal = Number(currentPrice) * Number(asset.quantidade);
  const valorMeta = Number(asset.meta) * Number(asset.quantidade);
  return {
    ...asset,
    preco_unitario: Number(currentPrice),
    valor_total: Number(valorTotal.toFixed(2)),
    valor_meta: Number(valorMeta.toFixed(2)),
    diferenca_meta: Number((valorTotal - valorMeta).toFixed(2)),
  };
}

router.get('/', async (req, res) => {
  try {
    const portfolio = investRepo.all();
    const assets = await Promise.all(
      portfolio.map(async (asset) => {
        const quoteInfo = await quote(asset.ativo);
        return calculateAsset(asset, quoteInfo.price);
      })
    );

    assets.sort((a, b) => a.diferenca_meta - b.diferenca_meta);
    res.json({ assets });
  } catch (error) {
    res.status(500).json({ error: 'Falha ao carregar a carteira de investimento.' });
  }
});

router.post('/import-csv', async (req, res) => {
  const { csv } = req.body;
  if (!csv) {
    return res.status(400).json({ error: 'Conteúdo CSV não fornecido.' });
  }

  try {
    investRepo.importCsv(csv);
    res.json({ success: true });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

router.get('/export-csv', (req, res) => {
  const csv = investRepo.exportCsv();
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename=carteira-investimento.csv');
  res.send(csv);
});

router.post('/confirm-investment', async (req, res) => {
  const { updates } = req.body;
  if (!Array.isArray(updates) || updates.length === 0) {
    return res.status(400).json({ error: 'Atualizações inválidas.' });
  }

  try {
    investRepo.updateQuantities(
      updates.map((item) => ({
        ativo: item.ativo,
        quantidade: Number(item.quantidade),
      }))
    );
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Erro ao confirmar investimento.' });
  }
});

router.get('/auditoria', (req, res) => {
  try {
    const events = investRepo.allAudit();
    res.json({ events });
  } catch (error) {
    res.status(500).json({ error: 'Falha ao carregar auditoria.' });
  }
});

module.exports = router;
