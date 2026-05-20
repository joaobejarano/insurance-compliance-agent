"""
Nodes do Insurance Compliance Agent — v2 (Supervisor Pattern).

EVOLUÇÃO:
- v1 (Dia 2): pipeline fixa (extract → validate → report)
  Motivo: ordem determinística, sem overhead de supervisor LLM
- v2 (Dia 5): supervisor pattern (supervisor decide dinamicamente)
  Motivo: mais flexível, demonstra LangGraph multi-agent,
  permite adicionar novos workers sem refatorar o fluxo
"""

import json
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from state import InsuranceState
from tools import (
    extract_policy_data,
    check_compliance_rules,
    generate_compliance_report,
)


# ── Modelos ──
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
supervisor_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ═══════════════════════════════════════════════════════
# NÓ 1: CLASSIFY (sem mudança — só ajustou o goto)
# ═══════════════════════════════════════════════════════

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
    Literal["supervisor", "human_review"]
]:
    """
    Porteiro do sistema: classifica o documento e decide o caminho.
    Urgente → vai direto pro humano (pula processamento).
    Normal → vai pro SUPERVISOR (antes ia direto pro extract).
    """
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

    result = classification.model_dump()

    if result["urgency"] == "high":
        return Command(
            update={"classification": result},
            goto="human_review",
        )

    return Command(
        update={"classification": result},
        goto="supervisor",  # v1: "agent_extract" → v2: "supervisor"
    )


# ═══════════════════════════════════════════════════════
# NÓ 2: SUPERVISOR (NOVO — o cérebro do multi-agent)
# Analisa o estado e decide qual worker chamar
# ═══════════════════════════════════════════════════════

class SupervisorDecision(BaseModel):
    """Decisão do supervisor sobre próximo passo."""
    next_agent: Literal["extractor", "validator", "reporter", "human_review"] = Field(
        description="Which agent to call next"
    )
    reasoning: str = Field(
        description="Brief explanation of why this agent is needed next"
    )


def supervisor(state: InsuranceState) -> Command[
    Literal["extractor", "validator", "reporter", "human_review"]
]:
    """
    O chefe da equipe. Analisa o que já foi feito e decide o próximo passo.

    Na v1 isso era hardcoded: extract → validate → report.
    Na v2 o LLM decide, o que permite:
    - Lidar com edge cases
    - Adaptar a ordem baseado no conteúdo
    - Adicionar novos workers sem mudar o routing
    """
    status_summary = {
        "classification": "done" if state.get("classification") else "pending",
        "extraction": "done" if state.get("extracted_data") else "pending",
        "compliance_check": "done" if state.get("compliance_result") else "pending",
        "report": "done" if state.get("report") else "pending",
    }

    decision = supervisor_llm.with_structured_output(
        SupervisorDecision
    ).invoke(
        f"""You are a supervisor managing an insurance document analysis team.

Current status of the analysis:
{json.dumps(status_summary, indent=2)}

Your team members:
- extractor: Extracts structured data from insurance documents
- validator: Checks extracted data against compliance rules
- reporter: Generates the final compliance report
- human_review: Sends to human for final approval (only when ALL other steps are done)

Rules:
1. Extraction MUST happen before validation
2. Validation MUST happen before reporting
3. Only send to human_review when extraction, validation, AND reporting are ALL done
4. Never skip a step

What should be done next?"""
    )

    return Command(
        update={"next_agent": decision.next_agent},
        goto=decision.next_agent,
    )


# ═══════════════════════════════════════════════════════
# NÓ 3: EXTRACTOR (antes: agent_extract)
# Mudança: goto="supervisor" em vez de goto="agent_validate"
# ═══════════════════════════════════════════════════════

extract_llm = llm.bind_tools([extract_policy_data])


def extractor(state: InsuranceState) -> Command[Literal["supervisor"]]:
    """
    Worker: extrai dados do documento.
    v1: ia direto pro validate (hardcoded)
    v2: volta pro supervisor (ele decide o próximo)
    """
    response = extract_llm.invoke([
        {
            "role": "system",
            "content": """You are an insurance document data extractor.
Your job: extract ALL structured data from the insurance document.
ALWAYS use the extract_policy_data tool with the PDF file path provided by the user.
Look for the file path in the user's message.""",
        },
        *state["messages"],
    ])

    messages_to_add = [response]
    extracted = None

    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_result = extract_policy_data.invoke(tool_call["args"])
        extracted = tool_result
        messages_to_add.append(
            ToolMessage(content=tool_result, tool_call_id=tool_call["id"])
        )

    return Command(
        update={"extracted_data": extracted, "messages": messages_to_add},
        goto="supervisor",  # v1: "agent_validate" → v2: "supervisor"
    )


# ═══════════════════════════════════════════════════════
# NÓ 4: VALIDATOR (antes: agent_validate)
# Mudança: goto="supervisor" em vez de goto="agent_report"
# ═══════════════════════════════════════════════════════

validate_llm = llm.bind_tools([check_compliance_rules])


def validator(state: InsuranceState) -> Command[Literal["supervisor"]]:
    """
    Worker: verifica compliance dos dados extraídos.
    v1: ia direto pro report (hardcoded)
    v2: volta pro supervisor (ele decide o próximo)
    """
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
        update={"compliance_result": compliance, "messages": messages_to_add},
        goto="supervisor",  # v1: "agent_report" → v2: "supervisor"
    )


# ═══════════════════════════════════════════════════════
# NÓ 5: REPORTER (antes: agent_report)
# Mudança: goto="supervisor" em vez de goto="human_review"
# ═══════════════════════════════════════════════════════

report_llm = llm.bind_tools([generate_compliance_report])


def reporter(state: InsuranceState) -> Command[Literal["supervisor"]]:
    """
    Worker: gera o relatório final de compliance.
    v1: ia direto pro human_review (hardcoded)
    v2: volta pro supervisor (ele decide o próximo)
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
        update={"report": report, "messages": messages_to_add},
        goto="supervisor",  # v1: "human_review" → v2: "supervisor"
    )


# ═══════════════════════════════════════════════════════
# NÓ 6: HUMAN_REVIEW (ajustado: reject vai pro supervisor)
# ═══════════════════════════════════════════════════════

def human_review(state: InsuranceState) -> Command[
    Literal["supervisor", "__end__"]
]:
    """
    Pausa pra aprovação humana.
    Aprovado → END
    Rejeitado → volta pro SUPERVISOR com feedback (v1: voltava pro extract)
    """
    review_data = {
        "classification": state.get("classification"),
        "extracted_data": state.get("extracted_data"),
        "compliance_result": state.get("compliance_result"),
        "report": state.get("report"),
    }

    decision = interrupt({
        "message": "Please review the analysis and approve or reject.",
        "data": review_data,
    })

    if decision.get("approved"):
        return Command(
            update={"approved": True},
            goto="__end__",
        )

    feedback = decision.get("feedback", "Please redo the analysis.")
    return Command(
        update={
            "approved": False,
            "messages": [("user", f"Human feedback: {feedback}")],
            # Limpa dados pra forçar re-processamento pelo supervisor
            "extracted_data": None,
            "compliance_result": None,
            "report": None,
        },
        goto="supervisor",  # v1: "agent_extract" → v2: "supervisor"
    )