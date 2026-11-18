import frappe


def after_install():
	"""Bật đồng Việt Nam (VND) và đặt ký hiệu ₫ để tiền hiển thị đúng dạng 1.350.000 ₫."""
	frappe.db.set_value("Currency", "VND", {"enabled": 1, "symbol": "₫"})
