// Copyright (c) 2026, Muhammad Ardhan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Delivery Gateway Settings", {
	refresh(frm) {
		if (frm.doc.enabled) {
			frm.add_custom_button(__("Test API Connection"), function() {
				frappe.call({
					method: "delivery_app.services.biteship.test_connection",
					freeze: true,
					freeze_message: __("Connecting to Biteship API..."),
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.msgprint({
								title: __("Connection Successful"),
								indicator: "green",
								message: __("Successfully connected to Biteship API! Account: {0}", [r.message.account_name || "Active"])
							});
						} else {
							frappe.msgprint({
								title: __("Connection Failed"),
								indicator: "red",
								message: r.message ? r.message.error : __("Failed to connect.")
							});
						}
					}
				});
			});
		}
	}
});
