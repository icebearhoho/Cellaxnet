"""Bản dịch tiếng Anh cho văn bản backend gửi ra giao diện.

Khoá là câu tiếng Việt, giống cách làm ở frontend (``lib/i18n-en.ts``) — xem
``app/core/i18n.py`` để biết vì sao.

Câu ghép động dùng chỗ trống có tên (``{giá}``, ``{trung_vị}``) chứ không phải
``{}`` thứ tự: tiếng Anh và tiếng Việt sắp xếp thành phần câu khác nhau, nên
bản dịch phải được phép đảo thứ tự các giá trị.
"""

from __future__ import annotations

EN: dict[str, str] = {
    # --- Gợi ý giá bán: nhãn ba mốc thị trường ---------------------------
    "Nhóm giá thấp": "Lower price band",
    "Trung vị thị trường": "Market median",
    "Nhóm giá cao": "Upper price band",
    "Dễ được chọn khi khách so giá, nhưng lợi nhuận mỗi đơn thấp nhất trong ba mức.":
        "Easy to pick when shoppers compare prices, but the thinnest profit per "
        "order of the three.",
    "Không nổi bật về giá theo hướng nào, đổi lại ít rủi ro bị đánh giá là đắt hay rẻ bất thường.":
        "It stands out in neither direction, which is also why it is unlikely to "
        "read as unusually expensive or suspiciously cheap.",
    "Lợi nhuận mỗi đơn cao nhất, nhưng cần lý do để khách chấp nhận trả hơn mặt bằng.":
        "The highest profit per order, but you need a reason for shoppers to pay "
        "above the going rate.",

    # --- Gợi ý giá bán: lời giải thích ------------------------------------
    "{giá} cao hơn nhiều so với {cơ_sở} — đề xuất giảm để cạnh tranh hơn.":
        "{giá} is well above {cơ_sở} — consider lowering it to compete.",
    "{giá} thấp hơn nhiều so với {cơ_sở} — có thể đang bán dưới giá, đề xuất tăng.":
        "{giá} is well below {cơ_sở} — you may be underpricing; consider raising it.",
    "{giá} đã sát {cơ_sở} — chỉ cần tinh chỉnh nhẹ.":
        "{giá} already sits close to {cơ_sở} — only a small adjustment is needed.",
    "Chưa có giá hiện tại — lấy {cơ_sở}.":
        "No current price given — using {cơ_sở}.",
    "trung vị {trung_vị} từ {số_mẫu} sản phẩm {phạm_vi}{nhà_bán} quan sát được trên {thị_trường}":
        "a median of {trung_vị} across {số_mẫu} {phạm_vi} listings{nhà_bán} "
        "observed on {thị_trường}",
    "trung vị danh mục {danh_mục} trên {số_mẫu} sản phẩm":
        "the {danh_mục} category median across {số_mẫu} products",
    " của {số_shop} nhà bán": " from {số_shop} shops",
    "Mức giá này {vị_trí}.": "This price {vị_trí}.",
    "đắt hơn {phần_trăm}% sản phẩm đang bán":
        "is pricier than {phần_trăm}% of what is on sale",
    "rẻ hơn {phần_trăm}% sản phẩm đang bán":
        "is cheaper than {phần_trăm}% of what is on sale",
    "{cơ_sở} thấp hơn giá vốn cho phép. Để giữ biên {biên}%{phí}, giá thấp nhất là {sàn} — nên giữ ở mức này thay vì chạy theo thị trường.":
        "{cơ_sở} is below what your unit cost allows. To hold a {biên}% margin{phí}, "
        "the lowest workable price is {sàn} — better to stay there than chase the market.",
    " sau phí {kênh} {phần_trăm}%": " after {kênh} fees of {phần_trăm}%",
    "Chưa có giá vốn nên mức tham khảo chỉ dựa trên thị trường — chưa kiểm tra được có đảm bảo lợi nhuận hay không.":
        "With no unit cost entered, the reference is based on the market alone — "
        "whether it leaves a profit is unverified.",

    # --- Gợi ý giá bán: các dòng "vì sao" --------------------------------
    "Giá hiện tại {giá} đang cao hơn trung vị thị trường {trung_vị}.":
        "The current price of {giá} sits above the market median of {trung_vị}.",
    "Giá hiện tại {giá} đang thấp hơn trung vị thị trường {trung_vị}.":
        "The current price of {giá} sits below the market median of {trung_vị}.",
    "Với giá vốn {giá_vốn} và mục tiêu biên {biên}% sau phí {kênh}, mức thấp nhất là {sàn}.":
        "With a unit cost of {giá_vốn} and a {biên}% margin target after {kênh} "
        "fees, the floor is {sàn}.",
    "Giá vốn cao nên mức tham khảo phải nhích lên so với mặt bằng thị trường để giữ được biên lợi nhuận.":
        "The unit cost is high, so the reference has to sit above the market to "
        "hold the margin.",
    "Mức tham khảo {giá} vẫn thấp hơn trung vị thị trường khoảng {phần_trăm}%.":
        "The reference of {giá} is still about {phần_trăm}% below the market median.",
    "Mức tham khảo {giá} cao hơn trung vị thị trường khoảng {phần_trăm}%.":
        "The reference of {giá} is about {phần_trăm}% above the market median.",
    "Biên lợi nhuận giảm từ {từ}% xuống {đến}%.":
        "The margin falls from {từ}% to {đến}%.",
    "Biên lợi nhuận tăng từ {từ}% lên {đến}%.":
        "The margin rises from {từ}% to {đến}%.",
    "Mức điều chỉnh khá lớn ({phần_trăm}%). Có thể thử {giá} trước để xem phản ứng của khách trước khi đi hết mức tham khảo.":
        "That is a large move ({phần_trăm}%). You could try {giá} first to see how "
        "shoppers react before going all the way.",
    "Không nên bán dưới {sàn} nếu muốn giữ biên {biên}% sau phí {kênh}.":
        "Do not sell below {sàn} if you want to hold a {biên}% margin after {kênh} fees.",

    "Với giá vốn {giá_vốn} và mục tiêu biên {biên}%, mức thấp nhất là {sàn}.":
        "With a unit cost of {giá_vốn} and a {biên}% margin target, the floor is {sàn}.",
    "Mức tham khảo {giá} ngang với trung vị thị trường.":
        "The reference of {giá} sits level with the market median.",
    "Giá vốn hiện còn thấp so với mặt bằng thị trường, nên mức tham khảo được quyết định bởi giá thị trường.":
        "The unit cost is still low against the market, so the reference is set by "
        "the market price rather than by cost.",
    "Mức thấp nhất {sàn} còn cao hơn cả sản phẩm đắt nhất quan sát được ({đắt_nhất}, chênh {chênh}%) — với giá vốn này sản phẩm nằm ngoài vùng giá của thị trường.":
        "The floor of {sàn} is above even the dearest listing observed "
        "({đắt_nhất}, a gap of {chênh}%) — at this unit cost the product sits "
        "outside the market's price range.",

    "Thời trang": "Fashion",
    "Mỹ phẩm": "Cosmetics",
    "Phụ kiện": "Accessories",

    # --- Rủi ro khách hàng ------------------------------------------------
    "Chưa cần can thiệp — tiếp tục chăm sóc như hiện tại.":
        "No action needed — carry on as you are.",
    "Chủ động gửi hướng dẫn chọn size và nhắc chính sách đổi trả trước khi giao.":
        "Send sizing guidance and a reminder of the returns policy before shipping.",

    # --- Phân tích đánh giá -----------------------------------------------
    "Có nhiều dấu hiệu bất thường nhưng thiếu chi tiết cụ thể.":
        "Several signals look off, and there is no concrete detail.",
    "Nội dung có chi tiết cụ thể hoặc cách diễn đạt cân bằng.":
        "The text carries concrete detail, or reads in a balanced way.",
    "Có dấu hiệu nội dung được tạo tự động":
        "Shows signs of machine-generated text",
    "Không có dấu hiệu giả mạo rõ ràng": "No clear signs of a fake review",
    "Tín hiệu còn lẫn lộn hoặc chủ yếu mô tả thông tin thực tế.":
        "The signals are mixed, or the review is mostly factual description.",
    "Cụm từ quá chung chung: {cụm_từ}": "Phrasing is too generic: {cụm_từ}",
    "Nội dung rất ngắn, không có chi tiết về sản phẩm":
        "Very short, with no detail about the product",
    "Dùng quá nhiều dấu chấm than": "Too many exclamation marks",
    "Lặp lại từ ngữ": "Repeated wording",
    "Không có chi tiết cụ thể về chất liệu, mùi hương hoặc giao hàng":
        "No concrete detail about material, scent or delivery",
    "Tín hiệu tích cực ({tích_cực}) nhiều hơn tín hiệu tiêu cực ({tiêu_cực}).":
        "Positive signals ({tích_cực}) outnumber negative ones ({tiêu_cực}).",
    "Đánh giá có nhiều tín hiệu tiêu cực ({tiêu_cực}).":
        "The review carries several negative signals ({tiêu_cực}).",
}
