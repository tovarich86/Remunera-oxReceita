import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

st.set_page_config(page_title="Remuneração vs Receita Bi", layout="wide")

@st.cache_data
def load_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_excel(io.BytesIO(response.content), sheet_name="fre_cia_aberta_remuneracao_maxi")
        df["Ano"] = pd.to_datetime(df["Data_Fim_Exercicio_Social"], errors="coerce").dt.year
        df.dropna(subset=["Ano"], inplace=True)
        df["Ano"] = df["Ano"].astype(int)
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao baixar o arquivo do GitHub: {e}")
        return None
    except FileNotFoundError:
        st.error(f"Erro: Aba 'fre_cia_aberta_remuneracao_maxi' não encontrada no arquivo Excel.")
        return None
    except KeyError as e:
        st.error(f"Erro: Coluna esperada não encontrada no arquivo: {e}. Verifique o arquivo de origem.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar os dados: {e}")
        return None

st.title("Análise: Remuneração da Administração vs Receita da Companhia")

github_url = "https://raw.githubusercontent.com/tovarich86/Remunera-oxReceita/main/remuneração%20faturamento.xlsx"
df = load_data(github_url)

if df is not None:
    try:
        st.sidebar.header("Filtros Principais")
        available_years = sorted(df["Ano"].unique(), reverse=True)
        selected_year = st.sidebar.selectbox("Ano", available_years, index=0)

        available_organs = sorted(df["Orgao_Administracao"].dropna().unique())
        selected_organ = st.sidebar.selectbox("Órgão Administrativo", available_organs, index=0)

        selected_rem_type = st.sidebar.radio(
            "Tipo de Remuneração",
            ["Média", "Máxima", "Mínima"],
            horizontal=True
        )

        st.sidebar.header("Filtros Adicionais")
        filter_by = st.sidebar.radio(
            "Agrupar/Colorir por:",
            ["Nenhum", "Setor de Atividade", "Controle Acionário", "Empresa"],
            index=1
        )

        df_filt = df[
            (df["Ano"] == selected_year) &
            (df["Orgao_Administracao"] == selected_organ)
        ].copy()

        dynamic_filter_column = None
        sector_col_name = "Setor de ativdade"  # Corrija se necessário

        # Filtros dinâmicos conforme solicitado
        if filter_by == "Setor de Atividade":
            dynamic_filter_column = sector_col_name
            available_options = sorted(df_filt[dynamic_filter_column].dropna().unique())
            setores_selecionados = st.sidebar.multiselect(
                "Selecione o(s) Setor(es) de Atividade",
                available_options,
                default=[]
            )
            if setores_selecionados:
                empresas_filtradas = sorted(
                    df_filt[df_filt[dynamic_filter_column].isin(setores_selecionados)]["Nome_Companhia"].dropna().unique()
                )
            else:
                empresas_filtradas = []
            empresas_selecionadas = st.sidebar.multiselect(
                "Selecione a(s) Empresa(s)",
                empresas_filtradas,
                default=empresas_filtradas
            )
            if setores_selecionados and empresas_selecionadas:
                df_filt = df_filt[
                    (df_filt[dynamic_filter_column].isin(setores_selecionados)) &
                    (df_filt["Nome_Companhia"].isin(empresas_selecionadas))
                ]
            else:
                df_filt = df_filt.iloc[0:0]

        elif filter_by == "Controle Acionário":
            dynamic_filter_column = "Especie_Controle_Acionario"
            available_options = sorted(df_filt[dynamic_filter_column].dropna().astype(str).unique())
            controles_selecionados = st.sidebar.multiselect(
                "Selecione o(s) Controle(s) Acionário(s)",
                available_options,
                default=[]
            )
            if controles_selecionados:
                empresas_filtradas = sorted(
                    df_filt[df_filt[dynamic_filter_column].astype(str).isin(controles_selecionados)]["Nome_Companhia"].dropna().unique()
                )
            else:
                empresas_filtradas = []
            empresas_selecionadas = st.sidebar.multiselect(
                "Selecione a(s) Empresa(s)",
                empresas_filtradas,
                default=empresas_filtradas
            )
            if controles_selecionados and empresas_selecionadas:
                df_filt = df_filt[
                    (df_filt[dynamic_filter_column].isin(controles_selecionados)) &
                    (df_filt["Nome_Companhia"].isin(empresas_selecionadas))
                ]
            else:
                df_filt = df_filt.iloc[0:0]

        elif filter_by == "Empresa":
            dynamic_filter_column = "Nome_Companhia"
            available_options = sorted(df_filt[dynamic_filter_column].dropna().unique())
            empresas_selecionadas = st.sidebar.multiselect(
                "Selecione a(s) Empresa(s)",
                available_options,
                default=[]
            )
            if empresas_selecionadas:
                df_filt = df_filt[df_filt[dynamic_filter_column].isin(empresas_selecionadas)]
            else:
                df_filt = df_filt.iloc[0:0]

        # Seleção da coluna de remuneração
        if selected_rem_type == "Média":
            remuneration_col = "Valor_Medio_Remuneracao"
        elif selected_rem_type == "Máxima":
            remuneration_col = "Valor_Maior_Remuneracao"
        else:
            remuneration_col = "Valor_Menor_Remuneracao"

        required_cols = [remuneration_col, "Receita", "Nome_Companhia", "ticker"]
        color_col = None
        if filter_by == "Setor de Atividade":
            color_col = sector_col_name
            required_cols.append(sector_col_name)
        elif filter_by == "Controle Acionário":
            color_col = "Especie_Controle_Acionario"
            required_cols.append("Especie_Controle_Acionario")
        elif filter_by == "Empresa":
            color_col = "Nome_Companhia"

        missing_cols = [col for col in required_cols if col not in df_filt.columns]
        if missing_cols:
            st.warning(f"Colunas necessárias ausentes nos dados filtrados: {', '.join(missing_cols)}. Verifique o arquivo de origem ou os filtros.")
            df_plot = pd.DataFrame()
        else:
            df_plot = df_filt.dropna(subset=[remuneration_col, "Receita"]).copy()
            x_axis_col = 'Receita'
            x_axis_label = "Receita (R$ Bi)"

        if not df_plot.empty:
            st.subheader(f"Relação entre Receita e Remuneração {selected_rem_type}")
            st.markdown(f"**Ano:** {selected_year} | **Órgão:** {selected_organ}")

            hover_data_config = {
                "Nome_Companhia": True,
                "ticker": True,
                sector_col_name: True,
                "Especie_Controle_Acionario": True,
                x_axis_col: ':.2f',
                remuneration_col: ':.2f'
            }

            fig = px.scatter(
                df_plot,
                x=x_axis_col,
                y=remuneration_col,
                color=color_col,
                hover_name="Nome_Companhia",
                hover_data=hover_data_config,
                labels={
                    x_axis_col: x_axis_label,
                    remuneration_col: f"Remuneração {selected_rem_type} (R$)",
                    color_col: filter_by if color_col else None
                },
                title=f"Remuneração {selected_rem_type} vs Receita ({selected_year}, {selected_organ})",
                template="simple_white"
            )

            if len(df_plot) > 1:
                try:
                    fig_trend = px.scatter(df_plot, x=x_axis_col, y=remuneration_col, trendline="ols")
                    fig.add_traces(fig_trend.data[1])
                except Exception as trend_err:
                    st.warning(f"Não foi possível calcular a linha de tendência: {trend_err}")

            fig.update_traces(marker=dict(size=12, opacity=0.8), selector=dict(mode='markers'))
            fig.update_layout(
                height=600,
                xaxis_title=x_axis_label,
                yaxis_title=f"Remuneração {selected_rem_type} (R$)",
                legend_title_text=filter_by if color_col else None
            )

            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Ver dados detalhados (filtrados)"):
                display_cols = ["Nome_Companhia", "ticker", sector_col_name,
                                "Especie_Controle_Acionario", "Receita", remuneration_col]
                display_cols_exist = [col for col in display_cols if col in df_plot.columns]
                st.dataframe(df_plot[display_cols_exist].style.format({
                    "Receita": "R$ {:,.2f}",
                    remuneration_col: "R$ {:,.2f}"
                }))

            st.caption("Fonte: Dados públicos CVM (Comissão de Valores Mobiliários) compilados. "
                       f"Atenção: Esta aplicação é um protótipo e serve apenas para fins exploratórios e educacionais. "
                       f"Os dados e análises apresentados podem conter limitações, inconsistências ou desatualizações. "
                       f"Sempre valide informações antes de tomar decisões com base nestes resultados.")

        else:
            st.warning("Não há dados disponíveis para os filtros selecionados.")

    except KeyError as e:
        st.error(f"Erro de processamento: Uma coluna esperada ({e}) não foi encontrada nos dados filtrados. "
                 f"Isso pode ocorrer se a estrutura do arquivo mudou ou se os filtros resultaram em dados incompletos.")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado durante o processamento ou visualização: {e}")

elif df is None:
    st.error("Não foi possível carregar os dados. Verifique a URL do arquivo e a conexão com a internet.")
