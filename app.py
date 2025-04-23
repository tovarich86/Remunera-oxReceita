import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# Set page configuration (should be the first Streamlit command)
st.set_page_config(page_title="Remuneração vs Receita", layout="wide")

# --- Data Loading Function ---
@st.cache_data # Cache the data to avoid reloading on every interaction
def load_data(url):
    """
    Loads data from the specified Excel file URL on GitHub,
    prepares the 'Ano' column, and returns a Pandas DataFrame.
    """
    try:
        # Download the file content
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Load the Excel data from the downloaded content
        # Using io.BytesIO to treat the byte content as a file
        df = pd.read_excel(io.BytesIO(response.content), sheet_name="fre_cia_aberta_remuneracao_maxi")

        # --- Data Preparation ---
        # Convert 'Data_Fim_Exercicio_Social' to datetime and extract the year
        # Coerce errors will turn unparseable dates into NaT (Not a Time)
        df["Ano"] = pd.to_datetime(df["Data_Fim_Exercicio_Social"], errors="coerce").dt.year

        # Drop rows where 'Ano' could not be determined (due to parsing errors)
        df.dropna(subset=["Ano"], inplace=True)

        # Convert 'Ano' to integer type after handling NaNs
        df["Ano"] = df["Ano"].astype(int)

        return df

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar o arquivo do GitHub: {e}")
        return None
    except FileNotFoundError: # Although less likely with URL, BytesIO might raise internal errors mapped here
         st.error(f"Erro: Aba 'fre_cia_aberta_remuneracao_maxi' não encontrada no arquivo Excel.")
         return None
    except KeyError as e:
        st.error(f"Erro: Coluna esperada não encontrada no arquivo: {e}. Verifique o arquivo de origem.")
        return None
    except Exception as e: # Catch other potential errors during loading/parsing
        st.error(f"Ocorreu um erro inesperado ao carregar os dados: {e}")
        return None

# --- Main Application Logic ---
st.title("Análise: Remuneração da Administração vs Receita da Companhia")

# URL for the raw Excel file on GitHub
github_url = "https://raw.githubusercontent.com/tovarich86/Remunera-oxReceita/main/remuneração%20faturamento.xlsx"

# Load the data using the function
df = load_data(github_url)

# Proceed only if data loading was successful
if df is not None:
    try:
        # --- Sidebar Filters ---
        st.sidebar.header("Filtros Principais")

        # Filter by Year - Sort years descending for relevance
        available_years = sorted(df["Ano"].unique(), reverse=True)
        selected_year = st.sidebar.selectbox("Ano", available_years, index=0)

        # Filter by Administrative Body
        # NOTE: Handling potential NaN values in filter options
        available_organs = sorted(df["Orgao_Administracao"].dropna().unique())
        selected_organ = st.sidebar.selectbox("Órgão Administrativo", available_organs, index=0)

        # Filter by Type of Remuneration
        selected_rem_type = st.sidebar.radio(
            "Tipo de Remuneração",
            ["Média", "Máxima", "Mínima"],
            horizontal=True # Display options horizontally
        )

        st.sidebar.header("Filtros Adicionais")
        # Filter by Category (Sector, Control, Company)
        filter_by = st.sidebar.radio(
            "Agrupar/Colorir por:",
            ["Nenhum", "Setor de Atividade", "Controle Acionário", "Empresa"],
            index=1 # Default to "Setor de Atividade"
        )

        # --- Apply Filters ---
        df_filt = df[
            (df["Ano"] == selected_year) &
            (df["Orgao_Administracao"] == selected_organ)
        ].copy() # Use .copy() to avoid SettingWithCopyWarning

        # --- Dynamic Secondary Filters ---
        # These filters depend on the primary selections and the 'filter_by' choice
        dynamic_filter_column = None
        dynamic_selection = None

        # NOTE: Using "Setor de ativdade" because this seems to be the column name in the source file.
        # If the actual column name is "Setor de atividade", please correct it here.
        sector_col_name = "Setor de ativdade" # Potential typo in source data column name

        if filter_by == "Setor de Atividade":
            dynamic_filter_column = sector_col_name
            available_options = sorted(df_filt[dynamic_filter_column].dropna().unique())
            dynamic_selection = st.sidebar.multiselect(f"Selecione o(s) Setor(es) de Atividade", available_options, default=available_options)
        elif filter_by == "Controle Acionário":
            dynamic_filter_column = "Especie_Controle_Acionario"
            available_options = sorted(df_filt[dynamic_filter_column].dropna().unique())
            dynamic_selection = st.sidebar.multiselect("Selecione o(s) Controle(s) Acionário(s)", available_options, default=available_options)
        elif filter_by == "Empresa":
            dynamic_filter_column = "Nome_Companhia"
            available_options = sorted(df_filt[dynamic_filter_column].dropna().unique())
            # Default selection for 'Empresa' might be too long, consider leaving it empty by default
            # default_companies = available_options if len(available_options) < 50 else [] # Example: Limit default selection
            dynamic_selection = st.sidebar.multiselect("Selecione a(s) Empresa(s)", available_options, default=available_options) # Keeping default as all for now

        # Apply dynamic filter if one is active
        if dynamic_filter_column and dynamic_selection:
            df_filt = df_filt[df_filt[dynamic_filter_column].isin(dynamic_selection)]

        # --- Select Remuneration Column ---
        remuneration_col = ""
        if selected_rem_type == "Média":
            remuneration_col = "Valor_Medio_Remuneracao"
        elif selected_rem_type == "Máxima":
            remuneration_col = "Valor_Maior_Remuneracao"
        else: # Mínima
            remuneration_col = "Valor_Menor_Remuneracao"

        # --- Prepare Data for Plotting ---
        # Ensure required columns exist before dropping NA
        required_cols = [remuneration_col, "Receita", "Nome_Companhia", "ticker"]
        # Add dynamic filter column if used for color, handling the potential typo case
        color_col = None
        if filter_by == "Setor de Atividade":
             color_col = sector_col_name
             required_cols.append(sector_col_name)
        elif filter_by == "Controle Acionário":
             color_col = "Especie_Controle_Acionario"
             required_cols.append("Especie_Controle_Acionario")
        elif filter_by == "Empresa":
             # Color by company name might be too noisy if many companies selected
             color_col = "Nome_Companhia"
             # No need to append 'Nome_Companhia' again if already required

        # Ensure all required columns are present before proceeding
        missing_cols = [col for col in required_cols if col not in df_filt.columns]
        if missing_cols:
             st.warning(f"Colunas necessárias ausentes nos dados filtrados: {', '.join(missing_cols)}. Verifique o arquivo de origem ou os filtros.")
             df_plot = pd.DataFrame() # Create empty DataFrame to avoid plotting errors
        else:
             # Drop rows where essential data for plotting (remuneration or revenue) is missing
             df_plot = df_filt.dropna(subset=[remuneration_col, "Receita"]).copy()

             # Optional: Convert Receita to millions for better axis scale, if desired
             # df_plot['Receita_Milhoes'] = df_plot['Receita'] / 1_000_000
             # x_axis_col = 'Receita_Milhoes'
             # x_axis_label = "Receita (R$ Milhões)"
             x_axis_col = 'Receita' # Keep original for now
             x_axis_label = "Receita (R$)"


        # --- Create Scatter Plot ---
        if not df_plot.empty:
            st.subheader(f"Relação entre Receita e Remuneração {selected_rem_type}")
            st.markdown(f"**Ano:** {selected_year} | **Órgão:** {selected_organ}")

            # Define hover data more explicitly
            hover_data_config = {
                "Nome_Companhia": True, # Show company name
                "ticker": True, # Show ticker symbol
                sector_col_name: True, # Show sector (using the potentially misspelled name)
                "Especie_Controle_Acionario": True, # Show control type
                x_axis_col: ':.2f', # Format Revenue
                remuneration_col: ':.2f' # Format Remuneration
            }

            fig = px.scatter(
                df_plot,
                x=x_axis_col,
                y=remuneration_col,
                color=color_col, # Color based on the selected filter category
                hover_name="Nome_Companhia", # Primary identifier on hover
                hover_data=hover_data_config,
                labels={ # Custom labels for axes
                    x_axis_col: x_axis_label,
                    remuneration_col: f"Remuneração {selected_rem_type} (R$)",
                    # Add labels for color legend if color_col is set
                    color_col: filter_by if color_col else None
                },
                title=f"Remuneração {selected_rem_type} vs Receita ({selected_year}, {selected_organ})",
                template="simple_white" # Cleaner plot template
            )

            # Add Trendline (OLS - Ordinary Least Squares) if more than one data point
            if len(df_plot) > 1:
                try:
                    # Create a temporary figure just to calculate the trendline
                    fig_trend = px.scatter(df_plot, x=x_axis_col, y=remuneration_col, trendline="ols")
                    # Add only the trendline trace from the temporary figure to the main figure
                    fig.add_traces(fig_trend.data[1])
                except Exception as trend_err:
                    st.warning(f"Não foi possível calcular a linha de tendência: {trend_err}")


            # Update marker appearance
            fig.update_traces(marker=dict(size=12, opacity=0.8), selector=dict(mode='markers')) # Slightly smaller markers

            # Adjust layout
            fig.update_layout(
                height=600,
                xaxis_title=x_axis_label,
                yaxis_title=f"Remuneração {selected_rem_type} (R$)",
                legend_title_text=filter_by if color_col else None # Set legend title
            )

            # Display the plot
            st.plotly_chart(fig, use_container_width=True)

            # --- Display Filtered Data Table ---
            with st.expander("Ver dados detalhados (filtrados)"):
                # Define columns to display in the table
                display_cols = ["Nome_Companhia", "ticker", sector_col_name,
                                "Especie_Controle_Acionario", "Receita", remuneration_col]
                # Ensure columns exist before trying to display them
                display_cols_exist = [col for col in display_cols if col in df_plot.columns]
                st.dataframe(df_plot[display_cols_exist].style.format({ # Apply formatting
                     "Receita": "R$ {:,.2f}",
                     remuneration_col: "R$ {:,.2f}"
                 }))

            st.caption("Fonte: Dados públicos CVM (Comissão de Valores Mobiliários) compilados.")

        else:
            # Message if no data is available after filtering
            st.warning("Não há dados disponíveis para os filtros selecionados.")

    except KeyError as e:
        st.error(f"Erro de processamento: Uma coluna esperada ({e}) não foi encontrada nos dados filtrados. "
                 f"Isso pode ocorrer se a estrutura do arquivo mudou ou se os filtros resultaram em dados incompletos.")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado durante o processamento ou visualização: {e}")

elif df is None:
    # Message if data loading failed initially
    st.error("Não foi possível carregar os dados. Verifique a URL do arquivo e a conexão com a internet.")
