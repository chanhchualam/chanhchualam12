frappe.listview_settings["OM Order"] = {
	get_indicator(doc) {
		const colors = { "Mới": "blue", "Đã giao": "green", "Hủy": "red" };
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
};
