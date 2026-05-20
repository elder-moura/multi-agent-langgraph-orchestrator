import streamlit as st
import os
import json
import re  
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph import StateGraph, END

# ==========================================================
# 1. CONFIGURAÇÃO DA INTERFACE E ESTADO DA SESSÃO
# ==========================================================
st.set_page_config(page_title="M.A.T.O - LangGraph Pro", layout="wide")

if "resultado_final" not in st.session_state:
    st.session_state.resultado_final = ""
if "logs_agentes" not in st.session_state:
    st.session_state.logs_agentes = []

st.title("🤖 M.A.T.O - Multi-Agent Tech Orchestrator")

# ==========================================================
# 2. CAMADA DE SEGURANÇA: GUARDRAILS DETERMINÍSTICOS
# ==========================================================
def guardrail_entrada(tema: str) -> tuple[bool, str]:
    """
    Input Guardrail: Bloqueia termos inadequados e tentativas de engenharia de prompt (Jailbreak).
    """
    termos_proibidos = [
        "hackear", "crackear", "pirataria", "burlar sistema", 
        "criar virus", "criar vírus", "ofensivo", "vazar dados"
    ]
    tema_lower = tema.lower()
    
    # 1. Verificação de termos de risco
    for termo in termos_proibidos:
        if termo in tema_lower:
            return False, f"⚠️ **Bloqueio de Segurança:** O termo '{termo}' viola as diretrizes de governança do sistema."
            
    # 2. Proteção contra Prompt Injection
    if "ignore as instruções" in tema_lower or "esqueça seu papel" in tema_lower or "ignore as instrucoes" in tema_lower:
        return False, "⚠️ **Aviso de Segurança:** Tentativa de Prompt Injection / Jailbreak detectada e neutralizada."
        
    return True, ""

def guardrail_saida(texto_relatorio: str) -> str:
    """
    Output Guardrail: Varre o texto final e mascara informações sensíveis (Conformidade LGPD).
    """
    # Expressão Regular para capturar CPFs (com ou sem pontuação)
    padrao_cpf = r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b'
    # Expressão Regular para capturar E-mails
    padrao_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Mascara as informações encontradas
    texto_protegido = re.sub(padrao_cpf, "[DADO SENSÍVEL MASCARADO (LGPD)]", texto_relatorio)
    texto_protegido = re.sub(padrao_email, "[E-MAIL PROTEGIDO PARA PRIVACIDADE]", texto_protegido)
    
    return texto_protegido

# ==========================================================
# 3. BARRA LATERAL (CONFIGURAÇÕES E DESIGN DO GRAFO)
# ==========================================================
with st.sidebar:
    st.header("⚙️ Configurações Gerais")
    groq_key = st.text_input("Groq API Key", type="password", help="Insira sua chave gsk_...")
    
    modelo_selecionado = st.selectbox(
        "Cérebro do Agente (LLM)",
        ["llama-3.3-70b-versatile", "llama3-8b-8192"]
    )
    
    st.divider()
    
    st.header("👤 Perfil do Especialista")
    perfil_selecionado = st.selectbox(
        "Selecionar Persona:",
        ["Analista de Tecnologia", "Contador Consultor", "Engenheiro de Software", "Especialista em Marketing"]
    )

    perfis_config = {
        "Analista de Tecnologia": {
            "role": "Analista de Tecnologia Sênior",
            "backstory": "Especialista em hardware de ponta, infraestrutura de nuvem, IA e análise de benchmarks."
        },
        "Contador Consultor": {
            "role": "Consultor Contábil e Tributário",
            "backstory": "Especialista em planejamento fiscal estratégico, legislação brasileira e análise financeira de balanços."
        },
        "Engenheiro de Software": {
            "role": "Arquiteto de Sistemas Full Stack",
            "backstory": "Especialista em Clean Code, microsserviços, escalabilidade, segurança cibernética e design patterns."
        },
        "Especialista em Marketing": {
            "role": "Estrategista de Growth Marketing",
            "backstory": "Especialista em comportamento do consumidor digital, SEO avançado, tráfego e tendências de mercado."
        }
    }

    if st.button("🗑️ Limpar Memória do App"):
        st.session_state.resultado_final = ""
        st.session_state.logs_agentes = []
        st.rerun()

# ==========================================================
# 4. DEFINIÇÃO DO ESTADO DO GRAFO (STATE)
# ==========================================================
class AgentState(TypedDict):
    tema: str
    perfil: dict
    mensagens: list[BaseMessage]
    relatorio_proposto: str
    feedback_revisor: str
    revisoes_feitas: int
    aprovado: bool

# Inicializa a ferramenta de busca
search_tool = DuckDuckGoSearchRun()

# ==========================================================
# 5. ÁREA PRINCIPAL DO COMPONENTE WEB
# ==========================================================
tema_usuario = st.text_input(f"O que o {perfil_selecionado} deve analisar hoje?", 
                            placeholder="Digite o cenário, problema ou tema de pesquisa...")

if st.button("🚀 Iniciar Grafo com Segurança"):
    if not groq_key:
        st.error("⚠️ Por favor, insira sua chave da Groq na barra lateral.")
    elif not tema_usuario:
        st.warning("⚠️ O campo de busca/tema não pode ficar vazio.")
    else:
        
        # 🛡️ DISPARO DO GUARDRAIL DE ENTRADA
        sucesso_entrada, mensagem_erro = guardrail_entrada(tema_usuario)
        
        if not sucesso_entrada:
            st.error(mensagem_erro)
        else:
            st.session_state.logs_agentes = []
            try:
                # Inicializa a LLM da Groq
                llm = ChatGroq(
                    temperature=0.1,  # Rigor técnico máximo
                    groq_api_key=groq_key,
                    model_name=modelo_selecionado
                )
                
                # Faz o "bind" (vínculo) das ferramentas na LLM do Pesquisador
                llm_with_tools = llm.bind_tools([search_tool])
                
                # --- DEFINIÇÃO DOS NÓS (NODES) ---
                
                def node_pesquisador(state: AgentState) -> dict:
                    st.session_state.logs_agentes.append("🔍 **[Pesquisador]** Avaliando o cenário e cruzando referências...")
                    
                    if not state["mensagens"]:
                        prompt_base = f"""Você é um {state['perfil']['role']}. Backstory: {state['perfil']['backstory']}
                        Seu objetivo é gerar um relatório técnico impecável e profundo sobre o tema: '{state['tema']}'.
                        
                        Regra de Operação: Se você precisar de dados reais ou atualizados sobre este tema, você DEVE acionar a ferramenta 'duckduckgo_search' para coletar evidências na web antes de formular o relatório final.
                        Retorne seu relatório final estruturado em Markdown completo."""
                        mensagens_atuais = [HumanMessage(content=prompt_base)]
                    else:
                        mensagens_atuais = state["mensagens"]
                        
                    if state["feedback_revisor"]:
                        mensagens_atuais.append(HumanMessage(content=f"Ajuste o relatório com base nas críticas do Revisor:\n{state['feedback_revisor']}"))
                    
                    resposta = llm_with_tools.invoke(mensagens_atuais)
                    mensagens_atuais.append(resposta)
                    
                    return {
                        "mensagens": mensagens_atuais,
                        "relatorio_proposto": resposta.content if not resposta.tool_calls else ""
                    }

                def node_ferramentas(state: AgentState) -> dict:
                    st.session_state.logs_agentes.append("🌐 **[Sistema de Ferramentas]** Agente solicitou acesso externo. Varrendo a internet...")
                    
                    ultima_mensagem = state["mensagens"][-1]
                    mensagens_atualizadas = list(state["mensagens"])
                    
                    for tool_call in ultima_mensagem.tool_calls:
                        if tool_call["name"] == "duckduckgo_search":
                            query = tool_call["args"]["query"]
                            st.session_state.logs_agentes.append(f"📡 Realizando busca semântica por: *'{query}'*")
                            
                            resultado_busca = search_tool.run(query)
                            
                            mensagem_ferramenta = ToolMessage(
                                content=resultado_busca, 
                                tool_call_id=tool_call["id"],
                                name=tool_call["name"]
                            )
                            mensagens_atualizadas.append(mensagem_ferramenta)
                    
                    return {"mensagens": mensagens_atualizadas}

                def node_revisor(state: AgentState) -> dict:
                    st.session_state.logs_agentes.append("⚖️ **[Revisor]** Auditando a qualidade técnica do relatório gerado...")
                    
                    prompt_revisao = f"""Você é um Auditor e Revisor Técnico Científico. 
                    Verifique se o seguinte relatório atende com excelência ao tema '{state['tema']}':
                    
                    ---
                    {state['relatorio_proposto']}
                    ---
                    
                    Total de revisões processadas até agora: {state['revisoes_feitas']}/2.
                    Responda única e exclusivamente neste formato JSON estruturado:
                    {{"aprovado": true ou false, "feedback": "escreva os pontos que necessitam de melhoria ou correções se for reprovado"}}"""
                    
                    resposta = llm.invoke([HumanMessage(content=prompt_revisao)])
                    
                    try:
                        res_json = json.loads(resposta.content.replace("```json", "").replace("```", "").strip())
                        aprovado = res_json.get("aprovado", False)
                        feedback = res_json.get("feedback", "")
                    except:
                        aprovado = "true" in resposta.content.lower()
                        feedback = "Ajustar refinamentos textuais e normativas técnicas." if not aprovado else ""
                        
                    if state['revisoes_feitas'] >= 1:
                        aprovado = True
                        st.session_state.logs_agentes.append("⏱️ **[Sistema]** Limite de iterações atingido no Grafo. Forçando convergência e aprovação.")
                        
                    return {
                        "aprovado": aprovado,
                        "feedback_revisor": feedback,
                        "revisoes_feitas": state['revisoes_feitas'] + 1
                    }

                # --- ARESTAS CONDICIONAIS (ROTEADORES) ---
                def roteador_pesquisador(state: AgentState):
                    ultima_msg = state["mensagens"][-1]
                    if hasattr(ultima_msg, "tool_calls") and ultima_msg.tool_calls:
                        return "chamar_ferramenta"
                    return "ir_para_revisor"

                def roteador_revisor(state: AgentState):
                    if state["aprovado"]:
                        st.session_state.logs_agentes.append("✅ **[Revisor]** Relatório homologado com sucesso!")
                        return "finalizar"
                    else:
                        st.session_state.logs_agentes.append("🔄 **[Revisor -> Pesquisador]** Reprovado! Enviando correções ao nó inicial.")
                        return "corrigir"

                # --- MONTAGEM E COMPILAÇÃO DO GRAFO (LANGGRAPH) ---
                workflow = StateGraph(AgentState)

                workflow.add_node("Pesquisador", node_pesquisador)
                workflow.add_node("Ferramentas", node_ferramentas)
                workflow.add_node("Revisor", node_revisor)

                workflow.set_entry_point("Pesquisador")
                
                workflow.add_conditional_edges(
                    "Pesquisador",
                    roteador_pesquisador,
                    {
                        "chamar_ferramenta": "Ferramentas",
                        "ir_para_revisor": "Revisor"
                    }
                )

                workflow.add_edge("Ferramentas", "Pesquisador")
                
                workflow.add_conditional_edges(
                    "Revisor",
                    roteador_revisor,
                    {
                        "corrigir": "Pesquisador",
                        "finalizar": END
                    }
                )

                app_com_tools = workflow.compile()

                # --- FLUXO DE EXECUÇÃO WEB ---
                with st.status("Executando Grafo com Tool Calling e Guardrails...", expanded=True) as status:
                    container_logs = st.container()
                    
                    estado_inicial = {
                        "tema": tema_usuario,
                        "perfil": perfis_config[perfil_selecionado],
                        "mensagens": [],
                        "relatorio_proposto": "",
                        "feedback_revisor": "",
                        "revisoes_feitas": 0,
                        "aprovado": False
                    }
                    
                    # Invoca o grafo rodando a lógica completa
                    resultado = app_com_tools.invoke(estado_inicial)
                    
                    # Exibe logs dinamicamente na tela
                    for log in st.session_state.logs_agentes:
                        container_logs.markdown(log)
                        
                    # 🛡️ DISPARO DO GUARDRAIL DE SAÍDA ANTES DA EXIBIÇÃO
                    relatorio_cru = resultado["relatorio_proposto"]
                    relatorio_higienizado = guardrail_saida(relatorio_cru)
                    
                    st.session_state.resultado_final = relatorio_higienizado
                    status.update(label="✅ Grafo Concluído de Forma Segura!", state="complete")

            except Exception as e:
                st.error(f"Erro interno no processamento do Grafo: {e}")

# EXIBIÇÃO DOS RESULTADOS FINAIS
if st.session_state.resultado_final:
    st.divider()
    st.subheader(f"📄 Relatório Final Higienizado ({perfil_selecionado})")
    st.markdown(st.session_state.resultado_final)
    
    st.download_button(
        label="📥 Baixar Documento Aprovado (.md)",
        data=str(st.session_state.resultado_final),
        file_name=f"analise_segura_{perfil_selecionado.replace(' ', '_')}.md",
        mime="text/markdown"
    )
