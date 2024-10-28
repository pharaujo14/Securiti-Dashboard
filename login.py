import streamlit as st

# Função de autenticação
def login():

    # Configurações da página com o logo
    st.set_page_config(page_title="Century Data", page_icon="Century_mini_logo-32x32.png")

    # Adiciona o logo ao topo da página
    st.image("logo_century.png", use_column_width=True)

    # Obtém as credenciais do arquivo secrets.toml
    credentials = st.secrets["credentials"]

    # Campos de entrada para o usuário e senha
    st.title("Login")
    
    # Aqui permite que o Enter envie o formulário de login
    login_form = st.form(key="login_form")
    username = login_form.text_input("Usuário")
    password = login_form.text_input("Senha", type="password")

    # Validação das credenciais ao enviar o formulário
    login_button = login_form.form_submit_button("Entrar")

    if login_button:
        if username in credentials and password == credentials[username]:
            st.session_state['logged_in'] = True
            st.session_state['username'] = username  # Salva o nome do usuário na sessão
            st.success(f"Bem-vindo, {username}!")
            st.experimental_rerun()  # Força a página a recarregar após o login
        else:
            st.error("Usuário ou senha incorretos.")

# Verifica o estado de login
def is_authenticated():
    return st.session_state.get('logged_in', False)
