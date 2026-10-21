# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.exceptions import ValidationError

from delivery_app.services.so_intake import (
	create_delivery_note_from_so,
	get_eligible_sales_orders,
	get_sales_order_intake_detail,
)


class TestSalesOrderIntake(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		if not frappe.db:
			frappe.init(site="development.localhost")
			frappe.connect()

	def test_create_dn_rejects_missing_so(self):
		with self.assertRaises(frappe.ValidationError):
			create_delivery_note_from_so("")

	def test_create_dn_rejects_invalid_method(self):
		with self.assertRaises(frappe.ValidationError):
			create_delivery_note_from_so("SO-TEST-001", delivery_method="Metode Lain")

	def test_create_dn_rejects_unsubmitted_so(self):
		def mock_sql(query, values=None, **kwargs):
			if "FOR UPDATE" in query:
				return [SimpleNamespace(name="SO-001", docstatus=0, status="Draft", per_delivered=0.0, company="ROPI")]
			return []

		with patch.object(frappe.db, "sql", side_effect=mock_sql):
			with self.assertRaises(frappe.ValidationError):
				create_delivery_note_from_so("SO-001")

	def test_create_dn_rejects_closed_or_cancelled_so(self):
		def mock_sql(query, values=None, **kwargs):
			if "FOR UPDATE" in query:
				return [SimpleNamespace(name="SO-001", docstatus=1, status="Closed", per_delivered=0.0, company="ROPI")]
			return []

		with patch.object(frappe.db, "sql", side_effect=mock_sql):
			with self.assertRaises(frappe.ValidationError):
				create_delivery_note_from_so("SO-001")

	def test_create_dn_rejects_partially_delivered_so(self):
		def mock_sql(query, values=None, **kwargs):
			if "FOR UPDATE" in query:
				return [SimpleNamespace(name="SO-001", docstatus=1, status="To Deliver and Bill", per_delivered=50.0, company="ROPI")]
			return []

		with patch.object(frappe.db, "sql", side_effect=mock_sql):
			with self.assertRaises(frappe.ValidationError):
				create_delivery_note_from_so("SO-001")

	def test_create_dn_rejects_duplicate_active_dn(self):
		def mock_sql(query, values=None, **kwargs):
			if "FOR UPDATE" in query:
				return [SimpleNamespace(name="SO-001", docstatus=1, status="To Deliver and Bill", per_delivered=0.0, company="ROPI")]
			if "tabDelivery Note Item" in query:
				return [SimpleNamespace(name="DN-EXISTING", docstatus=1)]
			return []

		with patch.object(frappe.db, "sql", side_effect=mock_sql):
			with self.assertRaises(frappe.ValidationError):
				create_delivery_note_from_so("SO-001")

	def test_create_dn_verifies_full_quantity_mapping(self):
		so_locked = [SimpleNamespace(name="SO-001", docstatus=1, status="To Deliver and Bill", per_delivered=0.0, company="ROPI")]

		def mock_sql(query, values=None, **kwargs):
			if "FOR UPDATE" in query:
				return so_locked
			if "tabDelivery Note Item" in query:
				return []
			return []

		mock_dn = SimpleNamespace(
			name="DN-NEW-001",
			items=[SimpleNamespace(so_detail="item_1", qty=5.0)],  # Only 5, but SO has 10
			customer="Cust A",
			company="ROPI",
			grand_total=100000,
			total_qty=5.0,
			insert=Mock(),
			submit=Mock()
		)

		so_items = [SimpleNamespace(name="item_1", item_code="ROTI", qty=10.0)]

		with patch.object(frappe.db, "sql", side_effect=mock_sql), \
		     patch("delivery_app.services.so_intake.make_delivery_note", return_value=mock_dn), \
		     patch.object(frappe, "get_all", return_value=so_items):
			with self.assertRaises(frappe.ValidationError):
				create_delivery_note_from_so("SO-001")

	def test_create_dn_success_armada_sendiri(self):
		so_locked = [SimpleNamespace(name="SO-001", docstatus=1, status="To Deliver and Bill", per_delivered=0.0, company="ROPI")]

		def mock_sql(query, values=None, **kwargs):
			if "FOR UPDATE" in query:
				return so_locked
			if "tabDelivery Note Item" in query:
				return []
			return []

		mock_dn = SimpleNamespace(
			name="DN-NEW-001",
			items=[SimpleNamespace(so_detail="item_1", qty=10.0, warehouse="Gudang A")],
			customer="Cust A",
			company="ROPI",
			grand_total=100000,
			total_qty=10.0,
			custom_delivery_method=None,
			custom_pod_status=None,
			insert=Mock(),
			submit=Mock()
		)

		so_items = [SimpleNamespace(name="item_1", item_code="ROTI", qty=10.0)]

		with patch.object(frappe.db, "sql", side_effect=mock_sql), \
		     patch("delivery_app.services.so_intake.make_delivery_note", return_value=mock_dn), \
		     patch.object(frappe, "get_all", return_value=so_items), \
		     patch.object(frappe.db, "savepoint"), \
		     patch.object(frappe.db, "commit"):
			res = create_delivery_note_from_so("SO-001", delivery_method="Armada Sendiri")

			self.assertTrue(res["success"])
			self.assertEqual(res["delivery_note"], "DN-NEW-001")
			self.assertEqual(mock_dn.custom_delivery_method, "Armada Sendiri")
			self.assertEqual(mock_dn.custom_pod_status, "Pending")
			mock_dn.insert.assert_called_once()
			mock_dn.submit.assert_called_once()

	def test_create_dn_rollback_on_submit_failure(self):
		so_locked = [SimpleNamespace(name="SO-001", docstatus=1, status="To Deliver and Bill", per_delivered=0.0, company="ROPI")]

		def mock_sql(query, values=None, **kwargs):
			if "FOR UPDATE" in query:
				return so_locked
			if "tabDelivery Note Item" in query:
				return []
			return []

		mock_dn = SimpleNamespace(
			name="DN-NEW-001",
			items=[SimpleNamespace(so_detail="item_1", qty=10.0, warehouse="Gudang A")],
			customer="Cust A",
			company="ROPI",
			grand_total=100000,
			total_qty=10.0,
			insert=Mock(),
			submit=Mock(side_effect=Exception("Insufficient Stock in Gudang A"))
		)

		so_items = [SimpleNamespace(name="item_1", item_code="ROTI", qty=10.0)]

		with patch.object(frappe.db, "sql", side_effect=mock_sql), \
		     patch("delivery_app.services.so_intake.make_delivery_note", return_value=mock_dn), \
		     patch.object(frappe, "get_all", return_value=so_items), \
		     patch.object(frappe.db, "savepoint"), \
		     patch.object(frappe.db, "rollback") as mock_rollback:
			with self.assertRaises(Exception):
				create_delivery_note_from_so("SO-001")

			mock_rollback.assert_called_once()
