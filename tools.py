"""
Tools do Insurance Compliance Agent.
As ações que os agentes podem executar no mundo real.

IMPORTANTE: Hoje usamos mock data pra validar o fluxo.
No Dia 3, vamos trocar por OCR real (Google Document AI / PyMuPDF).
"""

import json
import pymupdf4llm
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

class PolicyData(BaseModel):
    """Schema dos dados extraídos de uma apólice de seguro."""
    policy_number: str = Field(description="Policy number (e.g. POL-2024-00789)")
    holder_name: str = Field(description="Policyholder company or person name")
    holder_employees: int | None = Field(description="Number of employees", default=None)
    business_type: str | None = Field(description="Type of business", default=None)
    annual_revenue: str | None = Field(description="Annual revenue", default=None)
    coverage_type: str = Field(description="Primary type of coverage")
    coverage_amount: str = Field(description="Primary coverage amount with currency")
    deductible: str | None = Field(description="Primary deductible amount", default=None)
    premium_annual: str | None = Field(description="Total annual premium", default=None)
    effective_date: str = Field(description="Policy start date (YYYY-MM-DD)")
    expiry_date: str = Field(description="Policy expiration date (YYYY-MM-DD)")
    additional_coverages: list[str] = Field(
        description="List of additional coverages included",
        default_factory=list,
    )
    exclusions: list[str] = Field(
        description="List of exclusions from coverage",
        default_factory=list,
    )


# LLM pra structured output (temperature=0 pra resultados consistentes)
extraction_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ═══════════════════════════════════════════════════════
# TOOL 1: EXTRACT POLICY DATA (REAL — PyMuPDF4LLM + LLM)
# Substituiu o mock do Dia 2
# ═══════════════════════════════════════════════════════

@tool
def extract_policy_data(pdf_path: str) -> str:
    """
    Extrai dados estruturados de um documento PDF de apólice de seguro.
    Recebe o caminho do arquivo PDF e retorna os dados extraídos em JSON.

    Use esta tool quando precisar analisar um documento de seguro.
    Passe o caminho completo do arquivo PDF.
    """

    # ── CAMADA 1: PyMuPDF4LLM extrai texto ──
    # Determinística, rápida (~0.1s), grátis
    # OCR automático se o PDF for escaneado
    try:
        markdown_text = pymupdf4llm.to_markdown(pdf_path)
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {pdf_path}"})
    except Exception as e:
        return json.dumps({"error": f"Failed to read PDF: {str(e)}"})

    # Verifica se extraiu algo útil
    if len(markdown_text.strip()) < 20:
        return json.dumps({"error": "PDF appears empty or unreadable"})

    # ── CAMADA 2: LLM com structured output normaliza ──
    # Probabilística, mas forçada a seguir o schema PolicyData
    # Custo: ~1-2 centavos por documento
    structured_llm = extraction_llm.with_structured_output(PolicyData)

    try:
        policy = structured_llm.invoke(
            f"""Extract all insurance policy data from this document.
Be thorough - extract every field you can find.
For dates, use YYYY-MM-DD format.
If a field is not found in the document, use null.

Document content:
{markdown_text}"""
        )
        return json.dumps(policy.model_dump(), indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to extract structured data: {str(e)}"})


# ═══════════════════════════════════════════════════════
# TOOL 2: CHECK COMPLIANCE RULES (ainda mock — Dia 4)
# ═══════════════════════════════════════════════════════

@tool
def check_compliance_rules(policy_data: str) -> str:
    """
    Verifica uma apólice contra regras regulatórias de compliance.
    Recebe os dados da apólice em JSON e retorna gaps e warnings encontrados.

    Use esta tool após extrair os dados da apólice para verificar
    se ela está em conformidade com as regras regulatórias.
    """
    # ── MOCK: será substituído no Dia 4 (Eval Pipelines) ──
    return json.dumps({
        "status": "FAIL",
        "rules_checked": 5,
        "passed": 3,
        "failed": 1,
        "warnings": 1,
        "details": [
            {
                "rule": "Minimum Liability Coverage",
                "requirement": "$1,000,000 minimum",
                "actual": "$2,000,000",
                "status": "PASS",
            },
            {
                "rule": "Workers Compensation",
                "requirement": "Required for companies with 50+ employees",
                "actual": "NOT FOUND - listed in exclusions",
                "status": "FAIL",
                "severity": "CRITICAL",
            },
            {
                "rule": "Policy Expiry",
                "requirement": "Must not expire within 90 days",
                "actual": "Expires 2025-03-15",
                "status": "WARNING",
                "severity": "MEDIUM",
            },
            {
                "rule": "Deductible Limit",
                "requirement": "Max $25,000 for this coverage tier",
                "actual": "$10,000",
                "status": "PASS",
            },
            {
                "rule": "Additional Coverage - Property",
                "requirement": "Recommended for manufacturing companies",
                "actual": "Included",
                "status": "PASS",
            },
        ],
    }, indent=2)


# ═══════════════════════════════════════════════════════
# TOOL 3: GENERATE COMPLIANCE REPORT (ainda mock — Dia 5)
# ═══════════════════════════════════════════════════════

@tool
def generate_compliance_report(policy_data: str, compliance_results: str) -> str:
    """
    Gera um relatório formal de compliance combinando dados da apólice
    e resultados da validação.

    Use esta tool após a verificação de compliance para criar
    o relatório final que será enviado para revisão humana.
    """
    # ── MOCK: será substituído no Dia 5 (GCP + Deploy) ──
    return """
        INSURANCE COMPLIANCE REPORT
        ═══════════════════════════════════════════
        Policy: POL-2024-00789
        Holder: Acme Manufacturing Corp (120 employees)
        Coverage: General Liability - $2,000,000
        Period: 2024-03-15 to 2025-03-15

        ─── COMPLIANCE STATUS: FAIL ───

        ❌ CRITICAL: Workers Compensation coverage missing
        → Required for companies with 50+ employees
        → Currently listed in policy exclusions
        → ACTION: Add Workers Comp endorsement immediately

        ⚠️  WARNING: Policy expiring within 90 days
        → Expiry: 2025-03-15
        → ACTION: Initiate renewal process

        ✅ PASSED: Minimum liability coverage ($2M >= $1M required)
        ✅ PASSED: Deductible within limits ($10K <= $25K max)
        ✅ PASSED: Property damage coverage included

        ─── SUMMARY ───
        Rules checked: 5 | Passed: 3 | Failed: 1 | Warnings: 1

        RECOMMENDATION: Policy is NON-COMPLIANT.
        Priority action required on Workers Compensation.
        ═══════════════════════════════════════════
        """