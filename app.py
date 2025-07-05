import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# Configurações da página
st.set_page_config(page_title="Análise de Remuneração e Faturamento", layout="wide")

# Função para carregar dados de uma URL do GitHub (para o arquivo original .xlsx)
@st.cache_data
def load_excel_sheet_data(url, sheet_name):
    """
    Carrega dados de uma planilha específica de um arquivo Excel hospedado no GitHub.
    Processa a coluna de data para extrair o ano.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Levanta um erro para respostas HTTP ruins (4xx ou 5xx)
        df = pd.read_excel(io.BytesIO(response.content), sheet_name=sheet_name)
        df["Ano"] = pd.to_datetime(df["Data_Fim_Exercicio_Social"], errors="coerce").dt.year
        df.dropna(subset=["Ano"], inplace=True)
        df["Ano"] = df["Ano"].astype(int)
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar o arquivo do GitHub: {e}")
        return None
    except FileNotFoundError:
        st.error(f"Erro: Aba '{sheet_name}' não encontrada no arquivo Excel.")
        return None
    except KeyError as e:
        st.error(f"Erro: Coluna esperada não encontrada no arquivo: {e}. Verifique o arquivo de origem.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar os dados do Excel: {e}")
        return None

# Função para carregar dados de arquivos CSV de uma URL do GitHub
@st.cache_data
def load_csv_data(url, delimiter=';'):
    """
    Carrega dados de um arquivo CSV hospedado no GitHub.
    Processa a coluna de data para extrair o ano.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Levanta um erro para respostas HTTP ruins (4xx ou 5xx)
        # Decodifica o conteúdo da resposta para string e usa io.StringIO para ler como CSV
        df_raw = pd.read_csv(io.StringIO(response.content.decode('utf-8')), delimiter=delimiter)

        # Padroniza nomes de colunas para facilitar o merge e a análise
        df_raw.columns = [col.replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').strip() for col in df_raw.columns]

        # Tenta extrair o ano da coluna 'Data_Fim_Exercicio_Social' ou 'Data_Referencia'
        if 'Data_Fim_Exercicio_Social' in df_raw.columns:
            df_raw["Ano"] = pd.to_datetime(df_raw["Data_Fim_Exercicio_Social"], errors="coerce").dt.year
        elif 'Data_Referencia' in df_raw.columns:
            df_raw["Ano"] = pd.to_datetime(df_raw["Data_Referencia"], errors="coerce").dt.year
        else:
            st.warning(f"Coluna de data não encontrada em {url}. A análise por ano pode ser limitada.")
            df_raw["Ano"] = None # Define como None se nenhuma coluna de data for encontrada

        if "Ano" in df_raw.columns:
            df_raw.dropna(subset=["Ano"], inplace=True)
            df_raw["Ano"] = df_raw["Ano"].astype(int)

        return df_raw
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar o arquivo CSV do GitHub ({url}): {e}")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar os dados de '{url}': {e}")
        return None

st.title("Análise de Remuneração e Faturamento de Companhias Abertas")

# URL base do repositório GitHub
github_base_url = "https://raw.githubusercontent.com/tovarich86/Remunera-oxReceita/main/"

# Carregar o arquivo original de remuneração vs faturamento
df_remuneracao_faturamento = load_excel_sheet_data(f"{github_base_url}remuneração%20faturamento.xlsx", sheet_name="fre_cia_aberta_remuneracao_maxi")

# Carregar os novos arquivos CSV do GitHub
df_remuneracao_max_min_media = load_csv_data(f"{github_base_url}fre_cia_aberta_remuneracao_maxima_minima_media_2025.csv")
df_remuneracao_total_orgao = load_csv_data(f"{github_base_url}fre_cia_aberta_remuneracao_total_orgao_2025.csv")
df_remuneracao_variavel = load_csv_data(f"{github_base_url}fre_cia_aberta_remuneracao_variavel_2025.csv")

# Verificar se todos os dataframes foram carregados com sucesso
if df_remuneracao_faturamento is None or \
   df_remuneracao_max_min_media is None or \
   df_remuneracao_total_orgao is None or \
   df_remuneracao_variavel is None:
    st.error("Não foi possível carregar todos os dados necessários. Verifique os arquivos e tente novamente.")
else:
    # Combinar anos disponíveis de todos os dataframes para o filtro global de ano
    all_years = pd.concat([
        df_remuneracao_faturamento['Ano'],
        df_remuneracao_max_min_media['Ano'],
        df_remuneracao_total_orgao['Ano'],
        df_remuneracao_variavel['Ano']
    ]).dropna().unique()
    available_years = sorted(all_years, reverse=True)

    st.sidebar.header("Filtros Principais")
    selected_year = st.sidebar.selectbox("Ano", available_years, index=0)

    # Filtrar dataframes pelo ano selecionado
    df_faturamento_filtered = df_remuneracao_faturamento[df_remuneracao_faturamento["Ano"] == selected_year].copy()
    df_max_min_media_filtered = df_remuneracao_max_min_media[df_remuneracao_max_min_media["Ano"] == selected_year].copy()
    df_total_orgao_filtered = df_remuneracao_total_orgao[df_remuneracao_total_orgao["Ano"] == selected_year].copy()
    df_variavel_filtered = df_remuneracao_variavel[df_remuneracao_variavel["Ano"] == selected_year].copy()

    # --- Seção 1: Análise Original (Remuneração vs Receita) ---
    st.header("1. Remuneração da Administração vs Receita da Companhia")

    if not df_faturamento_filtered.empty:
        available_organs_faturamento = sorted(df_faturamento_filtered["Orgao_Administracao"].dropna().unique())
        selected_organ_faturamento = st.sidebar.selectbox("Órgão Administrativo (Faturamento)", available_organs_faturamento, index=0)

        selected_rem_type = st.sidebar.radio(
            "Tipo de Remuneração (Faturamento)",
            ["Média", "Máxima", "Mínima"],
            horizontal=True
        )

        df_plot_faturamento = df_faturamento_filtered[
            (df_faturamento_filtered["Orgao_Administracao"] == selected_organ_faturamento)
        ].copy()

        if selected_rem_type == "Média":
            remuneration_col = "Valor_Medio_Remuneracao"
        elif selected_rem_type == "Máxima":
            remuneration_col = "Valor_Maior_Remuneracao"
        else:
            remuneration_col = "Valor_Menor_Remuneracao"

        required_cols_faturamento = [remuneration_col, "Receita", "Nome_Companhia", "ticker", "Setor_de_ativdade", "Especie_Controle_Acionario"]
        df_plot_faturamento = df_plot_faturamento.dropna(subset=[remuneration_col, "Receita"]).copy()

        if not df_plot_faturamento.empty:
            fig_faturamento = px.scatter(
                df_plot_faturamento,
                x="Receita",
                y=remuneration_col,
                color="Setor_de_ativdade",
                hover_name="Nome_Companhia",
                hover_data={"Nome_Companhia": True, "ticker": True, "Setor_de_ativdade": True, "Especie_Controle_Acionario": True, "Receita": ':.2f', remuneration_col: ':.2f'},
                labels={
                    "Receita": "Receita (R$ Bi)",
                    remuneration_col: f"Remuneração {selected_rem_type} (R$)",
                    "Setor_de_ativdade": "Setor de Atividade"
                },
                title=f"Remuneração {selected_rem_type} vs Receita ({selected_year}, {selected_organ_faturamento})",
                template="simple_white"
            )
            fig_faturamento.update_traces(marker=dict(size=12, opacity=0.8), selector=dict(mode='markers'))
            fig_faturamento.update_layout(height=600)
            st.plotly_chart(fig_faturamento, use_container_width=True)
        else:
            st.warning("Não há dados de faturamento disponíveis para os filtros selecionados.")
    else:
        st.warning("Não há dados de faturamento disponíveis para o ano selecionado.")

    # --- Seção 2: Análise de Bônus e Participação ---
    st.header("2. Análise de Bônus e Participação")

    if not df_variavel_filtered.empty:
        # Filtrar apenas a Diretoria Estatutária para bônus e participação, pois geralmente é onde se aplica
        df_variavel_diretoria = df_variavel_filtered[df_variavel_filtered["Orgao_Administracao"] == "Diretoria Estatutária"].copy()

        if not df_variavel_diretoria.empty:
            # Converter colunas de bônus e participação para numérico
            df_variavel_diretoria['Bonus_Valor_Efetivo'] = pd.to_numeric(df_variavel_diretoria['Bonus_Valor_Efetivo'], errors='coerce').fillna(0)
            df_variavel_diretoria['Participacao_Valor_Efetivo'] = pd.to_numeric(df_variavel_diretoria['Participacao_Valor_Efetivo'], errors='coerce').fillna(0)

            # Calcular o total de bônus e participação por empresa
            df_bonus_participacao_empresa = df_variavel_diretoria.groupby('Nome_Companhia').agg(
                Total_Bonus=('Bonus_Valor_Efetivo', 'sum'),
                Total_Participacao=('Participacao_Valor_Efetivo', 'sum')
            ).reset_index()

            st.subheader(f"Distribuição de Bônus e Participação ({selected_year})")

            # Histograma/Box plot para o range de bônus
            fig_bonus_range = px.histogram(
                df_variavel_diretoria[df_variavel_diretoria['Bonus_Valor_Efetivo'] > 0],
                x='Bonus_Valor_Efetivo',
                title='Distribuição do Valor Efetivo de Bônus',
                labels={'Bonus_Valor_Efetivo': 'Valor do Bônus (R$)'},
                template="simple_white"
            )
            st.plotly_chart(fig_bonus_range, use_container_width=True)

            # Histograma/Box plot para o range de participação
            fig_participacao_range = px.histogram(
                df_variavel_diretoria[df_variavel_diretoria['Participacao_Valor_Efetivo'] > 0],
                x='Participacao_Valor_Efetivo',
                title='Distribuição do Valor Efetivo de Participação',
                labels={'Participacao_Valor_Efetivo': 'Valor da Participação (R$)'},
                template="simple_white"
            )
            st.plotly_chart(fig_participacao_range, use_container_width=True)

            st.subheader(f"Empresas que Mais Pagarão Bônus e Participação ({selected_year})")

            # Top 10 empresas por Total de Bônus
            df_top_bonus = df_bonus_participacao_empresa.sort_values(by='Total_Bonus', ascending=False).head(10)
            fig_top_bonus = px.bar(
                df_top_bonus,
                x='Nome_Companhia',
                y='Total_Bonus',
                title='Top 10 Empresas por Total de Bônus',
                labels={'Nome_Companhia': 'Empresa', 'Total_Bonus': 'Total de Bônus (R$)'},
                template="simple_white"
            )
            st.plotly_chart(fig_top_bonus, use_container_width=True)

            # Top 10 empresas por Total de Participação
            df_top_participacao = df_bonus_participacao_empresa.sort_values(by='Total_Participacao', ascending=False).head(10)
            fig_top_participacao = px.bar(
                df_top_participacao,
                x='Nome_Companhia',
                y='Total_Participacao',
                title='Top 10 Empresas por Total de Participação',
                labels={'Nome_Companhia': 'Empresa', 'Total_Participacao': 'Total de Participação (R$)'},
                template="simple_white"
            )
            st.plotly_chart(fig_top_participacao, use_container_width=True)

        else:
            st.warning("Não há dados de bônus e participação para a Diretoria Estatutária no ano selecionado.")
    else:
        st.warning("Não há dados de remuneração variável disponíveis para o ano selecionado.")

    # --- Seção 3: Análise de Salário Base Médio ---
    st.header("3. Análise de Salário Base Médio por Empresa")

    if not df_total_orgao_filtered.empty:
        # Filtrar apenas a Diretoria Estatutária para salário base médio
        df_salario_diretoria = df_total_orgao_filtered[df_total_orgao_filtered["Orgao_Administracao"] == "Diretoria Estatutária"].copy()
        
        if not df_salario_diretoria.empty:
            # Converter 'Salario' para numérico
            df_salario_diretoria['Salario'] = pd.to_numeric(df_salario_diretoria['Salario'], errors='coerce').fillna(0)
            df_salario_diretoria['Numero_Membros_Remunerados'] = pd.to_numeric(df_salario_diretoria['Numero_Membros_Remunerados'], errors='coerce').fillna(0)

            # Calcular o salário base médio por membro
            # Evitar divisão por zero
            df_salario_diretoria['Salario_Base_Medio_Membro'] = df_salario_diretoria.apply(
                lambda row: row['Salario'] / row['Numero_Membros_Remunerados'] if row['Numero_Membros_Remunerados'] > 0 else 0,
                axis=1
            )

            # Agrupar por empresa e calcular o salário base médio geral da empresa
            df_salario_medio_empresa = df_salario_diretoria.groupby('Nome_Companhia')['Salario_Base_Medio_Membro'].mean().reset_index()

            st.subheader(f"Top 10 Empresas com Maior Salário Base Médio da Diretoria ({selected_year})")

            # Top 10 empresas por Salário Base Médio
            df_top_salario = df_salario_medio_empresa.sort_values(by='Salario_Base_Medio_Membro', ascending=False).head(10)
            fig_top_salario = px.bar(
                df_top_salario,
                x='Nome_Companhia',
                y='Salario_Base_Medio_Membro',
                title='Top 10 Empresas por Salário Base Médio da Diretoria',
                labels={'Nome_Companhia': 'Empresa', 'Salario_Base_Medio_Membro': 'Salário Base Médio (R$)'},
                template="simple_white"
            )
            st.plotly_chart(fig_top_salario, use_container_width=True)
        else:
            st.warning("Não há dados de salário para a Diretoria Estatutária no ano selecionado.")
    else:
        st.warning("Não há dados de remuneração total por órgão disponíveis para o ano selecionado.")

    st.caption("Fonte: Dados públicos CVM (Comissão de Valores Mobiliários) compilados. "
               f"Atenção: Esta aplicação é um protótipo e serve apenas para fins exploratórios e educacionais. "
               f"Os dados e análises apresentados podem conter limitações, inconsistências ou desatualizações. "
               f"Sempre valide informações antes de tomar decisões com base nestes resultados.")
