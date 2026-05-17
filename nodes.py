"""
Nodes do Insurance Compliance Agent.
Cada nó: recebe state → faz trabalho → retorna updates.
"""

from typing import Literal
from langchain_openai import ChatOpenAI
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from state import InsuranceState
from tools import (
    extract_policy_data,
    check_compliance_rules,
    generate_compliance_report,
)
from langchain_core.messages import ToolMessage


# ── Modelo ──
# gpt-4o-mini pra economizar nos agentes, gpt-4o se precisar de mais qualidade
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ═══════════════════════════════════════════════════════
# NÓ 1: CLASSIFY (Routing pattern)
# Classifica o documento e roteia o fluxo
# ═══════════════════════════════════════════════════════

# Structured output: força o LLM a retornar exatamente esse formato
class DocumentClassification(BaseModel):
    type: Literal["policy", "claim", "complaint"] = Field(
        description="Tipo do documento de seguro"
    )
    urgency: Literal["low", "high"] = Field(
        description="Nível de urgência. High = precisa de revisão humana imediata"
    )
    summary: str = Field(
        description="Resumo em 1 frase do conteúdo do documento"
    )


def classify(state: InsuranceState) -> Command[
    Literal["agent_extract", "human_review"]
]:
    """
    Porteiro do sistema: classifica o documento e decide o caminho.
    Urgente → vai direto pro humano (pula processamento).
    Normal → vai pro extractor.
    """
    # Pega a última mensagem (o documento enviado pelo usuário)
    last_message = state["messages"][-1].content

    classification = llm.with_structured_output(
        DocumentClassification
    ).invoke(
        f"""Classify this insurance document:

{last_message}

Determine the document type and urgency level.
Mark as HIGH urgency if: expired policy, missing critical coverage, 
or any compliance violation that requires immediate human attention."""
    )

    # Converte pra dict pra salvar no state
    result = classification.model_dump()

    if result["urgency"] == "high":
        return Command(
            update={"classification": result},
            goto="human_review",
        )

    return Command(
        update={"classification": result},
        goto="agent_extract",
    )


# ═══════════════════════════════════════════════════════
# NÓ 2: AGENT_EXTRACT (ReAct com tool de extração)
# Extrai dados estruturados do documento
# ═══════════════════════════════════════════════════════

# LLM com a tool de extração vinculada
extract_llm = llm.bind_tools([extract_policy_data])


def agent_extract(state: InsuranceState) -> Command[Literal["agent_validate"]]:
    response = extract_llm.invoke([
        {
            "role": "system",
            "content": """You are an insurance document data extractor.
Your job: extract ALL structured data from the insurance document.
ALWAYS use the extract_policy_data tool. Never skip extraction.""",
        },
        *state["messages"],
    ])

    extracted = None
    messages_to_add = [response]  # sempre salva o AIMessage

    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_result = extract_policy_data.invoke(tool_call["args"])
        extracted = tool_result

        # ✅ ToolMessage obrigatório após todo tool_call
        messages_to_add.append(
            ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_call["id"],
            )
        )

    return Command(
        update={
            "extracted_data": extracted,
            "messages": messages_to_add,
        },
        goto="agent_validate",
    )

# ═══════════════════════════════════════════════════════
# NÓ 3: AGENT_VALIDATE (ReAct com tool de compliance)
# Verifica os dados contra regras regulatórias
# ═══════════════════════════════════════════════════════

validate_llm = llm.bind_tools([check_compliance_rules])


def agent_validate(state: InsuranceState) -> Command[
    Literal["agent_report"]
]:
    """
    Validator agent: usa a tool pra verificar compliance.
    Sempre vai pro reporter depois.
    """
    # Monta contexto com os dados extraídos
    extracted = state.get("extracted_data", "No data extracted yet")

    response = validate_llm.invoke([
        {
            "role": "system",
            "content": f"""You are an insurance compliance validator.
            Your job: check the extracted policy data against regulatory rules.
            ALWAYS use the check_compliance_rules tool.

            Extracted policy data:
            {extracted}""",
                    },
                    *state["messages"],
                ])

    compliance = None
    messages_to_add = [response]

    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_result = check_compliance_rules.invoke(tool_call["args"])
        compliance = tool_result

        messages_to_add.append(
            ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_call["id"],
            )
        )

    return Command(
        update={
            "compliance_result": compliance,
            "messages": messages_to_add,
        },
        goto="agent_report",
    )


# ═══════════════════════════════════════════════════════
# NÓ 4: AGENT_REPORT (ReAct com tool de relatório)
# Gera o relatório final de compliance
# ═══════════════════════════════════════════════════════

report_llm = llm.bind_tools([generate_compliance_report])


def agent_report(state: InsuranceState) -> Command[
    Literal["human_review"]
]:
    """
    Reporter agent: gera o relatório combinando dados + compliance.
    Sempre vai pro human review depois.
    """
    extracted = state.get("extracted_data", "No data")
    compliance = state.get("compliance_result", "No compliance data")

    response = report_llm.invoke([
        {
            "role": "system",
                        "content": f"""You are an insurance compliance report generator.
            Your job: create a clear, actionable compliance report.
            ALWAYS use the generate_compliance_report tool.

            Policy data: {extracted}
            Compliance results: {compliance}""",
                    },
                    *state["messages"],
                ])

    report = None
    messages_to_add = [response]

    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_result = generate_compliance_report.invoke(tool_call["args"])
        report = tool_result

        messages_to_add.append(
            ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_call["id"],
            )
        )

    return Command(
        update={
            "report": report,
            "messages": messages_to_add,
        },
        goto="human_review",
    )


# ═══════════════════════════════════════════════════════
# NÓ 5: HUMAN_REVIEW (Human-in-the-Loop)
# Pausa pra aprovação humana
# ═══════════════════════════════════════════════════════

def human_review(state: InsuranceState) -> Command[
    Literal["agent_extract", "__end__"]
]:
    """
    Pausa o grafo e mostra resultados pro humano.
    Aprovado → END
    Rejeitado → volta pro extract com feedback
    """
    # Monta o resumo pra o humano ver
    review_data = {
        "classification": state.get("classification"),
        "extracted_data": state.get("extracted_data"),
        "compliance_result": state.get("compliance_result"),
        "report": state.get("report"),
    }

    # ── INTERRUPT: congela aqui ──
    decision = interrupt({
        "message": "Please review the analysis and approve or reject.",
        "data": review_data,
    })

    # ── Retoma quando o humano responder ──
    if decision.get("approved"):
        return Command(
            update={"approved": True},
            goto="__end__",
        )

    # Rejeitado: adiciona feedback do humano e volta pro extract
    feedback = decision.get("feedback", "Please redo the analysis.")
    return Command(
        update={
            "approved": False,
            "messages": [("user", f"Human feedback: {feedback}")],
        },
        goto="agent_extract",
    )