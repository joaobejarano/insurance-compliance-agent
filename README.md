# 🛡️ Insurance Compliance Agent

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.4+-purple.svg)](https://docs.langchain.com/oss/python/langgraph/)
[![GCP Cloud Run](https://img.shields.io/badge/Deploy-Cloud%20Run-4285F4.svg)](https://cloud.google.com/run)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An AI-powered document analysis system that processes insurance policy PDFs, extracts structured data, validates compliance against regulatory rules, and generates actionable reports — with human-in-the-loop approval.

Built with **LangGraph** (multi-agent orchestration), **PyMuPDF** (document processing), **OpenAI GPT-4o-mini** (extraction & reasoning), and deployed on **GCP Cloud Run**.

---

## 🎯 What it does

Upload an insurance policy PDF → the agent automatically:

1. **Classifies** the document (type + urgency)
2. **Extracts** structured data (policy number, coverage, dates, exclusions)
3. **Validates** compliance against regulatory rules
4. **Generates** a detailed compliance report
5. **Pauses** for human review and approval

If rejected, the agent re-processes with the reviewer's feedback.

---

## 🏗️ Architecture

```
                         ┌──────────────┐
                         │    START     │
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │   Classify    │ ← Structured output (type + urgency)
                         └──────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    │ urgent?               │
               ┌────▼────┐          ┌───────▼───────┐
               │  Human   │          │  Supervisor    │ ← LLM decides next worker
               │  Review   │          │  (coordinator) │
               └──────────┘          └───────┬───────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                       ┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐
                       │  Extractor  ││  Validator  ││  Reporter   │
                       │  (OCR+LLM)  ││ (compliance)││  (report)   │
                       └──────┬──────┘└──────┬──────┘└──────┬──────┘
                              │              │              │
                              └──────────────┴──────────────┘
                                             │
                                      back to supervisor
                                             │
                                      ┌──────▼───────┐
                                      │ Human Review  │ ← interrupt() + checkpointing
                                      └──────┬───────┘
                                             │
                                  ┌──────────┴──────────┐
                                  │                     │
                           ┌──────▼──────┐       ┌──────▼──────┐
                           │  Approved   │       │  Rejected   │
                           │    END      │       │  → Supervisor│
                           └─────────────┘       └─────────────┘
```

### Patterns used

| Pattern | Where | Why |
|---|---|---|
| **Routing** | `classify` node | Structured output for predictable classification |
| **Supervisor** | `supervisor` node | LLM dynamically routes between workers |
| **ReAct** | Each worker | Tool calling with reasoning loop |
| **Human-in-the-Loop** | `human_review` node | `interrupt()` + checkpointing for approval |
| **Evaluator-Optimizer** | Rejection flow | Human feedback → re-processing loop |
| **Checkpointing** | Entire graph | Fault tolerance + persistence |

### Evolution

The project evolved through two versions:

- **v1 — Fixed pipeline:** `extract → validate → report` (hardcoded order). Simple and cost-effective when processing order is deterministic.
- **v2 — Supervisor pattern:** Workers return to supervisor, which dynamically decides the next step. More flexible, supports adding new workers without rewiring.

---

## 🛠️ Tech stack

| Layer | Technology | Purpose |
|---|---|---|
| **Orchestration** | LangGraph | Multi-agent state graph with checkpointing |
| **LLM** | OpenAI GPT-4o-mini | Classification, extraction, reasoning |
| **OCR** | PyMuPDF + PyMuPDF4LLM | PDF text extraction with automatic OCR fallback |
| **Structured Output** | Pydantic + LLM | Schema-enforced data normalization |
| **Frontend** | Streamlit | Upload UI + human-in-the-loop approval |
| **API** | FastAPI | Programmatic REST endpoint |
| **Eval** | Custom pipeline | Golden dataset + code-based evaluators |
| **Observability** | LangSmith | Tracing, token usage, latency monitoring |
| **Deploy** | Docker + GCP Cloud Run | Serverless, auto-scaling, scale-to-zero |
| **Secrets** | GCP Secret Manager | Secure API key storage |

---

## 🚀 Quick start

### Prerequisites

- Python 3.12+
- OpenAI API key

### Install

```bash
git clone https://github.com/YOUR_USERNAME/insurance-compliance-agent.git
cd insurance-compliance-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run

```bash
# Option 1: Streamlit UI (recommended)
streamlit run app_streamlit.py
# Open http://localhost:8501

# Option 2: CLI
python run.py

# Option 3: API
uvicorn api:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080/docs

# Option 4: Docker
docker build -t insurance-agent .
docker run -p 8501:8501 --env-file .env insurance-agent
```

---

## 📊 Eval results

```
═══════════════════════════════════════════
EVAL REPORT — Insurance Compliance Agent
═══════════════════════════════════════════

Extraction Accuracy:     100.0% (12/12 fields)
Classification Accuracy: 100.0%
Latency:                 9.0s per document

Model: gpt-4o-mini | Test cases: 1
═══════════════════════════════════════════
```

Run evals:

```bash
python eval/run_eval.py
```

### Extraction strategy

Two-layer approach:
1. **Layer 1 (deterministic):** PyMuPDF4LLM extracts text from PDF (~0.1s, free, automatic OCR for scanned docs)
2. **Layer 2 (probabilistic):** LLM with Pydantic structured output normalizes text into schema (~2s, ~$0.01)

This isolates bugs: if data is wrong, check the Markdown output first (Layer 1), then the prompt/schema (Layer 2).

---

## 📁 Project structure

```
insurance-compliance-agent/
├── state.py              # Shared state (TypedDict with reducers)
├── tools.py              # Agent tools (OCR extraction + compliance mocks)
├── nodes.py              # Graph nodes (classify, supervisor, workers, HITL)
├── graph.py              # Graph assembly and compilation
│
├── app_streamlit.py      # Streamlit frontend with HITL
├── api.py                # FastAPI REST endpoint
├── run.py                # CLI runner
│
├── eval/
│   ├── golden_dataset.json   # Test cases with expected outputs
│   ├── evaluators.py         # Extraction + classification evaluators
│   └── run_eval.py           # Eval pipeline runner
│
├── Dockerfile            # Container for deployment
├── cloudbuild.yaml       # CI/CD pipeline
└── requirements.txt      # Dependencies
```

---

## 🔑 Key technical decisions

**Why Supervisor over fixed pipeline?** The supervisor adds one LLM call per routing decision (~$0.001), but enables: dynamic worker selection, easy addition of new workers (e.g. Drive integration), and selective re-processing after human rejection. Trade-off: latency +1s for flexibility.

**Why PyMuPDF4LLM over Google Document AI?** PyMuPDF4LLM is free, runs locally, handles 95% of documents with automatic OCR fallback. Document AI would be the upgrade for production-scale processing of complex forms and handwriting.

**Why GPT-4o-mini over GPT-4o?** Cost optimization: workers do narrow, well-prompted tasks that don't need frontier reasoning. At ~$0.03/document vs ~$0.30, it's 10x cheaper. The supervisor could be upgraded to GPT-4o for better routing if needed.

**Why Streamlit over React?** Speed-to-demo. A production frontend would use React with the FastAPI backend, but for portfolio demonstration Streamlit delivers a professional UI in 150 lines of Python.

---

## ☁️ Deploy to GCP

```bash
# One-time setup
gcloud auth login
gcloud config set project YOUR_PROJECT
gcloud services enable run.googleapis.com secretmanager.googleapis.com
echo -n "sk-your-key" | gcloud secrets create openai-api-key --data-file=-

# Deploy
gcloud run deploy insurance-agent \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --set-secrets OPENAI_API_KEY=openai-api-key:latest \
    --port 8501 \
    --memory 2Gi \
    --timeout 120
```

---

## 🗺️ Roadmap

- [ ] **v2.1:** Google Drive MCP integration (fetch docs from shared folders)
- [ ] **v2.2:** Slack notifications for critical compliance gaps
- [ ] **v2.3:** Real compliance rules engine (replace mock)
- [ ] **v2.4:** PDF report generation (replace text mock)
- [ ] **v3:** Batch processing with Orchestrator-Worker pattern (Send API)

---

## 📄 License

MIT
