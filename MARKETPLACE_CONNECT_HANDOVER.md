# Bàn giao — Kết nối bán hàng đa sàn

**Người thực hiện:** Phú · **Ngày:** 2026-08-22
**Kèm theo:** [MARKETPLACE_CONNECT_PLAN.md](MARKETPLACE_CONNECT_PLAN.md)

---

## Tóm tắt 30 giây

**Hai trên ba sàn đã kết nối được. Chỉ còn Shopee, và vướng ở thủ tục chứ không
phải kỹ thuật.**

| Sàn | Khoá ứng dụng | Code adapter | Kết nối |
|---|---|---|---|
| **TikTok Shop** | ✅ | ✅ | ✅ **Được** |
| **Lazada** | ✅ | ✅ | ✅ **Được** |
| **Shopee** | ❌ | ✅ | ⚠️ Chờ shop đạt hạng "Shop Yêu Thích" |

**Kiểm thử:** 163 test pass · mypy 122 file 0 lỗi · ruff sạch · alembic chạy trọn
5 migration trên DB trắng.

---

## 1. Kiến trúc — và bằng chứng nó đúng

```
LỚP 1  DOMAIN      SellerAccount · ShopConnection · Product · Order · Stock
                   ↑ không có chữ "shopee" / "lazada" / "tiktok" nào
LỚP 2  NORMALIZER  trạng thái · tiền tệ · timezone · định danh · phân trang
LỚP 3  ADAPTER     ShopeeAdapter ✅ │ TikTokAdapter ✅ │ LazadaAdapter ✅
```

Toàn bộ luồng kết nối, vòng đồng bộ, tầng lưu trữ và giao diện viết dựa trên
`MarketplaceAdapter` — một protocol, không phải một sàn cụ thể.

**Đây không còn là lý thuyết.** Sàn thứ hai (TikTok) và sàn thứ ba (Lazada) đều
được thêm bằng đúng một cách: **một file adapter mới + một dòng import**. Cả hai
lần đều không phải sửa bảng dữ liệu, luồng OAuth, vòng đồng bộ hay giao diện.

### Ba sàn khác nhau tới mức nào

Đây là lý do lớp adapter phải tồn tại — không có hai sàn nào giống nhau ở bất kỳ
dòng nào:

| Khác biệt | Shopee | TikTok Shop | Lazada |
|---|---|---|---|
| **Thuật toán ký** | Nối chuỗi `partner_id + path + ts + token + shop_id` | Bọc `app_secret` **hai đầu**, phủ cả body | **Không bọc**, digest phải **in hoa** |
| **access_token khi ký** | Được ký | Là header, **loại khỏi** phần ký | Là query param, **nằm trong** phần ký |
| **Phân trang** | offset | cursor `page_token` | offset |
| **Dữ liệu phụ bắt buộc** | không | **`shop_cipher`** trên mọi call | không |
| **Host API** | một host + sandbox | một host | **theo từng quốc gia** |
| **Mã lỗi** | `error` chuỗi | `code` **số**, `0` = ok | `code` **chuỗi**, `"0"` = ok |
| **Vòng đời token** | 4 giờ / 30 ngày | 7 ngày / 365 ngày | 7 ngày / 30 ngày |

---

## 2. Database — 9 bảng (migration `0005`)

```
seller_accounts          tài khoản bán hàng trên platform
  └─< shop_connections   1 tài khoản ↔ N shop trên N sàn
        ├── shop_credentials   token mã hoá, TÁCH BẢNG RIÊNG
        ├─< shop_products
        │     └─< shop_inventory
        ├─< shop_orders
        │     └─< shop_order_items
        └─< sync_runs          nhật ký từng lần đồng bộ
oauth_states             chống giả mạo callback, dùng 1 lần
```

### Ba quyết định thiết kế đáng giải thích

**Token tách sang bảng riêng.** Màn danh sách shop lúc nào cũng `SELECT` bảng
`shop_connections`. Nếu token nằm chung, chỉ cần một serializer cẩu thả là rò
token ra API — kiểu rò rỉ phổ biến nhất ở loại tính năng này. Token không thể rò
ra từ một bảng mà không truy vấn nào đụng tới.

**Lưu `raw_json` song song với cột đã chuẩn hoá.** Lần tích hợp đầu chắc chắn sẽ
ánh xạ sai ở đâu đó. Có raw thì **chuẩn hoá lại được mà không phải gọi lại API** —
tránh chạm rate limit và tránh mất dữ liệu sàn đã xoá.

**Tiền lưu số nguyên đơn vị nhỏ nhất (đồng).** Số thực tích luỹ sai số ngay khi
đem cộng.

---

## 3. Đã xử lý những tình huống nào

| Tình huống | Hệ thống làm gì |
|---|---|
| Người bán **từ chối** cấp quyền | Báo rõ, **không để lại kết nối rác** |
| `state` sai / hết hạn / **dùng lại** | Từ chối + ghi log — dùng lại là dấu hiệu callback bị đánh cắp |
| Access token sắp hết hạn | Tự làm mới ở **80% vòng đời**, không đợi tới lúc 401 |
| Refresh token chết | → `expired`, yêu cầu nối lại, **giữ nguyên dữ liệu đã đồng bộ** |
| Bị thu hồi quyền từ phía sàn | → `revoked` (khác `expired`: người bán đã chủ động) |
| Nối trùng shop | Cập nhật kết nối cũ, không tạo bản ghi thứ hai |
| Chạm rate limit | Nhận diện riêng, kèm thời gian chờ |
| **Sàn báo lỗi kèm HTTP 200** | Đọc lỗi trong body — **cả ba sàn đều làm vậy** |
| Trạng thái đơn lạ | Ghi `unknown` + cảnh báo, **tuyệt đối không đoán bừa** |
| Thiếu `shop_cipher` (TikTok) | Báo đúng nguyên nhân, không để lẫn với token hết hạn |
| Mất endpoint chi tiết đơn (Lazada) | Vẫn giữ đơn hàng — tổng tiền và ngày vẫn dùng được |

---

## 4. Kiểm thử

| Bộ | Số ca |
|---|---|
| Adapter Shopee | 29 |
| Adapter TikTok Shop | 26 |
| Adapter Lazada | 38 |
| Mã hoá credential | 13 |
| **Toàn hệ thống** | **163 pass, 0 lỗi** |

### Vì sao chữ ký tin được dù chưa gọi thật vào Shopee

Bộ test **tính lại HMAC bằng tay** theo đặc tả từng sàn, độc lập với code, rồi so
sánh. Điểm quan trọng: một test so code với chính nó vẫn xanh y nguyên khi chuỗi
ký sai — mà chuỗi ký sai chính là lỗi dễ xảy ra nhất ở đây, và cả ba sàn đều trả
lỗi chung chung không chỉ ra sai chỗ nào.

Có thêm các test riêng cho những bẫy im lặng:

- **Lazada:** một test chứng minh thuật toán ký **không trùng** cách bọc secret của
  TikTok — chống việc sao chép nhầm giữa hai adapter
- **Lazada:** test riêng cho bẫy `code` là chuỗi `"0"` — so với số `0` sẽ coi mọi
  lần thành công là lỗi
- **TikTok:** một test stub tầng HTTP để kiểm chứng `shop_cipher` và chữ ký **thật
  sự lên đường truyền**, không chỉ đúng ở tham số hàm
- **Cả ba:** test xác nhận mọi trạng thái được ánh xạ đều nằm trong bộ từ vựng
  canonical, không có giá trị lạ lọt vào database

---

## 5. ⚠️ Vướng mắc duy nhất còn lại — Shopee

**Không phải việc code.** `ShopeeAdapter` đã viết xong và kiểm thử 29 ca; chỉ
thiếu `SHOPEE_PARTNER_ID` và `SHOPEE_PARTNER_KEY`.

Shopee yêu cầu shop đạt hạng **"Shop Yêu Thích"** hoặc **"Shopee Mall"** mới cấp
khoá cho loại app đọc dữ liệu shop (theo `banhang.shopee.vn/edu/article/8449`).
Hạng này chỉ đạt được sau một thời gian bán hàng có doanh số và đánh giá — không
có ngay với shop mới mở.

### Điều đáng nói: dự đoán ban đầu về TikTok và Lazada đã sai

Bản plan đầu tiên dự đoán **cả ba sàn** đều chặn theo cùng một khuôn. Thực tế:

| Sàn | Dự đoán ban đầu | Thực tế |
|---|---|---|
| TikTok Shop | Đòi shop đã kích hoạt | ❌ Sai — nhánh "Nhà phát triển ứng dụng" **không cần shop nào** |
| Lazada | Khả năng cao chặn tương tự | ❌ Sai — qua được sau khi xác thực nhà cung cấp dịch vụ |
| Shopee | Đòi hạng shop | ✅ Đúng |

**Bài học:** rào cản không nằm ở "sàn nào cũng khó", mà ở **chọn đúng loại hồ sơ**.
Chọn nhánh in-house của người bán thì sàn nào cũng đòi có shop trước; chọn nhánh
nhà phát triển thì TikTok và Lazada đều mở.

### Khi có khoá Shopee thì làm gì

Điền 3 dòng vào `backend/.env`, khởi động lại backend. **Không sửa code.**

```
SHOPEE_PARTNER_ID=...
SHOPEE_PARTNER_KEY=...
SHOPEE_SANDBOX=true
```

**Hệ thống xử lý trạng thái này một cách trung thực:** sàn chưa có khoá thì nút
"Kết nối" bị khoá và ghi rõ thiếu biến nào, thay vì mở ra một luồng chắc chắn
không hoàn tất được.

```
Vào /seller/marketplace hiện tại sẽ thấy:
  Shopee       [Chưa cấu hình]  Thiếu SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY
  TikTok Shop  [Sẵn sàng kết nối]
  Lazada       [Sẵn sàng kết nối]
```

---

## 6. Về kết nối KiotViet đang chạy song song

Vẫn giữ và vẫn hoạt động. Đây là **nguồn dữ liệu thật duy nhất hiện có**: 46 hoá
đơn, hơn 1,4 tỷ đồng, khớp chính xác dashboard gốc của cửa hàng.

Restock Planner đọc số đơn theo kênh từ đó (`channel_link.synced_rates`), nên đây
không phải code cũ bỏ đi — nó đang phục vụ một tính năng đang chạy.

Hai đường chạy song song, không xung đột:

- **KiotViet** — một liên kết mang dữ liệu tổng hợp nhiều kênh, đã có dữ liệu thật
- **Marketplace adapter** — kết nối thẳng từng sàn, chi tiết hơn (sản phẩm, tồn
  kho, từng dòng hàng), đã sẵn sàng nhận dữ liệu

---

## 7. Câu hỏi cần team chốt

| # | Câu hỏi | Đề xuất |
|---|---|---|
| 1 | **Có theo đuổi Shopee tới cùng không?** | **Không** trong khung thời gian này. Hai sàn đã đủ chứng minh cả kiến trúc lẫn luồng dữ liệu |
| 2 | **Ai làm phần `users` / auth?** | `auth.py` đang trả `"REPLACE_ME"`. `seller_accounts.user_id` để nullable nên không bị chặn |
| 3 | **Giữ connector KiotViet không?** | **Giữ** — nguồn dữ liệu thật duy nhất, và Restock Planner đang phụ thuộc |
| 4 | **Có lưu thông tin người mua không?** | **Không** — hiện chỉ băm một chiều có muối |
| 5 | **Tần suất đồng bộ định kỳ?** | Đơn 15-30 phút · tồn kho 1-4 giờ · sản phẩm hằng ngày |

---

## 8. Thử ngay được gì hôm nay

Vào `http://localhost:3000/seller/marketplace`:

1. **Tạo tài khoản bán hàng** → hoạt động đầy đủ
2. **Xem danh sách shop** → cột Shop / Sàn / Trạng thái / Đồng bộ gần nhất
3. **Bấm Kết nối TikTok Shop hoặc Lazada** → sinh đúng URL uỷ quyền của sàn
4. **Bấm Kết nối Shopee** → bị chặn kèm thông báo chỉ rõ thiếu khoá nào

Kiểm chứng bằng API:

```bash
curl localhost:8000/api/v1/marketplace/platforms
curl -X POST localhost:8000/api/v1/marketplace/accounts \
  -H 'Content-Type: application/json' -d '{"name":"Shop Test"}'
curl localhost:8000/api/v1/marketplace/shops
```

---

## 9. Việc còn lại theo thứ tự

| Ưu tiên | Việc | Ai |
|---|---|---|
| 🔴 Ngay | Nối shop TikTok/Lazada thật để có dữ liệu đơn hàng chảy vào | Cần tài khoản người bán |
| 🟡 Sau đó | Job đồng bộ định kỳ, thay cho bấm tay | Phú |
| 🟡 Song song | Chốt phần `users` / auth | Team |
| 🟢 Nếu có điều kiện | Khoá Shopee khi shop đạt hạng | **0 dòng code** |
