"""
Tools do Insurance Compliance Agent.
As ações que os agentes podem executar no mundo real.

IMPORTANTE: Hoje usamos mock data pra validar o fluxo.
No Dia 3, vamos trocar por OCR real (Google Document AI / PyMuPDF).
"""

from langchain_core.tools import tool


@tool
def extract_policy_data(document_text: str) -> str:
    """
    Extrai dados estruturados de um documento de apólice de seguro.
    Recebe o texto do documento e retorna os campos-chave.
    """
    # ── MOCK: simula extração de dados ──
    # Em produção: OCR + LLM com structured output
    return """{
        "policy_number": "POL-2024-00789",
        "holder_name": "Acme Corp",
        "holder_employees": 120,
        "coverage_type": "General Liability",
        "coverage_amount": "$2,000,000",
        "deductible": "$10,000",
        "premium_annual": "$12,400",
        "effective_date": "2024-03-15",
        "expiry_date": "2025-03-15",
        "additional_coverages": ["Property Damage", "Product Liability"],
        "exclusions": ["Cyber Liability", "Workers Compensation"]
    }"""


@tool
def check_compliance_rules(policy_data: str) -> str:
    """
    Verifica uma apólice contra regras regulatórias de compliance.
    Recebe os dados da apólice e retorna gaps e warnings.
    """
    # ── MOCK: simula verificação de compliance ──
    # Em produção: consulta banco de regras + lógica de negócio
    return """{
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
                "status": "PASS"
            },
            {
                "rule": "Workers Compensation",
                "requirement": "Required for companies with 50+ employees",
                "actual": "NOT FOUND - listed in exclusions",
                "status": "FAIL",
                "severity": "CRITICAL"
            },
            {
                "rule": "Policy Expiry",
                "requirement": "Must not expire within 90 days",
                "actual": "Expires 2025-03-15 (within 90 days)",
                "status": "WARNING",
                "severity": "MEDIUM"
            },
            {
                "rule": "Deductible Limit",
                "requirement": "Max $25,000 for this coverage tier",
                "actual": "$10,000",
                "status": "PASS"
            },
            {
                "rule": "Additional Coverage - Property",
                "requirement": "Recommended for manufacturing companies",
                "actual": "Included",
                "status": "PASS"
            }
        ]
    }"""


@tool
def generate_compliance_report(
    policy_data: str, 
    compliance_results: str
) -> str:
    """
    Gera um relatório formal de compliance combinando dados da apólice
    e resultados da validação.
    """
    # ── MOCK: simula geração de relatório ──
    # Em produção: template engine + formatação profissional
    return """
    ═══════════════════════════════════════════
    INSURANCE COMPLIANCE REPORT
    ═══════════════════════════════════════════
    
    Policy: POL-2024-00789
    Holder: Acme Corp (120 employees)
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