// Constantes do Mapa de Meses
const MESES_MAPA = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
};

const MAPA_REVERSO_MES = {
    "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12
};

const LISTA_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

// Estado Global da SPA
let anoAtivo = new Date().getFullYear();
let mesFiltrado = "Ano Completo";
let dadosPivotados = []; // Estrutura: [{ item, tipo, categoria, meses: {1: {valor, pago}, 2: ...} }]
let apenasPagosDetalhe = true;
let tipoDetalheSelecionado = "Despesa";

// Elementos da Interface
const selectAno = document.getElementById("select-ano");
const selectMes = document.getElementById("select-mes");
const selectTipoDetalhe = document.getElementById("select-tipo-detalhe");
const checkApenasPagos = document.getElementById("check-apenas-pagos");

const authModal = document.getElementById("auth-modal");
const tokenInput = document.getElementById("token-input");
const authError = document.getElementById("auth-error");
const btnLogin = document.getElementById("btn-login");
const btnLogout = document.getElementById("btn-logout");

const btnAdicionarLinha = document.getElementById("btn-adicionar-linha");
const btnPropagar = document.getElementById("btn-propagar");
const btnSalvar = document.getElementById("btn-salvar");

const loadingOverlay = document.getElementById("loading-overlay");

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
    inicializarSeletores();
    configurarEventListeners();
    verificarAutenticacao();
});

// Inicializa os selects de Ano e Event Listeners Básicos
function inicializarSeletores() {
    const anoAtual = new Date().getFullYear();
    selectAno.innerHTML = "";
    
    // Janela de anos: Atual - 2 até Atual + 1 (Igual original)
    const anosOpcoes = [anoAtual - 2, anoAtual - 1, anoAtual, anoAtual + 1];
    anosOpcoes.forEach(ano => {
        const option = document.createElement("option");
        option.value = ano;
        option.textContent = ano;
        if (ano === anoAtual) {
            option.selected = true;
            anoAtivo = ano;
        }
        selectAno.appendChild(option);
    });
}

function configurarEventListeners() {
    // Mudança de Filtros
    selectAno.addEventListener("change", (e) => {
        anoAtivo = parseInt(e.target.value);
        carregarDadosDoAno();
    });

    selectMes.addEventListener("change", (e) => {
        mesFiltrado = e.target.value;
        
        // Exibe ou esconde o botão de propagação conforme filtro de mês
        if (mesFiltrado === "Ano Completo") {
            btnPropagar.classList.add("hidden");
        } else {
            btnPropagar.classList.remove("hidden");
            btnPropagar.textContent = `✨ Preencher meses seguintes a ${mesFiltrado}`;
        }
        
        renderizarTabelas();
        atualizarMetricas();
        atualizarGraficos();
    });

    selectTipoDetalhe.addEventListener("change", (e) => {
        tipoDetalheSelecionado = e.target.value;
        atualizarGraficos();
    });

    checkApenasPagos.addEventListener("change", (e) => {
        apenasPagosDetalhe = e.target.checked;
        atualizarGraficos();
    });

    // Ações de Botões
    btnAdicionarLinha.addEventListener("click", adicionarLinha);
    btnPropagar.addEventListener("click", propagarValores);
    btnSalvar.addEventListener("click", salvarDadosServidor);

    // Login/Logout
    btnLogin.addEventListener("click", realizarLogin);
    tokenInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") realizarLogin();
    });
    btnLogout.addEventListener("click", realizarLogout);

    // Configuração de abas
    const tabBtns = document.querySelectorAll(".tab-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            const tabId = btn.getAttribute("data-tab");
            document.getElementById(tabId).classList.add("active");
            
            // Re-renderiza para garantir a consistência das tabelas
            renderizarTabelas();
        });
    });
}

// Utilitários de Cookies
function obterCookie(nome) {
    const valor = `; ${document.cookie}`;
    const partes = valor.split(`; ${nome}=`);
    if (partes.length === 2) return partes.pop().split(';').shift();
    return null;
}

// Verifica se está logado
function verificarAutenticacao() {
    const token = obterCookie("session_token");
    if (token) {
        authModal.classList.remove("active");
        carregarDadosDoAno();
    } else {
        authModal.classList.add("active");
        tokenInput.focus();
    }
}

// Login
async function realizarLogin() {
    const token = tokenInput.value.trim();
    if (!token) return;

    exibirLoading(true);
    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token })
        });

        if (response.ok) {
            authError.classList.add("hidden");
            authModal.classList.remove("active");
            tokenInput.value = "";
            carregarDadosDoAno();
        } else {
            authError.classList.remove("hidden");
            tokenInput.focus();
        }
    } catch (e) {
        console.error("Erro no login:", e);
        authError.textContent = "Erro de conexão com o servidor.";
        authError.classList.remove("hidden");
    } finally {
        exibirLoading(false);
    }
}

// Logout
async function realizarLogout() {
    exibirLoading(true);
    try {
        await fetch("/api/auth/logout", { method: "POST" });
    } catch (e) {
        console.error("Erro no logout:", e);
    } finally {
        // Remove cookie manualmente por precaução
        document.cookie = "session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
        authModal.classList.add("active");
        exibirLoading(false);
    }
}

// Carregar transações do backend
async function carregarDadosDoAno() {
    exibirLoading(true);
    try {
        const token = obterCookie("session_token");
        const response = await fetch(`/api/transacoes?ano=${anoAtivo}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (response.status === 401) {
            realizarLogout();
            return;
        }

        if (!response.ok) throw new Error("Erro ao carregar dados do ano.");

        const transacoes = await response.json();
        processarEPivotarDados(transacoes);
        
        renderizarTabelas();
        atualizarMetricas();
        popularSeletorTipoDetalhe();
        atualizarGraficos();

    } catch (e) {
        console.error(e);
        alert("Falha ao buscar lançamentos do servidor.");
    } finally {
        exibirLoading(false);
    }
}

// Transforma a lista plana em formato pivotado estruturado
function processarEPivotarDados(transacoes) {
    const mapa = {};
    
    transacoes.forEach(t => {
        // Chave de agrupamento base: Item, Tipo, Categoria
        const chave = `${t.item.trim()}|||${t.tipo.trim()}|||${t.categoria.trim()}`;
        
        if (!mapa[chave]) {
            mapa[chave] = {
                item: t.item.trim(),
                tipo: t.tipo.trim(),
                categoria: t.categoria.trim(),
                meses: {}
            };
            // Inicializa todos os 12 meses zerados
            for (let m = 1; m <= 12; m++) {
                mapa[chave].meses[m] = { valor: 0.0, pago: false };
            }
        }
        
        // Atribui o valor do respectivo mês
        if (t.mes >= 1 && t.mes <= 12) {
            mapa[chave].meses[t.mes] = {
                valor: parseFloat(t.valor) || 0.0,
                pago: boolValue(t.pago)
            };
        }
    });

    dadosPivotados = Object.values(mapa);
}

// Popular seletor de Tipos no Detalhamento
function popularSeletorTipoDetalhe() {
    const tiposDisponiveis = [...new Set(dadosPivotados.map(d => d.tipo).filter(t => t.trim() !== ""))];
    selectTipoDetalhe.innerHTML = "";
    
    if (tiposDisponiveis.length === 0) {
        tiposDisponiveis.push("Receita", "Despesa", "Investimento", "Reserva");
    }

    tiposDisponiveis.forEach(tipo => {
        const option = document.createElement("option");
        option.value = tipo;
        option.textContent = tipo;
        if (tipo === tipoDetalheSelecionado) {
            option.selected = true;
        }
        selectTipoDetalhe.appendChild(option);
    });
    
    if (!tiposDisponiveis.includes(tipoDetalheSelecionado)) {
        tipoDetalheSelecionado = tiposDisponiveis[0];
    }
}

// Renderiza ambas as tabelas (Edição e Visualização Colorida)
function renderizarTabelas() {
    renderizarTabelaEdicao();
    renderizarTabelaVisualizacao();
}

// Renderiza a Tabela Interativa de Edição
function renderizarTabelaEdicao() {
    const tabela = document.getElementById("tabela-edicao");
    const thead = tabela.querySelector("thead");
    const tbody = tabela.querySelector("tbody");
    
    thead.innerHTML = "";
    tbody.innerHTML = "";

    // 1. Cria Cabeçalho
    const headerRow = document.createElement("tr");
    
    // Colunas fixas
    const thAcoes = document.createElement("th");
    thAcoes.innerHTML = '<i class="fa-solid fa-gear"></i>';
    thAcoes.style.width = "50px";
    headerRow.appendChild(thAcoes);

    const thItem = document.createElement("th");
    thItem.textContent = "Item";
    headerRow.appendChild(thItem);

    const thTipo = document.createElement("th");
    thTipo.textContent = "Tipo";
    thTipo.style.width = "130px";
    headerRow.appendChild(thTipo);

    const thCategoria = document.createElement("th");
    thCategoria.textContent = "Categoria";
    headerRow.appendChild(thCategoria);

    // Colunas de meses filtrados
    const mesesAExibir = mesFiltrado === "Ano Completo" ? LISTA_MESES : [mesFiltrado];
    mesesAExibir.forEach(mes => {
        const thMesVal = document.createElement("th");
        thMesVal.textContent = mes;
        thMesVal.style.textAlign = "right";
        thMesVal.style.width = "100px";
        headerRow.appendChild(thMesVal);

        const thMesPago = document.createElement("th");
        thMesPago.textContent = `${mes} - Pago`;
        thMesPago.style.textAlign = "center";
        thMesPago.style.width = "85px";
        headerRow.appendChild(thMesPago);
    });

    thead.appendChild(headerRow);

    // Ordenação idêntica ao original: Tipo desc, Pago asc, Valor desc, Categoria desc, Item asc
    const mesAtualNome = MESES_MAPA[new Date().getMonth() + 1];
    const mesOrdenacao = mesFiltrado === "Ano Completo" ? mesAtualNome : mesFiltrado;
    const numMesOrdenacao = MAPA_REVERSO_MES[mesOrdenacao];

    const dadosOrdenados = [...dadosPivotados].sort((a, b) => {
        // Tipo desc (Receita vem antes de Despesa se compararmos texto ou priorizarmos. No original: 'Tipo' descending)
        // No original: Receita, Despesa, Investimento, Reserva
        const prioridadeTipo = { "Receita": 4, "Despesa": 3, "Investimento": 2, "Reserva": 1 };
        const pA = prioridadeTipo[a.tipo] || 0;
        const pB = prioridadeTipo[b.tipo] || 0;
        if (pA !== pB) return pB - pA; // Descending

        // Pago do mês atual asc
        const pagoA = a.meses[numMesOrdenacao]?.pago ? 1 : 0;
        const pagoB = b.meses[numMesOrdenacao]?.pago ? 1 : 0;
        if (pagoA !== pagoB) return pagoA - pagoB; // Ascending

        // Valor do mês atual desc
        const valA = a.meses[numMesOrdenacao]?.valor || 0;
        const valB = b.meses[numMesOrdenacao]?.valor || 0;
        if (valA !== valB) return valB - valA; // Descending

        // Categoria desc
        const catA = a.categoria || "";
        const catB = b.categoria || "";
        if (catA !== catB) return catB.localeCompare(catA);

        // Item asc
        const itemA = a.item || "";
        const itemB = b.item || "";
        return itemA.localeCompare(itemB);
    });

    // 2. Preenche o corpo
    dadosOrdenados.forEach((row, idx) => {
        // Encontra o index real no array original dadosPivotados
        const idxOriginal = dadosPivotados.findIndex(d => d === row);
        
        const tr = document.createElement("tr");

        // Botão Deletar
        const tdDel = document.createElement("td");
        tdDel.style.textAlign = "center";
        tdDel.innerHTML = `<button class="btn-delete-row" onclick="excluirLinha(${idxOriginal})" title="Excluir Lançamento"><i class="fa-solid fa-trash-can"></i></button>`;
        tr.appendChild(tdDel);

        // Input Item
        const tdItem = document.createElement("td");
        const inputItem = document.createElement("input");
        inputItem.type = "text";
        inputItem.className = "cell-input";
        inputItem.value = row.item;
        inputItem.addEventListener("change", (e) => {
            dadosPivotados[idxOriginal].item = e.target.value.trim();
            atualizarMetricas();
            atualizarGraficos();
        });
        tdItem.appendChild(inputItem);
        tr.appendChild(tdItem);

        // Select Tipo
        const tdTipo = document.createElement("td");
        const selectTp = document.createElement("select");
        selectTp.className = "cell-select";
        ["Receita", "Despesa", "Investimento", "Reserva"].forEach(tp => {
            const opt = document.createElement("option");
            opt.value = tp;
            opt.textContent = tp;
            if (row.tipo === tp) opt.selected = true;
            selectTp.appendChild(opt);
        });
        selectTp.addEventListener("change", (e) => {
            dadosPivotados[idxOriginal].tipo = e.target.value;
            atualizarMetricas();
            popularSeletorTipoDetalhe();
            atualizarGraficos();
        });
        tdTipo.appendChild(selectTp);
        tr.appendChild(tdTipo);

        // Input Categoria
        const tdCat = document.createElement("td");
        const inputCat = document.createElement("input");
        inputCat.type = "text";
        inputCat.className = "cell-input";
        inputCat.value = row.categoria;
        inputCat.addEventListener("change", (e) => {
            dadosPivotados[idxOriginal].categoria = e.target.value.trim();
            atualizarMetricas();
            atualizarGraficos();
        });
        tdCat.appendChild(inputCat);
        tr.appendChild(tdCat);

        // Inputs dos meses
        mesesAExibir.forEach(mes => {
            const numMes = MAPA_REVERSO_MES[mes];
            const dadosMes = row.meses[numMes] || { valor: 0.0, pago: false };

            // Célula Valor
            const tdVal = document.createElement("td");
            const inputVal = document.createElement("input");
            inputVal.type = "number";
            inputVal.step = "0.01";
            inputVal.className = "cell-input cell-input-number";
            inputVal.value = dadosMes.valor === 0 ? "0.00" : dadosMes.valor.toFixed(2);
            inputVal.addEventListener("change", (e) => {
                let v = parseFloat(e.target.value) || 0.0;
                dadosPivotados[idxOriginal].meses[numMes].valor = v;
                e.target.value = v === 0 ? "0.00" : v.toFixed(2);
                atualizarMetricas();
                atualizarGraficos();
            });
            tdVal.appendChild(inputVal);
            tr.appendChild(tdVal);

            // Célula Pago (Checkbox)
            const tdPago = document.createElement("td");
            tdPago.style.textAlign = "center";
            const inputPago = document.createElement("input");
            inputPago.type = "checkbox";
            inputPago.className = "table-checkbox";
            inputPago.checked = dadosMes.pago;
            inputPago.addEventListener("change", (e) => {
                dadosPivotados[idxOriginal].meses[numMes].pago = e.target.checked;
                atualizarMetricas();
                atualizarGraficos();
            });
            tdPago.appendChild(inputPago);
            tr.appendChild(tdPago);
        });

        tbody.appendChild(tr);
    });
}

// Renderiza a Tabela de Visualização Colorida
function renderizarTabelaVisualizacao() {
    const tabela = document.getElementById("tabela-visualizacao");
    const thead = tabela.querySelector("thead");
    const tbody = tabela.querySelector("tbody");
    
    thead.innerHTML = "";
    tbody.innerHTML = "";

    // 1. Cria Cabeçalho
    const headerRow = document.createElement("tr");
    
    const thItem = document.createElement("th");
    thItem.textContent = "Item";
    headerRow.appendChild(thItem);

    const thTipo = document.createElement("th");
    thTipo.textContent = "Tipo";
    thTipo.style.width = "130px";
    headerRow.appendChild(thTipo);

    const thCategoria = document.createElement("th");
    thCategoria.textContent = "Categoria";
    headerRow.appendChild(thCategoria);

    // Colunas de meses filtrados
    const mesesAExibir = mesFiltrado === "Ano Completo" ? LISTA_MESES : [mesFiltrado];
    mesesAExibir.forEach(mes => {
        const thMesVal = document.createElement("th");
        thMesVal.textContent = mes;
        thMesVal.style.textAlign = "right";
        thMesVal.style.width = "110px";
        headerRow.appendChild(thMesVal);

        const thMesPago = document.createElement("th");
        thMesPago.textContent = `${mes} - Pago`;
        thMesPago.style.textAlign = "center";
        thMesPago.style.width = "95px";
        headerRow.appendChild(thMesPago);
    });

    thead.appendChild(headerRow);

    // Ordenação idêntica ao original
    const mesAtualNome = MESES_MAPA[new Date().getMonth() + 1];
    const mesOrdenacao = mesFiltrado === "Ano Completo" ? mesAtualNome : mesFiltrado;
    const numMesOrdenacao = MAPA_REVERSO_MES[mesOrdenacao];

    const dadosOrdenados = [...dadosPivotados].sort((a, b) => {
        const prioridadeTipo = { "Receita": 4, "Despesa": 3, "Investimento": 2, "Reserva": 1 };
        const pA = prioridadeTipo[a.tipo] || 0;
        const pB = prioridadeTipo[b.tipo] || 0;
        if (pA !== pB) return pB - pA;

        const pagoA = a.meses[numMesOrdenacao]?.pago ? 1 : 0;
        const pagoB = b.meses[numMesOrdenacao]?.pago ? 1 : 0;
        if (pagoA !== pagoB) return pagoA - pagoB;

        const valA = a.meses[numMesOrdenacao]?.valor || 0;
        const valB = b.meses[numMesOrdenacao]?.valor || 0;
        if (valA !== valB) return valB - valA;

        const catA = a.categoria || "";
        const catB = b.categoria || "";
        if (catA !== catB) return catB.localeCompare(catA);

        const itemA = a.item || "";
        const itemB = b.item || "";
        return itemA.localeCompare(itemB);
    });

    // 2. Preenche o corpo (Colorido)
    dadosOrdenados.forEach(row => {
        const tr = document.createElement("tr");
        
        // Aplica classe de cor baseado no Tipo
        const tipoLimpo = row.tipo.trim().toLowerCase();
        if (tipoLimpo === "receita") tr.className = "row-receita";
        else if (tipoLimpo === "despesa") tr.className = "row-despesa";
        else if (tipoLimpo === "investimento") tr.className = "row-investimento";
        else if (tipoLimpo === "reserva") tr.className = "row-reserva";
        else tr.className = "row-padrao";

        // Células estáticas
        const tdItem = document.createElement("td");
        tdItem.textContent = row.item || "-";
        tr.appendChild(tdItem);

        const tdTipo = document.createElement("td");
        tdTipo.textContent = row.tipo || "-";
        tr.appendChild(tdTipo);

        const tdCat = document.createElement("td");
        tdCat.textContent = row.categoria || "-";
        tr.appendChild(tdCat);

        // Valores e Status dos meses
        mesesAExibir.forEach(mes => {
            const numMes = MAPA_REVERSO_MES[mes];
            const dadosMes = row.meses[numMes] || { valor: 0.0, pago: false };

            // Valor formatado em R$
            const tdVal = document.createElement("td");
            tdVal.style.textAlign = "right";
            tdVal.style.fontWeight = "500";
            tdVal.textContent = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(dadosMes.valor);
            tr.appendChild(tdVal);

            // Checkbox estático (Apenas leitura)
            const tdPago = document.createElement("td");
            tdPago.style.textAlign = "center";
            const iconCheck = document.createElement("i");
            if (dadosMes.pago) {
                iconCheck.className = "fa-solid fa-circle-check";
                iconCheck.style.color = "var(--color-receita)";
            } else {
                iconCheck.className = "fa-solid fa-circle-minus";
                iconCheck.style.color = "var(--text-muted)";
            }
            tdPago.appendChild(iconCheck);
            tr.appendChild(tdPago);
        });

        tbody.appendChild(tr);
    });
}

// Adicionar Linha Vazia
function adicionarLinha() {
    const novaLinha = {
        item: "",
        tipo: "Despesa",
        categoria: "",
        meses: {}
    };
    
    // Inicializa meses com valor zerado e pago=false
    for (let m = 1; m <= 12; m++) {
        novaLinha.meses[m] = { valor: 0.0, pago: false };
    }
    
    dadosPivotados.push(novaLinha);
    renderizarTabelas();
    
    // Rola a tabela de edição para o final para facilitar visualização
    setTimeout(() => {
        const container = document.querySelector("#tab-editar .table-container");
        container.scrollTop = container.scrollHeight;
    }, 100);
}

// Excluir Linha
function excluirLinha(index) {
    if (confirm("Deseja realmente remover esta linha do lançamento?")) {
        dadosPivotados.splice(index, 1);
        renderizarTabelas();
        atualizarMetricas();
        atualizarGraficos();
    }
}

// Propagar valores do mês ativo para os meses seguintes
function propagarValores() {
    if (mesFiltrado === "Ano Completo") return;
    
    const numMesOrigem = MAPA_REVERSO_MES[mesFiltrado];
    if (!numMesOrigem || numMesOrigem === 12) {
        alert("Não é possível propagar a partir de Dezembro.");
        return;
    }

    if (!confirm(`Deseja propagar os valores maiores que R$ 0,00 de ${mesFiltrado} para os meses seguintes (onde o valor for R$ 0,00)?`)) {
        return;
    }

    let alterados = 0;
    dadosPivotados.forEach(row => {
        const valorOrigem = parseFloat(row.meses[numMesOrigem].valor) || 0.0;
        
        if (valorOrigem > 0) {
            // Varre meses futuros (numMesOrigem + 1 até 12)
            for (let m = numMesOrigem + 1; m <= 12; m++) {
                const valorFuturo = parseFloat(row.meses[m].valor) || 0.0;
                if (valorFuturo === 0) {
                    row.meses[m].valor = valorOrigem;
                    row.meses[m].pago = false; // Define como previsto
                    alterados++;
                }
            }
        }
    });

    if (alterados > 0) {
        renderizarTabelas();
        atualizarMetricas();
        atualizarGraficos();
        alert(`${alterados} valores vazios foram preenchidos com sucesso.`);
    } else {
        alert("Nenhum valor elegível para propagação foi encontrado.");
    }
}

// Atualiza os painéis de métrica (Saldo Atual e Saldo Projetado)
function atualizarMetricas() {
    const mesAtualNome = MESES_MAPA[new Date().getMonth() + 1];
    const mesAlvo = mesFiltrado === "Ano Completo" ? mesAtualNome : mesFiltrado;
    const numMesAlvo = MAPA_REVERSO_MES[mesAlvo];

    document.getElementById("label-saldo-atual").textContent = `${mesAlvo}: Saldo Efetivado`;
    document.getElementById("label-saldo-projetado").textContent = `${mesAlvo}: Saldo Projetado`;

    let totalReceitaAtual = 0;
    let totalNaoReceitaAtual = 0;

    let totalReceitaProjetado = 0;
    let totalNaoReceitaProjetado = 0;

    dadosPivotados.forEach(row => {
        const dadosMes = row.meses[numMesAlvo] || { valor: 0.0, pago: false };
        const valor = parseFloat(dadosMes.valor) || 0.0;
        const pago = boolValue(dadosMes.pago);
        const tipo = row.tipo.trim().toLowerCase();

        // 1. Saldo Efetivado (Apenas pagos)
        if (pago) {
            if (tipo === "receita") {
                totalReceitaAtual += valor;
            } else {
                totalNaoReceitaAtual += valor;
            }
        }

        // 2. Saldo Projetado (Independe se foi pago ou não)
        if (tipo === "receita") {
            totalReceitaProjetado += valor;
        } else {
            totalNaoReceitaProjetado += valor;
        }
    });

    const saldoAtual = totalReceitaAtual - totalNaoReceitaAtual;
    const saldoProjetado = totalReceitaProjetado - totalNaoReceitaProjetado;

    // Formata na tela
    const valAtualEl = document.getElementById("val-saldo-atual");
    const valProjEl = document.getElementById("val-saldo-projetado");

    valAtualEl.textContent = formatarMoeda(saldoAtual);
    valProjEl.textContent = formatarMoeda(saldoProjetado);

    // Ajusta classes baseadas no valor para feedback visual (verde para positivo, vermelho para negativo)
    ajustarCorMetrica(valAtualEl, saldoAtual);
    ajustarCorMetrica(valProjEl, saldoProjetado);
}

function ajustarCorMetrica(elemento, valor) {
    if (valor > 0) {
        elemento.style.color = "var(--color-receita)";
    } else if (valor < 0) {
        elemento.style.color = "var(--color-despesa)";
    } else {
        elemento.style.color = "var(--text-primary)";
    }
}

// Despivota dados em memória e salva no banco de dados via API
async function salvarDadosServidor() {
    exibirLoading(true);
    try {
        const transacoesPlanas = [];
        
        dadosPivotados.forEach(row => {
            // Só exporta se pelo menos uma coluna Item/Tipo/Categoria estiver preenchida
            if (row.item.trim() || row.tipo.trim() || row.categoria.trim()) {
                // Para cada um dos 12 meses
                for (let m = 1; m <= 12; m++) {
                    const dadosMes = row.meses[m] || { valor: 0.0, pago: false };
                    
                    transacoesPlanas.push({
                        ano: anoAtivo,
                        mes: m,
                        item: row.item.trim(),
                        tipo: row.tipo.trim(),
                        categoria: row.categoria.trim(),
                        valor: parseFloat(dadosMes.valor) || 0.0,
                        pago: boolValue(dadosMes.pago)
                    });
                }
            }
        });

        const token = obterCookie("session_token");
        const response = await fetch(`/api/transacoes/bulk-save?ano=${anoAtivo}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(transacoesPlanas)
        });

        if (response.status === 401) {
            realizarLogout();
            return;
        }

        if (!response.ok) throw new Error("Erro ao salvar transações no servidor.");

        alert(`Lançamentos do ano ${anoAtivo} salvos com sucesso!`);
        carregarDadosDoAno(); // Recarrega para consolidar os dados

    } catch (e) {
        console.error(e);
        alert("Falha ao salvar dados no servidor. Verifique sua conexão.");
    } finally {
        exibirLoading(false);
    }
}

// Atualiza todos os gráficos
function atualizarGraficos() {
    // 1. Gera lista de transações planas virtuais (temporárias) com base no estado atual da tabela
    // para alimentar os métodos de plotagem
    const transacoesVirtuais = [];
    dadosPivotados.forEach(row => {
        for (let m = 1; m <= 12; m++) {
            transacoesVirtuais.push({
                mes: m,
                tipo: row.tipo,
                categoria: row.categoria,
                item: row.item,
                valor: row.meses[m].valor,
                pago: row.meses[m].pago
            });
        }
    });

    // 2. Chama funções do charts.js
    atualizarGraficoMensal(transacoesVirtuais, anoAtivo);
    atualizarGraficosDetalhamento(transacoesVirtuais, tipoDetalheSelecionado, apenasPagosDetalhe, mesFiltrado);
}

// Utilitários de Interface
function exibirLoading(visivel) {
    if (visivel) {
        loadingOverlay.classList.remove("hidden");
    } else {
        loadingOverlay.classList.add("hidden");
    }
}

function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor);
}

function boolValue(val) {
    if (typeof val === 'boolean') return val;
    if (typeof val === 'string') return val.toLowerCase() === 'true';
    return !!val;
}
