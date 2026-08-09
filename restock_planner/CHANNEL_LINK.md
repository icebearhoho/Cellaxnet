# Kết nối tài khoản bán hàng — Shopee / Lazada / TikTok Shop

Nối qua **KiotViet** — nền tảng bán hàng đa kênh của Việt Nam đã được cả ba sàn
cấp quyền sẵn. **Một liên kết mang về đơn của cả ba sàn**, mỗi đơn có ghi rõ đến
từ kênh nào.

Màn hình: `/seller/restock-planner` → khối **"Kết nối tài khoản bán hàng"**.

---

## 1. Ý nghĩa — vì sao feature này quan trọng

### Với Restock Planner

Restock Planner cần biết **mỗi kênh bán được bao nhiêu** thì mới chia vốn nhập
hàng đúng. Không có dữ liệu này thì seller phải **tự khai** tình hình từng kênh
(bán chạy / bán ít / theo mùa / không bán được) — tức là một giả định.

Tầng kết nối biến giả định đó thành **số đo**: nối tài khoản → đọc đơn hàng thật
→ tự tính hệ số cầu từng kênh. Seller không phải khai gì nữa.

### Với cả hệ thống

Toàn bộ platform hiện đọc từ một catalog dùng chung
(`backend/app/services/commerce_store.py`). Khi có dữ liệu bán hàng thật chảy
vào, **không chỉ Restock Planner hưởng lợi** — Review Intelligence, Dynamic
Pricing, Customer Risk, Demand Forecast đều đang lấy từ cùng nguồn đó.

Đây là **cửa ngõ đưa dữ liệu thật vào toàn hệ thống**, không phải một tính năng
đứng riêng.

---

## 2. Vì sao đi qua KiotViet thay vì nối thẳng từng sàn

### Rào cản của cách nối thẳng

Muốn đọc đơn hàng của một shop trên Shopee/Lazada/TikTok, phải có **một ứng dụng
đã được sàn đó duyệt**. Mỗi sàn một cửa ải riêng:

| Sàn | Điều kiện lấy khoá ứng dụng |
|---|---|
| Shopee | Duyệt hồ sơ danh tính trước khi cho tạo app — CCCD hoặc giấy phép kinh doanh |
| Lazada | Nộp giấy tờ, đội vận hành xét duyệt |
| TikTok Shop | Bắt buộc đã có TikTok Shop kích hoạt mới đăng ký được |

Ba sàn là **ba lần xin duyệt**, mỗi lần đều vướng giấy tờ và thời gian chờ.

### Vì sao KiotViet giải được

KiotViet là phần mềm quản lý bán hàng mà rất nhiều seller Việt đang dùng thật.
Họ đã qua cả ba cửa ải đó từ lâu, đồng bộ đơn từ Shopee/Lazada/TikTok Shop, và
mở **Public API** cho lập trình viên.

| | Nối thẳng 3 sàn | Qua KiotViet |
|---|---|---|
| Số lần xin duyệt ứng dụng | 3 | **0** |
| Số tích hợp phải viết & bảo trì | 3 | **1** |
| Sàn phủ được | 3 | **3, cùng lúc** |
| Cần redirect URL / HTTPS công khai | Có | **Không** |

**Điểm ăn tiền lớn nhất:** KiotViet xác thực bằng **OAuth2 client credentials** —
gọi thẳng server-to-server. Không có bước chuyển hướng người dùng, nên **không
cần địa chỉ HTTPS công khai, không cần đường hầm (ngrok) khi chạy máy cá nhân,
và không phải đăng ký ứng dụng ở cổng developer nào**. Chủ shop chỉ copy hai
chuỗi trong phần cài đặt cửa hàng của chính họ.

**Điểm ăn tiền thứ hai:** mỗi đơn có `saleChannelId`, nên một lần đồng bộ trả về
đơn **đã phân loại sẵn theo kênh** — đúng thứ Restock Planner cần.

Mã kênh **khác nhau ở mỗi cửa hàng**, nên connector không gán cứng mà đọc
`/salechannel` rồi khớp theo **tên** (chứa "shopee" / "lazada" / "tiktok").
Kênh nào không phải ba sàn — bán trực tiếp, Facebook, website — gộp vào
**Cửa hàng riêng**, vì xét theo bài toán chia hàng chúng dùng chung một gian
hàng và một mức phí.

---

## 3. Các bước kết nối — giải thích chi tiết

### Ba bên tham gia

| Bên | Vai trò |
|---|---|
| **Chủ shop** | Sở hữu dữ liệu đơn hàng, và sở hữu khoá API của cửa hàng mình |
| **App của nhóm** | Muốn đọc dữ liệu đó |
| **KiotViet** | Nơi giữ dữ liệu, và đã nối sẵn với 3 sàn |

### Toàn cảnh luồng

```
   Seller                  App (backend)                 KiotViet
     │                          │                           │
 1.  ├── dán khoá API vào .env  │                           │
     │                          │                           │
 2.  ├── bấm "Kết nối" ────────►├── xin token ─────────────►│
     │                          │◄── access_token (1 giờ) ──┤
     │                          │                           │
 3.  │                    ghi nhận "Đã kết nối"             │
     │                          │                           │
 4.  ├── bấm "Lấy đơn hàng" ───►├── GET /salechannel ──────►│
     │                          │◄── danh sách kênh bán ────┤
     │                          ├── GET /invoices ─────────►│
     │                          ├── GET /orders ───────────►│
     │                          │◄── đơn + saleChannelId ───┤
     │                          │                           │
 5.  │        đếm đơn theo từng kênh → Restock Planner      │
```

**Không có bước nào chuyển hướng trình duyệt.** Đây là khác biệt cốt lõi so với
OAuth ba bước — và là lý do bỏ được toàn bộ yêu cầu về HTTPS/ngrok/redirect URL.

### Chi tiết từng bước

**Bước 1 — Lấy khoá API**

Chủ shop vào **Thiết lập cửa hàng → Thiết lập kết nối API** trong KiotViet, tạo
ứng dụng, nhận về:

```
Client ID
Client Secret
Retailer (tên cửa hàng)
```

Không cần đăng ký cổng developer, không chờ duyệt.

**Bước 2 — Bấm "Kết nối"**

App gọi `POST /api/v1/channel-link/connect`. Backend gửi thẳng tới KiotViet:

```
POST https://id.kiotviet.vn/connect/token
Content-Type: application/x-www-form-urlencoded

scopes=PublicApi&grant_type=client_credentials&client_id=...&client_secret=...
```

Nhận về `access_token` sống khoảng **1 giờ**.

Xác thực **ngay lúc bấm Kết nối** là có chủ ý: khoá sai sẽ báo lỗi tại chỗ, thay
vì im lặng rồi lòi ra ở lần đồng bộ sau dưới dạng "cửa hàng không có đơn nào".

**Bước 3 — Ghi nhận kết nối**

Chỉ lưu tên cửa hàng và trạng thái. **Token cố tình không lưu** — nó sống một
giờ và mỗi lần đồng bộ đều xin mới, nên không có gì để hết hạn.

**Bước 4 — Lấy đơn hàng**

```
GET https://public.kiotapi.com/salechannel
GET https://public.kiotapi.com/invoices?fromPurchaseDate=...&pageSize=100&currentItem=...
GET https://public.kiotapi.com/orders?fromPurchaseDate=...&pageSize=100&currentItem=...

Headers: Authorization: Bearer <token>
         Retailer: <tên cửa hàng>
```

⚠️ **Thiếu header `Retailer` là bị từ chối dù token đúng** — đây là chỗ dễ sai.

Gọi `/salechannel` trước để biết cửa hàng này đặt mã nào cho Shopee/Lazada/TikTok,
rồi mới đếm đơn theo đúng mã đó.

⚠️ **Phải đọc cả `/invoices` lẫn `/orders`.** KiotViet tách một lần bán thành hai
chỗ, nằm ở đâu tuỳ đường nó đi vào:

- **Hoá đơn** (`/invoices`) = bán xong. Bán lẻ tại quầy vào thẳng đây, không qua
  đơn hàng. Kiểm chứng trên cửa hàng thật: `/orders` trả **0** trong khi
  `/invoices` trả **46** đúng bằng doanh thu dashboard báo — chỉ đọc `/orders`
  sẽ hiển thị nhầm là cửa hàng không bán được gì.
- **Đơn hàng** (`/orders`) = đặt trước, chưa giao xong. **Đơn đồng bộ từ
  Shopee/Lazada/TikTok về nằm ở đây trước**, chỉ thành hoá đơn sau khi giao —
  chỉ đọc `/invoices` sẽ bỏ sót toàn bộ đơn đang trên đường, đúng phần tín hiệu
  nhu cầu mà kế hoạch nhập hàng cần nhất.

Khử trùng theo `orderCode`: hoá đơn xuất ra từ một đơn hàng có mang mã đơn gốc,
nên một lần bán không bị đếm hai lần.

Duyệt hết các trang; dừng khi một trang trả về ít hơn `pageSize` hoặc đã lấy đủ
số `total` mà KiotViet báo.

Chỉ lưu **số liệu tổng hợp** (số đơn, doanh thu theo kênh) — **không lưu thông
tin khách hàng**.

**Bước 5 — Đưa vào kế hoạch nhập hàng**

Từ số đơn/ngày mỗi kênh, tính hệ số cầu bằng cách so với mức trung bình:

```
Ví dụ 60 ngày: Shopee 340 đơn, Lazada 45, TikTok 120, Cửa hàng riêng 20

Shopee         : 340/60 = 5.67 đơn/ngày  ÷ 2.19 (TB) = hệ số 2.591
TikTok Shop    : 120/60 = 2.00 đơn/ngày  ÷ 2.19      = hệ số 0.914
Lazada         :  45/60 = 0.75 đơn/ngày  ÷ 2.19      = hệ số 0.343
Cửa hàng riêng :  20/60 = 0.33 đơn/ngày  ÷ 2.19      = hệ số 0.152
```

Hệ số này thay thẳng phần seller tự khai. Thẻ kênh đổi nhãn sang
**"Từ đơn hàng thật"**.

---

## 4. Đã xây dựng những gì

### Backend

| File | Vai trò |
|---|---|
| `app/services/channel_connectors.py` | Connector KiotViet: lấy token, đọc kênh bán, kéo đơn, phân loại theo kênh |
| `app/services/channel_link.py` | Vòng đời kết nối, lưu/xoá liên kết, tính số đơn/ngày |
| `app/models/channel_link.py` | Bảng `channel_connections` |
| `alembic/versions/0004_channel_connections.py` | Migration |
| `app/schemas/channel_link.py` | Kiểu dữ liệu API |
| `app/api/v1/endpoints/channel_link.py` | 4 endpoint |

**API:**

```
GET  /api/v1/channel-link/            trạng thái + số đơn theo từng kênh
POST /api/v1/channel-link/connect     kiểm chứng khoá API, ghi nhận liên kết
POST /api/v1/channel-link/sync        kéo đơn hàng về
POST /api/v1/channel-link/disconnect  ngắt + xoá liên kết
```

### Frontend

`components/features/channel-link-panel.tsx` — một thẻ kết nối với nút
**Kết nối** / **Lấy đơn hàng** / **Ngắt**, kèm bảng số đơn từng kênh sau khi
đồng bộ.

### Bảo mật

| Biện pháp | Chi tiết |
|---|---|
| Không có bề mặt CSRF | Không có bước chuyển hướng nào để tấn công |
| Không đụng mật khẩu | Chỉ dùng khoá API do chính chủ shop cấp, thu hồi được bất cứ lúc nào từ KiotViet |
| Token không lưu | Xin mới mỗi lần đồng bộ, không có token cũ nằm trong DB |
| Khoá không lộ | API chỉ trả trạng thái, không bao giờ trả khoá |
| Không lưu dữ liệu cá nhân | Chỉ lưu số đơn/doanh thu tổng hợp theo kênh |
| Ngắt kết nối | Xoá sạch liên kết khỏi DB |

---

## 5. Cấu hình

Chủ shop vào **Thiết lập cửa hàng → Thiết lập kết nối API** trong KiotViet, rồi
khai vào `backend/.env`:

```
KIOTVIET_CLIENT_ID=...
KIOTVIET_CLIENT_SECRET=...
KIOTVIET_RETAILER=...
```

**Không cần redirect URL, không cần HTTPS công khai, không cần ngrok** — xác
thực là gọi thẳng server-to-server.

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `CHANNEL_SYNC_DAYS` | 60 | Kéo đơn hàng trong bao nhiêu ngày gần nhất |

Chưa khai khoá thì thẻ hiện "Chưa cấu hình" và **nút Kết nối bị khoá** — chủ ý
như vậy, vì một nút bấm vào không thể hoàn tất thì không nên sáng lên.

---

## 6. Đã kiểm thử

### Kiểm chứng bằng cách gọi thật vào KiotViet

| Kiểm tra | Bằng chứng |
|---|---|
| Endpoint lấy token có thật | `POST id.kiotviet.vn/connect/token` → `{"error":"invalid_client"}` |
| Chấp nhận `client_credentials` | Trả `invalid_client`, **không phải** `unsupported_grant_type` |
| API đơn hàng có thật | `GET public.kiotapi.com/orders` → `401`, `www-authenticate: jwt` |
| API kênh bán có thật | `GET public.kiotapi.com/salechannel` → `401` |
| Backend gọi được tới KiotViet | Bấm Kết nối với khoá sai → KiotViet từ chối → app báo đúng chỗ cần sửa |

### Đã chạy thật trên cửa hàng có dữ liệu

| Bước | Kết quả |
|---|---|
| Lấy token | ✅ HTTP 200, token sống 86.400 giây |
| Bấm "Kết nối" | ✅ `{"success":true,"retailer":"pizzaaddict"}` |
| Bấm "Lấy đơn hàng" | ✅ **46 hoá đơn, 1.406.817.000₫** (24/06 → 08/08/2026) |
| Đối chiếu dashboard KiotViet | ✅ Khớp — không phải số tự tạo |
| Chảy vào Restock Planner | ✅ Hệ số cầu tính từ số đơn thật |
| Số đo thắng phần tự khai | ✅ Đặt kênh = "không bán được" mà có dữ liệu thật thì vẫn giữ số thật |

⚠️ **Cửa hàng thử nghiệm chưa nối sàn nào vào KiotViet**, nên cả 46 hoá đơn đang
xếp vào **Cửa hàng riêng**. Đường ống đã thông và có dữ liệu chảy, nhưng để thấy
đơn tách theo Shopee/Lazada/TikTok thì chủ shop phải nối gian hàng ở mục
**Bán online → Kết nối sàn thương mại điện tử** trong KiotViet. Việc đó chỉ cần
tài khoản người bán thường, **không cần tài khoản developer**, và **không phải
sửa dòng code nào** — connector đọc `/salechannel` nên kênh mới tự hiện.

### Kiểm thử tự động

| Kiểm thử | Kết quả |
|---|---|
| Lấy token: đúng endpoint, `grant_type`, `scopes` | ✅ |
| Khoá sai → báo lỗi chỉ rõ chỗ sửa | ✅ |
| Ánh xạ kênh theo **tên** (id khác nhau mỗi cửa hàng) | ✅ Shopee/Lazada/TikTok nhận đúng, kênh khác rơi vào Cửa hàng riêng |
| Đếm đơn theo kênh, gộp nhiều trang | ✅ 102 đơn/2 trang chia đúng 61/25/10/6 |
| Dừng đúng khi hết đơn | ✅ Không lặp vô hạn |
| Token hết hạn giữa chừng | ✅ Ném lỗi, **không âm thầm đếm 0 đơn** |
| Thiếu cấu hình | ✅ Chặn ngay, liệt kê biến còn thiếu |
| Gửi đủ header `Retailer` + `Bearer` | ✅ |
| Đọc cả `/invoices` lẫn `/orders`, khử trùng theo `orderCode` | ✅ Một đơn đã xuất hoá đơn chỉ đếm 1 lần; đơn đang giao vẫn được đếm |
| Đơn hàng thật thay phần tự khai | ✅ Hệ số tính ra khớp phép tính tay 100% |
| Regression 48 route toàn hệ thống | ✅ 0 lỗi 500 |
| Bộ kiểm thử Restock Planner | ✅ 12.709 phép kiểm tra, 0 lỗi |
| Frontend build + type-check | ✅ Sạch |
| `alembic upgrade head` trên DB trắng | ✅ Chuỗi migration thẳng, đúng 1 head |
| `mypy app` / `ruff check` | ✅ 112 file, 0 lỗi |

### Ghi chú cho nhóm

**Một lỗi của code dùng chung đã được sửa trong PR này:** handler lỗi validate
(`backend/app/core/exceptions.py`) không serialize được object `ValueError` nên
trả **500 kèm traceback** thay vì 422. Bất kỳ ai viết validator tuỳ chỉnh cũng
sẽ gặp lỗi này.

**Về bảng `channel_connections`:** được tạo tự động khi dùng lần đầu, vì các
container của dự án không chạy alembic lúc khởi động. Cách này **không tự thêm
cột** khi schema đổi — nếu sau này thêm cột thì cần chạy migration hoặc tạo lại
bảng.

**Về số hiệu migration:** ban đầu đánh `0002` khi tách nhánh, đổi thành `0004`
lúc gộp lại. Hai migration cùng nối tiếp `0001_initial` sẽ để lại **hai head**,
và khi đó `alembic upgrade head` **từ chối chạy hoàn toàn** — kéo theo cả job
test trên CI chết trước khi chạy test nào. Chuỗi migration phải luôn thẳng.
