import streamlit as st

from PIL import Image
from streamlit_autorefresh import st_autorefresh
from streamlit_option_menu import option_menu

from conectaBanco import conectaBanco
from cadastra_user import trocar_senha, adicionar_usuario
from login import login, is_authenticated
from api import atualizar_dados, buscar_dados
from auxiliar import obter_ultima_atualizacao, atualizacao_periodica
from pagina_dsar import pagina_dsar
from pagina_cookies import pagina_cookies
from aux_cookies import fetch_missing_data, processar_para_mongo

# Verifica se o usuário está autenticado
if not is_authenticated():
    login()
    st.stop()

# Verifica a role do usuário logado
user_role = st.session_state.get('role', '')

# Carregar credenciais do banco de dados
db_user = st.secrets["database"]["user"]
db_password = st.secrets["database"]["password"]

# Conexão com o banco de dados
collection = conectaBanco(db_user, db_password)

# Carregar logos
logo_carrefour = Image.open("logo.png")
logo_century = Image.open("logo_century.png")

# Configurações da página com o logo
st.set_page_config(page_title="Century Data", page_icon="Century_mini_logo-32x32.png", layout="wide")

# Atualizar a cada 5 minutos (300 segundos)
count = st_autorefresh(interval=3600000, key="data_refresh")
atualizacao_periodica()

# Conectar à collection de histórico de atualizações
collection_historico = conectaBanco(db_user, db_password)['historico_atualizacoes']

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
    
    atualizar_dados(collection, collection_historico)

    dados = buscar_dados(collection)  # Inicializa dados antes do botão

    # Exibir a última atualização
    ultima_atualizacao = obter_ultima_atualizacao(collection_historico)
    st.write(f"Última atualização: {ultima_atualizacao}")


    # Determinar opções do menu com base na role
    menu_options = ["Dashboard DSAR", "Dashboard Cookies", "Trocar Senha"]
    menu_icons = ["bar-chart", "bar-chart", "key"]

    if user_role == "admin":
        menu_options.append("Cadastrar Novo Usuário")
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
elif selected_tab == "Dashboard Cookies":
    pagina_cookies()
            
# Aba de Relatórios
elif selected_tab == "Trocar Senha":
    trocar_senha()
            
# Aba de Relatórios
elif selected_tab == "Cadastrar Novo Usuário":        
    adicionar_usuario()
    
# Aba de Relatórios
elif selected_tab == "Upload Cookies":        
    fetch_missing_data()
    processar_para_mongo()