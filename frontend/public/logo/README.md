# Logo

Bỏ file logo vào đúng thư mục này (`frontend/public/logo/`).

## Cần những file nào

| Tên file | Dùng ở đâu | Ghi chú |
|---|---|---|
| `logo.svg` | Sidebar, trang đăng nhập | Ưu tiên SVG — sắc nét ở mọi kích thước. PNG cũng được, nhưng để ≥ 256×256. |
| `favicon.ico` | Tab trình duyệt | Hoặc `icon.png` 512×512 — Next.js tự nhận. |

Chỉ cần `logo.svg` là đủ để gắn vào sidebar; favicon thêm sau cũng được.

## Đặt tên

Giữ đúng tên `logo.svg` / `favicon.ico` thì code gắn sẵn chạy được ngay.
Nếu đặt tên khác, báo lại để sửa đường dẫn trong `components/shell/sidebar.tsx`.

## Lưu ý

- Logo nền trong suốt sẽ hợp hơn, vì sidebar dùng nền mờ (`bg-surface/70`).
- Nếu logo đã có sẵn nền tím bo góc như bản thiết kế thì cũng dùng được —
  code sẽ bỏ khung nền phụ để tránh chồng hai lớp nền.
