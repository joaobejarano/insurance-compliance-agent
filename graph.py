"""
Montagem do grafo do Insurance Compliance Agent.
Conecta todos os nós e compila com checkpointer.
"""

from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from state import InsuranceState
from nodes import (
    classify,
    agent_extract,
    agent_validate,
    agent_report,
    human_review,
)


def build_graph():
    """Constrói e compila o grafo do agente."""

    # 1. Cria o grafo com nosso State
    graph = StateGraph(InsuranceState)

    # 2. Adiciona os nós (trabalhadores)
    graph.add_node("classify", classify)
    graph.add_node("agent_extract", agent_extract)
    graph.add_node("agent_validate", agent_validate)
    graph.add_node("agent_report", agent_report)
    graph.add_node("human_review", human_review)

    # 3. Conecta o ponto de entrada
    # Só precisamos definir o START — o resto é via Command nos nós
    graph.add_edge(START, "classify")

    # 4. Compila com checkpointer (necessário pro interrupt funcionar)
    checkpointer = MemorySaver()  # Em produção: PostgresSaver
    app = graph.compile(checkpointer=checkpointer)

    return app