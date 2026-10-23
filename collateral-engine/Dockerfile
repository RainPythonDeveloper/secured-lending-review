# One image, two entry points: the API (default) and the officer console.
# Build from the repository root, so the NBG rules shared with the income engine are copied in:
#   docker build -f collateral-engine/Dockerfile .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /collateral-engine
COPY collateral-engine/pyproject.toml collateral-engine/README.md ./
COPY collateral-engine/src ./src
RUN pip install --no-cache-dir -e ".[dev]"
COPY income-engine/config/nbg_rules.yaml /income-engine/config/nbg_rules.yaml
COPY collateral-engine/ ./
# Synthetic sales are generated in the image, so every replica values against the same market.
RUN python -m collateral_engine.synth && python -m pytest -q
RUN useradd -m collateral && chown -R collateral /collateral-engine
USER collateral
EXPOSE 8100 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/health')" || exit 1
CMD ["uvicorn", "collateral_engine.api:create_app_from_environment", "--factory", "--host", "0.0.0.0", "--port", "8100"]
