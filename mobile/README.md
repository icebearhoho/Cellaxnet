# AREA 303 Mobile

Ứng dụng Expo dành cho iOS/Android. Bản hiện tại dùng `react-native-webview` để
hiển thị đúng Next.js app đang chạy trong `frontend/`; cả browser và mobile dùng
chung FastAPI, auth, workspace và feature logic.

## Chạy nhanh trên iPhone bằng Expo Go

Điều kiện:

- Laptop và iPhone cùng một Wi-Fi, không bật client/AP isolation.
- Expo Go được cài từ App Store.
- Dependencies của `backend/`, `frontend/` và `mobile/` đã được cài.
- Script tự khởi tạo PostgreSQL cluster riêng ở
  `backend/var/area303-postgres`, chỉ listen `127.0.0.1:5433`. Port `5432` trên
  máy hiện thuộc Tekno và không được dùng cho project này.

Từ repo root:

```powershell
.\scripts\start-mobile-local.ps1
```

Script tự tìm IPv4 LAN, mở ba terminal cho FastAPI, Next.js và Expo, rồi in QR
để quét bằng Expo Go. Nếu máy có nhiều network adapter, truyền IP Wi-Fi cụ thể:

```powershell
.\scripts\start-mobile-local.ps1 -HostIp 192.168.1.64
```

Sau khi Next.js sẵn sàng, URL web cũng mở được bằng Safari/Chrome:

```text
http://<LAN-IP>:3000
```

## Chạy thủ công

Terminal backend:

```powershell
cd backend
$env:DEBUG="false"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Terminal web:

```powershell
cd frontend
$env:NEXT_PUBLIC_API_URL="/api/v1"
$env:BACKEND_INTERNAL_URL="http://127.0.0.1:8010"
npm run dev:lan
```

Terminal Expo:

```powershell
cd mobile
$env:EXPO_PUBLIC_WEB_URL="http://192.168.1.64:3000"
npm run start:lan
```

## Vì sao API dùng đường dẫn tương đối?

Browser trong iPhone không thể dùng `localhost` để gọi laptop. Frontend gọi
`/api/v1`; Next.js server proxy request đó tới `BACKEND_INTERNAL_URL`. Cách này
giữ API token và request cùng origin, tránh CORS và không cần mở port FastAPI ra
mạng LAN.

## Phạm vi Expo Go

WebView hỗ trợ Expo Go nên không cần native build cho bước này. Khi thêm native
camera pipeline, push notification, deep/universal links hoặc native SDK không
có sẵn trong Expo Go, chuyển sang Expo development build; không cần bỏ Expo hay
viết lại FastAPI.
