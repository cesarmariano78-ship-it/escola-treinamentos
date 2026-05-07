import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime, date, timedelta

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

FORMAS_PAGAMENTO = {
    "pix": "💠 PIX",
    "boleto": "📄 Boleto",
    "cartao": "💳 Cartão",
    "dinheiro": "💵 Dinheiro",
    "transferencia": "🏦 Transferência"
}

STATUS_LANCAMENTO = {
    "pendente": "🟡 Pendente",
    "pago": "🟢 Pago",
    "atrasado": "🔴 Atrasado",
    "cancelado": "⚫ Cancelado"
}

# ============================================================
# FUNÇÕES DE DADOS
# ============================================================
def listar_lancamentos(tipo=None, status=None, mes=None, ano=None):
    try:
        query = supabase.table("lancamentos").select(
            "*, clientes(nome), matriculas(turmas(nome))"
        ).order("data_vencimento")

        if tipo:
            query = query.eq("tipo", tipo)
        if status and status != "todos":
            query = query.eq("status", status)
        if mes and ano:
            inicio = date(ano, mes, 1).isoformat()
            if mes == 12:
                fim = date(ano + 1, 1, 1).isoformat()
            else:
                fim = date(ano, mes + 1, 1).isoformat()
            query = query.gte("data_vencimento", inicio).lte("data_vencimento", fim)

        resultado = query.execute()

        # Atualiza status de atrasados automaticamente
        dados = resultado.data or []
        hoje = date.today().isoformat()
        for l in dados:
            if l["status"] == "pendente" and l["data_vencimento"] < hoje:
                l["status"] = "atrasado"

        return dados
    except Exception as e:
        st.error(f"Erro ao listar lançamentos: {e}")
        return []

def criar_lancamento(dados):
    try:
        resultado = supabase.table("lancamentos").insert(dados).execute()
        return True, resultado.data[0]["id"] if resultado.data else None
    except Exception as e:
        return False, str(e)

def marcar_pago(lancamento_id, forma_pagamento):
    try:
        supabase.table("lancamentos").update({
            "status": "pago",
            "data_pagamento": date.today().isoformat(),
            "forma_pagamento": forma_pagamento,
            "atualizado_em": datetime.now().isoformat()
        }).eq("id", lancamento_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

def cancelar_lancamento(lancamento_id):
    try:
        supabase.table("lancamentos").update({
            "status": "cancelado",
            "atualizado_em": datetime.now().isoformat()
        }).eq("id", lancamento_id).execute()
        return True
    except:
        return False

def listar_matriculas_sem_cobranca():
    try:
        todas = supabase.table("matriculas").select(
            "id, clientes(id, nome), turmas(nome, valor)"
        ).eq("status", "ativa").execute()

        com_cobranca = supabase.table("lancamentos").select(
            "matricula_id"
        ).not_.is_("matricula_id", "null").execute()

        ids_com_cobranca = {l["matricula_id"] for l in (com_cobranca.data or [])}
        return [m for m in (todas.data or []) if m["id"] not in ids_com_cobranca]
    except:
        return []

def listar_parceiros_com_comissao():
    try:
        resultado = supabase.table("parceiros").select(
            "id, nome, percentual_comissao"
        ).eq("ativo", True).order("nome").execute()
        return resultado.data or []
    except:
        return []

def calcular_resumo(mes, ano):
    lancamentos = listar_lancamentos(mes=mes, ano=ano)
    receitas = [l for l in lancamentos if l["tipo"] == "receita"]
    despesas = [l for l in lancamentos if l["tipo"] == "despesa"]

    total_receber = sum(l["valor"] for l in receitas if l["status"] in ["pendente", "atrasado"])
    total_recebido = sum(l["valor"] for l in receitas if l["status"] == "pago")
    total_atrasado = sum(l["valor"] for l in receitas if l["status"] == "atrasado")
    total_pagar = sum(l["valor"] for l in despesas if l["status"] in ["pendente", "atrasado"])
    total_pago = sum(l["valor"] for l in despesas if l["status"] == "pago")

    return {
        "total_receber": total_receber,
        "total_recebido": total_recebido,
        "total_atrasado": total_atrasado,
        "total_pagar": total_pagar,
        "total_pago": total_pago,
        "saldo": total_recebido - total_pago
    }

def gerar_parcelas(matricula_id, cliente_id, turma_nome, valor_total, num_parcelas, data_primeira, forma):
    try:
        for i in range(num_parcelas):
            mes_offset = i
            ano = data_primeira.year
            mes = data_primeira.month + mes_offset
            while mes > 12:
                mes -= 12
                ano += 1
            vencimento = date(ano, mes, data_primeira.day)

            valor_parcela = round(valor_total / num_parcelas, 2)
            if i == num_parcelas - 1:
                valor_parcela = round(valor_total - (valor_parcela * (num_parcelas - 1)), 2)

            criar_lancamento({
                "tipo": "receita",
                "descricao": f"Mensalidade — {turma_nome} ({i+1}/{num_parcelas})",
                "valor": valor_parcela,
                "data_vencimento": vencimento.isoformat(),
                "status": "pendente",
                "forma_pagamento": forma,
                "matricula_id": matricula_id,
                "cliente_id": cliente_id,
                "parcela_numero": i + 1,
                "parcela_total": num_parcelas
            })
        return True
    except Exception as e:
        st.error(f"Erro ao gerar parcelas: {e}")
        return False

# ============================================================
# INTERFACE PRINCIPAL
# ============================================================
def pagina_financeiro():
    st.title("💰 Financeiro")

    hoje = date.today()
    col1, col2 = st.columns([1, 3])
    with col1:
        mes_sel = st.selectbox("Mês", list(range(1, 13)),
                               index=hoje.month - 1,
                               format_func=lambda x: datetime(2000, x, 1).strftime("%B").capitalize())
        ano_sel = st.selectbox("Ano", list(range(2024, 2030)), index=list(range(2024, 2030)).index(hoje.year))

    # RESUMO
    resumo = calcular_resumo(mes_sel, ano_sel)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💚 Recebido", f"R$ {resumo['total_recebido']:,.2f}")
    with col2:
        st.metric("🟡 A receber", f"R$ {resumo['total_receber']:,.2f}")
    with col3:
        st.metric("🔴 Atrasado", f"R$ {resumo['total_atrasado']:,.2f}")
    with col4:
        saldo_cor = "normal" if resumo["saldo"] >= 0 else "inverse"
        st.metric("📊 Saldo", f"R$ {resumo['saldo']:,.2f}")

    st.markdown("---")

    aba1, aba2, aba3, aba4 = st.tabs([
        "📥 A Receber", "📤 A Pagar", "➕ Novo Lançamento", "🔗 Gerar Cobrança"
    ])

    # ABA A RECEBER
    with aba1:
        col1, col2 = st.columns([2, 1])
        with col2:
            filtro = st.selectbox("Filtrar", ["todos"] + list(STATUS_LANCAMENTO.keys()),
                                  format_func=lambda x: "Todos" if x == "todos" else STATUS_LANCAMENTO[x],
                                  key="filtro_receber")

        lancamentos = listar_lancamentos(tipo="receita", status=filtro, mes=mes_sel, ano=ano_sel)
        st.markdown(f"**{len(lancamentos)} lançamento(s)**")

        for l in lancamentos:
            cliente = l.get("clientes") or {}
            matricula = l.get("matriculas") or {}
            turma = matricula.get("turmas") or {} if matricula else {}
            status = l.get("status", "pendente")
            cor = {"pago": "#E8F5E9", "atrasado": "#FFEBEE", "pendente": "#FFF8E1", "cancelado": "#F5F5F5"}

            parcela_txt = f" ({l['parcela_numero']}/{l['parcela_total']})" if l.get("parcela_numero") else ""

            with st.expander(f"{STATUS_LANCAMENTO.get(status, status)} · {cliente.get('nome', '—')} · R$ {l['valor']:,.2f}{parcela_txt} · Venc: {l['data_vencimento']}"):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**Descrição:** {l.get('descricao', '—')}")
                    st.markdown(f"**Cliente:** {cliente.get('nome', '—')}")
                    st.markdown(f"**Turma:** {turma.get('nome', '—') if turma else '—'}")
                    st.markdown(f"**Vencimento:** {l['data_vencimento']}")
                    if l.get("data_pagamento"):
                        st.markdown(f"**Pago em:** {l['data_pagamento']}")
                with col2:
                    st.markdown(f"**Valor:** R$ {l['valor']:,.2f}")
                    st.markdown(f"**Status:** {STATUS_LANCAMENTO.get(status, status)}")
                    if l.get("forma_pagamento"):
                        st.markdown(f"**Forma:** {FORMAS_PAGAMENTO.get(l['forma_pagamento'], l['forma_pagamento'])}")
                with col3:
                    if status in ["pendente", "atrasado"]:
                        forma_sel = st.selectbox(
                            "Forma",
                            list(FORMAS_PAGAMENTO.keys()),
                            format_func=lambda x: FORMAS_PAGAMENTO[x],
                            key=f"forma_{l['id']}"
                        )
                        if st.button("✅ Recebido", key=f"pago_{l['id']}"):
                            if marcar_pago(l["id"], forma_sel):
                                st.success("Marcado como pago!")
                                st.rerun()
                        if st.button("❌ Cancelar", key=f"cancel_{l['id']}"):
                            if cancelar_lancamento(l["id"]):
                                st.rerun()

    # ABA A PAGAR
    with aba2:
        col1, col2 = st.columns([2, 1])
        with col2:
            filtro_pagar = st.selectbox("Filtrar", ["todos"] + list(STATUS_LANCAMENTO.keys()),
                                        format_func=lambda x: "Todos" if x == "todos" else STATUS_LANCAMENTO[x],
                                        key="filtro_pagar")

        lancamentos_pagar = listar_lancamentos(tipo="despesa", status=filtro_pagar, mes=mes_sel, ano=ano_sel)
        st.markdown(f"**{len(lancamentos_pagar)} lançamento(s)**")

        for l in lancamentos_pagar:
            status = l.get("status", "pendente")
            with st.expander(f"{STATUS_LANCAMENTO.get(status, status)} · {l.get('descricao', '—')} · R$ {l['valor']:,.2f} · Venc: {l['data_vencimento']}"):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**Descrição:** {l.get('descricao', '—')}")
                    st.markdown(f"**Vencimento:** {l['data_vencimento']}")
                    if l.get("observacoes"):
                        st.markdown(f"**Obs:** {l['observacoes']}")
                with col2:
                    st.markdown(f"**Valor:** R$ {l['valor']:,.2f}")
                    st.markdown(f"**Status:** {STATUS_LANCAMENTO.get(status, status)}")
                with col3:
                    if status in ["pendente", "atrasado"]:
                        forma_sel = st.selectbox(
                            "Forma",
                            list(FORMAS_PAGAMENTO.keys()),
                            format_func=lambda x: FORMAS_PAGAMENTO[x],
                            key=f"forma_p_{l['id']}"
                        )
                        if st.button("✅ Pago", key=f"pago_p_{l['id']}"):
                            if marcar_pago(l["id"], forma_sel):
                                st.success("Marcado como pago!")
                                st.rerun()

    # ABA NOVO LANÇAMENTO
    with aba3:
        st.markdown("### Lançamento manual")
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo", ["receita", "despesa"],
                                format_func=lambda x: "📥 Receita" if x == "receita" else "📤 Despesa")
            descricao = st.text_input("Descrição *")
            valor = st.number_input("Valor (R$)", min_value=0.01, step=10.0)
            vencimento = st.date_input("Data de vencimento", value=date.today())
        with col2:
            forma = st.selectbox("Forma de pagamento", list(FORMAS_PAGAMENTO.keys()),
                                 format_func=lambda x: FORMAS_PAGAMENTO[x])
            observacoes = st.text_area("Observações")

        if st.button("💾 Salvar lançamento"):
            if not descricao or not valor:
                st.warning("Preencha descrição e valor.")
            else:
                ok, _ = criar_lancamento({
                    "tipo": tipo,
                    "descricao": descricao,
                    "valor": valor,
                    "data_vencimento": vencimento.isoformat(),
                    "status": "pendente",
                    "forma_pagamento": forma,
                    "observacoes": observacoes
                })
                if ok:
                    st.success("Lançamento criado!")
                    st.rerun()

    # ABA GERAR COBRANÇA
    with aba4:
        st.markdown("### Gerar cobrança por matrícula")
        matriculas = listar_matriculas_sem_cobranca()

        if not matriculas:
            st.info("Todas as matrículas ativas já têm cobrança gerada.")
        else:
            opcoes = [f"{m.get('clientes', {}).get('nome', '—')} — {m.get('turmas', {}).get('nome', '—')}" for m in matriculas]
            ids = [m["id"] for m in matriculas]
            clientes_ids = [m.get("clientes", {}).get("id") for m in matriculas]
            turmas_nomes = [m.get("turmas", {}).get("nome", "—") for m in matriculas]
            valores_turma = [m.get("turmas", {}).get("valor", 0) or 0 for m in matriculas]

            sel = st.selectbox("Selecione a matrícula", opcoes)
            idx = opcoes.index(sel)

            col1, col2 = st.columns(2)
            with col1:
                valor_total = st.number_input("Valor total (R$)", min_value=0.01,
                                              value=float(valores_turma[idx]) if valores_turma[idx] else 100.0,
                                              step=50.0)
                num_parcelas = st.number_input("Número de parcelas", min_value=1, max_value=24, value=1)
            with col2:
                primeira_parcela = st.date_input("Vencimento da 1ª parcela",
                                                 value=date.today() + timedelta(days=7))
                forma_cobranca = st.selectbox("Forma de pagamento preferencial",
                                              list(FORMAS_PAGAMENTO.keys()),
                                              format_func=lambda x: FORMAS_PAGAMENTO[x],
                                              key="forma_cobranca")

            if num_parcelas > 1:
                valor_parcela = round(valor_total / num_parcelas, 2)
                st.info(f"Serão geradas {num_parcelas} parcelas de R$ {valor_parcela:,.2f}")

            if st.button("✅ Gerar cobrança"):
                if gerar_parcelas(ids[idx], clientes_ids[idx], turmas_nomes[idx],
                                  valor_total, num_parcelas, primeira_parcela, forma_cobranca):
                    st.success(f"Cobrança gerada com {num_parcelas} parcela(s)!")
                    st.balloons()
                    st.rerun()