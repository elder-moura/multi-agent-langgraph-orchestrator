import streamlit as st
import os
import json
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph import StateGraph, END

# ==========================================================
# 1. CONFIGURAÇÃO DA INTERFACE E ESTADO DA SESSÃO
# ==========================================================
st.set_page_config(page_title="LangGraph Agent + Tools", layout="wide")

if "resultado_final" not in st.session_state:
    st.session_state.resultado_final = ""
if "logs_agentes" not in st.session_state:
    st.session_state.logs_agentes = []

st.title("🧠 LangGraph Multi-Agent com Chamada de Ferramentas (Tools)")
st.markdown("Os agentes agora podem decidir, de forma autônoma, pesquisar na internet antes de responder.")

# ==========================================================
# 2. BARRA LATERAL (CONFIGURAÇÕES)
# ==========================================================
with st.sidebar:
    st.header("⚙️ Configurações")
    groq_key = st.text_input("Groq API Key", type="password", help="Insira sua chave gsk_...")
    
    modelo_selecionado = st.selectbox(
        "Cérebro do Agente (LLM)",
        ["llama-3.3-70b-versatile", "llama3-8b-8192"]
    )
    
    st.divider()
    
    st.header("👤 Perfil do Especialista")
    perfil_selecionado = st.selectbox(
        "Agir como:",
        ["Analista de Tecnologia", "Contador Consultor", "Engenheiro de Software", "Especialista em Marketing"]
    )

    perfis_config = {
        "Analista de Tecnologia": {
            "role": "Analista de Tecnologia Sênior",
            "backstory": "Especialista em hardware de ponta, infraestrutura de nuvem e inteligência artificial."
        },
        "Contador Consultor": {
            "role": "Consultor Contábil e Tributário",
            "backstory": "Especialista em planejamento fiscal, legislação e análise financeira profunda."
        },
        "Engenheiro de Software": {
            "role": "Arquiteto de Sistemas Full Stack",
            "backstory": "Especialista em design de sistemas, microsserviços, escalabilidade e segurança."
        },
        "Especialista em Marketing": {
            "role": "Estrategista de Growth Marketing",
            "backstory": "Especialista em análise de mercado, SEO, tráfego e tendências de consumo digitais."
        }
    }

    if st.button("🗑️ Limpar Memória/Sessão"):
        st.session_state.resultado_final = ""
        st.session_state.logs_agentes = []
        st.rerun()

# ==========================================================
# 3. DEFINIÇÃO DO ESTADO DO GRAFO
# ==========================================================
class AgentState(TypedDict):
    tema: str
    perfil: dict
    mensagens: list[BaseMessage]       # Histórico interno para a LLM saber que usou ferramentas
    relatorio_proposto: str
    feedback_revisor: str
    revisoes_feitas: int
    aprovado: bool

# Instancia a ferramenta de busca na Web
search_tool = DuckDuckGoSearchRun()

# ==========================================================
# 4. ÁREA PRINCIPAL E LÓGICA DO GRAFO
# ==========================================================
tema_usuario = st.text_input(f"O que o {perfil_selecionado} deve analisar?", 
                            placeholder="Ex: Qual o impacto das novas GPUs da Nvidia no mercado local?")

if st.button("🚀 Iniciar Grafo Avançado"):
    if not groq_key:
        st.error("⚠️ Por favor, insira sua chave da Groq na barra lateral.")
    elif not tema_usuario:
        st.warning("⚠️ Digite um tema para a pesquisa.")
    else:
        st.session_state.logs_agentes = []
        try:
            # Inicializa a LLM conectada com as Ferramentas (Tool Binding)
            llm = ChatGroq(
                temperature=0.1,
                groq_api_key=groq_key,
                model_name=modelo_selecionado
            )
            # Vincula a ferramenta de busca ao modelo da Groq
            llm_with_tools = llm.bind_tools([search_tool])
            
            # --- DEFINIÇÃO DOS NÓS ---
            
            def node_pesquisador(state: AgentState) -> dict:
                st.session_state.logs_agentes.append("🔍 **[Pesquisador]** Analisando o problema atual...")
                
                # Se for a primeira iteração, monta o prompt inicial
                if not state["mensagens"]:
                    prompt_base = f"""Você é um {state['perfil']['role']}. {state['perfil']['backstory']}
                    Seu objetivo é gerar um relatório técnico impecável sobre o tema: '{state['tema']}'.
                    
                    Regra Crítica: Se você não tiver dados atualizados de 2025/2026 sobre este tema, você DEVE usar a ferramenta 'duckduckgo_search' para pesquisar na internet antes de entregar a resposta final.
                    Retorne o relatório final estruturado em Markdown."""
                    mensagens_atuais = [HumanMessage(content=prompt_base)]
                else:
                    mensagens_atuais = state["mensagens"]
                    
                # Caso o revisor tenha mandado de volta com feedbacks
                if state["feedback_revisor"]:
                    mensagens_atuais.append(HumanMessage(content=f"Corrija os seguintes pontos apontados pelo Revisor:\n{state['feedback_revisor']}"))
                
                resposta = llm_with_tools.invoke(mensagens_atuais)
                
                # Adiciona a resposta da IA na lista de mensagens do estado
                mensagens_atuais.append(resposta)
                
                return {
                    "mensagens": mensagens_atuais,
                    "relatorio_proposto": resposta.content if not resposta.tool_calls else ""
                }

            def node_ferramentas(state: AgentState) -> dict:
                st.session_state.logs_agentes.append("🌐 **[Sistema de Ferramentas]** O agente decidiu pesquisar na internet por dados recentes...")
                
                ultima_mensagem = state["mensagens"][-1]
                mensagens_atualizadas = list(state["mensagens"])
                
                for tool_call in ultima_mensagem.tool_calls:
                    if tool_call["name"] == "duckduckgo_search":
                        query = tool_call["args"]["query"]
                        st.session_state.logs_agentes.append(f"📡 Buscando na Web por: *'{query}'*")
                        
                        # Executa a busca real na internet
                        resultado_busca = search_tool.run(query)
                        
                        # Devolve o resultado como uma mensagem de ferramenta para a IA ler
                        mensagem_ferramenta = ToolMessage(
                            content=resultado_busca, 
                            tool_call_id=tool_call["id"],
                            name=tool_call["name"]
                        )
                        mensagens_atualizadas.append(mensagem_ferramenta)
                
                return {"mensagens": mensagens_atualizadas}

            def node_revisor(state: AgentState) -> dict:
                st.session_state.logs_agentes.append("⚖️ **[Revisor]** Inspecionando o relatório em busca de falhas técnicas ou falta de dados...")
                
                prompt_revisao = f"""Você é um Revisor e Auditor Científico Sênior. 
                Avalie com rigor se este relatório atende com profundidade e precisão ao tema '{state['tema']}':
                
                ---
                {state['relatorio_proposto']}
                ---
                
                Você já realizou {state['revisoes_feitas']} revisões. Limite máximo: 2.
                Responda estritamente neste formato JSON bruto (sem markdown):
                {{"aprovado": true ou false, "feedback": "liste o que melhorar se for reprovado"}}"""
                
                resposta = llm.invoke([HumanMessage(content=prompt_revisao)])
                
                try:
                    res_json = json.loads(resposta.content.replace("```json", "").replace("```", "").strip())
                    aprovado = res_json.get("aprovado", False)
                    feedback = res_json.get("feedback", "")
                except:
                    aprovado = "true" in resposta.content.lower()
                    feedback = "Polir detalhes e rigor técnico." if not approved else ""
                    
                if state['revisoes_feitas'] >= 1:
                    aprovado = True
                    st.session_state.logs_agentes.append("⏱️ **[Sistema]** Teto de iterações alcançado. Forçando aprovação.")
                    
                return {
                    "aprovado": aprovado,
                    "feedback_revisor": feedback,
                    "revisoes_feitas": state['revisoes_feitas'] + 1
                }

            # --- ARESTAS DE ROTEAMENTO CONDICIONAL ---
            
            def roteador_pesquisador(state: AgentState):
                # Se a última mensagem da IA tiver pedidos de chamadas de ferramenta
                ultima_msg = state["mensagens"][-1]
                if hasattr(ultima_msg, "tool_calls") and ultima_msg.tool_calls:
                    return "chamar_ferramenta"
                return "ir_para_revisor"

            def roteador_revisor(state: AgentState):
                if state["aprovado"]:
                    st.session_state.logs_agentes.append("✅ **[Revisor]** Relatório validado e aprovado com sucesso!")
                    return "finalizar"
                else:
                    st.session_state.logs_agentes.append(f"🔄 **[Revisor -> Pesquisador]** Reprovado! Feedback técnico enviado.")
                    return "corrigir"

            # --- MONTAGEM DO GRAFO AVANÇADO ---
            workflow = StateGraph(AgentState)

            # Adiciona os 3 nós
            workflow.add_node("Pesquisador", node_pesquisador)
            workflow.add_node("Ferramentas", node_ferramentas)
            workflow.add_node("Revisor", node_revisor)

            # Define fluxo de entrada e decisões do Pesquisador (Se usa ferramenta ou se entrega)
            workflow.set_entry_point("Pesquisador")
            workflow.add_conditional_edges(
                "Pesquisador",
                roteador_pesquisador,
                {
                    "chamar_ferramenta": "Ferramentas",
                    "ir_para_revisor": "Revisor"
                }
            )

            # O nó de ferramentas sempre devolve o fluxo para o Pesquisador ler o resultado
            workflow.add_edge("Ferramentas", "Pesquisador")

            # Decisões do Revisor (Se aprova ou manda corrigir)
            workflow.add_conditional_edges(
                "Revisor",
                roteador_revisor,
                {
                    "corrigir": "Pesquisador",
                    "finalizar": END
                }
            )

            app_com_tools = workflow.compile()

            # --- EXECUÇÃO ---
            with st.status("Executando Grafo com Tool Calling...", expanded=True) as status:
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
                
                resultado = app_com_tools.invoke(estado_inicial)
                
                for log in st.session_state.logs_agentes:
                    container_logs.markdown(log)
                    
                st.session_state.resultado_final = resultado["relatorio_proposto"]
                status.update(label="✅ Fluxo Finalizado!", state="complete")

        except Exception as e:
            st.error(f"Erro na execução: {e}")

# EXIBIÇÃO DO RESULTADO
if st.session_state.resultado_final:
    st.divider()
    st.subheader(f"📄 Relatório Final Enriquecido com buscas da Web")
    st.markdown(st.session_state.resultado_final)
    
    st.download_button(
        label="📥 Baixar Documento (.md)",
        data=str(st.session_state.resultado_final),
        file_name=f"analise_tools_{perfil_selecionado.replace(' ', '_')}.md",
        mime="text/markdown"
    )
