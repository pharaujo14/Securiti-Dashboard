import streamlit as st
import pandas as pd
import altair as alt

def grafico_consents(df_filtrado):     

    # Preparar dados
    df_group = df_filtrado.groupby('organization_label')['total_consents'].sum().reset_index()
    df_group['total_formatado'] = df_group['total_consents'].apply(lambda x: f'{x / 1_000_000:.1f}M'.replace('.', ','))
    df_group = df_group.sort_values(by='total_consents', ascending=False)

    # Definir ordem personalizada no eixo X
    df_group['organization_label'] = pd.Categorical(
        df_group['organization_label'], categories=df_group['organization_label'], ordered=True
    )

    # Gráfico Altair com tudo ajustado
    chart = alt.Chart(df_group).mark_bar(color='#0000CD').encode(
        x=alt.X('organization_label:N', title='', sort=list(df_group['organization_label'])),
        y=alt.Y(
            'total_consents:Q',
            title='',
            axis=alt.Axis(
                labelExpr="datum.value >= 1000000 ? (datum.value / 1000000) + 'M' : datum.value"
            ),
            scale=alt.Scale(domain=[0, df_group['total_consents'].max() * 1.1])
        ),
        tooltip=[
            alt.Tooltip('organization_label:N', title='Organização'),
            alt.Tooltip('total_consents:Q', title='Total de Consents', format=',')
        ]
    ).properties(width=600, height=400)

    # Texto no topo das barras
    text = chart.mark_text(
        align='center',
        baseline='bottom',
        dy=-4,
        color='black'
    ).encode(
        text='total_formatado:N'
    )

    # Renderizar no Streamlit
    st.altair_chart(chart + text, use_container_width=True)

def grafico_categorias(df_filtrado):     

    # Preparar dados
    categorias_data = []
    for _, row in df_filtrado.iterrows():
        org = row['organization_label']
        categorias = row['metrics'].get('categories', {})
        for cat, val in categorias.items():
            categorias_data.append({"Organização": org, "Categoria": cat, "Valor": val})

    df_categorias = pd.DataFrame(categorias_data)

    if not df_categorias.empty:
        # Agrupar valores por organização e categoria
        df_categorias = df_categorias.groupby(["Organização", "Categoria"]).sum().reset_index()

        # Ordenar organizações por total de cookies (desc)
        ordem_org = df_categorias.groupby("Organização")["Valor"].sum().sort_values(ascending=False).index.tolist()
        df_categorias["Organização"] = pd.Categorical(df_categorias["Organização"], categories=ordem_org, ordered=True)

        # Gráfico Altair empilhado com tooltip e formatação
        chart = alt.Chart(df_categorias).mark_bar().encode(
            x=alt.X("Organização:N", title="", sort=ordem_org),
            y=alt.Y(
                "Valor:Q",
                title="",
                axis=alt.Axis(labelExpr="datum.value >= 1000000 ? (datum.value / 1000000) + 'M' : datum.value"),
                scale=alt.Scale(domain=[0, df_categorias.groupby("Organização")["Valor"].sum().max() * 1.1])
            ),
            color=alt.Color("Categoria:N", title="Categoria", legend=alt.Legend(orient="right")),
            tooltip=[
                alt.Tooltip("Organização:N", title="Organização"),
                alt.Tooltip("Categoria:N", title="Categoria"),
                alt.Tooltip("Valor:Q", title="Valor", format=",")
            ]
        ).properties(width=700, height=400)

        st.altair_chart(chart, use_container_width=True)

    else:
        st.write("Sem dados de categorias para exibir.")

    # # === GRÁFICO DE PAÍSES (TOP 10) ===
def grafico_paises(df_filtrado):     

    # Função para gerar o emoji da bandeira
    def emoji_bandeira(pais):
        if len(pais) == 2:
            return ''.join(chr(127397 + ord(c)) for c in pais.upper())
        return pais

    # Preparar dados
    paises_data = []
    for _, row in df_filtrado.iterrows():
        paises = row["metrics"].get("countries", {})
        for pais, val in paises.items():
            paises_data.append({"País": pais, "Valor": val})

    df_paises = pd.DataFrame(paises_data)

    if not df_paises.empty:
        # Agrupar e pegar top 10
        df_top = df_paises.groupby("País")["Valor"].sum().sort_values(ascending=False).head(10).reset_index()

        # Substituir país apenas pela bandeira
        df_top["Bandeira"] = df_top["País"].apply(emoji_bandeira)
        df_top["Bandeira"] = pd.Categorical(df_top["Bandeira"], categories=df_top["Bandeira"], ordered=True)

        # Gráfico Altair
        chart = alt.Chart(df_top).mark_bar(color="#0000CD").encode(
            y=alt.Y("Bandeira:N", title="", sort=list(df_top["Bandeira"])),
            x=alt.X(
                "Valor:Q",
                title="",
                axis=alt.Axis(
                    labelExpr="datum.value >= 1000000 ? (datum.value / 1000000) + 'M' : datum.value"
                ),
                scale=alt.Scale(domain=[0, df_top["Valor"].max() * 1.1])
            ),
            tooltip=[
                alt.Tooltip("País:N", title="País"),
                alt.Tooltip("Valor:Q", title="Valor", format=",")
            ]
        ).properties(width=700, height=400)

        st.altair_chart(chart, use_container_width=True)

    else:
        st.write("Sem dados de países para exibir.")


    # # === GRÁFICO DE DOMÍNIOS MAIS ACESSADOS (TOP 10) ===
def grafico_dominios(df_filtrado):     

    # Preparar dados
    dominios_data = []
    for _, row in df_filtrado.iterrows():
        dominios = row["metrics"].get("domains", {})
        for dom, val in dominios.items():
            dominios_data.append({"Domínio": dom, "Valor": val})

    df_dominios = pd.DataFrame(dominios_data)

    if not df_dominios.empty:
        # Agrupar e pegar top 10
        df_top = df_dominios.groupby("Domínio")["Valor"].sum().sort_values(ascending=False).head(10).reset_index()

        # Ordenação explícita para o eixo Y
        df_top["Domínio"] = pd.Categorical(df_top["Domínio"], categories=df_top["Domínio"], ordered=True)

        # Gráfico Altair
        chart = alt.Chart(df_top).mark_bar(color="#0000CD").encode(
            y=alt.Y("Domínio:N", title="", sort=list(df_top["Domínio"])),
            x=alt.X(
                "Valor:Q",
                title="",
                axis=alt.Axis(
                    labelExpr="datum.value >= 1000000 ? (datum.value / 1000000) + 'M' : datum.value"
                ),
                scale=alt.Scale(domain=[0, df_top["Valor"].max() * 1.1])
            ),
            tooltip=[
                alt.Tooltip("Domínio:N", title="Domínio"),
                alt.Tooltip("Valor:Q", title="Valor", format=",")
            ]
        ).properties(width=700, height=400)

        st.altair_chart(chart, use_container_width=True)

    else:
        st.write("Sem dados de domínios para exibir.")
