"""Báo cáo doanh thu theo ngày.

Mỗi ngày một dòng: số đơn và tổng thành tiền.
Chỉ tính đơn 'Đã giao', nhóm theo NGÀY TẠO ĐƠN (trường creation).
"""

import frappe
from frappe.query_builder.functions import Count, Date, Sum
from frappe.utils import add_days, getdate

from order_management.order_management.order_rules import DELIVERED


def execute(filters=None):
	return get_columns(), get_data(frappe._dict(filters or {}))


def get_columns():
	return [
		{"fieldname": "order_date", "label": "Ngày", "fieldtype": "Date", "width": 140},
		{"fieldname": "order_count", "label": "Số đơn", "fieldtype": "Int", "width": 120},
		{
			"fieldname": "total_amount",
			"label": "Tổng thành tiền",
			"fieldtype": "Currency",
			"precision": 0,
			"width": 180,
		},
	]


def get_data(filters):
	order = frappe.qb.DocType("OM Order")
	order_date = Date(order.creation)

	query = (
		frappe.qb.from_(order)
		.select(
			order_date.as_("order_date"),
			Count(order.name).as_("order_count"),
			Sum(order.amount).as_("total_amount"),
		)
		.where(order.status == DELIVERED)
		.groupby(order_date)
		.orderby(order_date)
	)

	if filters.from_date:
		query = query.where(order.creation >= getdate(filters.from_date))
	if filters.to_date:
		# creation là datetime nên lấy "< ngày kế tiếp" để bao trọn ngày cuối.
		query = query.where(order.creation < add_days(getdate(filters.to_date), 1))

	return query.run(as_dict=True)
