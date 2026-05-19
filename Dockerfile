# ═══════════════════════════════════════════════════════
# Dockerfile — Insurance Compliance Agent
# 
# Roda o Streamlit (frontend) na porta 8501
# e o FastAPI (API) na porta 8080
# 
# Build:  docker build -t insurance-agent .
# Run:    docker run -p 8501:8501 -e OPENAI_API_KEY=sk-... insurance-agent
# ═══════════════════════════════════════════════════════

FROM python:3.12-slim

# Instala Tesseract pra OCR de docs escaneados
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copia e instala dependências primeiro (melhor cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do projeto
COPY . .

# Porta do Streamlit
EXPOSE 8501

# Roda o Streamlit
CMD ["streamlit", "run", "app_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
