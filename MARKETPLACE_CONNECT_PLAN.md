# Technical Plan — Kết nối bán hàng đa sàn (Shopee / Lazada / TikTok Shop)

**Người thực hiện:** Phú
**Trạng thái:** ✅ TikTok Shop và Lazada đã kết nối được · ⚠️ Còn Shopee chờ điều kiện shop
**Ngày:** 2026-08-09 · cập nhật 2026-08-22

> Bản kế hoạch kỹ thuật gửi team duyệt, nay đã cập nhật theo kết quả triển khai
> thực tế. Mục 0.1 ghi lại rào cản của từng sàn sau khi đăng ký thật, chứ không
> còn là dự đoán.

---

## 0. Tóm tắt điều hành

Tầng kết nối bán hàng xây theo kiến trúc **Adapter** — một lõi chung, mỗi sàn một
bộ chuyển đổi riêng. Kết quả: **thêm sàn thứ hai và thứ ba đều chỉ tốn một file
adapter mới và một dòng import**, không sửa lõi.

**Phạm vi 5 nhóm dữ liệu đồng bộ:** thông tin cửa hàng · sản phẩm · đơn hàng ·
tồn kho · trạng thái kết nối.

### Trạng thái ba sàn

| Sàn | Khoá ứng dụng | Code adapter | Kết nối được chưa |
|---|---|---|---|
| **TikTok Shop** | ✅ Đã có | ✅ Xong | ✅ **Được** |
| **Lazada** | ✅ Đã có | ✅ Xong | ✅ **Được** |
| **Shopee** | ❌ Chưa | ✅ Xong | ⚠️ Chờ shop đạt hạng |

### Ba điều team cần biết

| # | Vấn đề | Tác động |
|---|---|---|
| 1 | **Chỉ còn Shopee bị chặn** | Shopee đòi shop đạt hạng "Shop Yêu Thích" hoặc "Shopee Mall" mới cấp khoá — hạng chỉ có sau một thời gian bán hàng thật. Hai sàn còn lại đã qua. |
| 2 | **Hệ thống chưa có tài khoản người dùng thật** | `auth.py` và `users.py` vẫn là skeleton (`access_token: "REPLACE_ME"`), chưa có bảng `users`. `seller_accounts.user_id` để nullable nên không bị chặn, gắn user sau được. |
| 3 | **Kiến trúc adapter đã được kiểm chứng bằng thực tế** | Không phải lý thuyết: thêm TikTok rồi thêm Lazada, cả hai lần đều không phải sửa luồng OAuth, vòng đồng bộ, tầng lưu trữ hay giao diện. |

---

## 0.1 Rào cản từng sàn — ghi theo kết quả đăng ký thật

Phần này viết lại sau khi trực tiếp đăng ký trên cả ba cổng developer. Dự đoán
ban đầu là cả ba sàn đều chặn theo cùng một khuôn; thực tế **chỉ Shopee chặn**.

### Khuôn chung ban đầu dự đoán

> *"Để một app đọc được dữ liệu shop qua API, shop đó phải đã ở một trạng thái
> thiết lập từ trước."*

### Thực tế kiểm chứng

| Sàn | Loại hồ sơ đã dùng | Kết quả |
|---|---|---|
| **TikTok Shop** | "Nhà phát triển ứng dụng" trên Partner Center | ✅ **Qua** — không cần shop nào cả. Dự đoán ban đầu (đòi shop đã kích hoạt) **sai**; rào cản đó chỉ áp dụng cho nhánh in-house của người bán. |
| **Lazada** | "Seller In-house APP" trên Service Provider Center | ✅ **Qua** — sau khi xác thực nhà cung cấp dịch vụ. Dự đoán ban đầu **sai**. |
| **Shopee** | Cả "Shopee Seller" lẫn "Third-party Partner Platform" | ❌ **Chặn** — loại app đọc dữ liệu shop yêu cầu shop đạt hạng **"Shop Yêu Thích"** hoặc **"Shopee Mall"** (theo `banhang.shopee.vn/edu/article/8449`). Hạng này chỉ đạt sau một thời gian bán hàng có doanh số và đánh giá. |

**Bài học:** rào cản không nằm ở "sàn nào cũng khó", mà ở **chọn đúng loại hồ sơ**.
Chọn nhánh in-house của người bán thì sàn nào cũng đòi có shop trước; chọn nhánh
nhà phát triển/nhà cung cấp dịch vụ thì TikTok và Lazada đều mở.

### Vướng mắc còn lại và hướng giải

**Shopee** là sàn duy nhất còn tắc, và tắc ở khâu thủ tục chứ không phải kỹ thuật:
`ShopeeAdapter` đã viết xong, kiểm thử 29 ca, chỉ thiếu `SHOPEE_PARTNER_ID` và
`SHOPEE_PARTNER_KEY`.

Hai hướng:

1. **Mở shop Shopee rồi bán tới khi đạt hạng** — đúng bài nhưng mất hàng tháng,
   ngoài khung thời gian đồ án.
2. **Chấp nhận hai sàn** — TikTok và Lazada đã đủ chứng minh cả kiến trúc lẫn
   luồng dữ liệu. Điền khoá Shopee sau này là **đổi config, không đổi code**.

Đề xuất hướng 2.

---

## 1. Hiện trạng — cái gì đang có

| Thành phần | File | Vai trò |
|---|---|---|
| Adapter Shopee | `app/services/marketplace/shopee.py` | ✅ Xong, chờ khoá |
| Adapter TikTok Shop | `app/services/marketplace/tiktok.py` | ✅ Đang chạy |
| Adapter Lazada | `app/services/marketplace/lazada.py` | ✅ Đang chạy |
| Giao thức chung | `app/services/marketplace/base.py` | Lõi, không đổi khi thêm sàn |
| Mã hoá credential | `app/services/marketplace/crypto.py` | Fernet + băm một chiều người mua |
| Vòng đời kết nối | `app/services/marketplace_link.py` | Dùng chung cả ba sàn |
| 9 bảng dữ liệu | `app/models/marketplace.py` + migration `0005` | |
| API | `app/api/v1/endpoints/marketplace.py` | 6 endpoint |
| Giao diện | `components/features/marketplace-panel.tsx` | Màn danh sách shop |

**Kết nối qua KiotViet (`channel_link.*`) vẫn giữ và vẫn chạy.** Đây là nguồn dữ
liệu thật duy nhất hiện có (46 hoá đơn, hơn 1,4 tỷ đồng), và Restock Planner đọc
số đơn theo kênh từ đó. Hai đường chạy song song, không xung đột.

---

## 2. Kiến trúc

### 2.1 Ba lớp tách bạch

```
┌─────────────────────────────────────────────────────────────┐
│  LỚP 1 — DOMAIN (không biết sàn nào là sàn nào)              │
│  SellerAccount · ShopConnection · Product · Order · Stock    │
└─────────────────────────────────────────────────────────────┘
                          ▲
                          │  dữ liệu đã chuẩn hoá
┌─────────────────────────────────────────────────────────────┐
│  LỚP 2 — NORMALIZER (raw → canonical)                        │
│  ánh xạ trạng thái, đơn vị tiền, timezone, tên trường        │
└─────────────────────────────────────────────────────────────┘
                          ▲
                          │  payload thô của từng sàn
┌─────────────────────────────────────────────────────────────┐
│  LỚP 3 — ADAPTER (mỗi sàn một bộ, cùng một giao diện)        │
│  ShopeeAdapter   TikTokAdapter   LazadaAdapter               │
│  ký số riêng · OAuth riêng · phân trang riêng                │
└─────────────────────────────────────────────────────────────┘
```

**Nguyên tắc:** mọi thứ đặc thù của sàn chỉ tồn tại ở Lớp 3. Lớp 1 và 2 không có
chữ `shopee` / `lazada` / `tiktok` ở đâu ngoài giá trị enum.

Đã kiểm chứng hai lần: thêm TikTok, rồi thêm Lazada, **không lần nào phải sửa lõi**.

### 2.2 Giao diện chung mọi adapter tuân theo

```python
class MarketplaceAdapter(Protocol):
    platform: str

    def authorize_url(self, state: str, redirect_uri: str) -> str: ...
    async def exchange_code(self, code: str, params: dict) -> TokenBundle: ...
    async def refresh(self, refresh_token: str, cred: Cred) -> TokenBundle: ...

    async def fetch_shop(self, cred: Cred) -> ShopProfile: ...
    async def fetch_products(self, cred: Cred, cursor: str | None) -> Page: ...
    async def fetch_orders(self, cred: Cred, since: datetime,
                           cursor: str | None) -> Page: ...
    async def fetch_inventory(self, cred: Cred, cursor: str | None) -> Page: ...
```

### 2.3 Ba sàn khác nhau ở đâu — và adapter giấu đi thế nào

| Khác biệt | Shopee | TikTok Shop | Lazada |
|---|---|---|---|
| **Thuật toán ký** | Nối chuỗi `partner_id + path + ts + token + shop_id` | Bọc `app_secret` ở **cả hai đầu**, phủ cả body | **Không bọc**, và digest phải **in hoa** |
| **access_token khi ký** | Là thành phần được ký | Là header, **loại khỏi** phần ký | Là query param, **nằm trong** phần ký |
| **Phân trang** | offset | cursor `page_token` | offset |
| **Dữ liệu phụ bắt buộc** | không | **`shop_cipher`** trên mọi call | không |
| **Host API** | một host (+ sandbox riêng) | một host | **theo từng quốc gia** |
| **Mã lỗi** | `error` dạng chuỗi | `code` dạng **số**, 0 = ok | `code` dạng **chuỗi**, `"0"` = ok |
| **Vòng đời token** | 4 giờ / 30 ngày | 7 ngày / 365 ngày | 7 ngày / 30 ngày |

Bảng này là lý do lớp adapter tồn tại: không có hai sàn nào giống nhau ở bất kỳ
dòng nào.

### 2.4 Lưu raw song song với canonical

Mỗi bảng dữ liệu có cột `raw_json`. Khi phát hiện ánh xạ sai — chuyện chắc chắn
xảy ra ở lần tích hợp đầu — có thể **chuẩn hoá lại từ raw mà không gọi lại API**,
tránh chạm rate limit và tránh mất dữ liệu sàn đã xoá.

---

## 3. Database schema

```
users (chưa có — user_id để nullable)
  │
  └─< seller_accounts          tài khoản bán hàng trên platform
        │
        └─< shop_connections   1 tài khoản ↔ N shop trên N sàn
              ├── shop_credentials   (1-1, token mã hoá, tách bảng)
              ├─< shop_products
              │     └─< shop_inventory
              ├─< shop_orders
              │     └─< shop_order_items
              └─< sync_runs          nhật ký từng lần đồng bộ

oauth_states                    chống giả mạo callback (độc lập)
```

### Ba quyết định thiết kế đáng giải thích

**Token tách sang bảng riêng.** Màn danh sách shop lúc nào cũng `SELECT` bảng
`shop_connections`. Nếu token nằm chung, chỉ cần một serializer cẩu thả là rò
token ra API — kiểu rò rỉ phổ biến nhất ở loại tính năng này. Token không thể rò
ra từ bảng mà không truy vấn nào đụng tới.

**Tiền lưu số nguyên đơn vị nhỏ nhất (đồng).** Số thực tích luỹ sai số ngay khi
đem cộng.

**Không lưu thông tin cá nhân người mua.** Chỉ lưu `buyer_ref` = băm một chiều có
muối, đủ nhận ra khách quay lại, không lần ngược ra danh tính.

---

## 4. User flow

### 4.1 Tạo tài khoản bán hàng

```
1. Vào "Kết nối bán hàng" → "Tạo tài khoản bán hàng"
2. Điền tên, loại hình (cá nhân/doanh nghiệp), liên hệ
3. Hệ thống tạo seller_account, trạng thái active
4. Chuyển tới màn danh sách shop (đang trống)
```

### 4.2 Kết nối một shop

```
   Người bán            Platform (BE)                    Sàn
       │                     │                            │
 1.    ├─ bấm "Kết nối" ────►│                            │
       │                     │ tạo state (TTL 15 phút)    │
       │                     │ dựng authorize_url + ký    │
       │  ◄── 302 redirect ──┤                            │
 2.    ├──── đăng nhập & cấp quyền ──────────────────────►│
 3.    │  ◄──── redirect về /callback?code=&state= ───────┤
 4.    │                     ├─ kiểm state (còn hạn? chưa dùng?)
       │                     ├─ đổi code lấy token ──────►│
       │                     ├─ lưu token (đã mã hoá)     │
       │                     ├─ đọc tên shop ────────────►│
       │                     ├─ shop_connection = connected
 5.    │  ◄── về màn danh sách, hiện shop vừa nối ────────┤
```

### 4.3 Các nhánh lỗi đã xử lý

| Tình huống | Hệ thống làm gì |
|---|---|
| Người bán **từ chối** cấp quyền | Báo rõ, **không để lại kết nối rác** |
| `state` sai / hết hạn / **dùng lại** | Từ chối + ghi log — dùng lại là dấu hiệu callback bị đánh cắp |
| Access token sắp hết hạn | Tự làm mới ở **80% vòng đời**, không đợi 401 |
| Refresh token chết | → `expired`, yêu cầu nối lại, **giữ nguyên dữ liệu đã đồng bộ** |
| Bị thu hồi quyền từ phía sàn | → `revoked` (khác `expired`: người bán chủ động) |
| Nối trùng shop | Cập nhật kết nối cũ, không tạo bản ghi thứ hai |
| Chạm rate limit | Nhận diện riêng, kèm thời gian chờ |
| **Sàn báo lỗi kèm HTTP 200** | Đọc lỗi trong body — cả ba sàn đều làm vậy |
| Trạng thái đơn lạ | Ghi `unknown` + cảnh báo, **không đoán bừa** |
| Thiếu `shop_cipher` (TikTok) | Báo đúng nguyên nhân, không để lẫn với token hết hạn |

---

## 5. Chuẩn hoá dữ liệu — bảng ánh xạ trạng thái đơn

| Canonical | Shopee | TikTok Shop | Lazada |
|---|---|---|---|
| `unpaid` | `UNPAID` | `UNPAID` | `unpaid` |
| `awaiting_shipment` | `READY_TO_SHIP`, `PROCESSED` | `AWAITING_SHIPMENT`, `ON_HOLD` | `pending`, `packed`, `topack`, `toship` |
| `shipped` | `SHIPPED` | `AWAITING_COLLECTION`, `IN_TRANSIT` | `shipped`, `shipping` |
| `delivered` | `TO_CONFIRM_RECEIVE` | `DELIVERED` | `delivered` |
| `completed` | `COMPLETED` | `COMPLETED` | `confirmed` |
| `cancelled` | `CANCELLED`, `IN_CANCEL` | `CANCELLED` | `canceled`, `failed`, `lost` |
| `returned` | `TO_RETURN` | — | `returned` |

Mã lạ chưa có trong bảng → ánh xạ `unknown` + ghi cảnh báo, **tuyệt đối không gán
bừa**. Có test riêng cho từng sàn xác nhận điều này.

### Các chuẩn hoá khác

| Vấn đề | Quy tắc thống nhất |
|---|---|
| Tiền tệ | Số nguyên đơn vị nhỏ nhất (đồng). Không dùng float |
| Thời gian | Unix timestamp (Shopee, TikTok) hoặc chuỗi có offset (Lazada) → quy hết về **UTC** |
| Định danh sản phẩm | `item_id/model_id`, `product_id/sku_id`, `item_id/SkuId` → gộp về `external_product_id` + `external_sku_id` |
| Phân trang | offset và cursor → lộ ra ngoài đều là `Page(items, next_cursor)` |

---

## 6. API và quyền truy cập từng sàn

### 6.1 TikTok Shop Partner Center ✅

| Mục | Giá trị |
|---|---|
| Uỷ quyền | `services.tiktokshop.com/open/authorize` |
| Token | `auth.tiktok-shops.com/api/v2/token/get` · `/refresh` |
| Lấy `shop_cipher` | `/authorization/202309/shops` ⚠️ bắt buộc trước mọi call |
| Sản phẩm | `POST /product/202312/products/search` |
| Đơn hàng | `POST /order/202309/orders/search` |

**Ký:** bọc `app_secret` hai đầu, phủ path + query đã sắp xếp + body
**Token:** access ~7 ngày · refresh ~365 ngày

### 6.2 Lazada Open Platform ✅

| Mục | Giá trị |
|---|---|
| Uỷ quyền | `auth.lazada.com/oauth/authorize` |
| Token | `auth.lazada.com/rest/auth/token/create` · `/refresh` |
| Thông tin shop | `/seller/get` |
| Sản phẩm | `/products/get` |
| Đơn hàng | `/orders/get` + `/orders/items/get` |
| Host | Theo quốc gia: `api.lazada.vn/rest` cho VN |

**Ký:** `HMAC-SHA256(app_secret, path + sorted(k+v))` → **in hoa**, không bọc
**Token:** access ~7 ngày · refresh ~30 ngày · giới hạn 5 shop được uỷ quyền

### 6.3 Shopee Open Platform ⚠️ chờ khoá

| Mục | Giá trị |
|---|---|
| Uỷ quyền | `/api/v2/shop/auth_partner` |
| Token | `/api/v2/auth/token/get_access_token` · `/api/v2/auth/access_token/get` |
| Sản phẩm | `/api/v2/product/get_item_list` + `get_item_base_info` |
| Tồn kho | `/api/v2/product/get_model_list` |
| Đơn hàng | `/api/v2/order/get_order_list` + `get_order_detail` |
| Sandbox | `partner.test-stable.shopeemobile.com` |

**Ký:** `HMAC-SHA256(partner_key, partner_id + path + ts + access_token + shop_id)`
**Token:** access ~4 giờ (ngắn nhất trong ba sàn) · refresh ~30 ngày

---

## 7. Danh sách dữ liệu đồng bộ

**Nhóm 1 — Thông tin cửa hàng** *(khi kết nối + hằng ngày)*
`external_shop_id` · `shop_name` · `region` · `trạng thái shop`

**Nhóm 2 — Sản phẩm** *(hằng ngày)*
`external_product_id` · `external_sku_id` · `sku` · `tên` · `thương hiệu` ·
`ngành hàng` · `giá niêm yết` · `giá bán` · `trạng thái` · `ảnh chính`

**Nhóm 3 — Đơn hàng** *(15-30 phút, đồng bộ tăng dần)*
`external_order_id` · `trạng thái đã chuẩn hoá` · `tổng tiền` ·
`phương thức thanh toán` · `thời điểm đặt` · `thời điểm cập nhật` ·
**các dòng hàng**: `sku`, `số lượng`, `đơn giá`

❌ **Không lấy:** tên, số điện thoại, địa chỉ người mua

**Nhóm 4 — Tồn kho** *(1-4 giờ)*
`external_sku_id` · `warehouse_id` · `số lượng khả dụng` · `số lượng đã giữ`

**Nhóm 5 — Trạng thái kết nối** *(realtime)*
`status` · `authorized_at` · `expires_at` · `last_synced_at` · `last_error`

---

## 8. Tiến độ thực tế

| GĐ | Nội dung | Trạng thái |
|---|---|---|
| 1 | Domain model + migration + CRUD tài khoản + màn danh sách shop | ✅ Xong |
| 2 | `MarketplaceAdapter` protocol + khung OAuth + mã hoá token | ✅ Xong |
| 3 | **ShopeeAdapter** | ✅ Code xong · ⚠️ chờ khoá |
| 4 | Normalizer + vòng đồng bộ + `sync_runs` + xử lý lỗi | ✅ Xong |
| 5 | **TikTokAdapter** | ✅ **Xong, đã kết nối** |
| 6 | **LazadaAdapter** | ✅ **Xong, đã kết nối** |
| 7 | Job đồng bộ định kỳ | ⏳ Chưa — hiện bấm tay |

---

## 9. Những điểm cần team quyết

| # | Câu hỏi | Đề xuất |
|---|---|---|
| 1 | **Có theo đuổi Shopee tới cùng không?** | Đề xuất **không** trong khung thời gian này. Hai sàn đã đủ chứng minh; điền khoá Shopee sau là đổi config |
| 2 | **Ai làm phần `users` / auth?** | `seller_accounts.user_id` đang nullable nên không bị chặn, gắn user sau được |
| 3 | **Giữ connector KiotViet không?** | Đề xuất **giữ**. Nguồn dữ liệu thật duy nhất (46 hoá đơn / 1,4 tỷ), Restock Planner đang đọc từ đó |
| 4 | **Có lưu thông tin người mua không?** | Đề xuất **không** — hiện chỉ băm một chiều |
| 5 | **Tần suất đồng bộ?** | Đơn 15-30 phút · tồn kho 1-4 giờ · sản phẩm hằng ngày |

---

## 10. Deliverables — đối chiếu yêu cầu

| Yêu cầu bàn giao | Trạng thái |
|---|---|
| User flow tạo tài khoản + kết nối shop | ✅ Mục 4, đã code, chạy tại `/seller/marketplace` |
| Danh sách API, quyền truy cập, dữ liệu từng sàn | ✅ Mục 6 + 7 |
| Database schema / data mapping | ✅ Mục 3 + 5, 9 bảng thật (migration `0005`) |
| Luồng kết nối chạy được | ✅ **TikTok Shop và Lazada đã kết nối** |
| Phần còn thiếu cho các sàn khác | ✅ Chỉ còn Shopee, chờ điều kiện shop |
| Technical plan gửi team review | ✅ Chính là tài liệu này |

> Chi tiết đã code gì, kiểm thử gì: xem
> [MARKETPLACE_CONNECT_HANDOVER.md](MARKETPLACE_CONNECT_HANDOVER.md).

---

## 11. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Shopee không đạt hạng kịp | 🟡 Vừa | Chấp nhận hai sàn; điền khoá sau là đổi config |
| Token TikTok/Lazada hết hạn giữa chừng | 🟢 Thấp | Tự làm mới ở 80% vòng đời, đã có test |
| Ánh xạ trạng thái sai | 🟡 Vừa | Lưu `raw_json` → chuẩn hoá lại không cần gọi API |
| Chạm rate limit khi đồng bộ lần đầu | 🟡 Vừa | Đồng bộ tăng dần + ghi `sync_runs` |
| Rò rỉ token | 🔴 Cao | Tách bảng riêng + mã hoá Fernet + schema API không có trường token |
| Lazada giới hạn 5 shop uỷ quyền | 🟢 Thấp | Đủ cho demo và pilot 5-10 shop |
| Phụ thuộc phần auth chưa ai làm | 🟡 Vừa | `seller_accounts` đứng độc lập được |
