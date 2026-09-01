# AREA 303 — AI/ML E-Commerce Platform

Data + AI/ML **monorepo** for **ARRA 303 ("The Buffalo Playground")** — clothing & accessories + cosmetics/personal care on Vietnamese e-commerce platforms (Shopee, Tiki, Lazada).

This repo is organized as a small **monorepo**:

- `backend/` — FastAPI API service (Python 3.11)
- `frontend/` — Next.js web app (App Router)
- `mobile/` — Expo Go iOS/Android shell dùng chung web và FastAPI
- `dataset/` — raw + processed datasets for the 17 candidate product ideas
- `common/` + feature folders (`review_sentiment/`, `fake_review/`, `dynamic_pricing/`, `personal_shopper/`, `customer_churn/`) — the LLM modeling layer for ideas #01–#05
- `docker-compose.yml` — local Postgres + Redis + backend
- `.github/workflows/` — CI pipelines

The `dataset/` folder already shipped; see `dataset/by_idea/idea_*` for the 17 ideas' cleaned datasets.

## Modeling — features #01–#05

An LLM-first modeling layer (no model training) for the first five ideas: review
sentiment, fake-review detection, dynamic pricing, personal shopper, customer churn.
Inference runs on OpenAI `gpt-4o-mini` by default or a local Ollama fallback; labelled
data is used for evaluation only, and all datasets are free (no Kaggle required).
See **[`MODELING.md`](MODELING.md)**. Quick look: `python demo.py`.

## Quick start (backend)
An AI/ML e-commerce application built for **AREA 303 ("The Buffalo Playground")** —
the AI/ML + Prototype track, e-commerce focus. The platform bundles **17 AI-powered
features** across NLP, time series, computer vision, generative AI, and behavioral AI,
targeting **clothing & accessories and cosmetics/personal care** on Vietnamese
marketplaces (Shopee, Tiki, Lazada).

The goal: give sellers and shoppers a smarter storefront — better search, pricing,
recommendations, review trust, demand planning, and customer insight — grounded in
real Vietnamese e-commerce data.

## The 17 ideas

| Category | Ideas |
|---|---|
| **NLP** | #01 Review Sentiment · #05 Fake Review Detection · #08 Social Trend Analyzer · #09 Content Generator |
| **Time Series** | #02 Dynamic Pricing · #06 Demand Forecasting · #15 Price Sensitivity · #16 Supply-Chain Disruption |
| **Computer Vision** | #07 Visual Search · #12 Virtual Try-On |
| **Generative AI** | #03 Personal Shopper · #11 Recommendation System · #17 Seller Intelligence |
| **Behavioral AI** | #04 Churn Prediction · #10 Return Prediction · #13 Customer Segmentation |

Each idea is powered by 1–2 curated datasets and a recommended model. Full
dataset-to-idea mapping and model choices live in `report/model suggestions.xlsx` and
`report/AREA303_Dataset_Model_Plan.docx` — kept locally by the data-processing role,
not part of this repo.

## What's in this repository

This repo is the **data foundation** for the platform — the sourcing, cleaning, and
packaging of every dataset the 17 features build on. It is organized so any teammate
(or their AI assistant) can pick up one idea and start modeling immediately.

- **Cleaned, analysis-ready data** in three pipelines — reviews/text, transactions/behavior, catalog/images.
- **Per-idea folders** (`dataset/by_idea/idea_XX_*/`) that bundle each idea's datasets with:
  - **`AI_BRIEF.md`** — a self-contained briefing to paste into an AI assistant (goal, recommended model, decoded data, pitfalls, first steps).
  - **`DATA_DICTIONARY.md`** — every column explained, coded values decoded.
- **`DATA_REPORT.md`** — one-page overview of all datasets.
- Reproducible **download → clean → validate → package** scripts.

> Full pipeline documentation and reproduction steps: **[`dataset/README.md`](dataset/README.md)**.

## Modeling (features #01–#05)

The LLM-powered modeling layer for ideas #01–#05 (review sentiment, fake-review
detection, dynamic pricing, personal shopper, customer churn) lives in top-level
feature folders and is documented in **[`MODELING.md`](MODELING.md)**. It is
LLM-first (no training): OpenAI `gpt-4o-mini` by default, or local Ollama. Run
`python demo.py` to see all five working; `python code/build_dashboard.py` builds a
results dashboard.

## Quick start

```bash
cp backend/.env.example backend/.env
docker compose up -d postgres redis
cd backend
python -m venv .venv
. .venv/Scripts/Activate.ps1   # PowerShell
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: <http://localhost:8000/docs>

## Chạy web và app iOS local

Sau khi cài dependencies trong `backend/`, `frontend/` và `mobile/`, cho laptop
và iPhone vào cùng Wi-Fi rồi chạy:

```powershell
.\scripts\start-mobile-local.ps1
```

Mở web bằng URL LAN mà script in ra, hoặc quét QR bằng Expo Go để mở app. Xem
chi tiết và troubleshooting trong [`mobile/README.md`](mobile/README.md).

## API response standard

All JSON responses from the backend follow this envelope:

```json
{
  "success": true,
  "data": { "...": "..." },
  "meta": { "request_id": "...", "page": 1, "page_size": 20, "total": 0 },
  "error": null
}
```

On failure:

```json
{
  "success": false,
  "data": null,
  "meta": { "request_id": "..." },
  "error": { "code": "RESOURCE_NOT_FOUND", "message": "...", "details": {} }
}
```

See `backend/app/core/responses.py` for the implementation and `backend/app/core/exceptions.py` for the error codes.

## Contributing

Branch naming: `feat/<scope>-<short-desc>`, `fix/<scope>-<short-desc>`, `chore/<scope>`. Open PRs against `main`. CI must pass (lint + tests).
The cleaned, ready-to-use data for each idea is in `dataset/by_idea/idea_XX_*/` — see
[`dataset/README.md`](dataset/README.md) for how to load it. The download → clean →
validate → package pipeline (`code/`) is maintained locally by the data-processing role
and isn't distributed in this repo; ask them if you need to reproduce or extend it.

The raw + processed data (~11 GB) is **gitignored** and rebuilt from these scripts —
the repo itself stays lightweight.

## Tech stack

Python · pandas · PyArrow (Parquet) · HuggingFace Hub · Kaggle API.
Modeling (per idea, planned): PhoBERT/ViSoBERT, XGBoost, CLIP + FAISS, Prophet,
Gemini via LangChain, and more — see the plan documents.

## Status

✅ Data foundation complete — all datasets sourced, cleaned, validated, documented,
and packaged per idea. Modeling of the 17 features builds on top of `dataset/by_idea/`.

## Team

Built by a 5-person team for AREA 303. This repository is the **data-processing
workstream**.

## Contributing

See [`report/CONTRIBUTING.md`](report/CONTRIBUTING.md) for branch naming, commit style, and the PR process.
