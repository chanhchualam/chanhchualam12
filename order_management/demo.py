"""Dữ liệu mẫu để demo.

    bench --site <site> execute order_management.demo.setup_demo

- Site chưa qua Setup Wizard thì tự hoàn tất (Việt Nam, VND, Asia/Ho_Chi_Minh).
- Tạo khách hàng, mặt hàng và 60 đơn rải trong 30 ngày qua. Đơn được tạo bằng
  doc.insert() / doc.save() nên đi qua đúng các kiểm tra ở server.
- Chạy lại không tạo trùng.
"""

import random
from datetime import timedelta

import frappe
from frappe.utils import now_datetime

from order_management.order_management.order_rules import CANCELLED, DELIVERED

CUSTOMERS = {  # tên -> số điện thoại
	"Công ty TNHH Minh Long": "0903111222",
	"Cửa hàng Hoa Mai": "0912333444",
	"Nguyễn Văn An": "0987555666",
	"Trần Thị Bích": "0938777888",
	"Công ty CP Sao Việt": "0281234567",
	"Lê Hoàng Nam": "0905999000",
	"Siêu thị mini Phúc An": "0919222333",
	"Phạm Thu Hà": "0977444555",
}

ITEMS = [  # (mã số, tên, đơn giá mặc định VND)
	("MH001", "Bàn phím cơ", 450000),
	("MH002", "Chuột không dây", 250000),
	("MH003", "Màn hình 24 inch", 3200000),
	("MH004", "Tai nghe Bluetooth", 690000),
	("MH005", "Ổ cứng SSD 512GB", 1150000),
	("MH006", "Cáp sạc USB-C", 90000),
	("MH007", "Loa mini", 380000),
	("MH008", "Webcam HD", 520000),
]

ORDER_COUNT = 60
DAYS = 30


def setup_demo():
	complete_setup_wizard()
	if frappe.db.exists("OM Customer", next(iter(CUSTOMERS))):
		print("Dữ liệu mẫu đã có, bỏ qua.")
		return

	create_customers_and_items()
	create_orders()
	frappe.db.commit()
	print(f"Đã tạo {len(CUSTOMERS)} khách hàng, {len(ITEMS)} mặt hàng, {ORDER_COUNT} đơn hàng.")


def complete_setup_wizard():
	if frappe.is_setup_complete():
		return

	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	setup_complete(
		{"language": "Việt", "country": "Vietnam", "timezone": "Asia/Ho_Chi_Minh", "currency": "VND"}
	)


def create_customers_and_items():
	for name, phone in CUSTOMERS.items():
		frappe.get_doc({"doctype": "OM Customer", "customer_name": name, "phone": phone}).insert()
	for code, name, rate in ITEMS:
		frappe.get_doc({"doctype": "OM Item", "item_code": code, "item_name": name, "rate": rate}).insert()


def create_orders():
	rng = random.Random(2026)  # cố định để lần nào cũng ra cùng bộ dữ liệu
	now = now_datetime()

	# Sắp theo thời gian để mã đơn DH-xxxxx tăng dần theo ngày tạo.
	times = sorted(now - timedelta(seconds=rng.randint(60, DAYS * 86400)) for _ in range(ORDER_COUNT))

	for created_at in times:
		order = frappe.get_doc(
			{
				"doctype": "OM Order",
				"customer": rng.choice(list(CUSTOMERS)),
				"item": rng.choice(ITEMS)[0],
				"qty": rng.choice([1, 1, 1, 2, 2, 3, 5, 10]),
				# không nhập rate: server tự lấy đơn giá của mặt hàng
			}
		).insert()

		status = rng.choices([None, DELIVERED, CANCELLED], weights=[15, 75, 10])[0]
		if status:
			order.status = status
			order.save()

		# Lùi ngày tạo về quá khứ để báo cáo có nhiều ngày.
		frappe.db.set_value(
			"OM Order", order.name, {"creation": created_at, "modified": created_at}, update_modified=False
		)
