# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import json
from typing import Any, Dict, List, Optional, Tuple
import frappe
from frappe import _
from frappe.utils import format_datetime, getdate, now_datetime


def _clean_coord(val: Any) -> Optional[float]:
	"""Convert coordinate value to float, preserving 0.0, rejecting invalid values."""
	if val is None or val == "":
		return None
	try:
		f = float(val)
		# Basic geographic sanity check
		if -180.0 <= f <= 180.0:
			return f
	except (ValueError, TypeError):
		pass
	return None


def is_valid_coord_pair(lat: Any, lng: Any) -> bool:
	"""
	Check if a (latitude, longitude) pair is valid and non-placeholder.
	Rejects None, out-of-range, and (0.0, 0.0) placeholder defaults.
	"""
	c_lat = _clean_coord(lat)
	c_lng = _clean_coord(lng)
	if c_lat is None or c_lng is None:
		return False
	if abs(c_lat) < 1e-6 and abs(c_lng) < 1e-6:
		return False
	return True


def parse_geolocation(value: Any) -> Tuple[Optional[float], Optional[float]]:
	"""
	Extract (latitude, longitude) as floats from Frappe Geolocation field.
	Returns (lat, lng) where each is float or None.
	GeoJSON standard: Point coordinates are [longitude, latitude].
	"""
	if not value:
		return None, None

	if isinstance(value, str):
		value = value.strip()
		if not value:
			return None, None
		try:
			value = json.loads(value)
		except Exception:
			return None, None

	if not isinstance(value, dict):
		return None, None

	# Case 1: FeatureCollection (Standard Frappe Geolocation control format)
	if value.get("type") == "FeatureCollection":
		features = value.get("features") or []
		if features and isinstance(features, list):
			first = features[0] if isinstance(features[0], dict) else {}
			geom = first.get("geometry") or {}
			coords = geom.get("coordinates")
			if isinstance(coords, (list, tuple)) and len(coords) >= 2:
				lng = _clean_coord(coords[0])
				lat = _clean_coord(coords[1])
				return lat, lng

	# Case 2: Feature
	if value.get("type") == "Feature":
		geom = value.get("geometry") or {}
		coords = geom.get("coordinates")
		if isinstance(coords, (list, tuple)) and len(coords) >= 2:
			return _clean_coord(coords[1]), _clean_coord(coords[0])

	# Case 3: Point geometry
	if value.get("type") == "Point":
		coords = value.get("coordinates")
		if isinstance(coords, (list, tuple)) and len(coords) >= 2:
			return _clean_coord(coords[1]), _clean_coord(coords[0])

	# Case 4: lat / lng dict
	if "lat" in value and "lng" in value:
		return _clean_coord(value.get("lat")), _clean_coord(value.get("lng"))
	if "latitude" in value and "longitude" in value:
		return _clean_coord(value.get("latitude")), _clean_coord(value.get("longitude"))

	return None, None


def format_point_geojson(lat: Any, lng: Any) -> Optional[str]:
	"""Format latitude and longitude as GeoJSON FeatureCollection Point string."""
	clean_lat = _clean_coord(lat)
	clean_lng = _clean_coord(lng)
	if clean_lat is None or clean_lng is None:
		return None

	return json.dumps({
		"type": "FeatureCollection",
		"features": [
			{
				"type": "Feature",
				"properties": {},
				"geometry": {
					"type": "Point",
					"coordinates": [round(clean_lng, 7), round(clean_lat, 7)]
				}
			}
		]
	}, ensure_ascii=False)


def get_trip_scan_history(trip_name: str, delivery_notes: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
	"""
	Read valid visit confirmation scan history from Scanner Scan History.
	Returns a dict keyed by delivery_note:
	    {
	        "confirmed_at": datetime,
	        "scanned_by": str,
	        "scanned_by_name": str,
	        "source_trip": str
	    }
	Filters:
	- operation = 'Delivery Note'
	- reference_doctype = 'Delivery Note'
	- already_visited is False (ignores duplicate rescans to prevent moving checkpoint time)
	- Takes the latest valid confirmation if re-scanned after reset
	"""
	if not frappe.db.table_exists("Scanner Scan History"):
		return {}

	conditions = [
		"ssh.reference_doctype = 'Delivery Note'",
		"ssh.operation = 'Delivery Note'"
	]
	params = {}

	if trip_name:
		conditions.append("(ssh.source_name = %(trip_name)s OR ssh.details LIKE %(trip_pattern)s)")
		params["trip_name"] = trip_name
		params["trip_pattern"] = f"%{trip_name}%"

	if delivery_notes:
		conditions.append("ssh.reference_name IN %(delivery_notes)s")
		params["delivery_notes"] = tuple(delivery_notes)

	where_clause = " AND ".join(conditions)

	records = frappe.db.sql(f"""
		SELECT
			ssh.name, ssh.recorded_at, ssh.scanned_by, ssh.reference_name,
			ssh.source_name, ssh.details, u.full_name as scanned_by_name
		FROM `tabScanner Scan History` ssh
		LEFT JOIN `tabUser` u ON u.name = ssh.scanned_by
		WHERE {where_clause}
		ORDER BY ssh.recorded_at ASC
	""", params, as_dict=True)

	checkpoints = {}
	for row in records:
		dn_name = row.get("reference_name")
		if not dn_name:
			continue

		is_rescan = False
		details_raw = row.get("details")
		if details_raw:
			try:
				details = json.loads(details_raw) if isinstance(details_raw, str) else details_raw
				if isinstance(details, list) and len(details) > 0:
					first = details[0]
					if isinstance(first, dict):
						is_rescan = bool(first.get("already_visited"))
			except Exception:
				pass

		# If already_visited was true at the time of scanning, it was a duplicate rescan.
		# Per plan 5.2, ignore rescans so the checkpoint timestamp remains the genuine arrival time.
		if is_rescan:
			continue

		# Valid genuine visit confirmation
		checkpoints[dn_name] = {
			"confirmed_at": row.get("recorded_at"),
			"scanned_by": row.get("scanned_by"),
			"scanned_by_name": row.get("scanned_by_name") or row.get("scanned_by") or "",
			"source_trip": row.get("source_name") or trip_name,
		}

	return checkpoints


def compute_trip_monitoring_status(
	docstatus: int,
	total_stops: int,
	visited_stops: int,
	actual_departure: Any = None,
	native_status: Optional[str] = None
) -> str:
	"""
	Compute unified monitoring status:
	1. Docstatus 2 -> 'Dibatalkan'
	2. Docstatus 0 -> 'Draft'
	3. Docstatus 1:
	   - If total_stops > 0 and visited_stops == total_stops -> 'Selesai Kunjungan'
	   - If actual_departure is set or visited_stops > 0 or native_status == 'In Transit' -> 'Dalam Perjalanan'
	   - Otherwise -> 'Terjadwal'
	"""
	if docstatus == 2:
		return "Dibatalkan"
	if docstatus == 0:
		return "Draft"

	if total_stops > 0 and visited_stops >= total_stops:
		return "Selesai Kunjungan"

	if actual_departure or visited_stops > 0 or (native_status and native_status == "In Transit"):
		return "Dalam Perjalanan"

	return "Terjadwal"
