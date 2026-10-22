# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from delivery_app.services.fleet_monitoring import _clean_coord, parse_geolocation


def validate_delivery_trip(doc, method=None):
	"""
	Enforce fleet routing integrity:
	1. Prevent assigning 3PL/Ekspedisi Delivery Notes to internal fleet Delivery Trips.
	2. Enforce company consistency: all Delivery Notes must belong to the trip's Company.
	3. Snapshot dispatch origin coordinates from Company master if not set.
	4. Snapshot customer delivery coordinates from Customer master if stop coordinates are empty.
	"""
	dn_companies = set()

	for stop in doc.delivery_stops:
		if not stop.delivery_note:
			continue

		dn_data = frappe.db.get_value(
			"Delivery Note",
			stop.delivery_note,
			["custom_delivery_method", "company", "customer"],
			as_dict=True
		)

		if not dn_data:
			continue

		# 1. Enforce Armada Sendiri
		if dn_data.custom_delivery_method == "Ekspedisi":
			frappe.throw(
				_(
					"Delivery Note <b>{0}</b> diatur untuk metode pengiriman <b>Ekspedisi</b> (3PL). "
					"Dokumen ini tidak dapat dijadwalkan ke trip dengan checkpoint scanner."
				).format(stop.delivery_note),
				title=_("Metode Pengiriman Tidak Sesuai")
			)

		# 2. Collect company
		if dn_data.company:
			dn_companies.add(dn_data.company)

	# Validate company consistency across all stops
	if len(dn_companies) > 1:
		frappe.throw(
			_(
				"Semua Delivery Note dalam satu trip harus berasal dari Company yang sama. "
				"Ditemukan beberapa company: {0}"
			).format(", ".join(sorted(dn_companies))),
			title=_("Company Tidak Seragam")
		)

	if dn_companies:
		target_company = next(iter(dn_companies))
		if not doc.company:
			doc.company = target_company
		elif doc.company != target_company:
			frappe.throw(
				_(
					"Company pada Delivery Trip (<b>{0}</b>) tidak sesuai dengan Company pada Delivery Note (<b>{1}</b>)."
				).format(doc.company, target_company),
				title=_("Company Mismatch")
			)

	# 3. Snapshot Company dispatch origin coordinates if missing
	if doc.company:
		orig_lat = _clean_coord(doc.get("custom_origin_latitude"))
		orig_lng = _clean_coord(doc.get("custom_origin_longitude"))
		if orig_lat is None or orig_lng is None:
			comp_coords = frappe.db.get_value("Company", doc.company, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
			c_lat = _clean_coord(comp_coords.get("custom_latitude"))
			c_lng = _clean_coord(comp_coords.get("custom_longitude"))
			if c_lat is not None and c_lng is not None:
				doc.custom_origin_latitude = c_lat
				doc.custom_origin_longitude = c_lng

	# 4. Snapshot Customer coordinates to Delivery Stop if empty
	for stop in doc.delivery_stops:
		stop_has_coords = (stop.lat is not None and stop.lng is not None and (stop.lat != 0.0 or stop.lng != 0.0))
		if not stop_has_coords and stop.customer:
			cust_coords = frappe.db.get_value("Customer", stop.customer, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
			c_lat = _clean_coord(cust_coords.get("custom_latitude"))
			c_lng = _clean_coord(cust_coords.get("custom_longitude"))
			if c_lat is not None and c_lng is not None:
				stop.lat = c_lat
				stop.lng = c_lng
