# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from delivery_app.services.osrm_routing import (
	calculate_osrm_route,
	get_osrm_settings,
	get_trip_osrm_route,
)


class TestOsrmRouting(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		if not frappe.db:
			frappe.init(site="development.localhost")
			frappe.connect()

	def test_fewer_than_two_points(self):
		res = calculate_osrm_route([(-7.61, 110.68)])
		self.assertFalse(res["success"])
		self.assertEqual(res["route_points"], [])
		self.assertIn("minimal 2", res["message"])

	def test_disabled_osrm(self):
		with patch("delivery_app.services.osrm_routing.get_osrm_settings", return_value=(False, "http://localhost")):
			res = calculate_osrm_route([(-7.61, 110.68), (-7.75, 110.36)])
			self.assertFalse(res["success"])
			self.assertIn("dinonaktifkan", res["message"])

	def test_network_failure_fallback(self):
		with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
			res = calculate_osrm_route([(-7.61, 110.68), (-7.75, 110.36)])
			self.assertFalse(res["success"])
			self.assertEqual(res["route_points"], [])
			self.assertIn("belum tersedia", res["message"])

	def test_successful_osrm_route_parsing(self):
		mock_osrm_response = {
			"code": "Ok",
			"routes": [{
				"geometry": {
					"coordinates": [
						[110.68, -7.61],
						[110.50, -7.68],
						[110.36, -7.75],
					],
					"type": "LineString"
				},
				"distance": 32500.0,
				"duration": 2400.0
			}]
		}

		mock_res = Mock()
		mock_res.read.return_value = json.dumps(mock_osrm_response).encode("utf-8")
		mock_res.__enter__ = Mock(return_value=mock_res)
		mock_res.__exit__ = Mock(return_value=None)

		with patch("urllib.request.urlopen", return_value=mock_res), \
		     patch.object(frappe.cache(), "get_value", return_value=None), \
		     patch.object(frappe.cache(), "set_value"):
			res = calculate_osrm_route([(-7.61, 110.68), (-7.75, 110.36)])

			self.assertTrue(res["success"])
			self.assertEqual(len(res["route_points"]), 3)
			# Coordinates are converted to Leaflet [latitude, longitude]
			self.assertEqual(res["route_points"][0], [-7.61, 110.68])
			self.assertEqual(res["route_points"][2], [-7.75, 110.36])
			self.assertEqual(res["distance_km"], 32.5)
			self.assertEqual(res["duration_min"], 40.0)

	def test_get_trip_osrm_route_builds_points(self):
		mock_trip = SimpleNamespace(
			name="TRIP-TEST-001",
			company="ROPI",
			custom_origin_latitude=-7.61,
			custom_origin_longitude=110.68,
			delivery_stops=[
				SimpleNamespace(idx=1, customer="Cust 1", lat=-7.70, lng=110.45),
				SimpleNamespace(idx=2, customer="Cust 2", lat=-7.75, lng=110.36),
			],
			get=lambda k: getattr(mock_trip, k, None)
		)

		mock_calc_result = {
			"success": True,
			"route_points": [[-7.61, 110.68], [-7.70, 110.45], [-7.75, 110.36]],
			"distance_km": 35.0,
			"duration_min": 45.0,
			"message": "OK"
		}

		with patch.object(frappe, "get_doc", return_value=mock_trip), \
		     patch("delivery_app.services.osrm_routing.calculate_osrm_route", return_value=mock_calc_result):
			res = get_trip_osrm_route("TRIP-TEST-001")
			self.assertTrue(res["success"])
			self.assertEqual(res["trip_name"], "TRIP-TEST-001")
			self.assertEqual(res["total_stops"], 2)
			self.assertEqual(res["points_count"], 3)
