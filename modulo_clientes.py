import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ORIGENS = [
    "Instagram", "Facebook", "Google", "YouTube", "Indicação de aluno",
    "Indicação de parceiro", "WhatsApp", "Site", "Evento", "Outro"
]

# ============================================================
# FUNÇÕES DE DADOS
# ============================================================
def listar_clientes(busca=""):
    try:
        query = supabase.table("clientes").select(
            "*, parceiros(nome)"
        ).eq("ativo", True).order("nome")
        resultado = query.execute()
        dados = resultado.data or []
        if busca:
            busca = busca.lower()
            dados = [c for c in dados if
                     busca in c.get("nome", "").lower() or
                     busca in c.get("email", "").lower() or
                     busca in c.get("telefone", "").lower()]
        return dados
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []

def buscar_cliente_por_id(cliente_id):
    try:
        resultado = supabase.table("clientes").select("*").eq("id", cliente_id).single().execute()
        return resultado.data
    except:
        return None

def listar_parceiros():
    try:
        resultado = supabase.table("parceiros").select("id, nome").eq("ativo", True).order("nome").execute()
        return resultado.data or []
    except:
        return []

def listar_clientes_para_indicacao():
    try:
        resultado = supabase.table("clientes").select("id, nome").eq("ativo", True).order("nome").execute()
        return resultado.data or []
    except:
        return []

def criar_cliente(dados):
    try:
        resultado = supabase.table("clientes").insert(dados).execute()
        return True, resultado.data[0]["id"] if resultado.data else None
    except Exception as e:
        return False, str(e)

def atualizar_cliente(cliente_id, dados):
    try:
        dados["atualizado_em"] = datetime.now().isoformat()
        supabase.table("clientes").update(dados).eq("id", cliente_id).execute()
        return True
    except Exception as e:
        return False

def desativar_cliente(cliente_id):
    try:
        supabase.table("clientes").update({"ativo": False}).eq("id", cliente_id).execute()
        return True
    except:
        return False

def buscar_historico_cliente(cliente_id):
    try:
        leads = supabase.table("leads").select(
            "*, turmas(nome)"
        ).eq("cliente_id", cliente_id).order("criado_em", desc=True).execute()

        matriculas = supabase.table("matriculas").select(
            "*, turmas(nome, cursos(nome))"
        ).eq("cliente_id", cliente_id).order("criado_em", desc=True).execute()

        return leads.data or [], matriculas.data or []
    except:
        return [], []

def buscar_indicacoes_feitas(cliente_id):
    try:
        resultado = supabase.table("clientes").select(
            "id, nome, criado_em"
        ).eq("indicado_por", cliente_id).execute()
        return resultado.data or []
    except:
        return []

# ============================================================
# FORMULÁRIO DE CLIENTE
# ============================================================
def formulario_cliente(cliente=None):
    parceiros = listar_parceiros()
    clientes_lista = listar_clientes_para_indicacao()

    parceiro_opcoes = ["Nenhum"] + [p["nome"] for p in parceiros]
    parceiro_ids = [None] + [p["id"] for p in parceiros]

    cliente_opcoes = ["Nenhum"] + [c["nome"] for c in clientes_lista]
    cliente_ids = [None] + [c["id"] for c in clientes_lista]

    # Valores padrão para edição
    nome_val = cliente.get("nome", "") if cliente else ""
    email_val = cliente.get("email", "") if cliente else ""
    telefone_val = cliente.get("telefone", "") if cliente else ""
    cpf_val = cliente.get("cpf", "") if cliente else ""
    obs_val = cliente.get("observacoes", "") if cliente else ""

    origem_idx = ORIGENS.index(cliente["origem"]) if cliente and cliente.get("origem") in ORIGENS else 0
    parceiro_idx = parceiro_ids.index(cliente["parceiro_id"]) if cliente and cliente.get("parceiro_id") in parceiro_ids else 0
    indicado_idx = cliente_ids.index(cliente["indicado_por"]) if cliente and cliente.get("indicado_por") in cliente_ids else 0

    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome completo *", value=nome_val)
        apelido = st.text_input("Apelido / Como quer ser chamado", value=cliente.get("apelido", "") if cliente else "")
        email = st.text_input("E-mail", value=email_val)
        telefone = st.text_input("Telefone / WhatsApp", value=telefone_val)
        cpf = st.text_input("CPF", value=cpf_val)
        data_nasc = st.date_input("Data de nascimento", value=None, key="data_nasc")

    with col2:
        origem = st.selectbox("Como chegou até nós? *", ORIGENS, index=origem_idx)

        parceiro_sel = st.selectbox("Parceiro indicador", parceiro_opcoes, index=parceiro_idx)
        parceiro_id = parceiro_ids[parceiro_opcoes.index(parceiro_sel)]

        indicado_sel = st.selectbox("Indicado por (aluno)", cliente_opcoes, index=indicado_idx)
        indicado_por = cliente_ids[cliente_opcoes.index(indicado_sel)]

    observacoes = st.text_area("Observações", value=obs_val, height=100)

    return {
        "nome": nome,
        "apelido": apelido,
        "email": email,
        "telefone": telefone,
        "cpf": cpf,
        "data_nascimento": data_nasc.isoformat() if data_nasc else None,
        "origem": origem,
        "parceiro_id": parceiro_id,
        "indicado_por": indicado_por,
        "observacoes": observacoes
    }

# ============================================================
# INTERFACE PRINCIPAL
# ============================================================
def pagina_clientes():
    st.title("👥 Clientes")
# EXPORTAÇÃO
    with st.expander("📤 Exportar dados"):
        import pandas as pd
        import io

        clientes_exp = listar_clientes()
        if not clientes_exp:
            st.info("Nenhum cliente para exportar.")
        else:
            campos_disponiveis = {
                "nome": "Nome completo",
                "apelido": "Apelido",
                "email": "E-mail",
                "telefone": "Telefone",
                "cpf": "CPF",
                "data_nascimento": "Data de nascimento",
                "origem": "Origem",
                "observacoes": "Observações"
            }
            campos_sel = st.multiselect(
                "Selecione os campos para exportar",
                list(campos_disponiveis.keys()),
                default=["nome", "apelido", "telefone", "email"],
                format_func=lambda x: campos_disponiveis[x]
            )
            if campos_sel:
                df = pd.DataFrame([{c: cl.get(c, "") for c in campos_sel} for cl in clientes_exp])
                df.columns = [campos_disponiveis[c] for c in campos_sel]

                col1, col2 = st.columns(2)
                with col1:
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Baixar CSV", csv, "clientes.csv", "text/csv")
                with col2:
                    buffer = io.BytesIO()
                    df.to_excel(buffer, index=False, engine="openpyxl")
                    st.download_button("⬇️ Baixar Excel", buffer.getvalue(), "clientes.xlsx")
    aba1, aba2, aba3 = st.tabs(["📋 Lista", "➕ Novo Cliente", "🤝 Parceiros"])

    # ── ABA 1: LISTA DE CLIENTES ──
    with aba1:
        busca = st.text_input("🔍 Buscar por nome, e-mail ou telefone", placeholder="Digite para buscar...")
        clientes = listar_clientes(busca)

        st.markdown(f"**{len(clientes)} cliente(s) encontrado(s)**")
        st.markdown("---")

        if not clientes:
            st.info("Nenhum cliente cadastrado ainda.")
        else:
            for c in clientes:
                parceiro_nome = c.get("parceiros", {})
                parceiro_txt = f" · Parceiro: {parceiro_nome['nome']}" if parceiro_nome else ""
                origem_txt = f" · {c.get('origem', '')}" if c.get('origem') else ""

                with st.expander(f"👤 {c['nome']}{origem_txt}{parceiro_txt}"):
                    col1, col2, col3 = st.columns([3, 2, 1])

                    with col1:
                        st.markdown(f"**E-mail:** {c.get('email', '—')}")
                        st.markdown(f"**Telefone:** {c.get('telefone', '—')}")
                        st.markdown(f"**CPF:** {c.get('cpf', '—')}")
                        st.markdown(f"**Origem:** {c.get('origem', '—')}")
                        if c.get('observacoes'):
                            st.markdown(f"**Obs:** {c['observacoes']}")

                    with col2:
                        # Histórico rápido
                        leads, matriculas = buscar_historico_cliente(c["id"])
                        indicacoes = buscar_indicacoes_feitas(c["id"])
                        st.markdown(f"**Leads:** {len(leads)}")
                        st.markdown(f"**Matrículas:** {len(matriculas)}")
                        st.markdown(f"**Indicações feitas:** {len(indicacoes)}")

                    with col3:
                        if st.button("✏️ Editar", key=f"edit_{c['id']}"):
                            st.session_state["editar_cliente"] = c["id"]
                            st.rerun()
                        if st.button("🗑️ Arquivar", key=f"del_{c['id']}"):
                            if desativar_cliente(c["id"]):
                                st.success("Cliente arquivado.")
                                st.rerun()

                    # Indicações feitas por esse cliente
                    if indicacoes:
                        st.markdown("---")
                        st.markdown("**Indicações realizadas:**")
                        for ind in indicacoes:
                            st.markdown(f"· {ind['nome']}")

        # Modal de edição
        if "editar_cliente" in st.session_state:
            cliente_id = st.session_state["editar_cliente"]
            cliente = buscar_cliente_por_id(cliente_id)
            if cliente:
                st.markdown("---")
                st.markdown("### ✏️ Editando cliente")
                dados = formulario_cliente(cliente)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Salvar alterações"):
                        if not dados["nome"]:
                            st.warning("Nome é obrigatório.")
                        else:
                            if atualizar_cliente(cliente_id, dados):
                                st.success("Cliente atualizado!")
                                del st.session_state["editar_cliente"]
                                st.rerun()
                with col2:
                    if st.button("❌ Cancelar"):
                        del st.session_state["editar_cliente"]
                        st.rerun()

    # ── ABA 2: NOVO CLIENTE ──
    with aba2:
        st.markdown("### Cadastrar novo cliente")
        dados = formulario_cliente()

        if st.button("✅ Salvar cliente"):
            if not dados["nome"]:
                st.warning("Nome é obrigatório.")
            else:
                with st.spinner("Salvando..."):
                    ok, resultado = criar_cliente(dados)
                    if ok:
                        st.success(f"Cliente {dados['nome']} cadastrado com sucesso!")
                        st.balloons()
                    else:
                        st.error(f"Erro ao cadastrar: {resultado}")

    # ── ABA 3: PARCEIROS ──
    with aba3:
        st.markdown("### 🤝 Parceiros de indicação")

        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("➕ Novo parceiro"):
                st.session_state["novo_parceiro"] = True

        # Formulário novo parceiro
        if st.session_state.get("novo_parceiro"):
            st.markdown("---")
            st.markdown("#### Cadastrar parceiro")
            p_nome = st.text_input("Nome do parceiro *")
            p_email = st.text_input("E-mail do parceiro")
            p_tel = st.text_input("Telefone")
            p_tipo = st.selectbox("Tipo", ["pessoa_fisica", "pessoa_juridica"])
            p_comissao = st.number_input("Percentual de comissão (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5)
            p_obs = st.text_area("Observações")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Salvar parceiro"):
                    if not p_nome:
                        st.warning("Nome é obrigatório.")
                    else:
                        try:
                            supabase.table("parceiros").insert({
                                "nome": p_nome,
                                "email": p_email,
                                "telefone": p_tel,
                                "tipo": p_tipo,
                                "percentual_comissao": p_comissao,
                                "observacoes": p_obs,
                                "ativo": True
                            }).execute()
                            st.success(f"Parceiro {p_nome} cadastrado!")
                            del st.session_state["novo_parceiro"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
            with col2:
                if st.button("❌ Cancelar parceiro"):
                    del st.session_state["novo_parceiro"]
                    st.rerun()

        # Lista de parceiros
        st.markdown("---")
        try:
            parceiros = supabase.table("parceiros").select("*").eq("ativo", True).order("nome").execute()
            if not parceiros.data:
                st.info("Nenhum parceiro cadastrado ainda.")
            else:
                for p in parceiros.data:
                    with st.expander(f"🤝 {p['nome']} · {p['percentual_comissao']}% comissão"):
                        st.markdown(f"**E-mail:** {p.get('email', '—')}")
                        st.markdown(f"**Telefone:** {p.get('telefone', '—')}")
                        st.markdown(f"**Tipo:** {'Pessoa Física' if p['tipo'] == 'pessoa_fisica' else 'Pessoa Jurídica'}")
                        st.markdown(f"**Comissão:** {p['percentual_comissao']}%")
                        if p.get("observacoes"):
                            st.markdown(f"**Obs:** {p['observacoes']}")

                        # Quantas indicações esse parceiro gerou
                        try:
                            total = supabase.table("clientes").select("id", count="exact").eq("parceiro_id", p["id"]).execute()
                            st.markdown(f"**Indicações geradas:** {total.count or 0}")
                        except:
                            pass

                        if st.button("🗑️ Desativar", key=f"desat_parc_{p['id']}"):
                            supabase.table("parceiros").update({"ativo": False}).eq("id", p["id"]).execute()
                            st.success("Parceiro desativado.")
                            st.rerun()
        except Exception as e:
            st.error(f"Erro ao listar parceiros: {e}")