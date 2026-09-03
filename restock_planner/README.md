# Smart Restock Planner

> "Với số vốn này, tháng này tôi nên nhập mặt hàng nào, bao nhiêu cái?"

Ra quyết định **số lượng nhập hàng** cho seller nhỏ từ ba tín hiệu:

| Tham số | Nguồn | Là dữ liệu gì |
|---|---|---|
| **SEASON** | Google Trends, 5 năm lịch sử tuần (SerpApi) | Thật — 262 điểm/keyword, 2021→nay |
| **TREND** | Google Shopping, giá & giá gạch của big brand (SerpApi) | Thật — bản đo có thời điểm, backend đọc từ cache |
| **SHOP** | Đơn hợp lệ 45 ngày + tồn kho của shop | Dữ liệu vận hành — không tự gán tốc độ bán |
| **MONEY** | Vốn + giá vốn/giá bán của chính shop | Dữ liệu shop + input của seller |

Kế hoạch hiện là kế hoạch nhập **toàn cửa hàng**, mỗi SKU chỉ xuất hiện một lần.
Không tự chia sang Shopee/Lazada/TikTok khi chưa có lịch sử đơn theo SKU đủ tin cậy.

Không có con số thị trường nào được bịa. Mùa vụ học từ lịch sử thật; mức sale của
big brand đo từ chênh lệch giá niêm yết ↔ giá bán đang hiển thị.

## Khác gì các feature đã có

| Feature | Trả lời câu hỏi |
|---|---|
| #08 Sentiment Alert | 1 SP: buzz + tồn kho → có cần restock gấp không? |
| #19 Market Intelligence | 1 SP: nên bán **giá** bao nhiêu? |
| **Restock Planner** | **Cả danh mục: chia vốn ra sao, nhập mỗi mã bao nhiêu cái?** |

Đây là feature duy nhất có **ràng buộc vốn** và **mùa vụ nhiều năm**.

## Dữ liệu phía shop

- Tốc độ bán của mỗi SKU = số lượng trong đơn hợp lệ 45 ngày gần nhất / 45.
- Đơn `pending`, `cancelled`, `returned` không tạo nhu cầu nhập.
- SKU không có đơn hợp lệ có tốc độ bán bằng 0; không dùng số sàn giả để lấp chỗ trống.
- Giá vốn, giá bán và tồn kho lấy nguyên từ catalog shop demo. Khi nối shop thật,
  ba trường này phải được thay bằng dữ liệu đồng bộ từ shop đó.

## Cách hoạt động

```
Google Trends (5y)  ──► season_model.py   ──► chỉ số mùa vụ theo tháng (12 giá trị/ngành)
Google Shopping     ──► competition.py    ──► hệ số cầu do big brand sale
Đơn hợp lệ + tồn kho ───────────────────────────────┐
Vốn + catalog shop  ────────────────────────────────┴─► backend/app/services/restock.py
                                                         └─► nhập mã nào, bao nhiêu cái
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

**Phân bổ vốn** (backend) — tính nhu cầu của từng SKU một lần, xếp theo biên gộp,
độ gấp của tồn kho và hai tín hiệu thị trường. Không có trần phần trăm tự đặt và
không ép tiêu hết ngân sách khi nhu cầu đã đủ. Lợi nhuận hiển thị là **lãi gộp
trước phí sàn và chi phí vận hành**, vì chưa có phân bổ SKU theo sàn đáng tin cậy.

## Chạy

```bash
pip install -r requirements.txt
echo SERPAPI_KEY=xxx > .env          # không commit, đã gitignore

python fetch_trends.py               # 9 call  — lịch sử 5 năm
python fetch_brand_sale.py           # 13 call — sale hiện tại của big brand
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
```

## Kết quả thật đo được (2026-08)

Mùa vụ — Thời trang đỉnh **T11 = 1.41**, T12 = 1.29, đáy **T8 = 0.79**; Mỹ phẩm
gần như phẳng (0.94–1.08). Đúng thực tế mùa Tết/đông ở VN.

Áp lực sale — tháng 8 các big brand không chạy chiến dịch lớn: pressure
0.003–0.028 → hệ số 0.99. Con số thấp là **kết quả đo thật**, không phải lỗi;
vào 11.11 / 12.12 nó sẽ tụt rõ.

Tác dụng lên kế hoạch — đổi tháng hoặc số ngày phủ hàng làm thay đổi nhu cầu;
tăng ngân sách chỉ làm tăng lượng nhập cho tới khi toàn bộ nhu cầu đã được đáp ứng.

## Giới hạn cần biết

- `COMPETITION_SENSITIVITY` (0.5) là **giả định chính sách**, không phải hệ số đo
  được — nó nói "cầu nhạy thế nào với sale của đối thủ". Chỉnh trong `config.py`
  theo kinh nghiệm thật của shop.
- Google Trends đo **lượt tìm kiếm**, không phải doanh số. Nó là proxy tốt cho
  mùa vụ nhưng không thay được số bán thật của shop.
- SerpApi Free = 250 lượt/tháng. Một lần chạy full tốn 31 lượt → cache là bắt buộc.
