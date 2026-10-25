# Hugging Face Space: the officer console and the Open Banking gateway in one container, built
# from the GitHub repository. The Space exposes one port, so nginx on 7860 sends the OAuth
# callback and the gateway's Swagger to the gateway and everything else to the console.
ARG REPOSITORY=https://github.com/Weegoos/gita-project.git
ARG BRANCH=main

FROM node:24-slim AS source
ARG REPOSITORY
ARG BRANCH
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Changes whenever main moves, so a rebuild never reuses an old clone.
ADD https://api.github.com/repos/Weegoos/gita-project/git/refs/heads/${BRANCH} /tmp/branch-ref.json
RUN git clone --depth 1 --branch "${BRANCH}" "${REPOSITORY}" /platform
WORKDIR /platform/server
RUN npm ci && npm run build && npm prune --omit=dev

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# LightGBM in the income engine needs the OpenMP runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 nginx \
    && rm -rf /var/lib/apt/lists/*
COPY --from=source /usr/local/bin/node /usr/local/bin/node
COPY --from=source /platform /platform
RUN pip install --no-cache-dir -e /platform/income-engine -e /platform/collateral-engine
# The same synthetic markets and income models as the Docker Compose image; CI runs the tests.
WORKDIR /platform/collateral-engine
RUN python -m collateral_engine.synth && python -m collateral_engine.vehicles.synth
RUN cd /platform/income-engine && python -m ite.synth --out data && python -m ite.train \
    && python -m ite.report
COPY nginx.conf /etc/nginx/space.conf
COPY start.sh /usr/local/bin/start-space
# Hugging Face runs Spaces as the user with uid 1000.
RUN useradd -m -u 1000 user && chown -R user /platform && chmod +x /usr/local/bin/start-space
USER user

# The gateway: the same settings as docker-compose.yml, with the public callback of this Space.
ENV PORT=3000 \
    NODE_ENV=production \
    TBC_API_BASE_URL=https://tbc-bank-mock-open-banking-api.vercel.app/0.8 \
    TBC_OAUTH_AUTHORIZE_URL=https://tbc-bank-mock-open-banking-api.vercel.app/psd2/openbanking/oauth/authorize \
    TBC_OAUTH_TOKEN_URL=https://tbc-bank-mock-open-banking-api.vercel.app/openbanking/oauth/token \
    TBC_OAUTH_CLIENT_ID=virtual-field-visit-gateway \
    TBC_OAUTH_REDIRECT_URI=https://x7x-secured-lending-review.hf.space/oauth/callback \
    TBC_OAUTH_UI_LOCALE=en \
    TBC_HTTP_TIMEOUT_MS=8000 \
    TBC_RETRY_MAX_ATTEMPTS=3 \
    TBC_RETRY_BASE_DELAY_MS=250 \
    TBC_RETRY_MAX_DELAY_MS=2000 \
    OAUTH_STATE_TTL_MS=600000 \
    OAUTH_TOKEN_REFRESH_MARGIN_MS=60000 \
    DATASET_XLSX_PATH=/platform/data/open-banking-synthetic-100-customers.xlsx \
    OPEN_BANKING_GATEWAY_URL=http://127.0.0.1:3000
EXPOSE 7860
CMD ["start-space"]
