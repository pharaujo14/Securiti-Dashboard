import streamlit as st
import bcrypt

from pymongo import MongoClient

from conectaBanco import conectaBanco

# Função para adicionar um novo usuário ao MongoDB com senha criptografada (usado para fins de administração)
def adicionar_usuario(username, senha):
    # Carregar credenciais do banco de dados
    db_user = st.secrets["database"]["user"]
    db_password = st.secrets["database"]["password"]

    # Conexão com o banco de dados
    db = conectaBanco(db_user, db_password)
    users_collection = db["users"]
    hashed_password = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())
    users_collection.insert_one({"username": username, "password": hashed_password})
    st.success(f"Usuário {username} adicionado com sucesso.")

# Função para troca de senha
def trocar_senha():
    # Carregar credenciais do banco de dados
    db_user = st.secrets["database"]["user"]
    db_password = st.secrets["database"]["password"]

    db = conectaBanco(db_user, db_password)
    users_collection = db["users"]
    username = st.session_state.get('username')

    if not username:
        st.error("Você precisa estar logado para trocar a senha.")
        return

    with st.form("form_trocar_senha"):
        st.write("Troca de Senha")
        senha_atual = st.text_input("Senha Atual", type="password")
        nova_senha = st.text_input("Nova Senha", type="password")
        confirmar_nova_senha = st.text_input("Confirmar Nova Senha", type="password")
        senha_valida = validar_senha(nova_senha) and nova_senha == confirmar_nova_senha

        trocar_button = st.form_submit_button("Alterar Senha")

        if trocar_button:
            user_data = users_collection.find_one({"username": username})
            if user_data:
                if bcrypt.checkpw(senha_atual.encode("utf-8"), user_data["password"]):
                    if senha_valida:
                        nova_senha_hash = bcrypt.hashpw(nova_senha.encode("utf-8"), bcrypt.gensalt())
                        users_collection.update_one({"username": username}, {"$set": {"password": nova_senha_hash}})
                        st.success("Senha alterada com sucesso!")
                        st.session_state.mostrar_form_troca_senha = False  # Oculta o formulário após sucesso
                    else:
                        if nova_senha != confirmar_nova_senha:
                            st.warning('As senhas não coincidem.')
                        elif not validar_senha(nova_senha):
                            st.warning('A senha deve conter no mínimo 8 caracteres e conter letra maiúscula, minúscula, número e caractere especial.')
                else:
                    st.error("A senha atual está incorreta.")
            else:
                st.error("Usuário não encontrado.")
                
def validar_senha(senha):
    return (
        len(senha) >= 8 and
        any(c.isupper() for c in senha) and
        any(c.islower() for c in senha) and
        any(c.isdigit() for c in senha) and
        any(not c.isalnum() for c in senha)
    )

# adicionar_usuario("anderson.franca@centurydata.com.br", "Teste@12345")

# adicionar_usuario("malu_gallotti@carrefour.com", "e2@TcANvq8u")
# adicionar_usuario("fernanda_lobato@carrefour.com", "nLRwO#V8Q1s")
# adicionar_usuario("yasmin_silva_17@carrefour.com", "oBhLsqMU$4p")
# adicionar_usuario("mariana_girondi@carrefour.com", "jkVAU&EZxOC")
# adicionar_usuario("danilo_kinoshita@carrefour.com", "yyufTnAyQ#8")