# Smart Restock Planner

> "Với số vốn này, tháng này tôi nên nhập mặt hàng nào, bao nhiêu cái?"

Ra quyết định **số lượng nhập hàng** cho seller nhỏ từ ba tín hiệu:

| Tham số | Nguồn | Là dữ liệu gì |
|---|---|---|
| **SEASON** | Google Trends, 5 năm lịch sử tuần (SerpApi) | Thật — 262 điểm/keyword, 2021→nay |
| **TREND** | Google Shopping, giá & giá gạch của big brand (SerpApi) | Thật — đo sale đang chạy ngay lúc gọi |
| **MONEY** | Vốn + giá vốn/giá bán của chính shop | Thật — input của seller |

Kế hoạch chia vốn theo **4 kênh bán** (Shopee / Lazada / TikTok Shop / Cửa hàng
riêng), có trừ phí sàn. Xem [CHANNEL_LINK.md](CHANNEL_LINK.md) cho phần nối
tài khoản bán hàng thật.

Không có con số thị trường nào được bịa. Mùa vụ học từ lịch sử thật; mức sale của
big brand đo từ chênh lệch giá niêm yết ↔ giá bán đang hiển thị.

## Khác gì các feature đã có

| Feature | Trả lời câu hỏi |
|---|---|
| #08 Sentiment Alert | 1 SP: buzz + tồn kho → có cần restock gấp không? |
| #19 Market Intelligence | 1 SP: nên bán **giá** bao nhiêu? |
| **Restock Planner** | **Cả danh mục: chia vốn ra sao, nhập mỗi mã bao nhiêu cái?** |

Đây là feature duy nhất có **ràng buộc vốn** và **mùa vụ nhiều năm**.

## 4 kênh bán

Cùng một mã hàng chạy khác nhau trên từng nơi bán, nên kế hoạch chia vốn theo
**cặp (kênh × mã)** — hàng gửi vào kho sàn nào là gắn với sàn đó.

| Kênh | Phí mặc định | Đo được thị phần? |
|---|---|---|
| Shopee | 5% | ✅ Google Shopping trả về `source` = Shopee |
| Lazada | 4% | ✅ |
| TikTok Shop | 5% | ❌ **không đẩy hàng lên Google Shopping** |
| Cửa hàng riêng | 2% (phí cổng thanh toán) | ❌ đúng bản chất — là shop của mình |

**4 case** — hồ sơ bán hàng seller tự khai cho từng kênh:

| Case | Ý nghĩa | Hệ số cầu (mùa cao → mùa thấp) |
|---|---|---|
| Bán chạy, nhiều đơn | Kênh chủ lực, ít bị đối thủ hút khách | 2.48 → 1.39 |
| Bán ít, ít đơn | Đơn nhỏ giọt, dễ mất khách khi đối thủ sale | 0.38 → 0.24 |
| Theo mùa & trend | Bùng nổ đúng mùa rồi nguội hẳn | 1.42 → 0.33 |
| Không bán được | Chưa ra đơn — nhập thêm chỉ đọng vốn | 0 → 0 |

> ⚠️ **Số đơn của shop bạn trên mỗi kênh là do bạn khai, không phải đo được.**
> Shopee/Lazada/TikTok Shop đều khoá dữ liệu đơn hàng sau đăng nhập seller +
> app được duyệt. Cái đo được thật là **thị phần và giá trên từng sàn** qua
> trường `source` của Google Shopping.

## Cách hoạt động

```
Google Trends (5y)  ──► season_model.py   ──► chỉ số mùa vụ theo tháng (12 giá trị/ngành)
Google Shopping     ──► competition.py    ──► hệ số cầu do big brand sale
Google Shopping     ──► fetch_channel_market.py ──► thị phần & giá theo từng sàn (THẬT)
Case do seller khai ──► channels.py       ──► hệ số cầu riêng từng kênh
                                                    │
Vốn + catalog shop  ─────────────────────────────► backend/app/services/restock.py
                                                    └─► nhập mã nào, ở kênh nào, bao nhiêu cái
```

**Phân bổ vốn nằm ở backend, không có bản sao.** Trước đây folder này có
`planner.py` chép lại công thức; nó lệch khỏi backend ngay khi thêm kênh, nên
đã bỏ — folder này chỉ còn lo việc kéo dữ liệu và mô hình hoá tín hiệu.

**Mùa vụ** (`season_model.py`) — mỗi keyword được chuẩn hoá theo trung bình của
chính nó (Trends scale 0-100 riêng từng truy vấn), rồi lấy trung bình theo tháng
qua 5 năm. Trung bình nhiều năm là thứ tách "ngành này luôn đỉnh tháng 11" khỏi
"năm ngoái tháng 11 tình cờ cao".

**Áp lực big brand** (`competition.py`) — `pressure = tỉ lệ SP đang sale × độ sâu
giảm giá`. Nhân hai thành phần là có chủ đích: 1 món giảm 70% không phải chiến
dịch, nhưng nửa catalog giảm 30% thì có. Hết sale → lần fetch sau pressure tụt →
hệ số tự bò về 1.0, không ai phải sửa số bằng tay.

**Phân bổ vốn** (backend) — xếp hạng theo `ROI × độ gấp × hệ số cầu của kênh`,
với ROI tính trên **giá đã trừ phí sàn**. Trần 25%/SKU chia cho số kênh đang
cần hàng, để vốn dàn ra thay vì 4 dòng là hết tiền; lượt 2 bỏ trần tiêu nốt.
Hết tiền thì các dòng cuối bảng nhận 0 — đúng hành vi "hết vốn thì giảm bớt
mặt hàng".

## Chạy

```bash
pip install -r requirements.txt
echo SERPAPI_KEY=xxx > .env          # không commit, đã gitignore

python fetch_trends.py               # 9 call  — lịch sử 5 năm
python fetch_brand_sale.py           # 13 call — sale hiện tại của big brand
python fetch_channel_market.py       # 9 call  — thị phần & giá theo từng sàn
python prepare_demo_data.py          # gộp -> outputs/demo_data.json

# backend đọc bản sao này:
cp outputs/demo_data.json ../backend/app/data/restock_market.json
```

`demo_data.json` là bundle tự chứa: backend đọc nó nên **chạy được offline**,
không phụ thuộc quota. Gọi API live chỉ là bản nâng cấp phía trên, không bắt buộc.

Xem nhanh kết quả từng model:
```bash
python season_model.py    # chỉ số mùa vụ 12 tháng/ngành
python competition.py     # áp lực sale theo ngành
python channels.py        # 4 kênh + hệ số cầu của 4 case
```

## Kết quả thật đo được (2026-08)

Mùa vụ — Thời trang đỉnh **T11 = 1.41**, T12 = 1.29, đáy **T8 = 0.79**; Mỹ phẩm
gần như phẳng (0.94–1.08). Đúng thực tế mùa Tết/đông ở VN.

Áp lực sale — tháng 8 các big brand không chạy chiến dịch lớn: pressure
0.003–0.028 → hệ số 0.99. Con số thấp là **kết quả đo thật**, không phải lỗi;
vào 11.11 / 12.12 nó sẽ tụt rõ.

Tác dụng lên kế hoạch — cùng 50tr: T11 chia 24% vốn cho Thời trang (vào đỉnh),
T8 chia **0%** (vào đáy). Mùa vụ đổi được cả cơ cấu nhập hàng.

## Giới hạn cần biết

- `COMPETITION_SENSITIVITY` (0.5) là **giả định chính sách**, không phải hệ số đo
  được — nó nói "cầu nhạy thế nào với sale của đối thủ". Chỉnh trong `config.py`
  theo kinh nghiệm thật của shop.
- Google Trends đo **lượt tìm kiếm**, không phải doanh số. Nó là proxy tốt cho
  mùa vụ nhưng không thay được số bán thật của shop.
- SerpApi Free = 250 lượt/tháng. Một lần chạy full tốn 31 lượt → cache là bắt buộc.
