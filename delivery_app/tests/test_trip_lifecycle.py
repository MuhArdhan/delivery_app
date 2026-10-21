# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.exceptions import ValidationError
from delivery_app.api import (
	complete_trip,
	mark_trip_departed,
	start_trip,
	update_trip_stop_details,
)


class TestTripLifecycle(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		if not frappe.db:
			frappe.init(site="development.localhost")
			frappe.connect()

	def test_start_trip_records_departure_timestamp(self):
		mock_trip = SimpleNamespace(
			name="TRIP-TEST-001",
			docstatus=1,
			status="Scheduled",
			custom_actual_departure=None,
			custom_departed_by=None,
			get=lambda k: getattr(mock_trip, k, None)
		)

		with patch.object(frappe, "get_doc", return_value=mock_trip), \
		     patch.object(frappe.db, "set_value") as mock_set_value, \
		     patch.object(frappe.db, "commit"):
			res = start_trip("TRIP-TEST-001")
			self.assertTrue(res["success"])
			self.assertEqual(res["status"], "In Transit")
			self.assertIsNotNone(res["actual_departure"])
			mock_set_value.assert_called_once()
			args = mock_set_value.call_args[0]
			self.assertEqual(args[0], "Delivery Trip")
			self.assertEqual(args[1], "TRIP-TEST-001")
			self.assertEqual(args[2]["status"], "In Transit")

	def test_start_trip_cancelled_or_completed_throws(self):
		mock_trip_cancelled = SimpleNamespace(
			name="TRIP-CANCELLED",
			docstatus=2,
			status="Cancelled",
			get=lambda k: getattr(mock_trip_cancelled, k, None)
		)
		with patch.object(frappe, "get_doc", return_value=mock_trip_cancelled):
			with self.assertRaises(frappe.ValidationError):
				start_trip("TRIP-CANCELLED")

		mock_trip_completed = SimpleNamespace(
			name="TRIP-COMPLETED",
			docstatus=1,
			status="Completed",
			get=lambda k: getattr(mock_trip_completed, k, None)
		)
		with patch.object(frappe, "get_doc", return_value=mock_trip_completed):
			with self.assertRaises(frappe.ValidationError):
				start_trip("TRIP-COMPLETED")

	def test_complete_trip_with_unvisited_stops_throws(self):
		stop1 = SimpleNamespace(idx=1, visited=1)
		stop2 = SimpleNamespace(idx=2, visited=0)
		mock_trip = SimpleNamespace(
			name="TRIP-TEST-002",
			docstatus=1,
			status="In Transit",
			delivery_stops=[stop1, stop2],
			db_set=Mock(),
			flags=SimpleNamespace(ignore_validate_update_after_submit=False),
			save=Mock()
		)

		with patch.object(frappe, "get_doc", return_value=mock_trip):
			# Should throw without force
			with self.assertRaises(frappe.ValidationError):
				complete_trip("TRIP-TEST-002", force=0)

			# Should succeed with force=1
			with patch.object(frappe.db, "commit"):
				res = complete_trip("TRIP-TEST-002", force=1)
				self.assertTrue(res["success"])
				self.assertEqual(res["status"], "Completed")
				self.assertEqual(stop2.visited, 1)

	def test_complete_trip_when_all_stops_visited(self):
		stop1 = SimpleNamespace(idx=1, visited=1)
		stop2 = SimpleNamespace(idx=2, visited=1)
		mock_trip = SimpleNamespace(
			name="TRIP-TEST-003",
			docstatus=1,
			status="In Transit",
			delivery_stops=[stop1, stop2],
			db_set=Mock()
		)

		with patch.object(frappe, "get_doc", return_value=mock_trip), \
		     patch.object(frappe.db, "commit"):
			res = complete_trip("TRIP-TEST-003")
			self.assertTrue(res["success"])
			self.assertEqual(res["status"], "Completed")
			mock_trip.db_set.assert_called_once_with("status", "Completed")

	def test_update_trip_stop_details(self):
		stop1 = SimpleNamespace(idx=1, details="")
		stop2 = SimpleNamespace(idx=2, details="Jalan ditutup proyek")
		mock_trip = SimpleNamespace(
			name="TRIP-TEST-004",
			delivery_stops=[stop1, stop2],
			flags=SimpleNamespace(ignore_validate_update_after_submit=False),
			save=Mock()
		)

		with patch.object(frappe, "get_doc", return_value=mock_trip), \
		     patch.object(frappe.db, "commit"):
			res = update_trip_stop_details("TRIP-TEST-004", stop_idx=1, details="Penerima minta titip pos satpam")
			self.assertTrue(res["success"])
			self.assertEqual(stop1.details, "Penerima minta titip pos satpam")
			mock_trip.save.assert_called_once()
