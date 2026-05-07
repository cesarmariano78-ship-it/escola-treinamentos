import streamlit as st
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime, date
import uuid

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# FUNÇÕES DE DADOS
# ============================================================
def listar_matriculas_concluidas():
    try:
        resultado = supabase.table("matriculas").select(
            "id, clientes(id, nome, email), turmas(id, nome, cursos(nome), carga_horaria, data_fim)"
        ).eq("status", "concluida").execute()

        # Filtra as que ainda não têm certificado
        com_cert = supabase.table("certificados").select("matricula_id").execute()
        ids_com_cert = {c["matricula_id"] for c in (com_cert.data or [])}

        return [m for m in (resultado.data or []) if m["id"] not in ids_com_cert]
    except Exception as e:
        st.error(f"Erro: {e}")
        return []

def listar_certificados():
    try:
        resultado = supabase.table("certificados").select(
            "*, clientes(nome), turmas(nome, cursos(nome), carga_horaria)"
        ).order("criado_em", desc=True).execute()
        return resultado.data or []
    except Exception as e:
        st.error(f"Erro: {e}")
        return []

def gerar_certificado(matricula_id, cliente_id, turma_id):
    try:
        codigo = str(uuid.uuid4())[:8].upper()
        resultado = supabase.table("certificados").insert({
            "matricula_id": matricula_id,
            "cliente_id": cliente_id,
            "turma_id": turma_id,
            "data_emissao": datetime.now().isoformat(),
            "codigo_validacao": codigo
        }).execute()
        return True, codigo
    except Exception as e:
        return False, str(e)

def listar_matriculas_ativas_para_avaliacao():
    try:
        resultado = supabase.table("matriculas").select(
            "id, clientes(nome), turmas(nome)"
        ).eq("status", "ativa").execute()

        com_aval = supabase.table("avaliacoes").select("matricula_id").execute()
        ids_com_aval = {a["matricula_id"] for a in (com_aval.data or [])}

        return [m for m in (resultado.data or []) if m["id"] not in ids_com_aval]
    except:
        return []

def listar_avaliacoes():
    try:
        resultado = supabase.table("avaliacoes").select(
            "*, matriculas(clientes(nome), turmas(nome))"
        ).order("data_avaliacao", desc=True).execute()
        return resultado.data or []
    except:
        return []

def salvar_avaliacao(matricula_id, nota, feedback):
    try:
        supabase.table("avaliacoes").insert({
            "matricula_id": matricula_id,
            "nota": nota,
            "feedback": feedback,
            "data_avaliacao": datetime.now().isoformat()
        }).execute()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

def buscar_certificado_por_codigo(codigo):
    try:
        resultado = supabase.table("certificados").select(
            "*, clientes(nome), turmas(nome, cursos(nome), carga_horaria)"
        ).eq("codigo_validacao", codigo.upper()).execute()
        return resultado.data[0] if resultado.data else None
    except:
        return None

def concluir_matricula(matricula_id):
    try:
        supabase.table("matriculas").update({
            "status": "concluida"
        }).eq("id", matricula_id).execute()
        return True
    except:
        return False

def listar_matriculas_ativas():
    try:
        resultado = supabase.table("matriculas").select(
            "id, clientes(nome), turmas(nome)"
        ).eq("status", "ativa").execute()
        return resultado.data or []
    except:
        return []

# ============================================================
# GERADOR DE CERTIFICADO VISUAL (HTML)
# ============================================================
def gerar_html_certificado(nome_aluno, nome_curso, carga_horaria, data_emissao, codigo):
    MESES_PT = {1:"janeiro",2:"fevereiro",3:"março",4:"abril",5:"maio",6:"junho",7:"julho",8:"agosto",9:"setembro",10:"outubro",11:"novembro",12:"dezembro"}
    dt = datetime.fromisoformat(data_emissao) if data_emissao else datetime.now()
    data_fmt = f"{dt.day:02d} de {MESES_PT[dt.month]} de {dt.year}"
    carga = f"{carga_horaria}h" if carga_horaria else ""
    carga_html = f'<div style="font-size: 0.95rem; color: #718096; margin-bottom: 16px;">Carga horária: {carga}</div>' if carga else ""
    html = f"""
    <div style="
        border: 8px double #2C5282;
        padding: 40px;
        text-align: center;
        font-family: Georgia, serif;
        background: linear-gradient(135deg, #f8fafc 0%, #EBF4FF 100%);
        border-radius: 12px;
        max-width: 700px;
        margin: auto;
    ">
        <div style="font-size: 2rem; color: #2C5282; font-weight: bold; margin-bottom: 8px;">
            🎓 CERTIFICADO DE CONCLUSÃO
        </div>
        <div style="color: #718096; font-size: 0.9rem; margin-bottom: 24px;">Escola de Treinamentos</div>
        <div style="font-size: 1rem; color: #4A5568; margin-bottom: 8px;">Certificamos que</div>
        <div style="font-size: 1.8rem; color: #2C5282; font-weight: bold; border-bottom: 2px solid #2C5282; padding-bottom: 8px; margin: 0 40px 16px;">
            {nome_aluno}
        </div>
        <div style="font-size: 1rem; color: #4A5568; margin-bottom: 8px;">concluiu com êxito o curso</div>
        <div style="font-size: 1.4rem; color: #2D3748; font-weight: bold; margin-bottom: 8px;">
            {nome_curso}
        </div>
        {carga_html}
        <div style="font-size: 0.9rem; color: #718096; margin-top: 24px;">{data_fmt}</div>
        <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #CBD5E0;">
            <div style="font-size: 0.75rem; color: #A0AEC0;">Código de validação: <strong>{codigo}</strong></div>
        </div>
    </div>
    """
    return html

# ============================================================
# INTERFACE PRINCIPAL
# ============================================================
def pagina_certificados():
    st.title("🏆 Certificados")

    aba1, aba2, aba3, aba4 = st.tabs([
        "📋 Certificados emitidos",
        "✅ Emitir certificado",
        "📝 Avaliações",
        "🔍 Validar certificado"
    ])

    # ABA 1 — CERTIFICADOS EMITIDOS
    with aba1:
        certificados = listar_certificados()

        if not certificados:
            st.info("Nenhum certificado emitido ainda.")
        else:
            st.markdown(f"**{len(certificados)} certificado(s) emitido(s)**")
            for c in certificados:
                cliente = c.get("clientes") or {}
                turma = c.get("turmas") or {}
                curso = turma.get("cursos") or {}
                data = c.get("data_emissao", "")[:10] if c.get("data_emissao") else "—"

                with st.expander(f"🎓 {cliente.get('nome', '—')} · {curso.get('nome', '—')} · {data}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Aluno:** {cliente.get('nome', '—')}")
                        st.markdown(f"**Curso:** {curso.get('nome', '—')}")
                        st.markdown(f"**Turma:** {turma.get('nome', '—')}")
                        st.markdown(f"**Emitido em:** {data}")
                        st.markdown(f"**Código:** `{c.get('codigo_validacao', '—')}`")
                    with col2:
                        if st.button("👁️ Visualizar", key=f"viz_{c['id']}"):
                            st.session_state[f"cert_viz_{c['id']}"] = True

                    if st.session_state.get(f"cert_viz_{c['id']}"):
                        html = gerar_html_certificado(
                            cliente.get("nome", "—"),
                            curso.get("nome", "—"),
                            turma.get("carga_horaria"),
                            c.get("data_emissao", ""),
                            c.get("codigo_validacao", "—")
                        )
                        st.components.v1.html(html, height=500)
                        if st.button("Fechar", key=f"fech_{c['id']}"):
                            del st.session_state[f"cert_viz_{c['id']}"]
                            st.rerun()

    # ABA 2 — EMITIR CERTIFICADO
    with aba2:
        st.markdown("### Emitir novo certificado")

        # Primeiro: concluir matrícula
        st.markdown("#### Passo 1 — Marcar matrícula como concluída")
        matriculas_ativas = listar_matriculas_ativas()

        if matriculas_ativas:
            opcoes_ativas = [f"{m.get('clientes', {}).get('nome', '—')} — {m.get('turmas', {}).get('nome', '—')}" for m in matriculas_ativas]
            ids_ativas = [m["id"] for m in matriculas_ativas]
            sel_ativa = st.selectbox("Selecione a matrícula", opcoes_ativas)
            idx_ativa = opcoes_ativas.index(sel_ativa)

            if st.button("✅ Marcar como concluída"):
                if concluir_matricula(ids_ativas[idx_ativa]):
                    st.success("Matrícula concluída! Agora pode emitir o certificado abaixo.")
                    st.rerun()
        else:
            st.info("Nenhuma matrícula ativa no momento.")

        st.markdown("---")
        st.markdown("#### Passo 2 — Emitir certificado")

        matriculas = listar_matriculas_concluidas()

        if not matriculas:
            st.info("Nenhuma matrícula concluída aguardando certificado.")
        else:
            opcoes = [f"{m.get('clientes', {}).get('nome', '—')} — {(m.get('turmas') or {}).get('nome', '—')}" for m in matriculas]
            ids = [m["id"] for m in matriculas]
            clientes_ids = [m.get("clientes", {}).get("id") for m in matriculas]
            turmas_ids = [m.get("turmas", {}).get("id") if m.get("turmas") else None for m in matriculas]
            nomes_alunos = [m.get("clientes", {}).get("nome", "—") for m in matriculas]
            nomes_cursos = [(m.get("turmas") or {}).get("cursos", {}).get("nome", "—") if m.get("turmas") else "—" for m in matriculas]
            cargas = [(m.get("turmas") or {}).get("carga_horaria") for m in matriculas]

            sel = st.selectbox("Selecione a matrícula concluída", opcoes)
            idx = opcoes.index(sel)

            # Preview do certificado
            st.markdown("**Preview do certificado:**")
            html_preview = gerar_html_certificado(
                nomes_alunos[idx],
                nomes_cursos[idx],
                cargas[idx],
                datetime.now().isoformat(),
                "XXXXXXXX"
            )
            st.markdown(html_preview, unsafe_allow_html=True)

            st.markdown("---")
            if st.button("🎓 Emitir certificado oficial"):
                ok, codigo = gerar_certificado(ids[idx], clientes_ids[idx], turmas_ids[idx])
                if ok:
                    st.success(f"Certificado emitido! Código: **{codigo}**")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"Erro: {codigo}")

    # ABA 3 — AVALIAÇÕES
    with aba3:
        st.markdown("### 📝 Avaliações dos alunos")

        aba3a, aba3b = st.tabs(["Registrar avaliação", "Ver avaliações"])

        with aba3a:
            matriculas_aval = listar_matriculas_ativas_para_avaliacao()
            if not matriculas_aval:
                st.info("Nenhuma matrícula pendente de avaliação.")
            else:
                opcoes_aval = [f"{m.get('clientes', {}).get('nome', '—')} — {m.get('turmas', {}).get('nome', '—')}" for m in matriculas_aval]
                ids_aval = [m["id"] for m in matriculas_aval]
                sel_aval = st.selectbox("Selecione a matrícula", opcoes_aval, key="sel_aval_registro")
                idx_aval = opcoes_aval.index(sel_aval)

                nota = st.slider("Nota (0 a 10)", 0.0, 10.0, 7.0, 0.5)
                feedback = st.text_area("Feedback / observações")

                if st.button("💾 Salvar avaliação"):
                    if salvar_avaliacao(ids_aval[idx_aval], nota, feedback):
                        st.success("Avaliação registrada!")
                        st.rerun()

        with aba3b:
            avaliacoes = listar_avaliacoes()
            if not avaliacoes:
                st.info("Nenhuma avaliação registrada ainda.")
            else:
                media = sum(a.get("nota", 0) for a in avaliacoes) / len(avaliacoes)
                st.metric("Média geral", f"{media:.1f}")
                st.markdown("---")
                for a in avaliacoes:
                    matricula = a.get("matriculas") or {}
                    cliente = (matricula.get("clientes") or {}).get("nome", "—")
                    turma = (matricula.get("turmas") or {}).get("nome", "—")
                    nota = a.get("nota", 0)
                    cor = "#E8F5E9" if nota >= 7 else "#FFF3CD" if nota >= 5 else "#FFEBEE"
                    data = a.get("data_avaliacao", "")[:10] if a.get("data_avaliacao") else "—"
                    st.markdown(f"""
                    <div style="background:{cor};padding:10px;border-radius:8px;margin-bottom:6px;">
                        <strong>{cliente}</strong> · {turma} · Nota: <strong>{nota}</strong> · {data}<br>
                        <small>{a.get('feedback', '')}</small>
                    </div>
                    """, unsafe_allow_html=True)

    # ABA 4 — VALIDAR CERTIFICADO
    with aba4:
        st.markdown("### 🔍 Validar certificado")
        st.markdown("Digite o código de validação para verificar a autenticidade do certificado.")

        codigo_busca = st.text_input("Código de validação", placeholder="Ex: A1B2C3D4")

        if st.button("🔍 Validar"):
            if not codigo_busca:
                st.warning("Digite o código.")
            else:
                cert = buscar_certificado_por_codigo(codigo_busca)
                if cert:
                    cliente = cert.get("clientes") or {}
                    turma = cert.get("turmas") or {}
                    curso = turma.get("cursos") or {}
                    st.success("✅ Certificado válido e autêntico!")
                    html = gerar_html_certificado(
                        cliente.get("nome", "—"),
                        curso.get("nome", "—"),
                        turma.get("carga_horaria"),
                        cert.get("data_emissao", ""),
                        cert.get("codigo_validacao", "—")
                    )
                    st.components.v1.html(html, height=500)
                else:
                    st.error("❌ Certificado não encontrado. Verifique o código e tente novamente.")