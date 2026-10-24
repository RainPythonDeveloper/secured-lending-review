# One image for the whole platform, two entry points: the API (default) and the officer console.
# Build from the repository root, so the income engine is copied in next to the collateral engine:
#   docker build -f collateral-engine/Dockerfile .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# LightGBM in the income engine needs the OpenMP runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY income-engine/ /income-engine/
RUN pip install --no-cache-dir -e /income-engine
WORKDIR /collateral-engine
COPY collateral-engine/pyproject.toml collateral-engine/README.md ./
COPY collateral-engine/src ./src
RUN pip install --no-cache-dir -e ".[dev]"
COPY collateral-engine/ ./
# Synthetic data and the income models are built in the image, so every replica serves the same
# markets and the same versioned model; the image is not built if a test fails.
RUN python -m collateral_engine.synth && python -m collateral_engine.vehicles.synth
RUN cd /income-engine && python -m ite.synth --out data && python -m ite.train && python -m ite.report
RUN python -m pytest -q && cd /income-engine && python -m pytest -q
RUN useradd -m platform && chown -R platform /collateral-engine /income-engine
USER platform
EXPOSE 8100 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/health')" || exit 1
CMD ["uvicorn", "collateral_engine.api:create_app_from_environment", "--factory", "--host", "0.0.0.0", "--port", "8100"]
