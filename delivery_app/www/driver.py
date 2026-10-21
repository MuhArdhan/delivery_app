# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import frappe
from urllib.parse import quote


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(
			frappe.request.path or "/driver", safe=""
		)
		raise frappe.Redirect

	csrf_token = ""
	try:
		if hasattr(frappe.local, "session") and hasattr(frappe.local.session, "data"):
			csrf_token = frappe.local.session.data.get("csrf_token", "")
		if not csrf_token:
			from frappe.sessions import get_csrf_token
			csrf_token = get_csrf_token()
	except Exception:
		csrf_token = ""

	context.no_cache = 1
	context.csrf_token = csrf_token
	context.user_fullname = frappe.utils.get_fullname(frappe.session.user)
	context.user_id = frappe.session.user

	# Fetch driver record if linked
	driver = frappe.db.get_value("Driver", {"user": frappe.session.user}, ["name", "full_name", "cell_number"], as_dict=True)
	if not driver:
		employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if employee:
			driver = frappe.db.get_value("Driver", {"employee": employee}, ["name", "full_name", "cell_number"], as_dict=True)

	context.driver_name = driver.full_name if driver else context.user_fullname
	context.driver_id = driver.name if driver else None
	return context
