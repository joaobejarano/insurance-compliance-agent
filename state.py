"""
State do Insurance Compliance Agent.
O quadro branco compartilhado — todos os nós leem e escrevem aqui.
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
    # Formato esperado: {"type": "policy|claim|complaint", "urgency": "low|high"}
    
    # ── Dados extraídos da apólice ──
    extracted_data: dict | None
    # Formato esperado: {"policy_number": "...", "holder": "...", "coverage": "...", ...}
    
    # ── Resultado da validação de compliance ──
    compliance_result: dict | None
    # Formato esperado: {"status": "pass|fail", "gaps": [...], "warnings": [...]}
    
    # ── Relatório final ──
    report: str | None
    
    # ── Aprovação humana ──
    approved: bool | None