import streamlit as st

from streamlit_autorefresh import st_autorefresh
from streamlit_option_menu import option_menu

from pagina_dsar import pagina_dsar
from pagina_cookies import pagina_cookies
from pagina_trocarSenha import trocar_senha
from pagina_usuarios import gerenciar_usuarios
from pagina_atualizar_cookies import fetch_missing_data, processar_para_mongo
from pagina_gerador_pia import gerador_pia

from utils.login import login, is_authenticated
from utils.conectaBanco import conectaBanco
from utils.api import atualizar_dados, buscar_dados
from utils.auxiliar import obter_ultima_atualizacao
from utils.logos.import_logos import logo_carrefour, logo_century

# Verifica a role do usuário logado
user_role = st.session_state.get('role', '')

# Carregar credenciais do banco de dados
db_user = st.secrets["database"]["user"]
db_password = st.secrets["database"]["password"]

# Conexão com o banco de dados (agora cacheada com st.cache_resource — ver
# utils/conectaBanco.py — então isso não abre uma conexão nova a cada rerun)
collection = conectaBanco(db_user, db_password)

# Verifica se o usuário está autenticado
if not is_authenticated():
    login(collection)
    st.stop()

# Carregar logos
logo_carrefour = logo_carrefour()
logo_century = logo_century()

# Configurações da página com o logo
st.set_page_config(page_title="Century Data", page_icon="./utils/logos/Century_mini_logo-32x32.png", layout="wide")

# Atualiza a tela a cada 5 minutos, alinhado com o TTL do cache de dados
# (utils/api.buscar_dados). Isto só reflete dados novos que o job agendado
# (GitHub Actions, ver scripts/sync_dsar.py) já tiver gravado no Mongo — o
# autorefresh NÃO dispara mais nenhuma sincronização com a API da Securiti,
# então navegar no dashboard continua rápido mesmo com isso ligado.
st_autorefresh(interval=300000, key="data_refresh")

# Sub-coleção de histórico de atualizações (mesmo caminho que o job agendado usa)
collection_historico = collection['historico_atualizacoes']

# Definir as colunas da primeira linha do layout
col1, col2, col3 = st.columns([1, 3, 1])

# Exibir os logos e o título na primeira linha
with col1:
    st.image(logo_carrefour, width=150)

with col2:
    st.markdown("<h1 style='text-align: center; color: black;'>Atendimento da Central de Privacidade</h1>", unsafe_allow_html=True)

with col3:
    st.image(logo_century, width=150)

# Linha separadora vermelha para o "Atendimento"
st.markdown("<hr style='border:3px solid red'>", unsafe_allow_html=True)

# Filtros e seleção de período
with st.sidebar:

    st.image(logo_century, width=150)

    # A sincronização com a API da Securiti NÃO roda mais aqui a cada carregamento
    # de página — isso é feito por um job agendado (GitHub Actions, de hora em
    # hora). Aqui só LEMOS o que já está no Mongo, com cache de 5 min.
    dados = buscar_dados(collection)

    # Exibir a última atualização (agora é a última execução do job agendado)
    ultima_atualizacao = obter_ultima_atualizacao(collection_historico)
    st.write(f"Última atualização: {ultima_atualizacao}")

    # Botão de fallback manual, só pra admin: útil se precisar forçar uma
    # atualização fora do horário do job, ou pra depurar algo na hora.
    # Isso NÃO deveria ser o mecanismo principal de atualização — é um extra.
    if user_role == "admin":
        if st.button("🔄 Forçar atualização agora", key="forcar_atualizacao_dsar"):
            with st.spinner("Buscando dados mais recentes na API..."):
                try:
                    atualizar_dados(collection, collection_historico)
                    buscar_dados.clear()  # invalida o cache pra refletir os dados novos
                    st.success("Dados atualizados.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Falha ao atualizar: {e}")

    # Determinar opções do menu com base na role
    menu_options = ["Dashboard DSAR", "Dashboard Cookies", "Gerador de PDF do PIA em preenchimento", "Trocar Senha"]
    menu_icons = ["bar-chart", "bar-chart", "upload", "key"]

    if user_role == "admin":
        menu_options.append("Controle de usuários")
        menu_icons.append("person-plus")

        menu_options.append("Upload Cookies")
        menu_icons.append("key")


    # Configuração do menu dinâmico
    selected_tab = option_menu(
        menu_title="Menu Principal",
        options=menu_options,
        icons=menu_icons,
        menu_icon="list",
        default_index=0,
    )

# Aba de Dashboard DSAR
if selected_tab == "Dashboard DSAR":
    pagina_dsar(dados)

# Aba de Relatórios
elif selected_tab == "Gerador de PDF do PIA em preenchimento":
    gerador_pia()

 # Aba de Relatórios
elif selected_tab == "Dashboard Cookies":
    pagina_cookies(collection)

# Aba de Relatórios
elif selected_tab == "Trocar Senha":
    trocar_senha(collection)

# Aba de Relatórios
elif selected_tab == "Controle de usuários":
    gerenciar_usuarios(collection)

# Aba de Relatórios — mantida como fallback manual (a sincronização "de verdade"
# agora roda via GitHub Actions, ver scripts/sync_cookies.py)
elif selected_tab == "Upload Cookies":
    st.info("A sincronização diária de cookies agora roda automaticamente via GitHub Actions. "
            "Use os botões abaixo só se precisar forçar uma atualização manual.")
    if st.button("Buscar dados ausentes agora"):
        fetch_missing_data()
    if st.button("Processar para o Mongo agora"):
        processar_para_mongo(collection)
