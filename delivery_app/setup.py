# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Delivery Note": [
		{
			"fieldname": "custom_sec_delivery_logistics",
			"label": "Logistics & Delivery Tracking",
			"fieldtype": "Section Break",
			"insert_after": "transporter_info",
			"collapsible": 0,
		},
		{
			"fieldname": "custom_delivery_method",
			"label": "Delivery Method",
			"fieldtype": "Select",
			"options": "Armada Sendiri\nEkspedisi",
			"default": "Armada Sendiri",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"allow_on_submit": 1,
			"insert_after": "custom_sec_delivery_logistics",
		},
		{
			"fieldname": "custom_courier_code",
			"label": "Courier (Ekspedisi)",
			"fieldtype": "Select",
			"options": "\njne: JNE Express\njnt: J&T Express\nsicepat: SiCepat Express\nanteraja: Anteraja\nninja: Ninja Xpress\npos: POS Indonesia\nsentral: Sentral Cargo\nwahana: Wahana\ntiki: TIKI\nidexpress: ID Express\nlion: Lion Parcel\ngosend: GoSend\ngrab: GrabExpress",
			"depends_on": "eval:doc.custom_delivery_method=='Ekspedisi'",
			"allow_on_submit": 1,
			"insert_after": "custom_delivery_method",
		},
		{
			"fieldname": "custom_waybill_no",
			"label": "Waybill No / No Resi (AWB)",
			"fieldtype": "Data",
			"depends_on": "eval:doc.custom_delivery_method=='Ekspedisi'",
			"allow_on_submit": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"insert_after": "custom_courier_code",
		},
		{
			"fieldname": "custom_col_break_delivery",
			"fieldtype": "Column Break",
			"insert_after": "custom_waybill_no",
		},
		{
			"fieldname": "custom_tracking_status",
			"label": "Tracking Status",
			"fieldtype": "Select",
			"options": "\nPending\nIn Transit\nDelivered\nReturned\nCancelled\nFailed",
			"default": "",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"depends_on": "eval:doc.custom_delivery_method=='Ekspedisi'",
			"allow_on_submit": 1,
			"insert_after": "custom_col_break_delivery",
		},
		{
			"fieldname": "custom_last_tracking_update",
			"label": "Last Tracking Update",
			"fieldtype": "Datetime",
			"read_only": 1,
			"depends_on": "eval:doc.custom_delivery_method=='Ekspedisi'",
			"allow_on_submit": 1,
			"insert_after": "custom_tracking_status",
		},
		{
			"fieldname": "custom_pod_status",
			"label": "POD Status",
			"fieldtype": "Select",
			"options": "Pending\nDelivered\nFailed",
			"default": "Pending",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"depends_on": "eval:doc.custom_delivery_method=='Armada Sendiri'",
			"allow_on_submit": 1,
			"insert_after": "custom_last_tracking_update",
		},
		{
			"fieldname": "custom_proof_of_delivery",
			"label": "Proof of Delivery",
			"fieldtype": "Link",
			"options": "Proof of Delivery",
			"read_only": 1,
			"depends_on": "eval:doc.custom_delivery_method=='Armada Sendiri' && doc.custom_proof_of_delivery",
			"allow_on_submit": 1,
			"insert_after": "custom_pod_status",
		},
		{
			"fieldname": "custom_sec_tracking_history",
			"label": "Live Tracking Timeline",
			"fieldtype": "Section Break",
			"collapsible": 1,
			"depends_on": "eval:doc.custom_delivery_method=='Ekspedisi' && doc.custom_waybill_no",
			"insert_after": "custom_proof_of_delivery",
		},
		{
			"fieldname": "custom_tracking_history_html",
			"label": "Tracking History Timeline",
			"fieldtype": "Long Text",
			"hidden": 1,
			"allow_on_submit": 1,
			"insert_after": "custom_sec_tracking_history",
		},
	],
	"Delivery Stop": [
		{
			"fieldname": "custom_proof_of_delivery",
			"label": "Proof of Delivery",
			"fieldtype": "Link",
			"options": "Proof of Delivery",
			"read_only": 1,
			"in_list_view": 1,
			"allow_on_submit": 1,
			"insert_after": "visited",
		}
	],
	"Customer": [
		{
			"fieldname": "custom_latitude",
			"label": "Latitude",
			"fieldtype": "Float",
			"insert_after": "customer_primary_address",
		},
		{
			"fieldname": "custom_longitude",
			"label": "Longitude",
			"fieldtype": "Float",
			"insert_after": "custom_latitude",
		},
	],
	"Company": [
		{
			"fieldname": "custom_latitude",
			"label": "Latitude",
			"fieldtype": "Float",
			"insert_after": "company_name",
		},
		{
			"fieldname": "custom_longitude",
			"label": "Longitude",
			"fieldtype": "Float",
			"insert_after": "custom_latitude",
		},
	],
	"Delivery Trip": [
		{
			"fieldname": "custom_origin_latitude",
			"label": "Origin Latitude",
			"fieldtype": "Float",
			"insert_after": "departure_time",
			"allow_on_submit": 1,
		},
		{
			"fieldname": "custom_origin_longitude",
			"label": "Origin Longitude",
			"fieldtype": "Float",
			"insert_after": "custom_origin_latitude",
			"allow_on_submit": 1,
		},
		{
			"fieldname": "custom_actual_departure",
			"label": "Waktu Berangkat Aktual",
			"fieldtype": "Datetime",
			"read_only": 1,
			"allow_on_submit": 1,
			"insert_after": "custom_origin_longitude",
		},
		{
			"fieldname": "custom_departed_by",
			"label": "Diberangkatkan Oleh",
			"fieldtype": "Link",
			"options": "User",
			"read_only": 1,
			"allow_on_submit": 1,
			"insert_after": "custom_actual_departure",
		},
	],
}


def ensure_custom_fields():
	# Clean up any obsolete geolocation fields if present
	obsolete = [
		("Customer", "custom_delivery_location"),
		("Company", "custom_dispatch_location"),
		("Delivery Trip", "custom_origin_location"),
	]
	for dt, fld in obsolete:
		cf = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fld}, "name")
		if cf:
			frappe.delete_doc("Custom Field", cf, ignore_permissions=True)

	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.db.commit()


def setup():
	ensure_custom_fields()
