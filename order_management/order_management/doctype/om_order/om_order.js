// Giao diện chỉ để thao tác cho tiện; mọi quy tắc đều được kiểm tra ở server (om_order.py).
frappe.ui.form.on("OM Order", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.status === "Mới") {
			["Đã giao", "Hủy"].forEach((status) => {
				frm.add_custom_button(__(status), () => change_status(frm, status), __("Đổi trạng thái"));
			});
		} else {
			frm.disable_form();
			frm.set_intro(__("Đơn ở trạng thái {0} không thể sửa.", [frm.doc.status]), "orange");
		}
	},

	// Chọn mặt hàng thì điền sẵn đơn giá của mặt hàng đó; người dùng vẫn sửa được.
	item(frm) {
		if (!frm.doc.item) return;
		frappe.db.get_value("OM Item", frm.doc.item, "rate").then(({ message }) => {
			frm.set_value("rate", message.rate);
		});
	},
});

function change_status(frm, status) {
	frappe.confirm(__("Chuyển đơn sang trạng thái {0}?", [status]), () => {
		frm.set_value("status", status);
		frm.save().catch(() => frm.reload_doc());
	});
}
