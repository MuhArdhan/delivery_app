# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import hashlib
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple
import frappe
from frappe import _
from delivery_app.services.fleet_monitoring import _clean_coord, is_valid_coord_pair

DEFAULT_OSRM_URL = "https://router.project-osrm.org"
ROUTE_CACHE_EXPIRY = 86400  # 24 hours in seconds


def get_osrm_settings() -> Tuple[bool, str]:
	"""Get OSRM enable flag and base URL from Delivery Gateway Settings or conf."""
	enabled = True
	base_url = DEFAULT_OSRM_URL

	try:
		if frappe.db.table_exists("Delivery Gateway Settings"):
			settings = frappe.get_single("Delivery Gateway Settings")
			if hasattr(settings, "osrm_enabled") and settings.osrm_enabled is not None:
				enabled = bool(settings.osrm_enabled)
			if hasattr(settings, "osrm_base_url") and settings.osrm_base_url:
				base_url = settings.osrm_base_url.strip().rstrip("/")
	except Exception:
		pass

	# Site config override takes highest priority if defined
	conf_url = frappe.conf.get("osrm_base_url")
	if conf_url:
		base_url = conf_url.strip().rstrip("/")

	return enabled, base_url


def calculate_osrm_route(points: List[Tuple[float, float]], profile: str = "driving") -> Dict[str, Any]:
	"""
	Calculate road route geometry using OSRM Route API.
	Points input: List of (latitude, longitude) tuples in travel sequence.
	Returns:
	    {
	        "success": bool,
	        "route_points": List[[lat, lng]],  # Formatted for Leaflet
	        "distance_km": float,
	        "duration_min": float,
	        "message": str
	    }
	"""
	valid_points = []
	for p in points:
		if p and len(p) >= 2:
			lat = _clean_coord(p[0])
			lng = _clean_coord(p[1])
			if is_valid_coord_pair(lat, lng):
				valid_points.append((lat, lng))

	if len(valid_points) < 2:
		return {
			"success": False,
			"route_points": [],
			"distance_km": 0.0,
			"duration_min": 0.0,
			"message": _("Rute membutuhkan minimal 2 titik koordinat valid.")
		}

	enabled, base_url = get_osrm_settings()
	if not enabled:
		return {
			"success": False,
			"route_points": [],
			"distance_km": 0.0,
			"duration_min": 0.0,
			"message": _("Layanan routing OSRM dinonaktifkan dalam Pengaturan.")
		}

	# OSRM expects coordinates in URL as {longitude},{latitude};...
	coord_str = ";".join([f"{round(lng, 7)},{round(lat, 7)}" for lat, lng in valid_points])
	cache_key = f"osrm_route:{hashlib.md5(f'{base_url}:{profile}:{coord_str}'.encode()).hexdigest()}"

	# Check Frappe Cache
	try:
		cached_data = frappe.cache().get_value(cache_key)
		if cached_data:
			if isinstance(cached_data, str):
				cached_data = json.loads(cached_data)
			return cached_data
	except Exception:
		pass

	url = f"{base_url}/route/v1/{profile}/{coord_str}?overview=full&geometries=geojson"

	try:
		req = urllib.request.Request(
			url,
			headers={
				"User-Agent": "DeliveryApp/1.0 (Frappe Logistics)",
				"Accept": "application/json"
			}
		)
		with urllib.request.urlopen(req, timeout=6) as response:
			raw_body = response.read().decode("utf-8")
			data = json.loads(raw_body)

		if data.get("code") == "Ok" and data.get("routes"):
			route = data["routes"][0]
			geometry = route.get("geometry") or {}
			raw_coords = geometry.get("coordinates") or []

			# OSRM GeoJSON coords are [longitude, latitude] -> convert to Leaflet [latitude, longitude]
			leaflet_points = [[c[1], c[0]] for c in raw_coords if len(c) >= 2]
			distance_meters = float(route.get("distance") or 0.0)
			duration_seconds = float(route.get("duration") or 0.0)

			result = {
				"success": True,
				"route_points": leaflet_points,
				"distance_km": round(distance_meters / 1000.0, 2),
				"duration_min": round(duration_seconds / 60.0, 1),
				"message": _("Rute rencana jalan berhasil dimuat.")
			}

			try:
				frappe.cache().set_value(cache_key, json.dumps(result), expires_in_sec=ROUTE_CACHE_EXPIRY)
			except Exception:
				pass

			return result

		err_msg = data.get("message") or _("Rute jalan belum tersedia.")
		return {
			"success": False,
			"route_points": [],
			"distance_km": 0.0,
			"duration_min": 0.0,
			"message": err_msg
		}

	except Exception as err:
		# Graceful fallback: connection timeout, DNS lookup error, network unreachable
		return {
			"success": False,
			"route_points": [],
			"distance_km": 0.0,
			"duration_min": 0.0,
			"message": _("Rute jalan belum tersedia.")
		}


def get_trip_osrm_route(trip_name: str) -> Dict[str, Any]:
	"""
	Generate road polyline for a Delivery Trip from origin through all stops.
	"""
	if not trip_name:
		return {
			"success": False,
			"route_points": [],
			"distance_km": 0.0,
			"duration_min": 0.0,
			"message": _("Delivery Trip harus ditentukan.")
		}

	trip = frappe.get_doc("Delivery Trip", trip_name)

	# 1. Origin coordinates
	orig_lat = _clean_coord(trip.get("custom_origin_latitude"))
	orig_lng = _clean_coord(trip.get("custom_origin_longitude"))
	if not is_valid_coord_pair(orig_lat, orig_lng):
		if trip.company:
			comp_coords = frappe.db.get_value("Company", trip.company, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
			orig_lat = _clean_coord(comp_coords.get("custom_latitude"))
			orig_lng = _clean_coord(comp_coords.get("custom_longitude"))

	points = []
	if is_valid_coord_pair(orig_lat, orig_lng):
		points.append((orig_lat, orig_lng))

	# 2. Stops in plan sequence
	for stop in trip.delivery_stops:
		s_lat = _clean_coord(stop.lat)
		s_lng = _clean_coord(stop.lng)
		if not is_valid_coord_pair(s_lat, s_lng):
			if stop.customer:
				cust_coords = frappe.db.get_value("Customer", stop.customer, ["custom_latitude", "custom_longitude"], as_dict=True) or {}
				s_lat = _clean_coord(cust_coords.get("custom_latitude"))
				s_lng = _clean_coord(cust_coords.get("custom_longitude"))

		if is_valid_coord_pair(s_lat, s_lng):
			points.append((s_lat, s_lng))

	if len(points) < 2:
		return {
			"success": False,
			"route_points": [],
			"distance_km": 0.0,
			"duration_min": 0.0,
			"has_origin": bool(is_valid_coord_pair(orig_lat, orig_lng)),
			"stops_located": len(points) - (1 if is_valid_coord_pair(orig_lat, orig_lng) else 0),
			"total_stops": len(trip.delivery_stops),
			"message": _("Rute membutuhkan titik asal dan minimal satu titik tujuan.")
		}

	res = calculate_osrm_route(points)
	res["trip_name"] = trip_name
	res["total_stops"] = len(trip.delivery_stops)
	res["points_count"] = len(points)
	return res
