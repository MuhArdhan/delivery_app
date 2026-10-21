# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import frappe
from frappe.sessions import get_csrf_token


def get_context(context):
	# Require a logged-in user
	if frappe.session.user == "Guest":
		context.guest_login_redirect = True
		context.no_cache = 1
		return context

	context.csrf_token = get_csrf_token()
	context.workspace_user = frappe.get_cached_value("User", frappe.session.user, "full_name") or frappe.session.user
	context.no_cache = 1
	return context
