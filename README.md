# 🧠 Multi-Agent Conversational Graph (LangGraph)

Este repositório contém uma aplicação avançada de **Inteligência Artificial Multi-Agente** baseada em **Grafos Cíclicos Direcionados (DAG)**, desenvolvida utilizando o framework **LangGraph** (ecossistema LangChain).

Diferente de arquiteturas lineares tradicionais, este sistema implementa uma **interação real e dinâmica** entre os agentes por meio de um estado compartilhado e loops de feedback/revisão.

## 🔄 Arquitetura do Grafo (Como funciona)

O sistema quebra a linearidade do desenvolvimento de software tradicional através de nós e arestas condicionais:

1. **Nó Pesquisador:** Recebe o tema do usuário e gera um rascunho técnico baseado no perfil selecionado.
2. **Nó Revisor:** Atua como um controle de qualidade rigoroso, avaliando o texto e emitindo uma nota/aprovação em formato JSON estruturado.
3. **Aresta Condicional (Roteador):** Se o Revisor aprovar, o fluxo se encerra. Se reprovar, o fluxo **retorna** dinamicamente para o Pesquisador com críticas estruturadas, forçando uma nova iteração e correção de forma autônoma.

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **LangGraph & LangChain Core:** Orquestração baseada em estados e grafos.
- **LangChain Groq:** Integração de modelos de linguagem de altíssima velocidade (Llama 3).
- **Streamlit:** Interface de usuário para exibição dos logs de conversação em tempo real.
- **GitHub Codespaces:** Ambiente de desenvolvimento em nuvem.

## 🚀 Como Executar

1. Instale as dependências:
   ```bash
   python -m pip install -r requirements.txt

## Desenvolvido por Elder Moura como um estudo avançado sobre coordenação, comunicação e tomada de decisão em sistemas multiagentes.

  
