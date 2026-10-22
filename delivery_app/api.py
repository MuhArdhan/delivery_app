# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import base64
import json
import frappe
from frappe import _
from frappe.utils import now_datetime, getdate, format_datetime
from frappe.utils.file_manager import save_file

from delivery_app.services.fleet_monitoring import (
	_clean_coord,
	compute_trip_monitoring_status,
	format_point_geojson,
	get_trip_scan_history,
	is_valid_coord_pair,
	parse_geolocation,
)


COURIER_LIST = [
	{"code": "jne", "name": "JNE Express", "services": ["REG", "YES", "JTR (Kargo)"], "badge": "jne"},
	{"code": "jnt", "name": "J&T Express", "services": ["EZ", "J&T Super", "J&T Cargo"], "badge": "jnt"},
	{"code": "sicepat", "name": "SiCepat Express", "services": ["SIUNT", "BEST", "GOKIL (Kargo)"], "badge": "sicepat"},
	{"code": "anteraja", "name": "Anteraja", "services": ["Regular", "Next Day", "Cargo"], "badge": "anteraja"},
	{"code": "ninja", "name": "Ninja Xpress", "services": ["Standard", "Fast"], "badge": "ninja"},
	{"code": "pos", "name": "POS Indonesia", "services": ["Pos Reguler", "Pos Nextday", "Pos Jumbo"], "badge": "pos"},
	{"code": "sentral", "name": "Sentral Cargo", "services": ["Kargo Darat", "Kargo Udara"], "badge": "sentral"},
	{"code": "wahana", "name": "Wahana Express", "services": ["Ekonomis", "Kargo"], "badge": "wahana"},
	{"code": "tiki", "name": "TIKI", "services": ["REG", "ONS", "TRC"], "badge": "tiki"},
	{"code": "idexpress", "name": "ID Express", "services": ["Standard", "Cargo"], "badge": "idexpress"},
	{"code": "lion", "name": "Lion Parcel", "services": ["REPACK", "ONEPACK", "JAGOPACK", "BIGPACK"], "badge": "lion"},
	{"code": "gosend", "name": "GoSend Instant", "services": ["Instant", "SameDay"], "badge": "gosend"},
	{"code": "grab", "name": "GrabExpress", "services": ["Instant", "SameDay"], "badge": "grab"},
]


COURIER_OPTION_MAP = {
	c["code"]: f"{c['code']}: {c['name']}" for c in COURIER_LIST
}


# ==============================================================================
# 1. DRIVER PORTAL APIS (Existing & Mobile Navigator)
# ==============================================================================

@frappe.whitelist()
def get_driver_profile():
	"""Get current user's linked driver record if any."""
	user = frappe.session.user
	driver = frappe.db.get_value("Driver", {"user": user}, ["name", "full_name", "cell_number"], as_dict=True)
	if not driver:
		employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if employee:
			driver = frappe.db.get_value("Driver", {"employee": employee}, ["name", "full_name", "cell_number"], as_dict=True)

	return driver


@frappe.whitelist()
def get_active_trips():
	"""Get active Delivery Trips for the logged-in driver (or all active trips if manager)."""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	is_manager = "System Manager" in roles or "Delivery Manager" in roles or "Stock Manager" in roles

	driver = get_driver_profile()
	filters = {
		"status": ["in", ["Draft", "Scheduled", "In Transit"]],
		"docstatus": ["in", [0, 1]],
	}

	if driver and not is_manager:
		filters["driver"] = driver.name

	trips = frappe.get_all(
		"Delivery Trip",
		filters=filters,
		fields=["name", "departure_time", "driver", "driver_name", "vehicle", "status", "total_distance", "uom", "modified"],
		order_by="modified desc",
		limit=20,
	)

	result = []
	for trip_summary in trips:
		trip_doc = frappe.get_doc("Delivery Trip", trip_summary.name)
		stops = []
		for stop in trip_doc.delivery_stops:
			phone = ""
			if stop.customer:
				contact_name = frappe.db.get_value("Dynamic Link", {"link_doctype": "Customer", "link_name": stop.customer, "parenttype": "Contact"}, "parent")
				if contact_name:
					phone = frappe.db.get_value("Contact", contact_name, "mobile_no") or frappe.db.get_value("Contact", contact_name, "phone") or ""

			address_display = stop.customer_address or ""
			if not address_display and stop.address:
				addr_doc = frappe.db.get_value("Address", stop.address, ["address_line1", "city"], as_dict=True)
				if addr_doc:
					address_display = f"{addr_doc.address_line1 or ''}, {addr_doc.city or ''}"

			dn_pod_status = ""
			if stop.delivery_note:
				dn_pod_status = frappe.db.get_value("Delivery Note", stop.delivery_note, "custom_pod_status") or "Pending"

			stops.append({
				"idx": stop.idx,
				"name": stop.name,
				"customer": stop.customer,
				"customer_address": address_display,
				"phone": phone,
				"lat": stop.lat,
				"lng": stop.lng,
				"delivery_note": stop.delivery_note,
				"visited": stop.visited,
				"pod_status": dn_pod_status,
				"custom_proof_of_delivery": getattr(stop, "custom_proof_of_delivery", None),
				"details": stop.details or "",
				"estimated_arrival": str(stop.estimated_arrival or ""),
			})

		trip_summary["stops"] = stops
		trip_summary["total_stops"] = len(stops)
		trip_summary["completed_stops"] = sum(1 for s in stops if s["visited"])
		result.append(trip_summary)

	return result


@frappe.whitelist()
def start_trip(trip_name: str):
	"""
	Confirm and record actual departure for a Delivery Trip.
	Idempotently sets custom_actual_departure and custom_departed_by.
	Updates status to In Transit.
	"""
	trip = frappe.get_doc("Delivery Trip", trip_name)
	if trip.docstatus == 2:
		frappe.throw(_("Delivery Trip {0} sudah dibatalkan.").format(trip.name))
	if trip.status == "Completed":
		frappe.throw(_("Delivery Trip {0} sudah selesai.").format(trip.name))

	now = now_datetime()
	actual_departure = trip.get("custom_actual_departure") or now
	departed_by = trip.get("custom_departed_by") or frappe.session.user

	update_dict = {
		"status": "In Transit",
		"custom_actual_departure": actual_departure,
		"custom_departed_by": departed_by,
	}
	frappe.db.set_value("Delivery Trip", trip_name, update_dict, update_modified=True)
	frappe.db.commit()
	return {
		"success": True,
		"status": "In Transit",
		"actual_departure": actual_departure,
		"departed_by": departed_by,
	}


@frappe.whitelist()
def mark_trip_departed(trip_name: str):
	"""Alias for start_trip to mark departure."""
	return start_trip(trip_name)


@frappe.whitelist()
def submit_pod(
	delivery_note: str,
	recipient_name: str,
	recipient_relationship: str = "Yang Bersangkutan",
	recipient_phone: str = None,
	proof_photo_data: str = None,
	signature_data: str = None,
	latitude: float = None,
	longitude: float = None,
	location_address: str = None,
	delivery_trip: str = None,
	delivery_stop: str = None,
	notes: str = None,
):
	"""Whitelisted method to submit digital Proof of Delivery from Driver Mobile Portal or SPA."""
	if not delivery_note:
		frappe.throw(_("Delivery Note is required."))
	if not recipient_name:
		frappe.throw(_("Recipient Name is required."))
	if not proof_photo_data:
		frappe.throw(_("Proof photo is required."))

	proof_photo_url = proof_photo_data
	if proof_photo_data and proof_photo_data.startswith("data:image"):
		try:
			header, encoded = proof_photo_data.split(",", 1)
			file_ext = "jpg"
			if "png" in header:
				file_ext = "png"
			file_bytes = base64.b64decode(encoded)
			filename = f"pod_{delivery_note}_{now_datetime().strftime('%Y%m%d%H%M%S')}.{file_ext}"
			saved_file = save_file(filename, file_bytes, "Proof of Delivery", None, is_private=0)
			proof_photo_url = saved_file.file_url
		except Exception as e:
			frappe.log_error(f"Error saving POD photo file: {e}", "POD Photo Error")

	signature_url = signature_data
	if signature_data and signature_data.startswith("data:image"):
		try:
			header, encoded = signature_data.split(",", 1)
			file_bytes = base64.b64decode(encoded)
			filename = f"sig_{delivery_note}_{now_datetime().strftime('%Y%m%d%H%M%S')}.png"
			saved_file = save_file(filename, file_bytes, "Proof of Delivery", None, is_private=0)
			signature_url = saved_file.file_url
		except Exception as e:
			frappe.log_error(f"Error saving POD signature file: {e}", "POD Signature Error")

	pod = frappe.new_doc("Proof of Delivery")
	pod.delivery_note = delivery_note
	pod.delivery_trip = delivery_trip
	pod.delivery_stop = delivery_stop
	pod.recipient_name = recipient_name
	pod.recipient_relationship = recipient_relationship
	pod.recipient_phone = recipient_phone
	pod.proof_photo = proof_photo_url
	pod.signature = signature_url
	pod.latitude = float(latitude) if latitude else None
	pod.longitude = float(longitude) if longitude else None
	pod.location_address = location_address
	pod.notes = notes
	pod.submitted_at = now_datetime()
	pod.delivered_by = frappe.session.user
	pod.status = "Submitted"

	pod.flags.ignore_permissions = True
	pod.insert()
	frappe.db.commit()

	return {
		"success": True,
		"pod_name": pod.name,
		"delivery_note": delivery_note,
		"status": pod.status,
	}


# ==============================================================================
# 2. FLEETBASE OPERATIONS CONSOLE SPA APIS
# ==============================================================================

@frappe.whitelist()
def get_operations_summary():
	"""KPIs, Real Map Points, and Recent Activity for Fleet Operations."""
	today = getdate()

	# 1. Total pending delivery notes needing scheduling (Armada Sendiri not on an active trip)
	pending_notes = frappe.db.sql("""
		SELECT count(name) FROM `tabDelivery Note`
		WHERE docstatus = 1
		AND status NOT IN ('Cancelled', 'Closed')
		AND (
			(custom_delivery_method = 'Armada Sendiri' AND (custom_pod_status IS NULL OR custom_pod_status = 'Pending') AND (delivery_trip IS NULL OR delivery_trip = ''))
			OR
			(custom_delivery_method = 'Ekspedisi' AND (custom_tracking_status IS NULL OR custom_tracking_status IN ('', 'Pending')))
			OR
			(custom_delivery_method IS NULL AND (delivery_trip IS NULL OR delivery_trip = ''))
		)
	""")[0][0] or 0

	# 2. Active Trips
	active_trips_count = frappe.db.sql("""
		SELECT count(name) FROM `tabDelivery Trip`
		WHERE docstatus IN (0, 1)
		AND status IN ('Draft', 'Scheduled', 'In Transit')
	""")[0][0] or 0

	# 3. Scheduled Trips
	scheduled_trips_count = frappe.db.sql("""
		SELECT count(name) FROM `tabDelivery Trip`
		WHERE docstatus = 1
		AND status = 'Scheduled'
	""")[0][0] or 0

	# 4. In Transit Trips
	in_transit_trips_count = frappe.db.sql("""
		SELECT count(name) FROM `tabDelivery Trip`
		WHERE docstatus = 1
		AND status = 'In Transit'
	""")[0][0] or 0

	# 5. 3PL Couriers in transit
	in_transit_couriers = frappe.db.sql("""
		SELECT count(name) FROM `tabDelivery Note`
		WHERE docstatus = 1
		AND custom_delivery_method = 'Ekspedisi'
		AND custom_tracking_status = 'In Transit'
	""")[0][0] or 0

	# 6. Delivered today
	delivered_today = frappe.db.sql("""
		SELECT count(name) FROM `tabProof of Delivery`
		WHERE DATE(submitted_at) = %s
	""", (today,))[0][0] or 0

	if not delivered_today:
		delivered_today = frappe.db.sql("""
			SELECT count(name) FROM `tabDelivery Note`
			WHERE docstatus = 1
			AND (custom_pod_status = 'Delivered' OR custom_tracking_status = 'Delivered')
			AND DATE(modified) = %s
		""", (today,))[0][0] or 0

	# Total Vehicles & Drivers
	total_vehicles = frappe.db.count("Vehicle")
	total_drivers = frappe.db.count("Driver")

	# Fetch Real Map Points from active trips and recent notes (no synthetic demo coordinates)
	map_markers = []
	unlocated_count = 0
	companies_seen = set()

	# A. Active Trips & Stops
	active_trips = frappe.db.sql("""
		SELECT dt.name, dt.company, dt.driver_name, dt.vehicle, dt.status,
		       dt.custom_origin_latitude, dt.custom_origin_longitude
		FROM `tabDelivery Trip` dt
		WHERE dt.docstatus IN (0, 1)
		AND dt.status IN ('Scheduled', 'In Transit')
		ORDER BY dt.modified DESC
		LIMIT 15
	""", as_dict=True)

	for trip in active_trips:
		# Company dispatch origin
		if trip.company and trip.company not in companies_seen:
			companies_seen.add(trip.company)
			orig_lat = _clean_coord(trip.get("custom_origin_latitude"))
			orig_lng = _clean_coord(trip.get("custom_origin_longitude"))
			if not is_valid_coord_pair(orig_lat, orig_lng):
				comp_coords = frappe.db.get_value("Company", trip.company, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
				orig_lat = _clean_coord(comp_coords.get("custom_latitude"))
				orig_lng = _clean_coord(comp_coords.get("custom_longitude"))

			if is_valid_coord_pair(orig_lat, orig_lng):
				map_markers.append({
					"id": f"ORIGIN-{trip.company}",
					"type": "origin",
					"trip_id": trip.name,
					"customer": f"Gudang: {trip.company}",
					"address": trip.company,
					"method": "Armada Sendiri",
					"status": "Asal Keberangkatan",
					"lat": orig_lat,
					"lng": orig_lng,
					"has_coordinates": True,
					"grand_total": 0,
				})

		# Trip stops
		stops = frappe.db.sql("""
			SELECT idx, customer, delivery_note, visited, customer_address, details, lat, lng
			FROM `tabDelivery Stop`
			WHERE parent = %s
			ORDER BY idx ASC
		""", (trip.name,), as_dict=True)

		for s in stops:
			s_lat = _clean_coord(s.get("lat"))
			s_lng = _clean_coord(s.get("lng"))
			if not is_valid_coord_pair(s_lat, s_lng):
				if s.get("customer"):
					c_coords = frappe.db.get_value("Customer", s["customer"], ["custom_latitude", "custom_longitude"], as_dict=True) or {}
					s_lat = _clean_coord(c_coords.get("custom_latitude"))
					s_lng = _clean_coord(c_coords.get("custom_longitude"))

			if is_valid_coord_pair(s_lat, s_lng):
				map_markers.append({
					"id": s.get("delivery_note") or f"{trip.name}-stop-{s.get('idx')}",
					"type": "stop",
					"trip_id": trip.name,
					"customer": s.get("customer") or "Pelanggan",
					"address": (s.get("customer_address") or "").replace("<br>", ", ").strip(),
					"method": "Armada Sendiri",
					"status": "Terkirim" if s.get("visited") else "Dalam Pengiriman",
					"visited": bool(s.get("visited")),
					"lat": s_lat,
					"lng": s_lng,
					"has_coordinates": True,
					"grand_total": 0,
				})
			else:
				unlocated_count += 1

	# B. Unassigned recent submitted notes
	unassigned_notes = frappe.db.sql("""
		SELECT dn.name, dn.customer, dn.customer_name, dn.shipping_address, dn.shipping_address_name,
		       dn.custom_delivery_method, dn.grand_total
		FROM `tabDelivery Note` dn
		WHERE dn.docstatus = 1
		AND (dn.delivery_trip IS NULL OR dn.delivery_trip = '')
		AND (dn.custom_pod_status IS NULL OR dn.custom_pod_status = 'Pending')
		ORDER BY dn.creation DESC
		LIMIT 20
	""", as_dict=True)

	for note in unassigned_notes:
		c_coords = frappe.db.get_value("Customer", note["customer"], ["custom_latitude", "custom_longitude"], as_dict=True) or {}
		c_lat = _clean_coord(c_coords.get("custom_latitude"))
		c_lng = _clean_coord(c_coords.get("custom_longitude"))
		if is_valid_coord_pair(c_lat, c_lng):
			map_markers.append({
				"id": note["name"],
				"type": "note",
				"customer": note.get("customer_name") or note["customer"],
				"address": (note.get("shipping_address") or "").replace("<br>", ", ").strip(),
				"method": note.get("custom_delivery_method") or "Armada Sendiri",
				"status": "Siap Kirim",
				"visited": False,
				"lat": c_lat,
				"lng": c_lng,
				"has_coordinates": True,
				"grand_total": note.get("grand_total") or 0,
			})
		else:
			unlocated_count += 1

	# Recent activity log
	activity_log = []
	recent_trips = frappe.get_all(
		"Delivery Trip",
		fields=["name", "driver_name", "vehicle", "status", "modified"],
		order_by="modified desc",
		limit=5
	)
	for t in recent_trips:
		activity_log.append({
			"type": "trip",
			"title": f"Trip {t.name}",
			"description": f"Driver {t.driver_name or 'N/A'} ({t.vehicle or 'N/A'}) · Status: {t.status}",
			"time": format_datetime(t.modified, "dd MMM yyyy, HH:mm"),
			"status": t.status,
			"link": f"#/trips/{t.name}"
		})

	recent_pods = frappe.get_all(
		"Proof of Delivery",
		fields=["name", "delivery_note", "recipient_name", "status", "submitted_at"],
		order_by="submitted_at desc",
		limit=5
	)
	for p in recent_pods:
		activity_log.append({
			"type": "pod",
			"title": f"POD: {p.delivery_note}",
			"description": f"Diterima oleh {p.recipient_name} · Status: {p.status}",
			"time": format_datetime(p.submitted_at, "dd MMM yyyy, HH:mm"),
			"status": p.status,
			"link": f"#/pod"
		})

	return {
		"kpi": {
			"pending_orders": pending_notes,
			"active_trips": active_trips_count,
			"scheduled_trips": scheduled_trips_count,
			"in_transit_trips": in_transit_trips_count,
			"in_transit_couriers": in_transit_couriers,
			"delivered_today": delivered_today,
			"total_vehicles": total_vehicles,
			"total_drivers": total_drivers,
		},
		"map_markers": map_markers,
		"unlocated_count": unlocated_count,
		"activity_log": activity_log,
	}


@frappe.whitelist()
def get_delivery_notes(status_filter=None, method_filter=None, search=None, page=1, page_size=20):
	"""List Delivery Notes with rich logistics status, stops link, and preview items."""
	page = int(page)
	page_size = int(page_size)
	offset = (page - 1) * page_size

	conditions = ["dn.docstatus = 1"]
	params = {}

	if status_filter:
		if status_filter == "Ready":
			conditions.append("""(
				(dn.custom_delivery_method = 'Armada Sendiri' AND (dn.custom_pod_status IS NULL OR dn.custom_pod_status = 'Pending'))
				OR
				(dn.custom_delivery_method = 'Ekspedisi' AND (dn.custom_tracking_status IS NULL OR dn.custom_tracking_status = 'Pending' OR dn.custom_waybill_no IS NULL))
			)""")
		elif status_filter == "In Transit":
			conditions.append("""(
				dn.custom_tracking_status = 'In Transit'
				OR EXISTS (
					SELECT 1 FROM `tabDelivery Stop` ds
					INNER JOIN `tabDelivery Trip` dt ON dt.name = ds.parent
					WHERE ds.delivery_note = dn.name AND dt.status = 'In Transit' AND ds.visited = 0
				)
			)""")
		elif status_filter == "Delivered":
			conditions.append("(dn.custom_pod_status = 'Delivered' OR dn.custom_tracking_status = 'Delivered')")

	if method_filter and method_filter != "All":
		conditions.append("dn.custom_delivery_method = %(method)s")
		params["method"] = method_filter

	if search:
		conditions.append("""(
			dn.name LIKE %(search)s
			OR dn.customer LIKE %(search)s
			OR dn.customer_name LIKE %(search)s
			OR dn.custom_waybill_no LIKE %(search)s
			OR dn.shipping_address LIKE %(search)s
		)""")
		params["search"] = f"%{search}%"

	where_clause = " AND ".join(conditions)

	total_count = frappe.db.sql(f"""
		SELECT count(dn.name)
		FROM `tabDelivery Note` dn
		WHERE {where_clause}
	""", params)[0][0] or 0

	query = f"""
		SELECT
			dn.name, dn.customer, dn.customer_name, dn.posting_date, dn.posting_time,
			dn.grand_total, dn.total_qty, dn.status, dn.custom_delivery_method,
			dn.custom_courier_code, dn.custom_waybill_no, dn.custom_tracking_status,
			dn.custom_last_tracking_update, dn.custom_tracking_history_html,
			dn.custom_pod_status, dn.custom_proof_of_delivery, dn.shipping_address,
			dn.contact_display, dn.contact_mobile, dn.contact_email
		FROM `tabDelivery Note` dn
		WHERE {where_clause}
		ORDER BY dn.creation DESC
		LIMIT {page_size} OFFSET {offset}
	"""

	notes = frappe.db.sql(query, params, as_dict=True)

	# Batch resolve items & trip links
	dn_names = [n["name"] for n in notes]
	items_by_dn = {}
	trips_by_dn = {}

	if dn_names:
		items = frappe.db.sql("""
			SELECT parent, item_code, item_name, qty, uom
			FROM `tabDelivery Note Item`
			WHERE parent IN %(names)s
			ORDER BY idx ASC
		""", {"names": dn_names}, as_dict=True)

		for item in items:
			items_by_dn.setdefault(item["parent"], []).append({
				"item_code": item["item_code"],
				"item_name": item["item_name"],
				"qty": item["qty"],
				"uom": item["uom"]
			})

		stops = frappe.db.sql("""
			SELECT ds.delivery_note, ds.parent as trip_name, ds.visited, dt.status as trip_status, dt.driver_name, dt.vehicle
			FROM `tabDelivery Stop` ds
			INNER JOIN `tabDelivery Trip` dt ON dt.name = ds.parent
			WHERE ds.delivery_note IN %(names)s
			AND dt.status NOT IN ('Cancelled')
		""", {"names": dn_names}, as_dict=True)

		for s in stops:
			trips_by_dn[s["delivery_note"]] = {
				"trip_name": s["trip_name"],
				"trip_status": s["trip_status"],
				"visited": s["visited"],
				"driver_name": s["driver_name"],
				"vehicle": s["vehicle"],
			}

	for note in notes:
		note["items"] = items_by_dn.get(note["name"], [])
		note["trip"] = trips_by_dn.get(note["name"])
		# Formatted address string
		raw_addr = note.get("shipping_address") or ""
		clean_addr = raw_addr.replace("<br>", ", ").replace("\n", ", ").strip()
		note["address_display"] = clean_addr

	return {
		"items": notes,
		"total_count": total_count,
		"page": page,
		"page_size": page_size,
	}


@frappe.whitelist()
def get_delivery_note_detail(delivery_note: str):
	"""Fetch complete Delivery Note details, timeline, and Proof of Delivery."""
	if not delivery_note:
		frappe.throw(_("Delivery Note name is required."))

	dn = frappe.get_doc("Delivery Note", delivery_note)
	detail = dn.as_dict()

	# Resolve POD if exists
	pod_data = None
	if dn.custom_proof_of_delivery:
		pod = frappe.get_doc("Proof of Delivery", dn.custom_proof_of_delivery)
		pod_data = pod.as_dict()
	elif frappe.db.exists("Proof of Delivery", {"delivery_note": delivery_note}):
		pod_name = frappe.db.get_value("Proof of Delivery", {"delivery_note": delivery_note}, "name")
		pod = frappe.get_doc("Proof of Delivery", pod_name)
		pod_data = pod.as_dict()

	detail["pod"] = pod_data

	# Resolve active trip if exists
	trip_link = frappe.db.sql("""
		SELECT ds.parent as trip_name, ds.idx, ds.visited, dt.status, dt.driver_name, dt.vehicle, dt.departure_time
		FROM `tabDelivery Stop` ds
		INNER JOIN `tabDelivery Trip` dt ON dt.name = ds.parent
		WHERE ds.delivery_note = %s
		ORDER BY dt.creation DESC
		LIMIT 1
	""", (delivery_note,), as_dict=True)

	detail["trip"] = trip_link[0] if trip_link else None

	# Format address
	addr_text = (dn.shipping_address or dn.customer_address or "").replace("<br>", "\n").strip()
	detail["clean_address"] = addr_text

	return detail


@frappe.whitelist()
def dispatch_ekspedisi(delivery_note: str, courier_code: str, waybill_no: str = None, courier_service: str = None, notes: str = None):
	"""Set Delivery Note to 3PL Expedition with waybill resi and trigger tracking sync."""
	if not delivery_note:
		frappe.throw(_("Delivery Note is required."))
	if not courier_code:
		frappe.throw(_("Courier is required."))

	dn = frappe.get_doc("Delivery Note", delivery_note)
	dn.custom_delivery_method = "Ekspedisi"
	
	# Match select option label
	clean_courier = courier_code.split(":")[0].strip().lower()
	dn.custom_courier_code = COURIER_OPTION_MAP.get(clean_courier, courier_code)

	if waybill_no:
		dn.custom_waybill_no = waybill_no.strip().upper()
		dn.custom_tracking_status = "In Transit"
	else:
		dn.custom_tracking_status = "Pending"

	dn.custom_last_tracking_update = now_datetime()
	dn.flags.ignore_validate_update_after_submit = True
	dn.flags.ignore_permissions = True
	dn.save()
	frappe.db.commit()

	# If waybill provided, trigger live tracking sync in background or immediately
	tracking_result = None
	if waybill_no:
		from delivery_app.services.biteship import fetch_biteship_tracking, render_tracking_timeline_html
		try:
			track_data = fetch_biteship_tracking(waybill_no, courier_code)
			if track_data.get("success"):
				dn.custom_tracking_status = track_data.get("status")
				dn.custom_tracking_history_html = render_tracking_timeline_html(track_data)
				dn.save()
				frappe.db.commit()
				tracking_result = track_data
		except Exception as e:
			frappe.log_error(f"Error fetching tracking on dispatch: {e}")

	return {
		"success": True,
		"delivery_note": dn.name,
		"courier": courier_code,
		"waybill_no": dn.custom_waybill_no,
		"tracking_status": dn.custom_tracking_status,
		"tracking_result": tracking_result,
	}


@frappe.whitelist()
def get_eligible_delivery_notes_for_trip(company: str = None):
	"""
	Fetch submitted Delivery Notes eligible for assignment to an Armada Sendiri Delivery Trip.
	Must not belong to another active (Draft, Scheduled, In Transit) Delivery Trip.
	Excludes Ekspedisi notes.
	Returns coordinate info from Customer master.
	"""
	conditions = [
		"dn.docstatus = 1",
		"dn.status NOT IN ('Cancelled', 'Closed')",
		"(dn.custom_delivery_method IS NULL OR dn.custom_delivery_method != 'Ekspedisi')",
		"(dn.custom_pod_status IS NULL OR dn.custom_pod_status != 'Delivered')",
	]
	params = {}

	if company:
		conditions.append("dn.company = %(company)s")
		params["company"] = company

	where_clause = " AND ".join(conditions)

	notes = frappe.db.sql(f"""
		SELECT
			dn.name, dn.customer, dn.customer_name, dn.company, dn.posting_date,
			dn.grand_total, dn.shipping_address_name, dn.shipping_address, dn.delivery_trip
		FROM `tabDelivery Note` dn
		WHERE {where_clause}
		ORDER BY dn.creation DESC
		LIMIT 50
	""", params, as_dict=True)

	# Active Delivery Trips
	active_trips = set(
		frappe.db.sql_list("""
			SELECT dt.name FROM `tabDelivery Trip` dt
			WHERE dt.docstatus IN (0, 1) AND dt.status IN ('Draft', 'Scheduled', 'In Transit')
		""")
	)

	eligible = []
	for n in notes:
		if n.get("delivery_trip") and n["delivery_trip"] in active_trips:
			continue

		if active_trips:
			in_active_stop = frappe.db.sql("""
				SELECT 1 FROM `tabDelivery Stop` ds
				WHERE ds.delivery_note = %s AND ds.parent IN %s
			""", (n["name"], tuple(active_trips)))
			if in_active_stop:
				continue

		# Customer coordinates
		c_coords = frappe.db.get_value("Customer", n["customer"], ["custom_latitude", "custom_longitude"], as_dict=True) or {}
		lat = _clean_coord(c_coords.get("custom_latitude"))
		lng = _clean_coord(c_coords.get("custom_longitude"))

		addr_text = (n.get("shipping_address") or "").replace("<br>", ", ").strip()

		eligible.append({
			"name": n["name"],
			"customer": n["customer"],
			"customer_name": n["customer_name"] or n["customer"],
			"company": n["company"],
			"posting_date": str(n["posting_date"]),
			"grand_total": n["grand_total"],
			"shipping_address_name": n.get("shipping_address_name") or "",
			"customer_address": addr_text,
			"lat": lat,
			"lng": lng,
			"has_coordinates": bool(lat is not None and lng is not None)
		})

	return eligible


@frappe.whitelist()
def create_delivery_trip(driver: str, vehicle: str, departure_time: str = None, stops: str = None, company: str = None):
	"""Create native ERPNext Delivery Trip with sequenced stops from Delivery Notes."""
	if not driver:
		frappe.throw(_("Driver is required."))
	if not vehicle:
		frappe.throw(_("Vehicle is required."))

	if isinstance(stops, str):
		stops = json.loads(stops)

	if not stops:
		frappe.throw(_("At least one Delivery Stop is required."))

	# Validate no Ekspedisi notes are included and check company consistency
	dn_companies = set()
	for stop_data in stops:
		dn_name = stop_data.get("delivery_note")
		if dn_name:
			dn_info = frappe.db.get_value("Delivery Note", dn_name, ["custom_delivery_method", "company"], as_dict=True)
			if dn_info:
				if dn_info.custom_delivery_method == "Ekspedisi":
					frappe.throw(_("Delivery Note {0} menggunakan tracking resi ekspedisi dan tidak dapat dijadwalkan ke trip dengan checkpoint scanner.").format(dn_name))
				if dn_info.company:
					dn_companies.add(dn_info.company)

	# Validate company consistency across all stops
	if len(dn_companies) > 1:
		frappe.throw(_("Semua Delivery Note dalam satu trip harus berasal dari Company yang sama: {0}").format(", ".join(sorted(dn_companies))))

	if dn_companies:
		target_company = next(iter(dn_companies))
		if company and company != target_company:
			frappe.throw(_("Company yang dipilih ({0}) berbeda dengan Company pada Delivery Note ({1}).").format(company, target_company))
		company = target_company
	elif not company:
		company = frappe.db.get_single_value("Global Defaults", "default_company")

	trip = frappe.new_doc("Delivery Trip")
	trip.company = company
	trip.driver = driver
	trip.vehicle = vehicle
	trip.departure_time = departure_time or now_datetime()
	trip.status = "Draft"

	# Snapshot Company dispatch origin coordinates as trip origin
	if company:
		comp_coords = frappe.db.get_value("Company", company, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
		c_lat = _clean_coord(comp_coords.get("custom_latitude"))
		c_lng = _clean_coord(comp_coords.get("custom_longitude"))
		if c_lat is not None and c_lng is not None:
			trip.custom_origin_latitude = c_lat
			trip.custom_origin_longitude = c_lng

	# Add stops
	for idx, s in enumerate(stops, 1):
		dn_name = s.get("delivery_note")
		dn_doc = frappe.get_doc("Delivery Note", dn_name) if dn_name else None

		customer_name = s.get("customer") or (dn_doc.customer if dn_doc else "")

		# Resolve coordinates: priority is passed coordinates, fallback to Customer master
		stop_lat = _clean_coord(s.get("lat"))
		stop_lng = _clean_coord(s.get("lng"))
		if stop_lat is None or stop_lng is None:
			if customer_name:
				c_coords = frappe.db.get_value("Customer", customer_name, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
				stop_lat = _clean_coord(c_coords.get("custom_latitude"))
				stop_lng = _clean_coord(c_coords.get("custom_longitude"))

		stop_row = trip.append("delivery_stops", {})
		stop_row.customer = customer_name
		stop_row.delivery_note = dn_name
		stop_row.address = s.get("address") or (dn_doc.shipping_address_name if dn_doc else "")
		stop_row.customer_address = s.get("customer_address") or (dn_doc.shipping_address if dn_doc else "")
		stop_row.grand_total = dn_doc.grand_total if dn_doc else 0
		stop_row.contact = dn_doc.contact_person if dn_doc else None
		stop_row.lat = stop_lat
		stop_row.lng = stop_lng
		stop_row.details = s.get("details") or ""
		stop_row.visited = 0

	trip.insert()

	# Mark Delivery Notes as Armada Sendiri & In Progress
	for s in stops:
		dn_name = s.get("delivery_note")
		if dn_name:
			frappe.db.set_value("Delivery Note", dn_name, {
				"custom_delivery_method": "Armada Sendiri",
				"custom_pod_status": "Pending"
			}, update_modified=False)

	frappe.db.commit()

	return {
		"success": True,
		"trip_name": trip.name,
		"driver": trip.driver,
		"vehicle": trip.vehicle,
		"company": trip.company,
		"status": trip.status,
		"total_stops": len(trip.delivery_stops)
	}


@frappe.whitelist()
def submit_delivery_trip(trip_name: str):
	"""Submit trip and set status to Scheduled."""
	trip = frappe.get_doc("Delivery Trip", trip_name)
	if trip.docstatus == 0:
		trip.submit()
	trip.status = "Scheduled"
	trip.save()
	frappe.db.commit()
	return {"success": True, "trip_name": trip.name, "status": trip.status}


@frappe.whitelist()
def complete_trip(trip_name: str, force: bool = False):
	"""Mark trip as completed consistent with stops visited status."""
	trip = frappe.get_doc("Delivery Trip", trip_name)
	if trip.docstatus != 1:
		frappe.throw(_("Hanya Delivery Trip yang berstatus submitted yang dapat diselesaikan."))

	unvisited = [s for s in trip.delivery_stops if not s.visited]
	force = frappe.utils.cint(force)
	if unvisited and not force:
		frappe.throw(_("Tidak dapat menyelesaikan trip. Masih terdapat {0} dari {1} titik antar yang belum dikunjungi.").format(len(unvisited), len(trip.delivery_stops)))

	if unvisited and force:
		for s in unvisited:
			s.visited = 1
		trip.flags.ignore_validate_update_after_submit = True
		trip.save(ignore_permissions=True)

	trip.db_set("status", "Completed")
	frappe.db.commit()
	return {"success": True, "status": "Completed"}


@frappe.whitelist()
def get_delivery_trips_list(status_filter=None, company_filter=None, search=None, page=1, page_size=20):
	"""List Delivery Trips with stops progress, monitoring status, and vehicle info."""
	page = int(page)
	page_size = int(page_size)
	offset = (page - 1) * page_size

	conditions = ["dt.docstatus IN (0, 1)"]
	params = {}

	if company_filter and company_filter != "All":
		conditions.append("dt.company = %(company)s")
		params["company"] = company_filter

	if status_filter and status_filter != "All":
		conditions.append("dt.status = %(status)s")
		params["status"] = status_filter

	if search:
		conditions.append("(dt.name LIKE %(search)s OR dt.driver_name LIKE %(search)s OR dt.vehicle LIKE %(search)s)")
		params["search"] = f"%{search}%"

	where_clause = " AND ".join(conditions)

	total_count = frappe.db.sql(f"SELECT count(dt.name) FROM `tabDelivery Trip` dt WHERE {where_clause}", params)[0][0] or 0

	trips = frappe.db.sql(f"""
		SELECT
			dt.name, dt.departure_time, dt.driver, dt.driver_name, dt.vehicle,
			dt.status, dt.total_distance, dt.uom, dt.modified, dt.company, dt.docstatus,
			dt.custom_actual_departure, dt.custom_departed_by
		FROM `tabDelivery Trip` dt
		WHERE {where_clause}
		ORDER BY dt.creation DESC
		LIMIT {page_size} OFFSET {offset}
	""", params, as_dict=True)

	for t in trips:
		stops = frappe.db.sql("""
			SELECT idx, customer, delivery_note, visited, customer_address, details, lat, lng
			FROM `tabDelivery Stop`
			WHERE parent = %s
			ORDER BY idx ASC
		""", (t["name"],), as_dict=True)

		total_stops = len(stops)
		completed_stops = sum(1 for s in stops if s["visited"])

		# Scan history for checkpoint
		dn_names = [s["delivery_note"] for s in stops if s.get("delivery_note")]
		scan_history = get_trip_scan_history(t["name"], dn_names)

		last_checkpoint = None
		unlocated_stops = 0
		for s in stops:
			s_lat = _clean_coord(s.get("lat"))
			s_lng = _clean_coord(s.get("lng"))
			if not is_valid_coord_pair(s_lat, s_lng):
				unlocated_stops += 1

			if s["visited"]:
				dn = s.get("delivery_note")
				scan = scan_history.get(dn) if dn else None
				if scan and scan.get("confirmed_at"):
					conf_at = scan["confirmed_at"]
					if not last_checkpoint or (last_checkpoint.get("confirmed_at") and conf_at > last_checkpoint["confirmed_at"]):
						last_checkpoint = {
							"customer": s["customer"],
							"delivery_note": dn,
							"confirmed_at": conf_at,
							"text": f"{s['customer']} ({format_datetime(conf_at, 'HH:mm')})"
						}
				elif not last_checkpoint:
					last_checkpoint = {
						"customer": s["customer"],
						"delivery_note": dn,
						"confirmed_at": None,
						"text": f"{s['customer']} (waktu belum tersedia)"
					}

		monitoring_status = compute_trip_monitoring_status(
			t["docstatus"],
			total_stops,
			completed_stops,
			t.get("custom_actual_departure"),
			t.get("status")
		)

		next_stop = next((s for s in stops if not s["visited"]), None)

		t["stops"] = stops
		t["total_stops"] = total_stops
		t["completed_stops"] = completed_stops
		t["monitoring_status"] = monitoring_status
		t["last_checkpoint"] = last_checkpoint
		t["unlocated_stops"] = unlocated_stops
		t["next_planned_stop"] = {
			"idx": next_stop.get("idx"),
			"customer": next_stop.get("customer"),
			"delivery_note": next_stop.get("delivery_note"),
		} if next_stop else None

	return {
		"items": trips,
		"total_count": total_count,
		"page": page,
		"page_size": page_size
	}


@frappe.whitelist()
def get_delivery_trip_detail(trip_name: str):
	"""Detailed view of a Delivery Trip including full stop records, scan history, coordinates and PODs."""
	trip = frappe.get_doc("Delivery Trip", trip_name)
	trip_data = trip.as_dict()

	# Origin location
	orig_lat = _clean_coord(trip.get("custom_origin_latitude"))
	orig_lng = _clean_coord(trip.get("custom_origin_longitude"))
	if not is_valid_coord_pair(orig_lat, orig_lng):
		if trip.company:
			comp_coords = frappe.db.get_value("Company", trip.company, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
			orig_lat = _clean_coord(comp_coords.get("custom_latitude"))
			orig_lng = _clean_coord(comp_coords.get("custom_longitude"))

	trip_data["origin_lat"] = orig_lat if is_valid_coord_pair(orig_lat, orig_lng) else None
	trip_data["origin_lng"] = orig_lng if is_valid_coord_pair(orig_lat, orig_lng) else None
	trip_data["has_origin_coordinates"] = is_valid_coord_pair(orig_lat, orig_lng)

	# Scan history
	dn_names = [stop.delivery_note for stop in trip.delivery_stops if stop.delivery_note]
	scan_history = get_trip_scan_history(trip.name, dn_names)

	stops_detailed = []
	visited_count = 0
	last_checkpoint = None

	for stop in trip.delivery_stops:
		stop_dict = stop.as_dict()

		# Check coordinates
		stop_lat = _clean_coord(stop.lat)
		stop_lng = _clean_coord(stop.lng)
		if not is_valid_coord_pair(stop_lat, stop_lng):
			if stop.customer:
				c_coords = frappe.db.get_value("Customer", stop.customer, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
				stop_lat = _clean_coord(c_coords.get("custom_latitude"))
				stop_lng = _clean_coord(c_coords.get("custom_longitude"))

		has_coords = is_valid_coord_pair(stop_lat, stop_lng)
		stop_dict["lat"] = stop_lat if has_coords else None
		stop_dict["lng"] = stop_lng if has_coords else None
		stop_dict["has_coordinates"] = has_coords

		# Visit & Confirmation status
		is_visited = bool(stop.visited)
		if is_visited:
			visited_count += 1
			dn = stop.delivery_note
			scan = scan_history.get(dn) if dn else None
			if scan and scan.get("confirmed_at"):
				conf_at = scan["confirmed_at"]
				stop_dict["confirmed_at"] = conf_at
				stop_dict["scanned_by"] = scan.get("scanned_by")
				stop_dict["scanned_by_name"] = scan.get("scanned_by_name")
				stop_dict["confirmation_status"] = "confirmed"
				stop_dict["confirmation_text"] = f"Terkonfirmasi: {format_datetime(conf_at, 'HH:mm')}"

				if not last_checkpoint or (last_checkpoint.get("confirmed_at") and conf_at > last_checkpoint["confirmed_at"]):
					last_checkpoint = {
						"customer": stop.customer,
						"delivery_note": dn,
						"confirmed_at": conf_at,
						"text": f"{stop.customer} ({format_datetime(conf_at, 'HH:mm')})"
					}
			else:
				stop_dict["confirmed_at"] = None
				stop_dict["scanned_by"] = None
				stop_dict["scanned_by_name"] = None
				stop_dict["confirmation_status"] = "visited_without_time"
				stop_dict["confirmation_text"] = "Dikunjungi (waktu belum tersedia)"

				if not last_checkpoint:
					last_checkpoint = {
						"customer": stop.customer,
						"delivery_note": dn,
						"confirmed_at": None,
						"text": f"{stop.customer} (waktu belum tersedia)"
					}
		else:
			stop_dict["confirmed_at"] = None
			stop_dict["scanned_by"] = None
			stop_dict["scanned_by_name"] = None
			stop_dict["confirmation_status"] = "pending"
			stop_dict["confirmation_text"] = "Belum dikunjungi"

		# Check POD info
		pod_info = None
		if stop.custom_proof_of_delivery:
			pod_info = frappe.db.get_value(
				"Proof of Delivery",
				stop.custom_proof_of_delivery,
				["name", "recipient_name", "recipient_relationship", "proof_photo", "signature", "latitude", "longitude", "submitted_at"],
				as_dict=True
			)
		elif stop.delivery_note:
			pod_name = frappe.db.get_value("Proof of Delivery", {"delivery_note": stop.delivery_note}, "name")
			if pod_name:
				pod_info = frappe.db.get_value(
					"Proof of Delivery",
					pod_name,
					["name", "recipient_name", "recipient_relationship", "proof_photo", "signature", "latitude", "longitude", "submitted_at"],
					as_dict=True
				)
		stop_dict["pod"] = pod_info

		# Check items
		if stop.delivery_note:
			items = frappe.db.sql("""
				SELECT item_code, item_name, qty, uom
				FROM `tabDelivery Note Item`
				WHERE parent = %s
			""", (stop.delivery_note,), as_dict=True)
			stop_dict["items"] = items

		stops_detailed.append(stop_dict)

	total_stops = len(stops_detailed)
	monitoring_status = compute_trip_monitoring_status(
		trip.docstatus,
		total_stops,
		visited_count,
		trip.get("custom_actual_departure"),
		trip.get("status")
	)

	next_stop = next((s for s in stops_detailed if not s.get("visited")), None)

	trip_data["delivery_stops"] = stops_detailed
	trip_data["total_stops"] = total_stops
	trip_data["completed_stops"] = visited_count
	trip_data["monitoring_status"] = monitoring_status
	trip_data["last_checkpoint"] = last_checkpoint
	trip_data["next_planned_stop"] = {
		"idx": next_stop.get("idx"),
		"customer": next_stop.get("customer"),
		"delivery_note": next_stop.get("delivery_note"),
		"address": next_stop.get("customer_address"),
	} if next_stop else None

	# Attach OSRM Road Route
	from delivery_app.services.osrm_routing import get_trip_osrm_route
	trip_data["route"] = get_trip_osrm_route(trip.name)

	return trip_data


@frappe.whitelist()
def get_trip_route(trip_name: str):
	"""Get OSRM road route geometry and distance for a Delivery Trip."""
	from delivery_app.services.osrm_routing import get_trip_osrm_route
	return get_trip_osrm_route(trip_name)


@frappe.whitelist()
def update_trip_stop_details(trip_name: str, stop_idx: int, details: str = None):
	"""Update Delivery Stop details (kendala pengantaran / catatan operasional)."""
	if not trip_name:
		frappe.throw(_("Delivery Trip harus ditentukan."))

	trip = frappe.get_doc("Delivery Trip", trip_name)
	found = False
	for stop in trip.delivery_stops:
		if stop.idx == int(stop_idx):
			stop.details = details or ""
			found = True
			break

	if not found:
		frappe.throw(_("Stop urutan {0} tidak ditemukan pada trip {1}.").format(stop_idx, trip_name))

	trip.flags.ignore_validate_update_after_submit = True
	trip.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"trip_name": trip_name,
		"stop_idx": stop_idx,
		"details": details or ""
	}



@frappe.whitelist()
def get_fleet_resources():
	"""Get Drivers, Vehicles, Companies, and supported couriers for dispatching."""
	drivers = frappe.get_all(
		"Driver",
		fields=["name", "full_name", "cell_number", "user", "transporter"],
		order_by="full_name asc"
	)

	vehicles = frappe.get_all(
		"Vehicle",
		fields=["name", "license_plate", "make", "model", "fuel_type"],
		order_by="license_plate asc"
	)

	companies_raw = frappe.get_all("Company", fields=["name", "company_name", "abbr", "custom_latitude", "custom_longitude"])
	companies = []
	for c in companies_raw:
		c_lat = _clean_coord(c.get("custom_latitude"))
		c_lng = _clean_coord(c.get("custom_longitude"))
		has_loc = is_valid_coord_pair(c_lat, c_lng)
		companies.append({
			"name": c.name,
			"company_name": c.company_name,
			"abbr": c.abbr,
			"has_dispatch_location": has_loc,
			"dispatch_lat": c_lat if has_loc else None,
			"dispatch_lng": c_lng if has_loc else None,
		})

	default_company = frappe.db.get_single_value("Global Defaults", "default_company")

	return {
		"drivers": drivers,
		"vehicles": vehicles,
		"companies": companies,
		"default_company": default_company,
		"couriers": COURIER_LIST
	}


@frappe.whitelist()
def get_customer_delivery_location(customer: str):
	"""Get customer coordinates from Customer master (custom_latitude, custom_longitude)."""
	if not customer:
		frappe.throw(_("Customer is required."))
	c_data = frappe.db.get_value("Customer", customer, ["custom_latitude", "custom_longitude", "customer_primary_address"], as_dict=True) or {}
	lat = _clean_coord(c_data.get("custom_latitude"))
	lng = _clean_coord(c_data.get("custom_longitude"))
	has_loc = is_valid_coord_pair(lat, lng)
	primary_addr = c_data.get("customer_primary_address")
	address_display = ""
	if primary_addr:
		addr_dict = frappe.db.get_value("Address", primary_addr, ["address_line1", "city", "pincode"], as_dict=True) or {}
		address_display = ", ".join([v for v in addr_dict.values() if v])

	return {
		"customer": customer,
		"latitude": lat if has_loc else None,
		"longitude": lng if has_loc else None,
		"has_location": has_loc,
		"address_display": address_display
	}


@frappe.whitelist()
def set_customer_delivery_location(customer: str, latitude: float, longitude: float):
	"""Set customer coordinates in Customer master (custom_latitude, custom_longitude)."""
	if not customer:
		frappe.throw(_("Customer is required."))
	lat = _clean_coord(latitude)
	lng = _clean_coord(longitude)
	if lat is None or lng is None:
		frappe.throw(_("Koordinat latitude dan longitude tidak valid."))

	frappe.db.set_value("Customer", customer, {
		"custom_latitude": lat,
		"custom_longitude": lng,
	}, update_modified=True)
	frappe.db.commit()

	return {
		"success": True,
		"customer": customer,
		"latitude": lat,
		"longitude": lng,
		"has_location": True
	}


@frappe.whitelist()
def get_company_dispatch_location(company: str):
	"""Get dispatch coordinates from Company master (custom_latitude, custom_longitude)."""
	if not company:
		frappe.throw(_("Company is required."))
	c_data = frappe.db.get_value("Company", company, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
	lat = _clean_coord(c_data.get("custom_latitude"))
	lng = _clean_coord(c_data.get("custom_longitude"))
	has_loc = is_valid_coord_pair(lat, lng)
	return {
		"company": company,
		"latitude": lat if has_loc else None,
		"longitude": lng if has_loc else None,
		"has_location": has_loc
	}


@frappe.whitelist()
def set_company_dispatch_location(company: str, latitude: float, longitude: float):
	"""Set dispatch coordinates in Company master (custom_latitude, custom_longitude)."""
	if not company:
		frappe.throw(_("Company is required."))
	lat = _clean_coord(latitude)
	lng = _clean_coord(longitude)
	if lat is None or lng is None:
		frappe.throw(_("Koordinat latitude dan longitude tidak valid."))

	frappe.db.set_value("Company", company, {
		"custom_latitude": lat,
		"custom_longitude": lng,
	}, update_modified=True)
	frappe.db.commit()

	return {
		"success": True,
		"company": company,
		"latitude": lat,
		"longitude": lng,
		"has_location": True
	}


@frappe.whitelist()
def get_pods_list(page=1, page_size=24, search=None):
	"""List Proof of Delivery records with full details and gallery thumbnails."""
	page = int(page)
	page_size = int(page_size)
	offset = (page - 1) * page_size

	conditions = ["1=1"]
	params = {}

	if search:
		conditions.append("(pod.name LIKE %(s)s OR pod.delivery_note LIKE %(s)s OR pod.recipient_name LIKE %(s)s OR pod.delivery_trip LIKE %(s)s)")
		params["s"] = f"%{search}%"

	where_clause = " AND ".join(conditions)

	total = frappe.db.sql(f"SELECT count(name) FROM `tabProof of Delivery` pod WHERE {where_clause}", params)[0][0] or 0

	pods = frappe.db.sql(f"""
		SELECT
			pod.name, pod.delivery_note, pod.delivery_trip, pod.recipient_name,
			pod.recipient_relationship, pod.recipient_phone, pod.proof_photo,
			pod.signature, pod.latitude, pod.longitude, pod.location_address,
			pod.submitted_at, pod.status, pod.notes, pod.delivered_by
		FROM `tabProof of Delivery` pod
		WHERE {where_clause}
		ORDER BY pod.submitted_at DESC
		LIMIT {page_size} OFFSET {offset}
	""", params, as_dict=True)

	return {
		"items": pods,
		"total_count": total,
		"page": page,
		"page_size": page_size
	}


@frappe.whitelist()
def get_gateway_settings_api():
	"""Fetch settings for SPA."""
	settings = frappe.get_single("Delivery Gateway Settings")
	return {
		"enabled": settings.enabled,
		"environment": settings.environment,
		"has_api_key": bool(settings.get_password("api_key", raise_exception=False)),
		"auto_tracking": settings.auto_tracking,
		"sync_interval_hours": settings.sync_interval_hours,
		"supported_couriers": settings.supported_couriers or "",
		"webhook_endpoint": settings.webhook_endpoint or "/api/method/delivery_app.services.biteship.handle_webhook",
		"has_webhook_secret": bool(settings.get_password("webhook_secret", raise_exception=False)),
		"osrm_enabled": bool(getattr(settings, "osrm_enabled", 1)),
		"osrm_base_url": getattr(settings, "osrm_base_url", "https://router.project-osrm.org") or "https://router.project-osrm.org",
	}


@frappe.whitelist()
def save_gateway_settings_api(
	enabled,
	environment,
	api_key=None,
	auto_tracking=1,
	sync_interval_hours=3,
	supported_couriers=None,
	webhook_secret=None,
	osrm_enabled=1,
	osrm_base_url=None
):
	"""Update settings from SPA."""
	roles = frappe.get_roles(frappe.session.user)
	if not ("System Manager" in roles or "Stock Manager" in roles or "Delivery Manager" in roles):
		frappe.throw(_("Permission denied to update Delivery Gateway Settings."))

	settings = frappe.get_single("Delivery Gateway Settings")
	settings.enabled = int(enabled)
	settings.environment = environment
	if api_key and api_key != "********":
		settings.api_key = api_key
	if webhook_secret and webhook_secret != "********":
		settings.webhook_secret = webhook_secret
	settings.auto_tracking = int(auto_tracking)
	settings.sync_interval_hours = int(sync_interval_hours)
	if supported_couriers:
		settings.supported_couriers = supported_couriers

	if hasattr(settings, "osrm_enabled"):
		settings.osrm_enabled = int(osrm_enabled)
	if hasattr(settings, "osrm_base_url") and osrm_base_url is not None:
		settings.osrm_base_url = osrm_base_url.strip()

	settings.save()
	frappe.db.commit()

	return {"success": True}


@frappe.whitelist()
def track_waybill_live(delivery_note: str = None, delivery_note_name: str = None):
	"""Live track a delivery note resi via Biteship."""
	from delivery_app.services.biteship import track_delivery_note
	return track_delivery_note(delivery_note_name=delivery_note_name or delivery_note)


@frappe.whitelist()
def check_rates_estimate(courier_code: str = None, weight_grams: int = 1000):
	"""Calculate realistic shipping rates for couriers."""
	# Simulated realistic rate estimates per courier based on weight
	weight_kg = max(1, round(int(weight_grams) / 1000))
	rates = []

	for c in COURIER_LIST:
		if courier_code and c["code"] != courier_code:
			continue

		base_reg = 11000 * weight_kg
		base_exp = 18000 * weight_kg
		base_cargo = max(35000, 4500 * weight_kg * 5)

		rates.append({
			"courier_name": c["name"],
			"courier_code": c["code"],
			"service_name": "Reguler",
			"service_code": "REG",
			"price": base_reg,
			"etd": "2-3 Hari",
		})
		rates.append({
			"courier_name": c["name"],
			"courier_code": c["code"],
			"service_name": "Next Day / Express",
			"service_code": "EXPRESS",
			"price": base_exp,
			"etd": "1 Hari",
		})
		if weight_kg >= 5:
			rates.append({
				"courier_name": c["name"],
				"courier_code": c["code"],
				"service_name": "Cargo / Trucking",
				"service_code": "CARGO",
				"price": base_cargo,
				"etd": "3-5 Hari",
			})

	return rates


@frappe.whitelist()
def get_sales_orders(company=None, date_from=None, date_to=None, search=None, status_filter="all", page=1, page_size=20):
	"""List submitted Sales Orders eligible for Delivery Note intake."""
	from delivery_app.services.so_intake import get_eligible_sales_orders
	return get_eligible_sales_orders(
		company=company,
		date_from=date_from,
		date_to=date_to,
		search=search,
		status_filter=status_filter,
		page=page,
		page_size=page_size,
	)


@frappe.whitelist()
def get_sales_order_detail(sales_order: str):
	"""Fetch details of a single Sales Order for intake verification and modal review."""
	from delivery_app.services.so_intake import get_sales_order_intake_detail
	return get_sales_order_intake_detail(sales_order)


@frappe.whitelist()
def create_delivery_note_from_so(sales_order: str, delivery_method: str = "Armada Sendiri", custom_warehouse: str = None):
	"""Atomically create and submit a Delivery Note from a full Sales Order."""
	from delivery_app.services.so_intake import create_delivery_note_from_so as _create_dn
	return _create_dn(
		sales_order=sales_order,
		delivery_method=delivery_method,
		custom_warehouse=custom_warehouse,
	)

