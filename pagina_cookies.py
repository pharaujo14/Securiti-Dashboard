import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

from utils.graficos.graficos_cookies import (
    grafico_consents,
    grafico_categorias,
    grafico_paises,
    grafico_dominios,
    grafico_barras_categoria_status
)

from utils.pdf.pd_generator_cookies import gerar_pdf_cookies  


def pagina_cookies(db):

    # === CARREGAR DADOS ===
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

    df['organization_label'] = df['organization'].map(aliases).fillna(df['organization'])

    # === FILTRO DE ORGANIZAÇÃO ===
    orgs_labels = sorted(df['organization_label'].unique())
    org_selecionada_label = st.sidebar.selectbox("Organização", ["Todas"] + orgs_labels)

    # traduz label → valor real
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

    # === FILTRO DE PERÍODO ===
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

    # ======================================================
    #   APLICAR FILTROS — versão corrigida (ordem correta)
    # ======================================================
    df_filtrado = df.copy()

    # 1) DOMÍNIO
    if dominio_selecionado != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["metrics"].apply(
                lambda x: dominio_selecionado in x.get("domains", {})
            )
        ]

    # 2) PERÍODO
    df_filtrado = df_filtrado[
        (df_filtrado['date'] >= data_inicio) & (df_filtrado['date'] <= data_fim)
    ]

    # 3) ORGANIZAÇÃO
    if org_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado['organization'] == org_selecionada]

    # ======================================================
    #   RESUMO DE CONSENTIMENTO
    # ======================================================

    st.markdown("### Consentimento")

    status_map = {
        1: "GRANTED",
        2: "DECLINED",
        3: "WITHDRAWN",
        4: "NOACTION",
        5: "PENDING",
        6: "NO_CONSENT"
    }

    status_counts = {label: 0 for label in status_map.values()}
    total_itens = 0

    for _, row in df_filtrado.iterrows():
        items = row["metrics"].get("items_by_category_id", {})
        for key, value in items.items():
            try:
                id_part = int(key.strip().split("--")[-1])
                label = status_map.get(id_part)
                if label:
                    status_counts[label] += value
                    total_itens += value
            except:
                continue

    def pct(valor):
        return round((valor / total_itens) * 100, 1) if total_itens > 0 else 0

    def formatar_milhar(valor):
        return f"{valor:,}".replace(",", ".")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Action Rate", f"{pct(status_counts['GRANTED'] + status_counts['DECLINED'])}%", 
                  f"{formatar_milhar(status_counts['GRANTED'] + status_counts['DECLINED'])}")

    with col2:
        st.metric("Consent Rate", f"{pct(status_counts['GRANTED'])}%", 
                  f"{formatar_milhar(status_counts['GRANTED'])}")

    with col3:
        st.metric("Decline Rate", f"{pct(status_counts['DECLINED'])}%", 
                  f"{formatar_milhar(status_counts['DECLINED'])}")

    with col4:
        st.metric("No Action Rate", f"{pct(status_counts['NOACTION'])}%", 
                  f"{formatar_milhar(status_counts['NOACTION'])}")

    # === gráfico categoria/status ===
    st.markdown("### Categoria de Cookies e Status de Consentimento")
    grafico_barras_categoria_status(df_filtrado)

    # === TOTAL DE CONSENTS ===
    total_consents = df_filtrado['total_consents'].sum()
    total_formatado = f"{total_consents:,.0f}".replace(",", ".")
    st.sidebar.markdown("### Total de Consents")
    st.sidebar.markdown(f"<h2 style='text-align: center;'>{total_formatado}</h2>", unsafe_allow_html=True)

    # === GERAR PDF ===
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

    # === GRÁFICOS ===
    st.markdown("### Domínios mais acessados (Top 10)")
    grafico_dominios(df_filtrado)

    st.markdown("### Categorias de Cookies por Domínios (Top 5)")
    grafico_categorias(df_filtrado)

    st.markdown("### Distribuição de Países (Top 10)")
    grafico_paises(df_filtrado)

    st.markdown("### Total de Consents por Organização")
    grafico_consents(df_filtrado)
