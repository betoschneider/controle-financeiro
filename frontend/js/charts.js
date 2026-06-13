// Estado Global dos Gráficos
let chartMensalInstancia = null;
let chartRoscaInstancia = null;
let chartBarrasHInstancia = null;

// Mapa de Cores RGB bases
const CORES_RGB = {
    "Receita": [46, 204, 113],
    "Despesa": [231, 76, 60],
    "Investimento": [52, 152, 219],
    "Reserva": [241, 196, 15]
};

const CORES_EXTRAS_RGB = [
    [155, 89, 182], // Roxo
    [26, 188, 156],  // Ciano
    [230, 126, 34],  // Laranja
    [52, 73, 94]     // Grafite
];

function obterCorTipoRGB(tipoStr, index = 0) {
    const busca = tipoStr.trim().charAt(0).toUpperCase() + tipoStr.trim().slice(1).toLowerCase();
    if (CORES_RGB[busca]) {
        return CORES_RGB[busca];
    }
    return CORES_EXTRAS_RGB[index % CORES_EXTRAS_RGB.length];
}

/**
 * Atualiza o Gráfico Mensal (Barras Empilhadas + Média Anual)
 * @param {Array} transacoes - Lista de transações brutas do ano
 * @param {number} anoSelecionado - Ano selecionado
 */
function atualizarGraficoMensal(transacoes, anoSelecionado) {
    const ctx = document.getElementById('chart-mensal').getContext('2d');
    const mesesAbreviados = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
    
    // Inicializa estrutura de agregação por mês (1 a 12)
    const dadosPorTipo = {
        "Receita": { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) },
        "Despesa": { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) },
        "Investimento": { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) },
        "Reserva": { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) }
    };

    const hoje = new Date();
    const mesAtualSistema = hoje.getMonth() + 1; // 1-12
    const anoAtualSistema = hoje.getFullYear();

    // Agrega os valores
    transacoes.forEach(t => {
        const tipo = t.tipo.trim().charAt(0).toUpperCase() + t.tipo.trim().slice(1).toLowerCase();
        if (!dadosPorTipo[tipo]) {
            dadosPorTipo[tipo] = { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) };
        }
        
        const idxMes = t.mes - 1; // 0-11
        if (idxMes < 0 || idxMes > 11) return;

        const valor = parseFloat(t.valor) || 0.0;
        const pago = boolValue(t.pago);

        const isMesPassado = (anoSelecionado < anoAtualSistema) || (anoSelecionado === anoAtualSistema && t.mes < mesAtualSistema);

        if (pago) {
            dadosPorTipo[tipo].efetivado[idxMes] += valor;
        } else {
            // Se o mês já passou e não foi pago, o valor efetivado é zero (ignorado)
            if (!isMesPassado) {
                dadosPorTipo[tipo].previsto[idxMes] += valor;
            }
        }
    });

    // Calcula as médias anuais
    const mediasAnuais = {};
    Object.keys(dadosPorTipo).forEach(tipo => {
        const totalEfetivado = dadosPorTipo[tipo].efetivado.reduce((a, b) => a + b, 0);
        const totalPrevisto = dadosPorTipo[tipo].previsto.reduce((a, b) => a + b, 0);
        mediasAnuais[tipo] = (totalEfetivado + totalPrevisto) / 12.0;
    });

    // Configuração dos Datasets
    const datasets = [];
    let colorIdx = 0;

    Object.keys(dadosPorTipo).forEach(tipo => {
        const rgb = obterCorTipoRGB(tipo, colorIdx++);
        const corEfetivado = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 1.0)`;
        const corPrevisto = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 0.35)`;

        // Dataset Efetivado
        datasets.push({
            type: 'bar',
            label: `${tipo} (Efetivado)`,
            data: dadosPorTipo[tipo].efetivado,
            backgroundColor: corEfetivado,
            borderColor: corEfetivado,
            borderWidth: 1,
            stack: tipo,
            barPercentage: 0.8,
            categoryPercentage: 0.8
        });

        // Dataset Previsto
        datasets.push({
            type: 'bar',
            label: `${tipo} (Previsto)`,
            data: dadosPorTipo[tipo].previsto,
            backgroundColor: corPrevisto,
            borderColor: corEfetivado,
            borderWidth: 1,
            borderDash: [2, 2],
            stack: tipo,
            barPercentage: 0.8,
            categoryPercentage: 0.8
        });

        // Dataset Linha da Média
        datasets.push({
            type: 'line',
            label: `Média Anual ${tipo}`,
            data: Array(12).fill(mediasAnuais[tipo]),
            borderColor: corEfetivado,
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            pointRadius: 0,
            pointHitRadius: 0,
            order: -1 // Garante que a linha fique por cima
        });
    });

    // Destrói gráfico anterior se houver
    if (chartMensalInstancia) {
        chartMensalInstancia.destroy();
    }

    chartMensalInstancia = new Chart(ctx, {
        data: {
            labels: mesesAbreviados,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#f1f1f5',
                        font: { family: 'Outfit', size: 12 },
                        filter: function(item) {
                            // Oculta previstos da legenda para não poluir
                            return !item.text.includes('(Previsto)');
                        }
                    }
                },
                tooltip: {
                    mode: 'x',
                    intersect: false,
                    titleFont: { family: 'Outfit', size: 14 },
                    bodyFont: { family: 'Outfit', size: 12 },
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9090a2', font: { family: 'Outfit' } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#9090a2',
                        font: { family: 'Outfit' },
                        callback: function(value) {
                            return 'R$ ' + value.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
                        }
                    }
                }
            }
        }
    });
}

/**
 * Atualiza os gráficos de detalhamento (Rosca de Categorias e Ranking de Itens)
 * @param {Array} transacoes - Lista de transações do ano
 * @param {string} tipoSelecionado - Tipo para explodir (ex: Receita, Despesa)
 * @param {boolean} apenasPagos - Se deve considerar apenas efetivados
 * @param {string} mesFiltrado - Filtro de visão (Ano Completo ou Mês específico)
 */
function atualizarGraficosDetalhamento(transacoes, tipoSelecionado, apenasPagos, mesFiltrado) {
    const canvasRosca = document.getElementById('chart-rosca');
    const canvasBarrasH = document.getElementById('chart-barras-h');
    
    if (!canvasRosca || !canvasBarrasH) return;
    
    const ctxRosca = canvasRosca.getContext('2d');
    const ctxBarrasH = canvasBarrasH.getContext('2d');

    const mesesMapaReverso = {
        "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
        "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12
    };

    const numMesFiltrado = mesesMapaReverso[mesFiltrado] || null;

    // Filtra transações relevantes
    const transacoesFiltradas = transacoes.filter(t => {
        // Filtro por Tipo
        const tipoT = t.tipo.trim().charAt(0).toUpperCase() + t.tipo.trim().slice(1).toLowerCase();
        const tipoS = tipoSelecionado.trim().charAt(0).toUpperCase() + tipoSelecionado.trim().slice(1).toLowerCase();
        if (tipoT !== tipoS) return false;

        // Filtro por Mês
        if (numMesFiltrado !== null && t.mes !== numMesFiltrado) return false;

        // Filtro de Efetivado (Pago)
        if (apenasPagos && !boolValue(t.pago)) return false;

        return true;
    });

    // 1. Agrupar por Categoria
    const categoriaSomas = {};
    transacoesFiltradas.forEach(t => {
        const cat = t.categoria.trim() || "Sem Categoria";
        const valor = parseFloat(t.valor) || 0.0;
        categoriaSomas[cat] = (categoriaSomas[cat] || 0) + valor;
    });

    // 2. Agrupar por Item
    const itemSomas = {};
    transacoesFiltradas.forEach(t => {
        const item = t.item.trim() || "Sem Nome";
        const valor = parseFloat(t.valor) || 0.0;
        itemSomas[item] = (itemSomas[item] || 0) + valor;
    });

    // Formata dados para os gráficos
    const labelsCategorias = Object.keys(categoriaSomas);
    const valoresCategorias = Object.values(categoriaSomas);

    // Ordena Itens (maior para menor)
    const itensOrdenados = Object.entries(itemSomas)
        .sort((a, b) => b[1] - a[1]) // Decrescente
        .slice(0, 15); // Limita aos 15 maiores itens para não sobrecarregar
    const labelsItens = itensOrdenados.map(i => i[0]);
    const valoresItens = itensOrdenados.map(i => i[1]);

    // Cor principal do Tipo Selecionado
    const rgbBase = obterCorTipoRGB(tipoSelecionado);
    
    // Destrói instâncias anteriores se houver
    if (chartRoscaInstancia) chartRoscaInstancia.destroy();
    if (chartBarrasHInstancia) chartBarrasHInstancia.destroy();

    if (valoresCategorias.length === 0) {
        // Se não houver dados, desenha estados vazios simples
        exibirMensagemSemDadosGraficos();
        return;
    }

    // Gerador de cores em degradê para as categorias da Rosca
    const backgroundColorsRosca = labelsCategorias.map((_, idx) => {
        // Reduz a opacidade conforme o índice para dar efeito degradê
        const opacidade = Math.max(0.2, 1.0 - (idx * 0.15));
        return `rgba(${rgbBase[0]}, ${rgbBase[1]}, ${rgbBase[2]}, ${opacidade})`;
    });

    // Renderiza Gráfico Rosca (Pie/Doughnut)
    chartRoscaInstancia = new Chart(ctxRosca, {
        type: 'doughnut',
        data: {
            labels: labelsCategorias,
            datasets: [{
                data: valoresCategorias,
                backgroundColor: backgroundColorsRosca,
                borderColor: 'rgba(255,255,255,0.05)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#f1f1f5',
                        font: { family: 'Outfit', size: 11 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.parsed;
                            return ' ' + context.label + ': ' + new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
                        }
                    }
                }
            }
        }
    });

    // Renderiza Gráfico Barras Horizontal
    const corBarrasH = `rgba(${rgbBase[0]}, ${rgbBase[1]}, ${rgbBase[2]}, 0.85)`;
    chartBarrasHInstancia = new Chart(ctxBarrasH, {
        type: 'bar',
        data: {
            labels: labelsItens,
            datasets: [{
                data: valoresItens,
                backgroundColor: corBarrasH,
                borderColor: `rgba(${rgbBase[0]}, ${rgbBase[1]}, ${rgbBase[2]}, 1.0)`,
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y', // Inverte eixo para barras horizontais
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ' ' + new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(context.parsed.x);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#9090a2',
                        font: { family: 'Outfit' },
                        callback: function(value) {
                            return 'R$ ' + value.toLocaleString('pt-BR');
                        }
                    }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#f1f1f5', font: { family: 'Outfit', size: 12 } }
                }
            }
        }
    });
}

function exibirMensagemSemDadosGraficos() {
    // Caso de ausência de dados tratado em charts.js apenas limpando instâncias.
    // O JS em app.js também notificará a interface.
}

// Auxiliar para converter boleano
function boolValue(val) {
    if (typeof val === 'boolean') return val;
    if (typeof val === 'string') return val.toLowerCase() === 'true';
    return !!val;
}
