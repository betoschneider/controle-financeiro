let investmentPortfolio = null;
let investmentDeviationChart = null;
let investmentSuggestions = [];

const GROUP_COLORS = [
    "#2ecc71",
    "#3498db",
    "#f1c40f",
    "#e74c3c",
    "#00d2d3",
    "#ff7f50",
    "#9b59b6",
    "#95a5a6"
];

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("tab-carteira")) return;

    const uploadInput = document.getElementById("btn-inv-upload");
    const uploadTrigger = document.getElementById("btn-inv-upload-trigger");
    const refreshButton = document.getElementById("btn-inv-refresh");
    const downloadButton = document.getElementById("btn-inv-download");
    const contributionValue = document.getElementById("inv-contribution-value");
    const contributionAssets = document.getElementById("inv-contribution-assets");
    const confirmCheck = document.getElementById("inv-confirm-check");
    const confirmButton = document.getElementById("btn-inv-confirm");

    if (uploadTrigger && uploadInput) uploadTrigger.addEventListener("click", () => uploadInput.click());
    if (uploadInput) {
        uploadInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) uploadInvestments(e.target.files[0]);
        });
    }
    if (refreshButton) refreshButton.addEventListener("click", carregarInvestments);
    if (downloadButton) downloadButton.addEventListener("click", downloadInvestments);
    if (contributionValue) contributionValue.addEventListener("input", renderInvestmentSuggestions);
    if (contributionAssets) contributionAssets.addEventListener("input", renderInvestmentSuggestions);
    if (confirmCheck && confirmButton) {
        confirmCheck.addEventListener("change", () => {
            confirmButton.disabled = !confirmCheck.checked || investmentSuggestions.length === 0;
        });
    }
    if (confirmButton) confirmButton.addEventListener("click", confirmInvestmentContribution);

    window.onInvestmentTabActivated = () => {
        if (!investmentPortfolio) carregarInvestments();
        carregarAuditLogs();
    };
});

async function carregarInvestments() {
    const token = obterCookie("session_token");
    if (!token) return;

    exibirLoading(true);
    try {
        const resp = await fetch("/api/investments/portfolio", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (resp.status === 401) {
            realizarLogout();
            return;
        }
        if (!resp.ok) throw new Error("Falha ao carregar carteira");

        investmentPortfolio = await resp.json();
        renderInvestmentPortfolio();
        renderInvestmentSuggestions();
        await carregarAuditLogs();
    } catch (e) {
        console.error(e);
        alert("Não foi possível carregar a carteira de investimento.");
    } finally {
        exibirLoading(false);
    }
}

function renderInvestmentPortfolio() {
    const assets = investmentPortfolio?.assets || [];
    const metrics = investmentPortfolio?.metrics || {};
    setText("inv-total", formatarMoeda(metrics.portfolio_total || 0));
    setText("inv-assets-count", String(metrics.asset_count || 0));
    setText("inv-target-sum", `${formatNumber(metrics.target_sum || 0, 2)}%`);

    const updatedAt = investmentPortfolio?.last_updated ? new Date(investmentPortfolio.last_updated) : null;
    setText("inv-last-updated", updatedAt ? `Última consulta: ${updatedAt.toLocaleString("pt-BR")}` : "Cotações ainda não carregadas.");

    const tbody = document.getElementById("inv-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!assets.length) {
        renderEmptyRow(tbody, 10, "Importe um CSV para iniciar a carteira.");
        renderDeviationChart([]);
        return;
    }

    assets.forEach(asset => {
        const tr = document.createElement("tr");
        tr.style.setProperty("--group-color", colorForGroup(asset.group));
        appendCell(tr, asset.ticker, "", true);
        tr.lastChild.innerHTML = "";
        const ticker = document.createElement("span");
        ticker.className = "ticker-pill";
        ticker.textContent = asset.ticker;
        tr.lastChild.appendChild(ticker);
        appendCell(tr, asset.company);
        appendCell(tr, asset.quantity, "numeric");
        appendCell(tr, formatarMoeda(asset.price || 0), "numeric");
        appendCell(tr, formatarMoeda(asset.total || 0), "numeric");
        appendCell(tr, `${formatNumber(asset.target || 0, 2)}%`, "numeric");
        appendCell(tr, `${formatNumber(asset.current_percent || 0, 2)}%`, "numeric");
        appendCell(tr, `${formatNumber(asset.deviation || 0, 2)}%`, `numeric ${asset.deviation < 0 ? "deviation-negative" : "deviation-positive"}`);
        appendCell(tr, asset.sector || "-");
        appendCell(tr, asset.group || "-");
        tbody.appendChild(tr);
    });

    renderDeviationChart(assets);
}

function renderDeviationChart(assets) {
    const canvas = document.getElementById("inv-deviation-chart");
    if (!canvas || typeof Chart === "undefined") return;

    const labels = assets.map(asset => asset.ticker);
    const values = assets.map(asset => asset.deviation || 0);
    const colors = assets.map(asset => colorForGroup(asset.group));
    const borderColors = assets.map(asset => asset.deviation < 0 ? "rgba(231, 76, 60, 0.9)" : "rgba(46, 204, 113, 0.9)");
    const textColor = getComputedStyle(document.body).getPropertyValue("--text-secondary").trim() || "#9090a2";
    const gridColor = getComputedStyle(document.body).getPropertyValue("--border-color").trim() || "rgba(255,255,255,.08)";

    const zeroLinePlugin = {
        id: "zeroLine",
        afterDatasetsDraw(chart) {
            const xScale = chart.scales.x;
            const yScale = chart.scales.y;
            if (!xScale || !yScale) return;
            const x = xScale.getPixelForValue(0);
            const ctx = chart.ctx;
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(x, yScale.top);
            ctx.lineTo(x, yScale.bottom);
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 4]);
            ctx.strokeStyle = "#ff4757";
            ctx.stroke();
            ctx.restore();
        }
    };

    if (investmentDeviationChart) investmentDeviationChart.destroy();
    investmentDeviationChart = new Chart(canvas, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Desvio",
                data: values,
                backgroundColor: colors,
                borderColor: borderColors,
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `Desvio: ${formatNumber(ctx.parsed.x, 2)}%`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, callback: (value) => `${value}%` }
                },
                y: {
                    grid: { color: "transparent" },
                    ticks: { color: textColor }
                }
            }
        },
        plugins: [zeroLinePlugin]
    });
}

function renderInvestmentSuggestions() {
    const assets = investmentPortfolio?.assets || [];
    const tbody = document.getElementById("inv-suggestion-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    investmentSuggestions = [];

    if (!assets.length) {
        renderEmptyRow(tbody, 5, "Sem ativos para sugerir aporte.");
        updateSuggestionTotals(0, getContributionValue());
        updateConfirmState();
        return;
    }

    const contributionValue = getContributionValue();
    const assetsCountInput = document.getElementById("inv-contribution-assets");
    const assetCount = Math.max(1, Math.min(parseInt(assetsCountInput?.value || "1", 10), assets.length));
    const candidates = assets.filter(asset => (asset.price || 0) > 0).slice(0, assetCount);
    const valuePerAsset = candidates.length ? contributionValue / candidates.length : 0;

    candidates.forEach(asset => {
        const quantity = Math.max(0, Math.floor(valuePerAsset / asset.price));
        investmentSuggestions.push({
            ticker: asset.ticker,
            price: asset.price,
            currentQuantity: asset.quantity,
            target: asset.target,
            quantity,
        });
    });

    investmentSuggestions.forEach((suggestion, index) => {
        const tr = document.createElement("tr");
        const asset = assets.find(item => item.ticker === suggestion.ticker);
        tr.style.setProperty("--group-color", colorForGroup(asset?.group || ""));
        appendCell(tr, suggestion.ticker);
        appendCell(tr, formatarMoeda(suggestion.price), "numeric");

        const quantityCell = document.createElement("td");
        quantityCell.className = "numeric";
        const input = document.createElement("input");
        input.type = "number";
        input.min = "0";
        input.step = "1";
        input.value = String(suggestion.quantity);
        input.addEventListener("input", () => {
            investmentSuggestions[index].quantity = Math.max(0, parseInt(input.value || "0", 10));
            refreshSuggestionRows();
        });
        quantityCell.appendChild(input);
        tr.appendChild(quantityCell);

        appendCell(tr, "", "numeric suggestion-subtotal");
        appendCell(tr, "", "numeric suggestion-new-deviation");
        tbody.appendChild(tr);
    });

    refreshSuggestionRows();
}

function refreshSuggestionRows() {
    const assets = investmentPortfolio?.assets || [];
    const rows = document.querySelectorAll("#inv-suggestion-tbody tr");
    const currentTotal = assets.reduce((sum, asset) => sum + (asset.total || 0), 0);
    const suggestedTotal = investmentSuggestions.reduce((sum, item) => sum + item.quantity * item.price, 0);
    const newPortfolioTotal = currentTotal + suggestedTotal;

    rows.forEach((row, index) => {
        const suggestion = investmentSuggestions[index];
        const asset = assets.find(item => item.ticker === suggestion.ticker);
        const subtotal = suggestion.quantity * suggestion.price;
        const newAssetTotal = ((asset?.quantity || 0) + suggestion.quantity) * suggestion.price;
        const newPercent = newPortfolioTotal > 0 ? (newAssetTotal / newPortfolioTotal) * 100 : 0;
        const newDeviation = newPercent - (asset?.target || 0);
        row.querySelector(".suggestion-subtotal").textContent = formatarMoeda(subtotal);
        const deviationCell = row.querySelector(".suggestion-new-deviation");
        deviationCell.textContent = `${formatNumber(newDeviation, 2)}%`;
        deviationCell.classList.toggle("deviation-negative", newDeviation < 0);
        deviationCell.classList.toggle("deviation-positive", newDeviation >= 0);
    });

    updateSuggestionTotals(suggestedTotal, getContributionValue() - suggestedTotal);
    updateConfirmState();
}

async function confirmInvestmentContribution() {
    const purchases = investmentSuggestions
        .filter(item => item.quantity > 0)
        .map(item => ({ ticker: item.ticker, quantity: item.quantity }));

    if (!purchases.length) {
        alert("Informe ao menos uma cota para confirmar o aporte.");
        return;
    }

    const token = obterCookie("session_token");
    exibirLoading(true);
    try {
        const resp = await fetch("/api/investments/contribution", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ purchases })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || "Falha ao confirmar aporte.");
        alert(data.message || "Aporte confirmado.");
        document.getElementById("inv-confirm-check").checked = false;
        await carregarInvestments();
    } catch (e) {
        console.error(e);
        alert(e.message || "Não foi possível confirmar o aporte.");
    } finally {
        exibirLoading(false);
    }
}

async function uploadInvestments(file) {
    if (!confirm("A importação removerá os dados atuais da carteira de investimento e substituirá pelo CSV selecionado. Deseja continuar?")) {
        document.getElementById("btn-inv-upload").value = "";
        return;
    }

    const token = obterCookie("session_token");
    const fd = new FormData();
    fd.append("file", file);
    exibirLoading(true);
    try {
        const resp = await fetch("/api/investments/upload", {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` },
            body: fd
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || "Falha na importação.");
        alert(data.message || "Carteira importada.");
        await carregarInvestments();
    } catch (e) {
        console.error(e);
        alert(e.message || "Não foi possível importar a carteira.");
    } finally {
        document.getElementById("btn-inv-upload").value = "";
        exibirLoading(false);
    }
}

async function downloadInvestments() {
    const token = obterCookie("session_token");
    if (!token) return;
    exibirLoading(true);
    try {
        const response = await fetch("/api/investments/download", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!response.ok) throw new Error("Falha na exportação.");
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "carteira.csv";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (e) {
        console.error(e);
        alert("Não foi possível exportar a carteira.");
    } finally {
        exibirLoading(false);
    }
}

async function carregarAuditLogs() {
    const token = obterCookie("session_token");
    const tbody = document.getElementById("audit-tbody");
    if (!token || !tbody) return;

    try {
        const resp = await fetch("/api/audit-logs", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error("Falha ao carregar auditoria.");
        const logs = await resp.json();
        tbody.innerHTML = "";
        if (!logs.length) {
            renderEmptyRow(tbody, 3, "Nenhum evento registrado.");
            return;
        }
        logs.forEach(log => {
            const tr = document.createElement("tr");
            appendCell(tr, new Date(log.timestamp).toLocaleString("pt-BR"));
            appendCell(tr, log.action);
            appendCell(tr, log.detail || "-");
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
    }
}

function updateSuggestionTotals(total, leftover) {
    setText("inv-suggested-total", formatarMoeda(total));
    setText("inv-suggested-leftover", formatarMoeda(leftover));
}

function updateConfirmState() {
    const confirmCheck = document.getElementById("inv-confirm-check");
    const confirmButton = document.getElementById("btn-inv-confirm");
    if (!confirmCheck || !confirmButton) return;
    const hasPurchases = investmentSuggestions.some(item => item.quantity > 0);
    confirmButton.disabled = !confirmCheck.checked || !hasPurchases;
}

function getContributionValue() {
    return Math.max(0, parseFloat(document.getElementById("inv-contribution-value")?.value || "0"));
}

function appendCell(row, value, className = "") {
    const td = document.createElement("td");
    if (className) td.className = className;
    td.textContent = value;
    row.appendChild(td);
}

function renderEmptyRow(tbody, colSpan, message) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = colSpan;
    td.textContent = message;
    td.style.textAlign = "center";
    td.style.color = "var(--text-secondary)";
    tr.appendChild(td);
    tbody.appendChild(tr);
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatNumber(value, digits = 2) {
    return new Intl.NumberFormat("pt-BR", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
    }).format(value || 0);
}

function colorForGroup(group) {
    const text = String(group || "Sem grupo");
    let hash = 0;
    for (let i = 0; i < text.length; i += 1) {
        hash = ((hash << 5) - hash) + text.charCodeAt(i);
        hash |= 0;
    }
    return GROUP_COLORS[Math.abs(hash) % GROUP_COLORS.length];
}
