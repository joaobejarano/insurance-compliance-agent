"""
Montagem do grafo do Insurance Compliance Agent — v2 (Supervisor Pattern).

EVOLUÇÃO:
- v1: START → classify → extract → validate → report → human_review → END
  Pipeline fixa, edges determinísticos
  
- v2: START → classify → supervisor ⟲ [extractor | validator | reporter] → human_review → END
  Supervisor LLM decide dinamicamente qual worker chamar
  Todos os workers voltam pro supervisor após terminar

O grafo:
    START → classify → [urgente?]
                         ├─ SIM → human_review
                         └─ NÃO → supervisor ──→ extractor ──┐
                                     ↑          → validator ──┤
                                     │          → reporter  ──┘
                                     │          → human_review
                                     └──────────────┘ (workers voltam pro supervisor)
"""

from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from state import InsuranceState
from nodes import (
    classify,
    supervisor,
    extractor,
    validator,
    reporter,
    human_review,
)


def build_graph():
    """Constrói e compila o grafo do agente."""

    graph = StateGraph(InsuranceState)

    # Adiciona os nós
    graph.add_node("classify", classify)
    graph.add_node("supervisor", supervisor)
    graph.add_node("extractor", extractor)
    graph.add_node("validator", validator)
    graph.add_node("reporter", reporter)
    graph.add_node("human_review", human_review)

    # Ponto de entrada
    graph.add_edge(START, "classify")

    # O resto é via Command nos nós:
    # classify      → supervisor ou human_review
    # supervisor    → extractor, validator, reporter, ou human_review
    # extractor     → supervisor
    # validator     → supervisor
    # reporter      → supervisor
    # human_review  → supervisor (reject) ou __end__ (approve)

    # Compila com checkpointer
    checkpointer = MemorySaver()
    app = graph.compile(checkpointer=checkpointer)

    return app