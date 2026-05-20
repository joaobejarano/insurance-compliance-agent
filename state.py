"""
State do Insurance Compliance Agent.
O quadro branco compartilhado — todos os nós leem e escrevem aqui.

EVOLUÇÃO:
- v1 (Dia 2): pipeline fixa, sem campo de routing
- v2 (Dia 5): supervisor pattern, adicionado next_agent pra routing dinâmico
"""

from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages


class InsuranceState(TypedDict):
    # ── Mensagens do chat ──
    # Reducer: add_messages (concatena + atualiza por ID)
    messages: Annotated[list, add_messages]

    # ── Classificação do documento ──
    # Sem reducer → substitui a cada update
    classification: dict | None
    # {"type": "policy|claim|complaint", "urgency": "low|high"}

    # ── Dados extraídos da apólice ──
    extracted_data: dict | None
    # {"policy_number": "...", "holder": "...", "coverage": "...", ...}

    # ── Resultado da validação de compliance ──
    compliance_result: dict | None
    # {"status": "pass|fail", "gaps": [...], "warnings": [...]}

    # ── Relatório final ──
    report: str | None

    # ── Aprovação humana ──
    approved: bool | None

    # ── Routing do supervisor (v2) ──
    # O supervisor escreve aqui pra onde o fluxo deve ir
    next_agent: str | None