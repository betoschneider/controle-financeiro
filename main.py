from pathlib import Path
import pandas as pd
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import locale

try:
    locale.setlocale(locale.LC_TIME, "pt_BR.utf8")
except:
    try:
        locale.setlocale(locale.LC_TIME, "portuguese_brazil")
    except:
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
    tipo_busca = str(tipo_str).strip().capitalize()
    if tipo_busca in PALETA_RGB:
        return PALETA_RGB[tipo_busca]
    return CORES_EXTRAS[index_reserva % len(CORES_EXTRAS)]

def carregar_ou_criar_df(ano_selecionado):
    caminho_pasta = Path("./csv")
    caminho_pasta.mkdir(parents=True, exist_ok=True)
    caminho_arquivo = caminho_pasta / f"{ano_selecionado}.csv"
    
    ano_atual_sistema = pd.Timestamp.now().year
    df = pd.DataFrame()

    if caminho_arquivo.exists():
        df = pd.read_csv(caminho_arquivo)
        if 'Pago' not in df.columns: 
            df['Pago'] = False
    else:
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
        
        if df.empty:
            for i in range(1, 13):
                nova_linha = pd.DataFrame(
                    [[f"01/{i:02d}/{ano_selecionado}", "", "", "", 0.0, False]], 
                    columns=['Data', 'Item', 'Tipo', 'Categoria', 'Valor', 'Pago']
                )
                df = pd.concat([df, nova_linha], ignore_index=True)
            
    df['Data_DT'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
    df['Mes_Nome'] = df['Data_DT'].dt.month.map(MESES_MAPA)
    
    df_valor = df.pivot_table(index=['Item', 'Tipo', 'Categoria'], columns='Mes_Nome', values='Valor', aggfunc='sum').reset_index()
    df_pago = df.pivot_table(index=['Item', 'Tipo', 'Categoria'], columns='Mes_Nome', values='Pago', aggfunc='max').reset_index()
    
    colunas_meses = [col for col in df_valor.columns if col not in ['Item', 'Tipo', 'Categoria']]
    for col in colunas_meses:
        df_pago = df_pago.rename(columns={col: f"{col} - Pago"})
        
    df_pivotado = pd.merge(df_valor, df_pago, on=['Item', 'Tipo', 'Categoria'])
    
    colunas_finais = ['Item', 'Tipo', 'Categoria']
    meses_ordenados = [MESES_MAPA[i] for i in range(1, 13) if MESES_MAPA[i] in colunas_meses]
    for mes in meses_ordenados:
        colunas_finais.append(mes)
        colunas_finais.append(f"{mes} - Pago")
        
    df_pivotado = df_pivotado.reindex(columns=colunas_finais)
    return df_pivotado.fillna(0.0).astype({'Item': 'str', 'Tipo': 'str', 'Categoria': 'str'})

def main():
    st.set_page_config(page_title="Controle Financeiro Anual", page_icon="📊", layout="wide")
    st.title("Controle Financeiro Anual")

    col_ano, col_mes = st.columns(2)
    with col_ano:
        ano_atual = pd.Timestamp.now().year
        ano_selecionado = st.selectbox(
            "Selecione o Ano de Trabalho:", 
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

    with col_mes:
        opcoes_mes = ["Ano Completo"] + [MESES_MAPA[i] for i in range(1, 13)]
        mes_filtrado = st.selectbox("Filtrar Visão da Tabela:", options=opcoes_mes, index=0)

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

        if st.button(f"Salvar Dados de {ano_selecionado}", type="primary"):
            # CORREÇÃO CRÍTICA: Reconstrói o DataFrame completo combinando a tabela base com as mudanças do editor
            estado_editor = st.session_state["df_editor_compras"]
            
            # 1. Começamos com os dados antigos estruturados
            df_completo_atualizado = df_ordenado.copy()
            
            # 2. Aplica as células editadas (linhas existentes)
            if "edited_rows" in estado_editor:
                for idx, mudancas in estado_editor["edited_rows"].items():
                    for col, valor in mudancas.items():
                        df_completo_atualizado.at[idx, col] = valor

            # 3. Captura e acopla as linhas NOVAS criadas pelo usuário
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

            # 4. Remove linhas marcadas para exclusão
            if "deleted_rows" in estado_editor and estado_editor["deleted_rows"]:
                df_completo_atualizado = df_completo_atualizado.drop(estado_editor["deleted_rows"]).reset_index(drop=True)

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
        else:
            # Garante que a aba de visualização colorida acompanhe as edições em tempo de execução
            df_completo_atualizado = df_ordenado.copy()
            if "edited_rows" in st.session_state["df_editor_compras"]:
                for idx, mudancas in st.session_state["df_editor_compras"]["edited_rows"].items():
                    for col, valor in mudancas.items():
                        df_completo_atualizado.at[idx, col] = valor
            if "added_rows" in st.session_state["df_editor_compras"] and st.session_state["df_editor_compras"]["added_rows"]:
                df_novas_linhas = pd.DataFrame(st.session_state["df_editor_compras"]["added_rows"])
                for col in df_ordenado.columns:
                    if col not in df_novas_linhas.columns:
                        df_novas_linhas[col] = False if " - Pago" in col else ("" if col in colunas_base else 0.0)
                df_completo_atualizado = pd.concat([df_completo_atualizado, df_novas_linhas[df_ordenado.columns]], ignore_index=True)
            if "deleted_rows" in st.session_state["df_editor_compras"]:
                df_completo_atualizado = df_completo_atualizado.drop(st.session_state["df_editor_compras"]["deleted_rows"]).reset_index(drop=True)

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
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Insira dados válidos no editor para renderizar o gráfico descritivo.")

if __name__ == "__main__":
    main()