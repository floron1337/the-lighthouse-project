FROM python:3.12-slim AS base
WORKDIR /app

# Install dependencies via pip (requirements.txt is kept in sync with pyproject.toml)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# LLM_MOCK=true by default so the image works without Ollama.
# Override at runtime: docker run -e LLM_MOCK=false -e OLLAMA_URL=http://host:11434 ...
ENV LLM_MOCK=true \
    OLLAMA_URL=http://localhost:11434 \
    OLLAMA_MODEL=llama3.2

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
