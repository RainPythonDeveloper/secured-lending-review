---
title: Secured Lending Review
emoji: 🏦
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Collateral second opinion and NBG loan checks
---

# Secured Lending Review

The officer console of the platform built for the NBG AI & Open Banking Hackathon 2026 (Track 1
AI in Finance, AI1 Credit Risk & Lending). Source, architecture and guardrails:
https://github.com/Weegoos/gita-project

All data is synthetic. No login is needed.

This Space runs the console alone. The Open Banking gateway is not deployed here, so **Use the
bank's records** loads a customer instead of the TBC sandbox consent; the full platform, gateway
included, runs with `docker compose up --build` from the repository.
