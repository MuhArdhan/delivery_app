# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def validate_delivery_trip(doc, method=None):
	"""Prevent assigning 3PL/Ekspedisi Delivery Notes to internal fleet Delivery Trips."""
	for stop in doc.delivery_stops:
		if stop.delivery_note:
			method = frappe.db.get_value("Delivery Note", stop.delivery_note, "custom_delivery_method")
			if method == "Ekspedisi":
				frappe.throw(
					_(
						"Delivery Note <b>{0}</b> diatur untuk metode pengiriman <b>Ekspedisi</b> (3PL). "
						"Dokumen ini tidak dapat dijadwalkan ke Armada Sendiri (Delivery Trip)."
					).format(stop.delivery_note),
					title=_("Metode Pengiriman Tidak Sesuai")
				)
