const portfolioTableBody = document.querySelector('#portfolio-table tbody');
const distributionTableBody = document.querySelector('#distribution-table tbody');
const auditLog = document.querySelector('#audit-log');
const refreshButton = document.querySelector('#refresh-button');
const exportButton = document.querySelector('#export-csv-button');
const confirmButton = document.querySelector('#confirm-investment-button');
const confirmCheckbox = document.querySelector('#confirm-checkbox');
const fileInput = document.querySelector('#csv-file');
const investValueInput = document.querySelector('#invest-value');
const assetCountInput = document.querySelector('#asset-count');
const chartCanvas = document.querySelector('#meta-chart');
const totalAssets = document.querySelector('#total-assets');
const totalInvestment = document.querySelector('#total-investment');
const totalDeficit = document.querySelector('#total-deficit');
const negativeAssets = document.querySelector('#negative-assets');

const groupColors = {
  'Gigante Cíclica': '#fde2e4',
  'Trio de Ferro': '#e2f0cb',
  'Utilidade Pública - Energia e Saneamento': '#dbe7f3',
  'Financeiro / Seguros e Bolsa': '#f4ecd8',
};

let portfolioAssets = [];
let chartInstance = null;

function groupClassName(group) {
  return `group-${group.replace(/\W+/g, '-').toLowerCase()}`;
}

function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
}

function setRowBackground(row, group) {
  const color = groupColors[group] || '#f8f8f8';
  row.style.background = color;
}

function renderPortfolioTable() {
  portfolioTableBody.innerHTML = '';
  portfolioAssets.forEach((asset) => {
    const row = document.createElement('tr');
    row.className = groupClassName(asset.grupo || '');
    setRowBackground(row, asset.grupo);

    row.innerHTML = `
      <td>${asset.empresa}</td>
      <td>${asset.ativo}</td>
      <td>${asset.quantidade}</td>
      <td>${formatCurrency(asset.preco_unitario)}</td>
      <td>${formatCurrency(asset.valor_total)}</td>
      <td>${formatCurrency(asset.valor_meta)}</td>
      <td>${formatCurrency(asset.diferenca_meta)}</td>
      <td>${asset.ramo || '-'}</td>
      <td>${asset.grupo || '-'}</td>
    `;
    portfolioTableBody.appendChild(row);
  });
}

function renderMetrics() {
  const loadedAssets = portfolioAssets.length;
  const totalValue = portfolioAssets.reduce((sum, asset) => sum + asset.valor_total, 0);
  const totalGap = portfolioAssets
    .filter((asset) => asset.diferenca_meta < 0)
    .reduce((sum, asset) => sum + Math.abs(asset.diferenca_meta), 0);
  const belowMeta = portfolioAssets.filter((asset) => asset.diferenca_meta < 0).length;

  totalAssets.textContent = loadedAssets;
  totalInvestment.textContent = formatCurrency(totalValue);
  totalDeficit.textContent = formatCurrency(totalGap);
  negativeAssets.textContent = belowMeta;
}

function renderDistribution() {
  const investValue = Number(investValueInput.value) || 0;
  const assetCount = Math.max(1, Number(assetCountInput.value) || 1);
  const negativeAssetsList = portfolioAssets
    .filter((asset) => asset.diferenca_meta < 0)
    .sort((a, b) => a.diferenca_meta - b.diferenca_meta)
    .slice(0, assetCount);

  const totalDeficitValue =
    negativeAssetsList.reduce((sum, asset) => sum + Math.abs(asset.diferenca_meta), 0) || 1;

  distributionTableBody.innerHTML = '';
  if (negativeAssetsList.length === 0) {
    const row = document.createElement('tr');
    row.innerHTML = `<td colspan="5">Nenhum ativo com desvio negativo da meta encontrado.</td>`;
    distributionTableBody.appendChild(row);
    return [];
  }

  const updates = negativeAssetsList.map((asset) => {
    const allocation = investValue * (Math.abs(asset.diferenca_meta) / totalDeficitValue);
    const suggestedQuantity = Math.floor(allocation / asset.preco_unitario);
    const newQuantity = asset.quantidade + suggestedQuantity;
    const newValueTotal = newQuantity * asset.preco_unitario;
    const newDiff = newValueTotal - asset.meta * newQuantity;

    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${asset.ativo}</td>
      <td>${formatCurrency(asset.preco_unitario)}</td>
      <td>${suggestedQuantity}</td>
      <td>${formatCurrency(newValueTotal)}</td>
      <td>${formatCurrency(newDiff)}</td>
    `;
    distributionTableBody.appendChild(row);

    return {
      ativo: asset.ativo,
      quantidade: newQuantity,
    };
  });

  return updates;
}

function renderChart() {
  if (!chartCanvas) return;
  const labels = portfolioAssets.map((asset) => asset.ativo);
  const values = portfolioAssets.map((asset) => asset.diferenca_meta);
  const ctx = chartCanvas.getContext('2d');
  if (!ctx) return;

  const width = chartCanvas.width;
  const height = chartCanvas.height;
  ctx.clearRect(0, 0, width, height);

  const maxValue = Math.max(...values.map(Math.abs), 1);
  const barHeight = 24;
  const gap = 14;
  const baseLine = Math.max(80, width * 0.2);
  const availableWidth = width - baseLine - 20;

  portfolioAssets.forEach((asset, index) => {
    const barWidth = (Math.abs(asset.diferenca_meta) / maxValue) * availableWidth;
    const y = index * (barHeight + gap) + 30;
    const x = asset.diferenca_meta < 0 ? baseLine - barWidth : baseLine;

    ctx.fillStyle = asset.diferenca_meta < 0 ? '#f28b82' : '#81c995';
    ctx.fillRect(x, y, barWidth, barHeight);

    ctx.fillStyle = '#333';
    ctx.font = '12px Arial';
    ctx.fillText(asset.ativo, 10, y + 16);
    ctx.fillText(formatCurrency(asset.diferenca_meta), baseLine + (asset.diferenca_meta < 0 ? -barWidth - 10 : barWidth + 10), y + 16);
  });

  ctx.strokeStyle = '#444';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(baseLine, 20);
  ctx.lineTo(baseLine, height - 10);
  ctx.stroke();
}

async function loadAudit() {
  const response = await fetch('/api/carteira-investimento/auditoria');
  const data = await response.json();
  auditLog.innerHTML = '';
  data.events.forEach((event) => {
    const item = document.createElement('div');
    item.className = 'audit-item';
    item.textContent = `${event.criado_em} — ${event.evento}: ${event.detalhe}`;
    auditLog.appendChild(item);
  });
}

async function loadPortfolio() {
  const response = await fetch('/api/carteira-investimento');
  const data = await response.json();
  portfolioAssets = data.assets;
  renderPortfolioTable();
  renderMetrics();
  renderChart();
  renderDistribution();
  await loadAudit();
}

async function exportCsv() {
  const response = await fetch('/api/carteira-investimento/export-csv');
  const csv = await response.text();
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
  link.download = 'carteira-investimento.csv';
  link.click();
}

async function confirmInvestment() {
  if (!confirmCheckbox.checked) {
    alert('Marque a confirmação antes de aplicar o investimento.');
    return;
  }

  const updates = renderDistribution();
  if (updates.length === 0) {
    alert('Não há investimentos sugeridos para confirmar.');
    return;
  }

  await fetch('/api/carteira-investimento/confirm-investment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ updates }),
  });

  confirmCheckbox.checked = false;
  confirmButton.disabled = true;
  await loadPortfolio();
}

fileInput.addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const text = await file.text();
  await fetch('/api/carteira-investimento/import-csv', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ csv: text }),
  });
  await loadPortfolio();
});

refreshButton.addEventListener('click', loadPortfolio);
exportButton.addEventListener('click', exportCsv);
confirmButton.addEventListener('click', confirmInvestment);
confirmCheckbox.addEventListener('change', () => {
  confirmButton.disabled = !confirmCheckbox.checked;
});
investValueInput.addEventListener('input', renderDistribution);
assetCountInput.addEventListener('input', renderDistribution);

loadPortfolio();
