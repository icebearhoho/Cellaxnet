# Contributing

Guidelines for the AREA 303 team (5 members) working in this repo.

## Branches

- `main` is always in a working state — no direct pushes.
- Branch off `main` per task: `<type>/<short-description>`
  - `data/add-tiki-pipeline`
  - `fix/sephora-null-handling`
  - `docs/update-data-report`
  - Types: `data`, `feat`, `fix`, `docs`, `chore`

## Commits

Keep commits scoped and use a short imperative summary:

```
clean_pipeline2: dedupe rees46 churn rows
```

## Pull requests

1. Open a PR from your branch into `main` using the PR template.
2. Fill in what changed and how it was tested/verified (e.g. re-ran `validate_datasets.py`).
3. Request review from at least one teammate before merging.
4. Squash-merge once approved; delete the branch after merge.

## Data changes

- Never commit files under `dataset/` except the small doc files (`README.md`, `_SOURCE.txt`) that already ship with each source — see `.gitignore`.
- If a cleaning script's output schema changes, update `DATA_REPORT.md` in the same PR.
- Run `validate_datasets.py` and `check_data_quality.py` before opening a PR that touches a `clean_pipeline*.py` script.

## Reporting issues

Use the issue templates (bug report / feature or task request) so the rest of the team has enough context to pick it up.

## Seller feature integration

Seller-owned data must follow the workspace tenant contract in
[`SELLER_WORKSPACE_INTEGRATION.md`](SELLER_WORKSPACE_INTEGRATION.md). In
particular, use the verified `X-Workspace-ID` dependency and never trust a
workspace id from the request body by itself.

## End-to-end project workflow

Quy trình chung, BPMN, Git workflow và stuck-resolution playbook nằm trong
[`PROJECT_PROCESS_BPMN.md`](PROJECT_PROCESS_BPMN.md). Mỗi task nên đi qua
Definition of Ready, contract review, implementation, verification và Definition
of Done trong tài liệu đó.

## Feature logic and benchmark

Kết quả kiểm thử logic từng feature, đối chiếu flow với Shopify/Amazon/Klaviyo/
Google/AWS và backlog theo mức độ ưu tiên nằm trong
[`FEATURE_LOGIC_BENCHMARK.md`](FEATURE_LOGIC_BENCHMARK.md).

## Coherent demo shop

Nguồn dữ liệu mẫu thống nhất, quy mô snapshot, entity links và mapping từ dữ
liệu sang từng feature nằm trong
[`COHERENT_DEMO_SHOP.md`](COHERENT_DEMO_SHOP.md). Khi thêm dữ liệu mẫu mới,
không tạo mock riêng trong component/service; hãy mở rộng `commerce_store` và
thêm invariant test để các dashboard và AI feature không lệch nhau.

## Web và mobile local

Expo shell nằm trong `mobile/` và dùng chung Next.js/FastAPI với web. Chạy
`.\scripts\start-mobile-local.ps1` từ repo root để mở backend, frontend LAN và
Expo Go. Client frontend phải gọi API tương đối qua `/api/v1`; không hardcode
`localhost` hoặc IP laptop vào component vì trên điện thoại `localhost` là chính
thiết bị đó.

## Seller Autopilot

Luồng phát hiện cơ hội, mô phỏng, phê duyệt, audit và cấu hình Ollama Cloud nằm
trong [`SELLER_AUTOPILOT.md`](SELLER_AUTOPILOT.md). Model chỉ được viết giải thích
từ evidence; mọi số liệu tác động phải do backend tính và action không được tự
động chạy khi chưa có người có quyền duyệt.
