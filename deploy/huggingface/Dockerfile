# Hugging Face Space: the officer console of the platform, built from the GitHub repository.
# The Space exposes one port, so it runs the console alone; without the Open Banking gateway the
# loan application falls back to the bank's records, as it does when the sandbox is down.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG REPOSITORY=https://github.com/Weegoos/gita-project.git
ARG BRANCH=main
# LightGBM in the income engine needs the OpenMP runtime.
RUN apt-get update && apt-get install -y --no-install-recommends git libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch "${BRANCH}" "${REPOSITORY}" /platform
RUN pip install --no-cache-dir -e /platform/income-engine -e /platform/collateral-engine
# The same synthetic markets and income models as the Docker Compose image; CI runs the tests.
WORKDIR /platform/collateral-engine
RUN python -m collateral_engine.synth && python -m collateral_engine.vehicles.synth
RUN cd /platform/income-engine && python -m ite.synth --out data && python -m ite.train \
    && python -m ite.report
# Hugging Face runs Spaces as the user with uid 1000.
RUN useradd -m -u 1000 user && chown -R user /platform
USER user
EXPOSE 7860
# The Space serves the app inside an iframe, where Streamlit's XSRF cookie breaks photo uploads.
CMD ["streamlit", "run", "app/platform_app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.enableXsrfProtection=false"]
