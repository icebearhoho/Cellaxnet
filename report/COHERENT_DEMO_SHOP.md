# Coherent demo shop

## Mục tiêu

`Mây House Official` là một shop giả lập có quy mô và quan hệ dữ liệu giống một
shop bán lẻ đa kênh thật. Đây không phải dữ liệu lấy từ một doanh nghiệp thật.
Toàn bộ dữ liệu được sinh deterministic để demo, test và phát triển không phụ
thuộc API bên ngoài nhưng các feature vẫn kể cùng một câu chuyện kinh doanh.

Mốc snapshot cố định: `2026-08-12T16:00:00+00:00`.

## Quy mô snapshot

| Entity | Số lượng | Liên kết chính |
|---|---:|---|
| Shop | 1 | `shop-may-001` |
| Kênh bán | 4 | Shopee, TikTok Shop, Tiki, Website |
| Danh mục | 3 | Thời trang, Mỹ phẩm, Phụ kiện |
| Sản phẩm | 60 | 20 SKU mỗi danh mục |
| Khách hàng | 120 | Mỗi khách có lịch sử đơn và hành vi rủi ro |
| Đơn hàng | 540 | 180 ngày, 1–3 line item/đơn |
| KPI ngày | 90 | Revenue, order, session, conversion, AOV, cancel, return |
| Creator | 12 | 48 campaign gắn với product cụ thể |
| Review | >= 720 | Gắn đúng product, rating dùng lại ở storefront và audit |
| Journey replay | 10 | Event sequence dùng catalog chung để đề xuất |

## Quan hệ dữ liệu

```text
Mây House Official
├── products ── reviews
│   ├── stock + sales velocity
│   ├── competitor prices
│   └── creator campaigns
├── customers ── orders ── order items ── products
│   └── risk profile + last order + lifetime value
└── daily metrics (derived from orders)
    ├── dashboard KPIs
    ├── revenue timeseries
    └── alerts by stock / review / customer risk
```

Các field `sales_history`, `sales_prev`, `sales_curr`, `daily_sales` và
`stock_status` của product được tính lại từ đúng order line đã sinh. Customer
risk giữ `last_order_no`, `last_product_id`, `last_order_value_vnd` để drill-down
về đơn nguồn. Dashboard không có bộ mock độc lập: KPI ngày và revenue đều derive
từ order fact table.

## Feature sử dụng snapshot

| Feature | Dữ liệu dùng chung |
|---|---|
| Storefront / Product Detail | 60 product, stock và review thật trong snapshot |
| Checkout / Orders | Giá đọc từ catalog; stock mutable; khi DB chưa có đơn thật, màn quản trị hiển thị đơn demo có nhãn |
| Seller Dashboard | KPI, chart, alert, tỉnh thành và counts derive từ order/customer/product |
| Personal Shopper | Tìm và xếp hạng chính catalog; loại sản phẩm hết hàng |
| Recommender | Lịch sử đơn của customer, co-purchase, popularity 90 ngày và live stock |
| Customer Journey | Event intent và đề xuất sản phẩm từ catalog chung |
| Customer Risk | Customer profile có đơn cuối, sản phẩm cuối, LTV và kênh ưa thích |
| Dynamic Pricing / Market | Giá catalog, giá đối thủ, margin guard và sample theo category |
| Seller Coach | Audit listing, price, image, review và inventory của 60 SKU |
| Product Graph / Copilot | Product, sales velocity, decision và creator cùng ID |
| Creator Performance | Campaign gắn `product_id`, category và attributed sales |

## Demo data và dữ liệu production

- API trả `demo_mode: true` hoặc nhãn `demo_order` ở nơi có fallback mẫu.
- Không gọi snapshot này là dữ liệu realtime hay dữ liệu của một shop thật.
- Dữ liệu database của user luôn được ưu tiên cho các luồng ghi như checkout,
  order lifecycle và stock mutable.
- Khi marketplace sync hoàn chỉnh, adapter của Shopee/Lazada/TikTok Shop phải
  chuẩn hóa về cùng contract; feature không nên đọc payload riêng của từng sàn.

## Kiểm tra tính nhất quán

`backend/tests/test_coherent_demo_shop.py` khóa các invariant quan trọng:

- mọi order phải trỏ tới customer và product tồn tại;
- subtotal, discount, shipping và total phải cân;
- product velocity phải bằng tổng unit trong order line theo kỳ;
- customer risk phải drill-down được về last order;
- creator campaign phải trỏ đúng product/category;
- dashboard KPI phải bằng daily fact;
- storefront rating phải bằng trung bình review;
- pricing, recsys và seller coach phải dùng catalog chung.

Chạy riêng:

```powershell
cd backend
$env:DEMO_MODE="true"
..\.venv\Scripts\python.exe -m pytest tests/test_coherent_demo_shop.py -q
```
