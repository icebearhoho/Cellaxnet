# Seller Autopilot

Seller Autopilot biến dữ liệu shop thành một vòng lặp có kiểm soát:

1. Backend phát hiện cơ hội từ cùng snapshot sản phẩm, review và khách hàng.
2. Backend tính evidence và impact định lượng; LLM không được tự tạo số.
3. Ollama Cloud `gpt-oss:120b` viết explanation tiếng Việt, tối đa 240 ký tự.
4. Seller mô phỏng một phương án trước khi quyết định.
5. Chỉ `owner` hoặc `manager` được duyệt/từ chối; mọi quyết định được audit.
6. Bản MVP tạo workflow draft, chưa tự ý sửa giá, campaign hay gửi voucher lên sàn.

## Cấu hình model thật

Trong `backend/.env`:

```dotenv
DEMO_MODE=false
OLLAMA_API_KEY=<key tạo tại ollama.com/settings/keys>
AUTOPILOT_OLLAMA_URL=https://ollama.com
AUTOPILOT_OLLAMA_MODEL=gpt-oss:120b
AUTOPILOT_LLM_TIMEOUT_SECONDS=60
```

`OLLAMA_API_KEY` là key riêng được tạo trên Ollama và không dùng chung với
`OPENAI_API_KEY`. API gọi trực tiếp `POST /api/chat` với Bearer token. Khi thiếu
key, timeout hoặc Ollama trả lỗi,
hệ thống hiển thị explanation định lượng dự phòng và ghi rõ
`deterministic_fallback`; không giả vờ rằng LLM đã chạy.

## API

- `POST /api/v1/autopilot/refresh`: owner/manager quét và gọi model.
- `GET /api/v1/autopilot/opportunities`: thành viên xem cơ hội.
- `POST /api/v1/autopilot/opportunities/{id}/simulate`: mô phỏng phương án.
- `POST /api/v1/autopilot/opportunities/{id}/decision`: owner/manager duyệt hoặc từ chối.
- `GET /api/v1/autopilot/audit`: xem lịch sử thao tác.

Tất cả endpoint bắt buộc Bearer JWT và `X-Workspace-ID`; truy vấn luôn bị giới hạn
theo workspace để tránh đọc hoặc sửa dữ liệu của shop khác.

## Chạy local

```powershell
.\scripts\start-area303-db.ps1
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
```

Mở seller portal, chọn workspace rồi chọn menu **Seller Autopilot**. Nhấn **Quét
cơ hội**; badge `Ollama Cloud · gpt-oss:120b` xác nhận explanation đến từ model.
