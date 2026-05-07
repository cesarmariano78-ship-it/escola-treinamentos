import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime, date, timedelta

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# FUNÇÕES DE DADOS
# ============================================================
def get_resumo_leads():
    try:
        estagios = ["novo", "em_negociacao", "proposta_enviada", "aguardando_pagamento", "matriculado", "perdido"]
        resultado = supabase.table("leads").select("estagio").execute()
        dados = resultado.data or []
        contagem = {e: 0 for e in estagios}
        for l in dados:
            e = l.get("estagio")
            if e in contagem:
                contagem[e] += 1
        return contagem
    except:
        return {}

def get_taxa_conversao():
    try:
        total = supabase.table("leads").select("id", count="exact").execute()
        convertidos = supabase.table("leads").select("id", count="exact").eq("estagio", "matriculado").execute()
        if total.count and total.count > 0:
            return round((convertidos.count / total.count) * 100, 1)
        return 0
    except:
        return 0

def get_resumo_financeiro():
    try:
        hoje = date.today()
        inicio_mes = date(hoje.year, hoje.month, 1).isoformat()
        if hoje.month == 12:
            fim_mes = date(hoje.year + 1, 1, 1).isoformat()
        else:
            fim_mes = date(hoje.year, hoje.month + 1, 1).isoformat()

        lancamentos = supabase.table("lancamentos").select(
            "tipo, valor, status"
        ).gte("data_vencimento", inicio_mes).lt("data_vencimento", fim_mes).execute()

        dados = lancamentos.data or []
        recebido = sum(l["valor"] for l in dados if l["tipo"] == "receita" and l["status"] == "pago")
        a_receber = sum(l["valor"] for l in dados if l["tipo"] == "receita" and l["status"] in ["pendente", "atrasado"])
        atrasado = sum(l["valor"] for l in dados if l["tipo"] == "receita" and l["status"] == "atrasado")
        return recebido, a_receber, atrasado
    except:
        return 0, 0, 0

def get_turmas_ativas():
    try:
        hoje = date.today().isoformat()
        turmas = supabase.table("turmas").select(
            "id, nome, vagas, cursos(nome)"
        ).eq("ativo", True).gte("data_fim", hoje).execute()

        resultado = []
        for t in (turmas.data or []):
            matriculas = supabase.table("matriculas").select(
                "id", count="exact"
            ).eq("turma_id", t["id"]).eq("status", "ativa").execute()
            ocupacao = matriculas.count or 0
            resultado.append({
                "nome": t["nome"],
                "curso": (t.get("cursos") or {}).get("nome", "—"),
                "vagas": t.get("vagas", 0),
                "ocupacao": ocupacao,
                "percentual": round((ocupacao / t["vagas"]) * 100, 1) if t.get("vagas") else 0
            })
        return resultado
    except:
        return []

def get_followups_proximos():
    try:
        hoje = date.today().isoformat()
        limite = (date.today() + timedelta(days=3)).isoformat()
        resultado = supabase.table("followups").select(
            "descricao, proximo_contato, leads(clientes(nome))"
        ).gte("proximo_contato", hoje).lte("proximo_contato", limite).order("proximo_contato").execute()
        return resultado.data or []
    except:
        return []

def get_pagamentos_vencendo():
    try:
        hoje = date.today().isoformat()
        limite = (date.today() + timedelta(days=5)).isoformat()
        resultado = supabase.table("lancamentos").select(
            "descricao, valor, data_vencimento, clientes(nome)"
        ).eq("tipo", "receita").eq("status", "pendente").gte(
            "data_vencimento", hoje
        ).lte("data_vencimento", limite).order("data_vencimento").execute()
        return resultado.data or []
    except:
        return []

def get_leads_sem_contato(dias=7):
    try:
        limite = (date.today() - timedelta(days=dias)).isoformat()
        todos_leads = supabase.table("leads").select(
            "id, curso_interesse, criado_em, clientes(nome)"
        ).not_.eq("estagio", "matriculado").not_.eq("estagio", "perdido").execute()

        resultado = []
        for lead in (todos_leads.data or []):
            ultimo_fu = supabase.table("followups").select(
                "criado_em"
            ).eq("lead_id", lead["id"]).order("criado_em", desc=True).limit(1).execute()

            if not ultimo_fu.data:
                criado = lead.get("criado_em", "")[:10]
                if criado <= limite:
                    resultado.append(lead)
            else:
                ultimo = ultimo_fu.data[0]["criado_em"][:10]
                if ultimo <= limite:
                    resultado.append(lead)

        return resultado
    except:
        return []

def get_total_clientes():
    try:
        resultado = supabase.table("clientes").select("id", count="exact").eq("ativo", True).execute()
        return resultado.count or 0
    except:
        return 0

# ============================================================
# INTERFACE PRINCIPAL
# ============================================================
def pagina_dashboard():
    perfil = st.session_state.get("perfil", {})
    nome = perfil.get("nome", "").split()[0]

    st.markdown(f"## 👋 Olá, {nome}!")
    st.markdown(f"*{date.today().strftime('%d/%m/%Y')}*")
    st.markdown("---")

    # ── MÉTRICAS PRINCIPAIS ──
    leads = get_resumo_leads()
    taxa = get_taxa_conversao()
    recebido, a_receber, atrasado = get_resumo_financeiro()
    total_clientes = get_total_clientes()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_leads = sum(leads.values())
        st.metric("📊 Total de Leads", total_leads)
    with col2:
        st.metric("🎓 Matriculados", leads.get("matriculado", 0))
    with col3:
        st.metric("📈 Taxa de Conversão", f"{taxa}%")
    with col4:
        st.metric("👥 Clientes", total_clientes)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💚 Recebido no mês", f"R$ {recebido:,.2f}")
    with col2:
        st.metric("🟡 A receber no mês", f"R$ {a_receber:,.2f}")
    with col3:
        st.metric("🔴 Em atraso", f"R$ {atrasado:,.2f}",
                  delta=f"-R$ {atrasado:,.2f}" if atrasado > 0 else None,
                  delta_color="inverse")

    st.markdown("---")

    # ── FUNIL VISUAL ──
    st.markdown("#### 📊 Funil de Vendas")
    estagios_label = {
        "novo": "🆕 Novo",
        "em_negociacao": "💬 Em negociação",
        "proposta_enviada": "📄 Proposta enviada",
        "aguardando_pagamento": "💰 Aguardando pagamento",
        "matriculado": "✅ Matriculado",
        "perdido": "❌ Perdido"
    }
    cols = st.columns(6)
    for i, (estagio, label) in enumerate(estagios_label.items()):
        with cols[i]:
            qtd = leads.get(estagio, 0)
            st.markdown(f"""
            <div style="background:#EBF4FF;padding:12px;border-radius:8px;text-align:center;">
                <div style="font-size:1.5rem;font-weight:bold;color:#2C5282;">{qtd}</div>
                <div style="font-size:0.75rem;color:#4A5568;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    # ── TURMAS ATIVAS ──
    with col1:
        st.markdown("#### 📚 Turmas em andamento")
        turmas = get_turmas_ativas()
        if not turmas:
            st.info("Nenhuma turma ativa no momento.")
        else:
            for t in turmas:
                percentual = t["percentual"]
                cor = "#E8F5E9" if percentual < 80 else "#FFF3CD" if percentual < 100 else "#FFEBEE"
                st.markdown(f"""
                <div style="background:{cor};padding:10px;border-radius:8px;margin-bottom:8px;">
                    <strong>{t['nome']}</strong> · {t['curso']}<br>
                    <small>👥 {t['ocupacao']}/{t['vagas']} vagas · {percentual}% ocupado</small>
                </div>
                """, unsafe_allow_html=True)

    # ── ALERTAS ──
    with col2:
        st.markdown("#### 🔔 Alertas")

        # Pagamentos vencendo
        pagamentos = get_pagamentos_vencendo()
        if pagamentos:
            st.markdown("**💰 Vencendo nos próximos 5 dias:**")
            for p in pagamentos:
                cliente = (p.get("clientes") or {}).get("nome", "—")
                st.markdown(f"""
                <div style="background:#FFF8E1;padding:8px;border-radius:6px;margin-bottom:4px;">
                    🟡 <strong>{cliente}</strong> · R$ {p['valor']:,.2f} · {p['data_vencimento']}
                </div>
                """, unsafe_allow_html=True)

        # Follow-ups próximos
        followups = get_followups_proximos()
        if followups:
            st.markdown("**📝 Follow-ups agendados:**")
            for f in followups:
                lead_info = f.get("leads") or {}
                cliente = (lead_info.get("clientes") or {}).get("nome", "—")
                data = f.get("proximo_contato", "")[:10]
                st.markdown(f"""
                <div style="background:#EBF4FF;padding:8px;border-radius:6px;margin-bottom:4px;">
                    📅 <strong>{cliente}</strong> · {data}
                </div>
                """, unsafe_allow_html=True)

        # Leads sem contato
        leads_frios = get_leads_sem_contato(7)
        if leads_frios:
            st.markdown(f"**🧊 Leads sem contato há +7 dias ({len(leads_frios)}):**")
            for l in leads_frios[:5]:
                cliente = (l.get("clientes") or {}).get("nome", "—")
                st.markdown(f"""
                <div style="background:#FFEBEE;padding:8px;border-radius:6px;margin-bottom:4px;">
                    🔴 <strong>{cliente}</strong> · {l.get('curso_interesse', '—')}
                </div>
                """, unsafe_allow_html=True)

        if not pagamentos and not followups and not leads_frios:
            st.success("✅ Tudo em dia! Nenhum alerta no momento.")