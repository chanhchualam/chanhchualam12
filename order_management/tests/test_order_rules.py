"""Unit test cho quy tắc nghiệp vụ — không cần Frappe.

Chạy: python -m unittest discover -s order_management/tests -t .
"""

import unittest

from order_management.order_management.order_rules import (
	CANCELLED,
	DELIVERED,
	NEW,
	OrderRuleError,
	compute_amount,
	validate_change,
	validate_delete,
	validate_initial_status,
	validate_qty_and_rate,
)


def order(**overrides):
	base = {"customer": "KH A", "item": "Áo", "qty": 2.0, "rate": 100.0, "status": NEW}
	base.update(overrides)
	return base


class TestQtyAndRate(unittest.TestCase):
	def test_positive_values_ok(self):
		validate_qty_and_rate(1, 0.5)

	def test_zero_negative_or_missing_rejected(self):
		for qty, rate in [(0, 10), (-1, 10), (None, 10), (1, 0), (1, -5), (1, None)]:
			with self.subTest(qty=qty, rate=rate), self.assertRaises(OrderRuleError):
				validate_qty_and_rate(qty, rate)

	def test_fractional_qty_rejected(self):
		with self.assertRaises(OrderRuleError):
			validate_qty_and_rate(1.5, 10)

	def test_compute_amount(self):
		self.assertEqual(compute_amount(3, 25000), 75000)


class TestInitialStatus(unittest.TestCase):
	def test_new_ok(self):
		validate_initial_status(NEW)

	def test_other_status_rejected(self):
		for status in (DELIVERED, CANCELLED, "", None):
			with self.subTest(status=status), self.assertRaises(OrderRuleError):
				validate_initial_status(status)


class TestChange(unittest.TestCase):
	def test_new_order_can_be_edited(self):
		validate_change(order(), order(qty=5.0, rate=200.0, customer="KH B"))

	def test_allowed_transitions(self):
		for target in (DELIVERED, CANCELLED):
			with self.subTest(target=target):
				validate_change(order(), order(status=target))

	def test_unknown_status_rejected(self):
		with self.assertRaises(OrderRuleError):
			validate_change(order(), order(status="Đang xử lý"))

	def test_final_order_cannot_change_status(self):
		for final in (DELIVERED, CANCELLED):
			for target in (NEW, DELIVERED, CANCELLED):
				if target == final:
					continue
				with self.subTest(final=final, target=target), self.assertRaises(OrderRuleError):
					validate_change(order(status=final), order(status=target))

	def test_final_order_cannot_be_edited(self):
		for final in (DELIVERED, CANCELLED):
			for field, value in [("qty", 9.0), ("rate", 1.0), ("customer", "X"), ("item", "Y")]:
				with self.subTest(final=final, field=field), self.assertRaises(OrderRuleError):
					validate_change(order(status=final), order(status=final, **{field: value}))

	def test_final_order_resave_without_changes_ok(self):
		validate_change(order(status=DELIVERED), order(status=DELIVERED))


class TestDelete(unittest.TestCase):
	def test_new_order_can_be_deleted(self):
		validate_delete(NEW)

	def test_final_order_cannot_be_deleted(self):
		for final in (DELIVERED, CANCELLED):
			with self.subTest(final=final), self.assertRaises(OrderRuleError):
				validate_delete(final)


if __name__ == "__main__":
	unittest.main()
