"""Dịch văn bản backend gửi ra giao diện.

Backend sinh một phần chữ người dùng đọc — lời giải thích giá, nhãn ba mốc
thị trường, lý do rủi ro — nên nó phải nói được cả hai thứ tiếng chứ không chỉ
frontend.

Cách dùng giống bên frontend: khoá tra cứu là chính câu tiếng Việt.

    from app.core.i18n import t
    t("Trung vị thị trường")          # -> "Market median" khi ngôn ngữ là EN

Ngôn ngữ lấy từ header ``Accept-Language`` của request, lưu trong một
:class:`contextvars.ContextVar`. Dùng ContextVar chứ không phải biến toàn cục
vì server chạy async: hai request có thể xen kẽ nhau trong cùng một luồng, và
một biến toàn cục sẽ để request này đọc trúng ngôn ngữ của request kia.

Câu ghép động dùng :func:`tf` — nó dịch phần khung rồi mới chèn số vào, nên
bản dịch giữ được cả cấu trúc câu:

    tf("{giá} cao hơn trung vị {trung_vị}.", giá=..., trung_vị=...)
"""

from __future__ import annotations

from contextvars import ContextVar

from app.core.translations import EN

#: Ngôn ngữ của request đang xử lý. Mặc định "vi" — tiếng Việt là bản gốc,
#: nên khi không có thông tin gì thì trả nguyên văn là đúng.
_language: ContextVar[str] = ContextVar("language", default="vi")


def set_language(accept_language: str | None) -> None:
    """Đặt ngôn ngữ cho request hiện tại từ header Accept-Language."""
    value = (accept_language or "").strip().lower()
    # Chỉ cần biết có phải "en" hay không: hệ thống có đúng hai ngôn ngữ, và
    # mọi thứ khác đều rơi về bản gốc tiếng Việt.
    _language.set("en" if value.startswith("en") else "vi")


def get_language() -> str:
    return _language.get()


def t(vi: str) -> str:
    """Dịch một câu. Không có bản dịch thì trả lại nguyên văn tiếng Việt."""
    if _language.get() == "vi":
        return vi
    return EN.get(vi, vi)


def tf(template: str, **values: object) -> str:
    """Dịch một câu có chỗ trống rồi mới điền giá trị vào.

    Dịch khung trước, chèn sau — nếu làm ngược lại thì câu đã có số bên trong
    sẽ không bao giờ khớp một khoá cố định nào.
    """
    return t(template).format(**values)
