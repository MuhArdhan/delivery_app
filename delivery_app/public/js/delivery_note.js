// Copyright (c) 2026, Muhammad Ardhan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Delivery Note", {
	refresh(frm) {
		setup_delivery_ui(frm);
	},

	custom_delivery_method(frm) {
		setup_delivery_ui(frm);
	},

	custom_waybill_no(frm) {
		setup_delivery_ui(frm);
	},

	custom_courier_code(frm) {
		setup_delivery_ui(frm);
	}
});

function setup_delivery_ui(frm) {
	const method = frm.doc.custom_delivery_method || "Armada Sendiri";

	// 1. Buttons for Ekspedisi (3PL tracking)
	if (method === "Ekspedisi") {
		if (frm.doc.custom_waybill_no && frm.doc.custom_courier_code) {
			frm.add_custom_button(__("Lacak Resi"), function() {
				frappe.call({
					method: "delivery_app.services.biteship.track_delivery_note",
					args: {
						delivery_note_name: frm.doc.name
					},
					freeze: true,
					freeze_message: __("Mengambil data pelacakan dari Biteship..."),
					callback: function(r) {
						if (r.message && r.message.success) {
							frm.reload_doc();

							// Show Timeline Dialog
							const d = new frappe.ui.Dialog({
								title: __("Pelacakan Resi: {0}", [r.message.waybill_id]),
								size: "large",
								fields: [
									{
										fieldtype: "HTML",
										fieldname: "timeline_view",
										options: r.message.timeline_html
									}
								],
								primary_action_label: __("Tutup"),
								primary_action: () => d.hide()
							});
							d.show();
						} else {
							frappe.msgprint({
								title: __("Pelacakan Resi"),
								indicator: "orange",
								message: (r.message && r.message.error) || __("Data pelacakan belum tersedia dari kurir.")
							});
						}
					}
				});
			}, __("Pengiriman"));
		}
	}

	// 2. Buttons for Armada Sendiri (Proof of Delivery)
	if (method === "Armada Sendiri" && frm.doc.docstatus === 1) {
		if (frm.doc.custom_pod_status !== "Delivered") {
			frm.add_custom_button(__("Input POD"), function() {
				open_pod_dialog(frm);
			}, __("Pengiriman"));
		}

		if (frm.doc.custom_proof_of_delivery) {
			frm.add_custom_button(__("Lihat POD"), function() {
				frappe.set_route("Form", "Proof of Delivery", frm.doc.custom_proof_of_delivery);
			}, __("Pengiriman"));
		}
	}
}

function open_pod_dialog(frm) {
	// Fast In-Desk POD Submission Dialog
	const d = new frappe.ui.Dialog({
		title: __("Bukti Serah Terima Barang (POD)"),
		fields: [
			{
				fieldtype: "Data",
				fieldname: "recipient_name",
				label: __("Nama Penerima"),
				reqd: 1,
				default: frm.doc.contact_display || ""
			},
			{
				fieldtype: "Select",
				fieldname: "recipient_relationship",
				label: __("Hubungan Penerima"),
				options: "Yang Bersangkutan\nKeluarga\nSatpam / Security\nResepsionis / Front Office\nRekan Kerja\nTetangga\nLainnya",
				default: "Yang Bersangkutan",
				reqd: 1
			},
			{
				fieldtype: "Data",
				fieldname: "recipient_phone",
				label: __("No. HP / Kontak Penerima"),
				default: frm.doc.contact_phone || frm.doc.contact_mobile || ""
			},
			{
				fieldtype: "Column Break"
			},
			{
				fieldtype: "Attach Image",
				fieldname: "proof_photo",
				label: __("Foto Serah Terima"),
				reqd: 1
			},
			{
				fieldtype: "Signature",
				fieldname: "signature",
				label: __("Tanda Tangan Digital Penerima")
			},
			{
				fieldtype: "Section Break",
				label: __("Catatan")
			},
			{
				fieldtype: "Small Text",
				fieldname: "notes",
				label: __("Catatan Lapangan / Keterangan")
			}
		],
		primary_action_label: __("Simpan Bukti (POD)"),
		primary_action(values) {
			if (!values.proof_photo) {
				frappe.msgprint(__("Foto bukti serah terima wajib diunggah."));
				return;
			}

			// Capture device GPS if permitted
			let lat = null;
			let lng = null;

			function save_pod() {
				frappe.call({
					method: "frappe.client.insert",
					args: {
						doc: {
							doctype: "Proof of Delivery",
							delivery_note: frm.doc.name,
							customer: frm.doc.customer,
							customer_name: frm.doc.customer_name,
							delivery_trip: frm.doc.delivery_trip || null,
							recipient_name: values.recipient_name,
							recipient_relationship: values.recipient_relationship,
							recipient_phone: values.recipient_phone,
							proof_photo: values.proof_photo,
							signature: values.signature,
							latitude: lat,
							longitude: lng,
							notes: values.notes,
							status: "Submitted"
						}
					},
					freeze: true,
					freeze_message: __("Menyimpan Bukti Pengiriman..."),
					callback: function(r) {
						if (r.message) {
							d.hide();
							frappe.show_alert({
								message: __("Proof of Delivery {0} berhasil disimpan!", [r.message.name]),
								indicator: "green"
							});
							frm.reload_doc();
						}
					}
				});
			}

			if (navigator.geolocation) {
				navigator.geolocation.getCurrentPosition(
					(pos) => {
						lat = pos.coords.latitude;
						lng = pos.coords.longitude;
						save_pod();
					},
					() => {
						// Fallback if denied or unavailable
						save_pod();
					},
					{ timeout: 5000 }
				);
			} else {
				save_pod();
			}
		}
	});

	d.show();
}
