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

// // Estado Global da SPA
let anoAtivo = new Date().getFullYear();
let mesFiltrado = "Ano Completo";
let dadosPivotados = []; // Estrutura: [{ item, tipo, categoria, meses: {1: {valor, pago}, 2: ...} }]
let dadosPivotadosAnoAnterior = []; // Dados do ano anterior para comparativo
let apenasPagosDetalhe = true;
let tipoDetalheSelecionado = "Despesa";
let filtroTipoAtivo = "Todos";
let filtroCategoriaAtiva = "Todas";
let currentLoginUsername = "";

// Elementos da Interface
const selectAno = document.getElementById("select-ano");
const selectMes = document.getElementById("select-mes");
const selectTipoDetalhe = document.getElementById("select-tipo-detalhe");
const checkApenasPagos = document.getElementById("check-apenas-pagos");

const authModal = document.getElementById("auth-modal");
const btnLogout = document.getElementById("btn-logout");
const btnThemeToggle = document.getElementById("btn-theme-toggle");

const btnAdicionarLinha = document.getElementById("btn-adicionar-linha");
const btnPropagar = document.getElementById("btn-propagar");
const btnSalvar = document.getElementById("btn-salvar");

const btnDownloadCsv = document.getElementById("btn-download-csv");
const btnUploadTrigger = document.getElementById("btn-upload-trigger");
const inputUploadCsv = document.getElementById("input-upload-csv");

const filterTipo = document.getElementById("filter-tipo");
const filterCategoria = document.getElementById("filter-categoria");

const loadingOverlay = document.getElementById("loading-overlay");

// Inicialização movida para o final do arquivo (DOMContentLoaded unificado)

// Inicializa os selects de Ano e Event Listeners Básicos
function inicializarSeletores() {
    const anoAtual = new Date().getFullYear();
    const anoSeguinte = anoAtual + 1;
    selectAno.innerHTML = "";
    
    // Janela inicial de anos de forma decrescente (antes do fetch do BD)
    const anosOpcoes = [anoSeguinte, anoAtual];
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
    // Tema claro/escuro
    if (btnThemeToggle) {
        btnThemeToggle.addEventListener("click", alternarTema);
    }

    // Mudança de Filtros no Cabeçalho
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

    // Filtros Locais da Tabela (Tipo e Categoria)
    if (filterTipo) {
        filterTipo.addEventListener("change", (e) => {
            filtroTipoAtivo = e.target.value;
            renderizarTabelas();
        });
    }
    if (filterCategoria) {
        filterCategoria.addEventListener("change", (e) => {
            filtroCategoriaAtiva = e.target.value;
            renderizarTabelas();
        });
    }

    // Ações de CSV
    if (btnDownloadCsv) {
        btnDownloadCsv.addEventListener("click", exportarCSV);
    }
    if (btnUploadTrigger && inputUploadCsv) {
        btnUploadTrigger.addEventListener("click", () => inputUploadCsv.click());
        inputUploadCsv.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) {
                importarCSV(e.target.files[0]);
            }
        });
    }

    // Ações de Botões
    btnAdicionarLinha.addEventListener("click", adicionarLinha);
    btnPropagar.addEventListener("click", propagarValores);
    btnSalvar.addEventListener("click", salvarDadosServidor);

    // Configuração do Modal de Autenticação - Eventos das Telas
    document.getElementById("btn-login-next").addEventListener("click", realizarLoginStep1);
    document.getElementById("login-password").addEventListener("keydown", (e) => {
        if (e.key === "Enter") realizarLoginStep1();
    });
    document.getElementById("login-username").addEventListener("keydown", (e) => {
        if (e.key === "Enter") realizarLoginStep1();
    });

    document.getElementById("btn-login-submit").addEventListener("click", realizarLoginStep2);
    document.getElementById("login-otp").addEventListener("keydown", (e) => {
        if (e.key === "Enter") realizarLoginStep2();
    });

    document.getElementById("btn-register-submit").addEventListener("click", realizarCadastro);
    document.getElementById("register-password").addEventListener("keydown", (e) => {
        if (e.key === "Enter") realizarCadastro();
    });

    document.getElementById("btn-setup-2fa-done").addEventListener("click", () => {
        showAuthScreen("auth-login-step1");
    });

    document.getElementById("btn-reset-submit").addEventListener("click", realizarRedefinicaoSenha);
    document.getElementById("reset-new-password").addEventListener("keydown", (e) => {
        if (e.key === "Enter") realizarRedefinicaoSenha();
    });

    // Links de navegação dentro do modal
    document.getElementById("link-go-register").addEventListener("click", (e) => {
        e.preventDefault();
        showAuthScreen("auth-register");
    });
    document.getElementById("link-go-reset").addEventListener("click", (e) => {
        e.preventDefault();
        showAuthScreen("auth-reset-password");
    });
    document.getElementById("link-back-to-step1").addEventListener("click", (e) => {
        e.preventDefault();
        showAuthScreen("auth-login-step1");
    });
    document.getElementById("link-register-back").addEventListener("click", (e) => {
        e.preventDefault();
        showAuthScreen("auth-login-step1");
    });
    document.getElementById("link-reset-back").addEventListener("click", (e) => {
        e.preventDefault();
        showAuthScreen("auth-login-step1");
    });

    btnLogout.addEventListener("click", realizarLogout);

    // Google OAuth button (popup flow)
    const btnGoogle = document.getElementById('btn-google-login');
    if (btnGoogle) btnGoogle.addEventListener('click', iniciarLoginGoogle);

    // Configuração de abas
    const tabBtns = document.querySelectorAll(".tab-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            const tabId = btn.getAttribute("data-tab");
            document.getElementById(tabId).classList.add("active");
            document.body.classList.toggle("investment-mode", tabId === "tab-carteira");
            
            // Re-renderiza para garantir a consistência das tabelas
            if (tabId === "tab-carteira") {
                if (typeof window.onInvestmentTabActivated === "function") {
                    window.onInvestmentTabActivated();
                }
            } else {
                renderizarTabelas();
            }
        });
    });
}

// Inicia fluxo de login com Google: abre popup que redireciona para Google OAuth e recebe id_token via postMessage
function iniciarLoginGoogle() {
    const meta = document.querySelector('meta[name="google-client-id"]');
    const clientId = meta ? meta.getAttribute('content') : '';
    if (!clientId) {
        alert('Google Client ID não configurado. Adicione uma meta tag name="google-client-id" no HTML.');
        return;
    }

    const redirect = `${window.location.origin}/google_oauth_callback.html`;
    const nonce = Math.random().toString(36).slice(2);
    const scope = encodeURIComponent('openid email profile');
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(clientId)}&response_type=id_token&redirect_uri=${encodeURIComponent(redirect)}&scope=${scope}&nonce=${nonce}`;

    const w = window.open(authUrl, 'google_oauth', 'width=600,height=700');

    function onMessage(e) {
        if (e.origin !== window.location.origin) return;
        const data = e.data || {};
        if (data.type === 'google-id-token' && data.id_token) {
            window.removeEventListener('message', onMessage);
            if (w) try { w.close(); } catch(e){}
            autenticarViaGoogle(data.id_token);
        }
    }

    window.addEventListener('message', onMessage);
}

async function autenticarViaGoogle(id_token) {
    exibirLoading(true);
    try {
        const resp = await fetch('/api/auth/login/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_token })
        });
        const data = await resp.json();
        if (resp.ok) {
            // Assume backend set cookie; close modal and reload data
            authModal.classList.remove('active');
            carregarDadosDoAno();
        } else {
            alert(data.detail || 'Falha no login via Google.');
        }
    } catch (e) {
        console.error('Erro OAuth Google', e);
        alert('Erro de conexão no login via Google.');
    } finally {
        exibirLoading(false);
    }
}

// Utilitários de Cookies
function obterCookie(nome) {
    const valor = `; ${document.cookie}`;
    const partes = valor.split(`; ${nome}=`);
    if (partes.length === 2) return partes.pop().split(';').shift();
    return null;
}

// Alterna a tela de autenticação visível
function showAuthScreen(screenId) {
    document.querySelectorAll(".auth-screen").forEach(screen => {
        screen.classList.add("hidden");
    });
    document.getElementById(screenId).classList.remove("hidden");
}

// Verifica se está logado
function verificarAutenticacao() {
    const token = obterCookie("session_token");
    if (token) {
        authModal.classList.remove("active");
        carregarDadosDoAno();
    } else {
        authModal.classList.add("active");
        showAuthScreen("auth-login-step1");
        document.getElementById("login-username").focus();
    }
}

// Primeira etapa de Login (Usuário e Senha)
async function realizarLoginStep1() {
    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;
    const errorEl = document.getElementById("login-step1-error");
    
    if (!username || !password) {
        errorEl.textContent = "Preencha todos os campos.";
        errorEl.classList.remove("hidden");
        return;
    }

    exibirLoading(true);
    try {
        const response = await fetch("/api/auth/login/step1", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            errorEl.classList.add("hidden");
            currentLoginUsername = username;
            showAuthScreen("auth-login-step2");
            document.getElementById("login-otp").focus();
        } else {
            errorEl.textContent = data.detail || "Usuário ou senha incorretos.";
            errorEl.classList.remove("hidden");
        }
    } catch (e) {
        console.error("Erro login etapa 1:", e);
        errorEl.textContent = "Erro de conexão com o servidor.";
        errorEl.classList.remove("hidden");
    } finally {
        exibirLoading(false);
    }
}

// Segunda etapa de Login (Google Authenticator 2FA)
async function realizarLoginStep2() {
    const code = document.getElementById("login-otp").value.trim();
    const errorEl = document.getElementById("login-step2-error");
    
    if (!code || code.length !== 6) {
        errorEl.textContent = "Insira o código de 6 dígitos.";
        errorEl.classList.remove("hidden");
        return;
    }

    exibirLoading(true);
    try {
        const response = await fetch("/api/auth/login/step2", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: currentLoginUsername, code })
        });

        const data = await response.json();
        if (response.ok) {
            errorEl.classList.add("hidden");
            authModal.classList.remove("active");
            
            // Limpa campos
            document.getElementById("login-username").value = "";
            document.getElementById("login-password").value = "";
            document.getElementById("login-otp").value = "";
            
            carregarDadosDoAno();
        } else {
            errorEl.textContent = data.detail || "Código de autenticação inválido.";
            errorEl.classList.remove("hidden");
        }
    } catch (e) {
        console.error("Erro login etapa 2:", e);
        errorEl.textContent = "Erro de conexão com o servidor.";
        errorEl.classList.remove("hidden");
    } finally {
        exibirLoading(false);
    }
}

// Cadastro de usuário
async function realizarCadastro() {
    const username = document.getElementById("register-username").value.trim();
    const password = document.getElementById("register-password").value;
    const errorEl = document.getElementById("register-error");
    
    if (!username || !password) {
        errorEl.textContent = "Preencha todos os campos.";
        errorEl.classList.remove("hidden");
        return;
    }

    exibirLoading(true);
    try {
        const response = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            errorEl.classList.add("hidden");
            
            // Exibe a tela de configuração 2FA com QR Code
            document.getElementById("setup-secret-key").value = data.totp_secret;
            document.getElementById("setup-qr-img").src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(data.totp_uri)}`;
            
            showAuthScreen("auth-setup-2fa");
            
            // Limpa formulário
            document.getElementById("register-username").value = "";
            document.getElementById("register-password").value = "";
        } else {
            errorEl.textContent = data.detail || "Erro ao criar conta de usuário.";
            errorEl.classList.remove("hidden");
        }
    } catch (e) {
        console.error("Erro ao registrar:", e);
        errorEl.textContent = "Erro de conexão com o servidor.";
        errorEl.classList.remove("hidden");
    } finally {
        exibirLoading(false);
    }
}

// Redefinição de senha com TOTP
async function realizarRedefinicaoSenha() {
    const username = document.getElementById("reset-username").value.trim();
    const code = document.getElementById("reset-otp").value.trim();
    const new_password = document.getElementById("reset-new-password").value;
    const errorEl = document.getElementById("reset-error");
    
    if (!username || !code || !new_password) {
        errorEl.textContent = "Preencha todos os campos.";
        errorEl.classList.remove("hidden");
        return;
    }

    exibirLoading(true);
    try {
        const response = await fetch("/api/auth/reset-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, code, new_password })
        });

        const data = await response.json();
        if (response.ok) {
            errorEl.classList.add("hidden");
            alert("Senha redefinida com sucesso! Prossiga com o login.");
            showAuthScreen("auth-login-step1");
            
            // Limpa formulário
            document.getElementById("reset-username").value = "";
            document.getElementById("reset-otp").value = "";
            document.getElementById("reset-new-password").value = "";
        } else {
            errorEl.textContent = data.detail || "Dados incorretos ou código 2FA inválido.";
            errorEl.classList.remove("hidden");
        }
    } catch (e) {
        console.error("Erro ao redefinir:", e);
        errorEl.textContent = "Erro de conexão com o servidor.";
        errorEl.classList.remove("hidden");
    } finally {
        exibirLoading(false);
    }
}

// Logout
async function realizarLogout() {
    exibirLoading(true);
    try {
        const token = obterCookie("session_token");
        await fetch("/api/auth/logout", {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` }
        });
    } catch (e) {
        console.error("Erro no logout:", e);
    } finally {
        // Remove cookie manualmente por precaução
        document.cookie = "session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
        authModal.classList.add("active");
        showAuthScreen("auth-login-step1");
        exibirLoading(false);
    }
}

// Exportar CSV
async function exportarCSV() {
    const token = obterCookie("session_token");
    if (!token) return;

    exibirLoading(true);
    try {
        const response = await fetch("/api/transactions/download", {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("Erro na exportação.");

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `transacoes_financeiras_${anoAtivo}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (e) {
        console.error("Erro ao exportar CSV:", e);
        alert("Não foi possível exportar os dados.");
    } finally {
        exibirLoading(false);
    }
}

// Importar CSV
async function importarCSV(file) {
    if (!file) return;

    const aviso = "ATENÇÃO: O upload de CSV apagará TODOS os lançamentos existentes no banco de dados e criará novos lançamentos baseados no arquivo. Deseja prosseguir?";
    if (!confirm(aviso)) {
        if (inputUploadCsv) inputUploadCsv.value = "";
        return;
    }

    const token = obterCookie("session_token");
    if (!token) return;

    const formData = new FormData();
    formData.append("file", file);

    exibirLoading(true);
    try {
        const response = await fetch("/api/transactions/upload", {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` },
            body: formData
        });

        const data = await response.json();
        if (response.ok) {
            alert(data.message || "Dados importados com sucesso!");
            carregarDadosDoAno();
        } else {
            alert(`Falha na importação: ${data.detail || "Verifique a formatação do CSV."}`);
        }
    } catch (e) {
        console.error("Erro ao importar CSV:", e);
        alert("Ocorreu um erro de rede ao importar o CSV.");
    } finally {
        if (inputUploadCsv) inputUploadCsv.value = "";
        exibirLoading(false);
    }
}

// Inicialização e gerenciamento do Tema Claro/Escuro
function inicializarTema() {
    const temaSalvo = localStorage.getItem("tema");
    const btnTheme = document.getElementById("btn-theme-toggle");
    if (temaSalvo === "claro") {
        document.body.classList.add("light-theme");
        if (btnTheme) btnTheme.innerHTML = '<i class="fa-solid fa-sun"></i>';
    } else {
        document.body.classList.remove("light-theme");
        if (btnTheme) btnTheme.innerHTML = '<i class="fa-solid fa-moon"></i>';
    }
}

function alternarTema() {
    const btnTheme = document.getElementById("btn-theme-toggle");
    if (document.body.classList.contains("light-theme")) {
        document.body.classList.remove("light-theme");
        localStorage.setItem("tema", "escuro");
        if (btnTheme) btnTheme.innerHTML = '<i class="fa-solid fa-moon"></i>';
    } else {
        document.body.classList.add("light-theme");
        localStorage.setItem("tema", "claro");
        if (btnTheme) btnTheme.innerHTML = '<i class="fa-solid fa-sun"></i>';
    }
    // Re-renderiza gráficos para aplicar as cores corretas do novo tema
    atualizarGraficos();
}


// Atualiza dinamicamente o seletor de anos com base no banco de dados e regras
async function atualizarSeletorAnos() {
    const token = obterCookie("session_token");
    if (!token) return;

    const anoAtual = new Date().getFullYear();
    const anoSeguinte = anoAtual + 1;
    let anos = [anoAtual, anoSeguinte];

    try {
        const response = await fetch("/api/transactions/anos", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (response.ok) {
            const anosDb = await response.json();
            anosDb.forEach(ano => {
                const aInt = parseInt(ano);
                if (!isNaN(aInt) && !anos.includes(aInt)) {
                    anos.push(aInt);
                }
            });
        }
    } catch (e) {
        console.error("Erro ao carregar anos do banco:", e);
    }

    // Classificar por ordem decrescente
    anos.sort((a, b) => b - a);

    const valorAntes = selectAno.value;
    selectAno.innerHTML = "";
    anos.forEach(ano => {
        const option = document.createElement("option");
        option.value = ano;
        option.textContent = ano;
        selectAno.appendChild(option);
    });

    const valorAntesInt = parseInt(valorAntes);
    if (valorAntes && anos.includes(valorAntesInt)) {
        selectAno.value = valorAntes;
        anoAtivo = valorAntesInt;
    } else {
        selectAno.value = anoAtual;
        anoAtivo = anoAtual;
    }
}


// Carregar transações do backend
async function carregarDadosDoAno() {
    exibirLoading(true);
    try {
        const token = obterCookie("session_token");
        await atualizarSeletorAnos();
        const response = await fetch(`/api/transactions?ano=${anoAtivo}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (response.status === 401) {
            realizarLogout();
            return;
        }

        if (!response.ok) throw new Error("Erro ao carregar dados do ano.");

        const transacoes = await response.json();
        processarEPivotarDados(transacoes);
        atualizarFiltroCategoriaOpcoes();
        renderizarTabelas();
        atualizarMetricas();
        popularSeletorTipoDetalhe();
        atualizarGraficos();

        // Carrega dados do ano anterior em background para o comparativo
        carregarDadosAnoAnterior(token);

    } catch (e) {
        console.error(e);
        alert("Falha ao buscar lançamentos do servidor.");
    } finally {
        exibirLoading(false);
    }
}

// Busca dados do ano anterior para calcular comparativo % do Saldo Total
async function carregarDadosAnoAnterior(token) {
    try {
        const anoAnterior = anoAtivo - 1;
        const resp = await fetch(`/api/transactions?ano=${anoAnterior}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!resp.ok) {
            dadosPivotadosAnoAnterior = [];
            atualizarMetricas();
            return;
        }
        const transacoesAnt = await resp.json();
        // Pivota os dados do ano anterior localmente
        const mapaAnt = {};
        transacoesAnt.forEach(t => {
            const chave = `${t.item.trim()}|||${t.tipo.trim()}|||${t.categoria.trim()}`;
            if (!mapaAnt[chave]) {
                mapaAnt[chave] = { item: t.item.trim(), tipo: t.tipo.trim(), categoria: t.categoria.trim(), meses: {} };
                for (let m = 1; m <= 12; m++) mapaAnt[chave].meses[m] = { valor: 0.0, pago: false };
            }
            if (t.mes >= 1 && t.mes <= 12) {
                mapaAnt[chave].meses[t.mes] = { valor: parseFloat(t.valor) || 0.0, pago: boolValue(t.pago) };
            }
        });
        dadosPivotadosAnoAnterior = Object.values(mapaAnt);
        // Re-renderiza as métricas agora que temos os dados do ano anterior
        atualizarMetricas();
    } catch (e) {
        console.warn("Não foi possível carregar dados do ano anterior:", e);
        dadosPivotadosAnoAnterior = [];
        atualizarMetricas();
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

// Atualizar opções do filtro de Categoria com base nos dados carregados
function atualizarFiltroCategoriaOpcoes() {
    const selectFiltroCat = document.getElementById("filter-categoria");
    if (!selectFiltroCat) return;
    
    const categorias = [...new Set(dadosPivotados.map(d => d.categoria).filter(c => c.trim() !== ""))];
    
    selectFiltroCat.innerHTML = '<option value="Todas">Todas</option>';
    categorias.forEach(cat => {
        const opt = document.createElement("option");
        opt.value = cat;
        opt.textContent = cat;
        if (cat === filtroCategoriaAtiva) {
            opt.selected = true;
        }
        selectFiltroCat.appendChild(opt);
    });
    
    if (!categorias.includes(filtroCategoriaAtiva)) {
        filtroCategoriaAtiva = "Todas";
        selectFiltroCat.value = "Todas";
    }
}

// Renderiza a tabela de lançamentos
function renderizarTabelas() {
    renderizarTabelaEdicao();
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
    const mesAtualNomeHeader = MESES_MAPA[new Date().getMonth() + 1];
    const mesesAExibir = mesFiltrado === "Ano Completo" ? LISTA_MESES : [mesFiltrado];
    mesesAExibir.forEach(mes => {
        const thMesVal = document.createElement("th");
        thMesVal.textContent = mes;
        thMesVal.style.textAlign = "right";
        thMesVal.style.width = "100px";
        // Destaca o cabeçalho do mês atual
        if (mes === mesAtualNomeHeader) {
            thMesVal.classList.add("th-mes-atual");
        }
        headerRow.appendChild(thMesVal);

        const thMesPago = document.createElement("th");
        // Não exibir título da coluna Pago — cabeçalho intencionalmente vazio
        thMesPago.textContent = "";
        thMesPago.className = "th-pago";
        if (mes === mesAtualNomeHeader) {
            thMesPago.classList.add("th-mes-atual");
        }
        thMesPago.style.textAlign = "left";
        thMesPago.style.width = "40px";
        thMesPago.style.paddingLeft = "6px";
        headerRow.appendChild(thMesPago);
    });

    thead.appendChild(headerRow);

    // Ordenação idêntica ao original: Tipo desc, Pago asc, Valor desc, Categoria desc, Item asc
    const mesAtualNome = MESES_MAPA[new Date().getMonth() + 1];
    const mesOrdenacao = mesFiltrado === "Ano Completo" ? mesAtualNome : mesFiltrado;
    const numMesOrdenacao = MAPA_REVERSO_MES[mesOrdenacao];

    const dadosOrdenados = [...dadosPivotados].sort((a, b) => {
        // Linhas novas sempre vêm primeiro
        if (a.isNew && !b.isNew) return -1;
        if (!a.isNew && b.isNew) return 1;

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
        const valA = (a.meses[numMesOrdenacao]?.valor === null || a.meses[numMesOrdenacao]?.valor === undefined) ? 0 : a.meses[numMesOrdenacao].valor;
        const valB = (b.meses[numMesOrdenacao]?.valor === null || b.meses[numMesOrdenacao]?.valor === undefined) ? 0 : b.meses[numMesOrdenacao].valor;
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

    const dadosFiltrados = dadosOrdenados.filter(row => {
        const matchTipo = filtroTipoAtivo === "Todos" || row.tipo === filtroTipoAtivo;
        const matchCategoria = filtroCategoriaAtiva === "Todas" || row.categoria === filtroCategoriaAtiva;
        return matchTipo && matchCategoria;
    });

    // 2. Preenche o corpo
    dadosFiltrados.forEach((row, idx) => {
        // Encontra o index real no array original dadosPivotados
        const idxOriginal = dadosPivotados.findIndex(d => d === row);
        
        const tr = document.createElement("tr");

        // Aplica classe de cor baseada no Tipo (igual à visualização colorida)
        const tipoLimpo = row.tipo.trim().toLowerCase();
        if (tipoLimpo === "receita") tr.className = "row-receita";
        else if (tipoLimpo === "despesa") tr.className = "row-despesa";
        else if (tipoLimpo === "investimento") tr.className = "row-investimento";
        else if (tipoLimpo === "reserva") tr.className = "row-reserva";
        else tr.className = "row-padrao";

        // Botão Deletar
        const tdDel = document.createElement("td");
        tdDel.style.textAlign = "left";
        tdDel.style.width = "50px";
        tdDel.style.paddingLeft = "6px";
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
        // Permitir valor vazio se for linha nova
        const tiposOpcoes = row.tipo === "" ? ["", "Receita", "Despesa", "Investimento", "Reserva"] : ["Receita", "Despesa", "Investimento", "Reserva"];
        tiposOpcoes.forEach(tp => {
            const opt = document.createElement("option");
            opt.value = tp;
            opt.textContent = tp;
            if (row.tipo === tp) opt.selected = true;
            selectTp.appendChild(opt);
        });
        selectTp.addEventListener("change", (e) => {
            const novoTipo = e.target.value;
            dadosPivotados[idxOriginal].tipo = novoTipo;
            
            // Atualiza cor de fundo da linha imediatamente
            const tipoLimpo = novoTipo.trim().toLowerCase();
            tr.className = "";
            if (tipoLimpo === "receita") tr.className = "row-receita";
            else if (tipoLimpo === "despesa") tr.className = "row-despesa";
            else if (tipoLimpo === "investimento") tr.className = "row-investimento";
            else if (tipoLimpo === "reserva") tr.className = "row-reserva";
            else tr.className = "row-padrao";

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
            const dadosMes = row.meses[numMes] || { valor: null, pago: false };

            // Célula Valor
            const tdVal = document.createElement("td");
            const inputVal = document.createElement("input");
            inputVal.type = "number";
            inputVal.step = "0.01";
            inputVal.className = "cell-input cell-input-number";
            
            // Exibir vazio se o valor for null ou undefined (em branco)
            const valorExibido = (dadosMes.valor === null || dadosMes.valor === undefined) ? "" : (dadosMes.valor === 0 ? "0.00" : dadosMes.valor.toFixed(2));
            inputVal.value = valorExibido;

            inputVal.addEventListener("change", (e) => {
                let v = e.target.value === "" ? null : parseFloat(e.target.value);
                if (isNaN(v)) v = null;
                dadosPivotados[idxOriginal].meses[numMes].valor = v;
                e.target.value = (v === null || v === undefined) ? "" : (v === 0 ? "0.00" : v.toFixed(2));
                atualizarMetricas();
                atualizarGraficos();
            });
            tdVal.appendChild(inputVal);
            tr.appendChild(tdVal);

            // Célula Pago (Checkbox)
            const tdPago = document.createElement("td");
            tdPago.className = "td-pago";
            tdPago.style.textAlign = "left";
            tdPago.style.paddingLeft = "6px";
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

// Adicionar Linha Vazia
function adicionarLinha() {
    const novaLinha = {
        item: "",
        tipo: "",
        categoria: "",
        meses: {},
        isNew: true
    };
    
    // Inicializa meses com valor nulo (em branco) e pago=false
    for (let m = 1; m <= 12; m++) {
        novaLinha.meses[m] = { valor: null, pago: false };
    }
    
    dadosPivotados.push(novaLinha);
    renderizarTabelas();
    
    // Rola a tabela de edição para o topo para facilitar visualização
    setTimeout(() => {
        const container = document.querySelector("#tab-editar .table-container");
        if (container) container.scrollTop = 0;
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

// Atualiza os painéis de métrica (Saldo Atual, Saldo Projetado e totais do ano)
function atualizarMetricas() {
    const mesAtualNome = MESES_MAPA[new Date().getMonth() + 1];
    const isAnoCompleto = mesFiltrado === "Ano Completo";
    const mesAlvo = isAnoCompleto ? mesAtualNome : mesFiltrado;
    const numMesAlvo = MAPA_REVERSO_MES[mesAlvo];

    document.getElementById("label-saldo-atual").textContent = `${isAnoCompleto ? 'Mês atual' : mesAlvo}: Saldo Efetivo`;
    document.getElementById("label-saldo-projetado").textContent = `${isAnoCompleto ? 'Mês atual' : mesAlvo}: Saldo Projetado`;

    // --- Cards do mês atual ---
    let totalReceitaAtual = 0;
    let totalNaoReceitaAtual = 0;
    let totalReceitaProjetado = 0;
    let totalNaoReceitaProjetado = 0;

    dadosPivotados.forEach(row => {
        const dadosMes = row.meses[numMesAlvo] || { valor: 0.0, pago: false };
        const valor = parseFloat(dadosMes.valor) || 0.0;
        const pago = boolValue(dadosMes.pago);
        const tipo = row.tipo.trim().toLowerCase();

        if (pago) {
            if (tipo === "receita") totalReceitaAtual += valor;
            else totalNaoReceitaAtual += valor;
        }

        if (tipo === "receita") totalReceitaProjetado += valor;
        else totalNaoReceitaProjetado += valor;
    });

    const saldoAtual = totalReceitaAtual - totalNaoReceitaAtual;
    const saldoProjetado = totalReceitaProjetado - totalNaoReceitaProjetado;

    const valAtualEl = document.getElementById("val-saldo-atual");
    const valProjEl = document.getElementById("val-saldo-projetado");

    valAtualEl.textContent = formatarMoeda(saldoAtual);
    valProjEl.textContent = formatarMoeda(saldoProjetado);
    ajustarCorMetrica(valAtualEl, saldoAtual);
    ajustarCorMetrica(valProjEl, saldoProjetado);

    // Delta % do Saldo Projetado do mês vs mês anterior
    const deltaEl = document.getElementById('val-saldo-projetado-delta');
    if (isAnoCompleto && deltaEl) {
        let numMesPrev = numMesAlvo - 1;
        if (numMesPrev < 1) numMesPrev = 12;

        let prevReceita = 0, prevNaoReceita = 0;
        dadosPivotados.forEach(row => {
            const dadosPrev = row.meses[numMesPrev] || { valor: 0.0, pago: false };
            const v = parseFloat(dadosPrev.valor) || 0.0;
            const tipo = row.tipo.trim().toLowerCase();
            if (tipo === 'receita') prevReceita += v;
            else prevNaoReceita += v;
        });
        const prevProjetado = prevReceita - prevNaoReceita;
        let percent = null;
        if (Math.abs(prevProjetado) > 0.0001) {
            percent = ((saldoProjetado - prevProjetado) / Math.abs(prevProjetado)) * 100;
        }
        if (percent === null) {
            deltaEl.textContent = '—';
            deltaEl.title = `Comparado ao saldo projetado do mês anterior: ${formatarMoeda(prevProjetado)}`;
            deltaEl.classList.remove('positive', 'negative');
        } else {
            deltaEl.textContent = `${percent >= 0 ? '+' : ''}${percent.toFixed(1)}%`;
            deltaEl.title = `Comparado ao saldo projetado do mês anterior: ${formatarMoeda(prevProjetado)}\nAtual: ${formatarMoeda(saldoProjetado)} • Diferença: ${percent >= 0 ? '+' : ''}${percent.toFixed(1)}%`;
            deltaEl.classList.remove('positive', 'negative');
            deltaEl.classList.add(percent >= 0 ? 'positive' : 'negative');
        }
    } else if (deltaEl) {
        deltaEl.textContent = '';
        deltaEl.title = '';
        deltaEl.classList.remove('positive', 'negative');
    }

    // --- Cards Saldo Total do Ano (ignoram filtro de Mês) ---
    let anoReceitaProj = 0, anoNaoReceitaProj = 0;
    let anoReceitaEfet = 0, anoNaoReceitaEfet = 0;

    dadosPivotados.forEach(row => {
        const tipo = row.tipo.trim().toLowerCase();
        for (let m = 1; m <= 12; m++) {
            const dm = row.meses[m] || { valor: 0.0, pago: false };
            const v = parseFloat(dm.valor) || 0.0;
            const pago = boolValue(dm.pago);

            if (tipo === 'receita') anoReceitaProj += v;
            else anoNaoReceitaProj += v;

            if (pago) {
                if (tipo === 'receita') anoReceitaEfet += v;
                else anoNaoReceitaEfet += v;
            }
        }
    });

    const saldoAnoProj = anoReceitaProj - anoNaoReceitaProj;
    const saldoAnoEfet = anoReceitaEfet - anoNaoReceitaEfet;

    const valAnoProjEl = document.getElementById('val-saldo-ano-projetado');
    const valAnoEfetEl = document.getElementById('val-saldo-ano-efetivo');

    if (valAnoProjEl) {
        valAnoProjEl.textContent = formatarMoeda(saldoAnoProj);
        ajustarCorMetrica(valAnoProjEl, saldoAnoProj);
    }
    if (valAnoEfetEl) {
        valAnoEfetEl.textContent = formatarMoeda(saldoAnoEfet);
        ajustarCorMetrica(valAnoEfetEl, saldoAnoEfet);
    }

    // Delta % do Saldo Total do Ano Projetado vs Saldo Total do Ano Efetivo do ano anterior
    const deltaAnoEl = document.getElementById('val-saldo-ano-projetado-delta');
    if (deltaAnoEl) {
        if (dadosPivotadosAnoAnterior.length === 0) {
            deltaAnoEl.textContent = '';
            deltaAnoEl.title = '';
            deltaAnoEl.classList.remove('positive', 'negative');
        } else {
            // Calcula Saldo Total Efetivo do ano anterior
            let antReceitaEfet = 0, antNaoReceitaEfet = 0;
            dadosPivotadosAnoAnterior.forEach(row => {
                const tipo = row.tipo.trim().toLowerCase();
                for (let m = 1; m <= 12; m++) {
                    const dm = row.meses[m] || { valor: 0.0, pago: false };
                    const v = parseFloat(dm.valor) || 0.0;
                    if (boolValue(dm.pago)) {
                        if (tipo === 'receita') antReceitaEfet += v;
                        else antNaoReceitaEfet += v;
                    }
                }
            });
            const saldoAntEfet = antReceitaEfet - antNaoReceitaEfet;

            let percentAno = null;
            if (Math.abs(saldoAntEfet) > 0.0001) {
                percentAno = ((saldoAnoProj - saldoAntEfet) / Math.abs(saldoAntEfet)) * 100;
            }

            if (percentAno === null) {
                deltaAnoEl.textContent = '—';
                deltaAnoEl.title = `Comparado ao Saldo Total Efetivo de ${anoAtivo - 1}: ${formatarMoeda(saldoAntEfet)}`;
                deltaAnoEl.classList.remove('positive', 'negative');
            } else {
                deltaAnoEl.textContent = `${percentAno >= 0 ? '+' : ''}${percentAno.toFixed(1)}% vs ${anoAtivo - 1}`;
                deltaAnoEl.title = `Saldo Total do Ano Projetado (${anoAtivo}) comparado ao Saldo Total Efetivo de ${anoAtivo - 1}\nAno anterior efetivo: ${formatarMoeda(saldoAntEfet)}\nEste ano projetado: ${formatarMoeda(saldoAnoProj)}\nVariação: ${percentAno >= 0 ? '+' : ''}${percentAno.toFixed(1)}%`;
                deltaAnoEl.classList.remove('positive', 'negative');
                deltaAnoEl.classList.add(percentAno >= 0 ? 'positive' : 'negative');
            }
        }
    }
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
                    const dadosMes = row.meses[m] || { valor: null, pago: false };
                    const valorSalvo = (dadosMes.valor === null || dadosMes.valor === undefined) ? 0.0 : (parseFloat(dadosMes.valor) || 0.0);
                    
                    transacoesPlanas.push({
                        ano: anoAtivo,
                        mes: m,
                        item: row.item.trim(),
                        tipo: row.tipo.trim(),
                        categoria: row.categoria.trim(),
                        valor: valorSalvo,
                        pago: boolValue(dadosMes.pago)
                    });
                }
            }
        });

        const token = obterCookie("session_token");
        const response = await fetch(`/api/transactions/bulk-save?ano=${anoAtivo}`, {
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

// --- Gráficos (ex charts.js) ---
let chartMensalInstancia = null;
let chartRoscaInstancia = null;
let chartBarrasHInstancia = null;

const CORES_RGB = {
    "Receita": [46, 204, 113],
    "Despesa": [231, 76, 60],
    "Investimento": [52, 152, 219],
    "Reserva": [241, 196, 15]
};

const CORES_EXTRAS_RGB = [
    [155, 89, 182],
    [26, 188, 156],
    [230, 126, 34],
    [52, 73, 94]
];

function corTextoTema() {
    return getComputedStyle(document.body).getPropertyValue('--text-primary').trim() || '#f1f1f5';
}

function corTextoSecundarioTema() {
    return getComputedStyle(document.body).getPropertyValue('--text-secondary').trim() || '#9090a2';
}

function gerarCoresCategoriasDistintas(rgbBase, quantidade) {
    const cores = [];
    const opMax = 0.95;
    const opMin = 0.35;
    for (let i = 0; i < quantidade; i++) {
        const opacidade = quantidade === 1
            ? opMax
            : opMax - (i * (opMax - opMin) / (quantidade - 1));
        cores.push(`rgba(${rgbBase[0]}, ${rgbBase[1]}, ${rgbBase[2]}, ${opacidade.toFixed(2)})`);
    }
    return cores;
}

function obterCorTipoRGB(tipoStr, index = 0) {
    const busca = tipoStr.trim().charAt(0).toUpperCase() + tipoStr.trim().slice(1).toLowerCase();
    if (CORES_RGB[busca]) {
        return CORES_RGB[busca];
    }
    return CORES_EXTRAS_RGB[index % CORES_EXTRAS_RGB.length];
}

function atualizarGraficoMensal(transacoes, anoSelecionado) {
    const canvas = document.getElementById('chart-mensal');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const mesesAbreviados = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

    const dadosPorTipo = {
        "Receita": { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) },
        "Despesa": { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) },
        "Investimento": { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) },
        "Reserva": { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) }
    };

    const hoje = new Date();
    const mesAtualSistema = hoje.getMonth() + 1;
    const anoAtualSistema = hoje.getFullYear();

    transacoes.forEach(t => {
        const tipo = t.tipo.trim().charAt(0).toUpperCase() + t.tipo.trim().slice(1).toLowerCase();
        if (!dadosPorTipo[tipo]) {
            dadosPorTipo[tipo] = { efetivado: Array(12).fill(0), previsto: Array(12).fill(0) };
        }

        const idxMes = t.mes - 1;
        if (idxMes < 0 || idxMes > 11) return;

        const valor = parseFloat(t.valor) || 0.0;
        const pago = boolValue(t.pago);
        const isMesPassado = (anoSelecionado < anoAtualSistema) || (anoSelecionado === anoAtualSistema && t.mes < mesAtualSistema);

        if (pago) {
            dadosPorTipo[tipo].efetivado[idxMes] += valor;
        } else if (!isMesPassado) {
            dadosPorTipo[tipo].previsto[idxMes] += valor;
        }
    });

    const mediasAnuais = {};
    Object.keys(dadosPorTipo).forEach(tipo => {
        const totalEfetivado = dadosPorTipo[tipo].efetivado.reduce((a, b) => a + b, 0);
        const totalPrevisto = dadosPorTipo[tipo].previsto.reduce((a, b) => a + b, 0);
        mediasAnuais[tipo] = (totalEfetivado + totalPrevisto) / 12.0;
    });

    const datasets = [];
    let colorIdx = 0;

    Object.keys(dadosPorTipo).forEach(tipo => {
        const rgb = obterCorTipoRGB(tipo, colorIdx++);
        const corEfetivado = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 1.0)`;
        const corPrevisto = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 0.35)`;

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
            order: -1
        });
    });

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
                        color: corTextoTema(),
                        font: { family: 'Outfit', size: 12 },
                        filter: function(item) {
                            return !item.text.includes('(Previsto)');
                        }
                    }
                },
                tooltip: {
                    mode: 'x',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
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
                    grid: { color: 'rgba(128, 128, 128, 0.15)' },
                    ticks: { color: corTextoSecundarioTema(), font: { family: 'Outfit' } }
                },
                y: {
                    grid: { color: 'rgba(128, 128, 128, 0.15)' },
                    ticks: {
                        color: corTextoSecundarioTema(),
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

function atualizarGraficosDetalhamento(transacoes, tipoSelecionado, apenasPagos, mesFiltrado) {
    const canvasRosca = document.getElementById('chart-rosca');
    const canvasBarrasH = document.getElementById('chart-barras-h');
    if (!canvasRosca || !canvasBarrasH) return;

    const ctxRosca = canvasRosca.getContext('2d');
    const ctxBarrasH = canvasBarrasH.getContext('2d');
    const numMesFiltrado = MAPA_REVERSO_MES[mesFiltrado] || null;

    const transacoesFiltradas = transacoes.filter(t => {
        const tipoT = t.tipo.trim().charAt(0).toUpperCase() + t.tipo.trim().slice(1).toLowerCase();
        const tipoS = tipoSelecionado.trim().charAt(0).toUpperCase() + tipoSelecionado.trim().slice(1).toLowerCase();
        if (tipoT !== tipoS) return false;
        if (numMesFiltrado !== null && t.mes !== numMesFiltrado) return false;
        if (apenasPagos && !boolValue(t.pago)) return false;
        return true;
    });

    const categoriaSomas = {};
    transacoesFiltradas.forEach(t => {
        const cat = t.categoria.trim() || "Sem Categoria";
        const valor = parseFloat(t.valor) || 0.0;
        categoriaSomas[cat] = (categoriaSomas[cat] || 0) + valor;
    });

    const itemSomas = {};
    transacoesFiltradas.forEach(t => {
        const item = t.item.trim() || "Sem Nome";
        const valor = parseFloat(t.valor) || 0.0;
        itemSomas[item] = (itemSomas[item] || 0) + valor;
    });

    const labelsCategorias = Object.keys(categoriaSomas);
    const valoresCategorias = Object.values(categoriaSomas);
    const itensOrdenados = Object.entries(itemSomas)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15);
    const labelsItens = itensOrdenados.map(i => i[0]);
    const valoresItens = itensOrdenados.map(i => i[1]);
    const rgbBase = obterCorTipoRGB(tipoSelecionado);

    if (chartRoscaInstancia) chartRoscaInstancia.destroy();
    if (chartBarrasHInstancia) chartBarrasHInstancia.destroy();

    if (valoresCategorias.length === 0) return;

    const backgroundColorsRosca = gerarCoresCategoriasDistintas(rgbBase, labelsCategorias.length);
    const mapaCoresCategorias = {};
    labelsCategorias.forEach((cat, idx) => {
        mapaCoresCategorias[cat] = backgroundColorsRosca[idx];
    });

    chartRoscaInstancia = new Chart(ctxRosca, {
        type: 'doughnut',
        data: {
            labels: labelsCategorias,
            datasets: [{
                data: valoresCategorias,
                backgroundColor: backgroundColorsRosca,
                borderColor: 'rgba(128,128,128,0.15)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: corTextoTema(), font: { family: 'Outfit', size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.parsed;
                            const total = context.dataset.data.reduce((sum, dataValue) => sum + (typeof dataValue === 'number' ? dataValue : 0), 0);
                            const percent = total ? (val / total) * 100 : 0;
                            return ' ' + context.label + ': ' + new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val) + ' (' + percent.toFixed(1) + '%)';
                        }
                    }
                }
            }
        }
    });

    const coresBarrasH = labelsItens.map(itemLabel => {
        const transacaoDoItem = transacoesFiltradas.find(t => (t.item.trim() || "Sem Nome") === itemLabel);
        const categoriaDoItem = transacaoDoItem ? (transacaoDoItem.categoria.trim() || "Sem Categoria") : null;
        if (categoriaDoItem && mapaCoresCategorias[categoriaDoItem]) {
            return mapaCoresCategorias[categoriaDoItem];
        }
        return `rgba(${rgbBase[0]}, ${rgbBase[1]}, ${rgbBase[2]}, 0.85)`;
    });

    chartBarrasHInstancia = new Chart(ctxBarrasH, {
        type: 'bar',
        data: {
            labels: labelsItens,
            datasets: [{
                data: valoresItens,
                backgroundColor: coresBarrasH,
                borderColor: coresBarrasH,
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.x;
                            const total = context.dataset.data.reduce((sum, dataValue) => sum + (typeof dataValue === 'number' ? dataValue : 0), 0);
                            const percent = total ? (value / total) * 100 : 0;
                            return ' ' + new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value) + ' (' + percent.toFixed(1) + '%)';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(128, 128, 128, 0.15)' },
                    ticks: {
                        color: corTextoSecundarioTema(),
                        font: { family: 'Outfit' },
                        callback: function(value) {
                            return 'R$ ' + value.toLocaleString('pt-BR');
                        }
                    }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: corTextoTema(), font: { family: 'Outfit', size: 12 } }
                }
            }
        }
    });
}

// --- Investimentos (ex investments.js) ---
let investmentPortfolio = null;
let investmentDeviationChart = null;
let investmentSuggestions = [];

const GROUP_COLORS = [
    "#2ecc71", "#3498db", "#f1c40f", "#e74c3c",
    "#00d2d3", "#ff7f50", "#9b59b6", "#95a5a6"
];

function initInvestments() {
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
    };
}

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

// --- Inicialização unificada ---
document.addEventListener("DOMContentLoaded", () => {
    inicializarTema();
    inicializarSeletores();
    configurarEventListeners();
    initInvestments();
    verificarAutenticacao();
});
