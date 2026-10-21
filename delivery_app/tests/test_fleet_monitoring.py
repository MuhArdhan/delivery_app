# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.exceptions import ValidationError

from delivery_app.overrides.delivery_trip import validate_delivery_trip
from delivery_app.services.fleet_monitoring import (
	_clean_coord,
	compute_trip_monitoring_status,
	format_point_geojson,
	get_trip_scan_history,
	parse_geolocation,
)


class TestFleetMonitoring(unittest.TestCase):
	def test_clean_coord(self):
		self.assertEqual(_clean_coord(0), 0.0)
		self.assertEqual(_clean_coord("0.0"), 0.0)
		self.assertEqual(_clean_coord(-7.6147), -7.6147)
		self.assertEqual(_clean_coord(110.6869), 110.6869)
		self.assertIsNone(_clean_coord(None))
		self.assertIsNone(_clean_coord(""))
		self.assertIsNone(_clean_coord("invalid"))
		self.assertIsNone(_clean_coord(200.0))  # Out of geographic range

	def test_parse_geolocation_formats(self):
		# 1. FeatureCollection (Standard Frappe Geolocation)
		geo_fc = json.dumps({
			"type": "FeatureCollection",
			"features": [{
				"type": "Feature",
				"properties": {},
				"geometry": {"type": "Point", "coordinates": [110.6869194, -7.6147137]}
			}]
		})
		lat, lng = parse_geolocation(geo_fc)
		self.assertAlmostEqual(lat, -7.6147137)
		self.assertAlmostEqual(lng, 110.6869194)

		# 2. Point geometry
		geo_point = {"type": "Point", "coordinates": [106.8271, -6.1754]}
		lat, lng = parse_geolocation(geo_point)
		self.assertAlmostEqual(lat, -6.1754)
		self.assertAlmostEqual(lng, 106.8271)

		# 3. Direct dictionary
		lat, lng = parse_geolocation({"lat": -6.2, "lng": 106.8})
		self.assertAlmostEqual(lat, -6.2)
		self.assertAlmostEqual(lng, 106.8)

		# 4. Zero coordinates preserved (equator/prime meridian)
		lat, lng = parse_geolocation({"lat": 0.0, "lng": 0.0})
		self.assertEqual(lat, 0.0)
		self.assertEqual(lng, 0.0)

		# 5. Invalid / empty inputs
		self.assertEqual(parse_geolocation(None), (None, None))
		self.assertEqual(parse_geolocation(""), (None, None))
		self.assertEqual(parse_geolocation("not-json"), (None, None))

	def test_format_point_geojson(self):
		res = format_point_geojson(-7.6147, 110.6869)
		self.assertIsNotNone(res)
		data = json.loads(res)
		self.assertEqual(data["type"], "FeatureCollection")
		coords = data["features"][0]["geometry"]["coordinates"]
		self.assertEqual(coords, [110.6869, -7.6147])

		# Zero coordinate valid
		res_zero = format_point_geojson(0.0, 0.0)
		self.assertIsNotNone(res_zero)
		self.assertEqual(json.loads(res_zero)["features"][0]["geometry"]["coordinates"], [0.0, 0.0])

		# Invalid
		self.assertIsNone(format_point_geojson(None, 110.0))

	def test_compute_trip_monitoring_status(self):
		# Cancelled
		self.assertEqual(compute_trip_monitoring_status(2, 3, 0), "Dibatalkan")
		# Draft
		self.assertEqual(compute_trip_monitoring_status(0, 3, 0), "Draft")
		# All visited
		self.assertEqual(compute_trip_monitoring_status(1, 3, 3), "Selesai Kunjungan")
		# Partial visited
		self.assertEqual(compute_trip_monitoring_status(1, 3, 1), "Dalam Perjalanan")
		# Actual departure set, 0 visited
		self.assertEqual(compute_trip_monitoring_status(1, 3, 0, actual_departure="2026-10-21 08:00:00"), "Dalam Perjalanan")
		# Scheduled, not yet departed
		self.assertEqual(compute_trip_monitoring_status(1, 3, 0, actual_departure=None, native_status="Scheduled"), "Terjadwal")

	def test_get_trip_scan_history_ignores_duplicate_rescans(self):
		records = [
			{
				"name": "SCAN-1",
				"recorded_at": "2026-10-21 09:00:00",
				"scanned_by": "driver1@test",
				"scanned_by_name": "Driver Satu",
				"reference_name": "DN-001",
				"source_name": "TRIP-001",
				"details": json.dumps([{"already_visited": False, "trip": "TRIP-001"}]),
			},
			{
				"name": "SCAN-2",
				"recorded_at": "2026-10-21 09:15:00",
				"scanned_by": "driver1@test",
				"scanned_by_name": "Driver Satu",
				"reference_name": "DN-001",
				"source_name": "TRIP-001",
				"details": json.dumps([{"already_visited": True, "trip": "TRIP-001"}]),  # Duplicate rescan
			},
		]
		with (
			patch.object(frappe.db, "table_exists", return_value=True),
			patch.object(frappe.db, "sql", return_value=records),
		):
			checkpoints = get_trip_scan_history("TRIP-001", ["DN-001"])
			self.assertIn("DN-001", checkpoints)
			# Must preserve the first genuine scan, not the rescan timestamp
			self.assertEqual(checkpoints["DN-001"]["confirmed_at"], "2026-10-21 09:00:00")
			self.assertEqual(checkpoints["DN-001"]["scanned_by_name"], "Driver Satu")

	def test_validate_delivery_trip_rejects_ekspedisi(self):
		stop = SimpleNamespace(delivery_note="DN-EKSP", customer="Cust 1", lat=None, lng=None)
		doc = SimpleNamespace(company="ROPI", delivery_stops=[stop], get=lambda k: None)

		def mock_get_value(doctype, name, field, **kwargs):
			if doctype == "Delivery Note" and name == "DN-EKSP":
				return SimpleNamespace(custom_delivery_method="Ekspedisi", company="ROPI", customer="Cust 1")
			return None

		with patch.object(frappe.db, "get_value", side_effect=mock_get_value):
			with self.assertRaises(ValidationError):
				validate_delivery_trip(doc)

	def test_validate_delivery_trip_enforces_company_consistency(self):
		stop1 = SimpleNamespace(delivery_note="DN-1", customer="Cust 1", lat=None, lng=None)
		stop2 = SimpleNamespace(delivery_note="DN-2", customer="Cust 2", lat=None, lng=None)
		doc = SimpleNamespace(company="ROPI", delivery_stops=[stop1, stop2], get=lambda k: None)

		def mock_get_value(doctype, name, field, **kwargs):
			if doctype == "Delivery Note":
				if name == "DN-1":
					return SimpleNamespace(custom_delivery_method="Armada Sendiri", company="ROPI", customer="Cust 1")
				if name == "DN-2":
					return SimpleNamespace(custom_delivery_method="Armada Sendiri", company="OTHER_COMP", customer="Cust 2")
			return None

		with patch.object(frappe.db, "get_value", side_effect=mock_get_value):
			with self.assertRaises(ValidationError):
				validate_delivery_trip(doc)

	def test_validate_delivery_trip_snapshots_coordinates(self):
		stop = SimpleNamespace(delivery_note="DN-1", customer="Cust 1", lat=0.0, lng=0.0)
		doc = SimpleNamespace(
			company="ROPI",
			delivery_stops=[stop],
			custom_origin_location=None,
			get=lambda k: getattr(doc, k, None)
		)

		comp_geo = format_point_geojson(-7.61, 110.68)
		cust_geo = format_point_geojson(-7.75, 110.36)

		def mock_get_value(doctype, name, field, **kwargs):
			if doctype == "Delivery Note" and name == "DN-1":
				return SimpleNamespace(custom_delivery_method="Armada Sendiri", company="ROPI", customer="Cust 1")
			if doctype == "Company" and name == "ROPI":
				return comp_geo
			if doctype == "Customer" and name == "Cust 1":
				return cust_geo
			return None

		with patch.object(frappe.db, "get_value", side_effect=mock_get_value):
			validate_delivery_trip(doc)
			# Origin snapshot
			self.assertEqual(doc.custom_origin_location, comp_geo)
			# Stop coordinate snapshot
			self.assertAlmostEqual(stop.lat, -7.75)
			self.assertAlmostEqual(stop.lng, 110.36)
