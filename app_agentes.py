import streamlit as st
import os
from typing import TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

# ==========================================================
# 1. CONFIGURAÇÃO DA INTERFACE E ESTADO DA SESSÃO
# ==========================================================
st.set_page_config(page_title="LangGraph Multi-Agent", layout="wide")

if "resultado_final" not in st.session_state:
    st.session_state.resultado_final = ""
if "logs_agentes" not in st.session_state:
    st.session_state.logs_agentes = []

st.title("🧠 LangGraph Conversational Multi-Agent Graph")
st.markdown("Sistema de agentes em grafo com loops de revisão e feedback dinâmico.")

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
            "backstory": "Especialista em hardware, tendências de IA e métricas de desempenho técnico."
        },
        "Contador Consultor": {
            "role": "Consultor Contábil e Tributário",
            "backstory": "Especialista em legislação brasileira, análise de balanços e planejamento fiscal."
        },
        "Engenheiro de Software": {
            "role": "Arquiteto de Sistemas Full Stack",
            "backstory": "Especialista em Clean Code, escalabilidade, segurança e padrões de projeto modernos."
        },
        "Especialista em Marketing": {
            "role": "Estrategista de Growth Marketing",
            "backstory": "Especialista em comportamento do consumidor, SEO, tráfego pago e branding digital."
        }
    }

    if st.button("🗑️ Limpar Memória/Sessão"):
        st.session_state.resultado_final = ""
        st.session_state.logs_agentes = []
        st.rerun()

# ==========================================================
# 3. DEFINIÇÃO DO ESTADO DO GRAFO (ESTADO COMPARTILHADO)
# ==========================================================
# O LangGraph exige um "State" para que os agentes compartilhem o mesmo contexto.
class AgentState(TypedDict):
    tema: str
    perfil: dict
    relatorio_proposto: str
    feedback_revisor: str
    revisoes_feitas: int
    aprovado: bool

# ==========================================================
# 4. ÁREA PRINCIPAL E LOGICA DO GRAFO
# ==========================================================
tema_usuario = st.text_input(f"O que o {perfil_selecionado} deve analisar?", 
                            placeholder="Digite o tema ou problema aqui...")

if st.button("🚀 Iniciar Processo em Grafo"):
    if not groq_key:
        st.error("⚠️ Por favor, insira sua chave da Groq na barra lateral.")
    elif not tema_usuario:
        st.warning("⚠️ Digite um tema para a pesquisa.")
    else:
        st.session_state.logs_agentes = []
        try:
            # Inicializa a LLM da Groq via LangChain
            llm = ChatGroq(
                temperature=0.1,  # Disciplina técnica rigorosa
                groq_api_key=groq_key,
                model_name=modelo_selecionado
            )
            
            # --- DEFINIÇÃO DOS NÓS DO GRAFO (OS AGENTES) ---
            
            def node_pesquisador(state: AgentState) -> dict:
                st.session_state.logs_agentes.append(f"🔍 **[Pesquisador]** Iniciando análise ou aplicando correções...")
                
                contexto_prompt = f"""
                Você é um {state['perfil']['role']}. Histórico: {state['perfil']['backstory']}.
                Seu objetivo é fazer uma análise profunda sobre o tema: {state['tema']}.
                
                Fator Crítico (Conversação): Se houver feedback do revisor abaixo, você DEVE corrigir e aprimorar o texto ignorando o que ele criticou.
                Feedback anterior do Revisor: {state['relatorio_proposto']}
                Críticas para corrigir: {state['feedback_revisor']}
                
                Retorne apenas o seu relatório técnico atualizado estruturado em Markdown.
                """
                
                resposta = llm.invoke([HumanMessage(content=contexto_prompt)])
                return {"relatorio_proposto": resposta.content}

            def node_revisor_redator(state: AgentState) -> dict:
                st.session_state.logs_agentes.append(f"⚖️ **[Revisor]** Avaliando a qualidade do relatório técnico...")
                
                contexto_prompt = f"""
                Você é um Revisor Técnico e Redator Científico exigente focado nas normas ABNT e clareza.
                Você deve avaliar o seguinte relatório proposto:
                
                ---
                {state['relatorio_proposto']}
                ---
                
                Regra de Negócio: Avalie se o relatório está completo, se tem profundidade técnica e se atende bem ao tema '{state['tema']}'.
                Limite máximo de revisões permitidas: 2. Você já revisou {state['revisoes_feitas']} vezes.
                
                Responda estritamente neste formato JSON (não coloque blocos ```json, apenas o texto bruto):
                {{
                    "aprovado": true ou false,
                    "feedback": "Se não aprovado, liste o que falta corrigir. Se aprovado, deixe em branco."
                }}
                """
                
                resposta = llm.invoke([HumanMessage(content=contexto_prompt)])
                
                # Trata a saída estruturada (JSON) de forma simples para evitar quebras
                import json
                try:
                    resultado_json = json.loads(resposta.content.replace("```json", "").replace("```", "").strip())
                    aprovado = resultado_json.get("aprovado", False)
                    feedback = resultado_json.get("feedback", "")
                except:
                    # Fallback caso o JSON venha desalinhado
                    aprovado = "true" in resposta.content.lower()
                    feedback = "Ajustar formatação geral técnica." if not aprovado else ""

                # Força aprovação se atingiu o teto de loops (evita loop infinito)
                if state['revisoes_feitas'] >= 1:
                    aprovado = True
                    st.session_state.logs_agentes.append(f"⏱️ **[Sistema]** Teto de iterações atingido. Forçando finalização.")

                return {
                    "aprovado": aprovado,
                    "feedback_revisor": feedback,
                    "revisoes_feitas": state['revisoes_feitas'] + 1
                }

            # --- ARESTA CONDICIONAL (O ROTEADOR DO GRAFO) ---
            def roteador_fluxo(state: AgentState):
                if state["aprovado"]:
                    st.session_state.logs_agentes.append("✅ **[Revisor]** Relatório aprovado com sucesso!")
                    return "finalizar"
                else:
                    st.session_state.logs_agentes.append(f"🔄 **[Revisor -> Pesquisador]** Reprovado! Enviando feedback técnico: *'{state['feedback_revisor']}'*")
                    return "corrigir"

            # --- MONTAGEM DO GRAFO ---
            workflow = StateGraph(AgentState)

            # Adiciona os nós
            workflow.add_node("Pesquisador", node_pesquisador)
            workflow.add_node("Revisor", node_revisor_redator)

            # Define a entrada e os caminhos fixos
            workflow.set_entry_point("Pesquisador")
            workflow.add_edge("Pesquisador", "Revisor")

            # Define o caminho dinâmico/cíclico (Interação Real entre Agentes)
            workflow.add_conditional_edges(
                "Revisor",
                roteador_fluxo,
                {
                    "corrigir": "Pesquisador", # Volta o fluxo pro pesquisador trabalhar de novo
                    "finalizar": END          # Termina o fluxo do grafo
                }
            )

            # Compila o grafo
            app_grafo = workflow.compile()

            # --- EXECUÇÃO COM FEEDBACK NA TELA ---
            with st.status("Executando Grafo de Agentes...", expanded=True) as status:
                container_logs = st.container()
                
                # Estado Inicial
                estado_inicial = {
                    "tema": tema_usuario,
                    "perfil": perfis_config[perfil_selecionado],
                    "relatorio_proposto": "",
                    "feedback_revisor": "",
                    "revisoes_feitas": 0,
                    "aprovado": False
                }
                
                # Roda o grafo completo
                resultado_final_grafo = app_grafo.invoke(estado_inicial)
                
                # Atualiza logs dinâmicos na tela
                for log in st.session_state.logs_agentes:
                    container_logs.markdown(log)
                
                st.session_state.resultado_final = resultado_final_grafo["relatorio_proposto"]
                status.update(label="✅ Grafo Concluído!", state="complete", expanded=True)

        except Exception as e:
            st.error(f"Erro na execução do Grafo: {e}")

# EXIBIÇÃO DOS RESULTADOS
if st.session_state.resultado_final:
    st.divider()
    st.subheader(f"📄 Relatório Final Aprovado pelo Revisor ({perfil_selecionado})")
    st.markdown(st.session_state.resultado_final)
    
    st.download_button(
        label="📥 Baixar Documento",
        data=str(st.session_state.resultado_final),
        file_name=f"analise_grafo_{perfil_selecionado.replace(' ', '_')}.md",
        mime="text/markdown"
    )