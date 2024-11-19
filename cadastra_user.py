import streamlit as st
import bcrypt

from pymongo import MongoClient

from conectaBanco import conectaBanco

# Função para adicionar um novo usuário ao MongoDB com senha criptografada e função (usado para fins de administração)
def adicionar_usuario(username, senha, role):
    # Validar a senha
    if not validar_senha(senha):
        st.error("A senha deve ter pelo menos 8 caracteres, incluir letras maiúsculas, minúsculas, números e caracteres especiais.")
        return
    
    # Verificar se a função é válida
    if role not in ["admin", "user"]:
        st.error("A função deve ser 'admin' ou 'user'.")
        return

    # Carregar credenciais do banco de dados
    db_user = st.secrets["database"]["user"]
    db_password = st.secrets["database"]["password"]

    # Conexão com o banco de dados
    db = conectaBanco(db_user, db_password)
    users_collection = db["users"]
    
    # Criptografar e inserir a senha no banco
    hashed_password = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())
    users_collection.insert_one({
        "username": username,
        "password": hashed_password,
        "role": role
    })
    st.success(f"Usuário {username} com função '{role}' adicionado com sucesso.")

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

# adicionar_usuario("rena_melo_santos@carrefour.com", "k8~$0<58Hl)V")
# adicionar_usuario("thiago_roberto_faria_lima@carrefour.com", "q#z5$Gx4s\^8")
# adicionar_usuario("carlos_barreto_1@carrefour.com", "o3<9||2Wi0V!")
# adicionar_usuario("gabriel_benedocci@carrefour.com", "k8+d9B)N5,c%")
# adicionar_usuario("guilherme_pedroso@carrefour.com", "43_IN3Tmv}\F")
# adicionar_usuario("rogerio_iwashita@carrefour.com", "CtJ@4M8&2!6_")