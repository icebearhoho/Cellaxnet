/**
 * Bản dịch tiếng Anh, khoá là câu tiếng Việt trong giao diện.
 *
 * Xem `lib/i18n.tsx` để biết vì sao khoá là cả câu chứ không phải mã ngắn. Thêm
 * chuỗi mới bằng cách chép đúng nguyên văn tiếng Việt làm khoá — sai một dấu là
 * tra không ra, và khi tra không ra thì giao diện hiện lại tiếng Việt (an toàn,
 * nhưng dev console sẽ cảnh báo).
 *
 * KHÔNG thêm vào đây các từ khoá tra cứu ("chống nắng", "mặt nạ"…): chúng
 * dùng để khớp tên sản phẩm, dịch đi là việc khớp hỏng lặng lẽ.
 *
 * Ba tên danh mục thì CÓ trong bảng, nhưng chỉ để hiển thị. Chúng cũng là giá
 * trị `Category = Literal[...]` mà backend kiểm tra
 * (app/schemas/market.py), nên chỗ nào gửi danh mục lên API phải dùng giá trị
 * gốc — gửi kết quả của `t()` là request trả về 422.
 */


export const EN: Record<string, string> = {
  // --- Danh mục ------------------------------------------------------------
  //
  // Ba tên này cũng là giá trị `Category` mà backend kiểm tra. Dịch chúng ở
  // đây an toàn vì `t()` chỉ chạy lúc hiển thị — nhưng chỗ nào GỬI danh mục
  // lên API thì phải dùng giá trị gốc, tuyệt đối không dùng kết quả của t().
  "Thời trang": "Fashion",
  "Mỹ phẩm": "Cosmetics",
  "Phụ kiện": "Accessories",

  // --- Điều hướng: tên tính năng -------------------------------------------
  "Trải nghiệm khách hàng": "Customer Experience",
  "Gợi ý giá bán": "Dynamic Pricing",
  "Rủi ro khách hàng": "Customer Risk",
  "Nhóm khách hàng": "Customer Segments",
  "Ưu đãi giữ chân": "Retention Offers",
  "Nội dung sản phẩm": "Product Content",
  "Cải thiện cửa hàng": "Store Improvement",
  "Cảnh báo nhu cầu": "Demand Alerts",
  "Rủi ro vận chuyển": "Shipping Risk",
  "Kế hoạch nhập hàng": "Restock Plan",
  "Kết nối bán hàng": "Channel Connections",
  "Biến động sản phẩm": "Product Movement",
  "So sánh đối thủ": "Competitor Comparison",
  "Hiệu quả nhà sáng tạo": "Creator Performance",
  "Hỗ trợ quyết định": "Decision Support",
  "Quan hệ sản phẩm": "Product Relationships",
  "Hành trình khách": "Customer Journey",
  "Trợ lý vận hành": "Operations Assistant",
  "Trợ lý mua sắm": "Shopping Assistant",
  "Dành cho bạn": "For You",
  "Hôm nay cần làm gì": "Today's Priorities",
  "Đơn hàng": "Orders",
  "Cửa hàng": "Storefront",

  // --- Điều hướng: nhóm và nhãn --------------------------------------------
  "Điều hướng": "Navigation",
  "Tổng quan": "Overview",
  "Không gian làm việc": "Workspaces",
  "Mua sắm thông minh": "Smart shopping",
  "Trung tâm quyết định": "Decision center",
  "Tăng trưởng & ưu đãi": "Growth & promotions",
  "Đơn hàng & tồn kho": "Orders & inventory",
  "Nội dung & nhà sáng tạo": "Content & creators",
  "Luồng chính": "Primary",
  "Công cụ nâng cao": "Advanced tools",
  "Kết nối dữ liệu": "Data connections",
  "Tìm, khám phá và thử sản phẩm trong cùng một hành trình.":
    "Search, discover and try products in one journey.",
  "Phát hiện vấn đề, mô phỏng phương án và duyệt hành động.":
    "Detect issues, simulate options and approve actions.",
  "Tăng doanh thu mà vẫn bảo vệ biên lợi nhuận.":
    "Grow revenue while protecting margin.",
  "Hiểu phản hồi, hành vi và nhóm khách cần can thiệp.":
    "Understand feedback, behavior and customers needing attention.",
  "Theo dõi đơn, dự báo nhu cầu và nhập hàng đúng lúc.":
    "Track orders, forecast demand and restock on time.",
  "Sản xuất nội dung và đo hiệu quả creator.":
    "Create content and measure creator performance.",
  "Hợp nhất tín hiệu shop thành quyết định có thể mô phỏng, duyệt và theo dõi kết quả.":
    "Turn shop signals into decisions you can simulate, approve and measure.",
  "Danh mục sản phẩm": "Product categories",
  "công cụ trong cùng một luồng công việc": "tools in one workflow",
  "snapshot vận hành liên kết": "connected operations snapshot",
  "GMV ghi nhận / 30 ngày": "Recognized GMV / 30 days",
  "Khách hoạt động": "Active customers",
  "Sau bán hàng": "After-sales",
  "Tồn kho cần xử lý": "Inventory requiring action",
  "{recognized}/{total} đơn được ghi nhận": "{recognized}/{total} recognized orders",
  "{rate}% đã quay lại mua": "{rate}% purchased again",
  "{rate}% hoàn": "{rate}% returned",
  "{rate}% đơn bị huỷ": "{rate}% orders cancelled",
  "{count} hết hàng": "{count} stockouts",
  "{count} SKU sắp thiếu": "{count} low-stock SKUs",
  "{products} SKU · {customers} khách · {orders} đơn · {reviews} đánh giá.":
    "{products} SKUs · {customers} customers · {orders} orders · {reviews} reviews.",
  "Cập nhật {date}": "Updated {date}",
  "Đang đồng bộ dữ liệu": "Syncing data",
  "{ok}/{total} khu vực ổn định": "{ok}/{total} regions stable",
  "Tính năng dành cho người bán.": "A feature for sellers.",
  "Chuyển sang": "Switch to",
  "Phân tích": "Analytics",
  "Vận hành": "Operations",
  "Nội dung": "Content",
  "Bán hàng": "Sales",
  "Người bán": "Seller",
  "Người mua": "Shopper",
  "Cổng người bán": "Seller portal",
  "Dành cho người mua": "For shoppers",
  "Dành cho tài khoản người bán": "For seller accounts",
  "Quản trị viên": "Administrator",
  "Tìm tính năng…": "Search features…",
  "Giỏ hàng": "Cart",
  giỏ: "cart",
  tìm: "search",

  // --- Mô tả tính năng ------------------------------------------------------
  "Đọc toàn bộ đánh giá của một sản phẩm, đã phân loại theo cảm xúc.":
    "Read every review for one product, already sorted by sentiment.",
  "Đề xuất giá bán cạnh tranh dựa trên trung vị các sản phẩm cùng danh mục.":
    "Suggests a competitive price from the median of comparable listings.",
  "Khách có nguy cơ rời đi, hoàn trả, hối hận — và ai đang rủi ro chồng cần can thiệp gấp.":
    "Customers at risk of leaving, returning or regretting — and who needs attention first.",
  "Nhóm khách hàng theo hành vi mua sắm.": "Groups customers by shopping behaviour.",
  "Phát hiện khách 'thích nhưng do dự' từ tín hiệu hành vi và kích hoạt ưu đãi cá nhân hoá đúng lúc.":
    "Spots interested-but-hesitant shoppers from behaviour signals and triggers a personalised offer.",
  "thích nhưng do dự": "interested but hesitant",
  "Viết nội dung sản phẩm cho các sàn.": "Writes product copy for each marketplace.",
  "Kiểm tra cửa hàng và đề xuất cải thiện.": "Audits the store and suggests improvements.",
  "Kết hợp buzz mạng xã hội với tồn kho để cảnh báo sớm trước khi sản phẩm viral gây hết hàng.":
    "Combines social buzz with stock levels to warn before a viral product sells out.",
  "Cảnh báo sớm gián đoạn chuỗi cung ứng (bão, ùn tắc cảng) theo khu vực kho hàng.":
    "Early warning for supply-chain disruption (storms, port congestion) by warehouse region.",
  "Phân bổ ngân sách nhập hàng theo mùa vụ, nhu cầu và áp lực khuyến mãi trên thị trường.":
    "Allocates restock budget across season, demand and market discount pressure.",
  "Kết nối và theo dõi trạng thái đồng bộ dữ liệu từ các sàn bán hàng.":
    "Connect marketplaces and track their data-sync status.",
  "Giải thích vì sao doanh số thay đổi — bóc tách các yếu tố tác động (giá, khuyến mãi, traffic, tồn kho).":
    "Explains why sales moved — separating price, promotion and stock effects.",
  "Phân tích đối thủ & giá — so sánh vị thế và đề xuất mức giá tối ưu không phá sàn lợi nhuận.":
    "Competitor and price analysis — compares your position and suggests a price that protects margin.",
  "Đo hiệu quả KOL/KOC theo doanh số quy đổi, doanh số/1k view và tỷ lệ tương tác.":
    "Measures KOL/KOC performance by attributed sales, sales per 1k views and engagement rate.",
  "Học từ quyết định quá khứ để rút ra hành động nên lặp lại và thời điểm chạy ads tốt nhất.":
    "Learns from past decisions to show which actions to repeat, and when it is safe to run them.",
  "Quan hệ SKU/brand + sản phẩm tương tự": "SKU/brand relationships and similar products",
  "Xem lại hành trình và bước tiếp theo của khách.":
    "Review a customer's journey and their likely next step.",
  "Trợ lý vận hành cửa hàng.": "Store operations assistant.",
  "Digital Twin hợp nhất tín hiệu shop thành quyết định có thể mô phỏng, duyệt và theo dõi.":
    "Digital Twin turns shop signals into decisions you can simulate, approve and log.",
  "Mô phỏng, kiểm tra biên lợi nhuận và duyệt ưu đãi trước khi đưa lên Shopee hoặc TikTok Shop.":
    "Simulate, margin-check and approve an offer before it goes live on Shopee or TikTok Shop.",
  "Việc ưu tiên theo tác động doanh thu": "Tasks ranked by revenue impact",
  "Đơn hàng thật do khách đặt — xác nhận, giao hoặc hủy.":
    "Real customer orders — confirm, ship or cancel.",
  "Tìm sản phẩm theo nhu cầu và ngân sách.": "Find products by need and budget.",
  "Sản phẩm phù hợp với bạn.": "Products picked for you.",
  "Tải ảnh của bạn và thử trang phục bằng mô hình CatVTON.":
    "Upload your photo and try the outfit on with the CatVTON model.",
  "Khám phá sản phẩm, đọc đánh giá thật, nhận gợi ý theo nhu cầu và ngân sách.":
    "Browse products, read real reviews, and get suggestions for your needs and budget.",
  "Phân tích đánh giá, rủi ro khách hàng, gợi ý giá, hành trình khách và trợ lý vận hành.":
    "Review analysis, customer risk, price guidance, customer journeys and an operations assistant.",

  // --- Gợi ý giá bán --------------------------------------------------------
  "Giá tham khảo": "Reference price",
  "Xem giá tham khảo": "Show reference price",
  "Cập nhật giá tham khảo": "Update reference price",
  "Khoảng giá thị trường": "Market price range",
  "Trung vị danh mục": "Category median",
  "Nhập tên hoặc chọn từ danh sách": "Type a name, or pick from the list",
  "Nhập tên sản phẩm để bắt đầu định giá.": "Enter a product name to start pricing.",
  "Nhập giá vốn để biết mức giá tham khảo có đủ lợi nhuận hay không.":
    "Enter the unit cost to see whether the reference price leaves enough profit.",
  "Tài khoản chưa có quyền định giá. Hãy dùng tài khoản người bán hoặc quản trị viên.":
    "This account cannot use pricing. Sign in as a seller or an administrator.",
  "Đang lấy dữ liệu giá…": "Loading price data…",
  "Đang tải danh sách sản phẩm…": "Loading products…",
  "Không tìm thấy sản phẩm phù hợp.": "No matching product.",
  "Mỹ phẩm biên gộp cao nhưng chi phí marketing lớn":
    "Cosmetics carry a high gross margin, but marketing costs are heavy",
  "Biên gộp ngành thời trang bán lẻ thường 50–65%":
    "Fashion retail gross margin is typically 50-65%",
  "Phụ kiện thường có biên gộp 40–55%":
    "Accessories typically run a 40-55% gross margin",
  "Cửa hàng riêng": "Own store",
  "Kênh bán": "Sales channel",
  "Cần cập nhật": "Needs updating",
  "Đã cập nhật": "Up to date",

  // --- Rủi ro khách hàng ----------------------------------------------------
  "Chọn phân khúc khách hàng": "Choose a customer segment",
  "Chú thích phân khúc": "Segment legend",
  "Đang phân tích khách hàng…": "Analysing customers…",
  "Tìm khách hàng": "Search customers",
  "Tìm khách, sản phẩm, mã đơn…": "Search customers, products, order IDs…",
  "Tìm tên, SĐT, email, thành phố…": "Search name, phone, email, city…",

  // --- Nhóm khách hàng ------------------------------------------------------
  "Khách hàng tích cực": "Active Customers",
  "Có nguy cơ rời bỏ": "At Risk of Leaving",
  "Không còn hoạt động": "Inactive",
  "Nhóm còn tương tác nhiều nhất: có lượt thích, wishlist và lịch sử mua.":
    "The most engaged group: likes, wishlist items and a purchase history.",
  "Có lịch sử đăng bán hoặc bán được hàng, nhưng phần lớn đã lâu không quay lại.":
    "Has listed or sold before, but most have not returned in a long time.",
  "Vẫn còn hiện diện nhưng mức tương tác đang giảm.":
    "Still present, but their engagement is falling.",
  "Đã ngừng tương tác trong thời gian dài.":
    "Stopped engaging a long time ago.",
  "Cung cấp thẻ loyalty/VIP và gợi ý sản phẩm theo lịch sử mua hoặc yêu thích.":
    "Offer a loyalty/VIP card, and suggest products from what they bought or liked.",
  "Can thiệp sớm bằng thông báo nhắc nhớ và ưu đãi nhỏ có thời hạn ngắn.":
    "Step in early with a reminder notification and a small, short-dated offer.",
  "Chạy chiến dịch win-back qua email/SMS với ưu đãi quay lại đủ mạnh nhưng tần suất vừa phải.":
    "Run a win-back campaign by email/SMS: an offer strong enough to return for, at a modest frequency.",
  "Phân bổ gồm 85 khách hàng tích cực, 42 người bán, 44 khách hàng có nguy cơ rời bỏ và 129 khách hàng không còn hoạt động":
    "The split is 85 active customers, 42 sellers, 44 customers at risk of leaving and 129 inactive customers",

  // --- Trải nghiệm khách hàng ----------------------------------------------
  "Tìm trong nhóm": "Search in",
  "Danh sách": "List of",
  "Hành động đề xuất": "Recommended action",
  "Hướng dẫn dùng": "Show them how to use",
  "để rà soát lại gian hàng. Sau đó xin phản hồi để biết họ đang vướng ở đâu và giới thiệu đúng tính năng hỗ trợ tiếp theo.":
    "to review their store. Then ask for feedback to learn where they are stuck, and point them at the right feature next.",
  "Tìm trong đánh giá": "Search reviews",
  "Tìm trong đánh giá…": "Search reviews…",
  "Không lấy được đánh giá của sản phẩm này.": "Could not load reviews for this product.",
  "Tích cực": "Positive",
  "Trung tính": "Neutral",
  "Tiêu cực": "Negative",

  // --- Dùng chung -----------------------------------------------------------
  "Tất cả": "All",
  "Chưa có dữ liệu.": "No data yet.",

  // --- Digital Twin / Autopilot ---------------------------------------------
  "Cập nhật Digital Twin": "Refresh Digital Twin",
  "Cập nhật phân tích": "Refresh analysis",
  "Cập nhật phân tích để đọc tồn kho, khách hàng và review từ cùng một snapshot.":
    "Refresh the analysis to read inventory, customers and reviews from one snapshot.",
  "Trung tâm quyết định chỉ dùng dữ liệu có nguồn trong snapshot. LLM được phép giải thích, không được tự tạo chỉ số hoặc vượt qua bước seller duyệt.":
    "The decision center only uses sourced snapshot data. The LLM may explain it, but cannot invent metrics or bypass seller approval.",
  "Đang dựng snapshot…": "Building snapshot…",
  "So sánh tác động trước khi duyệt": "Compare the impact before approving",
  "Doanh thu có rủi ro": "Revenue at risk",
  "Doanh thu được bảo vệ": "Revenue protected",
  "Chi phí lãng phí tránh được": "Wasted spend avoided",
  "LTV có rủi ro": "Lifetime value at risk",
  "Khách cần giữ chân": "Customers to retain",
  "Khách được nhắm tới": "Customers targeted",
  "Review thấp / 30 ngày": "Low reviews / 30 days",
  "Review được ưu tiên": "Reviews prioritised",
  "Campaign cần rà soát": "Campaigns to review",
  "Số ngày tồn kho sau xử lý": "Days of stock after action",
  "Tỷ lệ tái kích hoạt dự kiến (%)": "Expected reactivation rate (%)",
  "SLA phản hồi (giờ)": "Response SLA (hours)",
  "Giữ chân khách": "Customer retention",
  "Phát hiện": "Detected",
  "Rủi ro": "Risk",
  cao: "high",
  "HÀNH ĐỘNG ĐỀ XUẤT": "RECOMMENDED ACTION",
  "Mô phỏng": "Simulate",
  "Đã mô phỏng": "Simulated",
  "Thực thi": "Execute",
  "Đã duyệt": "Approved",
  "Đã bỏ": "Dismissed",
  "Cần xem": "Needs review",
  "Hành động không hợp lệ.": "That action is not valid.",
  "Không thể phân tích dữ liệu vận hành.": "Could not analyse the operations data.",
  "Hãy chọn workspace đang hoạt động.": "Select an active workspace.",

  // --- Gợi ý sản phẩm (RecSys) ---------------------------------------------
  "Hồ sơ demo": "Demo profile",
  "Khách mẫu": "Sample customer",
  "Tín hiệu đang dùng": "Signals in use",
  "Hồ sơ": "Profile",
  "Khách đang hoạt động": "An active shopper",
  "Nguồn": "Source",
  "Catalog và lịch sử đơn": "Catalogue and order history",
  "AI đang hoạt động": "AI is running",
  "Gợi ý theo hồ sơ minh hoạ": "Suggestions for an illustrative profile",
  "Sản phẩm trong danh sách dành cho bạn": "Products in your For You list",
  "Sản phẩm mua cùng minh hoạ": "Illustrative frequently-bought-together",
  "Số gợi ý": "Suggestions",
  "Độ khớp TB": "Avg. match",
  "Đánh giá TB": "Avg. rating",
  "Sao trung bình các món gợi ý": "Average rating of suggested items",
  "Trung bình mức phù hợp với hồ sơ": "Average fit against the profile",
  "Kênh ưa thích": "Preferred channel",
  "Khoảng giá": "Price range",
  "Từ thấp nhất đến cao nhất": "Lowest to highest",
  "Đã mua": "Purchased",
  "Quan tâm": "Interested in",
  "Dữ liệu demo": "Demo data",
  "Dữ liệu mẫu để minh hoạ luồng cá nhân hoá; chưa lấy lịch sử thật của tài khoản.":
    "Sample data to illustrate the personalisation flow; no real account history yet.",
  "Dữ liệu mẫu; chưa có ma trận đồng mua thật từ cửa hàng.":
    "Sample data; no real co-purchase matrix from the store yet.",
  "lịch sử đơn Mây House": "order history at May House",
  "serum, dưỡng ẩm": "serum, moisturiser",
  "serum dưỡng ẩm": "moisturising serum",

  // --- Tồn kho và bán hàng --------------------------------------------------
  "Sản phẩm": "Product",
  "Tồn kho": "Stock",
  "Tồn hiện tại": "Current stock",
  "Số ngày còn hàng": "Days of stock left",
  "Bán/ngày": "Sold/day",
  "thấp": "low",
  "vừa": "medium",

  // --- Digital Twin: văn bản JSX -------------------------------------------
  "Từ tín hiệu thành một quyết định có thể thực thi":
    "From signals to one decision you can act on",
  "Các module phân tích chạy phía sau để cung cấp bằng chứng. Màn hình này chỉ giữ lại vấn đề cần quyết định, tác động và hành động tiếp theo.":
    "The analysis modules run behind this screen to supply the evidence. What stays here is the decision to make, its impact, and the next action.",
  "Chưa có snapshot quyết định": "No decision snapshot yet",
  "Cập nhật Digital Twin để đọc tồn kho, khách hàng và review từ cùng một snapshot.":
    "Refresh the Digital Twin to read stock, customers and reviews from one snapshot.",
  "Ollama giải thích · số liệu do rule tính":
    "Explained by Ollama · figures computed by rules",
  "Bằng chứng đủ để quyết định": "Evidence behind the decision",
  "Mô phỏng tác động": "Simulate the impact",
  "Duyệt hành động": "Approve the action",
  "Bỏ qua": "Dismiss",
  "Bỏ": "Reject",
  "Mở Voucher Booster": "Open Voucher Booster",
  "Digital Twin chỉ dùng dữ liệu có nguồn trong snapshot. LLM được phép giải thích, không được tự tạo chỉ số hoặc vượt qua bước seller duyệt.":
    "The Digital Twin only uses data sourced from the snapshot. The LLM may explain the numbers; it may not invent them.",

  // --- Gợi ý giá bán: văn bản JSX ------------------------------------------
  "Thiết lập định giá": "Pricing setup",
  "Kết quả định giá": "Pricing result",
  "Danh mục": "Category",
  "Tên sản phẩm": "Product name",
  "Có thể nhập sản phẩm mới hoặc chọn nhanh từ catalog của cửa hàng.":
    "Type a new product, or pick one from your store catalogue.",
  "Giá bán hiện tại": "Current price",
  "Nhập nếu sản phẩm đang bán, để biết nên tăng hay giảm bao nhiêu. Bỏ trống nếu đang định giá sản phẩm mới.":
    "Fill this in for a product already on sale, to see how far to move the price. Leave it empty when pricing something new.",
  "Giá vốn": "Unit cost",
  "Dùng để tính mức giá thấp nhất còn giữ được biên lợi nhuận sau phí sàn.":
    "Used to work out the lowest price that still holds your margin after marketplace fees.",
  "Biên lợi nhuận tối thiểu": "Minimum margin",
  "ngành": "industry",
  "Lợi nhuận sau giá vốn và phí sàn, tính trên giá bán. Chưa trừ quảng cáo, voucher, phí đóng gói, vận chuyển shop hỗ trợ hay hoàn hàng — hãy để biên cao hơn mức tối thiểu bạn cần.":
    "Profit after unit cost and marketplace fees, measured against the selling price. Ads, vouchers, packaging, subsidised shipping and returns are not deducted yet — so set the margin above the minimum you actually need.",
  "Kết quả mang tính tham khảo, chưa tự động thay đổi giá bán.":
    "The result is a reference. It does not change your price automatically.",
  "Đang đối chiếu mặt bằng giá": "Comparing against the market",
  "Không thể lấy giá tham khảo": "Could not get a reference price",
  "Thử lại": "Try again",
  "Chưa có kết quả": "No result yet",
  "Điền thông tin sản phẩm và chọn “Xem giá tham khảo”.":
    "Fill in the product details, then choose “Show reference price”.",
  "Chưa nhập giá vốn — mức này dựa trên thị trường, chưa kiểm tra được có đảm bảo lợi nhuận hay không.":
    "No unit cost entered — this figure comes from the market alone, so whether it leaves a profit is unverified.",
  "Nếu áp dụng": "If applied",
  "Hiện tại": "Current",
  "Tham khảo": "Reference",
  "Giá bán": "Price",
  "Lãi mỗi sản phẩm": "Profit per unit",
  "Biên lợi nhuận": "Margin",
  "Sau giá vốn và phí sàn, chưa tính quảng cáo, voucher hay chi phí vận hành.":
    "After unit cost and marketplace fees; ads, vouchers and operating costs are not included.",
  "Ba mốc giá của thị trường": "Three market price markers",
  "Điểm do dự: {điểm}": "Hesitation score: {điểm}",
  "Hạng #{hạng} toàn shop": "Rank #{hạng} in the store",
  "Cao điểm dự kiến: tháng {tháng}": "Expected peak: month {tháng}",
  "Tối đa {số_ngày} ngày": "Up to {số_ngày} days",
  "Còn {số_mã} mã ít ưu tiên hơn — không đưa lên màn hình chính.":
    "{số_mã} more lower-priority SKUs — not shown on the main screen.",
  "Kết quả cho \u201c{từ_khoá}\u201d": "Results for \u201c{từ_khoá}\u201d",
  "Dự kiến chậm thêm {số_ngày} ngày": "Expected delay: {số_ngày} more days",
  "Phù hợp {phần_trăm}%": "{phần_trăm}% match",
  "Workspace hiện tại": "Current workspace",
  "Doanh thu hôm nay": "Revenue today",
  "Mô tả ngắn, nên bổ sung 2-3 bullet về chất liệu + cách dùng.":
    "The description is short — add 2-3 bullets on material and how to use it.",
  "Đang cao hơn median category 8% — thử giảm 5-7% trong 7 ngày.":
    "Sitting 8% above the category median — try cutting 5-7% for a week.",
  "Ảnh chính thiếu sáng, hero subject chỉ chiếm 32% frame.":
    "The main photo is underexposed, and the subject fills only 32% of the frame.",
  "Reply rate 92%, nhưng phản hồi negative chậm (>24h).":
    "92% reply rate, but negative reviews wait over 24 hours for a response.",
  "SKU top bán stockout 3 lần trong 30 ngày — set reorder buffer.":
    "The top-selling SKU ran out 3 times in 30 days — set a reorder buffer.",
  "Đơn hàng hôm nay": "Orders today",
  "Tỷ lệ chuyển đổi": "Conversion rate",
  "Giá trị đơn trung bình": "Average order value",
  "{số_lượng} hiển thị": "{số_lượng} shown",
  // Cột thời gian trong bảng cảnh báo. Khoá "Bắt đầu" đã dùng cho nút bắt
  // đầu ("Start"), nên cột này cần khoá riêng để không đụng nghĩa.
  "Bắt đầu lúc": "Started",
  "Trạng thái: {trạng_thái}": "Status: {trạng_thái}",
  "Mức rủi ro: {phần_trăm}%": "Risk level: {phần_trăm}%",
  "{số_mẫu} sản phẩm tương tự": "{số_mẫu} comparable listings",
  "Lợi nhuận": "Profit",
  "Mức điều chỉnh khá lớn ({phần_trăm}%). Có thể thử {giá} trước để xem phản ứng của khách trước khi đi hết mức tham khảo.":
    "That is a large move ({phần_trăm}%). You could try {giá} first to see how shoppers react before going all the way.",
  "Không nên bán dưới {sàn} nếu muốn giữ biên {biên}% sau phí {kênh}.":
    "Do not sell below {sàn} if you want to hold a {biên}% margin after {kênh} fees.",
  "Không nên bán dưới {sàn} nếu muốn giữ biên {biên}%.":
    "Do not sell below {sàn} if you want to hold a {biên}% margin.",
  "Đề xuất": "Suggested",

  // --- Nhóm khách hàng: văn bản JSX ----------------------------------------
  "Phân khúc khách hàng": "Customer segments",
  "Phân bổ khách hàng": "Customer distribution",
  "Phân bổ rủi ro": "Risk distribution",
  "4 phân khúc": "4 segments",
  "Tổng quy mô": "Total size",
  "Chưa chọn phân khúc": "No segment selected",
  "Chọn để xem danh sách": "Select one to see the list",
  "Bạn muốn xem nhóm khách hàng nào?": "Which customer group do you want to see?",
  "Chọn một phân khúc để xem toàn bộ khách hàng thuộc nhóm, thông tin liên hệ, hành vi và lịch sử hoạt động.":
    "Pick a segment to see every customer in it, with their contact details, behaviour and activity history.",
  "Chọn một trong bốn nhóm phía trên để mở danh sách khách hàng tương ứng.":
    "Choose one of the four groups above to open its customer list.",
  "Khách được chia theo việc cần làm — mỗi nhóm một hành động.":
    "Customers are grouped by the work they need — one action per group.",
  "Ai cần can thiệp trước": "Who needs attention first",
  "Không có khách hàng nào.": "No customers.",
  "Không có khách nào khớp từ khoá này.": "No customer matches that search.",
  "Không tìm thấy khách hàng": "No customer found",
  "Thử tên, số điện thoại, email hoặc thành phố khác.":
    "Try a different name, phone number, email or city.",
  "Xem hành vi và lịch sử": "View behaviour and history",
  "Hành vi": "Behaviour",
  "Lịch sử hoạt động": "Activity history",
  "Hiển thị": "Showing",
  "khách hàng": "customers",
  "khách hàng đã phân nhóm": "customers segmented",
  "Khách hàng": "Customer",
  "Trước": "Previous",

  // --- Trải nghiệm khách hàng: văn bản JSX ---------------------------------
  "Chọn một sản phẩm để đọc toàn bộ đánh giá, đã phân loại sẵn theo cảm xúc.":
    "Pick a product to read all of its reviews, already sorted by sentiment.",
  "Sản phẩm này chưa có đánh giá nào.": "This product has no reviews yet.",
  "Không có đánh giá nào khớp bộ lọc này.": "No review matches this filter.",
  "Đang đọc đánh giá…": "Reading reviews…",
  "Khách gửi": "Submitted by",
  "Sản phẩm gần nhất": "Most recent product",

  // --- Thông tin liên hệ / biểu mẫu ----------------------------------------
  "Tên": "Name",
  "Số điện thoại": "Phone",
  "Thành phố": "City",
  "Mật khẩu": "Password",
  "Nhập lại mật khẩu": "Confirm password",
  "Kênh": "Channel",
  "Sau khi đăng ký, bạn có thể tạo workspace để kích hoạt tài khoản người bán.":
    "After signing up you can create a workspace to activate a seller account.",

  // --- Trang chủ và trang lỗi ----------------------------------------------
  "Cellaxnet · mua sắm thời trang & mỹ phẩm":
    "Cellaxnet · fashion & cosmetics shopping",
  "Phân tích →": "Analytics →",
  "Đơn của tôi": "My orders",
  "404 — không tìm thấy": "404 — not found",
  "Trang này không tồn tại": "This page does not exist",
  "Đường dẫn có thể đã thay đổi hoặc chưa sẵn sàng.":
    "The link may have changed, or the page is not ready yet.",
  "Bạn có thể quay lại trang chính để dùng các tính năng đang hoạt động.":
    "You can go back to the main page to use the features that are working.",
  "Về trang tổng quan": "Back to overview",
  "Tính năng chưa sẵn sàng": "Feature not ready yet",

  // --- Quan hệ sản phẩm / Biến động sản phẩm -------------------------------
  "Danh mục nào đang tạo doanh thu?": "Which categories are generating revenue?",
  "Sản phẩm nào thật sự nổi bật?": "Which products genuinely stand out?",
  "Khách còn lựa chọn tương tự nào?": "What similar options do shoppers have?",
  "Không cần tìm kiếm. Hệ thống tự chỉ ra danh mục và sản phẩm tạo doanh thu, rồi so sánh ngay với các lựa chọn tương tự trong cùng shop.":
    "No searching needed. The system surfaces the categories and products earning revenue, then compares them against similar options in the same store.",
  "Khi có dữ liệu, trang sẽ trả lời 3 câu hỏi":
    "Once there is data, this page answers three questions",
  "Danh mục dẫn đầu doanh thu": "Top categories by revenue",
  "Sản phẩm nổi bật": "Standout products",
  "Sản phẩm nổi bật của shop": "Standout products in this store",
  "Lựa chọn tương tự": "Similar options",
  "Chọn danh mục để lọc danh sách sản phẩm phía dưới.":
    "Pick a category to filter the product list below.",
  "Hiện hạng doanh thu, số bán, số đơn và so sánh với 30 ngày trước.":
    "Shows revenue rank, units sold, order count and a comparison against the previous 30 days.",
  "Hạng trong nhóm": "Rank in group",
  "So kỳ trước": "vs. previous period",
  "So với 30 ngày trước": "vs. the previous 30 days",
  "So với sản phẩm đang xem": "vs. the product you are viewing",
  "Đã bán / đơn": "Sold / orders",
  "Dẫn đầu:": "Leading:",
  "Top {hạng} danh mục": "Top {hạng} category",
  "Top {hạng} danh mục {danh_mục}": "Top {hạng} in {danh_mục}",
  "{phần_trăm}% tỷ trọng doanh thu shop": "{phần_trăm}% of store revenue",
  "{số_lượng} sản phẩm": "{số_lượng} units",
  "{số_đơn} đơn": "{số_đơn} orders",
  "{số_lượng} SP · {số_đơn} đơn · Xem so sánh":
    "{số_lượng} units · {số_đơn} orders · Compare",
  "Nguồn số liệu bán hàng": "Sales data source",
  "Nguồn số liệu: {sàn} · {cửa_hàng}": "Source: {sàn} · {cửa_hàng}",
  "Kỳ tính {từ_ngày}–{đến_ngày} · dữ liệu cập nhật đến {cập_nhật}.":
    "Period {từ_ngày}–{đến_ngày} · data current to {cập_nhật}.",
  "Tỷ trọng danh mục:": "Category share:",
  "Tăng/giảm doanh thu:": "Revenue change:",
  "Xem tất cả": "View all",
  "Chi tiết vì sao nổi bật": "Why it stands out",
  "Cách các con số được tính": "How these numbers are calculated",
  "Doanh thu = tổng thành tiền từng sản phẩm trong các đơn đã thanh toán, đang giao hoặc đã giao; không tính đơn chờ thanh toán, đã huỷ hay hoàn trả.":
    "Revenue is the sum of line totals across paid, shipping and delivered orders; unpaid, cancelled and returned orders are excluded.",
  "Xếp hạng theo thành tiền của các dòng hàng thuộc đơn hợp lệ trong kỳ 30 ngày, không dựa trên lượt xem.":
    "Ranked by line-item value from valid orders over a 30-day window, not by page views.",
  "Xếp theo tổng thành tiền dòng hàng của các đơn hợp lệ.":
    "Ordered by total line-item value across valid orders.",
  "doanh thu danh mục ÷ tổng doanh thu cửa hàng trong cùng 30 ngày × 100.":
    "category revenue ÷ total store revenue over the same 30 days × 100.",
  "Các biến thể có cùng mã sản phẩm được gộp thành một sản phẩm khi xếp hạng.":
    "Variants sharing a product code are merged into one product for ranking.",
  "Sản phẩm tương tự được chọn trong cùng cửa hàng và cùng danh mục, ưu tiên cùng loại sản phẩm, thương hiệu, từ khoá tên và khoảng giá gần nhau.":
    "Similar products are chosen from the same store and category, preferring the same product type, brand, name keywords and a nearby price range.",
  "Hệ thống không ghép một sản phẩm khác danh mục chỉ để lấp chỗ trống.":
    "The system will not pair a product from another category just to fill a slot.",
  "Tự ghép sản phẩm cùng shop, cùng danh mục theo thương hiệu, tên và mức giá.":
    "Automatically pairs products from the same store and category by brand, name and price level.",
  "Nguồn cửa hàng": "Store source",
  "Dữ liệu cửa hàng": "Store data",
  "Dữ liệu đồng bộ từ sàn": "Data synced from the marketplace",
  "Tìm cửa hàng…": "Search stores…",
  "Kiểm tra lại dữ liệu": "Recheck the data",
  "bản ghi sản phẩm": "product records",
  "dòng hàng": "line items",
  "đơn hàng": "orders",
  "Chưa có dữ liệu thật để xếp hạng": "No real data to rank yet",
  "Khi có sản phẩm và đơn hàng, xếp hạng sẽ xuất hiện tự động theo công thức được ghi rõ trên trang.":
    "Once there are products and orders, the ranking appears automatically using the formula stated on this page.",
  "Chưa có giá": "No price yet",
  "Chưa có kỳ trước": "No previous period",
  "Chưa có nguồn cửa hàng": "No store source",
  "Chưa có thương hiệu": "No brand",
  "Chưa có sản phẩm cùng danh mục để so sánh":
    "No product in the same category to compare against",
  "Chưa đồng bộ": "Not synced",
  "Sàn chưa trả ảnh sản phẩm": "The marketplace returned no product image",
  "sàn chưa trả": "not returned by the marketplace",
  "Không tìm thấy cửa hàng.": "No store found.",
  "Không tải được bảng so sánh sản phẩm.": "Could not load the product comparison.",
  "Không đọc được dữ liệu sản phẩm đã đồng bộ. Kiểm tra backend rồi thử lại.":
    "Could not read the synced product data. Check the backend and try again.",
  "Đang đọc dữ liệu sản phẩm và đơn hàng đã đồng bộ…":
    "Reading synced product and order data…",
  "Đang đối chiếu các sản phẩm cùng shop…": "Comparing products within the store…",

  // --- Kế hoạch nhập hàng ---------------------------------------------------
  "Thông tin lập kế hoạch": "Planning inputs",
  "Tính nhanh với số vốn hiện có: nên nhập nhóm hàng nào, bao nhiêu sản phẩm và dự kiến thu được gì.":
    "A quick calculation from the budget you have: which groups to restock, how many units, and what to expect back.",
  "Ngân sách nhập": "Restock budget",
  "Ngân sách còn lại": "Budget remaining",
  "Vốn": "Budget",
  "Vốn cần": "Budget needed",
  "Vốn cần dùng": "Budget to use",
  "Vốn còn thiếu": "Budget shortfall",
  "Chọn vốn": "Choose a budget",
  "Nhập số vốn lớn hơn 0": "Enter a budget above 0",
  "Tháng cần hàng": "Month stock is needed",
  "Số ngày muốn đủ hàng": "Days of cover wanted",
  "Chỉ xem ngành": "Filter by category",
  "Xoá lọc": "Clear filter",
  "Xem nên nhập gì": "See what to restock",
  "Cập nhật kế hoạch": "Update the plan",
  "Đang tính…": "Calculating…",
  "Ưu tiên theo ngành": "Priority by category",
  "Một dòng cho mỗi ngành để biết nên tăng, giữ hay nhập thận trọng.":
    "One line per category: increase, hold, or restock cautiously.",
  "Nên tăng nhập": "Increase restock",
  "Giữ mức hiện tại": "Hold current level",
  "Nhập thận trọng": "Restock cautiously",
  "Nhu cầu dự kiến cao": "Forecast demand is high",
  "Sản phẩm nên nhập trước": "Products to restock first",
  "Danh sách rút gọn theo mức ưu tiên. Mở rộng danh sách chỉ khi cần kiểm tra chi tiết.":
    "A short list in priority order. Expand it only when you need the detail.",
  "Chưa có sản phẩm cần nhập": "No product needs restocking",
  "Với ngân sách và thời gian hiện tại, hàng đang có là đủ.":
    "For the current budget and time window, existing stock is enough.",
  "Số sản phẩm nhập": "Units to restock",
  "Lãi gộp dự kiến": "Expected gross profit",
  "trước phí sàn và chi phí vận hành": "before marketplace fees and operating costs",
  "Sắp hết hàng": "Running out of stock",
  "Ưu tiên nhưng ngân sách chưa đủ để nhập đủ nhu cầu":
    "Prioritised, but the budget does not cover the full need",
  "vì ngân sách không đủ; hệ thống ưu tiên các mã có tác động cao hơn.":
    "because the budget falls short; the system favours the higher-impact SKUs.",
  "để đáp ứng toàn bộ nhu cầu dự báo": "to meet the full forecast demand",
  "không cần nhập dư để dùng hết vốn": "no need to over-order just to spend the budget",
  "đã phân bổ đủ": "fully allocated",
  "Kết quả cần nhớ": "Key takeaways",
  "Nên làm": "What to do",
  "Lý do": "Why",
  "Quy tắc": "Rule",
  "Nhận định": "Read",
  "Quan sát": "Observation",
  "Nhập": "Restock",
  "Số lượng": "Quantity",
  "trước khi nhập": "before restocking",
  "và bao nhiêu": "and how many",
  "không rõ lý do": "no stated reason",
  "chưa đủ dữ liệu": "not enough data",
  "Đang tải…": "Loading…",

  // --- Theo dõi đối thủ -----------------------------------------------------
  "Theo dõi đối thủ": "Competitor tracking",
  "Danh sách theo dõi": "Watchlist",
  "Chỉ cần nhập ba thông tin dưới đây. Bỏ trống ngành để xem toàn bộ cửa hàng.":
    "Just fill in the three fields below. Leave the category empty to see every store.",
  "Dán link cửa hàng Shopee. Mỗi lần thu thập lưu lại một mốc số liệu — xu hướng chỉ xuất hiện từ lần thu thập thứ hai.":
    "Paste a Shopee store link. Each collection saves one data point — a trend only appears from the second collection onwards.",
  "Chưa theo dõi cửa hàng nào. Dán link ở trên để bắt đầu thu thập.":
    "No store tracked yet. Paste a link above to start collecting.",
  "Chưa có dữ liệu — bấm “Thu thập ngay”.":
    "No data yet — choose “Collect now”.",
  "Bỏ theo dõi": "Stop tracking",
  "Mở trang cửa hàng": "Open the store page",
  "cần 2 lần thu thập": "needs two collections",
  "cửa hàng": "stores",
  "Số sản phẩm": "Products",
  "Đánh giá": "Rating",
  "Đã bán": "Sold",
  "Bán chạy nhất": "Best seller",
  "Bán trong kỳ": "Sold in period",
  "GMV ước tính": "Estimated GMV",
  "Khuyến mãi": "Promotions",
  "sản phẩm đang giảm": "products on discount",
  "Số liệu bán hàng của đối thủ": "Competitor sales figures",
  "Chưa có số liệu bán hàng cho shop này — Shopee chỉ trả số đã bán / GMV / khuyến mãi cho phiên đã đăng nhập. Cấu hình một nguồn ở phần hướng dẫn bên trên để bật 4 chỉ số đó.":
    "No sales figures for this store yet — Shopee only returns units sold, GMV and promotions to a signed-in session. Configure a source in the guide above to enable those four metrics.",
  "Shopee chỉ trả doanh thu / đã bán / bán chạy / khuyến mãi cho phiên đã đăng nhập. Kết nối tài khoản Shopee của bạn để bật 4 chỉ số đó.":
    "Shopee only returns revenue, units sold, best sellers and promotions to a signed-in session. Connect your Shopee account to enable those four metrics.",
  "Lấy được ngay, không cần kết nối gì: tên shop, follower, điểm đánh giá, số sản phẩm. Lazada hiện chặn mọi yêu cầu tự động nên chỉ theo dõi được cửa hàng Shopee.":
    "Available with no connection at all: store name, followers, rating and product count. Lazada currently blocks all automated requests, so only Shopee stores can be tracked.",
  "Đọc trước khi kết nối.": "Read this before connecting.",
  "Shopee cấm truy cập tự động. Tài khoản bạn kết nối có thể bị giới hạn hoặc khoá. Hãy dùng tài khoản phụ, không dùng tài khoản đang bán hàng.":
    "Shopee prohibits automated access. The account you connect may be limited or suspended. Use a secondary account, not the one you sell from.",
  "Mật khẩu Shopee của bạn không bao giờ được gửi tới AREA-303":
    "Your Shopee password is never sent to AREA-303",
  "Cách kết nối — chạy trên máy của bạn:": "How to connect — run this on your own machine:",
  "Kết nối được kiểm tra bằng một lần đọc thật trước khi lưu, nên nếu Shopee từ chối thì bạn biết ngay, không phải đợi tới lần thu thập sau.":
    "The connection is verified with a real read before it is saved, so if Shopee refuses you find out immediately rather than at the next collection.",
  "Ngắt kết nối sẽ": "Disconnecting will",
  "xoá hẳn": "permanently delete",
  "cookie phiên khỏi máy chủ, không phải chỉ ẩn đi.":
    "the session cookie from the server, not merely hide it.",
  "Đã kết nối": "Connected",
  "Chưa kết nối": "Not connected",
  "Hết hạn": "Expired",
  "Máy chủ chưa cấu hình": "Server not configured",
  "Kiểm tra hiệu quả": "Check effectiveness",
  "dữ liệu mua": "purchase data",
  "tích luỹ": "cumulative",
  "đi ngang": "flat",
  "bạn có thể dùng": "you can use",
  " (hiện tại)": " (current)",
  "Không chạy được thu thập.": "Could not run the collection.",
  "Không thêm được cửa hàng.": "Could not add the store.",
  "Không kết nối được máy chủ.": "Could not reach the server.",
  "Đang giữ kết quả gần nhất để bạn vẫn xem được.":
    "Keeping the most recent result so you can still read it.",

  // --- Hành trình khách -----------------------------------------------------
  "Phiên của bạn": "Your session",
  "Hành trình tham khảo": "Reference journeys",
  "Chọn một hành trình để xem lại.": "Pick a journey to review.",
  "Video hành trình": "Journey video",
  "Video tái hiện chuỗi hành động của phiên, không phải ghi màn hình thời gian thực.":
    "The video reproduces the session's sequence of actions; it is not a live screen recording.",
  "Phiên demo dựng trước": "Pre-built demo session",
  "Video demo dựng trước": "Pre-built demo video",
  "Chọn một hành trình mẫu để xem video demo replay.":
    "Pick a sample journey to watch the demo replay.",
  "Demo replay minh hoạ đúng chuỗi hành động của phiên, không phải ghi hình thời gian thực.":
    "The replay reproduces the exact sequence of actions in the session; it is not a live recording.",
  "Chưa có phiên nào.": "No sessions yet.",
  "Chưa có hoạt động. Hãy mở": "No activity yet. Open",
  "và xem vài sản phẩm.": "and view a few products.",
  "sẽ xuất hiện ở đây. Phiên này không ghi video.":
    "will appear here. This session was not recorded.",
  "Đang tải phiên…": "Loading sessions…",
  "Không tải được phiên. Hãy thử lại.": "Could not load the sessions. Please try again.",
  "Không tải được video. Kết quả bên dưới vẫn dùng được.":
    "Could not load the video. The results below still work.",
  "Không tải được kết quả. Hãy thử lại.": "Could not load the results. Please try again.",
  "Khả năng mua": "Purchase likelihood",
  "Khả năng cao": "High likelihood",
  "Khả năng thấp": "Low likelihood",
  "Mức quan tâm": "Interest level",
  "Danh mục quan tâm": "Categories of interest",
  "Sản phẩm phù hợp": "Matching products",
  "Bước tiếp theo": "Next step",
  "Nhận biết": "Awareness",
  "Cân nhắc": "Consideration",
  "Có ý định": "Intent",
  "Mua hàng": "Purchase",
  "Tìm kiếm": "Search",
  "Xem sản phẩm": "View product",
  "Đọc đánh giá": "Read reviews",
  "Thêm vào giỏ": "Add to cart",
  "Thời gian trên trang:": "Time on page:",
  "Thời gian đến khi mua:": "Time to purchase:",
  "Dừng trung bình/bước:": "Average dwell per step:",
  "Hoạt động trong": "Active for",
  "Chưa rõ": "Unclear",
  "có": "yes",
  "không": "no",

  // --- Voucher Booster ------------------------------------------------------
  "Một quyết định, có rule trước khi lên sàn":
    "One decision, checked against rules before it goes live",
  "1 · Mô phỏng": "1 · Simulate",
  "2 · Duyệt rule": "2 · Rule check",
  "3 · Lên sàn": "3 · Go live",
  "Dữ liệu tồn kho và biên lợi nhuận tạo kịch bản. Seller duyệt ngân sách, sau đó hệ thống mới chuyển sang bước kết nối hoặc xác nhận trên Seller Center.":
    "Stock and margin data build the scenario. The seller approves the budget, and only then does the system move on to connecting or confirming in Seller Center.",
  "Kịch bản nên chạy": "Recommended scenario",
  "Lập campaign": "Create campaign",
  "Hàng đợi thực thi": "Execution queue",
  "Chưa có campaign. Chọn kịch bản phía trên để tạo một bản mô phỏng có thể kiểm chứng.":
    "No campaign yet. Pick a scenario above to build a simulation you can check.",
  "Chưa tạo được kịch bản từ snapshot hiện tại.":
    "Could not build a scenario from the current snapshot.",
  "Chỉ campaign đã qua rule mới được duyệt.":
    "Only a campaign that passes the rules can be approved.",
  "Qua toàn bộ rule": "Passes every rule",
  "Chưa an toàn": "Not safe yet",
  "Duyệt": "Approve",
  "Đã từ chối": "Rejected",
  "Đang chạy": "Running",
  "Đã dừng": "Stopped",
  "Mức giảm": "Discount",
  "Giảm": "Off",
  "Ngân sách": "Budget",
  "Doanh thu dự kiến": "Expected revenue",
  "Lợi nhuận tăng thêm": "Incremental profit",
  "Đơn dự kiến": "Expected orders",
  "Cần kết nối shop": "Store connection required",
  "Sẵn sàng kết nối": "Ready to connect",
  "Cần xác nhận trên sàn": "Needs confirming on the marketplace",
  "Mở Seller Center": "Open Seller Center",
  "Phân tích lại": "Analyse again",
  "Hãy cập nhật dữ liệu vận hành rồi thử phân tích lại.":
    "Refresh the operations data, then try analysing again.",
  "Đang đọc tồn kho, biên lợi nhuận và chuẩn bị kịch bản an toàn…":
    "Reading stock and margins, and preparing a safe scenario…",
  "Không thể duyệt campaign.": "Could not approve the campaign.",
  "Không thể lập campaign.": "Could not create the campaign.",
  "Không thể tải Voucher Booster. Hãy kiểm tra workspace và backend.":
    "Could not load Voucher Booster. Check the workspace and the backend.",

  // --- Virtual Try-On -------------------------------------------------------
  "Phòng thử đồ AI": "AI fitting room",
  "Kết quả thử đồ AI": "AI try-on result",
  "Tải ảnh người và trang phục lên để thử trực tiếp ngay trong AREA-303.":
    "Upload a model photo and a garment photo to try it on directly in AREA-303.",
  "Ảnh người mẫu": "Model photo",
  "Ảnh trang phục": "Garment photo",
  "Bấm để tải ảnh": "Click to upload",
  "Chọn ảnh khác": "Choose a different photo",
  "Chọn đủ hai ảnh để bắt đầu": "Select both photos to begin",
  "JPG, PNG hoặc WebP · tối đa 10 MB": "JPG, PNG or WebP · 10 MB max",
  "Ảnh vượt quá 10 MB. Hãy chọn ảnh nhỏ hơn.":
    "That image is over 10 MB. Please choose a smaller one.",
  "Chụp chính diện, nền đơn giản": "Front-facing, plain background",
  "Đứng thẳng, thấy rõ toàn thân": "Standing straight, full body visible",
  "Loại trang phục": "Garment type",
  "Áo": "Top",
  "Quần / váy": "Bottom",
  "Đầm / toàn bộ": "Dress / full outfit",
  "Tạo ảnh thử đồ": "Generate try-on",
  "Tải ảnh kết quả": "Download the result",
  "Làm lại": "Start over",
  "Kết quả": "Result",
  "Ảnh kết quả sẽ xuất hiện tại đây": "The result will appear here",
  "AI đang thay trang phục": "The AI is swapping the garment",
  "Đang thử đồ · khoảng 15 giây": "Trying on · about 15 seconds",
  "Giữ trang này mở trong lúc xử lý": "Keep this page open while it processes",
  "Đang kiểm tra GPU": "Checking the GPU",
  "GPU sẵn sàng": "GPU ready",
  "Dịch vụ đang tắt": "Service is off",
  "Máy đang chạy chế độ chất lượng cao 768×1024, 50 bước. Kết quả phụ thuộc tư thế người mẫu và ảnh trang phục; ảnh chính diện cho kết quả ổn định nhất.":
    "Running in high-quality mode at 768×1024, 50 steps. Results depend on the model's pose and the garment photo; front-facing shots are the most reliable.",
  "Không kết nối được dịch vụ thử đồ local.":
    "Could not reach the local try-on service.",
  "Không thể tạo ảnh thử đồ.": "Could not generate the try-on image.",
  "Không thể xử lý yêu cầu.": "Could not process the request.",

  // --- Workspace / onboarding ----------------------------------------------
  "Thiết lập không gian bán hàng": "Set up your selling space",
  "Workspace của bạn": "Your workspace",
  "Chưa có workspace": "No workspace yet",
  "Tạo workspace": "Create workspace",
  "Tạo workspace khác": "Create another workspace",
  "Tạo workspace đầu tiên": "Create your first workspace",
  "Tạo workspace đầu tiên để kích hoạt vai trò người bán.":
    "Create your first workspace to activate the seller role.",
  "Workspace là nơi gom shop, sản phẩm, đơn hàng và thành viên của một đơn vị bán hàng. Dữ liệu của mỗi workspace được tách riêng.":
    "A workspace holds the stores, products, orders and members of one selling business. Each workspace's data is kept separate.",
  "Vào workspace": "Open workspace",
  "Tiến độ thiết lập": "Setup progress",
  "Kích hoạt tài khoản người bán.": "Activate the seller account.",
  "Tên shop hoặc doanh nghiệp": "Store or business name",
  "Tên đơn vị bán hàng": "Selling entity name",
  "Ví dụ: Minh Anh Fashion": "For example: Minh Anh Fashion",
  "Kết nối cửa hàng": "Connect a store",
  "Kết nối Shopee — sắp có": "Shopee connection — coming soon",
  "Shopee OAuth sẽ được gắn vào workspace ở bước tích hợp tiếp theo.":
    "Shopee OAuth will be attached to the workspace in the next integration step.",
  "Chủ sở hữu": "Owner",
  "Quản lý": "Manager",
  "Chỉ xem": "View only",
  "Hoạt động": "Active",
  "Tạm khóa": "Suspended",
  "Đã lưu trữ": "Archived",
  "Quản trị nền tảng": "Platform administration",
  "Đang tải...": "Loading…",

  // --- Trang chủ ------------------------------------------------------------
  "Nền tảng thương mại điện tử có AI": "An e-commerce platform with AI built in",
  "Cellaxnet · thương mại điện tử thời trang & mỹ phẩm":
    "Cellaxnet · fashion & cosmetics e-commerce",
  "Cellaxnet gom phân tích đánh giá, hành trình khách hàng, gợi ý giá và trợ lý vận hành vào một nơi — cho cả người mua và người bán.":
    "Cellaxnet brings review analysis, customer journeys, price guidance and an operations assistant into one place — for shoppers and sellers alike.",
  "Mọi thứ người bán cần, trong một cổng": "Everything a seller needs, in one portal",
  "Không phải một tá dashboard rời rạc — các tính năng dùng chung dữ liệu nên câu trả lời luôn khớp nhau.":
    "Not a dozen disconnected dashboards — the features share their data, so the answers always agree.",
  "không phải nhiều việc hơn.": "not more work.",
  "Bắt đầu miễn phí": "Start for free",
  "Tạo tài khoản": "Create an account",
  "Tạo tài khoản người mua trong vài giây, hoặc mở cửa hàng demo để xem sản phẩm, đánh giá và giỏ hàng hoạt động thật.":
    "Create a shopper account in seconds, or open the demo store to see products, reviews and the cart working for real.",
  "Thử toàn bộ hệ thống ngay": "Try the whole system now",
  "Xem cửa hàng": "View the store",
  "Xem cửa hàng demo": "View the demo store",
  "Phân tích đánh giá": "Review analysis",
  "Phân loại cảm xúc và phát hiện đánh giá giả ngay khi khách gửi, trước khi nó lên trang sản phẩm.":
    "Classifies sentiment and flags fake reviews the moment they are submitted, before they reach the product page.",
  "Hành trình khách hàng": "Customer journey",
  "Thời gian trên trang, bỏ giỏ hàng, thời điểm chốt đơn — dựng lại từ hành vi thật, không phải phỏng đoán.":
    "Time on page, cart abandonment, the moment of purchase — reconstructed from real behaviour, not guesswork.",
  "So sánh với trung vị ngành hàng và giá đối thủ để đề xuất mức giá không phá lợi nhuận.":
    "Compares against the category median and competitor prices to suggest a price that protects margin.",
  "Ai sắp rời đi, ai dễ hoàn hàng, ai sẽ hối tiếc sau mua — và ai đang rủi ro chồng cần xử lý gấp.":
    "Who is about to leave, who is likely to return an item, who will regret the purchase — and who carries several risks at once and needs attention now.",
  "Phân nhóm hành vi mua sắm bằng mô hình đã huấn luyện, không phải chia theo cảm tính.":
    "Groups shopping behaviour with a trained model, not by gut feel.",
  "Hỏi bằng giọng nói hoặc chữ, nhận câu trả lời tổng hợp từ dữ liệu giá, doanh số, tồn kho và KOL.":
    "Ask by voice or text and get an answer drawn together from price, sales, stock and creator data.",
  "tính năng đang chạy": "features running",
  "sàn thương mại": "marketplaces",
  "tỉnh thành theo dõi": "provinces tracked",

  // --- Kết nối bán hàng -----------------------------------------------------
  "Kết nối tài khoản bán hàng": "Connect a selling account",
  "Sàn": "Marketplace",
  "Trạng thái": "Status",
  "Nối qua": "Connected via",
  "Chưa nối": "Not connected",
  "Ngắt": "Disconnect",
  "Ngắt kết nối": "Disconnect",
  "Đã ngắt": "Disconnected",
  "Đã ngắt kết nối và xoá token": "Disconnected, and the token was deleted",
  "Chờ kết nối": "Awaiting connection",
  "Sẵn sàng — bấm Kết nối": "Ready — choose Connect",
  "Chưa cấu hình": "Not configured",
  "Chưa khai khoá API của cửa hàng": "Store API key not entered",
  "Khoá API lấy trong": "Get the API key from",
  "Tài liệu API": "API documentation",
  "Lần kết nối gần nhất thất bại": "The last connection attempt failed",
  "Bấm “Lấy đơn hàng” để kéo đơn của các sàn về":
    "Choose “Fetch orders” to pull orders in from the marketplaces",
  "Đã kết nối KiotViet — bấm “Lấy đơn hàng” để kéo đơn về.":
    "KiotViet is connected — choose “Fetch orders” to pull the orders in.",
  "Mang về đơn từ:": "Brings in orders from:",
  "Đơn": "Orders",
  "Đơn/ngày": "Orders/day",
  "Cập nhật": "Update",
  "Cần xử lý": "Needs attention",
  "Đang chờ": "Pending",
  "Đang xử lý": "Processing",
  "Lỗi": "Error",
  "Lưu ý": "Note",

  // --- Workspace: thành viên ------------------------------------------------
  "Quản lý workspace": "Manage workspace",
  "Chuyển workspace": "Switch workspace",
  "Không gian bán hàng": "Selling space",
  "Thành viên": "Members",
  "Thành viên workspace": "Workspace members",
  "Thêm thành viên": "Add a member",
  "Xóa thành viên": "Remove member",
  "Email thành viên": "Member email",
  "Vai trò thành viên mới": "New member role",
  "Vai trò của bạn": "Your role",
  "Quyền truy cập chỉ áp dụng trong workspace này.":
    "Access applies only within this workspace.",
  "Connector cần gửi header X-Workspace-ID; API sẽ tự kiểm tra thành viên và tenant.":
    "Connectors must send the X-Workspace-ID header; the API checks membership and tenant itself.",
  "Chưa kết nối với workspace này.": "Not connected to this workspace.",
  "Mở dashboard quản trị": "Open the admin dashboard",
  "Kiểm tra cửa hàng": "Audit the store",
  "Tạo nội dung sản phẩm": "Write product content",
  "Đang mở workspace của bạn…": "Opening your workspace…",
  "Đang tải dữ liệu workspace...": "Loading workspace data…",
  "Máy chủ miễn phí có thể cần vài giây để khởi động. Bạn không cần tải lại trang.":
    "A free server can take a few seconds to wake up. There is no need to reload the page.",

  // --- So sánh đối thủ ------------------------------------------------------
  "Sản phẩm của bạn & đối thủ": "Your product & the competitor",
  "Sản phẩm của bạn": "Your product",
  "Tên đối thủ": "Competitor name",
  "Giá bán của bạn (₫)": "Your price (₫)",
  "Giá vốn (₫)": "Unit cost (₫)",
  "Giá đối thủ (₫)": "Competitor price (₫)",
  "Giảm giá (%)": "Discount (%)",
  "Biên tối thiểu (%)": "Minimum margin (%)",
  "So sánh giá với đối thủ và đề xuất mức giá tối ưu, không phá sàn lợi nhuận.":
    "Compares your price against a competitor and suggests a price that does not break your margin floor.",
  "Bấm Phân tích để so sánh giá với đối thủ.":
    "Choose Analyse to compare your price against the competitor.",
  "Rẻ hơn đối thủ": "Cheaper than the competitor",
  "Ngang giá": "Price parity",
  "Đắt hơn đối thủ": "Pricier than the competitor",
  "Giữ nguyên giá": "Hold the price",
  "Bám sát giá đối thủ": "Match the competitor",
  "Hạ giá thấp hơn": "Undercut them",
  "Khác biệt hoá, không đua giá": "Differentiate instead of competing on price",
  "Tăng về giá sàn để bảo vệ lợi nhuận": "Raise towards the floor to protect margin",
  "Giá sàn": "Price floor",
  "Biên tại giá đề xuất": "Margin at the suggested price",
  "Giá thực tế của đối thủ": "Competitor's effective price",
  "Không lấy được kết quả. Kiểm tra kết nối backend rồi thử lại.":
    "Could not get a result. Check the backend connection and try again.",

  // --- Trợ lý mua sắm -------------------------------------------------------
  "Trợ lý mua sắm · sẵn sàng": "Shopping assistant · ready",
  "Chào bạn! Mình có thể gợi ý quà, son, đồ đi làm hoặc sản phẩm chăm sóc da theo phong cách và ngân sách của bạn. Hôm nay bạn đang tìm gì?":
    "Hello! I can suggest gifts, lipstick, workwear or skincare to suit your style and budget. What are you looking for today?",
  "Hỏi gì đó — ví dụ: son cho da ngăm dưới 350k… hoặc bấm mic và nói \"Hey Cellaxnet\"":
    "Ask me something — say, lipstick for deeper skin tones under 350k… or tap the mic and say \"Hey Cellaxnet\"",
  "Gợi ý nhanh": "Quick suggestions",
  "Gợi ý theo hồ sơ hiện tại": "Suggestions for the current profile",
  "Gợi ý được tạo từ catalog hiện tại. Hãy kiểm tra giá và thông tin trên trang sản phẩm trước khi mua.":
    "Suggestions come from the current catalogue. Check the price and details on the product page before buying.",
  "Nhập thông tin sản phẩm rồi bấm “Tạo 3 phiên bản”.":
    "Fill in the product details, then choose “Generate 3 versions”.",
  "Sản phẩm thường được mua cùng": "Frequently bought together",
  "Theo dữ liệu backend hiện tại": "From the current backend data",
  "Tính từ snapshot sản phẩm, đơn hàng, đánh giá và tồn kho của workspace hiện tại.":
    "Computed from this workspace's snapshot of products, orders, reviews and stock.",
  "Xếp hạng từ lịch sử đồng mua trong dữ liệu cửa hàng.":
    "Ranked from co-purchase history in the store data.",
  "Xếp hạng từ tín hiệu phiên hiện tại và catalog backend.":
    "Ranked from the current session's signals and the backend catalogue.",
  "Đang nạp dữ liệu cửa hàng…": "Loading store data…",
  "Đang nạp gợi ý sản phẩm…": "Loading product suggestions…",
  "Catalog đang hoạt động": "Catalogue is live",
  "Nguồn gợi ý": "Suggestion source",
  "Nhu cầu, ngân sách và đánh giá": "Needs, budget and reviews",
  "Gợi ý được tạo từ danh mục mẫu. Hãy kiểm tra giá và thông tin trên trang sản phẩm trước khi mua.":
    "Suggestions come from a sample catalogue. Check the price and details on the product page before buying.",
  "Không lấy được gợi ý. Kiểm tra kết nối backend rồi thử lại.":
    "Could not get suggestions. Check the backend connection and try again.",
  "Gửi": "Send",
  "quà": "gift",
  "môi": "lips",
  "làm": "work",
  "học": "study",
  "công sở": "office",
  "sinh nhật": "birthday",
  "đi chơi": "going out",
  "Thời trang, mỹ phẩm, phụ kiện": "Fashion, cosmetics, accessories",
  "Sàn tham khảo": "Reference marketplace",
  "Dữ liệu mẫu gần đây": "Recent sample data",
  "Chưa xác định": "Not determined",
  " tỷ": " bn",
  "dùng số này thay cho phần bạn tự khai.": "uses this figure instead of the one you entered.",

  // --- Hỗ trợ quyết định ----------------------------------------------------
  "Học từ quyết định quá khứ": "Learn from past decisions",
  "Đối chiếu các quyết định đã thực hiện để rút ra hành động nên lặp lại.":
    "Compares the decisions already made to show which actions are worth repeating.",
  "Mô tả quyết định": "Describe the decision",
  "Thêm quyết định": "Add a decision",
  "Quyết định tốt nhất": "Best decision",
  "Tháng chạy ads tốt nhất": "Best month to run ads",
  "Tháng (nếu ads)": "Month (if running ads)",
  "Bối cảnh": "Context",
  "Lý giải": "Reasoning",
  "Chuẩn bị chiến dịch cho mùa cao điểm quý 4":
    "Prepare a campaign for the Q4 peak season",
  "Chạy ads TikTok tháng 11": "Run TikTok ads in November",
  "Giảm giá 10% dòng bán chậm": "Cut 10% off the slow-moving line",

  // --- Biến động sản phẩm ---------------------------------------------------
  "Giải thích vì sao doanh số thay đổi giữa hai kỳ.":
    "Explains why sales moved between two periods.",
  "Bấm Phân tích để xem vì sao doanh số thay đổi.":
    "Choose Analyse to see why sales moved.",
  "Phân tích nguyên nhân": "Analyse the cause",
  "Yếu tố tác động": "Contributing factors",
  "Sản phẩm & tín hiệu doanh số": "Product & sales signals",
  "Doanh số kỳ này": "Sales this period",
  "Doanh số kỳ trước": "Sales last period",
  "Thay đổi giá (%)": "Price change (%)",
  "Thay đổi traffic (%)": "Traffic change (%)",
  "Tăng doanh số (%)": "Sales change (%)",
  "Hiệu quả khuyến mãi:": "Promotion effectiveness:",
  "Đang có khuyến mãi": "Promotion running",
  "Đối thủ đang khuyến mãi": "A competitor is running a promotion",
  "Tăng": "Up",
  "Đi ngang": "Flat",
  "Chỉ số": "Metric",
  "Giá trị": "Value",

  // --- Cảnh báo nhu cầu / tồn kho -------------------------------------------
  "Kết hợp buzz mạng xã hội với tồn kho để cảnh báo sớm.":
    "Combines social buzz with stock levels for an early warning.",
  "Bấm Kiểm tra để xem cảnh báo tồn kho.": "Choose Check to see stock alerts.",
  "Sản phẩm + tín hiệu mạng xã hội": "Product + social signals",
  "Lượt nhắc đến MXH (7 ngày)": "Social mentions (7 days)",
  "Sentiment trung bình": "Average sentiment",
  "Mức độ quan tâm": "Interest level",
  "Tồn kho hiện tại": "Current stock",
  "Bán TB / ngày": "Average sold/day",
  "Tỷ lệ bán hết (%)": "Sell-through rate (%)",
  "Đề xuất nhập thêm:": "Suggested restock:",
  "Cảnh báo": "Alert",
  "Khẩn cấp": "Urgent",
  "Theo dõi": "Watch",
  "Bình thường": "Normal",
  "Đủ hàng": "In stock",
  "Còn đủ hàng": "Stock is sufficient",
  "Sắp hết": "Running low",
  "Hết hàng": "Out of stock",
  "Thấp": "Low",
  "Trung bình": "Medium",
  "sản phẩm": "products",
  "Không lấy được cảnh báo. Kiểm tra kết nối backend rồi thử lại.":
    "Could not get the alerts. Check the backend connection and try again.",

  // --- Nội dung sản phẩm ----------------------------------------------------
  "Nhập thông tin một lần để tạo nội dung phù hợp cho từng sàn.":
    "Enter the details once to generate copy suited to each marketplace.",
  "So sánh nội dung và hiệu quả dự kiến trên 3 sàn":
    "Compare the copy and its expected performance across three marketplaces",
  "3 sàn": "3 marketplaces",
  "Thông tin sản phẩm": "Product details",
  "Đặc điểm nổi bật": "Key features",
  "Mỗi dòng 1 đặc điểm": "One feature per line",
  "Giá": "Price",
  "Biên lợi nhuận (%)": "Margin (%)",
  "Tạo 3 phiên bản": "Generate 3 versions",
  "Đang tạo…": "Generating…",
  "Nội dung đã tạo": "Generated copy",
  "Sàn đang xem": "Marketplace shown",
  "CTR ước tính (quy tắc)": "Estimated CTR (rule-based)",
  "Cần duyệt trước khi đăng": "Review before publishing",
  "Quảng cáo": "Advertising",
  "Không tạo được nội dung. Kiểm tra kết nối backend rồi thử lại.":
    "Could not generate the copy. Check the backend connection and try again.",

  // --- Gian hàng người mua --------------------------------------------------
  "Cửa hàng Cellaxnet": "Cellaxnet store",
  "Thời trang, mỹ phẩm và phụ kiện.": "Fashion, cosmetics and accessories.",
  "Trợ lý mua sắm thông minh cho thời trang & mỹ phẩm — cứ nói bạn cần gì, Cellaxnet gợi ý ngay.":
    "A smart shopping assistant for fashion & cosmetics — tell it what you need and Cellaxnet suggests something.",
  "Tìm sản phẩm, thương hiệu…": "Search products, brands…",
  "Tìm": "Search",
  "Tìm đúng món": "Find the right item",
  "Danh mục hàng": "Categories",
  "Khám phá": "Explore",
  "Vào cửa hàng": "Enter the store",
  "Về cửa hàng": "Back to the store",
  "Tiếp tục mua sắm": "Continue shopping",
  "Vào cửa hàng chọn vài món nhé!": "Head to the store and pick a few things.",
  "Không tìm thấy sản phẩm": "No product found",
  "Không có sản phẩm phù hợp": "No matching product",
  "Thử từ khoá khác hoặc chọn danh mục khác nhé.":
    "Try a different keyword, or pick another category.",
  "Sản phẩm đã hết hàng": "This product is out of stock",
  "Sản phẩm tương tự": "Similar products",
  "Gợi ý dành riêng cho bạn": "Picked for you",
  "Thư viện ảnh sản phẩm": "Product image gallery",
  "Chưa tải được sản phẩm. Bạn thử lại sau nhé!":
    "Could not load the products. Please try again shortly.",
  "Cửa hàng đang nghỉ một chút": "The store is taking a short break",
  "Chưa kết nối được cửa hàng. Máy chủ có thể đang khởi động, hãy thử lại.":
    "Could not reach the store. The server may still be starting up — please try again.",
  "Thử tải lại": "Reload",
  "Kiểm tra kết nối rồi thử lại.": "Check the connection and try again.",

  // --- Giỏ hàng và đơn ------------------------------------------------------
  "Giỏ hàng trống": "Your cart is empty",
  "Tóm tắt đơn": "Order summary",
  "Tạm tính": "Subtotal",
  "Tổng cộng": "Total",
  "Người nhận": "Recipient",
  "Xem giỏ →": "View cart →",
  "Xem đơn của tôi": "View my orders",
  "Xóa": "Remove",
  "Chưa có đơn nào": "No orders yet",
  "Chưa tải được đơn": "Could not load the orders",
  "Lịch sử đặt hàng của tài khoản này.": "This account's order history.",
  "Không đặt được hàng.": "Could not place the order.",
  "Chờ xử lý": "Awaiting processing",
  "Cần đăng nhập": "Sign-in required",

  // --- Đánh giá sản phẩm ----------------------------------------------------
  "Viết đánh giá": "Write a review",
  "Chi tiết đánh giá": "Review details",
  "Chia sẻ cảm nhận của bạn về sản phẩm…": "Share what you thought of the product…",
  "Không gửi được đánh giá. Hãy thử lại.": "Could not submit the review. Please try again.",
  "5 nhóm đánh giá": "5 review groups",
  "5 tiêu chí": "5 criteria",

  // --- Trợ lý vận hành ------------------------------------------------------
  "Trợ lý vận hành · sẵn sàng": "Operations assistant · ready",
  "Hỏi bất cứ điều gì về shop của bạn": "Ask anything about your store",
  "Hỏi trợ lý mua sắm": "Ask the shopping assistant",
  "Hỏi về doanh số, giá đối thủ, nhà sáng tạo hoặc tồn kho để nhận một câu trả lời tổng hợp.":
    "Ask about sales, competitor prices, creators or stock, and get one combined answer.",
  "Trợ lý kết hợp dữ liệu giá, doanh số, nhà sáng tạo và tồn kho để đưa ra câu trả lời ngắn gọn cùng việc nên làm tiếp theo. Có thể hỏi bằng giọng nói — bấm mic và nói.":
    "The assistant combines price, sales, creator and stock data into a short answer plus a next step. You can also ask by voice — tap the mic and speak.",
  "Câu hỏi mẫu": "Example questions",
  "Hôm nay tôi nên ưu tiên làm gì?": "What should I prioritise today?",
  "Vì sao doanh số váy hoa nhí midi giảm và nên chỉnh giá thế nào?":
    "Why are sales of the midi floral dress falling, and how should I adjust the price?",
  "Nên hợp tác KOL nào cho mỹ phẩm và khi nào đẩy ads?":
    "Which creators should I work with for cosmetics, and when should I push ads?",
  "Sản phẩm nào tương tự serum vitamin c?": "Which products are similar to vitamin C serum?",
  "Nhấn để nói bằng giọng nói": "Tap to speak",
  "Nhấn để nói · \"Hey Cellaxnet\"": "Tap to speak · \"Hey Cellaxnet\"",
  "Ví dụ: vì sao doanh số giảm tuần này? · hoặc bấm mic và nói \"Hey Cellaxnet\"":
    "For example: why did sales drop this week? · or tap the mic and say \"Hey Cellaxnet\"",
  "Không lấy được câu trả lời. Kiểm tra kết nối backend rồi thử lại.":
    "Could not get an answer. Check the backend connection and try again.",
  "Tính từ cùng snapshot 60 SKU, đơn hàng, đánh giá và tồn kho của Mây House demo.":
    "Computed from the same snapshot of 60 SKUs, orders, reviews and stock in the May House demo.",

  // --- Rủi ro vận chuyển ----------------------------------------------------
  "Cảnh báo sớm gián đoạn logistics +": "Early warning for logistics disruption +",
  "Khu vực & danh mục": "Region & category",
  "Khu vực kho/vận chuyển": "Warehouse / shipping region",
  "Miền Bắc": "Northern Vietnam",
  "Miền Trung": "Central Vietnam",
  "Miền Nam": "Southern Vietnam",
  "Nguy cơ tổng thể": "Overall risk",
  "Mức rủi ro kịch bản": "Scenario risk level",
  "Phương án dự phòng:": "Contingency plan:",
  "Tin tức liên quan": "Related news",
  "Google News · trực tiếp": "Google News · live",
  "Không có cảnh báo nào cho khu vực này.": "No alerts for this region.",
  "Không lấy được dữ liệu. Kiểm tra kết nối backend rồi thử lại.":
    "Could not get the data. Check the backend connection and try again.",

  // --- Cải thiện cửa hàng ---------------------------------------------------
  "Kế hoạch 4 tuần": "4-week plan",
  "Các việc nên ưu tiên dựa trên tình trạng hiện tại.":
    "The work to prioritise, based on where the store stands now.",
  "So sánh các điểm còn yếu để chọn việc cần làm trước.":
    "Compare the weak points to decide what to fix first.",
  "Cách hoạt động": "How it works",
  "Sẵn sàng thực hiện": "Ready to run",
  "Hôm nay": "Today",

  // --- Chung ----------------------------------------------------------------
  "Sắp ra mắt": "Coming soon",
  "Thử ngay": "Try it",
  "Khám phá tính năng khác": "Explore other features",
  "Không tìm thấy trang này": "This page was not found",
  "Tính năng mua sắm.": "A shopping feature.",
  "Tính năng này đang được hoàn thiện. Quay lại sau nhé!":
    "This feature is still being finished. Please check back later.",

  // --- Hiệu quả nhà sáng tạo ------------------------------------------------
  "Hiệu quả KOL/KOC theo chiến dịch": "Creator performance by campaign",
  "So sánh creator theo doanh số quy đổi, doanh số / 1k view và tỷ lệ tương tác.":
    "Compares creators by attributed sales, sales per 1k views and engagement rate.",
  "Xếp hạng creator": "Creator ranking",
  "Creator nên hợp tác": "Creators worth working with",
  "Thêm creator": "Add a creator",
  "Tên creator": "Creator name",
  "Danh mục chiến dịch": "Campaign category",
  "Doanh số (₫)": "Sales (₫)",
  "Bài đăng": "Posts",
  "Tương tác": "Engagement",

  // --- Hôm nay cần làm gì ---------------------------------------------------
  "Việc ưu tiên theo tác động doanh thu, tổng hợp từ các tín hiệu của cửa hàng.":
    "Work ranked by revenue impact, pulled together from the store's signals.",
  "Hôm nay không có việc ưu tiên nào. Shop đang ổn định.":
    "Nothing to prioritise today. The store is steady.",
  "Đang tổng hợp briefing…": "Assembling the briefing…",
  "Đang tổng hợp dữ liệu… (có thể mất 5–15 giây)":
    "Gathering the data… (this can take 5–15 seconds)",
  "Không lấy được briefing. Kiểm tra kết nối backend rồi thử lại.":
    "Could not get the briefing. Check the backend connection and try again.",
  "Tổng tác động ước tính": "Estimated total impact",
  "Tác động": "Impact",
  "Tình hình": "Situation",
  "Mức độ": "Level",
  "Ưu tiên": "Priority",
  "Ưu tiên cao": "High priority",
  "Nghiêm trọng": "Critical",
  "Rủi ro cao": "High risk",
  "Ổn định": "Steady",
  "ổn định": "steady",
  "Điều chỉnh giá": "Adjust the price",
  "Điều tra nguyên nhân": "Investigate the cause",
  "Nhập thêm hàng": "Restock",
  "Đẩy khuyến mãi": "Push a promotion",
  "Giảm tồn kho": "Reduce stock",

  // --- Bảng điều khiển ------------------------------------------------------
  "Cảnh báo mới nhất": "Latest alerts",
  "Các sự kiện gần nhất cần người bán chú ý.":
    "The most recent events that need the seller's attention.",
  "Nhịp doanh thu theo giờ": "Hourly revenue rhythm",
  "Triệu ₫ trung bình theo giờ trong 14 ngày, phân nhóm theo ngành hàng.":
    "Average millions of ₫ per hour over 14 days, grouped by category.",
  "Chuỗi cung ứng — 63 tỉnh thành": "Supply chain — 63 provinces",
  "Rủi ro vận hành theo kho vùng (màu = mức độ cảnh báo).":
    "Operational risk by regional warehouse (colour = alert level).",
  "Vùng": "Region",
  "Đang tải snapshot sản phẩm, khách, đơn, tồn kho và đánh giá dùng chung cho mọi feature.":
    "Loading the shared snapshot of products, customers, orders, stock and reviews used by every feature.",
  "Điểm sức khỏe cửa hàng": "Store health score",
  "Điểm tổng": "Overall score",
  "Điểm từng trục + gợi ý cụ thể.": "A score per axis, with specific suggestions.",
  "Ưu tiên tuần 1–2 trước khi chạy promotion. Nếu điểm Inventory < 50, hoãn flash sale.":
    "Handle weeks 1–2 before running a promotion. If the Inventory score is under 50, postpone the flash sale.",
  "Bấm Phân tích để xem đề xuất.": "Choose Analyse to see the suggestions.",

  // --- Đơn hàng -------------------------------------------------------------
  "Đơn thật do khách đặt từ cửa hàng. Chưa có cổng thanh toán — người bán xác nhận trạng thái thủ công.":
    "Real orders placed by customers in the store. There is no payment gateway yet — the seller confirms each status manually.",
  "Chưa có đơn nào. Đặt thử một đơn từ cửa hàng để thấy nó ở đây.":
    "No orders yet. Place a test order from the store to see it here.",
  "Đơn đang ở trạng thái": "Order status",
  "Đơn đặt khi chưa đăng nhập không gắn với tài khoản nào, nên không tra được ở đây — hãy dùng mã đơn đã hiện lúc đặt.":
    "Orders placed while signed out are not linked to an account, so they cannot be looked up here — use the order code shown at checkout.",
  "Đã thanh toán": "Paid",
  "Đã xuất hàng": "Shipped",
  "Đã giao": "Delivered",
  "Đã hủy": "Cancelled",
  "Đã xử lý": "Processed",
  "chờ xử lý": "awaiting processing",
  "Đang tải đơn…": "Loading orders…",
  "Không tải được đơn. Kiểm tra kết nối backend rồi thử lại.":
    "Could not load the orders. Check the backend connection and try again.",
  "Đặt hàng thành công!": "Order placed.",
  "Đặt trong 10 phút để nhận thêm ưu đãi.": "Order within 10 minutes for an extra discount.",
  "— hệ thống chưa tích hợp cổng thanh toán, người bán sẽ xác nhận thủ công.":
    "— there is no payment gateway yet, so the seller confirms manually.",
  "đơn mẫu": "sample orders",

  // --- Ưu đãi giữ chân ------------------------------------------------------
  "Khách đang do dự": "Hesitant customers",
  "Mô phỏng tín hiệu hành vi (thời gian dừng, tốc độ scroll, số lần quay lại) để phát hiện khách “thích nhưng do dự”.":
    "Simulates behaviour signals (dwell time, scroll speed, return visits) to spot shoppers who are “interested but hesitant”.",
  "Hành vi trên trang sản phẩm": "Behaviour on the product page",
  "Thời gian dừng trên trang (giây)": "Dwell time on page (seconds)",
  "Độ sâu scroll (%)": "Scroll depth (%)",
  "Số lần quay lại xem": "Return visits",
  "Đã thêm vào giỏ nhưng chưa mua": "Added to cart but not purchased",
  "Kích hoạt ưu đãi ngay": "Trigger the offer now",
  "Giảm giá đề xuất:": "Suggested discount:",

  // --- Kết nối sàn ----------------------------------------------------------
  "Kết nối sàn bán hàng": "Connect a marketplace",
  "Kết nối": "Connect",
  "Chọn sàn để mở Seller Center và đăng nhập gian hàng của bạn.":
    "Pick a marketplace to open Seller Center and sign in to your store.",
  "Đăng nhập Seller Centre để chọn gian hàng Shopee của bạn.":
    "Sign in to Seller Centre to choose your Shopee store.",
  "Đăng nhập Seller Center để chọn gian hàng Lazada của bạn.":
    "Sign in to Seller Center to choose your Lazada store.",
  "Đăng nhập Seller Center để chọn gian hàng TikTok Shop của bạn.":
    "Sign in to Seller Center to choose your TikTok Shop store.",
  "Đăng nhập Seller Center để chọn gian hàng Tiki của bạn.":
    "Sign in to Seller Center to choose your Tiki store.",
  "— nền tảng bán hàng đa kênh đã được Shopee, Lazada và TikTok Shop cấp quyền sẵn. Một liên kết mang về đơn của cả ba sàn, mỗi đơn có ghi rõ đến từ kênh nào.":
    "— a multichannel selling platform already authorised by Shopee, Lazada and TikTok Shop. One link brings in orders from all three, each labelled with the channel it came from.",
  "Đang theo dõi": "Tracking",
  "Đang mở": "Opening",

  // --- Gian hàng: chi tiết --------------------------------------------------
  "Đánh giá sản phẩm": "Product reviews",
  "Đã thêm vào giỏ": "Added to cart",
  "Đi mua sắm": "Go shopping",
  "Gợi ý theo bạn": "Suggested for you",
  "Người mua tương tự": "Similar shoppers",
  "Vì sao phù hợp": "Why it fits",
  "Ảnh trước": "Previous image",
  "Ảnh tiếp theo": "Next image",
  "Đang tải sản phẩm…": "Loading products…",
  "← Về trang chủ": "← Back to home",
  "Bắt đầu": "Start",
  "Thông tin": "Details",
  "Tính năng": "Feature",
  "bạn": "you",
  "bạn thích": "you liked",
  "đang trả lời": "is replying",
  "Đang nghe — nhấn để dừng": "Listening — tap to stop",
  "Đang tải": "Loading",
  "Không có tính năng dành cho người bán nào khớp với đường dẫn này.":
    "No seller feature matches this path.",

  // --- Virtual Try-On: lỗi --------------------------------------------------
  "Ảnh được xử lý hoàn toàn trên máy này": "Images are processed entirely on this machine",
  "Thiếu ảnh người mẫu.": "The model photo is missing.",
  "Thiếu ảnh trang phục.": "The garment photo is missing.",
  "Yêu cầu phải chứa ảnh người mẫu và ảnh trang phục.":
    "The request must include both a model photo and a garment photo.",
  "CatVTON không thể xử lý hai ảnh này.": "CatVTON could not process these two images.",
  "Dịch vụ thử đồ đang tắt. Hãy chạy scripts/start-virtual-tryon.ps1 rồi thử lại.":
    "The try-on service is off. Run scripts/start-virtual-tryon.ps1 and try again.",
  "Định dạng tốt nhất": "Best format",
  "shop demo có quan hệ dữ liệu": "demo store with linked data",
  "shop demo thống nhất": "one consistent demo store",
  "tin tức thật": "real news",
  "cảnh báo": "alerts",
  "trợ lý": "assistant",
  "rủi ro": "risk",

  // --- Xác thực -------------------------------------------------------------
  "Đăng nhập": "Sign in",
  "Đăng ký": "Sign up",
  "Đăng xuất": "Sign out",
  "Tên của bạn": "Your name",
  Email: "Email",
  "(không bắt buộc)": "(optional)",
  "Đăng nhập không thành công.": "Sign-in failed.",
  "Đăng ký không thành công.": "Sign-up failed.",
  "Mật khẩu nhập lại không khớp.": "The passwords do not match.",
  "Tạo tài khoản để lưu giỏ hàng và nhận gợi ý phù hợp hơn.":
    "Create an account to keep your cart and get better suggestions.",
  "Vào cổng người bán hoặc tiếp tục mua sắm.":
    "Open the seller portal, or carry on shopping.",
  "Bắt đầu bán hàng →": "Start selling →",
  "Không gian bán hàng →": "Seller workspace →",
  "Xóa phiên": "Clear session",

  // --- Lỗi và trạng thái ----------------------------------------------------
  "Không tìm thấy": "Not found",
  "Không tìm thấy.": "No matches.",
  "Không kết nối được máy chủ. Hãy thử lại.":
    "Could not reach the server. Please try again.",
  "Không gọi được backend.": "Could not reach the backend.",
  "Không kết nối được backend. Kiểm tra docker compose đã chạy và cổng 8000 mở.":
    "Could not reach the backend. Check that docker compose is running and port 8000 is open.",
  "Không thể kết nối đến backend. Hãy kiểm tra dịch vụ FastAPI và thử lại.":
    "Could not reach the backend. Check the FastAPI service and try again.",
  "Không thể kết nối đến backend. Kiểm tra dịch vụ FastAPI và thử lại.":
    "Could not reach the backend. Check the FastAPI service and try again.",
  "Backend không thể xử lý yêu cầu định giá.":
    "The backend could not process the pricing request.",
  "Chế độ demo đang bật nên chưa thể gọi dịch vụ định giá.":
    "Demo mode is on, so the pricing service cannot be called yet.",
  "Chế độ demo đang bật nên chưa thể tải dữ liệu rủi ro khách hàng.":
    "Demo mode is on, so customer-risk data cannot be loaded yet.",
  "Đang ở chế độ demo (NEXT_PUBLIC_DEMO_MODE=true) nên không gọi backend. Đặt lại thành false trong frontend/.env.local.":
    "Demo mode is on (NEXT_PUBLIC_DEMO_MODE=true), so the backend is not called. Set it to false to use live data.",
  "kiểm tra lại vốn / số ngày phủ tồn kho": "check unit cost and days of stock cover",

  // --- Công tắc ngôn ngữ ----------------------------------------------------
  "Tiếng Việt": "Vietnamese",
  "Ngôn ngữ: Tiếng Việt — chuyển sang English":
    "Language: Vietnamese — switch to English",
};
