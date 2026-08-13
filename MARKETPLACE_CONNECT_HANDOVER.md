# Bàn giao — Kết nối bán hàng đa sàn

**Người thực hiện:** Phú · **Ngày:** 2026-08-13
**Kèm theo:** [MARKETPLACE_CONNECT_PLAN.md](MARKETPLACE_CONNECT_PLAN.md)

---

## Tóm tắt 30 giây

Technical plan đã xong và **phần nền đã code xong luôn** — không chờ team duyệt
mới bắt đầu, vì phần này không phụ thuộc vào quyết định nào còn treo.

| Deliverable yêu cầu | Trạng thái |
|---|---|
| Mô tả user flow tạo tài khoản bán hàng + kết nối shop | ✅ Xong (plan Mục 4) + **đã code chạy được** |
| Danh sách API, quyền truy cập, dữ liệu từng sàn | ✅ Xong (plan Mục 6 + 7) |
| Đề xuất database schema / data mapping | ✅ Xong (plan Mục 3 + 5) + **đã tạo bảng thật** |
| Luồng Shopee chạy trên sandbox | ⚠️ **Code xong, chờ khoá app** — xem Mục 4 |
| Danh sách phần còn thiếu cho Lazada / TikTok | ✅ Xong (Mục 5 dưới đây) |
| Technical plan gửi team review | ✅ Xong |

**Kiểm thử:** 99 test pass · mypy 120 file 0 lỗi · ruff sạch · eslint sạch ·
tsc sạch · alembic chạy trọn 5 migration trên DB trắng.

---

## 1. Kiến trúc — vì sao thêm Lazada/TikTok sau này rẻ

```
LỚP 1  DOMAIN      SellerAccount · ShopConnection · Product · Order · Stock
                   ↑ không có chữ "shopee" / "lazada" / "tiktok" nào
LỚP 2  NORMALIZER  trạng thái · tiền tệ · timezone · định danh · phân trang
LỚP 3  ADAPTER     ShopeeAdapter ✅ │ LazadaAdapter ⏳ │ TikTokAdapter ⏳
```

Toàn bộ luồng kết nối, vòng đồng bộ, tầng lưu trữ và giao diện viết dựa trên
`MarketplaceAdapter` — một protocol, không phải một sàn cụ thể. **Thêm Lazada
là thêm một file** thoả protocol đó rồi gọi `register()`, không sửa gì phía trên.

Mỗi adapter chịu trách nhiệm giấu đi:

| Thứ khác nhau giữa các sàn | Cách giấu |
|---|---|
| Ký số | Shopee ghép chuỗi rồi HMAC; Lazada sắp xếp tham số rồi in hoa; TikTok ký query đã sắp xếp |
| Phân trang | Shopee/Lazada theo offset, TikTok theo cursor → lộ ra ngoài đều là `Page(items, next_cursor)` |
| Định danh | `item_id/model_id` vs `item_id/sku_id` vs `product_id/sku_id` → gộp về `external_product_id` + `external_sku_id` |
| Trạng thái đơn | Mỗi sàn một bộ từ vựng → dịch về bộ chung |
| Dữ liệu phụ | TikTok bắt buộc có `shop_cipher` ở mọi call sau → `TokenBundle.extra` |

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
`shop_connections`. Nếu token nằm chung ở đó, chỉ cần một serializer cẩu thả là
rò token ra API — đây là kiểu rò rỉ phổ biến nhất ở loại tính năng này. Token
không thể rò ra từ một bảng mà không truy vấn nào đụng tới.

**Lưu `raw_json` song song với cột đã chuẩn hoá.** Lần tích hợp đầu tiên chắc
chắn sẽ ánh xạ sai ở đâu đó. Có raw thì **chuẩn hoá lại được mà không phải gọi
lại API sàn** — tránh chạm rate limit và tránh mất dữ liệu sàn đã xoá.

**Tiền lưu số nguyên đơn vị nhỏ nhất (đồng).** Số thực tích luỹ sai số ngay khi
đem cộng.

---

## 3. Đã xử lý những tình huống nào

Yêu cầu #4 nêu các trường hợp biên. Đã code và có test cho từng cái:

| Tình huống | Hệ thống làm gì |
|---|---|
| Người bán **từ chối** cấp quyền | Báo rõ, **không để lại kết nối rác** |
| `state` sai / hết hạn / **dùng lại** | Từ chối + ghi log cảnh báo — dùng lại là dấu hiệu callback bị đánh cắp |
| Access token sắp hết hạn | Tự làm mới ở **80% vòng đời**, không đợi tới lúc 401 |
| Refresh token chết | → `expired`, yêu cầu nối lại, **giữ nguyên dữ liệu đã đồng bộ** |
| Bị thu hồi quyền từ phía sàn | → `revoked` (khác `expired`: người bán đã chủ động, UI phải nói khác nhau) |
| Nối trùng shop | Cập nhật kết nối cũ, không tạo bản ghi thứ hai |
| Chạm rate limit | Nhận diện riêng, kèm thời gian chờ |
| **Shopee báo lỗi kèm HTTP 200** | Đọc lỗi trong body — chỉ xét status code sẽ lưu nhầm kết quả rỗng |
| Trạng thái đơn lạ | Ghi `unknown` + cảnh báo, **tuyệt đối không đoán bừa** |

Vì sao token Shopee cần cẩn thận: nó chỉ sống **~4 giờ**, ngắn nhất trong 3 sàn.
Thiết kế nào giả định token sống hết một lần đồng bộ sẽ hỏng ở đây.

---

## 4. ⚠️ Vướng mắc duy nhất — và nó không phải việc code, cũng không phải riêng Shopee

**Cả 3 sàn đã code đầy đủ luồng nhưng chưa kích hoạt được, vì chưa có khoá app —
và đây là một rào cản chung, lặp lại theo cùng một khuôn ở cả 3 sàn:**

> **Để một app đọc được dữ liệu shop qua API, shop đó phải đã ở một "trạng thái
> đã thiết lập" từ trước — không phải cứ có CCCD/giấy tờ là đủ điều kiện.**

| Sàn | Rào cản cụ thể | Đã tự tay thử chưa |
|---|---|---|
| **Shopee** | App dạng "Shopee Seller" (Live) yêu cầu shop đạt hạng **"Shop Yêu Thích"** hoặc **"Shopee Mall"** — hạng chỉ đạt được sau một thời gian bán hàng có doanh số/đánh giá, không có ngay lúc mới mở shop | ✅ Đã thử, xác nhận đúng |
| **TikTok Shop** | Bắt buộc **đã có shop kích hoạt** mới cho đăng ký Partner Center/developer | ✅ Đã ghi nhận từ trước |
| **Lazada** | Cùng mô hình Open Platform, phân loại hồ sơ theo ISV/Seller App — khả năng cao có rào cản dạng tương tự | ⚠️ Chưa tự tay kiểm chứng — cần thử thật |

Rào cản này **nặng hơn** bước duyệt hồ sơ danh tính (CCCD) — vì kể cả hồ sơ CCCD
được duyệt, app dạng Live vẫn bị chặn nếu shop chưa đạt điều kiện riêng của sàn.

**May mắn:** rào cản trên chỉ áp dụng cho app dạng **Live** (dùng cho shop thật).
Môi trường **Sandbox** — nơi sàn cấp sẵn tài khoản Test Seller/Test Buyer giả lập —
**không đòi hỏi shop đạt hạng nào**, chỉ cần qua bước duyệt hồ sơ developer cá
nhân. Đây vẫn là đường khả thi để hoàn thành deliverable #4 trong khung thời gian
đồ án — không nên đặt mục tiêu chạy trên shop thật, vì điều kiện đó ngoài tầm
kiểm soát của nhóm trong thời gian ngắn.

**Hệ thống xử lý việc này một cách trung thực:** sàn nào chưa có khoá thì nút
"Kết nối" **bị khoá** và ghi rõ thiếu biến nào — thay vì mở ra một luồng chắc
chắn không hoàn tất được.

```
Vào /seller/marketplace hiện tại sẽ thấy:
  Shopee       [Chưa cấu hình]  Thiếu SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY
  Lazada       [Chưa hỗ trợ]
  TikTok Shop  [Chưa hỗ trợ]
```

### Khi có khoá Sandbox rồi thì làm gì

Điền 2 dòng vào `backend/.env`, khởi động lại backend. **Không sửa code.**

```
SHOPEE_PARTNER_ID=...
SHOPEE_PARTNER_KEY=...
SHOPEE_SANDBOX=true
```

`SHOPEE_SANDBOX=true` trỏ sang `partner.test-stable.shopeemobile.com`. Chuyển
sang thật là **đổi config, không đổi code** — nhưng chạy trên shop thật vẫn cần
vượt qua rào cản "Shop Yêu Thích" nêu trên trước.

### Vì sao chữ ký vẫn tin được dù chưa gọi thật

Bộ test **tính lại HMAC bằng tay** theo đặc tả Shopee, độc lập với code, rồi so
sánh. Điểm quan trọng: một test so code với chính nó vẫn xanh y nguyên khi chuỗi
ký sai — mà chuỗi ký sai chính là lỗi dễ xảy ra nhất ở đây, và Shopee trả lỗi
chung chung không chỉ ra sai chỗ nào. Có cả test chứng minh **đảo thứ tự ghép
chuỗi sẽ ra chữ ký khác**.

---

## 5. Còn thiếu gì để làm Lazada và TikTok Shop

Phần **không phải làm lại**: toàn bộ lớp 1 và 2 — bảng, luồng kết nối, vòng đồng
bộ, giao diện, mã hoá token, chống giả mạo. Dùng lại nguyên vẹn.

### Lazada (~2 ngày)
- App + `app_key` / `app_secret` trên Lazada Open Platform ⚠️ *cần duyệt*
- Thuật toán ký riêng: sắp xếp tham số, nối chuỗi, **in hoa** kết quả
- Bảng ánh xạ trạng thái riêng
- Xử lý đa quốc gia (cột `region` đã có sẵn trong bảng)

### TikTok Shop (~2-3 ngày)
- App trên Partner Center ⚠️ *cần duyệt, và **bắt buộc đã có shop kích hoạt***
- **Bước lấy `shop_cipher`** — gọi sau khi có token, gắn vào **mọi** call sau đó.
  Đây là bước không sàn nào khác có; `TokenBundle.extra` đã thiết kế sẵn để đỡ
  chỗ này, nếu không thì tới lúc làm TikTok phải sửa lại cả tầng lưu token.
- Phân trang kiểu cursor
- API sản phẩm dùng `POST .../search` thay vì `GET list`

---

## 6. Câu hỏi cần team chốt

| # | Câu hỏi | Vì sao gấp |
|---|---|---|
| 1 | **Ai nộp hồ sơ developer Sandbox cả 3 sàn?** | Đây là **đường găng**. Code xong rồi, chỉ chờ khoá Sandbox — **không nhắm vào app Live**, vì app Live còn bị chặn thêm bởi rào cản "shop đã thiết lập" ở Mục 4, chung cả 3 sàn |
| 2 | **Ai làm phần `users`/auth?** | `auth.py` đang trả `"REPLACE_ME"`. Em đã để `seller_accounts.user_id` **nullable** nên không bị chặn, gắn user sau được |
| 3 | **Giữ connector KiotViet không?** | Đề xuất **giữ**. Nó đang là nguồn dữ liệu thật duy nhất (46 hoá đơn / 1,4 tỷ) và cho phép demo trong lúc chờ duyệt app. Hai đường chạy song song, không xung đột |
| 4 | **Có lưu thông tin người mua không?** | Em đề xuất **không** — hiện chỉ băm một chiều có muối. Cần cho Customer Risk thì phải quyết riêng |
| 5 | **Tần suất đồng bộ?** | Đề xuất đơn 15-30 phút · tồn kho 1-4 giờ · sản phẩm hằng ngày |

---

## 7. Thử ngay được gì hôm nay

Vào `http://localhost:3000/seller/marketplace`:

1. **Tạo tài khoản bán hàng** → hoạt động đầy đủ
2. **Xem danh sách shop** → cột Shop / Sàn / Trạng thái / Đồng bộ gần nhất — đúng
   yêu cầu #2
3. **Bấm Kết nối** → bị chặn kèm thông báo chỉ rõ thiếu khoá nào (đúng như thiết kế)

Kiểm chứng bằng API:

```bash
curl -X POST localhost:8000/api/v1/marketplace/accounts \
  -H 'Content-Type: application/json' -d '{"name":"Shop Test"}'

curl localhost:8000/api/v1/marketplace/platforms
curl localhost:8000/api/v1/marketplace/shops
```

---

## 8. Việc còn lại theo thứ tự

| Ưu tiên | Việc | Ai |
|---|---|---|
| 🔴 Ngay | Nộp hồ sơ developer Sandbox Shopee / Lazada / TikTok | Team quyết người đứng tên |
| 🟡 Sau khi có khoá | Điền `.env`, chạy thật trên sandbox Shopee | Phú — **0 dòng code** |
| 🟡 Song song | Chốt phần `users`/auth | Team |
| 🟢 Sau Shopee | LazadaAdapter | Phú — ~2 ngày |
| 🟢 Sau Shopee | TikTokAdapter | Phú — ~2-3 ngày |
| 🟢 Sau đó | Job đồng bộ định kỳ | Phú |
