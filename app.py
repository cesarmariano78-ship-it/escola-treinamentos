import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Escola de Treinamentos",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CONEXÃO COM SUPABASE
# ============================================================
@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# ============================================================
# ESTILOS
# ============================================================
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .login-box {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 2px 16px rgba(0,0,0,0.08);
        max-width: 400px;
        margin: auto;
    }
    .stButton > button {
        background-color: #2C5282;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #2a4a7f;
    }
    .perfil-badge {
        background: #EBF4FF;
        color: #2C5282;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# FUNÇÕES DE AUTENTICAÇÃO
# ============================================================
def fazer_login(email, senha):
    try:
        resposta = supabase.auth.sign_in_with_password({
            "email": email,
            "password": senha
        })
        return resposta.user, None
    except Exception as e:
        return None, str(e)

def buscar_perfil(user_id):
    try:
        resultado = supabase.table("perfis").select("*").eq("user_id", user_id).execute()
        if resultado.data and len(resultado.data) > 0:
            return resultado.data[0]
        return None
    except Exception as e:
        st.error(f"Erro ao buscar perfil: {e}")
        return None
def buscar_permissoes(user_id):
    try:
        resultado = supabase.table("permissoes").select("*").eq("user_id", user_id).execute()
        permissoes = {}
        for p in resultado.data:
            permissoes[p["modulo"]] = p["nivel"]
        return permissoes
    except:
        return {}

def tem_acesso(modulo, nivel_minimo="leitura"):
    perfil = st.session_state.get("perfil")
    permissoes = st.session_state.get("permissoes", {})

    if not perfil:
        return False

    # Gestor tem acesso total a tudo
    if perfil["tipo"] == "gestor":
        return True

    nivel = permissoes.get(modulo, "sem_acesso")
    ordem = {"sem_acesso": 0, "leitura": 1, "total": 2}
    return ordem.get(nivel, 0) >= ordem.get(nivel_minimo, 1)

def fazer_logout():
    supabase.auth.sign_out()
    for key in ["user", "perfil", "permissoes"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ============================================================
# TELA DE LOGIN
# ============================================================
def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🎓 Escola de Treinamentos")
        st.markdown("---")
        st.markdown("### Acesse sua conta")

        email = st.text_input("E-mail", placeholder="seu@email.com")
        senha = st.text_input("Senha", type="password", placeholder="••••••••")

        if st.button("Entrar"):
            if not email or not senha:
                st.warning("Preencha e-mail e senha.")
            else:
                with st.spinner("Verificando..."):
                    user, erro = fazer_login(email, senha)
                    if user:
                        perfil = buscar_perfil(user.id)
                        if not perfil:
                            st.error("Usuário sem perfil configurado. Contate o gestor.")
                        elif not perfil.get("ativo"):
                            st.error("Acesso desativado. Contate o gestor.")
                        else:
                            st.session_state["user"] = user
                            st.session_state["perfil"] = perfil
                            st.session_state["permissoes"] = buscar_permissoes(user.id)
                            st.success(f"Bem-vindo, {perfil['nome']}!")
                            st.rerun()
                    else:
                        st.error("E-mail ou senha incorretos.")

# ============================================================
# MENU LATERAL
# ============================================================
def menu_lateral():
    perfil = st.session_state.get("perfil", {})

    with st.sidebar:
        st.markdown(f"### 🎓 Escola")
        st.markdown(f"**{perfil.get('nome', '')}**")
        st.markdown(f"<span class='perfil-badge'>{perfil.get('tipo', '').capitalize()}</span>", unsafe_allow_html=True)
        st.markdown("---")

        opcoes = []

        if tem_acesso("clientes"):
            opcoes.append("👥 Clientes")
        if tem_acesso("crm"):
            opcoes.append("📊 CRM / Leads")
        if tem_acesso("turmas"):
            opcoes.append("📚 Turmas")
        if tem_acesso("financeiro"):
            opcoes.append("💰 Financeiro")
        if tem_acesso("propostas"):
            opcoes.append("📄 Propostas")
        if tem_acesso("certificados"):
            opcoes.append("🏆 Certificados")
        if tem_acesso("recompensas"):
            opcoes.append("⭐ Recompensas")
        if tem_acesso("relatorios"):
            opcoes.append("📈 Relatórios")
        if perfil.get("tipo") == "gestor":
            opcoes.append("⚙️ Usuários")

        if opcoes:
            pagina = st.selectbox("Menu", opcoes, label_visibility="collapsed")
        else:
            st.info("Nenhum módulo disponível.")
            pagina = None

        st.markdown("---")
        if st.button("🚪 Sair"):
            fazer_logout()

    return pagina

# ============================================================
# PÁGINAS DOS MÓDULOS (placeholders — serão construídos um a um)
# ============================================================
def pagina_clientes():
    from modulo_clientes import pagina_clientes as _pagina_clientes
    _pagina_clientes()

def pagina_crm():
    from modulo_crm import pagina_crm as _pagina_crm
    _pagina_crm()

def pagina_turmas():
    from modulo_turmas import pagina_turmas as _pagina_turmas
    _pagina_turmas()

def pagina_financeiro():
    from modulo_financeiro import pagina_financeiro as _pagina_financeiro
    _pagina_financeiro()

def pagina_propostas():
    st.title("📄 Propostas")
    st.info("Módulo em construção.")

def pagina_certificados():
    from modulo_certificados import pagina_certificados as _pagina_certificados
    _pagina_certificados()

def pagina_recompensas():
    from modulo_recompensas import pagina_recompensas as _pagina_recompensas
    _pagina_recompensas()

def pagina_relatorios():
    from modulo_dashboard import pagina_dashboard as _dash
    _dash()

def pagina_usuarios():
    from modulo_usuarios import pagina_usuarios as _pagina_usuarios
    _pagina_usuarios()
# ============================================================
# ROTEADOR PRINCIPAL
# ============================================================
def main():
    if "user" not in st.session_state:
        tela_login()
    else:
        pagina = menu_lateral()

        if pagina == "👥 Clientes":
            pagina_clientes()
        elif pagina == "📊 CRM / Leads":
            pagina_crm()
        elif pagina == "📚 Turmas":
            pagina_turmas()
        elif pagina == "💰 Financeiro":
            pagina_financeiro()
        elif pagina == "📄 Propostas":
            pagina_propostas()
        elif pagina == "🏆 Certificados":
            pagina_certificados()
        elif pagina == "⭐ Recompensas":
            pagina_recompensas()
        elif pagina == "📈 Relatórios":
            pagina_relatorios()
        elif pagina == "⚙️ Usuários":
            pagina_usuarios()
        else:
            from modulo_dashboard import pagina_dashboard
            pagina_dashboard()

if __name__ == "__main__":
    main()