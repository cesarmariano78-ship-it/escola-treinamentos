import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime, date

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MODALIDADES = {
    "presencial": "🏫 Presencial",
    "online_ao_vivo": "💻 Online ao vivo",
    "ead": "📱 EAD / Gravado",
    "in_company": "🏢 In company"
}

STATUS_MATRICULA = {
    "ativa": "✅ Ativa",
    "cancelada": "❌ Cancelada",
    "concluida": "🎓 Concluída",
    "trancada": "⏸️ Trancada"
}

# ============================================================
# FUNÇÕES DE DADOS
# ============================================================
def listar_cursos():
    try:
        resultado = supabase.table("cursos").select("*").eq("ativo", True).order("nome").execute()
        return resultado.data or []
    except:
        return []

def listar_turmas():
    try:
        resultado = supabase.table("turmas").select(
            "*, cursos(nome), perfis(nome)"
        ).eq("ativo", True).order("data_inicio", desc=True).execute()
        return resultado.data or []
    except Exception as e:
        st.error(f"Erro ao listar turmas: {e}")
        return []

def buscar_turma(turma_id):
    try:
        resultado = supabase.table("turmas").select(
            "*, cursos(nome), perfis(nome)"
        ).eq("id", turma_id).single().execute()
        return resultado.data
    except:
        return None

def listar_instrutores():
    try:
        resultado = supabase.table("perfis").select("user_id, nome").in_(
            "tipo", ["instrutor", "gestor"]
        ).eq("ativo", True).order("nome").execute()
        return resultado.data or []
    except:
        return []

def criar_curso(dados):
    try:
        resultado = supabase.table("cursos").insert(dados).execute()
        return True, resultado.data[0]["id"] if resultado.data else None
    except Exception as e:
        return False, str(e)

def criar_turma(dados):
    try:
        resultado = supabase.table("turmas").insert(dados).execute()
        return True, resultado.data[0]["id"] if resultado.data else None
    except Exception as e:
        return False, str(e)

def listar_matriculas(turma_id):
    try:
        resultado = supabase.table("matriculas").select(
            "*, clientes(nome, telefone, email)"
        ).eq("turma_id", turma_id).order("criado_em").execute()
        return resultado.data or []
    except Exception as e:
        st.error(f"Erro ao listar matrículas: {e}")
        return []

def listar_clientes_disponiveis(turma_id):
    try:
        todos = supabase.table("clientes").select("id, nome").eq("ativo", True).order("nome").execute()
        matriculados = supabase.table("matriculas").select("cliente_id").eq("turma_id", turma_id).execute()
        ids_matriculados = {m["cliente_id"] for m in matriculados.data}
        return [c for c in (todos.data or []) if c["id"] not in ids_matriculados]
    except:
        return []

def listar_leads_aguardando():
    try:
        resultado = supabase.table("leads").select(
            "id, curso_interesse, clientes(id, nome)"
        ).eq("estagio", "aguardando_pagamento").execute()
        return resultado.data or []
    except:
        return []

def matricular_cliente(turma_id, cliente_id, lead_id=None):
    try:
        supabase.table("matriculas").insert({
            "turma_id": turma_id,
            "cliente_id": cliente_id,
            "lead_id": lead_id,
            "status": "ativa"
        }).execute()

        # Atualiza lead para matriculado se veio de um lead
        if lead_id:
            supabase.table("leads").update({
                "estagio": "matriculado",
                "atualizado_em": datetime.now().isoformat()
            }).eq("id", lead_id).execute()

        return True
    except Exception as e:
        st.error(f"Erro ao matricular: {e}")
        return False

def atualizar_status_matricula(matricula_id, novo_status):
    try:
        supabase.table("matriculas").update({"status": novo_status}).eq("id", matricula_id).execute()
        return True
    except:
        return False

def listar_presencas(turma_id, data_aula):
    try:
        matriculas = listar_matriculas(turma_id)
        presencas_existentes = supabase.table("presencas").select("*").eq(
            "data_aula", data_aula.isoformat()
        ).execute()
        presencas_dict = {p["matricula_id"]: p for p in (presencas_existentes.data or [])}
        return matriculas, presencas_dict
    except Exception as e:
        st.error(f"Erro: {e}")
        return [], {}

def salvar_presenca(matricula_id, data_aula, presente, observacao=""):
    try:
        existente = supabase.table("presencas").select("id").eq(
            "matricula_id", matricula_id
        ).eq("data_aula", data_aula.isoformat()).execute()

        if existente.data:
            supabase.table("presencas").update({
                "presente": presente,
                "observacao": observacao
            }).eq("id", existente.data[0]["id"]).execute()
        else:
            supabase.table("presencas").insert({
                "matricula_id": matricula_id,
                "data_aula": data_aula.isoformat(),
                "presente": presente,
                "observacao": observacao
            }).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar presença: {e}")
        return False

def calcular_frequencia(matricula_id):
    try:
        total = supabase.table("presencas").select("id", count="exact").eq(
            "matricula_id", matricula_id
        ).execute()
        presentes = supabase.table("presencas").select("id", count="exact").eq(
            "matricula_id", matricula_id
        ).eq("presente", True).execute()
        if total.count and total.count > 0:
            return round((presentes.count / total.count) * 100, 1)
        return 0
    except:
        return 0

# ============================================================
# PAINEL DA TURMA
# ============================================================
def painel_turma(turma_id):
    turma = buscar_turma(turma_id)
    if not turma:
        st.error("Turma não encontrada.")
        return

    curso = turma.get("cursos") or {}
    instrutor = turma.get("perfis") or {}

    st.markdown(f"### 📚 {turma['nome']}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Curso:** {curso.get('nome', '—')}")
        st.markdown(f"**Modalidade:** {MODALIDADES.get(turma.get('modalidade', ''), '—')}")
        st.markdown(f"**Instrutor:** {instrutor.get('nome', '—')}")
    with col2:
        st.markdown(f"**Início:** {turma.get('data_inicio', '—')}")
        st.markdown(f"**Fim:** {turma.get('data_fim', '—')}")
        st.markdown(f"**Horário:** {turma.get('horario', '—')}")
    with col3:
        st.markdown(f"**Vagas:** {turma.get('vagas', '—')}")
        st.markdown(f"**Local/Link:** {turma.get('local_ou_link', '—')}")
        st.markdown(f"**Presença mínima:** {turma.get('presenca_minima', 75)}%")
        if turma.get('material_link'):
            st.markdown(f"**Material:** [Acessar]({turma['material_link']})")

    st.markdown("---")

    aba1, aba2, aba3 = st.tabs(["👥 Alunos", "📋 Presença", "➕ Matricular"])

    # ABA ALUNOS
    with aba1:
        matriculas = listar_matriculas(turma_id)
        presenca_minima = turma.get("presenca_minima", 75)

        if not matriculas:
            st.info("Nenhum aluno matriculado ainda.")
        else:
            st.markdown(f"**{len(matriculas)} aluno(s) matriculado(s)**")
    # Exportação
            with st.expander("📤 Exportar lista de alunos"):
                import pandas as pd
                import io

                campos_disponiveis = {
                    "nome": "Nome completo",
                    "apelido": "Apelido",
                    "email": "E-mail",
                    "telefone": "Telefone",
                    "cpf": "CPF",
                    "data_nascimento": "Data de nascimento"
                }
                campos_sel = st.multiselect(
                    "Selecione os campos",
                    list(campos_disponiveis.keys()),
                    default=["nome", "apelido", "telefone"],
                    format_func=lambda x: campos_disponiveis[x]
                )
                if campos_sel:
                    dados_exp = []
                    for m in matriculas:
                        cliente = m.get("clientes") or {}
                        dados_exp.append({campos_disponiveis[c]: cliente.get(c, "") for c in campos_sel})

                    df = pd.DataFrame(dados_exp)
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = df.to_csv(index=False).encode("utf-8")
                        st.download_button("⬇️ CSV", csv, f"{turma['nome']}.csv", "text/csv")
                    with col2:
                        buffer = io.BytesIO()
                        df.to_excel(buffer, index=False, engine="openpyxl")
                        st.download_button("⬇️ Excel", buffer.getvalue(), f"{turma['nome']}.xlsx")
            for m in matriculas:
                cliente = m.get("clientes") or {}
                freq = calcular_frequencia(m["id"])
                alerta = "🔴" if freq < presenca_minima and freq > 0 else "🟢"

                with st.expander(f"{alerta} {cliente.get('nome', '—')} · {STATUS_MATRICULA.get(m['status'], m['status'])} · Frequência: {freq}%"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Telefone:** {cliente.get('telefone', '—')}")
                        st.markdown(f"**E-mail:** {cliente.get('email', '—')}")
                        st.markdown(f"**Status:** {STATUS_MATRICULA.get(m['status'], m['status'])}")
                        st.markdown(f"**Frequência:** {freq}%")
                        if freq < presenca_minima and freq > 0:
                            st.warning(f"⚠️ Abaixo do mínimo de {presenca_minima}%")
                    with col2:
                        novo_status = st.selectbox(
                            "Alterar status",
                            list(STATUS_MATRICULA.keys()),
                            index=list(STATUS_MATRICULA.keys()).index(m["status"]) if m["status"] in STATUS_MATRICULA else 0,
                            format_func=lambda x: STATUS_MATRICULA[x],
                            key=f"status_{m['id']}"
                        )
                        if novo_status != m["status"]:
                            if atualizar_status_matricula(m["id"], novo_status):
                                st.success("Status atualizado!")
                                st.rerun()
                        # Observações da matrícula
                    st.markdown("---")
                    obs_atual = m.get("observacoes", "") or ""
                    nova_obs = st.text_area(
                        "📝 Observações (CS / Financeiro)",
                        value=obs_atual,
                        height=80,
                        key=f"obs_{m['id']}"
                    )
                    if st.button("💾 Salvar observação", key=f"salvar_obs_{m['id']}"):
                        try:
                            supabase.table("matriculas").update({
                                "observacoes": nova_obs
                            }).eq("id", m["id"]).execute()
                            st.success("Observação salva!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

    # ABA PRESENÇA
    with aba2:
        st.markdown("#### Registrar presença por aula")
        data_aula = st.date_input("Data da aula", value=date.today())
        matriculas, presencas_dict = listar_presencas(turma_id, data_aula)

        if not matriculas:
            st.info("Nenhum aluno matriculado.")
        else:
            presencas_novas = {}
            for m in matriculas:
                if m["status"] != "ativa":
                    continue
                cliente = m.get("clientes") or {}
                presente_atual = presencas_dict.get(m["id"], {}).get("presente", False)
                presencas_novas[m["id"]] = st.checkbox(
                    f"{cliente.get('nome', '—')}",
                    value=presente_atual,
                    key=f"pres_{m['id']}_{data_aula}"
                )

            if st.button("💾 Salvar presenças"):
                sucesso = True
                for matricula_id, presente in presencas_novas.items():
                    if not salvar_presenca(matricula_id, data_aula, presente):
                        sucesso = False
                if sucesso:
                    st.success("Presenças salvas!")
                    st.rerun()

    # ABA MATRICULAR
    with aba3:
        st.markdown("#### Matricular aluno")
        opcao = st.radio("Origem da matrícula", ["Cliente direto", "Lead existente"])

        if opcao == "Cliente direto":
            clientes_disp = listar_clientes_disponiveis(turma_id)
            if not clientes_disp:
                st.info("Todos os clientes já estão matriculados nesta turma.")
            else:
                nomes = [c["nome"] for c in clientes_disp]
                ids = [c["id"] for c in clientes_disp]
                sel = st.selectbox("Selecione o cliente", nomes)
                cliente_id = ids[nomes.index(sel)]
                if st.button("✅ Matricular"):
                    if matricular_cliente(turma_id, cliente_id):
                        st.success(f"{sel} matriculado com sucesso!")
                        st.rerun()

        else:
            leads = listar_leads_aguardando()
            if not leads:
                st.info("Nenhum lead aguardando pagamento no momento.")
            else:
                opcoes = [f"{l.get('clientes', {}).get('nome', '—')} — {l.get('curso_interesse', '—')}" for l in leads]
                ids_leads = [l["id"] for l in leads]
                ids_clientes = [l.get("clientes", {}).get("id") for l in leads]
                sel = st.selectbox("Selecione o lead", opcoes)
                idx = opcoes.index(sel)
                if st.button("✅ Matricular e fechar lead"):
                    if matricular_cliente(turma_id, ids_clientes[idx], ids_leads[idx]):
                        st.success("Aluno matriculado e lead atualizado para Matriculado!")
                        st.rerun()

    if st.button("← Voltar às turmas"):
        del st.session_state["turma_ativa"]
        st.rerun()

# ============================================================
# INTERFACE PRINCIPAL
# ============================================================
def pagina_turmas():
    st.title("📚 Turmas")

    if "turma_ativa" in st.session_state:
        painel_turma(st.session_state["turma_ativa"])
        return

    aba1, aba2, aba3 = st.tabs(["📋 Turmas", "➕ Nova Turma", "📖 Cursos"])

    # ABA TURMAS
    with aba1:
        turmas = listar_turmas()

        if not turmas:
            st.info("Nenhuma turma cadastrada ainda.")
        else:
            for t in turmas:
                curso = t.get("cursos") or {}
                instrutor = t.get("perfis") or {}
                modalidade = MODALIDADES.get(t.get("modalidade", ""), "—")

                with st.expander(f"📚 {t['nome']} · {modalidade} · {curso.get('nome', '—')}"):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**Início:** {t.get('data_inicio', '—')}")
                        st.markdown(f"**Fim:** {t.get('data_fim', '—')}")
                        st.markdown(f"**Horário:** {t.get('horario', '—')}")
                    with col2:
                        st.markdown(f"**Instrutor:** {instrutor.get('nome', '—')}")
                        st.markdown(f"**Vagas:** {t.get('vagas', '—')}")
                        st.markdown(f"**Local/Link:** {t.get('local_ou_link', '—')}")
                    with col3:
                        if st.button("📋 Abrir", key=f"turma_{t['id']}"):
                            st.session_state["turma_ativa"] = t["id"]
                            st.rerun()

    # ABA NOVA TURMA
    with aba2:
        st.markdown("### Criar nova turma")
        cursos = listar_cursos()
        instrutores = listar_instrutores()

        if not cursos:
            st.warning("Cadastre um curso primeiro na aba 'Cursos'.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                nomes_cursos = [c["nome"] for c in cursos]
                ids_cursos = [c["id"] for c in cursos]
                curso_sel = st.selectbox("Curso *", nomes_cursos)
                curso_id = ids_cursos[nomes_cursos.index(curso_sel)]

                nome_turma = st.text_input("Nome da turma *", placeholder="Ex: Turma A — Janeiro 2026")
                modalidade = st.selectbox("Modalidade", list(MODALIDADES.keys()), format_func=lambda x: MODALIDADES[x])
                horario = st.text_input("Horário", placeholder="Ex: Sábados 08h-12h")
                local_ou_link = st.text_input("Local ou link de acesso")

            with col2:
                if instrutores:
                    nomes_inst = [i["nome"] for i in instrutores]
                    ids_inst = [i["user_id"] for i in instrutores]
                    inst_sel = st.selectbox("Instrutor", nomes_inst)
                    instrutor_id = ids_inst[nomes_inst.index(inst_sel)]
                else:
                    instrutor_id = None
                    st.info("Nenhum instrutor cadastrado ainda.")

                data_inicio = st.date_input("Data de início")
                data_fim = st.date_input("Data de fim")
                vagas = st.number_input("Vagas", min_value=1, value=20)
                valor = st.number_input("Valor da turma (R$)", min_value=0.0, value=0.0, step=50.0)
                presenca_minima = st.slider("Presença mínima (%)", 0, 100, 75)
                material_link = st.text_input("Link do material didático (opcional)")

            if st.button("✅ Criar turma"):
                if not nome_turma or not curso_id:
                    st.warning("Nome e curso são obrigatórios.")
                else:
                    dados = {
                        "curso_id": curso_id,
                        "instrutor_id": instrutor_id,
                        "nome": nome_turma,
                        "modalidade": modalidade,
                        "horario": horario,
                        "local_ou_link": local_ou_link,
                        "data_inicio": data_inicio.isoformat(),
                        "data_fim": data_fim.isoformat(),
                        "vagas": vagas,
                        "valor": valor,
                        "presenca_minima": presenca_minima,
                        "material_link": material_link,
                        "tipo": "in_company" if modalidade == "in_company" else "aberta",
                        "ativo": True
                    }
                    ok, resultado = criar_turma(dados)
                    if ok:
                        st.success(f"Turma '{nome_turma}' criada com sucesso!")
                        st.balloons()
                    else:
                        st.error(f"Erro: {resultado}")

    # ABA CURSOS
    with aba3:
        st.markdown("### 📖 Cursos cadastrados")

        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("➕ Novo curso"):
                st.session_state["novo_curso"] = True

        if st.session_state.get("novo_curso"):
            st.markdown("---")
            st.markdown("#### Cadastrar novo curso")
            c_nome = st.text_input("Nome do curso *")
            c_desc = st.text_area("Descrição")
            c_carga = st.number_input("Carga horária (horas)", min_value=1, value=8)
            c_modalidade = st.selectbox("Modalidade padrão", list(MODALIDADES.keys()), format_func=lambda x: MODALIDADES[x], key="mod_curso")
            c_valor = st.number_input("Valor padrão (R$)", min_value=0.0, value=0.0, step=50.0)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Salvar curso"):
                    if not c_nome:
                        st.warning("Nome é obrigatório.")
                    else:
                        ok, _ = criar_curso({
                            "nome": c_nome,
                            "descricao": c_desc,
                            "carga_horaria": c_carga,
                            "modalidade": c_modalidade,
                            "valor_padrao": c_valor,
                            "ativo": True
                        })
                        if ok:
                            st.success(f"Curso '{c_nome}' cadastrado!")
                            del st.session_state["novo_curso"]
                            st.rerun()
            with col2:
                if st.button("❌ Cancelar curso"):
                    del st.session_state["novo_curso"]
                    st.rerun()

        st.markdown("---")
        cursos = listar_cursos()
        if not cursos:
            st.info("Nenhum curso cadastrado ainda.")
        else:
            for c in cursos:
                with st.expander(f"📖 {c['nome']} · {c.get('carga_horaria', '—')}h · R$ {c.get('valor_padrao', 0):.2f}"):
                    st.markdown(f"**Descrição:** {c.get('descricao', '—')}")
                    st.markdown(f"**Modalidade:** {MODALIDADES.get(c.get('modalidade', ''), '—')}")
                    st.markdown(f"**Carga horária:** {c.get('carga_horaria', '—')}h")
                    st.markdown(f"**Valor padrão:** R$ {c.get('valor_padrao', 0):.2f}")