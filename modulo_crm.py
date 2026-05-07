import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ESTAGIOS = {
    "novo": "🆕 Novo",
    "em_negociacao": "💬 Em negociação",
    "proposta_enviada": "📄 Proposta enviada",
    "aguardando_pagamento": "💰 Aguardando pagamento",
    "matriculado": "✅ Matriculado",
    "perdido": "❌ Perdido"
}

CORES_ESTAGIO = {
    "novo": "#EBF4FF",
    "em_negociacao": "#FFF3CD",
    "proposta_enviada": "#E8F5E9",
    "aguardando_pagamento": "#FFF8E1",
    "matriculado": "#E8F5E9",
    "perdido": "#FFEBEE"
}

TIPOS_FOLLOWUP = ["ligacao", "whatsapp", "email", "reuniao", "anotacao"]
TIPOS_FOLLOWUP_LABEL = {
    "ligacao": "📞 Ligação",
    "whatsapp": "💬 WhatsApp",
    "email": "📧 E-mail",
    "reuniao": "🤝 Reunião",
    "anotacao": "📝 Anotação"
}

# ============================================================
# FUNÇÕES DE DADOS
# ============================================================
def get_user_id():
    user = st.session_state.get("user")
    return user.id if user else None

def is_gestor():
    perfil = st.session_state.get("perfil", {})
    return perfil.get("tipo") == "gestor"

def listar_leads(estagio=None):
    try:
        query = supabase.table("leads").select(
            "*, clientes(nome, telefone, email), perfis(nome)"
        ).order("criado_em", desc=True)

        if not is_gestor():
            query = query.eq("responsavel_id", get_user_id())

        if estagio and estagio != "todos":
            query = query.eq("estagio", estagio)

        resultado = query.execute()
        return resultado.data or []
    except Exception as e:
        st.error(f"Erro ao listar leads: {e}")
        return []

def listar_clientes_sem_lead():
    try:
        todos = supabase.table("clientes").select("id, nome, telefone").eq("ativo", True).order("nome").execute()
        com_lead = supabase.table("leads").select("cliente_id").execute()
        ids_com_lead = {l["cliente_id"] for l in com_lead.data}
        return [c for c in (todos.data or []) if c["id"] not in ids_com_lead]
    except:
        return []

def listar_todos_clientes():
    try:
        resultado = supabase.table("clientes").select("id, nome, telefone").eq("ativo", True).order("nome").execute()
        return resultado.data or []
    except:
        return []

def listar_vendedores():
    try:
        resultado = supabase.table("perfis").select("user_id, nome").in_(
            "tipo", ["vendedor", "gestor"]
        ).eq("ativo", True).order("nome").execute()
        return resultado.data or []
    except:
        return []

def criar_lead(dados):
    try:
        resultado = supabase.table("leads").insert(dados).execute()
        return True, resultado.data[0]["id"] if resultado.data else None
    except Exception as e:
        return False, str(e)

def atualizar_estagio(lead_id, novo_estagio):
    try:
        supabase.table("leads").update({
            "estagio": novo_estagio,
            "atualizado_em": datetime.now().isoformat()
        }).eq("id", lead_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

def transferir_lead(lead_id, novo_responsavel_id, responsavel_anterior_id, motivo=""):
    try:
        supabase.table("leads").update({
            "responsavel_id": novo_responsavel_id,
            "atualizado_em": datetime.now().isoformat()
        }).eq("id", lead_id).execute()

        supabase.table("leads_historico").insert({
            "lead_id": lead_id,
            "responsavel_anterior": responsavel_anterior_id,
            "responsavel_novo": novo_responsavel_id,
            "transferido_por": get_user_id(),
            "motivo": motivo
        }).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao transferir: {e}")
        return False

def listar_followups(lead_id):
    try:
        resultado = supabase.table("followups").select(
            "*, perfis(nome)"
        ).eq("lead_id", lead_id).order("criado_em", desc=True).execute()
        return resultado.data or []
    except:
        return []

def criar_followup(dados):
    try:
        supabase.table("followups").insert(dados).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao registrar follow-up: {e}")
        return False

def buscar_lead(lead_id):
    try:
        resultado = supabase.table("leads").select(
            "*, clientes(nome, telefone, email, origem), perfis(nome)"
        ).eq("id", lead_id).single().execute()
        return resultado.data
    except:
        return None

# ============================================================
# COMPONENTES VISUAIS
# ============================================================
def card_lead(lead, mostrar_botoes=True):
    cliente = lead.get("clientes") or {}
    responsavel = lead.get("perfis") or {}
    estagio = lead.get("estagio", "novo")
    cor = CORES_ESTAGIO.get(estagio, "#F7FAFC")

    with st.container():
        st.markdown(f"""
        <div style="background:{cor};padding:12px;border-radius:8px;margin-bottom:8px;border-left:4px solid #2C5282;">
            <strong>👤 {cliente.get('nome', '—')}</strong><br>
            📱 {cliente.get('telefone', '—')}<br>
            📚 {lead.get('curso_interesse', '—')}<br>
            👔 {responsavel.get('nome', '—')}
        </div>
        """, unsafe_allow_html=True)

        if mostrar_botoes:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 Detalhes", key=f"det_{lead['id']}"):
                    st.session_state["lead_ativo"] = lead["id"]
                    st.rerun()
            with col2:
                estagios_lista = list(ESTAGIOS.keys())
                idx_atual = estagios_lista.index(estagio) if estagio in estagios_lista else 0
                if idx_atual < len(estagios_lista) - 2:
                    proximo = estagios_lista[idx_atual + 1]
                    if st.button(f"▶ {ESTAGIOS[proximo].split(' ')[1]}", key=f"av_{lead['id']}"):
                        if atualizar_estagio(lead["id"], proximo):
                            st.rerun()

def painel_lead(lead_id):
    lead = buscar_lead(lead_id)
    if not lead:
        st.error("Lead não encontrado.")
        return

    cliente = lead.get("clientes") or {}
    responsavel = lead.get("perfis") or {}

    st.markdown(f"### 👤 {cliente.get('nome', '—')}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Telefone:** {cliente.get('telefone', '—')}")
        st.markdown(f"**E-mail:** {cliente.get('email', '—')}")
        st.markdown(f"**Origem:** {cliente.get('origem', '—')}")
    with col2:
        st.markdown(f"**Curso de interesse:** {lead.get('curso_interesse', '—')}")
        st.markdown(f"**Responsável:** {responsavel.get('nome', '—')}")
    with col3:
        estagio_atual = lead.get("estagio", "novo")
        novo_estagio = st.selectbox(
            "Estágio",
            list(ESTAGIOS.keys()),
            index=list(ESTAGIOS.keys()).index(estagio_atual),
            format_func=lambda x: ESTAGIOS[x],
            key="sel_estagio"
        )
        if novo_estagio != estagio_atual:
            if atualizar_estagio(lead_id, novo_estagio):
                st.success("Estágio atualizado!")
                st.rerun()

    # Transferência
    if is_gestor():
        with st.expander("🔄 Transferir responsável"):
            vendedores = listar_vendedores()
            nomes = [v["nome"] for v in vendedores]
            ids = [v["user_id"] for v in vendedores]
            resp_idx = ids.index(lead.get("responsavel_id")) if lead.get("responsavel_id") in ids else 0
            novo_resp = st.selectbox("Novo responsável", nomes, index=resp_idx)
            motivo = st.text_input("Motivo da transferência")
            if st.button("✅ Confirmar transferência"):
                novo_id = ids[nomes.index(novo_resp)]
                if transferir_lead(lead_id, novo_id, lead.get("responsavel_id"), motivo):
                    st.success("Lead transferido!")
                    st.rerun()

    st.markdown("---")

    # Follow-ups
    st.markdown("#### 📝 Follow-ups")
    followups = listar_followups(lead_id)

    with st.expander("➕ Registrar novo follow-up", expanded=True):
        tipo_sel = st.selectbox(
            "Tipo de contato",
            TIPOS_FOLLOWUP,
            format_func=lambda x: TIPOS_FOLLOWUP_LABEL[x]
        )
        descricao = st.text_area("O que foi conversado?", height=100)
        proximo = st.date_input("Próximo contato (opcional)", value=None)

        if st.button("💾 Salvar follow-up"):
            if not descricao:
                st.warning("Descreva o que foi conversado.")
            else:
                dados_fu = {
                    "lead_id": lead_id,
                    "user_id": get_user_id(),
                    "tipo": tipo_sel,
                    "descricao": descricao,
                    "data_contato": datetime.now().isoformat(),
                    "proximo_contato": proximo.isoformat() if proximo else None
                }
                if criar_followup(dados_fu):
                    st.success("Follow-up registrado!")
                    st.rerun()

    if followups:
        for fu in followups:
            autor = fu.get("perfis") or {}
            data = fu.get("data_contato", "")[:10] if fu.get("data_contato") else "—"
            tipo_label = TIPOS_FOLLOWUP_LABEL.get(fu.get("tipo", ""), "📝")
            proximo_txt = f" · Próximo: {fu['proximo_contato'][:10]}" if fu.get("proximo_contato") else ""
            st.markdown(f"""
            <div style="background:#F7FAFC;padding:10px;border-radius:8px;margin-bottom:6px;">
                {tipo_label} <strong>{data}</strong> — {autor.get('nome', '—')}{proximo_txt}<br>
                {fu.get('descricao', '')}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nenhum follow-up registrado ainda.")

    if st.button("← Voltar ao funil"):
        del st.session_state["lead_ativo"]
        st.rerun()

# ============================================================
# INTERFACE PRINCIPAL
# ============================================================
def pagina_crm():
    st.title("📊 CRM / Leads")

    # Se há um lead ativo, mostra o painel dele
    if "lead_ativo" in st.session_state:
        painel_lead(st.session_state["lead_ativo"])
        return

    aba1, aba2, aba3 = st.tabs(["📊 Kanban", "📋 Lista", "➕ Novo Lead"])

    # ── ABA 1: KANBAN ──
    with aba1:
        leads = listar_leads()

        if not leads:
            st.info("Nenhum lead cadastrado ainda. Crie um na aba 'Novo Lead'.")
        else:
            # Agrupa por estágio
            por_estagio = {e: [] for e in ESTAGIOS}
            for lead in leads:
                estagio = lead.get("estagio", "novo")
                if estagio in por_estagio:
                    por_estagio[estagio].append(lead)

            # Exibe em colunas — 3 por vez para caber na tela
            estagios_lista = list(ESTAGIOS.items())
            for i in range(0, len(estagios_lista), 3):
                cols = st.columns(3)
                for j, (estagio_key, estagio_label) in enumerate(estagios_lista[i:i+3]):
                    with cols[j]:
                        leads_estagio = por_estagio[estagio_key]
                        st.markdown(f"**{estagio_label}** ({len(leads_estagio)})")
                        st.markdown("---")
                        if leads_estagio:
                            for lead in leads_estagio:
                                card_lead(lead)
                        else:
                            st.markdown("<small>Nenhum lead</small>", unsafe_allow_html=True)

    # ── ABA 2: LISTA ──
    with aba2:
        col1, col2 = st.columns([2, 1])
        with col1:
            busca = st.text_input("🔍 Buscar por nome ou curso", placeholder="Digite para buscar...")
        with col2:
            filtro_estagio = st.selectbox(
                "Filtrar por estágio",
                ["todos"] + list(ESTAGIOS.keys()),
                format_func=lambda x: "Todos" if x == "todos" else ESTAGIOS[x]
            )

        leads = listar_leads(filtro_estagio)

        if busca:
            busca_lower = busca.lower()
            leads = [l for l in leads if
                     busca_lower in (l.get("clientes") or {}).get("nome", "").lower() or
                     busca_lower in (l.get("curso_interesse") or "").lower()]

        st.markdown(f"**{len(leads)} lead(s)**")
        st.markdown("---")

        for lead in leads:
            cliente = lead.get("clientes") or {}
            responsavel = lead.get("perfis") or {}
            estagio = lead.get("estagio", "novo")
            cor = CORES_ESTAGIO.get(estagio, "#F7FAFC")

            with st.expander(f"{ESTAGIOS[estagio]} · {cliente.get('nome', '—')} · {lead.get('curso_interesse', '—')}"):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**Cliente:** {cliente.get('nome', '—')}")
                    st.markdown(f"**Telefone:** {cliente.get('telefone', '—')}")
                    st.markdown(f"**Curso:** {lead.get('curso_interesse', '—')}")
                with col2:
                    st.markdown(f"**Responsável:** {responsavel.get('nome', '—')}")
                    st.markdown(f"**Estágio:** {ESTAGIOS[estagio]}")
                    criado = lead.get("criado_em", "")[:10] if lead.get("criado_em") else "—"
                    st.markdown(f"**Criado em:** {criado}")
                with col3:
                    if st.button("📋 Abrir", key=f"abrir_{lead['id']}"):
                        st.session_state["lead_ativo"] = lead["id"]
                        st.rerun()

    # ── ABA 3: NOVO LEAD ──
    with aba3:
        st.markdown("### Abrir novo lead")

        clientes = listar_todos_clientes()
        vendedores = listar_vendedores()

        if not clientes:
            st.warning("Cadastre um cliente primeiro antes de abrir um lead.")
        else:
            cliente_nomes = [c["nome"] for c in clientes]
            cliente_ids = [c["id"] for c in clientes]
            cliente_sel = st.selectbox("Cliente *", cliente_nomes)
            cliente_id = cliente_ids[cliente_nomes.index(cliente_sel)]

            curso_interesse = st.text_input("Curso de interesse")
            origem = st.text_input("Origem do lead (opcional)")
            observacoes = st.text_area("Observações iniciais")

            # Responsável
            if is_gestor() and vendedores:
                nomes_vend = [v["nome"] for v in vendedores]
                ids_vend = [v["user_id"] for v in vendedores]
                resp_sel = st.selectbox("Responsável", nomes_vend)
                responsavel_id = ids_vend[nomes_vend.index(resp_sel)]
            else:
                responsavel_id = get_user_id()
                st.markdown(f"**Responsável:** Você")

            if st.button("✅ Abrir lead"):
                if not cliente_id:
                    st.warning("Selecione um cliente.")
                else:
                    dados = {
                        "cliente_id": cliente_id,
                        "responsavel_id": responsavel_id,
                        "estagio": "novo",
                        "curso_interesse": curso_interesse,
                        "origem": origem,
                        "observacoes": observacoes
                    }
                    ok, resultado = criar_lead(dados)
                    if ok:
                        st.success("Lead aberto com sucesso!")
                        st.balloons()
                    else:
                        st.error(f"Erro: {resultado}")