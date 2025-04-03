import streamlit as st
import bcrypt

from utils.logos.import_logos import logo_century

# Função para autenticação
def login(db):
    # Configurações da página com o logo
    st.set_page_config(page_title="Century Data", page_icon="Century_mini_logo-32x32.png")

    # Adiciona o logo ao topo da página
    logo = logo_century()
    st.image(logo, use_column_width=True)

    # Campos de entrada para o usuário e senha
    st.title("Login")

    # Aqui permite que o Enter envie o formulário de login
    login_form = st.form(key="login_form")
    username = login_form.text_input("Usuário")
    password = login_form.text_input("Senha", type="password")

    # Validação das credenciais ao enviar o formulário
    login_button = login_form.form_submit_button("Entrar")

    if login_button:
        users_collection = db["users"]  # Nome da sua collection de usuários
        user_data = users_collection.find_one({"username": username})

        if user_data:
            # Verifica a senha com bcrypt
            if bcrypt.checkpw(password.encode("utf-8"), user_data["password"]):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['role'] = user_data["role"]  # Armazena a role do usuário
                st.success(f"Bem-vindo, {username}!")
                st.experimental_rerun()  # Recarrega a página após o login
            else:
                st.error("Usuário ou senha incorretos.")
        else:
            st.error("Usuário ou senha incorretos.")

# Função para verificar se o usuário está autenticado
def is_authenticated():
    return st.session_state.get('logged_in', False)