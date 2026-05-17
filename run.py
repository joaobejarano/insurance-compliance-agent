"""
Script pra executar o Insurance Compliance Agent.
Roda o fluxo completo: classify → extract → validate → report → human review.
"""

import json
from pathlib import Path
from dotenv import load_dotenv
from langgraph.types import Command

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

from graph import build_graph

# Carrega a OPENAI_API_KEY do .env
load_dotenv()


def main():
    # ── 1. Constrói o grafo ──
    print("🔨 Building graph...")
    app = build_graph()
    
    # ── 2. Configura o thread (necessário pro checkpointer) ──
    # Cada thread_id é uma "sessão" independente
    config = {"configurable": {"thread_id": "policy-review-001"}}
    
    # ── 3. Documento de teste ──
    # Agora aponta pro PDF real em vez de texto hardcoded
    test_document = "Please analyze the insurance policy document at: test_policy.pdf"
    
    # ── 4. Primeira execução: roda até o interrupt ──
    print("\n" + "=" * 60)
    print("🚀 Running agent...")
    print("=" * 60)
    
    result = app.invoke(
        {"messages": [("user", test_document)]},
        config,
    )
    
    # ── 5. Mostra o que o agente fez antes de pausar ──
    print("\n" + "=" * 60)
    print("⏸️  Agent paused at HUMAN REVIEW")
    print("=" * 60)
    
    # Pega o estado atual do grafo (o quadro branco)
    state = app.get_state(config)
    
    # Mostra classificação
    classification = state.values.get("classification")
    if classification:
        print(f"\n📋 Classification:")
        print(f"   Type: {classification.get('type')}")
        print(f"   Urgency: {classification.get('urgency')}")
        print(f"   Summary: {classification.get('summary')}")
    
    # Mostra dados extraídos
    extracted = state.values.get("extracted_data")
    if extracted:
        print(f"\n📄 Extracted Data:")
        print(f"   {extracted[:200]}...")  # primeiros 200 chars
    
    # Mostra resultado de compliance
    compliance = state.values.get("compliance_result")
    if compliance:
        print(f"\n✅❌ Compliance Result:")
        print(f"   {compliance[:200]}...")
    
    # Mostra relatório
    report = state.values.get("report")
    if report:
        print(f"\n📊 Report:")
        print(f"   {report[:300]}...")

    # ── Mostra o state completo (sem truncar) ──
    print("\n" + "=" * 60)
    print("📋 FULL STATE DUMP")
    print("=" * 60)
    
    for key in ["classification", "extracted_data", "compliance_result", "report"]:
        value = state.values.get(key)
        if value:
            print(f"\n{'─' * 40}")
            print(f"🔑 {key}:")
            print(f"{'─' * 40}")
            print(value)
    
    # ── 6. Simula decisão humana ──
    print("\n" + "=" * 60)
    print("🙋 Simulating human approval...")
    print("=" * 60)
    
    # Retoma o grafo com a decisão do humano
    final_result = app.invoke(
        Command(resume={"approved": True}),
        config,
    )
    
    # ── 7. Resultado final ──
    print("\n" + "=" * 60)
    print("✅ Agent completed!")
    print("=" * 60)
    
    final_state = app.get_state(config)
    print(f"\n   Approved: {final_state.values.get('approved')}")
    print(f"   Total messages: {len(final_state.values.get('messages', []))}")
    
    print("\n🎉 Done! Full flow executed successfully.")


if __name__ == "__main__":
    main()