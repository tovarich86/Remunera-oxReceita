import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Remuneração x Receita", layout="wide")

# Carregar dados do arquivo Excel com tratamento correto para os valores nulos
@st.cache_data
def load_data():
    df = pd.read_excel("remuneracao-faturamento.xlsx", sheet_name="fre_cia_aberta_remuneracao_maxi")
    
    # Tratar valores "0" na coluna de controle acionário (substituir por valores vazios)
    df["Especie_Controle_Acionario"] = df["Especie_Controle_Acionario"].replace("0", "").replace(0, "")
    
    # Converter colunas numéricas para o tipo correto
    numeric_cols = ["Receita", "Valor_Medio_Remuneracao", "Valor_Maior_Remuneracao", "Valor_Menor_Remuneracao"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Converter datas e extrair ano
    df["Ano"] = pd.to_datetime(df["Data_Fim_Exercicio_Social"], errors="coerce").dt.year
    
    # Converter Receita para bilhões para facilitar visualização
    df["Receita_Bi"] = df["Receita"] / 1000
    
    return df

df = load_data()

st.title("Remuneração vs Receita")

# Painel de Filtros - Layout em 3 colunas
col1, col2, col3 = st.columns([1,1,1])

with col1:
    # Ano - Seleção simples
    anos_disponiveis = sorted(df["Ano"].dropna().unique())
    ano = st.selectbox("Ano", anos_disponiveis, index=len(anos_disponiveis)-1 if anos_disponiveis else 0)

with col2:
    # Órgão administrativo - Seleção simples
    orgaos = sorted(df["Orgao_Administracao"].dropna().unique())
    orgao = st.selectbox("Órgão Administrativo", orgaos, index=0)

with col3:
    # Tipo de remuneração - Rádio
    tipo_rem = st.radio(
        "Tipo de Remuneração",
        ["Média", "Máxima", "Mínima"],
        horizontal=True
    )

# Filtro por Receita (em bilhões)
st.subheader("Filtrar por Receita (em bilhões R$)")
# Obter limites de receita para o slider
receita_min = float(df["Receita_Bi"].min())
receita_max = float(df["Receita_Bi"].max())
# Arredondar para facilitar a visualização
receita_min = max(0, np.floor(receita_min))
receita_max = np.ceil(receita_max)

# Slider para seleção de faixa de receita
faixa_receita = st.slider(
    "Faixa de Receita", 
    min_value=receita_min,
    max_value=receita_max,
    value=(receita_min, receita_max),
    step=0.5
)

# Filtro principal com abordagem incremental
st.subheader("Selecionar Empresas")

# Tabs para diferentes tipos de filtro
filtro_tab = st.tabs(["Por Setor", "Por Controle Acionário", "Por Empresa Individual"])

# Filtragem inicial pelo ano e órgão
df_base = df[(df["Ano"] == ano) & (df["Orgao_Administracao"] == orgao)]
df_base = df_base[(df_base["Receita_Bi"] >= faixa_receita[0]) & (df_base["Receita_Bi"] <= faixa_receita[1])]

# Tab 1: Filtro por Setor
with filtro_tab[0]:
    col1_setor, col2_setor = st.columns([1,1])
    
    with col1_setor:
        # Lista de todos os setores disponíveis
        setores = sorted(df_base["Setor de ativdade"].dropna().unique())
        # Campo de busca para facilitar encontrar setores específicos
        busca_setor = st.text_input("Buscar Setor", key="busca_setor")
        
        # Filtrar setores baseado na busca
        if busca_setor:
            setores_filtrados = [s for s in setores if busca_setor.lower() in s.lower()]
        else:
            setores_filtrados = setores
            
        # Opção para selecionar/desselecionar todos
        if setores_filtrados:
            select_all_setores = st.checkbox("Selecionar Todos os Setores", key="all_setores")
            setores_selecionados = st.multiselect(
                "Selecione os Setores",
                options=setores_filtrados,
                default=setores_filtrados if select_all_setores else []
            )
        else:
            st.write("Nenhum setor encontrado com esse termo")
            setores_selecionados = []
    
    with col2_setor:
        # Mostrar empresas do(s) setor(es) selecionado(s) e permitir exclusões
        if setores_selecionados:
            empresas_dos_setores = df_base[df_base["Setor de ativdade"].isin(setores_selecionados)]["Nome_Companhia"].unique()
            empresas_dos_setores = sorted(empresas_dos_setores)
            
            st.write(f"Empresas dos setores selecionados: {len(empresas_dos_setores)}")
            
            # Campo de busca para empresas
            busca_empresa_setor = st.text_input("Buscar Empresa", key="busca_empresa_setor")
            
            # Filtrar empresas baseado na busca
            if busca_empresa_setor:
                empresas_filtradas = [e for e in empresas_dos_setores if busca_empresa_setor.lower() in e.lower()]
            else:
                empresas_filtradas = empresas_dos_setores
            
            # Empresas a serem excluídas do filtro
            empresas_excluidas = st.multiselect(
                "Selecione empresas para EXCLUIR",
                options=empresas_filtradas,
                default=[]
            )
        else:
            st.write("Selecione setores para ver empresas")
            empresas_excluidas = []

# Tab 2: Filtro por Controle Acionário
with filtro_tab[1]:
    col1_controle, col2_controle = st.columns([1,1])
    
    with col1_controle:
        # Lista de todos os tipos de controle acionário
        controles = sorted(df_base["Especie_Controle_Acionario"].dropna().unique())
        controles = [c for c in controles if c.strip() != ""]  # Remover valores vazios
        
        # Selecionar tipos de controle
        select_all_controles = st.checkbox("Selecionar Todos os Controles", key="all_controles")
        controles_selecionados = st.multiselect(
            "Selecione os Tipos de Controle Acionário",
            options=controles,
            default=controles if select_all_controles else []
        )
    
    with col2_controle:
        # Mostrar empresas do(s) controle(s) selecionado(s) e permitir exclusões
        if controles_selecionados:
            empresas_dos_controles = df_base[df_base["Especie_Controle_Acionario"].isin(controles_selecionados)]["Nome_Companhia"].unique()
            empresas_dos_controles = sorted(empresas_dos_controles)
            
            st.write(f"Empresas com controles selecionados: {len(empresas_dos_controles)}")
            
            # Campo de busca para empresas
            busca_empresa_controle = st.text_input("Buscar Empresa", key="busca_empresa_controle")
            
            # Filtrar empresas baseado na busca
            if busca_empresa_controle:
                empresas_filtradas_controle = [e for e in empresas_dos_controles if busca_empresa_controle.lower() in e.lower()]
            else:
                empresas_filtradas_controle = empresas_dos_controles
            
            # Empresas a serem excluídas do filtro
            empresas_excluidas_controle = st.multiselect(
                "Selecione empresas para EXCLUIR",
                options=empresas_filtradas_controle,
                default=[]
            )
        else:
            st.write("Selecione tipos de controle para ver empresas")
            empresas_excluidas_controle = []

# Tab 3: Filtro por Empresa Individual
with filtro_tab[2]:
    # Lista de todas as empresas disponíveis
    todas_empresas = sorted(df_base["Nome_Companhia"].dropna().unique())
    
    # Campo de busca para empresas
    busca_empresa_individual = st.text_input("Buscar Empresa", key="busca_empresa_individual")
    
    # Filtrar empresas baseado na busca
    if busca_empresa_individual:
        empresas_filtradas_individual = [e for e in todas_empresas if busca_empresa_individual.lower() in e.lower()]
    else:
        empresas_filtradas_individual = todas_empresas
    
    # Selecionar empresas individuais
    empresas_selecionadas = st.multiselect(
        "Selecione as Empresas",
        options=empresas_filtradas_individual,
        default=[]
    )

# Aplicar os filtros conforme a tab selecionada
st.subheader("Resultado da Filtragem")

# Determinar qual conjunto de filtros está ativo
if setores_selecionados:
    # Filtro por Setor está ativo
    df_filtrado = df_base[df_base["Setor de ativdade"].isin(setores_selecionados)]
    # Excluir empresas selecionadas
    if empresas_excluidas:
        df_filtrado = df_filtrado[~df_filtrado["Nome_Companhia"].isin(empresas_excluidas)]
    filtro_ativo = "setor"
elif controles_selecionados:
    # Filtro por Controle Acionário está ativo
    df_filtrado = df_base[df_base["Especie_Controle_Acionario"].isin(controles_selecionados)]
    # Excluir empresas selecionadas
    if empresas_excluidas_controle:
        df_filtrado = df_filtrado[~df_filtrado["Nome_Companhia"].isin(empresas_excluidas_controle)]
    filtro_ativo = "controle"
elif empresas_selecionadas:
    # Filtro por Empresa Individual está ativo
    df_filtrado = df_base[df_base["Nome_Companhia"].isin(empresas_selecionadas)]
    filtro_ativo = "empresa"
else:
    # Nenhum filtro ativo
    df_filtrado = df_base
    filtro_ativo = "nenhum"

# Seleciona a coluna de remuneração
if tipo_rem == "Média":
    col_rem = "Valor_Medio_Remuneracao"
elif tipo_rem == "Máxima":
    col_rem = "Valor_Maior_Remuneracao"
else:
    col_rem = "Valor_Menor_Remuneracao"

# Remove linhas sem remuneração ou receita
df_plot = df_filtrado.dropna(subset=[col_rem, "Receita"])

# Resumo das empresas no dataset filtrado
st.write(f"Empresas no gráfico: {len(df_plot['Nome_Companhia'].unique())}")

# Gráfico de dispersão
if not df_plot.empty:
    # Define cor por categoria com base no filtro ativo
    if filtro_ativo == "setor":
        color_col = "Setor de ativdade"
    elif filtro_ativo == "controle":
        color_col = "Especie_Controle_Acionario"
    else:
        color_col = "Nome_Companhia"

    fig = px.scatter(
        df_plot,
        x="Receita_Bi",
        y=col_rem,
        color=color_col,
        hover_name="Nome_Companhia",
        hover_data={
            "ticker": True,
            "Setor de ativdade": True,
            "Especie_Controle_Acionario": True,
            "Receita_Bi": ":.2f",
            col_rem: ":.2f"
        },
        labels={
            "Receita_Bi": "Receita (Bilhões R$)",
            col_rem: f"Remuneração {tipo_rem} (R$)"
        },
        title=f"Remuneração {tipo_rem} da Administração vs Receita ({ano}) - {orgao}",
        template="plotly_white"
    )

    # Linha de tendência (OLS)
    try:
        import statsmodels.api as sm
        
        if len(df_plot) > 1:
            fig_trend = px.scatter(
                df_plot,
                x="Receita_Bi",
                y=col_rem,
                trendline="ols"
            )
            fig.add_traces(fig_trend.data[1:2])  # Adiciona apenas a linha de tendência
    except ImportError:
        st.info("Para exibir a linha de tendência, instale o pacote 'statsmodels'")
    except Exception as e:
        st.warning(f"Não foi possível calcular a linha de tendência: {str(e)}")

    fig.update_traces(marker=dict(size=16, opacity=0.8), selector=dict(mode='markers'))
    fig.update_layout(height=600)

    st.plotly_chart(fig, use_container_width=True)

    # Exibe tabela dos dados filtrados
    with st.expander("Ver dados utilizados"):
        st.dataframe(df_plot[["Nome_Companhia", "ticker", "Setor de ativdade", 
                           "Especie_Controle_Acionario", "Receita_Bi", col_rem]])

else:
    st.warning("Não há dados disponíveis para os filtros selecionados.")
