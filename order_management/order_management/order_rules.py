"""Quy tắc nghiệp vụ của đơn hàng.

Không import frappe nên test được độc lập (python -m unittest).
Controller của DocType (om_order.py) gọi các hàm ở đây và đổi
OrderRuleError thành frappe.ValidationError.
"""

NEW = "Mới"
DELIVERED = "Đã giao"
CANCELLED = "Hủy"

# Trạng thái hiện tại -> các trạng thái được chuyển sang.
# Trạng thái không còn đi đâu được nữa (Đã giao, Hủy) nghĩa là đơn đã bị khóa.
TRANSITIONS = {
	NEW: {DELIVERED, CANCELLED},
	DELIVERED: set(),
	CANCELLED: set(),
}


class OrderRuleError(Exception):
	"""Vi phạm quy tắc nghiệp vụ của đơn hàng."""


def is_locked(status: str) -> bool:
	return not TRANSITIONS[status]


def compute_amount(qty: float, rate: float) -> float:
	return qty * rate


def validate_qty_and_rate(qty: float, rate: float) -> None:
	if qty is None or qty <= 0:
		raise OrderRuleError("Số lượng phải lớn hơn 0.")
	if qty != int(qty):
		raise OrderRuleError("Số lượng phải là số nguyên.")
	if rate is None or rate <= 0:
		raise OrderRuleError("Đơn giá phải lớn hơn 0.")


def validate_initial_status(status: str) -> None:
	if status != NEW:
		raise OrderRuleError(f"Đơn mới tạo phải ở trạng thái '{NEW}'.")


def validate_change(before: dict, after: dict) -> None:
	"""Kiểm tra một lần lưu đơn đã tồn tại.

	`before` và `after` là dict cùng khóa: customer, item, qty, rate, status.
	"""
	old_status, new_status = before["status"], after["status"]

	if new_status not in TRANSITIONS:
		raise OrderRuleError(f"Trạng thái không hợp lệ: '{new_status}'.")

	if is_locked(old_status):
		if before != after:
			raise OrderRuleError(f"Đơn ở trạng thái '{old_status}' không được sửa hay đổi trạng thái.")
		return

	if new_status != old_status and new_status not in TRANSITIONS[old_status]:
		raise OrderRuleError(f"Không thể chuyển trạng thái từ '{old_status}' sang '{new_status}'.")


def validate_delete(status: str) -> None:
	if is_locked(status):
		raise OrderRuleError(f"Không được xóa đơn ở trạng thái '{status}'.")
