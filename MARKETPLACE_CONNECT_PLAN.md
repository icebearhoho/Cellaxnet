# Technical Plan — Kết nối bán hàng đa sàn (Shopee / Lazada / TikTok Shop)

**Người thực hiện:** Phú
**Trạng thái:** ✅ Kiến trúc + code nền đã xong · ⚠️ Chờ khoá app cả 3 sàn
**Ngày:** 2026-08-09 (cập nhật 2026-08-13 — thêm Mục 0.1)

> Tài liệu này là bản kế hoạch kỹ thuật gửi team duyệt trước khi bắt tay vào code,
> theo đúng yêu cầu. Phần cuối có **checklist những điểm cần team xác nhận**.

---

## 0. Tóm tắt điều hành

Xây lại tầng kết nối bán hàng theo kiến trúc **Adapter** — một lõi chung, mỗi sàn
một bộ chuyển đổi riêng. Làm Shopee trước cho chạy được trên sandbox, rồi mở rộng
sang Lazada và TikTok Shop **mà không phải sửa lõi**.

**Phạm vi 5 nhóm dữ liệu đồng bộ:** thông tin cửa hàng · sản phẩm · đơn hàng ·
tồn kho · trạng thái kết nối.

### ⚠️ Bốn điều team cần biết ngay

| # | Vấn đề | Tác động |
|---|---|---|
| 1 | **Đăng ký developer cả 3 sàn là đường găng (critical path)** | Bắt duyệt hồ sơ **trước khi** cho tạo app. Không có app = không có sandbox = không hoàn thành được deliverable #4. **Phải nộp hồ sơ ngay, song song với code.** |
| 2 | **⚠️ Rào cản không dừng ở duyệt hồ sơ — xem Mục 0.1** | Cả 3 sàn đều đòi shop phải ở một **trạng thái đã thiết lập từ trước** mới cho đăng ký API, không phải cứ có CCCD/giấy tờ là qua. **Đây là phát hiện mới, quan trọng hơn cả bước duyệt hồ sơ.** |
| 3 | **Hệ thống chưa có tài khoản người dùng thật** | `auth.py` và `users.py` hiện chỉ là skeleton (`access_token: "REPLACE_ME"`), chưa có bảng `users`. Yêu cầu #2 (tài khoản bán hàng) **phụ thuộc vào việc này**. Cần quyết ai làm phần auth. |
| 4 | **Code kết nối cũ theo hướng OAuth 4 sàn đã mất** | PR trước bị squash nên không còn trong lịch sử git. Phần ký HMAC Shopee phải viết lại (ước tính 1 ngày, thiết kế đã rõ). |

---

## 0.1 ⚠️ Rào cản chung cho cả 3 sàn — phát hiện khi đăng ký thật

Đây là phần cập nhật sau khi trực tiếp thử đăng ký trên cả 3 cổng developer. Rào
cản dưới đây **không phải đặc thù của Shopee** — nó lặp lại theo cùng một khuôn ở
cả 3 sàn, chỉ khác tên gọi.

### Khuôn chung

> **Để một app đọc được dữ liệu shop qua API, shop đó phải đã ở một "trạng thái
> đã thiết lập" từ trước — không phải shop nào mới đăng ký cũng đủ điều kiện,
> kể cả khi đã có đầy đủ CCCD/giấy tờ.**

| Sàn | Tên gọi rào cản | Shop mới tạo có qua được không |
|---|---|---|
| **Shopee** | Loại app "Shopee Seller" yêu cầu shop đạt hạng **"Shop Yêu Thích"** hoặc **"Shopee Mall"** (theo trang chính thức `banhang.shopee.vn/edu/article/8449` — *Điều Kiện Sử Dụng & Quy Trình Xét Duyệt Open API*) | ❌ Không — hạng này chỉ đạt được sau một thời gian bán hàng có doanh số/đánh giá, không có ngay lúc mới mở shop |
| **TikTok Shop** | Bắt buộc **đã có TikTok Shop kích hoạt** mới cho đăng ký Partner Center/developer | ❌ Không — điều kiện tiên quyết là shop đã hoạt động, không phải shop vừa nộp hồ sơ |
| **Lazada** | Chưa tự tay thử tới bước này, nhưng cùng mô hình Open Platform như Shopee (ISV/Seller App phân theo loại hồ sơ) — **khả năng cao có rào cản dạng tương tự** | ⚠️ Chưa kiểm chứng trực tiếp — cần thử thật để xác nhận, không nên giả định đã an toàn |

**Vì sao xếp chung một nhóm:** cả 3 sàn đều tách biệt hai khái niệm — *"có shop
hợp lệ"* và *"shop đủ điều kiện gọi API"*. Duyệt hồ sơ danh tính (CCCD, giấy tờ)
chỉ là điều kiện cần; **điều kiện đủ là shop đã có lịch sử hoạt động thật**, thứ
một shop mới tạo cho đồ án không thể có ngay.

### Vì sao Sandbox vẫn là hướng đúng

Rào cản trên áp dụng cho **app dạng thật (Live/Seller App)**, dùng cho shop cụ
thể. Môi trường **Sandbox** — nơi Shopee cấp sẵn tài khoản Test Seller/Test
Buyer giả lập — **không đòi hỏi shop đạt hạng nào cả**, chỉ cần qua bước duyệt hồ
sơ developer cá nhân (CCCD). Đây vẫn là đường khả thi nhất để hoàn thành deliverable
#4 (luồng chạy trên sandbox), **tách biệt khỏi yêu cầu phải có shop đạt hạng**.

### Đề xuất cho team

1. **Ưu tiên hoàn thành trên Sandbox trước**, không chờ shop đạt hạng "Shop Yêu
   Thích" hay tương đương — việc đó có thể mất hàng tháng bán hàng thật, ngoài
   khung thời gian đồ án.
2. Khi trình bày, nói rõ: *"luồng OAuth + đọc dữ liệu chạy được trên môi trường
   test chính thức của sàn; chạy trên shop thật cần shop đạt điều kiện riêng của
   từng sàn, ngoài tầm kiểm soát của nhóm trong thời gian ngắn"* — đây là giới
   hạn khách quan, không phải thiếu sót kỹ thuật.
3. Xác nhận lại rào cản của Lazada bằng cách thử đăng ký thật, thay vì giả định
   giống 2 sàn kia — hàng dấu ⚠️ ở bảng trên cần được kiểm chứng, không suy diễn.

---

## 1. Hiện trạng — cái gì đang có, cái gì phải thay

### Đang có trong repo

| Thành phần | File | Số phận |
|---|---|---|
| Bảng `channel_connections` | `app/models/channel_link.py` | ⚠️ **Thay** — schema phẳng, không đỡ được nhiều shop/nhiều sàn/nhiều tài khoản |
| Service vòng đời kết nối | `app/services/channel_link.py` | ♻️ Giữ **pattern**, viết lại nội dung |
| Connector KiotViet | `app/services/channel_connectors.py` | ❓ **Cần team quyết** — xem Mục 9 |
| 4 endpoint kết nối | `app/api/v1/endpoints/channel_link.py` | ♻️ Mở rộng thành API đa shop |
| Giao diện 1 thẻ kết nối | `channel-link-panel.tsx` | ⚠️ **Thay** bằng màn danh sách shop |
| Auth / User | `auth.py`, `users.py`, `deps.get_current_user` | ❌ **Skeleton, chưa dùng được** |

### Vì sao phải thay `channel_connections`

Bảng hiện tại là **một dòng phẳng cho một kết nối**, khoá duy nhất `(platform, shop_id)`.
Không biểu diễn được:

- Một **tài khoản bán hàng** sở hữu nhiều shop (yêu cầu #2)
- Cùng một sàn nhưng **hai shop khác nhau** của cùng người bán
- Dữ liệu đồng bộ về (sản phẩm / đơn / tồn kho) — hiện chỉ lưu **số tổng hợp**
  trong một cột JSON, không truy vấn được

---

## 2. Kiến trúc đề xuất

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
│  ShopeeAdapter   LazadaAdapter   TikTokAdapter               │
│  ký số riêng · OAuth riêng · phân trang riêng                │
└─────────────────────────────────────────────────────────────┘
```

**Nguyên tắc bất di bất dịch:** mọi thứ đặc thù của sàn (ký số, tên trường, mã
trạng thái, cách phân trang) **chỉ được tồn tại ở Lớp 3**. Lớp 1 và 2 không được
có chữ `shopee` / `lazada` / `tiktok` ở đâu ngoài giá trị enum.

Đây chính là điều làm cho *"mở rộng sang Lazada và TikTok"* trở thành **thêm một
file adapter**, chứ không phải sửa khắp nơi.

### 2.2 Giao diện chung mọi adapter phải tuân theo

```python
class MarketplaceAdapter(Protocol):
    platform: str                    # "shopee" | "lazada" | "tiktok"

    # --- uỷ quyền ---
    def authorize_url(self, state: str, redirect_uri: str) -> str: ...
    async def exchange_code(self, code: str, ctx: dict) -> TokenBundle: ...
    async def refresh(self, refresh_token: str, ctx: dict) -> TokenBundle: ...

    # --- đọc dữ liệu (mỗi hàm trả 1 trang + con trỏ trang sau) ---
    async def fetch_shop(self, cred: Cred) -> RawShop: ...
    async def fetch_products(self, cred: Cred, cursor: str | None) -> Page: ...
    async def fetch_orders(self, cred: Cred, since: datetime,
                           cursor: str | None) -> Page: ...
    async def fetch_inventory(self, cred: Cred, cursor: str | None) -> Page: ...
```

```python
@dataclass(frozen=True)
class TokenBundle:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    refresh_expires_at: datetime | None
    scope: str | None
    extra: dict          # shop_cipher (TikTok), region (Lazada), ...
```

### 2.3 Lưu raw song song với canonical

Mỗi bảng dữ liệu có thêm cột `raw_json`.

**Lý do:** khi phát hiện ánh xạ sai (chuyện chắc chắn xảy ra ở lần tích hợp đầu),
có thể **chuẩn hoá lại từ raw mà không phải gọi lại API sàn** — tránh đụng rate
limit và tránh mất dữ liệu lịch sử đã bị sàn xoá.

---

## 3. Database schema đề xuất

### 3.1 Sơ đồ quan hệ

```
users (cần bổ sung — hiện chưa có)
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

### 3.2 Chi tiết từng bảng

**`seller_accounts`** — tài khoản bán hàng trên platform *(yêu cầu #2)*

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | PK | |
| `user_id` | FK → users | Chủ sở hữu |
| `name` | varchar(255) | Tên hiển thị |
| `business_type` | enum | `individual` / `company` |
| `contact_email`, `contact_phone` | varchar | |
| `status` | enum | `active` / `suspended` |
| `created_at`, `updated_at` | timestamptz | |

**`shop_connections`** — mỗi shop đã nối trên mỗi sàn

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | PK | |
| `seller_account_id` | FK | |
| `platform` | enum | `shopee` / `lazada` / `tiktok` |
| `external_shop_id` | varchar(64) | ID shop phía sàn |
| `shop_name` | varchar(255) | |
| `region` | varchar(8) | `VN` — Lazada/TikTok đa quốc gia |
| `status` | enum | `pending`/`connected`/`expired`/`revoked`/`error`/`disconnected` |
| `authorized_at` | timestamptz | Lúc seller cấp quyền |
| `last_synced_at` | timestamptz | **Hiển thị trên màn danh sách** |
| `last_error` | text | |
| `created_at`, `updated_at` | timestamptz | |

> **UNIQUE `(platform, external_shop_id)`** — chặn nối trùng một shop hai lần.

**`shop_credentials`** — token, **tách bảng riêng**

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `shop_connection_id` | PK, FK | 1-1 |
| `access_token_enc` | bytea | **Mã hoá** (Fernet, khoá từ env) |
| `refresh_token_enc` | bytea | **Mã hoá** |
| `expires_at` | timestamptz | Hạn access token |
| `refresh_expires_at` | timestamptz | Hạn refresh token |
| `scope` | text | Quyền đã được cấp |
| `extra_enc` | bytea | `shop_cipher` (TikTok) v.v. |
| `rotated_at` | timestamptz | Lần refresh gần nhất |

> **Vì sao tách bảng:** (a) token là dòng ghi nóng, metadata là dòng đọc nóng;
> (b) tách ra thì **không thể vô tình `SELECT *` rồi trả token ra API** — lỗi rò
> rỉ phổ biến nhất ở loại tính năng này.

**`oauth_states`** — chống giả mạo callback

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `state` | PK varchar(64) | Chuỗi ngẫu nhiên |
| `seller_account_id` | FK | Ràng buộc phiên vào đúng tài khoản |
| `platform` | enum | |
| `expires_at` | timestamptz | **TTL 15 phút** |
| `consumed_at` | timestamptz | **Dùng 1 lần** — đã dùng thì từ chối |

**`shop_products`**

| Cột | Ghi chú |
|---|---|
| `id`, `shop_connection_id` | |
| `external_product_id`, `external_sku_id` | Khoá phía sàn |
| `sku`, `name`, `brand`, `category_path` | |
| `price`, `currency` | Lưu **đơn vị nhỏ nhất** (đồng), tránh số thực |
| `status` | `active` / `inactive` / `deleted` |
| `image_url`, `raw_json`, `synced_at` | |

> UNIQUE `(shop_connection_id, external_product_id, external_sku_id)`

**`shop_inventory`** — tách riêng vì sàn hỗ trợ nhiều kho

| Cột | Ghi chú |
|---|---|
| `shop_connection_id`, `external_product_id`, `external_sku_id` | |
| `warehouse_id` | Mã kho phía sàn |
| `quantity_available`, `quantity_reserved` | |
| `synced_at` | |

**`shop_orders`**

| Cột | Ghi chú |
|---|---|
| `id`, `shop_connection_id` | |
| `external_order_id` | UNIQUE cùng `shop_connection_id` |
| `status` | **Trạng thái đã chuẩn hoá** — xem Mục 5 |
| `payment_method`, `total_amount`, `currency` | |
| `buyer_ref` | **Hash có muối** — xem cảnh báo bên dưới |
| `placed_at`, `updated_at_platform` | Giờ phía sàn, quy về UTC |
| `raw_json`, `synced_at` | |

**`shop_order_items`** — `order_id` FK, `external_product_id`, `sku`, `name`,
`quantity`, `unit_price`, `subtotal`

**`sync_runs`** — nhật ký, phục vụ quan sát và gỡ lỗi

| Cột | Ghi chú |
|---|---|
| `shop_connection_id`, `data_type` | `shop`/`product`/`order`/`inventory` |
| `started_at`, `finished_at`, `status` | |
| `records_read`, `records_written` | |
| `cursor_from`, `cursor_to` | Đồng bộ tăng dần (incremental) |
| `error` | |

> 🔒 **Về dữ liệu cá nhân người mua:** đề xuất **không lưu** tên / SĐT / địa chỉ
> người mua. Chỉ lưu `buyer_ref` = hash có muối của mã người mua, đủ để nhận biết
> khách quay lại. Nếu feature Customer Risk cần nhiều hơn, đó là **quyết định
> riêng cần team và pháp lý duyệt**, không gộp vào phạm vi này.

---

## 4. User flow

### 4.1 Tạo tài khoản bán hàng

```
1. Người dùng đăng nhập platform
2. Vào "Tài khoản bán hàng" → "Tạo mới"
3. Điền tên shop, loại hình (cá nhân/doanh nghiệp), liên hệ
4. Hệ thống tạo seller_account, trạng thái active
5. Chuyển tới màn "Kết nối shop" (đang trống)
```

### 4.2 Kết nối một shop (3 chân — có chuyển hướng)

```
   Người bán            Platform (BE)              Sàn (Shopee)
       │                     │                          │
 1.    ├─ bấm "Kết nối Shopee"─►                        │
       │                     │ tạo state (TTL 15p)      │
       │                     │ dựng authorize_url + ký  │
       │  ◄── 302 redirect ──┤                          │
       │                     │                          │
 2.    ├──── đăng nhập & cấp quyền ────────────────────►│
       │                     │                          │
 3.    │  ◄──── redirect về /callback?code=&shop_id=&state= ──┤
       │                     │                          │
 4.    │                     ├─ kiểm state (còn hạn? chưa dùng?)
       │                     ├─ đổi code lấy token ────►│
       │                     │ ◄── access + refresh ────┤
       │                     ├─ lưu token (đã mã hoá)   │
       │                     ├─ gọi fetch_shop ────────►│
       │                     │ ◄── tên shop, region ────┤
       │                     ├─ tạo shop_connection = connected
       │                     │                          │
 5.    │  ◄── về màn danh sách, hiện shop vừa nối ──────┤
       │                     │                          │
 6.    │                     ├─ kích hoạt đồng bộ lần đầu (nền)
```

### 4.3 Màn hình danh sách shop *(yêu cầu #2)*

| Shop | Sàn | Trạng thái | Đồng bộ gần nhất | Thao tác |
|---|---|---|---|---|
| Shop ABC | Shopee | 🟢 Đã kết nối | 2 phút trước | Đồng bộ · Ngắt |
| Shop XYZ | Lazada | 🟡 Hết hạn token | 3 ngày trước | **Kết nối lại** |
| Shop DEF | TikTok | 🔴 Bị thu hồi | 1 tuần trước | Kết nối lại · Xoá |

### 4.4 Các nhánh lỗi phải xử lý *(yêu cầu #4)*

| Tình huống | Phát hiện bằng | Hệ thống làm gì |
|---|---|---|
| Người bán **từ chối** cấp quyền | Callback không có `code`, hoặc có `error=access_denied` | `pending` → `error`, hiện thông báo dễ hiểu, **không tạo kết nối rác** |
| `state` sai / hết hạn / đã dùng | Không khớp DB | **Từ chối** — đây là dấu hiệu tấn công |
| Access token hết hạn | Sàn trả 401 hoặc còn <20% TTL | Tự refresh, thử lại **1 lần** |
| Refresh token hết hạn | Refresh trả lỗi | → `expired`, yêu cầu nối lại, **giữ nguyên dữ liệu đã đồng bộ** |
| Người bán thu hồi từ phía sàn | Mã lỗi riêng của sàn | → `revoked`, dừng đồng bộ, báo trên UI |
| Nối trùng shop đã có | Vi phạm UNIQUE | Cập nhật kết nối cũ thay vì tạo mới |
| Chạm rate limit | HTTP 429 | Lùi theo cấp số nhân, ghi vào `sync_runs` |

---

## 5. Chuẩn hoá dữ liệu — bảng ánh xạ

Đây là phần **quan trọng nhất** của việc "chuẩn hoá", và cũng là chỗ dễ sai nhất.

### 5.1 Trạng thái đơn hàng → canonical

| Canonical | Shopee | Lazada | TikTok Shop |
|---|---|---|---|
| `unpaid` | `UNPAID` | `unpaid` | `UNPAID` |
| `awaiting_shipment` | `READY_TO_SHIP`, `PROCESSED` | `pending`, `packed`, `ready_to_ship` | `AWAITING_SHIPMENT` |
| `shipped` | `SHIPPED` | `shipped` | `AWAITING_COLLECTION`, `IN_TRANSIT` |
| `delivered` | `TO_CONFIRM_RECEIVE` | `delivered` | `DELIVERED` |
| `completed` | `COMPLETED` | `confirmed` | `COMPLETED` |
| `cancelled` | `CANCELLED`, `IN_CANCEL` | `canceled`, `failed` | `CANCELLED` |
| `returned` | `TO_RETURN` | `returned` | `RETURNED` |

> ⚠️ Bảng này dựng từ tài liệu công khai, **phải đối chiếu lại với docs phiên bản
> hiện hành lúc implement** — các sàn có bổ sung/đổi mã trạng thái theo thời gian.
> Mã lạ chưa có trong bảng → ánh xạ `unknown` + **ghi cảnh báo**, tuyệt đối không
> âm thầm gán bừa.

### 5.2 Các chuẩn hoá khác

| Vấn đề | Quy tắc thống nhất |
|---|---|
| Tiền tệ | Lưu **số nguyên đơn vị nhỏ nhất** (đồng). Không dùng float |
| Thời gian | Sàn trả Unix timestamp (Shopee) hoặc ISO có offset (Lazada) → quy hết về **UTC**, cột `timestamptz` |
| Định danh sản phẩm | Shopee `item_id`+`model_id`, Lazada `item_id`+`sku_id`, TikTok `product_id`+`sku_id` → gộp về `external_product_id` + `external_sku_id` |
| Phân trang | Shopee offset, Lazada offset, TikTok cursor → adapter giấu hết, lớp trên chỉ thấy `Page(items, next_cursor)` |

---

## 6. Danh sách API và quyền truy cập từng sàn

> Endpoint/phiên bản dưới đây theo hiểu biết tại thời điểm viết — **phải xác nhận
> lại với tài liệu chính thức khi implement**, vì các sàn đổi phiên bản API thường
> xuyên.

### 6.1 Shopee Open Platform *(làm trước)*

| Mục | Giá trị |
|---|---|
| Uỷ quyền | `GET /api/v2/shop/auth_partner` |
| Lấy token | `POST /api/v2/auth/token/get_access_token` |
| Làm mới token | `POST /api/v2/auth/access_token/get` |
| Thông tin shop | `GET /api/v2/shop/get_shop_info` |
| Danh sách sản phẩm | `GET /api/v2/product/get_item_list` |
| Chi tiết sản phẩm | `GET /api/v2/product/get_item_base_info` |
| Tồn kho | `GET /api/v2/product/get_model_list` |
| Danh sách đơn | `GET /api/v2/order/get_order_list` |
| Chi tiết đơn | `GET /api/v2/order/get_order_detail` |
| **Sandbox host** | `partner.test-stable.shopeemobile.com` |

**Ký số:** `HMAC-SHA256(partner_key, partner_id + api_path + timestamp + access_token + shop_id)`

**Vòng đời token:** access ~**4 giờ** · refresh ~**30 ngày**
→ Token ngắn nhất trong 3 sàn, **cơ chế refresh phải chắc chắn**.

### 6.2 Lazada Open Platform

| Mục | Giá trị |
|---|---|
| Uỷ quyền | `https://auth.lazada.com/oauth/authorize` |
| Lấy token | `POST /auth/token/create` |
| Làm mới | `POST /auth/token/refresh` |
| Thông tin shop | `GET /seller/get` |
| Sản phẩm | `GET /products/get` |
| Đơn hàng | `GET /orders/get` + `GET /order/items/get` |

**Ký số:** `HMAC-SHA256(app_secret, api_path + các tham số sắp xếp nối chuỗi)` → **in hoa**
**Token:** access ~30 ngày · refresh ~30 ngày

### 6.3 TikTok Shop Partner Center

| Mục | Giá trị |
|---|---|
| Uỷ quyền | `https://services.tiktokshop.com/open/authorize` |
| Lấy token | `GET /api/v2/token/get` |
| Làm mới | `GET /api/v2/token/refresh` |
| **Lấy shop_cipher** | `GET /authorization/202309/shops` ⚠️ **bắt buộc trước mọi call khác** |
| Sản phẩm | `POST /product/202312/products/search` |
| Đơn hàng | `GET /order/202309/orders/search` |

**Token:** access ~**7 ngày** · refresh ~**365 ngày**

> ⚠️ **TikTok có thêm một bước không sàn nào khác có:** phải gọi lấy `shop_cipher`
> sau khi có token, và gắn nó vào **mọi** request sau đó. Đây là lý do
> `TokenBundle` cần trường `extra` — nếu không thiết kế sẵn thì tới lúc làm TikTok
> phải sửa lại toàn bộ lớp lưu token.

---

## 7. Danh sách dữ liệu dự kiến đồng bộ — **cần team xác nhận**

Đây là danh sách team cần duyệt trước khi code.

### Nhóm 1 — Thông tin cửa hàng *(tần suất: khi kết nối + hằng ngày)*
`external_shop_id` · `shop_name` · `region/country` · `trạng thái shop` · `ngày mở shop`

### Nhóm 2 — Sản phẩm *(hằng ngày, hoặc theo webhook nếu sàn hỗ trợ)*
`external_product_id` · `external_sku_id` · `sku` · `tên` · `thương hiệu` ·
`ngành hàng` · `giá niêm yết` · `giá bán` · `trạng thái` · `ảnh chính`

### Nhóm 3 — Đơn hàng *(mỗi 15-30 phút, đồng bộ tăng dần)*
`external_order_id` · `trạng thái (đã chuẩn hoá)` · `tổng tiền` · `phương thức thanh toán` ·
`thời điểm đặt` · `thời điểm cập nhật` · **các dòng hàng**: `sku`, `số lượng`, `đơn giá`

❌ **Không lấy:** tên, số điện thoại, địa chỉ người mua

### Nhóm 4 — Tồn kho *(mỗi 1-4 giờ)*
`external_sku_id` · `warehouse_id` · `số lượng khả dụng` · `số lượng đã giữ`

### Nhóm 5 — Trạng thái kết nối *(realtime)*
`status` · `authorized_at` · `expires_at` · `last_synced_at` · `last_error`

---

## 8. Kế hoạch triển khai theo giai đoạn

| GĐ | Nội dung | Ước tính | Phụ thuộc |
|---|---|---|---|
| **0** | Team duyệt bản plan này | — | **Đang chờ** |
| **1** | Domain model + migration + CRUD tài khoản bán hàng + màn danh sách shop | 2-3 ngày | Cần chốt phần `users`/auth |
| **2** | `MarketplaceAdapter` protocol + khung OAuth + `oauth_states` + mã hoá token | 2 ngày | GĐ 1 |
| **3** | **ShopeeAdapter** chạy được trên sandbox | 3-4 ngày | ⚠️ **Tài khoản developer Shopee (Sandbox)** |
| **4** | Normalizer + job đồng bộ + `sync_runs` + xử lý lỗi | 2-3 ngày | GĐ 3 |
| **5** | LazadaAdapter | 2 ngày | GĐ 4 |
| **6** | TikTokAdapter (thêm bước `shop_cipher`) | 2-3 ngày | GĐ 4 |

**Đường găng không phải là code, mà là thủ tục đăng ký developer — và như Mục 0.1
nêu, đây là rào cản chung cả 3 sàn, không riêng Shopee.** GĐ 1-2 làm được ngay
không cần chờ; GĐ 3, 5, 6 đều tắc như nhau nếu chưa có app ở môi trường Sandbox
(hoặc tương đương) của từng sàn.

👉 **Đề xuất: nộp hồ sơ đăng ký developer cả 3 sàn ngay hôm nay, nhắm thẳng vào
môi trường Sandbox/Test** — không nhắm vào app Live, vì app Live đòi shop đạt
điều kiện mà một shop mới không có được trong thời gian ngắn.

---

## 9. ❓ Những điểm cần team quyết trước khi code

| # | Câu hỏi | Vì sao cần quyết sớm |
|---|---|---|
| 1 | **Ai làm phần `users` / auth?** Hiện `auth.py` trả `"REPLACE_ME"`, chưa có bảng users | `seller_accounts.user_id` không tham chiếu vào đâu được. Nếu chưa có, em đề xuất tạm dùng `seller_account` độc lập, gắn user sau |
| 2 | **Giữ hay bỏ connector KiotViet đang chạy?** | Nó đang là nguồn dữ liệu thật duy nhất (46 hoá đơn). Đề xuất **giữ như một adapter thứ 4 loại "aggregator"** — không cản trở, lại có dữ liệu để demo trong lúc chờ duyệt app 3 sàn |
| 3 | **Ai đứng tên hồ sơ developer?** Cả 3 sàn cần CCCD hoặc giấy phép kinh doanh, **và thêm điều kiện shop đã thiết lập từ trước (Mục 0.1)** | Đây là việc **hành chính, không phải kỹ thuật**, và đang chặn deliverable #4 ở cả 3 sàn như nhau |
| 4 | **Có lưu thông tin người mua không?** | Em đề xuất **không**. Nếu team cần cho Customer Risk thì phải quyết riêng |
| 5 | **Khoá mã hoá token lưu ở đâu?** | Đề xuất biến môi trường `CREDENTIAL_ENCRYPTION_KEY`. Production thật nên dùng KMS/Vault |
| 6 | **Tần suất đồng bộ?** | Đề xuất: đơn 15-30 phút · tồn kho 1-4 giờ · sản phẩm hằng ngày. Cần khớp với rate limit từng sàn |

---

## 10. Deliverables — đối chiếu với yêu cầu

| Yêu cầu bàn giao | Trạng thái |
|---|---|
| Mô tả user flow tạo tài khoản + kết nối shop | ✅ Mục 4 — **đã code, chạy được trên `/seller/marketplace`** |
| Danh sách API, quyền truy cập, dữ liệu từng sàn | ✅ Mục 6 + 7 |
| Đề xuất database schema / data mapping | ✅ Mục 3 + 5 — **đã tạo 9 bảng thật (migration `0005`)** |
| Luồng Shopee chạy trên sandbox | ⚠️ Code xong (ShopeeAdapter + 42 test), **chờ khoá app Sandbox** — chặn bởi Mục 0.1 |
| Danh sách phần còn thiếu cho Lazada / TikTok | ✅ Mục 6.2, 6.3 + GĐ 5, 6 |
| Technical plan + danh sách dữ liệu để review | ✅ **Chính là tài liệu này** |

> Chi tiết đầy đủ những gì đã code, đã kiểm thử: xem
> [MARKETPLACE_CONNECT_HANDOVER.md](MARKETPLACE_CONNECT_HANDOVER.md).

### Phần còn thiếu để tích hợp Lazada & TikTok (tóm tắt)

**Lazada:** app + app_key/app_secret · thuật toán ký riêng (sắp xếp tham số, in hoa) ·
xử lý đa quốc gia (`region`) · ánh xạ trạng thái riêng · refresh token riêng

**TikTok Shop:** app trên Partner Center (**bắt buộc có shop đã kích hoạt**) ·
**bước lấy `shop_cipher`** · phân trang kiểu cursor · API sản phẩm dùng POST search
thay vì GET list · ánh xạ trạng thái riêng

---

## 11. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Không được duyệt app / duyệt lâu | 🔴 Cao | Nộp cả 3 sàn ngay hôm nay; giữ KiotViet làm nguồn dữ liệu dự phòng để vẫn demo được |
| **Shop chưa đạt điều kiện gọi API dù hồ sơ đã duyệt** (Mục 0.1) — chung cả 3 sàn | 🔴 Cao | Nhắm vào môi trường Sandbox/Test của từng sàn thay vì app Live; không đặt mục tiêu chạy trên shop thật trong khung thời gian đồ án |
| Token Shopee chỉ sống 4 giờ | 🟡 Vừa | Refresh chủ động ở 80% TTL + khoá phân tán chống refresh chồng chéo |
| Ánh xạ trạng thái sai | 🟡 Vừa | Lưu `raw_json` → chuẩn hoá lại được mà không gọi lại API |
| Chạm rate limit khi đồng bộ lần đầu | 🟡 Vừa | Đồng bộ tăng dần + lùi theo cấp số nhân + ghi `sync_runs` |
| Rò rỉ token | 🔴 Cao | Tách bảng riêng + mã hoá + schema API không bao giờ chứa trường token |
| Phụ thuộc phần auth chưa ai làm | 🟡 Vừa | Thiết kế `seller_accounts` đứng độc lập được, gắn `user_id` sau |
