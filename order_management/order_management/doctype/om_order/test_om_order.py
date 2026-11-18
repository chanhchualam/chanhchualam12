"""Test tích hợp với Frappe (cần site): bench --site <site> run-tests --app order_management"""

import frappe
from frappe.desk.search import search_link

try:  # Frappe v16
	from frappe.tests import IntegrationTestCase as TestCase
except ImportError:  # Frappe v15
	from frappe.tests.utils import FrappeTestCase as TestCase

from order_management.order_management.order_rules import CANCELLED, DELIVERED, NEW
from order_management.order_management.report.daily_revenue.daily_revenue import execute

CUSTOMER = "_Test KH"
ITEM = "_TEST-MH"  # mã số mặt hàng
ITEM_RATE = 70000


def make_order(qty=2, rate=50000, **kwargs):
	"""Tạo đơn. rate=None: không gửi đơn giá để server lấy theo mặt hàng."""
	values = {"doctype": "OM Order", "customer": CUSTOMER, "item": ITEM, "qty": qty, **kwargs}
	if rate is not None:
		values["rate"] = rate
	return frappe.get_doc(values).insert()


def set_status(name, status):
	doc = frappe.get_doc("OM Order", name)
	doc.status = status
	doc.save()
	return doc


class TestOMOrder(TestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("OM Customer", CUSTOMER):
			frappe.get_doc({"doctype": "OM Customer", "customer_name": CUSTOMER}).insert()
		if not frappe.db.exists("OM Item", ITEM):
			frappe.get_doc(
				{"doctype": "OM Item", "item_code": ITEM, "item_name": "_Test Mặt hàng", "rate": ITEM_RATE}
			).insert()

	# --- Tạo đơn, thành tiền ---

	def test_new_order_defaults_and_amount(self):
		doc = make_order(qty=3, rate=25000)
		self.assertEqual(doc.status, NEW)
		self.assertEqual(doc.amount, 75000)

	def test_rate_and_amount_are_rounded_to_whole_dong(self):
		doc = make_order(qty=3, rate=100.4)  # đơn giá 100,4 -> 100
		self.assertEqual(doc.rate, 100)
		self.assertEqual(doc.amount, 300)

	def test_fractional_qty_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			make_order(qty=1.5)

	def test_amount_from_client_is_ignored(self):
		doc = make_order(qty=2, rate=10, amount=999999)
		self.assertEqual(doc.amount, 20)

	def test_amount_recalculated_on_update(self):
		doc = make_order(qty=2, rate=10)
		doc.qty = 5
		doc.save()
		self.assertEqual(frappe.db.get_value("OM Order", doc.name, "amount"), 50)

	def test_qty_and_rate_must_be_positive(self):
		for qty, rate in [(0, 10), (-1, 10), (1, 0), (1, -10)]:
			with self.subTest(qty=qty, rate=rate), self.assertRaises(frappe.ValidationError):
				make_order(qty=qty, rate=rate)

	def test_cannot_create_with_non_new_status(self):
		with self.assertRaises(frappe.ValidationError):
			make_order(status=DELIVERED)

	# --- Khách hàng / mặt hàng tạo mới và liên kết với đơn ---

	def test_order_with_newly_created_customer_and_item(self):
		# Giống hộp thoại nhập nhanh trong form đơn: tạo khách hàng, mặt hàng rồi lưu đơn.
		customer = frappe.get_doc({"doctype": "OM Customer", "customer_name": "_Test KH mới"}).insert()
		item = frappe.get_doc(
			{"doctype": "OM Item", "item_code": "_TEST-MOI", "item_name": "_Test hàng mới", "rate": 1000}
		).insert()

		order = make_order(customer=customer.name, item=item.name)

		saved = frappe.db.get_value("OM Order", order.name, ["customer", "item"])
		self.assertEqual(saved, (customer.name, item.name))
		self.assertTrue(frappe.db.exists("OM Customer", "_Test KH mới"))
		self.assertTrue(frappe.db.exists("OM Item", "_TEST-MOI"))

	def test_order_with_unknown_customer_or_item_is_rejected(self):
		with self.assertRaises(frappe.LinkValidationError):
			make_order(customer="Khách không tồn tại")
		with self.assertRaises(frappe.LinkValidationError):
			make_order(item="Hàng không tồn tại")

	def test_customer_created_first_is_selectable_in_order(self):
		frappe.get_doc({"doctype": "OM Customer", "customer_name": "_Test KH chọn được"}).insert()

		results = search_link("OM Customer", "_Test KH chọn")  # ô chọn khách hàng gọi hàm này

		self.assertIn("_Test KH chọn được", [r["value"] for r in results])

	def test_customer_and_item_can_be_created_from_order_form(self):
		# quick_entry = 1: tạo ngay trong hộp thoại, không rời form đơn.
		for doctype in ("OM Customer", "OM Item"):
			self.assertEqual(frappe.get_meta(doctype).quick_entry, 1)

	# --- Mã số mặt hàng ---

	def test_item_requires_unique_code(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "OM Item", "item_name": "Không mã", "rate": 1}).insert()
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc({"doctype": "OM Item", "item_code": ITEM, "item_name": "Trùng mã", "rate": 1}).insert()

	# --- Đơn giá lấy từ mặt hàng ---

	def test_rate_defaults_to_item_rate(self):
		doc = make_order(qty=3, rate=None)
		self.assertEqual(doc.rate, ITEM_RATE)
		self.assertEqual(doc.amount, 3 * ITEM_RATE)

	def test_explicit_rate_overrides_item_rate(self):
		doc = make_order(qty=2, rate=65000)
		self.assertEqual((doc.rate, doc.amount), (65000, 130000))

	def test_changing_item_rate_does_not_change_existing_orders(self):
		item = frappe.get_doc(
			{"doctype": "OM Item", "item_code": "_TEST-GIA", "item_name": "_Test hàng đổi giá", "rate": 10000}
		).insert()
		order = make_order(qty=1, rate=None, item=item.name)

		frappe.db.set_value("OM Item", item.name, "rate", 15000)
		order = frappe.get_doc("OM Order", order.name)
		order.qty = 2
		order.save()

		self.assertEqual((order.rate, order.amount), (10000, 20000))

	# --- Chuyển trạng thái ---

	def test_new_to_delivered_and_cancelled(self):
		self.assertEqual(set_status(make_order().name, DELIVERED).status, DELIVERED)
		self.assertEqual(set_status(make_order().name, CANCELLED).status, CANCELLED)

	def test_final_orders_are_locked(self):
		for final in (DELIVERED, CANCELLED):
			name = set_status(make_order().name, final).name
			with self.subTest(final=final):
				for target in {NEW, DELIVERED, CANCELLED} - {final}:
					with self.assertRaises(frappe.ValidationError):
						set_status(name, target)

				doc = frappe.get_doc("OM Order", name)
				doc.qty = 100
				with self.assertRaises(frappe.ValidationError):
					doc.save()

				with self.assertRaises(frappe.ValidationError):
					frappe.delete_doc("OM Order", name)

	# --- Báo cáo ---

	def test_daily_revenue_report(self):
		# Đẩy ngày tạo về quá khứ để không lẫn với dữ liệu khác trên site test.
		day1, day2 = "2001-01-01", "2001-01-02"
		orders = [
			(day1, 2, 100, DELIVERED),
			(day1, 1, 50, DELIVERED),
			(day1, 1, 1000, CANCELLED),  # không tính
			(day1, 1, 1000, None),  # Mới, không tính
			(day2, 3, 10, DELIVERED),
		]
		for day, qty, rate, status in orders:
			doc = make_order(qty=qty, rate=rate)
			if status:
				set_status(doc.name, status)
			frappe.db.set_value("OM Order", doc.name, "creation", f"{day} 10:00:00", update_modified=False)

		_, data = execute({"from_date": day1, "to_date": day2})
		rows = {str(r.order_date): (r.order_count, r.total_amount) for r in data}

		self.assertEqual(rows, {day1: (2, 250), day2: (1, 30)})

		_, only_day2 = execute({"from_date": day2, "to_date": day2})
		self.assertEqual(len(only_day2), 1)
