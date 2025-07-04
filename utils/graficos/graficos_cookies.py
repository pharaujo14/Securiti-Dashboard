import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

# ===========================
# CONSENTS
# ===========================

def gerar_grafico_consents(df_filtrado):
    df_group = df_filtrado.groupby('organization_label')['total_consents'].sum().reset_index()
    df_group['total_formatado'] = df_group['total_consents'].apply(lambda x: f'{x / 1_000_000:.1f}M'.replace('.', ','))
    df_group = df_group.sort_values(by='total_consents', ascending=False)

    df_group['organization_label'] = pd.Categorical(
        df_group['organization_label'], categories=df_group['organization_label'], ordered=True
    )

    chart = alt.Chart(df_group).mark_bar(color='#0000CD').encode(
        x=alt.X('organization_label:N', title='', sort=list(df_group['organization_label'])),
        y=alt.Y(
            'total_consents:Q',
            title='',
            axis=alt.Axis(labelExpr="datum.value >= 1000000 ? (datum.value / 1000000) + 'M' : datum.value"),
            scale=alt.Scale(domain=[0, df_group['total_consents'].max() * 1.1])
        ),
        tooltip=[
            alt.Tooltip('organization_label:N', title='Organização'),
            alt.Tooltip('total_consents:Q', title='Total de Consents', format=',')
        ]
    ).properties(width=600, height=400)

    text = chart.mark_text(
        align='center',
        baseline='bottom',
        dy=-4,
        color='black'
    ).encode(
        text='total_formatado:N'
    )

    return chart + text


def grafico_consents(df_filtrado):
    chart = gerar_grafico_consents(df_filtrado)
    st.altair_chart(chart, use_container_width=True)


# ===========================
# CATEGORIAS
# ===========================

def gerar_grafico_categorias(df_filtrado):     
    categorias_data = []
    for _, row in df_filtrado.iterrows():
        dominios = row['metrics'].get('domains', {})
        categorias = row['metrics'].get('categories', {})
        for dom in dominios.keys():
            for cat, val in categorias.items():
                categorias_data.append({"Domínio": dom, "Categoria": cat, "Valor": val})

    df_categorias = pd.DataFrame(categorias_data)

    if df_categorias.empty:
        return None

    df_categorias = df_categorias.groupby(["Domínio", "Categoria"]).sum().reset_index()
    top5_dominios = df_categorias.groupby("Domínio")["Valor"].sum().nlargest(5).index.tolist()
    df_categorias = df_categorias[df_categorias["Domínio"].isin(top5_dominios)]
    df_categorias["Domínio"] = pd.Categorical(df_categorias["Domínio"], categories=top5_dominios, ordered=True)

    chart = alt.Chart(df_categorias).mark_bar().encode(
        x=alt.X("Domínio:N", title="", sort=top5_dominios),
        y=alt.Y(
            "Valor:Q",
            title="",
            axis=alt.Axis(labelExpr="datum.value >= 1000000 ? (datum.value / 1000000) + 'M' : datum.value"),
            scale=alt.Scale(domain=[0, df_categorias.groupby("Domínio")["Valor"].sum().max() * 1.1])
        ),
        color=alt.Color("Categoria:N", title="Categoria", legend=alt.Legend(orient="right")),
        tooltip=[
            alt.Tooltip("Domínio:N", title="Domínio"),
            alt.Tooltip("Categoria:N", title="Categoria"),
            alt.Tooltip("Valor:Q", title="Valor", format=",")
        ]
    ).properties(width=700, height=400)

    return chart


def grafico_categorias(df_filtrado):
    chart = gerar_grafico_categorias(df_filtrado)
    if chart:
        st.altair_chart(chart, use_container_width=True)
    else:
        st.write("Sem dados de categorias para exibir.")


# ===========================
# PAÍSES
# ===========================

def gerar_grafico_paises(df_filtrado):     

    def emoji_bandeira(pais):
        if len(pais) == 2:
            return ''.join(chr(127397 + ord(c)) for c in pais.upper())
        return pais

    paises_data = []
    for _, row in df_filtrado.iterrows():
        paises = row["metrics"].get("countries", {})
        for pais, val in paises.items():
            paises_data.append({"País": pais, "Valor": val})

    df_paises = pd.DataFrame(paises_data)

    if df_paises.empty:
        return None

    df_top = df_paises.groupby("País")["Valor"].sum().sort_values(ascending=False).head(10).reset_index()
    df_top["Bandeira"] = df_top["País"].apply(emoji_bandeira)
    df_top["Bandeira"] = pd.Categorical(df_top["Bandeira"], categories=df_top["Bandeira"], ordered=True)

    chart = alt.Chart(df_top).mark_bar(color="#0000CD").encode(
        y=alt.Y("Bandeira:N", title="", sort=list(df_top["Bandeira"])),
        x=alt.X(
            "Valor:Q",
            title="",
            axis=alt.Axis(labelExpr="datum.value >= 1000000 ? (datum.value / 1000000) + 'M' : datum.value"),
            scale=alt.Scale(domain=[0, df_top["Valor"].max() * 1.1])
        ),
        tooltip=[
            alt.Tooltip("País:N", title="País"),
            alt.Tooltip("Valor:Q", title="Valor", format=",")
        ]
    ).properties(width=700, height=400)

    return chart


def grafico_paises(df_filtrado):
    chart = gerar_grafico_paises(df_filtrado)
    if chart:
        st.altair_chart(chart, use_container_width=True)
    else:
        st.write("Sem dados de países para exibir.")


# ===========================
# DOMÍNIOS
# ===========================

def gerar_grafico_dominios(df_filtrado):     

    dominios_data = []
    for _, row in df_filtrado.iterrows():
        dominios = row["metrics"].get("domains", {})
        for dom, val in dominios.items():
            dominios_data.append({"Domínio": dom, "Valor": val})

    df_dominios = pd.DataFrame(dominios_data)

    if df_dominios.empty:
        return None

    df_top = df_dominios.groupby("Domínio")["Valor"].sum().sort_values(ascending=False).head(20).reset_index()
    df_top["Domínio"] = pd.Categorical(df_top["Domínio"], categories=df_top["Domínio"], ordered=True)

    chart = alt.Chart(df_top).mark_bar(color="#0000CD").encode(
        y=alt.Y("Domínio:N", title="", sort=list(df_top["Domínio"])),
        x=alt.X(
            "Valor:Q",
            title="",
            axis=alt.Axis(labelExpr="datum.value >= 1000000 ? (datum.value / 1000000) + 'M' : datum.value"),
            scale=alt.Scale(domain=[0, df_top["Valor"].max() * 1.1])
        ),
        tooltip=[
            alt.Tooltip("Domínio:N", title="Domínio"),
            alt.Tooltip("Valor:Q", title="Valor", format=",")
        ]
    ).properties(width=700, height=400)

    return chart


def grafico_dominios(df_filtrado):
    chart = gerar_grafico_dominios(df_filtrado)
    if chart:
        st.altair_chart(chart, use_container_width=True)
    else:
        st.write("Sem dados de domínios para exibir.")

def grafico_barras_categoria_status(df):

    status_map = {
        1: "GRANTED",
        2: "DECLINED",
        3: "WITHDRAWN",
        4: "NOACTION",
        5: "PENDING",
        6: "NO_CONSENT"
    }

    # Construir DataFrame para plotagem
    dados = []

    for _, row in df.iterrows():
        items = row["metrics"].get("items_by_category_id", {})
        for chave, qtd in items.items():
            try:
                categoria, id_raw = chave.split("--")
                categoria = categoria.strip().lower()

                categoria_map = {
                    "essencial": "Essential",
                    "essential": "Essential",
                    "publicidade para terceiros": "Publicidade para Terceiros",
                    "advertising": "Advertising",
                    "analytics & customization": "Analytics & Customization",
                    "analytics & customisation": "Analytics & Customization",
                    "performance & functionality": "Performance & Functionality",
                    "unclassified": "Unclassified",
                }
                
                categoria = categoria.strip().lower()
                categoria = categoria_map.get(categoria, categoria.title())
                status_id = int(id_raw.strip())
                status = status_map.get(status_id, "UNKNOWN")
                dados.append({
                    "Categoria": categoria,
                    "Status": status,
                    "Quantidade": qtd
                })
            except:
                continue

    if not dados:
        st.info("Sem dados suficientes para o gráfico.")
        return

    df_plot = pd.DataFrame(dados)
    df_plot = df_plot[df_plot["Status"] != "NOACTION"]


    fig = px.bar(
        df_plot,
        x="Quantidade",
        y="Categoria",
        color="Status",
        orientation="h",
        barmode="group",
        color_discrete_map={
            "GRANTED": "#6699FF",
            "DECLINED": "#FF6666",
            "WITHDRAWN": "#FFCC66",
            "NOACTION": "#999999",
            "PENDING": "#CCCCFF",
            "NO_CONSENT": "#CCCCCC"
        },
        title=None
    )

    fig.update_layout(
        xaxis_title=None,
        yaxis_title=None,
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)
