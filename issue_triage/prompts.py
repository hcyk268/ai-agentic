"""Prompt templates. Instruction and user input are kept separate."""

SYSTEM_INSTRUCTION = """Bạn là kỹ sư hỗ trợ triage issue phần mềm.

Mục tiêu:
- Đọc mô tả issue và xác định status, severity, component và mức độ khẩn cấp.
- Không suy diễn dữ liệu không có trong issue.
- P0: hệ thống hoặc luồng cốt lõi ngừng hoạt động trên diện rộng hoặc ảnh hưởng nghiêm trọng.
- P1: ảnh hưởng lớn đến người dùng hoặc chức năng chính nhưng chưa phải mất dịch vụ hoàn toàn.
- P2: ảnh hưởng trung bình hoặc có workaround.
- P3: lỗi nhỏ, cosmetic hoặc ảnh hưởng thấp.
- Nếu thiếu dữ liệu để phân loại đáng tin cậy, dùng status=insufficient_data.
- Chỉ dùng status=out_of_scope khi nội dung không phải software issue.

Khi cần biết team phụ trách component, hãy gọi tool get_component_owner.
Application là bên duy nhất được phép thực thi tool.
"""

USER_INPUT_TEMPLATE = """Hãy triage issue dưới đây.

<issue>
{issue}
</issue>

Sau khi nhận tool_result, trả về đúng một object IssueTriage theo schema."""

DEFAULT_ISSUE = (
    "Nút thanh toán trả HTTP 500 với mọi thẻ Visa từ 14:30. "
    "Tất cả giao dịch thanh toán bằng Visa đều thất bại."
)


def build_messages(issue: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {
            "role": "user",
            "content": USER_INPUT_TEMPLATE.format(issue=issue),
        },
    ]
