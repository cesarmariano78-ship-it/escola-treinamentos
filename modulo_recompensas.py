import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TIPOS_RECOMPENSA = {
    "indicacao": "🤝 Indicação",
    "bonus": "⭐ Bônus",
    "ajuste": "🔧 Ajuste manual"
}

STATUS_RECOMPENSA = {
    "pendente": "🟡 Pendente",
    "aprovado": "🟢 Aprovado",
    "pago": "✅ Pago",
    "cancelado": "⚫ Cancelado"
}

# ============================================================
# FUNÇÕES DE DADOS
# ============================================================
def listar_clientes():
    try:
        resultado = supabase.table("clientes").select("id, nome").eq("ativo", True).order("nome").execute()
        return resultado.data or []
    except:
        return []

def listar_parceiros():
    try:
        resultado = supabase.table("parceiros").select("id, nome, percentual_comissao").eq("ativo", True).order("nome").execute()
        return resultado.data or []
    except:
        return []

def buscar_saldo_cliente(cliente_id):
    try:
        resultado = supabase.table("recompensas").select("creditos, status").eq(
            "cliente_id", cliente_id
        ).in_("status", ["aprovado"]).execute()
        return sum(r["creditos"] for r in (resultado.data or []))
    except:
        return 0

def buscar_saldo_parceiro(parceiro_id):
    try:
        resultado = supabase.table("recompensas").select("valor_dinheiro, status").eq(
            "parceiro_id", parceiro_id
        ).in_("status", ["aprovado"]).execute()
        return sum(r.get("valor_dinheiro", 0) or 0 for r in (resultado.data or []))
    except:
        return 0

def listar_recompensas_cliente(cliente_id):
    try:
        resultado = supabase.table("recompensas").select(
            "*, clientes!recompensas_indicado_id_fkey(nome)"
        ).eq("cliente_id", cliente_id).order("criado_em", desc=True).execute()
        return resultado.data or []
    except:
        return []

def listar_recompensas_parceiro(parceiro_id):
    try:
        resultado = supabase.table("recompensas").select(
            "*, clientes!recompensas_cliente_id_fkey(nome)"
        ).eq("parceiro_id", parceiro_id).order("criado_em", desc=True).execute()
        return resultado.data or []
    except:
        return []

def listar_todas_recompensas():
    try:
        resultado = supabase.table("recompensas").select(
            "*, clientes!recompensas_cliente_id_fkey(nome), parceiros(nome)"
        ).order("criado_em", desc=True).execute()
        return resultado.data or []
    except Exception as e:
        st.error(f"Erro: {e}")
        return []

def criar_recompensa(dados):
    try:
        supabase.table("recompensas").insert(dados).execute()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

def atualizar_status_recompensa(recompensa_id, novo_status):
    try:
        supabase.table("recompensas").update({"status": novo_status}).eq("id", recompensa_id).execute()
        return True
    except:
        return False

def gerar_recompensa_indicacao(matricula_id, cliente_indicador_id, parceiro_id, valor_curso):
    try:
        # Recompensa para aluno indicador (crédito)
        if cliente_indicador_id:
            criar_recompensa({
                "cliente_id": cliente_indicador_id,
                "matricula_id": matricula_id,
                "tipo": "indicacao",
                "creditos": round(valor_curso * 0.05, 2),  # 5% em créditos
                "descricao": "Crédito por indicação de aluno",
                "status": "pendente"
            })

        # Recompensa para parceiro (dinheiro)
        if parceiro_id:
            parceiros = supabase.table("parceiros").select(
                "percentual_comissao"
            ).eq("id", parceiro_id).single().execute()
            percentual = parceiros.data.get("percentual_comissao", 0) if parceiros.data else 0
            criar_recompensa({
                "parceiro_id": parceiro_id,
                "matricula_id": matricula_id,
                "tipo": "indicacao",
                "creditos": 0,
                "valor_dinheiro": round(valor_curso * percentual / 100, 2),
                "descricao": f"Comissão por indicação ({percentual}%)",
                "status": "pendente"
            })
        return True
    except Exception as e:
        st.error(f"Erro ao gerar recompensa: {e}")
        return False

# ============================================================
# INTERFACE PRINCIPAL
# ============================================================
def pagina_recompensas():
    st.title("⭐ Programa de Recompensas")

    aba1, aba2, aba3, aba4 = st.tabs([
        "📋 Visão geral",
        "👤 Extrato do aluno",
        "🤝 Extrato do parceiro",
        "➕ Lançar recompensa"
    ])

    # ABA 1 — VISÃO GERAL
    with aba1:
        recompensas = listar_todas_recompensas()

        if not recompensas:
            st.info("Nenhuma recompensa registrada ainda.")
        else:
            # Resumo
            pendentes = [r for r in recompensas if r["status"] == "pendente"]
            aprovados = [r for r in recompensas if r["status"] == "aprovado"]
            pagos = [r for r in recompensas if r["status"] == "pago"]

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🟡 Pendentes", len(pendentes))
            with col2:
                st.metric("🟢 Aprovados", len(aprovados))
            with col3:
                st.metric("✅ Pagos", len(pagos))

            st.markdown("---")

            # Filtro
            filtro = st.selectbox(
                "Filtrar por status",
                ["todos"] + list(STATUS_RECOMPENSA.keys()),
                format_func=lambda x: "Todos" if x == "todos" else STATUS_RECOMPENSA[x],
                key="filtro_recompensas"
            )

            lista = recompensas if filtro == "todos" else [r for r in recompensas if r["status"] == filtro]
            st.markdown(f"**{len(lista)} registro(s)**")

            for r in lista:
                cliente = (r.get("clientes!recompensas_cliente_id_fkey") or {}).get("nome", "—")
                parceiro = (r.get("parceiros") or {}).get("nome", "")
                beneficiario = parceiro if parceiro else cliente
                tipo = TIPOS_RECOMPENSA.get(r.get("tipo", ""), "—")
                status = STATUS_RECOMPENSA.get(r.get("status", ""), "—")
                creditos = r.get("creditos", 0) or 0
                dinheiro = r.get("valor_dinheiro", 0) or 0
                data = r.get("criado_em", "")[:10] if r.get("criado_em") else "—"

                valor_txt = f"R$ {dinheiro:,.2f}" if dinheiro > 0 else f"{creditos} créditos"

                with st.expander(f"{status} · {beneficiario} · {tipo} · {valor_txt} · {data}"):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**Beneficiário:** {beneficiario}")
                        st.markdown(f"**Tipo:** {tipo}")
                        st.markdown(f"**Descrição:** {r.get('descricao', '—')}")
                        st.markdown(f"**Data:** {data}")
                    with col2:
                        st.markdown(f"**Créditos:** {creditos}")
                        st.markdown(f"**Valor em R$:** R$ {dinheiro:,.2f}")
                        st.markdown(f"**Status:** {status}")
                    with col3:
                        if r["status"] == "pendente":
                            if st.button("✅ Aprovar", key=f"apr_{r['id']}"):
                                if atualizar_status_recompensa(r["id"], "aprovado"):
                                    st.success("Aprovado!")
                                    st.rerun()
                        if r["status"] == "aprovado":
                            if st.button("💰 Pagar", key=f"pag_{r['id']}"):
                                if atualizar_status_recompensa(r["id"], "pago"):
                                    st.success("Marcado como pago!")
                                    st.rerun()
                        if r["status"] in ["pendente", "aprovado"]:
                            if st.button("❌ Cancelar", key=f"can_{r['id']}"):
                                if atualizar_status_recompensa(r["id"], "cancelado"):
                                    st.rerun()

    # ABA 2 — EXTRATO DO ALUNO
    with aba2:
        st.markdown("### 👤 Extrato de créditos do aluno")
        clientes = listar_clientes()

        if not clientes:
            st.info("Nenhum cliente cadastrado.")
        else:
            nomes = [c["nome"] for c in clientes]
            ids = [c["id"] for c in clientes]
            sel = st.selectbox("Selecione o aluno", nomes, key="sel_aluno_extrato")
            cliente_id = ids[nomes.index(sel)]

            saldo = buscar_saldo_cliente(cliente_id)
            st.metric("💳 Saldo de créditos", f"{saldo:.2f} créditos")

            recompensas_cliente = listar_recompensas_cliente(cliente_id)
            st.markdown("---")
            st.markdown("**Histórico:**")

            if not recompensas_cliente:
                st.info("Nenhuma recompensa registrada para este aluno.")
            else:
                for r in recompensas_cliente:
                    status = STATUS_RECOMPENSA.get(r.get("status", ""), "—")
                    tipo = TIPOS_RECOMPENSA.get(r.get("tipo", ""), "—")
                    data = r.get("criado_em", "")[:10] if r.get("criado_em") else "—"
                    creditos = r.get("creditos", 0) or 0
                    cor = {"aprovado": "#E8F5E9", "pago": "#E3F2FD", "pendente": "#FFF8E1", "cancelado": "#F5F5F5"}.get(r.get("status"), "#F7FAFC")
                    st.markdown(f"""
                    <div style="background:{cor};padding:10px;border-radius:8px;margin-bottom:6px;">
                        {status} · {tipo} · <strong>{creditos} créditos</strong> · {data}<br>
                        <small>{r.get('descricao', '')}</small>
                    </div>
                    """, unsafe_allow_html=True)

    # ABA 3 — EXTRATO DO PARCEIRO
    with aba3:
        st.markdown("### 🤝 Extrato de comissões do parceiro")
        parceiros = listar_parceiros()

        if not parceiros:
            st.info("Nenhum parceiro cadastrado.")
        else:
            nomes_p = [p["nome"] for p in parceiros]
            ids_p = [p["id"] for p in parceiros]
            sel_p = st.selectbox("Selecione o parceiro", nomes_p, key="sel_parceiro_extrato")
            parceiro_id = ids_p[nomes_p.index(sel_p)]

            saldo_p = buscar_saldo_parceiro(parceiro_id)
            st.metric("💰 Comissões aprovadas a pagar", f"R$ {saldo_p:,.2f}")

            recompensas_parceiro = listar_recompensas_parceiro(parceiro_id)
            st.markdown("---")
            st.markdown("**Histórico:**")

            if not recompensas_parceiro:
                st.info("Nenhuma comissão registrada para este parceiro.")
            else:
                for r in recompensas_parceiro:
                    status = STATUS_RECOMPENSA.get(r.get("status", ""), "—")
                    data = r.get("criado_em", "")[:10] if r.get("criado_em") else "—"
                    dinheiro = r.get("valor_dinheiro", 0) or 0
                    cor = {"aprovado": "#E8F5E9", "pago": "#E3F2FD", "pendente": "#FFF8E1", "cancelado": "#F5F5F5"}.get(r.get("status"), "#F7FAFC")
                    st.markdown(f"""
                    <div style="background:{cor};padding:10px;border-radius:8px;margin-bottom:6px;">
                        {status} · <strong>R$ {dinheiro:,.2f}</strong> · {data}<br>
                        <small>{r.get('descricao', '')}</small>
                    </div>
                    """, unsafe_allow_html=True)

    # ABA 4 — LANÇAR RECOMPENSA
    with aba4:
        st.markdown("### ➕ Lançar recompensa manualmente")

        tipo_benef = st.radio("Beneficiário", ["Aluno (créditos)", "Parceiro (comissão)"], key="tipo_benef")

        if tipo_benef == "Aluno (créditos)":
            clientes = listar_clientes()
            nomes_c = [c["nome"] for c in clientes]
            ids_c = [c["id"] for c in clientes]
            sel_c = st.selectbox("Aluno", nomes_c, key="sel_aluno_manual")
            cliente_id_manual = ids_c[nomes_c.index(sel_c)] if nomes_c else None

            creditos_manual = st.number_input("Quantidade de créditos", min_value=0.0, step=1.0)
            tipo_manual = st.selectbox("Tipo", list(TIPOS_RECOMPENSA.keys()),
                                       format_func=lambda x: TIPOS_RECOMPENSA[x],
                                       key="tipo_recomp_manual")
            desc_manual = st.text_input("Descrição")

            if st.button("💾 Lançar crédito"):
                if not cliente_id_manual or creditos_manual <= 0:
                    st.warning("Preencha todos os campos.")
                else:
                    if criar_recompensa({
                        "cliente_id": cliente_id_manual,
                        "tipo": tipo_manual,
                        "creditos": creditos_manual,
                        "descricao": desc_manual,
                        "status": "aprovado"
                    }):
                        st.success("Crédito lançado com sucesso!")
                        st.rerun()

        else:
            parceiros = listar_parceiros()
            nomes_p = [p["nome"] for p in parceiros]
            ids_p = [p["id"] for p in parceiros]
            sel_p2 = st.selectbox("Parceiro", nomes_p, key="sel_parceiro_manual")
            parceiro_id_manual = ids_p[nomes_p.index(sel_p2)] if nomes_p else None

            valor_manual = st.number_input("Valor da comissão (R$)", min_value=0.0, step=10.0)
            desc_p_manual = st.text_input("Descrição", key="desc_parceiro")

            if st.button("💾 Lançar comissão"):
                if not parceiro_id_manual or valor_manual <= 0:
                    st.warning("Preencha todos os campos.")
                else:
                    if criar_recompensa({
                        "parceiro_id": parceiro_id_manual,
                        "tipo": "bonus",
                        "creditos": 0,
                        "valor_dinheiro": valor_manual,
                        "descricao": desc_p_manual,
                        "status": "aprovado"
                    }):
                        st.success("Comissão lançada com sucesso!")
                        st.rerun()