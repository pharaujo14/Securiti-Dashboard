import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

from utils.graficos.graficos_cookies import grafico_consents, grafico_categorias, grafico_paises, grafico_dominios
from utils.pdf.pd_generator_cookies import gerar_pdf_cookies  # seu novo arquivo


def pagina_cookies(db):
      
    # Carregar dados
    dados = list(db["consolidado_cookies"].find({}))
    if not dados:
        st.warning("Nenhum dado encontrado.")
        return

    # === PREPARAÇÃO DOS DADOS ===
    df = pd.DataFrame(dados)
    df['date'] = pd.to_datetime(df['date']).dt.date
    df['organization'] = df['organization'].astype(str)
    df['total_consents'] = df['metrics'].apply(lambda x: x.get('total_consents', 0))

    # === ALIAS DE ORGANIZAÇÕES ===
    aliases = {
        "carrefour": "Grupo Carrefour Brasil",
        "cci": "CCI",
        "property": "Property",
        "sams": "Sam's Club"
    }

    # Aplicar aliases no DataFrame
    df['organization_label'] = df['organization'].map(aliases).fillna(df['organization'])

    # === FILTROS ===
    orgs_labels = sorted(df['organization_label'].unique())
    org_selecionada_label = st.sidebar.selectbox("Organização", ["Todas"] + orgs_labels)

    # Traduzir label de volta para nome real
    org_label_to_real = {v: k for k, v in aliases.items()}
    org_selecionada = org_label_to_real.get(org_selecionada_label, org_selecionada_label)
    
    # === PREPARAR LISTA DE DOMÍNIOS ===
    dominios_data = []
    for _, row in df.iterrows():
        dominios = row["metrics"].get("domains", {})
        for dom in dominios.keys():
            dominios_data.append(dom)

    dominios_unicos = sorted(set(dominios_data))

    # === FILTRO DE DOMÍNIOS ===
    dominio_selecionado = st.sidebar.selectbox("Domínio", ["Todos"] + dominios_unicos)

    # === FILTRAR PELOS DOMÍNIOS ===
    if dominio_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["metrics"].apply(lambda x: dominio_selecionado in x.get("domains", {}))]



    ontem = datetime.today().date() - timedelta(days=1)

    periodo_opcoes = [
        f'Todo o Período',
        f'Ontem ({ontem.strftime("%d/%m/%y")})',
        f'Última Semana (desde {(ontem - timedelta(days=6)).strftime("%d/%m/%y")})',
        f'Últimos 30 dias (desde {(ontem - timedelta(days=29)).strftime("%d/%m/%y")})',
        'Personalizado'
    ]
    
    opcao_selecionada = st.sidebar.selectbox('Período', periodo_opcoes)

    if opcao_selecionada.startswith('Todo'):
        data_inicio = df['date'].min()
        data_fim = ontem
    elif opcao_selecionada.startswith('Ontem'):
        data_inicio = ontem
        data_fim = ontem
    elif opcao_selecionada.startswith('Última Semana'):
        data_inicio = ontem - timedelta(days=6)
        data_fim = ontem
    elif opcao_selecionada.startswith('Últimos 30 dias'):
        data_inicio = ontem - timedelta(days=29)
        data_fim = ontem
    else:
        data_inicio = st.sidebar.date_input('Data de Início', ontem - timedelta(days=29))
        data_fim = st.sidebar.date_input('Data de Fim', ontem)

    # === APLICAR FILTROS ===
    df_filtrado = df[(df['date'] >= data_inicio) & (df['date'] <= data_fim)]
    if org_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado['organization'] == org_selecionada]

    # === TOTAL DE CONSENTS ===
    total_consents = df_filtrado['total_consents'].sum()
    total_formatado = f"{total_consents:,.0f}".replace(",", ".")
    st.sidebar.markdown("### Total de Consents")
    st.sidebar.markdown(f"<h2 style='text-align: center;'>{total_formatado}</h2>", unsafe_allow_html=True)
    
    # === BOTÃO PARA GERAR PDF ===
    if st.sidebar.button("Gerar PDF do Relatório"):
        pdf_bytes = gerar_pdf_cookies(
            data_inicio=data_inicio,
            data_fim=data_fim,
            df_filtrado=df_filtrado,
            org_selecionada=org_selecionada_label
        )

        st.sidebar.download_button(
            label="Baixar PDF",
            data=pdf_bytes,
            file_name=f"relatorio_cookies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf"
        )


    # === GRÁFICO DE DOMÍNIOS MAIS ACESSADOS (TOP 10) ===
    st.markdown("### Domínios mais acessados (Top 10)")
    
    grafico_dominios(df_filtrado)
    
    # === GRÁFICO DE CATEGORIAS DE COOKIES ===
    st.markdown("### Categorias de Cookies por Domínios (Top 5)")

    grafico_categorias(df_filtrado)

    # === GRÁFICO DE PAÍSES (TOP 10) ===
    st.markdown("### Distribuição de Países (Top 10)")

    grafico_paises(df_filtrado)
    
    # === GRÁFICO TOTAL POR ORGANIZAÇÃO ===
    st.markdown("### Total de Consents por Organização")

    grafico_consents(df_filtrado)