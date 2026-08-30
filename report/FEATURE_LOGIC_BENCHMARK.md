# Feature Logic Audit & Product-flow Benchmark

Ngày kiểm tra: 2026-08-12

## Kết luận ngắn

App đã có một demo/MVP khá rộng, nhưng chưa phải seller platform production.
Luồng lõi storefront, checkout, RBAC, workspace và phần lớn API chạy ổn. Các
feature intelligence chính hiện dùng chung snapshot `Mây House Official` thay vì
mỗi màn hình giữ một catalog/customer mock riêng. Khoảng cách lớn nhất với
Shopify/Amazon/Klaviyo nay là connector production: chưa lấy dữ liệu liên tục từ
shop thật, chưa lưu đầy đủ lịch sử theo workspace, chưa đo hiệu quả sau hành động
và chưa có drill-down xuyên suốt mọi feature.

Ký hiệu:

- **A — usable MVP:** logic chính nhất quán, có thể demo end-to-end.
- **B — partial/demo:** flow hợp lý nhưng dữ liệu, action hoặc feedback loop chưa production.
- **C — blocker:** không nên giới thiệu là feature production.

## Phạm vi và phương pháp

- Kiểm tra inventory route/UI từ `READY_NAV_ITEMS` và backend routers.
- Chạy contract/API/RBAC tests hiện có và bổ sung invariant tests cho các lỗi tìm được.
- Kiểm tra boundary input, state transition, stock, pricing floor, demo fallback, human review và thông điệp không được bịa dữ kiện.
- So sánh flow với tài liệu chính thức của Shopify, Amazon, Google Analytics, Klaviyo và AWS; Prisync được dùng làm benchmark chuyên biệt cho dynamic pricing.
- Trình duyệt tích hợp không có browser session trong môi trường hiện tại. Vì vậy UI được kiểm bằng source, TypeScript, lint và production build; chưa có visual click-through/screenshot trên browser thật trong vòng audit này.

Kết quả cuối: **219 backend tests pass**, Ruff pass, mypy pass, frontend typecheck/lint pass, Next.js production build pass và `npm audit --omit=dev` có **0 vulnerability**.

## Ma trận từng feature

| Feature | Flow hiện tại và kết quả test | So với sản phẩm tham chiếu | Xếp loại |
|---|---|---|---|
| Auth + RBAC + workspace | Register/login/refresh, role gate, membership DB check, owner protection và workspace switch đã có test. Seller thường chỉ được dùng feature đã tenant-safe. | Cấu trúc account → workspace → members → shops là đúng hướng SaaS. Khác: chưa có invitation lifecycle, audit log, granular permission và SSO. | A- |
| Kết nối shop/sàn | Có model chung cho marketplace shop, encrypted token fields, status, last sync và disconnect. Shopee OAuth thật chưa chạy; UI vẫn ở trạng thái chuẩn bị. | Shopify Marketplace Connect đi từ xác thực marketplace → connect account → listing/order/inventory/fulfillment sync → disconnect. App mới có data skeleton, chưa có authorization callback/token refresh/sync job. | C |
| Storefront | Catalog 60 SKU, filter/detail, 1.190 review, cart và checkout dùng chung snapshot; giá được đọc lại ở server, duplicate item được gộp, chống oversell. | Gần luồng commerce cơ bản. Khác: catalog vẫn là dữ liệu demo, chưa có variant, promotion engine, tax/shipping quote, payment và multi-location inventory. | A- |
| Orders | Đã chặn chuyển trạng thái ngược, lock row khi đổi trạng thái, hủy đơn chưa ship sẽ hoàn kho, doanh thu UI không còn tính đơn pending. | Shopify có payment/fulfillment/return/refund/restock/tracking/timeline riêng. App chỉ có pending → paid → shipped hoặc cancelled; chưa có delivered, partial fulfillment/refund và carrier tracking. | A- |
| Personal Shopper | Parse nhu cầu/ngân sách, lọc và trả product card từ đúng catalog storefront; rating/review/image/stock cùng nguồn và loại SKU hết hàng. | Google/Amazon assistant có memory, feedback, compare, live price/availability và add-to-cart action. App chưa có account context, comparison flow, preference feedback và action trong chat. | B+ demo |
| Recsys | Hai mode dùng lịch sử đơn của customer, co-purchase, popularity 90 ngày, intent và stock của catalog chung; loại seed item và SKU hết hàng. Offline metrics vẫn là demo cố định. | Shopify tự sinh related/complementary từ purchase history/product data, cho manual override và theo dõi click/purchase rate. App còn thiếu event feedback online, training pipeline, evaluation thật và manual override. | B+ demo, C production |
| Copilot | Phân loại câu hỏi, dispatch sang analytical tools, LLM tổng hợp hoặc fallback; read-only. | Shopify Sidekick dùng store context, có memory/saved skills, chạy task và hiển thị thay đổi để merchant review trước khi apply. App chưa có conversation memory bền vững, action plan có xác nhận, write tools và background job. | B |
| Daily Briefing | Tạo danh sách hành động ưu tiên và impact estimate từ store demo. | Pattern ưu tiên/impact giống operational assistant, nhưng dữ liệu và impact chưa đến từ workspace/shop thật; click action chưa mở workflow thực thi có tracking. | B |
| Review Intelligence | Sentiment + fake-review chạy song song, review thật được moderate trước khi publish, nghi giả luôn vào human queue thay vì auto-reject. | Amazon Customer Review Insights gom positive/negative theo product feature, frequency, rating impact, trend 6 tháng và benchmark category. App mạnh ở moderation nhưng thiếu aspect aggregation, trend, benchmark và calibration dataset. | A- moderation, B analytics |
| Dynamic Pricing | Dùng median category để đề xuất khoảng giá; validation pass. | Prisync dùng competitor feed, cost/markup, rule theo lowest/average/highest, scope và fallback rồi có thể reprice tự động. App chưa nhận cost/min margin ở feature này, chưa có lịch sử giá, rule set, approval/publish và measurement. Market Intelligence bên dưới bù một phần margin floor. | B |
| Customer Risk | Churn + return + regret được gộp theo customer id, có driver/action và portfolio ranking. | Klaviyo yêu cầu đủ lịch sử, cập nhật prediction theo chu kỳ, tạo dynamic segment và kích hoạt win-back flow; đồng thời cảnh báo prediction cá nhân có uncertainty. App dùng heuristic trên customer mẫu, chưa có eligibility, calibration, consent, persistent segment hay campaign outcome. | B-/demo |
| Emotion-aware Sale | Hesitation score từ dwell/scroll/revisit/cart abandon; chỉ trigger ưu đãi khi có cart abandon. Đã bỏ thông điệp scarcity không có bằng chứng. | Flow trigger cá nhân hóa tương tự onsite personalization, nhưng app đang là simulator form, chưa lấy live event, chưa có frequency cap, margin guard, holdout/A-B test hay approval. | B |
| Segmentation | XGBoost artifact được load/cached, trả persona probabilities, validation pass. | Shopify segment là query động trên customer table và tự add/remove member, sau đó dùng cho campaign. App chỉ classify một vector nhập tay; chưa lưu segment, rule, membership refresh hoặc activation. | B |
| Content Generator | Tạo biến thể theo sàn, call song song, timeout/fallback; fallback hiện bám đúng tên/features nhập vào và không tự thêm freeship/voucher/chính hãng/đổi trả. UI ghi rõ cần duyệt; CTR ghi là heuristic. | Shopify Magic tạo từ trang product, cho prompt tone/keywords rồi người bán edit/save ngay vào product và chịu trách nhiệm kiểm tra độ chính xác. App khác ở multi-platform — điểm tốt — nhưng chưa có tone/brand voice, product draft integration, policy validator, approval/version/A-B outcome. | A- demo, B production |
| Seller Coach | Audit 5 trục + roadmap 4 tuần được tính từ listing completeness, competitor price, image score, 1.190 review và stock của 60 SKU trong shop demo; không cho LLM tự bịa score. | Amazon Growth Opportunities gắn cơ hội với ASIN, action cụ thể và estimated sales lift dựa trên dữ liệu seller production. App đã thống nhất nguồn demo nhưng chưa đọc metric từ marketplace sync thật. | B demo, C production |
| Inventory/Sentiment Alert | Kết hợp mentions/sentiment với stock runway. Đã sửa stockout/no-buzz từ “bình thường” thành urgent và có regression test. | Shopify/Stocky dùng sales velocity, lead time, reorder point, depletion và lost revenue để ưu tiên. App có social signal khác biệt tốt, nhưng dữ liệu vẫn nhập tay, thiếu lead time, supplier/PO và actual social connector. | A- logic, B data flow |
| Supply Chain | Trả scenario theo vùng + optional news. Đã đổi toàn bộ wording sang “kịch bản tham chiếu”, không còn tuyên bố event tĩnh đang diễn ra. | AWS Supply Chain Insights dùng watchlist theo site/product, inventory risk, rebalancing option, subscription và lifecycle. App chưa có supplier/site/SKU exposure, weather/logistics verification, status/owner/action tracking. | B-/demo |
| Product Knowledge | Tính sales delta và rank stock/price/traffic/promo signals; wording đã đổi từ causal claim sang possible contributing signals. | Sản phẩm analytics thật cần time-series decomposition, experiment hoặc causal design để nói “vì sao”. App hiện là descriptive heuristic, chưa chứng minh nhân quả và chưa drill-down về dữ liệu nguồn. | B |
| Market Intelligence | So competitor effective price, position, cost-based floor và minimum margin. Đã sửa case action “hold” nhưng số lại tăng: nay trả `protect_margin`. Competitor URL collector có validation và test. | Gần flow của dynamic-pricing tools ở phần margin guard/competitor comparison. Khác: competitor collection còn phụ thuộc session/vendor, chưa có scheduler reliability/SLA, rule approval, price publish và outcome tracking. | A- calculator, B tracker |
| Creator Performance | Rank attributed sales, sales/1k views, engagement và content type; có correlation/playbook demo. | Shopify Collabs theo visits, sales, orders, conversion, commission, gifts, creator/date filter và export. App thiếu attribution method, code/link, order drill-down, commission/cost, date range và statistical confidence. | B |
| Decision Intelligence | Đã sửa so sánh raw ROAS với percentage: mọi metric được normalize trước khi chọn quyết định tốt nhất. Có seasonality/playbook fallback. | Flow “learn from prior outcomes” hợp lý, nhưng reference max hiện hard-coded; chưa kiểm soát sample size, context similarity, cost/risk và post-action measurement. | A- demo, B production |
| Product Graph | Resolve product/SKU/brand/category/similar/promotion và sales block từ store demo. | Gần lightweight knowledge graph/read model; khác: chưa có persisted graph, provenance, relationship confidence, graph query và catalog sync. | B |
| Customer Journey | Event vocabulary, timing, funnel, cart abandonment, next action, recommendation và LLM narrative cho live analyze đều hoạt động. Numeric score là deterministic; sample-session endpoint cố ý dùng fallback narrative để tránh N LLM calls. Đã bỏ scarcity nudge không có stock evidence. | GA4 Path Exploration là aggregate forward/backward tree, hỗ trợ segments/cross-session/loops; Shopify còn có attribution models. App tập trung session replay + next-best-action, thiếu aggregate paths, filters, backward path, attribution, experiment/outcome tracking. | A- session demo, B analytics |
| Dashboard/KPI | KPI, hourly revenue, counts, stock/review/risk alerts và tỉnh thành đều derive từ cùng 540 đơn, 120 khách và 60 SKU; UI ghi rõ shop demo. | Shopify overview dashboard có customizable cards, date comparison, drilldown reports, frequent refresh, insights và targets. App còn thiếu shared date filter, drilldown và dữ liệu production theo workspace. | B+/demo |

## Các lỗi logic đã sửa trong vòng audit này

1. Stock bằng 0 nhưng social buzz thấp từng trả `none` và nói runway ổn.
2. Journey và Emotion Sale từng tự bịa “chỉ còn ít hàng/số lượng giới hạn”.
3. Regret message từng hứa đổi trả miễn phí 7 ngày dù không có policy cấu hình.
4. Market Intelligence từng trả action `hold` nhưng recommended price lại tăng lên floor.
5. Decision Intelligence từng so trực tiếp ROAS 4.2 với sales lift 65 và mặc định 65 “tốt hơn” dù khác đơn vị.
6. Content Generator demo từng trả quảng cáo áo denim, freeship/TikiNOW/return policy cho mọi sản phẩm.
7. Seller Coach có thể nhờ LLM chấm shop chỉ từ `seller_id`; nay buộc demo cho tới khi có metric thật.
8. Supply Chain từng trình bày event mùa vụ tĩnh như sự cố “đang ảnh hưởng”.
9. Review nghi giả confidence cao từng bị auto-reject; nay luôn vào human moderation queue.
10. Order từng cho phép API nhảy trạng thái tùy ý, hủy không hoàn kho, và collision retry có thể commit order mà không trừ lại stock.
11. Checkout từng chấp nhận tên khách chỉ gồm khoảng trắng.
12. UI từng tính order pending là doanh thu và gọi `shipped` là “đã giao”.

Regression coverage nằm tại `backend/tests/test_feature_logic_regressions.py` và
`backend/tests/test_coherent_demo_shop.py` cùng các review/order tests đã cập
nhật. Contract nguồn dữ liệu thống nhất nằm tại `COHERENT_DEMO_SHOP.md`.

## Khác biệt nào là hợp lý, khác biệt nào cần sửa

### Khác có chủ đích — giữ lại

- Customer Journey dùng công thức cho probability/action và LLM chỉ cho reasoning. Đây là thiết kế hybrid đúng: LLM không nên tự quyết số xác suất.
- Content Generator tạo nhiều phiên bản theo sàn trong một lần, rộng hơn flow một product description của Shopify.
- Inventory Alert thêm social buzz vào stock runway; đây là điểm khác biệt có giá trị nếu sau này nối dữ liệu thật.
- Product Graph gom quan hệ catalog và sales signals trong một view; phù hợp demo kiến thức sản phẩm.

### Thiếu MVP — làm tiếp sau

- Date filter, drilldown và recent activity chung cho dashboard.
- Persistent segment + action/campaign activation.
- Recsys feedback (`not interested`, favorite, click, cart, purchase) và stock filtering.
- Orders: payment, delivered, refund, return, tracking, timeline.
- Creator: attribution links/codes, orders, conversion, commission/cost và export.
- Review: aspect/topic trends và product/category benchmark.

### Blocker để gọi là seller platform thật

1. Shopee OAuth/callback/token refresh/revoke và scheduled sync chưa triển khai.
2. Các legacy seller intelligence API vẫn admin-only vì chưa tenant-scope; seller thường hiện chỉ dùng Content Generator và Seller Coach tenant-safe.
3. Phần lớn intelligence chưa lấy dữ liệu từ workspace/shop thật.
4. Chưa có sync run log, retry/dead-letter, idempotency và reconciliation cho order/product/inventory.
5. Demo/live provenance chưa thống nhất thành một contract chung cho mọi response và card.

## Flow ưu tiên đề xuất

1. **Connect:** workspace → chọn Shopee → OAuth → callback → encrypted tokens → shop active.
2. **Initial sync:** shop profile → products/variants → inventory → orders; ghi `sync_run`, cursor và lỗi từng entity.
3. **Operate:** dashboard/card chỉ đọc normalized workspace data; mọi card drill xuống source rows.
4. **Act:** recommendation → merchant review/confirm → write action hoặc export task; không để LLM tự ghi thay đổi.
5. **Measure:** lưu action, baseline, outcome và confidence; dùng outcome để hiệu chỉnh pricing/risk/recsys/coach.
6. **Expand:** khi Shopee ổn mới thêm adapter Lazada/TikTok Shop, giữ model chung và mapping riêng.

## Nguồn benchmark

- Shopify Marketplace Connect setup: https://help.shopify.com/en/manual/online-sales-channels/marketplaces/marketplace-connect/setup
- Shopify orders, cancellation và fulfillment: https://help.shopify.com/en/manual/fulfillment/managing-orders ; https://help.shopify.com/en/manual/fulfillment/managing-orders/canceling-orders ; https://help.shopify.com/en/manual/fulfillment
- Shopify Magic product descriptions: https://help.shopify.com/en/manual/products/details/product-descriptions/shopify-magic
- Shopify Search & Discovery recommendations/analytics: https://help.shopify.com/en/manual/online-store/storefront-search/search-and-discovery-recommendations ; https://help.shopify.com/en/manual/online-store/storefront-search/search-and-discovery-analytics
- Shopify customer segmentation: https://help.shopify.com/en/manual/customers/customer-segmentation
- Shopify Sidekick: https://help.shopify.com/en/manual/shopify-admin/productivity-tools/sidekick
- Shopify analytics overview: https://help.shopify.com/en/manual/reports-and-analytics/shopify-reports/overview-dashboard
- Shopify Collabs creator management: https://help.shopify.com/en/manual/promoting-marketing/collabs/merchants/managing-creators
- Shopify/Stocky demand forecasting and low stock: https://help.shopify.com/en/manual/sell-in-person/shopify-pos/inventory-management/stocky/inventory-management/demand-forecasting ; https://help.shopify.com/en/manual/sell-in-person/shopify-pos/inventory-management/stocky/inventory-management/low-stock
- Klaviyo predictive analytics and segmentation: https://help.klaviyo.com/hc/en-us/articles/360020919731 ; https://help.klaviyo.com/hc/en-us/articles/360035312491
- Google Analytics Path Exploration: https://support.google.com/analytics/answer/9317498?hl=en
- Google personalized Shopping: https://blog.google/products-and-platforms/products/shopping/google-personalized-shopping-tips/
- Amazon Rufus shopping assistant: https://www.aboutamazon.com/news/retail/amazon-rufus-ai-assistant-personalized-shopping-features
- Amazon Customer Review Insights: https://sellercentral.amazon.com/seller-forums/discussions/t/d5bdc9b5-65ca-400f-9c89-4f2547d5f8cd
- Amazon Growth Opportunities: https://sellercentral.amazon.com/seller-forums/discussions/t/a9ba740c413cfda909cdf41cc51b8780/
- AWS Supply Chain Insights: https://docs.aws.amazon.com/aws-supply-chain/latest/adminguide/Insights.html
- Prisync dynamic pricing/rules: https://helpcenter.prisync.com/hc/en-us/articles/115002989513-What-is-Dynamic-Pricing ; https://helpcenter.prisync.com/hc/en-us/articles/115002988993-How-to-set-up-SmartPrice-rules
