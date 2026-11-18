import frappe
from frappe.model.document import Document
from frappe.utils import flt

from order_management.order_management import order_rules
from order_management.order_management.order_rules import OrderRuleError


class OMOrder(Document):
	def validate(self):
		self.normalize_qty_and_rate()
		self.check_rules()
		# Thành tiền luôn do server tính và làm tròn đến đồng, bỏ qua giá trị client gửi lên.
		self.amount = flt(order_rules.compute_amount(self.qty, self.rate), self.precision("amount"))

	def normalize_qty_and_rate(self):
		# Không gửi đơn giá thì lấy đơn giá của mặt hàng (gửi 0 vẫn bị từ chối ở check_rules).
		if self.rate is None:
			self.rate = frappe.db.get_value("OM Item", self.item, "rate")

		# API/form có thể gửi chuỗi; đơn giá làm tròn đến đồng.
		self.qty = flt(self.qty)
		self.rate = flt(self.rate, self.precision("rate"))

	def check_rules(self):
		try:
			order_rules.validate_qty_and_rate(self.qty, self.rate)
			if self.is_new():
				order_rules.validate_initial_status(self.status)
			else:
				order_rules.validate_change(_snapshot(self.get_doc_before_save()), _snapshot(self))
		except OrderRuleError as e:
			frappe.throw(str(e), title="Đơn hàng không hợp lệ")

	def on_trash(self):
		try:
			order_rules.validate_delete(self.status)
		except OrderRuleError as e:
			frappe.throw(str(e))


def _snapshot(doc) -> dict:
	"""Các trường mà đơn đã giao/hủy không được thay đổi."""
	return {
		"customer": doc.customer,
		"item": doc.item,
		"qty": flt(doc.qty),
		"rate": flt(doc.rate),
		"status": doc.status,
	}
