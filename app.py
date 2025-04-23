import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from streamlit_dynamic_filters import DynamicFilters
from streamlit_plotly_events import plotly_events

# Configuração da página
st.set_page_config(page_title="Análise de Remuneração", layout="wide")

# --- Função de Carregamento de Dados com Tratamento Aprimorado ---
@st.cache_data
def load_data(url):
    """
    Carrega dados da URL fornecida com tratamento robusto de valores faltantes e conversão de tipos
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        df = pd.read_excel(io.BytesIO(response.content), sheet_name="fre_cia_aberta_remuneracao_maxi")
        
        # Conversão e tratamento de colunas numéricas
        numeric_cols = ['Receita', 'Valor_Medio_Remuneracao', 
                       'Valor_Maior_Remuneracao', 'Valor_Menor_Remuneracao']
        
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(df[col].median())
        
        # Tratamento de datas
        df['Ano'] = pd.to_datetime(df['Data_Fim_Exercicio_Social'], errors='coerce').dt.year
        df = df.dropna(subset=['Ano'])
        df['Ano'] = df['Ano'].astype(int)
        
        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

# --- Interface Principal ---
st.title("Dashboard Analítico: Remuneração vs Performance Corporativa")

# Carregar dados
github_url = "https://raw.githubusercontent.com/tovarich86/Remunera-oxReceita/main/remuneração%20faturamento.xlsx"
df = load_data(github_url)

if df is not None:
    try:
        # --- Barra Lateral com Filtros Avançados ---
        st.sidebar.header("Filtros Principais")
        
        # Filtro de Ano
        available_years = sorted(df["Ano"].unique(), reverse=True)
        selected_year = st.sidebar.selectbox("Ano", available_years)
        
        # Filtro de Receita com Slider
        min_rec, max_rec = int(df['Receita'].min()), int(df['Receita'].max())
        faixa_receita = st.sidebar.slider("Faixa de Receita (R$)", min_rec, max_rec, (min_rec, max_rec))
        df = df[(df['Receita'] >= faixa_receita[0]) & (df['Receita'] <= faixa_receita[1])]
        
        # Busca Textual
        termo_busca = st.sidebar.text_input("Buscar Empresa:")
        if termo_busca:
            df = df[df['Nome_Companhia'].str.contains(termo_busca, case=False)]
        
        st.sidebar.markdown(f"**Empresas encontradas:** {len(df)}")

        # --- Sistema de Abas ---
        tab1, tab2, tab3 = st.tabs(["Visualização", "Filtros Dinâmicos", "Gestão de Dados"])
        
        with tab1:
            # --- Gráfico Interativo ---
            st.subheader("Análise Multidimensional")
            
            # Seleção de eixos e cores
            col1, col2, col3 = st.columns(3)
            with col1:
                x_axis = st.selectbox("Eixo X", numeric_cols, index=0)
            with col2:
                y_axis = st.selectbox("Eixo Y", numeric_cols, index=1)
            with col3:
                color_by = st.selectbox("Colorir por", ['Setor de ativdade', 'Especie_Controle_Acionario', 'Nome_Companhia'])
            
            fig = px.scatter(df, x=x_axis, y=y_axis, color=color_by,
                            hover_data=['Nome_Companhia', 'ticker', 'Receita'],
                            template="plotly_white")
            
            # Interatividade
            selected_points = plotly_events(fig, select_event=True)
            if selected_points:
                selected_index = selected_points[0]['pointIndex']
                empresa = df.iloc[selected_index]
                with st.expander(f"Detalhes: {empresa['Nome_Companhia']}"):
                    st.markdown(f"""
                    **Ticker:** {empresa['ticker']}  
                    **Setor:** {empresa['Setor de ativdade']}  
                    **Receita:** R$ {empresa['Receita']:,.2f}  
                    **Remuneração Média:** R$ {empresa['Valor_Medio_Remuneracao']:,.2f}
                    """)
            
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # --- Filtros Dinâmicos ---
            st.header("Filtragem Avançada")
            dynamic_filters = DynamicFilters(df, filters=['Setor de ativdade', 'Especie_Controle_Acionario'])
            dynamic_filters.display_filters()

        with tab3:
            # --- Gestão de Dados ---
            st.header("Operações em Massa")
            
            # Seleção de empresas
            empresas = df['Nome_Companhia'].unique()
            selecionadas = st.multiselect("Selecionar empresas:", empresas)
            
            # Ações
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Exportar Seleção", help="Exportar empresas selecionadas para CSV"):
                    csv = df[df['Nome_Companhia'].isin(selecionadas)].to_csv(index=False)
                    st.download_button("Baixar CSV", csv, "dados_selecionados.csv")
            with col2:
                if st.button("Excluir Seleção", type="primary"):
                    df = df[~df['Nome_Companhia'].isin(selecionadas)]
                    st.success(f"{len(selecionadas)} empresas removidas!")

            # Visualização rápida
            st.dataframe(df.head(10), use_container_width=True)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")

else:
    st.error("Falha ao carregar dados. Verifique a conexão e a URL.")
