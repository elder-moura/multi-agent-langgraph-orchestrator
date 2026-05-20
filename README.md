# 🤖 M.A.T.O - Multi-Agent Tech Orchestrator (LangGraph Edition)

O **M.A.T.O** é um ecossistema avançado de inteligência artificial baseado em **Sistemas Multiagentes Estocásticos e Dinâmicos**. Desenvolvido sobre o framework **LangGraph** (ecossistema LangChain), o projeto rompe a linearidade das arquiteturas sequenciais tradicionais ao implementar um **Grafo Cíclico Direcionado (DAG com loops)** focado em tomada de decisão autônoma, cooperação via estado compartilhado e governança de dados.

O sistema simula uma linha de produção corporativa inteligente, onde agentes especialistas interagem, utilizam ferramentas externas e sofrem auditoria contínua de qualidade e segurança antes de entregar o resultado ao usuário.

---

## 🔄 Arquitetura do Grafo e Engenharia de Fluxo

Diferente de sistemas rígidos, o fluxo de execução do **M.A.T.O** é determinado dinamicamente em tempo de execução pelas próprias LLMs através de nós e roteadores condicionais:

```mermaid
graph TD
    Start([Início: Input do Usuário]) --> InGuard[Input Guardrail]
    InGuard -- "Aprovado" --> Pesq[Nó Pesquisador]
    InGuard -- "Bloqueado" --> EndErr([Fim: Erro de Segurança])
    
    Pesq --> RotPesq{Roteador Pesquisador}
    RotPesq -- "Precisa de Dados Recentes" --> ToolNode[Nó de Ferramentas: Search Web]
    ToolNode --> Pesq
    RotPesq -- "Relatório Pronto" --> Rev[Nó Revisor / Auditor]
    
    Rev --> RotRev{Roteador Revisor}
    RotRev -- "Reprovado (Feedback)" --> Pesq
    RotRev -- "Aprovado" --> OutGuard[Output Guardrail]
    
    OutGuard --> EndSuccess([Fim: Entrega Higienizada LGPD])


Nó Pesquisador (Persona Concomitante): Assume o papel da persona selecionada e rascunha a análise técnica profunda. Possui capacidade cognitiva de avaliar a sua própria falta de dados históricos (degradação de contexto) e solicitar acesso à internet.

Nó de Ferramentas (Tool Calling): Executa buscas assíncronas em tempo real na web via motor DuckDuckGo para alimentar a memória do grafo com factos atualizados.

Nó Revisor (Auditoria e Qualidade): Atua como uma barreira rígida de controlo de qualidade, analisando criticamente o texto gerado e emitindo pareceres estruturados em JSON. Se houver falhas, o roteador condicional devolve a tarefa ao nó inicial, gerando um loop de auto-correção.

## 🛡️ **Camada de Governança e Segurança: Guardrails**
O projeto foi construído sob os pilares da segurança cibernética e conformidade regulatória com a LGPD (Lei Geral de Proteção de Dados):

Input Guardrail (Filtro de Entrada): Intercepta o prompt do utilizador antes do processamento da LLM, neutralizando ataques de Prompt Injection / Jailbreak (tentativas de subverter as regras do sistema) e bloqueando requisições com termos de risco de forma determinística.

Output Guardrail (Filtro de Saída): Um scanner pós-processamento que analisa o relatório homologado e mascara de forma autónoma dados sensíveis de identificação pessoal (PII) — como CPFs, RGs ou e-mails — garantindo privacidade absoluta na entrega final.

## 🛠️ **Stack Tecnológica**
Python 3.10+

LangGraph: Orquestração de fluxos cíclicos baseados em estados partilhados (AgentState).

LangChain Core & Community: Abstração de mensagens, tool binding e conectores comunitários.

ChatGroq (LLM Engine): Modelos de inferência de altíssima velocidade (Llama 3.3 70B / Llama 3 8B).

Streamlit: Interface web responsiva para renderização dos logs de execução e outputs.


## 🚀 **Como Executar o Projeto**

1. Clonar o Repositório
Bash - git clone https://github.com/elder-moura/multi-agent-langgraph-orchestrator.git
cd multi-agent-langgraph-orchestrator

2. Configurar o Ambiente e Instalar Dependências
Recomenda-se o uso do GitHub Codespaces ou ambiente virtual local. Instale os pacotes necessários:
python -m pip install -r requirements.txt

3. Executar a Aplicação via Streamlit
Inicie o motor do servidor web da aplicação:
Bash - python -m streamlit run app_agentes.py

## 📖 **Conceitos de Engenharia de IA Aplicados**
Para fins de avaliação académica e portfólio corporativo, este projeto implementa e valida empiricamente:

Stateful Multi-Agent Systems: Persistência e mutabilidade de contexto através de um objeto centralizado de mensagens.

Deterministic vs Stochastic Control: União de segurança determinística (Regex/Strings) com cognição estocástica (LLM).

ReAct Framework (Reasoning and Acting): Paradigma onde o agente pensa o que precisa de fazer e executa ações por meio de ferramentas antes de responder.

Graceful Convergence: Lógica de travamento contra loops infinitos (circuit breaker) baseada em teto de iterações configurado no estado do grafo.

-----------------------------------------------------------------------------------------------------------------------------------------------------------
Desenvolvido por Elder Moura como projeto avançado de Engenharia de Software e Inteligência Artificial.
