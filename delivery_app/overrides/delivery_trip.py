# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from delivery_app.services.fleet_monitoring import parse_geolocation


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
					"Dokumen ini tidak dapat dijadwalkan ke Armada Sendiri (Delivery Trip)."
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

	# 3. Snapshot Company dispatch origin location if missing
	if doc.company and not doc.get("custom_origin_location"):
		comp_loc = frappe.db.get_value("Company", doc.company, "custom_dispatch_location")
		if comp_loc:
			doc.custom_origin_location = comp_loc

	# 4. Snapshot Customer delivery coordinates to Delivery Stop if empty
	for stop in doc.delivery_stops:
		stop_has_coords = (stop.lat is not None and stop.lng is not None and (stop.lat != 0.0 or stop.lng != 0.0))
		if not stop_has_coords and stop.customer:
			cust_loc = frappe.db.get_value("Customer", stop.customer, "custom_delivery_location")
			if cust_loc:
				lat, lng = parse_geolocation(cust_loc)
				if lat is not None and lng is not None:
					stop.lat = lat
					stop.lng = lng

