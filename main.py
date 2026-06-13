"""Aplicação Streamlit para controle financeiro mensal.

Funcionalidades principais:
- Carrega/gera planilhas CSV por ano em formato despivotado (linhas por mês).
- Exibe um editor tabular para editar/ adicionar/ remover lançamentos.
- Salva os dados editados em `./csv/{ano}.csv` no formato original (despivotiado).
- Gera visualizações (barras empilhadas e médias) por tipo e status (Efetivado/Previsto).

Este arquivo contém funções auxiliares para carregar dados, mapear cores e
construir a interface e os gráficos com Streamlit e Plotly.
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import locale
import os
import hmac
from dotenv import load_dotenv
from datetime import datetime, timedelta
from streamlit_cookies_controller import CookieController

# Inicializa o controlador de cookies
controller = CookieController()

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")

# Tenta configurar localidade para formatação de datas em português do Brasil.
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.utf8")
except Exception:
    try:
        locale.setlocale(locale.LC_TIME, "portuguese_brazil")
    except Exception:
        # Se falhar, continua com localidade padrão do sistema.
        pass

MESES_MAPA = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}
MAPA_REVERSO_MES = {v: k for k, v in MESES_MAPA.items()}

PALETA_RGB = {
    "Receita": (46, 204, 113),      # Verde
    "Despesa": (231, 76, 60),       # Vermelho
    "Investimento": (52, 152, 219),  # Azul
    "Reserva": (241, 196, 15),       # Amarelo
}
CORES_EXTRAS = [
    (155, 89, 182),  # Roxo
    (26, 188, 156),  # Ciano
    (230, 126, 34),  # Laranja
    (52, 73, 94),    # Grafite
]

def obter_cor_tipo(tipo_str, index_reserva=0):
    """Retorna uma cor RGB para um `tipo` (Receita/Despesa/etc).

    Se o tipo estiver na paleta principal, usa-a; caso contrário, usa uma cor
    da lista de cores extras (rotacionada por `index_reserva`).
    """
    tipo_busca = str(tipo_str).strip().capitalize()
    if tipo_busca in PALETA_RGB:
        return PALETA_RGB[tipo_busca]
    return CORES_EXTRAS[index_reserva % len(CORES_EXTRAS)]

def carregar_ou_criar_df(ano_selecionado):
    """Carrega o CSV do ano se existir ou cria um DataFrame base para o ano.

    - Se existir `./csv/{ano}.csv`, carrega e garante a coluna `Pago`.
    - Caso não exista e o ano seja atual/futuro, tenta reutilizar o arquivo CSV
      mais recente como molde (ajustando o campo `Data` para o ano selecionado).
    - Se nenhum molde for encontrado, cria 12 linhas base (01/MM/ANO) com valores zerados.

    Retorna o DataFrame pivotado por Item/Tipo/Categoria com colunas dos meses
    e colunas auxiliares `{Mes} - Pago` para indicar realização.
    """
    caminho_pasta = Path("./csv")
    caminho_pasta.mkdir(parents=True, exist_ok=True)
    caminho_arquivo = caminho_pasta / f"{ano_selecionado}.csv"

    ano_atual_sistema = pd.Timestamp.now().year
    df = pd.DataFrame()

    # Se existir arquivo para o ano, carrega diretamente
    if caminho_arquivo.exists():
        df = pd.read_csv(caminho_arquivo)
        if 'Pago' not in df.columns:
            df['Pago'] = False
    else:
        # Tenta reutilizar o CSV mais recente como molde para anos atuais/ futuros
        if ano_selecionado >= ano_atual_sistema:
            arquivos_csv = [f for f in caminho_pasta.glob("*.csv") if f.stem.isdigit()]
            if arquivos_csv:
                arquivo_mais_recente = max(arquivos_csv, key=lambda x: int(x.stem))
                df_molde = pd.read_csv(arquivo_mais_recente)
                df_molde['Pago'] = False

                def atualizar_ano_string(data_str):
                    partes = str(data_str).split('/')
                    if len(partes) == 3:
                        return f"{partes[0]}/{partes[1]}/{ano_selecionado}"
                    return data_str

                df_molde['Data'] = df_molde['Data'].apply(atualizar_ano_string)
                df = df_molde

        # Se ainda estiver vazio, cria 12 linhas padrão (um por mês)
        if df.empty:
            for i in range(1, 13):
                nova_linha = pd.DataFrame(
                    [[f"01/{i:02d}/{ano_selecionado}", "", "", "", 0.0, False]],
                    columns=['Data', 'Item', 'Tipo', 'Categoria', 'Valor', 'Pago']
                )
                df = pd.concat([df, nova_linha], ignore_index=True)

    # Normaliza datas e cria coluna com nome do mês (abreviado)
    df['Data_DT'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
    df['Mes_Nome'] = df['Data_DT'].dt.month.map(MESES_MAPA)

    # Pivot: valores por mês e flags de pagamento por mês
    df_valor = df.pivot_table(index=['Item', 'Tipo', 'Categoria'], columns='Mes_Nome', values='Valor', aggfunc='sum').reset_index()
    df_pago = df.pivot_table(index=['Item', 'Tipo', 'Categoria'], columns='Mes_Nome', values='Pago', aggfunc='max').reset_index()

    colunas_meses = [col for col in df_valor.columns if col not in ['Item', 'Tipo', 'Categoria']]
    for col in colunas_meses:
        df_pago = df_pago.rename(columns={col: f"{col} - Pago"})

    df_pivotado = pd.merge(df_valor, df_pago, on=['Item', 'Tipo', 'Categoria'])

    # Reordena colunas para ficar Item/Tipo/Categoria, depois pares (Mês, Mês - Pago)
    colunas_finais = ['Item', 'Tipo', 'Categoria']
    meses_ordenados = [MESES_MAPA[i] for i in range(1, 13) if MESES_MAPA[i] in colunas_meses]
    for mes in meses_ordenados:
        colunas_finais.append(mes)
        colunas_finais.append(f"{mes} - Pago")

    df_pivotado = df_pivotado.reindex(columns=colunas_finais)
    return df_pivotado.fillna(0.0).astype({'Item': 'str', 'Tipo': 'str', 'Categoria': 'str'})

def propagar_valores_meses_seguintes(df, mes_origem):
    """Propaga valores do mês de origem para os meses seguintes onde estiverem zerados.

    Para cada linha do DataFrame pivotado:
    - Se o valor no `mes_origem` for > 0, percorre os meses posteriores.
    - Meses futuros com valor == 0.0 (ou NaN/vazio) recebem o valor do `mes_origem`.
    - A flag `{Mês} - Pago` dos meses preenchidos é setada como False (previsão).
    - Meses futuros que já possuam valor preenchido (> 0) são preservados.

    Args:
        df: DataFrame pivotado (colunas: Item, Tipo, Categoria, Jan, Jan - Pago, ...).
        mes_origem: Nome abreviado do mês de origem (ex: "Jan", "Fev").

    Returns:
        DataFrame com os valores propagados.
    """
    df_resultado = df.copy()
    num_mes_origem = MAPA_REVERSO_MES.get(mes_origem)
    if num_mes_origem is None:
        return df_resultado

    # Meses que vêm depois do mês de origem
    meses_futuros = [MESES_MAPA[i] for i in range(num_mes_origem + 1, 13)]
    if not meses_futuros:
        return df_resultado

    for idx in df_resultado.index:
        valor_origem = df_resultado.at[idx, mes_origem]
        # Trata NaN como zero
        if pd.isna(valor_origem):
            continue
        valor_origem = float(valor_origem)
        if valor_origem <= 0:
            continue

        for mes_futuro in meses_futuros:
            if mes_futuro not in df_resultado.columns:
                continue
            valor_futuro = df_resultado.at[idx, mes_futuro]
            # Só substitui se o mês futuro estiver zerado ou vazio
            if pd.isna(valor_futuro) or float(valor_futuro) == 0.0:
                df_resultado.at[idx, mes_futuro] = valor_origem
                col_pago = f"{mes_futuro} - Pago"
                if col_pago in df_resultado.columns:
                    df_resultado.at[idx, col_pago] = False

    return df_resultado

# --- AUTENTICAÇÃO ---
@st.dialog("🔐 Autenticação")
def dialog_autenticacao():
    """Diálogo modal para autenticação via token de acesso."""
    st.markdown("Informe o token de acesso para continuar.")
    token_input = st.text_input("Token:", type="password", key="token_input")
    if st.button("Entrar", type="primary", use_container_width=True):
        if token_input and hmac.compare_digest(token_input, ACCESS_TOKEN):
            # 1. Define o tempo de expiração (Ex: válido por 2 horas)
            validade = (datetime.now() + timedelta(hours=2)).isoformat()

            # 2. Salva no Cookie do navegador
            controller.set("token_validade", validade)

            # 3. Atualiza o session_state para resposta imediata
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Token inválido!")

def main():
    st.set_page_config(page_title="Controle Financeiro", page_icon="📊", layout="wide")

    # --- INICIO DA ROTINA DE BLOQUEIO ATUALIZADA ---
    # 1. Verifica se já está autenticado na sessão atual (evita ler o cookie toda hora)
    if not st.session_state.get("autenticado", False):

        # 2. Se não está no session_state, busca a informação no Cookie
        cookie_validade = controller.get("token_validade")

        if cookie_validade:
            try:
                # Converte o texto do cookie de volta para datetime
                data_expiracao = datetime.fromisoformat(cookie_validade)

                # 3. Se a data atual for menor que a expiração, revalida a sessão
                if datetime.now() < data_expiracao:
                    st.session_state.autenticado = True
                else:
                    # Token expirou, remove o cookie velho
                    controller.remove("token_validade")
            except ValueError:
                pass  # Trata erro caso o cookie esteja corrompido

    # 4. Se passou pelos testes e CONTINUA falso, abre o dialog
    if not st.session_state.get("autenticado", False):
        dialog_autenticacao()
        st.stop()
    # --- FIM DA ROTINA DE BLOQUEIO ---

    st.title("Controle Financeiro")

    col_ano, col_mes, col_vazio, col_metrics = st.columns(4)
    with col_ano:
        ano_atual = pd.Timestamp.now().year
        ano_selecionado = st.selectbox(
            "Selecione o Ano desejado:", 
            options=[ano_atual - 2, ano_atual - 1, ano_atual, ano_atual + 1], index=2
        )

    if "ano_ativo" not in st.session_state or st.session_state.ano_ativo != ano_selecionado:
        st.session_state.ano_ativo = ano_selecionado
        st.session_state.df_pivotado = carregar_ou_criar_df(ano_selecionado)
        if "df_editor_compras" in st.session_state:
            del st.session_state["df_editor_compras"]
            st.rerun()
    
    mes_atual_nome = MESES_MAPA[pd.Timestamp.now().month]
    coluna_pago_atual = f"{mes_atual_nome} - Pago"

    df_ordenado = st.session_state.df_pivotado.sort_values(
        by=['Tipo', coluna_pago_atual, mes_atual_nome, 'Categoria', 'Item'], 
        ascending=[False, True, False, False, True]
    ).reset_index(drop=True)

    # Reconstrói os dados caso haja edições em andamento no session_state do editor
    df_completo_atualizado = df_ordenado.copy()
    colunas_base = ['Item', 'Tipo', 'Categoria']
    estado_editor = st.session_state.get("df_editor_compras", {})

    if estado_editor:
        # 1. Aplica as células editadas (linhas existentes)
        if "edited_rows" in estado_editor:
            for idx, mudancas in estado_editor["edited_rows"].items():
                for col, valor in mudancas.items():
                    df_completo_atualizado.at[idx, col] = valor

        # 2. Captura e acopla as linhas NOVAS criadas pelo usuário
        if "added_rows" in estado_editor and estado_editor["added_rows"]:
            df_novas_linhas = pd.DataFrame(estado_editor["added_rows"])
            
            # Preenche colunas ausentes (meses ocultos no filtro) com valores padrão
            for col in df_ordenado.columns:
                if col not in df_novas_linhas.columns:
                    if " - Pago" in col:
                        df_novas_linhas[col] = False
                    elif col in colunas_base:
                        df_novas_linhas[col] = ""
                    else:
                        df_novas_linhas[col] = 0.0
                        
            df_novas_linhas = df_novas_linhas[df_ordenado.columns]
            df_completo_atualizado = pd.concat([df_completo_atualizado, df_novas_linhas], ignore_index=True)

        # 3. Remove linhas marcadas para exclusão
        if "deleted_rows" in estado_editor and estado_editor["deleted_rows"]:
            df_completo_atualizado = df_completo_atualizado.drop(estado_editor["deleted_rows"]).reset_index(drop=True)

    with col_mes:
        opcoes_mes = ["Ano Completo"] + [MESES_MAPA[i] for i in range(1, 13)]
        mes_filtrado = st.selectbox("Filtrar Visão da Tabela:", options=opcoes_mes, index=0)

    with col_metrics:
        col_metric, col_metric_previsto = st.columns(2)    
        with col_metric:
            colunas_base = ['Item', 'Tipo', 'Categoria']
            if mes_filtrado == "Ano Completo":
                colunas_para_exibir = list(df_ordenado.columns)
            else:
                colunas_para_exibir = colunas_base + [mes_filtrado, f"{mes_filtrado} - Pago"]
                
            # Define o mês alvo dinamicamente
            mes_alvo = mes_filtrado if mes_filtrado != "Ano Completo" else mes_atual_nome
            mes_pago_alvo = f"{mes_alvo} - Pago"
            
            df_metric = df_completo_atualizado[["Tipo", mes_alvo, mes_pago_alvo]]
            
            # CORREÇÃO: Filtra diretamente a coluna mes_alvo para a soma
            total_receita = df_metric[(df_metric["Tipo"] == "Receita") & (df_metric[mes_pago_alvo])][mes_alvo].sum()
            total_not_receita = df_metric[(df_metric["Tipo"] != "Receita") & (df_metric[mes_pago_alvo])][mes_alvo].sum()
            total_saldo = total_receita - total_not_receita
            
            st.metric(label=f"{mes_alvo}: Saldo Atual", value=f"R$ {total_saldo:,.2f}")
    
        with col_metric_previsto:
            colunas_base = ['Item', 'Tipo', 'Categoria']
            if mes_filtrado == "Ano Completo":
                colunas_para_exibir = list(df_ordenado.columns)
            else:
                colunas_para_exibir = colunas_base + [mes_filtrado, f"{mes_filtrado} - Pago"]
                
            mes_alvo = mes_filtrado if mes_filtrado != "Ano Completo" else mes_atual_nome
            mes_pago_alvo = f"{mes_alvo} - Pago"
            
            df_metric = df_completo_atualizado[["Tipo", mes_alvo, mes_pago_alvo]]
            
            # CORREÇÃO: Filtra diretamente a coluna mes_alvo para a soma projetada
            total_receita = df_metric[df_metric["Tipo"] == "Receita"][mes_alvo].sum()
            total_not_receita = df_metric[df_metric["Tipo"] != "Receita"][mes_alvo].sum()
            total_saldo = total_receita - total_not_receita
            
            st.metric(label=f"{mes_alvo}: Saldo Projetado", value=f"R$ {total_saldo:,.2f}")
        
    colunas_base = ['Item', 'Tipo', 'Categoria']
    if mes_filtrado == "Ano Completo":
        colunas_para_exibir = list(df_ordenado.columns)
    else:
        colunas_para_exibir = colunas_base + [mes_filtrado, f"{mes_filtrado} - Pago"]

    tab_editar, tab_visualizar = st.tabs(["📝 Editar Lançamentos", "🎨 Visualização Colorida"])

    with tab_editar:
        config_colunas = {}
        for col in df_ordenado.columns:
            if " - Pago" in col:
                config_colunas[col] = st.column_config.CheckboxColumn(col, default=False)
            elif col not in colunas_base:
                config_colunas[col] = st.column_config.NumberColumn(col, format="%.2f", default=0.0)

        # O editor agora renderiza a visão, mas monitoramos o dicionário de estado dele
        df_editado_visao = st.data_editor(
            df_ordenado[colunas_para_exibir],
            num_rows="dynamic",
            key="df_editor_compras",
            hide_index=True,
            column_config=config_colunas
        )

        col_btn_propagar, col_btn_salvar = st.columns(2)

        with col_btn_propagar:
            if mes_filtrado != "Ano Completo":
                if st.button("✨ Preencher meses seguintes", type="secondary", use_container_width=True):
                    df_propagado = propagar_valores_meses_seguintes(df_completo_atualizado, mes_filtrado)
                    st.session_state.df_pivotado = df_propagado
                    if "df_editor_compras" in st.session_state:
                        del st.session_state["df_editor_compras"]
                    st.rerun()

        with col_btn_salvar:
            salvar = st.button(f"Salvar Dados de {ano_selecionado}", type="primary", use_container_width=True)

        if salvar:
            # Processamento para salvar no CSV despivotado
            colunas_meses_puras = [MESES_MAPA[i] for i in range(1, 13)]
            linhas_despivotiadas = []
            
            for _, row in df_completo_atualizado.iterrows():
                for mes in colunas_meses_puras:
                    valor = row.get(mes, 0.0)
                    pago = row.get(f"{mes} - Pago", False)
                    num_mes = MAPA_REVERSO_MES[mes]
                    linhas_despivotiadas.append({
                        'Data': f"01/{num_mes:02d}/{ano_selecionado}", 'Item': row['Item'], 'Tipo': row['Tipo'],
                        'Categoria': row['Categoria'], 'Valor': valor, 'Pago': pago
                    })
            
            df_despivotado = pd.DataFrame(linhas_despivotiadas)
            df_despivotado = df_despivotado[(df_despivotado['Item'].str.strip() != "") | (df_despivotado['Tipo'].str.strip() != "") | (df_despivotado['Categoria'].str.strip() != "")]
            df_despivotado.drop_duplicates(inplace=True)
            
            caminho_salvar = Path(f"./csv/{ano_selecionado}.csv")
            df_despivotado.to_csv(caminho_salvar, index=False)
            
            st.session_state.df_pivotado = carregar_ou_criar_df(ano_selecionado)
            if "df_editor_compras" in st.session_state:
                del st.session_state["df_editor_compras"]
                st.rerun()

    with tab_visualizar:
        st.subheader("Planilha com Formatação Condicional")
        tipos_na_tabela = df_completo_atualizado['Tipo'].unique()
        mapa_cores_tabela = {tipo: obter_cor_tipo(tipo, i) for i, tipo in enumerate(tipos_na_tabela)}
        
        def colorir_linhas_dinamico(row):
            tipo = row['Tipo']
            rgb = mapa_cores_tabela.get(tipo, (255, 255, 255))
            return [f"background-color: rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.15); color: #000000;"] * len(row)

        df_estilizado = df_completo_atualizado[colunas_para_exibir].style.apply(colorir_linhas_dinamico, axis=1).format(precision=2)
        st.dataframe(df_estilizado, hide_index=True, use_container_width=True)

    # 5. CONSTRUÇÃO DO GRÁFICO
    hoje = pd.Timestamp.now()
    mes_atual_sistema = hoje.month
    ano_atual_sistema = hoje.year
    colunas_meses_puras = [MESES_MAPA[i] for i in range(1, 13)]
    
    dados_grafico = []
    for _, row in df_completo_atualizado.iterrows():
        tipo_bruto = str(row['Tipo']).strip()
        if tipo_bruto in ["", "None", "nan", "NaN"]: continue
        tipo = tipo_bruto.capitalize()
            
        for mes in colunas_meses_puras:
            num_mes = MAPA_REVERSO_MES[mes]
            valor = float(row.get(mes, 0.0))
            pago = bool(row.get(f"{mes} - Pago", False))
            
            is_mes_passado = (ano_selecionado < ano_atual_sistema) or (ano_selecionado == ano_atual_sistema and num_mes < mes_atual_sistema)
            
            status_realizacao = "Previsto"
            if pago:
                status_realizacao = "Efetivado"
            else:
                if is_mes_passado: valor = 0.0
            
            dados_grafico.append({'Mês': mes, 'Tipo': tipo, 'Status': status_realizacao, 'Valor': valor})
            
    df_plot = pd.DataFrame(dados_grafico)
    
    if not df_plot.empty and df_plot['Valor'].sum() > 0:
        df_plot_agrupado = df_plot.groupby(['Mês', 'Tipo', 'Status'])['Valor'].sum().reset_index()
        fig = go.Figure()
        ordem_meses_eixo = [MESES_MAPA[i] for i in range(1, 13)]
        
        tipos_unicos_grafico = df_plot_agrupado['Tipo'].unique()
        ordem_prioridade = {
            'Receita': 0,
            'Despesa': 1
        }

        tipos_unicos_grafico = sorted(
            tipos_unicos_grafico,
            key=lambda x: ordem_prioridade.get(x, 999)
        )
        
        for i, tipo in enumerate(tipos_unicos_grafico):
            rgb_base = obter_cor_tipo(tipo, i)
            cor_viva = f"rgb({rgb_base[0]}, {rgb_base[1]}, {rgb_base[2]})"
            cor_clara = f"rgba({rgb_base[0]}, {rgb_base[1]}, {rgb_base[2]}, 0.35)"
            
            for status in ['Efetivado', 'Previsto']:
                df_barra = df_plot_agrupado[(df_plot_agrupado['Tipo'] == tipo) & (df_plot_agrupado['Status'] == status)]
                df_barra = df_barra.set_index('Mês').reindex(ordem_meses_eixo).fillna(0.0).reset_index()
                
                cor_final = cor_viva if status == 'Efetivado' else cor_clara
                
                fig.add_trace(go.Bar(
                    x=df_barra['Mês'], y=df_barra['Valor'],
                    name=f"{tipo} ({status})",
                    marker_color=cor_final,
                    legendgroup=tipo,
                    offsetgroup=tipo
                ))
            
            total_ano_tipo = df_plot_agrupado[df_plot_agrupado['Tipo'] == tipo]['Valor'].sum()
            media_anual_tipo = total_ano_tipo / 12.0
            
            fig.add_trace(go.Scatter(
                x=ordem_meses_eixo, y=[media_anual_tipo] * 12,
                name=f"Média Anual {tipo}",
                line=dict(color=cor_viva, width=2, dash='dash'),
                mode='lines', legendgroup=tipo, showlegend=True
            ))

        fig.update_layout(
            barmode='stack', 
            xaxis_title="Meses", 
            yaxis_title="Total (R$)", 
            hovermode="x unified",
            yaxis=dict(
                tickformat=".2f",
                hoverformat=".2f"
            ),
            margin=dict(l=20, r=20, t=40, b=20), 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        # ... (Mantém o código do seu gráfico mensal atual intacto) ...
        st.plotly_chart(fig, use_container_width=True)
        
        # --- NOVA SEÇÃO: DETALHAMENTO (Tipo > Categoria > Item) ---
        st.markdown("---")
        st.subheader(f"🔍 Detalhamento Econômico: {mes_filtrado} ({ano_selecionado})")
        
        # Checkbox para filtrar apenas os lançamentos efetivados (pagos)
        apenas_pagos = st.checkbox("Filtrar apenas valores efetivados", value=True)
        
        # Prepara a base filtrada pelo mês selecionado para os novos gráficos
        dados_detalhe = []
        mes_alvo_filtro = mes_atual_nome if mes_filtrado == "Ano Completo" else mes_filtrado
        
        for _, row in df_completo_atualizado.iterrows():
            tipo_bruto = str(row['Tipo']).strip().capitalize()
            categoria_bruta = str(row['Categoria']).strip()
            item_bruto = str(row['Item']).strip()
            
            if tipo_bruto in ["", "None", "nan", "NaN"]: continue
            
            # Se for Ano Completo, varremos mês a mês aplicando o filtro do Checkbox individualmente
            if mes_filtrado == "Ano Completo":
                valor = 0.0
                for m in colunas_meses_puras:
                    pago_no_mes = bool(row.get(f"{m} - Pago", False))
                    # Se o checkbox estiver marcado, ignora o valor caso não esteja pago
                    if apenas_pagos and not pago_no_mes:
                        continue
                    valor += float(row.get(m, 0.0))
            else:
                # Se for mês específico, validamos a flag correspondente daquele mês
                pago_no_mes = bool(row.get(f"{mes_filtrado} - Pago", False))
                if apenas_pagos and not pago_no_mes:
                    valor = 0.0
                else:
                    valor = float(row.get(mes_filtrado, 0.0))
                
            if valor > 0:
                dados_detalhe.append({
                    'Tipo': tipo_bruto,
                    'Categoria': categoria_bruta if categoria_bruta else "Sem Categoria",
                    'Item': item_bruto if item_bruto else "Sem Item",
                    'Valor': valor
                })
                
        df_detalhe_base = pd.DataFrame(dados_detalhe)
        
        if not df_detalhe_base.empty:
            # Filtro interativo para explodir o Tipo
            tipos_disponiveis = df_detalhe_base['Tipo'].unique()
            tipo_selecionado = st.selectbox("Selecione o Tipo para explodir:", options=tipos_disponiveis)
            
            # Filtra os dados pelo tipo escolhido
            df_filtrado_tipo = df_detalhe_base[df_detalhe_base['Tipo'] == tipo_selecionado]
            
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.markdown(f"**Proporção por Categoria em {tipo_selecionado}**")
                df_cat = df_filtrado_tipo.groupby('Categoria')['Valor'].sum().reset_index()
                
                fig_rosca = go.Figure(data=[go.Pie(
                    labels=df_cat['Categoria'],
                    values=df_cat['Valor'],
                    hole=.4,
                    textinfo='percent+value',
                    insidetextorientation='radial',
                    marker=dict(colors=[f"rgba({obter_cor_tipo(tipo_selecionado)[0]}, {obter_cor_tipo(tipo_selecionado)[1]}, {obter_cor_tipo(tipo_selecionado)[2]}, {1 - (idx*0.15)})" for idx in range(len(df_cat))])
                )])
                fig_rosca.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_rosca, use_container_width=True)
                
            with col_graf2:
                st.markdown(f"**Ranking de Itens ({tipo_selecionado})**")
                df_item = df_filtrado_tipo.groupby('Item')['Valor'].sum().reset_index()
                df_item = df_item.sort_values(by='Valor', ascending=True) # Ascending True para o gráfico horizontal listar o maior no topo
                
                rgb_cor = obter_cor_tipo(tipo_selecionado)
                fig_barras_h = go.Figure(go.Bar(
                    x=df_item['Valor'],
                    y=df_item['Item'],
                    orientation='h',
                    marker_color=f"rgb({rgb_cor[0]}, {rgb_cor[1]}, {rgb_cor[2]})"
                ))
                fig_barras_h.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    xaxis=dict(tickformat=".2f"),
                    hovermode="y unified"
                )
                st.plotly_chart(fig_barras_h, use_container_width=True)
        else:
            st.info("Sem dados complementares para exibir o detalhamento neste período ou com os filtros selecionados.")
            
    else:
        st.info("Insira dados válidos no editor para renderizar o gráfico descritivo.")

if __name__ == "__main__":
    main()