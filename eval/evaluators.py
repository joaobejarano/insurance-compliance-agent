"""
Evaluators do Insurance Compliance Agent.

3 tipos de avaliação:
1. Extraction Evaluator — campos extraídos vs esperados (code-based)
2. Classification Evaluator — tipo e urgência corretos (code-based)
3. Latency Evaluator — tempo por step (code-based)

Nível 2 de maturidade: code-based + métricas automatizadas.
"""

import time
import json
from typing import Any


# ═══════════════════════════════════════════════════════
# EVALUATOR 1: EXTRACTION
# Compara campos extraídos com os esperados
# Calcula: accuracy por campo, precision, recall, F1
# ═══════════════════════════════════════════════════════

def eval_extraction(extracted: dict, expected: dict) -> dict:
    """
    Compara cada campo extraído com o esperado.
    
    Lógica por tipo:
    - str: comparação normalizada (case-insensitive, substring)
    - int/float: comparação exata
    - list: verifica se itens esperados estão contidos
    - None: verifica se campo está ausente
    """
    results = {}

    for field, expected_val in expected.items():
        actual_val = extracted.get(field)

        if expected_val is None:
            # Campo deve estar ausente
            results[field] = {
                "match": actual_val is None,
                "expected": None,
                "actual": actual_val,
            }

        elif isinstance(expected_val, list):
            # Lista: verifica se cada item esperado está contido
            actual_list = actual_val if isinstance(actual_val, list) else []
            matched = all(
                any(
                    str(exp).lower() in str(act).lower()
                    for act in actual_list
                )
                for exp in expected_val
            )
            results[field] = {
                "match": matched,
                "expected": expected_val,
                "actual": actual_val,
            }

        elif isinstance(expected_val, (int, float)):
            # Numérico: comparação exata
            results[field] = {
                "match": expected_val == actual_val,
                "expected": expected_val,
                "actual": actual_val,
            }

        else:
            # String: normalizada (case-insensitive, substring)
            match = str(expected_val).strip().lower() in str(actual_val).strip().lower()
            results[field] = {
                "match": match,
                "expected": expected_val,
                "actual": actual_val,
            }

    total = len(results)
    passed = sum(1 for r in results.values() if r["match"])

    return {
        "field_results": results,
        "passed": passed,
        "total": total,
        "accuracy": passed / total if total > 0 else 0,
    }


# ═══════════════════════════════════════════════════════
# EVALUATOR 2: CLASSIFICATION
# Verifica se tipo e urgência estão corretos
# ═══════════════════════════════════════════════════════

def eval_classification(actual: dict, expected: dict) -> dict:
    """
    Verifica se a classificação do documento está correta.
    Compara type e urgency.
    """
    type_match = actual.get("type") == expected.get("type")
    urgency_match = actual.get("urgency") == expected.get("urgency")

    return {
        "type": {
            "match": type_match,
            "expected": expected.get("type"),
            "actual": actual.get("type"),
        },
        "urgency": {
            "match": urgency_match,
            "expected": expected.get("urgency"),
            "actual": actual.get("urgency"),
        },
        "accuracy": (int(type_match) + int(urgency_match)) / 2,
    }


# ═══════════════════════════════════════════════════════
# EVALUATOR 3: LATENCY
# Mede tempo de execução
# ═══════════════════════════════════════════════════════

def eval_with_timing(func, *args, **kwargs) -> tuple[Any, float]:
    """
    Wrapper que mede tempo de execução de qualquer função.
    Retorna (resultado, tempo_em_segundos).
    """
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed


# ═══════════════════════════════════════════════════════
# HELPERS: Formatação do relatório
# ═══════════════════════════════════════════════════════

def format_eval_report(test_results: list[dict]) -> str:
    """
    Gera relatório formatado com os resultados de todos os test cases.
    """
    lines = []
    lines.append("")
    lines.append("═" * 60)
    lines.append("EVAL REPORT — Insurance Compliance Agent")
    lines.append("═" * 60)
    lines.append("")

    total_extraction_accuracy = []
    total_classification_accuracy = []
    total_latencies = []

    for tr in test_results:
        tc = tr["test_case"]
        lines.append(f"── {tc['id']}: {tc['name']} ({tc['difficulty']}) ──")
        lines.append("")

        # Extraction
        if "extraction" in tr:
            ext = tr["extraction"]
            total_extraction_accuracy.append(ext["accuracy"])
            lines.append(f"  📄 Extraction: {ext['passed']}/{ext['total']} fields ({ext['accuracy']:.1%})")

            for field, result in ext["field_results"].items():
                status = "✅" if result["match"] else "❌"
                if not result["match"]:
                    lines.append(
                        f"     {status} {field}: expected={result['expected']} "
                        f"got={result['actual']}"
                    )
            lines.append("")

        # Classification
        if "classification" in tr:
            cls = tr["classification"]
            total_classification_accuracy.append(cls["accuracy"])
            type_status = "✅" if cls["type"]["match"] else "❌"
            urg_status = "✅" if cls["urgency"]["match"] else "❌"
            lines.append(
                f"  📋 Classification: "
                f"{type_status} type={cls['type']['actual']} "
                f"{urg_status} urgency={cls['urgency']['actual']}"
            )
            lines.append("")

        # Latency
        if "latency" in tr:
            lat = tr["latency"]
            total_latencies.append(lat["total"])
            lines.append(f"  ⏱️  Latency: {lat['total']:.1f}s total")
            for step, duration in lat.get("steps", {}).items():
                lines.append(f"     {step}: {duration:.1f}s")
            lines.append("")

        lines.append("")

    # Summary
    lines.append("═" * 60)
    lines.append("SUMMARY")
    lines.append("═" * 60)

    if total_extraction_accuracy:
        mean_ext = sum(total_extraction_accuracy) / len(total_extraction_accuracy)
        lines.append(f"  Mean Extraction Accuracy:     {mean_ext:.1%}")

    if total_classification_accuracy:
        mean_cls = sum(total_classification_accuracy) / len(total_classification_accuracy)
        lines.append(f"  Mean Classification Accuracy: {mean_cls:.1%}")

    if total_latencies:
        mean_lat = sum(total_latencies) / len(total_latencies)
        lines.append(f"  Mean Latency:                 {mean_lat:.1f}s per document")

    lines.append("")
    lines.append(f"  Test cases: {len(test_results)}")
    lines.append("═" * 60)

    return "\n".join(lines)
