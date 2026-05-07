import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MODULOS = [
    "clientes", "crm", "turmas", "financeiro",
    "certificados", "propostas", "relatorios", "recompensas"
]

NIVEIS = ["sem_acesso", "leitura", "total"]

NIVEIS_LABEL = {
    "sem_acesso": "🔒 Sem acesso",
    "leitura": "👁️ Somente leitura",
    "total": "✅ Acesso total"
}

MODULOS_LABEL = {
    "clientes": "👥 Clientes",
    "crm": "📊 CRM / Leads",
    "turmas": "📚 Turmas",
    "financeiro": "💰 Financeiro",
    "certificados": "🏆 Certificados",
    "propostas": "📄 Propostas",
    "relatorios": "📈 Relatórios",
    "recompensas": "⭐ Recompensas"
}

PERFIL_PADRAO = {
    "gestor":     {m: "total" for m in MODULOS},
    "vendedor":   {"clientes": "total", "crm": "total", "propostas": "total",
                   "turmas": "leitura", "certificados": "sem_acesso",
                   "financeiro": "sem_acesso", "relatorios": "leitura", "recompensas": "leitura"},
    "instrutor":  {"turmas": "total", "clientes": "leitura", "certificados": "total",
                   "crm": "sem_acesso", "financeiro": "sem_acesso",
                   "propostas": "sem_acesso", "relatorios": "sem_acesso", "recompensas": "sem_acesso"},
    "financeiro": {"financeiro": "total", "clientes": "leitura", "relatorios": "total",
                   "crm": "sem_acesso", "turmas": "leitura", "certificados": "sem_acesso",
                   "propostas": "leitura", "recompensas": "leitura"},
    "aluno":      {m: "sem_acesso" for m in MODULOS}
}

def listar_usuarios():
    try:
        resultado = supabase.table("perfis").select("*").order("nome").execute()
        return resultado.data or []
    except Exception as e:
        st.error(f"Erro ao listar usuários: {e}")
        return []

def buscar_permissoes_usuario(user_id):
    try:
        resultado = supabase.table("permissoes").select("*").eq("user_id", user_id).execute()
        perms = {}
        for p in resultado.data:
            perms[p["modulo"]] = p["nivel"]
        return perms
    except:
        return {}

def salvar_permissoes(user_id, permissoes):
    try:
        for modulo, nivel in permissoes.items():
            supabase.table("permissoes").upsert({
                "user_id": user_id,
                "modulo": modulo,
                "nivel": nivel
            }, on_conflict="user_id,modulo").execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar permissões: {e}")
        return False

def criar_usuario(nome, email, senha, tipo):
    try:
        # Cria no Auth do Supabase
        resp = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": senha,
            "email_confirm": True
        })
        user_id = resp.user.id

        # Cria perfil
        supabase.table("perfis").insert({
            "user_id": user_id,
            "nome": nome,
            "email": email,
            "tipo": tipo,
            "ativo": True
        }).execute()

        # Aplica permissões padrão do perfil
        perms_padrao = PERFIL_PADRAO.get(tipo, {})
        salvar_permissoes(user_id, perms_padrao)

        return True, user_id
    except Exception as e:
        return False, str(e)

def alternar_status(user_id, status_atual):
    try:
        supabase.table("perfis").update({
            "ativo": not status_atual
        }).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

# ============================================================
# INTERFACE PRINCIPAL
# ============================================================
def pagina_usuarios():
    st.title("⚙️ Gestão de Usuários")

    aba1, aba2 = st.tabs(["👥 Usuários", "➕ Novo Usuário"])

    # ── ABA 1: LISTAR USUÁRIOS ──
    with aba1:
        usuarios = listar_usuarios()

        if not usuarios:
            st.info("Nenhum usuário cadastrado ainda.")
        else:
            for u in usuarios:
                with st.expander(f"{'🟢' if u['ativo'] else '🔴'} {u['nome']} — {u['tipo'].capitalize()}"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(f"**E-mail:** {u['email']}")
                        st.markdown(f"**Perfil:** {u['tipo'].capitalize()}")
                        st.markdown(f"**Status:** {'Ativo' if u['ativo'] else 'Desativado'}")

                    with col2:
                        label_btn = "Desativar" if u['ativo'] else "Reativar"
                        if st.button(label_btn, key=f"status_{u['user_id']}"):
                            if alternar_status(u['user_id'], u['ativo']):
                                st.success("Status atualizado!")
                                st.rerun()

                    # Permissões
                    if u['tipo'] != 'gestor':
                        st.markdown("---")
                        st.markdown("**Permissões por módulo:**")
                        perms_atuais = buscar_permissoes_usuario(u['user_id'])

                        novas_perms = {}
                        cols = st.columns(2)
                        for i, modulo in enumerate(MODULOS):
                            with cols[i % 2]:
                                nivel_atual = perms_atuais.get(modulo, "sem_acesso")
                                opcoes = list(NIVEIS_LABEL.values())
                                idx = NIVEIS.index(nivel_atual) if nivel_atual in NIVEIS else 0
                                escolha = st.selectbox(
                                    MODULOS_LABEL[modulo],
                                    opcoes,
                                    index=idx,
                                    key=f"perm_{u['user_id']}_{modulo}"
                                )
                                novas_perms[modulo] = NIVEIS[opcoes.index(escolha)]

                        if st.button("💾 Salvar permissões", key=f"salvar_{u['user_id']}"):
                            if salvar_permissoes(u['user_id'], novas_perms):
                                st.success("Permissões salvas com sucesso!")
                    else:
                        st.info("Gestor tem acesso total a todos os módulos.")

    # ── ABA 2: NOVO USUÁRIO ──
    with aba2:
        st.markdown("### Criar novo usuário")

        nome = st.text_input("Nome completo")
        email = st.text_input("E-mail")
        senha = st.text_input("Senha inicial", type="password",
                              help="O usuário poderá alterar depois")
        tipo = st.selectbox("Perfil", ["vendedor", "instrutor", "financeiro", "aluno", "gestor"])

        st.markdown("---")
        st.markdown("**Permissões iniciais** — baseadas no perfil selecionado. Você pode ajustar depois.")

        perms_preview = PERFIL_PADRAO.get(tipo, {})
        cols = st.columns(2)
        for i, modulo in enumerate(MODULOS):
            with cols[i % 2]:
                nivel = perms_preview.get(modulo, "sem_acesso")
                st.markdown(f"{MODULOS_LABEL[modulo]}: **{NIVEIS_LABEL[nivel]}**")

        st.markdown("---")
        if st.button("✅ Criar usuário"):
            if not nome or not email or not senha:
                st.warning("Preencha todos os campos.")
            elif len(senha) < 6:
                st.warning("A senha precisa ter pelo menos 6 caracteres.")
            else:
                with st.spinner("Criando usuário..."):
                    ok, resultado = criar_usuario(nome, email, senha, tipo)
                    if ok:
                        st.success(f"Usuário {nome} criado com sucesso!")
                        st.balloons()
                    else:
                        st.error(f"Erro ao criar usuário: {resultado}")