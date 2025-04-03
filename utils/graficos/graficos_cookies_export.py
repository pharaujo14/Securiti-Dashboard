import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import matplotlib.ticker as mticker
import numpy as np

plt.rcParams.update({
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.facecolor": "white",
    "axes.edgecolor": "black"
})

def formatar_numero(x, pos):
    if x >= 1e6:
        return f"{x/1e6:.1f}M"
    elif x >= 1e3:
        return f"{x/1e3:.0f}k"
    return f"{int(x)}"

def adicionar_rotulos(ax, barras, formatter):
    for bar in barras:
        width = bar.get_width() if isinstance(bar, plt.Rectangle) else bar.get_height()
        x = bar.get_x() + bar.get_width()/2 if isinstance(bar, plt.Rectangle) else width
        y = bar.get_y() + bar.get_height()/2
        ax.text(x + width*0.05, y, 
                formatter(width, None), 
                ha='left', va='center', 
                fontsize=8)

def gerar_grafico_consents_img(df_filtrado):
    df_group = df_filtrado.groupby('organization_label')['total_consents'].sum().reset_index()
    df_group = df_group.sort_values(by='total_consents', ascending=True)  # Ordenado para gráfico horizontal
    
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(df_group['organization_label'], df_group['total_consents'], color="#3BA1E3")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(formatar_numero))
    adicionar_rotulos(ax, bars, formatar_numero)
    ax.set_xlabel('')
    ax.set_ylabel('')
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

def gerar_grafico_categorias_img(df_filtrado):
    categorias_data = []
    for _, row in df_filtrado.iterrows():
        dominios = row['metrics'].get('domains', {})
        categorias = row['metrics'].get('categories', {})
        for dom in dominios.keys():
            for cat, val in categorias.items():
                if val > 0:  # Filtra valores zero
                    categorias_data.append({"Domínio": dom, "Categoria": cat, "Valor": val})

    df = pd.DataFrame(categorias_data)
    if df.empty:
        return None
    
    # Ordena domínios por valor total (decrescente)
    dominio_order = df.groupby("Domínio")["Valor"].sum().sort_values(ascending=False).index
    top5 = dominio_order[:5]  # Pega os top 5 domínios
    
    # Filtra apenas os top 5 domínios
    df = df[df["Domínio"].isin(top5)]
    
    # Ordena categorias por valor total (decrescente)
    cat_order = df.groupby("Categoria")["Valor"].sum().sort_values(ascending=False).index
    
    # Converte para categorical para manter a ordem
    df["Domínio"] = pd.Categorical(df["Domínio"], categories=top5)
    df["Categoria"] = pd.Categorical(df["Categoria"], categories=cat_order)
    df = df.sort_values(["Domínio", "Categoria"])
    
    # Agrupa os dados para o gráfico
    df_grouped = df.groupby(["Domínio", "Categoria"])["Valor"].sum().unstack().fillna(0)
    
    # Cores para as categorias
    cores = plt.cm.tab10.colors
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Plotagem das barras agrupadas - agora em ordem decrescente
    bottom = np.zeros(len(df_grouped))
    for i, (categoria, valores) in enumerate(df_grouped.items()):
        bars = ax.bar(df_grouped.index, valores, bottom=bottom, 
                     label=categoria, color=cores[i % len(cores)])
        
        # Adiciona rótulos apenas para segmentos significativos
        for idx, (dom, val) in enumerate(zip(df_grouped.index, valores)):
            if val > 0:
                y_pos = bottom[idx] + val/2
                ax.text(idx, y_pos, 
                       formatar_numero(val, None), 
                       ha='center', va='center', 
                       fontsize=7, color='white')
        bottom += valores
    
    # Configurações do gráfico
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(formatar_numero))
    ax.set_ylabel('Quantidade de Cookies')
    ax.set_title('Categorias de Cookies por Domínio (Top 5) - Ordem Decrescente')
    
    # Rotaciona labels do eixo X para melhor visualização
    plt.xticks(rotation=45, ha='right')
    
    # Legenda fora do gráfico
    ax.legend(title='Categorias', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def gerar_grafico_paises_img(df_filtrado):
    paises_data = []
    for _, row in df_filtrado.iterrows():
        paises = row['metrics'].get('countries', {})
        for pais, val in paises.items():
            paises_data.append({"País": pais, "Valor": val})

    df = pd.DataFrame(paises_data)
    if df.empty:
        return None
    
    # Ordenar do maior para o menor
    df = df.groupby("País")["Valor"].sum().nlargest(10).reset_index()
    df = df.sort_values(by="Valor", ascending=True)  # Para gráfico horizontal
    
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(df["País"], df["Valor"], color="#3BA1E3")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(formatar_numero))
    adicionar_rotulos(ax, bars, formatar_numero)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf

def gerar_grafico_dominios_img(df_filtrado):
    dominios_data = []
    for _, row in df_filtrado.iterrows():
        dominios = row['metrics'].get('domains', {})
        for dom, val in dominios.items():
            dominios_data.append({"Domínio": dom, "Valor": val})

    df = pd.DataFrame(dominios_data)
    if df.empty:
        return None
    
    # Ordenar do maior para o menor
    df = df.groupby("Domínio")["Valor"].sum().nlargest(10).reset_index()
    df = df.sort_values(by="Valor", ascending=True)  # Para gráfico horizontal
    
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(df["Domínio"], df["Valor"], color="#3BA1E3")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(formatar_numero))
    adicionar_rotulos(ax, bars, formatar_numero)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf