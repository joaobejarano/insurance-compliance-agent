"""
API HTTP — Insurance Compliance Agent.
Recebe PDFs via upload, roda o agente, retorna resultados.

Rodar: uvicorn api:app --host 0.0.0.0 --port 8080
Docs:  http://localhost:8080/docs (Swagger UI)
"""

import json
import os
import tempfile
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from langgraph.types import Command

load_dotenv()

from graph import build_graph

app = FastAPI(
    title="Insurance Compliance Agent",
    description="Analyzes insurance policy documents for compliance gaps",
    version="1.0.0",
)

# Builda o grafo uma vez na inicialização
agent = build_graph()


def safe_parse(value):
    """Tenta parsear JSON string."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


@app.get("/health")
def health():
    """Health check — Cloud Run usa isso pra saber se o container tá vivo."""
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_policy(file: UploadFile = File(...)):
    """
    Recebe um PDF de apólice e retorna a análise de compliance.

    O fluxo:
    1. Salva o PDF temporariamente
    2. Roda o agente (classify → extract → validate → report)
    3. Auto-aprova o human review (em produção, seria assíncrono)
    4. Retorna o resultado completo
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        config = {"configurable": {"thread_id": f"api-{file.filename}-{int(time.time())}"}}

        start = time.time()

        # Roda até o interrupt
        agent.invoke(
            {"messages": [("user", f"Analyze the insurance policy at: {tmp_path}")]},
            config,
        )

        state = agent.get_state(config)

        # Auto-aprova
        agent.invoke(Command(resume={"approved": True}), config)

        final_state = agent.get_state(config)
        elapsed = time.time() - start

        response = {
            "filename": file.filename,
            "latency_seconds": round(elapsed, 2),
            "classification": final_state.values.get("classification"),
            "extracted_data": safe_parse(final_state.values.get("extracted_data")),
            "compliance_result": safe_parse(final_state.values.get("compliance_result")),
            "report": final_state.values.get("report"),
            "approved": final_state.values.get("approved"),
        }

        return JSONResponse(content=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        os.unlink(tmp_path)
