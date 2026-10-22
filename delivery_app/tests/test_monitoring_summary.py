import unittest
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime

from delivery_app.services.monitoring_summary import fleet_kpis


class TestMonitoringSummary(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		if not frappe.db:
			frappe.init(site="development.localhost")
			frappe.connect()

	def test_counts_use_monitoring_state(self):
		rows = [frappe._dict(name="A", monitoring_state="Scheduled"),
			frappe._dict(name="B", monitoring_state="In Transit")]
		with patch.object(frappe.db, "sql", return_value=rows) as query:
			result = fleet_kpis("Company A")
		self.assertEqual(result["scheduled_trips"], 1)
		self.assertEqual(result["in_transit_trips"], 1)
		self.assertEqual(query.call_args.args[1], {"company": "Company A"})

	def test_completion_requires_all_confirmation_times(self):
		rows = [frappe._dict(name="A", monitoring_state="Completed")]
		with patch.object(frappe.db, "sql", return_value=rows), \
			patch.object(frappe, "get_all", return_value=["DN-1", "DN-2"]), \
			patch("delivery_app.services.monitoring_summary.get_trip_scan_history", return_value={
				"DN-1": {"confirmed_at": now_datetime()}
			}):
			self.assertEqual(fleet_kpis()["completed_trips_today"], 0)

	def test_completion_today_uses_latest_confirmed_scan(self):
		rows = [frappe._dict(name="A", monitoring_state="Completed")]
		with patch.object(frappe.db, "sql", return_value=rows), \
			patch.object(frappe, "get_all", return_value=["DN-1"]), \
			patch("delivery_app.services.monitoring_summary.get_trip_scan_history", return_value={
				"DN-1": {"confirmed_at": now_datetime()}
			}):
			self.assertEqual(fleet_kpis()["completed_trips_today"], 1)
