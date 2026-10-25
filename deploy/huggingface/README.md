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

The Space runs the officer console and the Open Banking gateway in one container: nginx on port
7860 sends the TBC sandbox's OAuth callback (`/oauth/callback`) and the gateway's Swagger
(`/api/docs`) to the gateway and everything else to the console.

The AI analysis of photos uses the Space secrets `NVIDIA_API_KEY` (or `ANTHROPIC_API_KEY` with
`COLLATERAL_VISION_PROVIDER=anthropic`) and the variable `COLLATERAL_VISION_ENABLED=true`; keys are
never stored in the repository.
