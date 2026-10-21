# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import base64
import json
import frappe
from frappe import _
from frappe.utils import now_datetime, getdate, format_datetime
from frappe.utils.file_manager import save_file


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
	"""Change Delivery Trip status to In Transit."""
	trip = frappe.get_doc("Delivery Trip", trip_name)
	if trip.status == "Completed":
		frappe.throw(_("Delivery Trip is already completed."))

	frappe.db.set_value("Delivery Trip", trip_name, "status", "In Transit", update_modified=True)
	frappe.db.commit()
	return {"status": "In Transit"}


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
	"""KPIs, Live Map Points, and Recent Activity for Command Center."""
	today = getdate()

	# 1. Total pending delivery notes
	pending_notes = frappe.db.sql("""
		SELECT count(name) FROM `tabDelivery Note`
		WHERE docstatus = 1
		AND status NOT IN ('Cancelled', 'Closed')
		AND (
			(custom_delivery_method = 'Armada Sendiri' AND (custom_pod_status IS NULL OR custom_pod_status = 'Pending'))
			OR
			(custom_delivery_method = 'Ekspedisi' AND (custom_tracking_status IS NULL OR custom_tracking_status IN ('', 'Pending')))
			OR
			(custom_delivery_method IS NULL)
		)
	""")[0][0] or 0

	# 2. Active Trips
	active_trips_count = frappe.db.sql("""
		SELECT count(name) FROM `tabDelivery Trip`
		WHERE docstatus IN (0, 1)
		AND status IN ('Draft', 'Scheduled', 'In Transit')
	""")[0][0] or 0

	# 3. 3PL Couriers in transit
	in_transit_couriers = frappe.db.sql("""
		SELECT count(name) FROM `tabDelivery Note`
		WHERE docstatus = 1
		AND custom_delivery_method = 'Ekspedisi'
		AND custom_tracking_status = 'In Transit'
	""")[0][0] or 0

	# 4. Delivered today
	delivered_today = frappe.db.sql("""
		SELECT count(name) FROM `tabProof of Delivery`
		WHERE DATE(submitted_at) = %s
	""", (today,))[0][0] or 0

	# If no POD today, check Delivery Notes marked delivered today
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

	# Fetch Recent 25 Delivery Notes with location info for Live Operations Map
	map_notes = frappe.db.sql("""
		SELECT
			dn.name, dn.customer, dn.customer_name, dn.posting_date, dn.grand_total,
			dn.custom_delivery_method, dn.custom_courier_code, dn.custom_waybill_no,
			dn.custom_tracking_status, dn.custom_pod_status, dn.shipping_address,
			dn.shipping_address_name
		FROM `tabDelivery Note` dn
		WHERE dn.docstatus = 1
		ORDER BY dn.creation DESC
		LIMIT 40
	""", as_dict=True)

	map_markers = []
	# Coordinate cache to spread pins around Jabodetabek/Indonesia realistically if geocode is empty
	base_lat, base_lng = -6.2000, 106.8166
	idx_offset = 0

	for note in map_notes:
		# Check Address
		lat, lng = None, None
		addr_name = note.get("shipping_address_name")
		city_name = ""
		if addr_name:
			addr = frappe.db.get_value("Address", addr_name, ["address_line1", "city", "pincode"], as_dict=True)
			if addr:
				city_name = addr.city or ""

		# Fallback deterministic coordinates for visual demonstration on Leaflet
		h = hash(note["name"]) % 1000
		lat = base_lat + ((h % 50) - 25) * 0.008
		lng = base_lng + (((h // 50) % 50) - 25) * 0.009
		idx_offset += 1

		status = "Pending"
		if note.get("custom_delivery_method") == "Ekspedisi":
			status = note.get("custom_tracking_status") or "Pending"
		else:
			status = note.get("custom_pod_status") or "Pending"

		map_markers.append({
			"id": note["name"],
			"customer": note.get("customer_name") or note.get("customer"),
			"address": (note.get("shipping_address") or "").replace("<br>", ", ").strip(),
			"method": note.get("custom_delivery_method") or "Armada Sendiri",
			"courier": note.get("custom_courier_code") or "",
			"waybill": note.get("custom_waybill_no") or "",
			"status": status,
			"lat": lat,
			"lng": lng,
			"grand_total": note.get("grand_total") or 0,
		})

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
			"in_transit_couriers": in_transit_couriers,
			"delivered_today": delivered_today,
			"total_vehicles": total_vehicles,
			"total_drivers": total_drivers,
		},
		"map_markers": map_markers,
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

	# Validate no Ekspedisi notes are included
	for stop_data in stops:
		dn_name = stop_data.get("delivery_note")
		if dn_name:
			method = frappe.db.get_value("Delivery Note", dn_name, "custom_delivery_method")
			if method == "Ekspedisi":
				frappe.throw(_("Delivery Note {0} diatur untuk Ekspedisi (3PL). Tidak dapat dimasukkan ke Armada Sendiri.").format(dn_name))

	if not company:
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		if not company:
			first_dn = stops[0].get("delivery_note")
			if first_dn:
				company = frappe.db.get_value("Delivery Note", first_dn, "company")

	trip = frappe.new_doc("Delivery Trip")
	trip.company = company
	trip.driver = driver
	trip.vehicle = vehicle
	trip.departure_time = departure_time or now_datetime()
	trip.status = "Draft"

	# Add stops
	for idx, s in enumerate(stops, 1):
		dn_name = s.get("delivery_note")
		dn_doc = frappe.get_doc("Delivery Note", dn_name) if dn_name else None

		stop_row = trip.append("delivery_stops", {})
		stop_row.customer = s.get("customer") or (dn_doc.customer if dn_doc else "")
		stop_row.delivery_note = dn_name
		stop_row.address = s.get("address") or (dn_doc.shipping_address_name if dn_doc else "")
		stop_row.customer_address = s.get("customer_address") or (dn_doc.shipping_address if dn_doc else "")
		stop_row.grand_total = dn_doc.grand_total if dn_doc else 0
		stop_row.contact = dn_doc.contact_person if dn_doc else None
		stop_row.lat = float(s.get("lat")) if s.get("lat") else None
		stop_row.lng = float(s.get("lng")) if s.get("lng") else None
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
def complete_trip(trip_name: str):
	"""Mark trip as completed."""
	frappe.db.set_value("Delivery Trip", trip_name, "status", "Completed", update_modified=True)
	frappe.db.commit()
	return {"success": True, "status": "Completed"}


@frappe.whitelist()
def get_delivery_trips_list(status_filter=None, search=None, page=1, page_size=20):
	"""List Delivery Trips with stops progress and vehicle info."""
	page = int(page)
	page_size = int(page_size)
	offset = (page - 1) * page_size

	conditions = ["dt.docstatus IN (0, 1)"]
	params = {}

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
			dt.status, dt.total_distance, dt.uom, dt.modified, dt.company, dt.docstatus
		FROM `tabDelivery Trip` dt
		WHERE {where_clause}
		ORDER BY dt.creation DESC
		LIMIT {page_size} OFFSET {offset}
	""", params, as_dict=True)

	for t in trips:
		stops = frappe.db.sql("""
			SELECT idx, customer, delivery_note, visited, customer_address, details
			FROM `tabDelivery Stop`
			WHERE parent = %s
			ORDER BY idx ASC
		""", (t["name"],), as_dict=True)
		t["stops"] = stops
		t["total_stops"] = len(stops)
		t["completed_stops"] = sum(1 for s in stops if s["visited"])

	return {
		"items": trips,
		"total_count": total_count,
		"page": page,
		"page_size": page_size
	}


@frappe.whitelist()
def get_delivery_trip_detail(trip_name: str):
	"""Detailed view of a Delivery Trip including full stop records and PODs."""
	trip = frappe.get_doc("Delivery Trip", trip_name)
	trip_data = trip.as_dict()

	stops_detailed = []
	for stop in trip.delivery_stops:
		stop_dict = stop.as_dict()
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

		# Check items for stop delivery note
		if stop.delivery_note:
			items = frappe.db.sql("""
				SELECT item_code, item_name, qty, uom
				FROM `tabDelivery Note Item`
				WHERE parent = %s
			""", (stop.delivery_note,), as_dict=True)
			stop_dict["items"] = items

		stops_detailed.append(stop_dict)

	trip_data["delivery_stops"] = stops_detailed
	return trip_data


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

	companies = frappe.get_all("Company", fields=["name", "company_name", "abbr"])
	default_company = frappe.db.get_single_value("Global Defaults", "default_company")

	return {
		"drivers": drivers,
		"vehicles": vehicles,
		"companies": companies,
		"default_company": default_company,
		"couriers": COURIER_LIST
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
	}


@frappe.whitelist()
def save_gateway_settings_api(enabled, environment, api_key=None, auto_tracking=1, sync_interval_hours=3, supported_couriers=None, webhook_secret=None):
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
