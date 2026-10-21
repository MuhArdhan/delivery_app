// Copyright (c) 2026, Muhammad Ardhan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Proof of Delivery", {
	refresh(frm) {
		if (frm.doc.latitude && frm.doc.longitude) {
			const map_url = `https://www.google.com/maps?q=${frm.doc.latitude},${frm.doc.longitude}`;
			frm.add_custom_button(__("View GPS on Google Maps"), function() {
				window.open(map_url, "_blank");
			});
		}

		if (frm.doc.delivery_note) {
			frm.add_custom_button(__("Open Delivery Note"), function() {
				frappe.set_route("Form", "Delivery Note", frm.doc.delivery_note);
			}, __("Links"));
		}

		if (frm.doc.delivery_trip) {
			frm.add_custom_button(__("Open Delivery Trip"), function() {
				frappe.set_route("Form", "Delivery Trip", frm.doc.delivery_trip);
			}, __("Links"));
		}
	},

	delivery_note(frm) {
		if (frm.doc.delivery_note) {
			frappe.db.get_value("Delivery Note", frm.doc.delivery_note, ["customer", "customer_name", "shipping_address_name"], (r) => {
				if (r) {
					frm.set_value("customer", r.customer);
					frm.set_value("customer_name", r.customer_name);
				}
			});
		}
	}
});
