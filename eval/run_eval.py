"""
Eval Pipeline Runner — Insurance Compliance Agent.

Roda o agente contra o golden dataset e gera relatório de métricas.

Uso:
    python eval/run_eval.py              # roda todos os test cases
    python eval/run_eval.py --case TC-001  # roda um caso específico
"""

import json
import sys
import time
from pathlib import Path

# Ajusta o path pra importar do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from tools import extract_policy_data
from evaluators import eval_extraction, eval_classification, eval_with_timing, format_eval_report


def load_golden_dataset(path: str = None) -> list[dict]:
    """Carrega o golden dataset."""
    if path is None:
        path = Path(__file__).parent / "golden_dataset.json"
    with open(path) as f:
        return json.load(f)


def run_extraction_eval(test_case: dict) -> dict:
    """
    Roda o eval de extração pra um test case.
    
    Testa APENAS a tool de extração (isolada do grafo).
    Isso é intencional: testar a tool isolada identifica
    se o problema é na extração ou na orquestração.
    """
    tc_input = test_case["input"]
    tc_expected = test_case["expected"]

    result = {
        "test_case": {
            "id": test_case["id"],
            "name": test_case["name"],
            "difficulty": test_case["difficulty"],
        },
    }

    latency_steps = {}

    # ── 1. Testa extração ──
    if "extraction" in tc_expected:
        print(f"  📄 Running extraction for {tc_input['pdf_path']}...")
        
        start = time.time()
        raw_output = extract_policy_data.invoke({"pdf_path": tc_input["pdf_path"]})
        latency_steps["extraction"] = time.time() - start

        try:
            extracted = json.loads(raw_output)
        except json.JSONDecodeError:
            extracted = {}

        if "error" in extracted:
            print(f"  ❌ Extraction error: {extracted['error']}")
            result["extraction"] = {
                "field_results": {},
                "passed": 0,
                "total": len(tc_expected["extraction"]),
                "accuracy": 0,
                "error": extracted["error"],
            }
        else:
            result["extraction"] = eval_extraction(extracted, tc_expected["extraction"])

    # ── 2. Testa classificação (simula com o input) ──
    if "classification" in tc_expected:
        # Pra testar classificação sem rodar o grafo inteiro,
        # importamos e chamamos o classify diretamente
        try:
            from nodes import classify, llm, DocumentClassification

            print(f"  📋 Running classification...")

            start = time.time()
            classification_result = llm.with_structured_output(
                DocumentClassification
            ).invoke(
                f"""Classify this insurance document:

{test_case['input'].get('user_message', 'Analyze this policy document.')}

Determine the document type and urgency level.
Mark as HIGH urgency if: expired policy, missing critical coverage,
or any compliance violation that requires immediate human attention."""
            )
            latency_steps["classification"] = time.time() - start

            actual_classification = classification_result.model_dump()
            result["classification"] = eval_classification(
                actual_classification, tc_expected["classification"]
            )
        except ImportError:
            print("  ⚠️  Could not import classify node, skipping classification eval")
        except Exception as e:
            print(f"  ❌ Classification error: {e}")

    # ── 3. Latência total ──
    total_latency = sum(latency_steps.values())
    result["latency"] = {
        "steps": latency_steps,
        "total": total_latency,
    }

    return result


def main():
    """Roda o eval pipeline completo."""
    print("=" * 60)
    print("🧪 EVAL PIPELINE — Insurance Compliance Agent")
    print("=" * 60)
    print()

    # Carrega golden dataset
    dataset = load_golden_dataset()
    print(f"📦 Loaded {len(dataset)} test cases")
    print()

    # Filtra por caso específico se passado como argumento
    if len(sys.argv) > 2 and sys.argv[1] == "--case":
        case_id = sys.argv[2]
        dataset = [tc for tc in dataset if tc["id"] == case_id]
        if not dataset:
            print(f"❌ Test case {case_id} not found")
            return

    # Roda cada test case
    all_results = []

    for i, test_case in enumerate(dataset):
        print(f"[{i+1}/{len(dataset)}] Running: {test_case['id']} — {test_case['name']}")

        try:
            result = run_extraction_eval(test_case)
            all_results.append(result)

            # Mostra resultado rápido
            if "extraction" in result:
                acc = result["extraction"]["accuracy"]
                print(f"  → Extraction accuracy: {acc:.1%}")
            if "classification" in result:
                acc = result["classification"]["accuracy"]
                print(f"  → Classification accuracy: {acc:.1%}")
            if "latency" in result:
                print(f"  → Latency: {result['latency']['total']:.1f}s")

        except Exception as e:
            print(f"  ❌ Error running test case: {e}")
            all_results.append({
                "test_case": {
                    "id": test_case["id"],
                    "name": test_case["name"],
                    "difficulty": test_case.get("difficulty", "unknown"),
                },
                "error": str(e),
            })

        print()

    # Gera relatório
    report = format_eval_report(all_results)
    print(report)

    # Salva relatório
    report_path = Path(__file__).parent / "eval_report.txt"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\n📄 Report saved to: {report_path}")

    # Salva resultados detalhados em JSON
    results_path = Path(__file__).parent / "eval_results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"📊 Detailed results saved to: {results_path}")


if __name__ == "__main__":
    main()
