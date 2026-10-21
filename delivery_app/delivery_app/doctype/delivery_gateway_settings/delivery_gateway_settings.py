# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DeliveryGatewaySettings(Document):
	def validate(self):
		if self.enabled and not self.api_key:
			frappe.throw(frappe._("Biteship API Key is required when integration is enabled."))

		if self.sync_interval_hours and self.sync_interval_hours < 1:
			self.sync_interval_hours = 1
