import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

st.set_page_config(page_title="Remuneração x Receita", layout="wide")

# Função para carregar e preparar os dados diretamente do GitHub
@st.cache_data
def load_data():
    # URL para a versão raw do arquivo no GitHub
    url = "https://raw.githubusercontent.com/tovarich86/Remunera-oxReceita/main/remuneração%20faturamento.xlsx"
    
    # Baixar o arquivo
    response = requests.get(url)
    
    # Carregar o Excel a partir dos bytes
    df = pd.read_excel(io.BytesIO(response.content), sheet_name="fre_cia_aberta_remuneracao_maxi")
    
    # Converter dados para formatos corretos
    df["Ano"] = pd.to_datetime(df["Data_Fim_Exercicio_Social"], errors="coerce").dt.year
    
    return df

# Carregar os dados
try:
    df = load_data()
    st.title("Remuneração Média da Administração vs Receita")
    
    # Filtros principais
    col1, col2, col3, col4 = st.columns([1,1,1,2])

    with col1:
        ano = st.selectbox("Ano", sorted(df["Ano"].dropna().unique()), index=0)

    with col2:
        orgao = st.selectbox("Órgão Administrativo", sorted(df["Orgao_Administracao"].dropna().unique()), index=0)

    with col3:
        tipo_rem = st.radio(
            "Tipo de Remuneração",
            ["Média", "Máxima", "Mínima"],
            horizontal=True
        )

    with col4:
        filtro = st.radio("Filtrar por", ["Nenhum", "Setor de Atividade", "Controle Acionário", "Empresa"], horizontal=True)

    # Filtros dinâmicos
    df_filt = df[df["Ano"] == ano]
    df_filt = df_filt[df_filt["Orgao_Administracao"] == orgao]

    if filtro == "Setor de Atividade":
        setores = sorted(df_filt["Setor de ativdade"].dropna().unique())
        setores_sel = st.multiselect("Selecione o(s) Setor(es)", setores, default=setores)
        df_filt = df_filt[df_filt["Setor de ativdade"].isin(setores_sel)]
    elif filtro == "Controle Acionário":
        controles = sorted(df_filt["Especie_Controle_Acionario"].dropna().unique())
        controles_sel = st.multiselect("Selecione o(s) Controle(s)", controles, default=controles)
        df_filt = df_filt[df_filt["Especie_Controle_Acionario"].isin(controles_sel)]
    elif filtro == "Empresa":
        empresas = sorted(df_filt["Nome_Companhia"].dropna().unique())
        empresas_sel = st.multiselect("Selecione a(s) Empresa(s)", empresas, default=empresas)
        df_filt = df_filt[df_filt["Nome_Companhia"].isin(empresas_sel)]

    # Seleciona a coluna de remuneração
    if tipo_rem == "Média":
        col_rem = "Valor_Medio_Remuneracao"
    elif tipo_rem == "Máxima":
        col_rem = "Valor_Maior_Remuneracao"
    else:
        col_rem = "Valor_Menor_Remuneracao"

    # Remove linhas sem remuneração ou receita
    df_plot = df_filt.dropna(subset=[col_rem, "Receita"])

    # Define cor por categoria
    if filtro == "Setor de Atividade":
        color_col = "Setor de ativdade"
    elif filtro == "Controle Acionário":
        color_col = "Especie_Controle_Acionario"
    else:
        color_col = "Nome_Companhia"

    # Gráfico de dispersão
    if not df_plot.empty:
        fig = px.scatter(
            df_plot,
            x="Receita",
            y=col_rem,
            color=color_col if filtro != "Nenhum" else None,
            hover_name="Nome_Companhia",
            hover_data={
                "ticker": True,
                "Setor de ativdade": True,
                "Especie_Controle_Acionario": True,
                "Receita": ":.2f",
                col_rem: ":.2f"
            },
            labels={
                "Receita": "Receita (R$ milhões)",
                col_rem: f"Remuneração {tipo_rem} (R$)"
            },
            title=f"Remuneração {tipo_rem} da Administração vs Receita ({ano}) - {orgao}",
            template="simple_white"
        )

        # Linha de tendência (OLS)
        if len(df_plot) > 1:
            fig_trend = px.scatter(
                df_plot,
                x="Receita",
                y=col_rem,
                trendline="ols"
            )
            fig.add_traces(fig_trend.data[1:2])  # Adiciona apenas a linha de tendência

        fig.update_traces(marker=dict(size=16, opacity=0.8), selector=dict(mode='markers'))
        fig.update_layout(height=600)

        st.plotly_chart(fig, use_container_width=True)

        # Exibe tabela dos dados filtrados
        with st.expander("Ver dados utilizados"):
            st.dataframe(df_plot[["Nome_Companhia", "ticker", "Setor de ativdade", "Especie_Controle_Acionario", "Receita", col_rem]])

        st.caption("Fonte: Dados públicos de remuneração e receita das companhias abertas.")
    else:
        st.warning("Não há dados disponíveis para os filtros selecionado.")
