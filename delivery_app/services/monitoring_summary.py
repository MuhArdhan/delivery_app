"""Shared monitoring predicates for filters and dashboard counts."""

import frappe
from frappe.utils import getdate

from delivery_app.services.fleet_monitoring import get_trip_scan_history


def trip_status_sql(alias="dt"):
	return f"""CASE
		WHEN {alias}.docstatus = 2 THEN 'Cancelled'
		WHEN {alias}.docstatus = 0 THEN 'Draft'
		WHEN EXISTS (SELECT 1 FROM `tabDelivery Stop` ds WHERE ds.parent = {alias}.name)
		 AND NOT EXISTS (SELECT 1 FROM `tabDelivery Stop` ds WHERE ds.parent = {alias}.name AND COALESCE(ds.visited, 0) = 0) THEN 'Completed'
		WHEN {alias}.custom_actual_departure IS NOT NULL
		 OR {alias}.status = 'In Transit'
		 OR EXISTS (SELECT 1 FROM `tabDelivery Stop` ds WHERE ds.parent = {alias}.name AND ds.visited = 1) THEN 'In Transit'
		ELSE 'Scheduled' END"""


def fleet_kpis(company=None):
	company_clause = "AND dt.company = %(company)s" if company else ""
	rows = frappe.db.sql(f"""
		SELECT dt.name, {trip_status_sql()} AS monitoring_state
		FROM `tabDelivery Trip` dt WHERE dt.docstatus = 1 {company_clause}
	""", {"company": company}, as_dict=True)
	completed_today = 0
	for trip in rows:
		if trip.monitoring_state != "Completed":
			continue
		stops = frappe.get_all("Delivery Stop", filters={"parent": trip.name}, pluck="delivery_note")
		history = get_trip_scan_history(trip.name, stops)
		times = [history.get(dn, {}).get("confirmed_at") for dn in stops]
		if times and all(times) and getdate(max(times)) == getdate():
			completed_today += 1
	return {
		"scheduled_trips": sum(t.monitoring_state == "Scheduled" for t in rows),
		"in_transit_trips": sum(t.monitoring_state == "In Transit" for t in rows),
		"completed_trips_today": completed_today,
	}
