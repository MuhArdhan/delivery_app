# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ProofofDelivery(Document):
	def validate(self):
		if not self.submitted_at:
			self.submitted_at = now_datetime()

		if not self.delivered_by:
			self.delivered_by = frappe.session.user

		if self.delivery_note:
			dn = frappe.db.get_value("Delivery Note", self.delivery_note, ["docstatus", "customer", "customer_name"], as_dict=True)
			if not dn:
				frappe.throw(frappe._("Delivery Note {0} does not exist.").format(self.delivery_note))
			if dn.docstatus != 1:
				frappe.msgprint(frappe._("Warning: Delivery Note {0} is not submitted yet.").format(self.delivery_note), indicator="orange")

			if not self.customer:
				self.customer = dn.customer
			if not self.customer_name:
				self.customer_name = dn.customer_name

	def on_submit(self):
		self.update_delivery_note_and_trip()

	def on_update(self):
		if self.status == "Verified" or self.status == "Submitted":
			self.update_delivery_note_and_trip()
		elif self.status == "Rejected":
			self.revert_delivery_note_and_trip()

	def update_delivery_note_and_trip(self):
		# 1. Update linked Delivery Note
		if self.delivery_note:
			dn = frappe.get_doc("Delivery Note", self.delivery_note)
			changed = False
			if hasattr(dn, "custom_pod_status") and dn.custom_pod_status != "Delivered":
				dn.custom_pod_status = "Delivered"
				changed = True
			if hasattr(dn, "custom_proof_of_delivery") and dn.custom_proof_of_delivery != self.name:
				dn.custom_proof_of_delivery = self.name
				changed = True
			if changed:
				dn.flags.ignore_validate_update_after_submit = True
				dn.flags.ignore_permissions = True
				dn.save()

		# 2. Update linked Delivery Trip if present
		if self.delivery_trip:
			trip = frappe.get_doc("Delivery Trip", self.delivery_trip)
			stop_updated = False
			for stop in trip.delivery_stops:
				# match by delivery_note or stop name or customer
				if (stop.delivery_note and stop.delivery_note == self.delivery_note) or (self.delivery_stop and stop.name == self.delivery_stop):
					if not stop.visited:
						stop.visited = 1
						stop_updated = True
					if hasattr(stop, "custom_proof_of_delivery") and stop.custom_proof_of_delivery != self.name:
						stop.custom_proof_of_delivery = self.name
						stop_updated = True

			# Check if all stops in trip are now visited
			all_visited = all(bool(s.visited) for s in trip.delivery_stops)
			if all_visited and trip.status in ["Draft", "Scheduled", "In Transit"]:
				trip.status = "Completed"
				stop_updated = True

			if stop_updated:
				trip.flags.ignore_validate_update_after_submit = True
				trip.flags.ignore_permissions = True
				trip.save()

	def revert_delivery_note_and_trip(self):
		if self.delivery_note:
			dn = frappe.get_doc("Delivery Note", self.delivery_note)
			if hasattr(dn, "custom_pod_status") and dn.custom_pod_status == "Delivered":
				dn.custom_pod_status = "Pending"
				if hasattr(dn, "custom_proof_of_delivery") and dn.custom_proof_of_delivery == self.name:
					dn.custom_proof_of_delivery = None
				dn.flags.ignore_validate_update_after_submit = True
				dn.flags.ignore_permissions = True
				dn.save()


# Backward compatibility and alternative casing
ProofOfDelivery = ProofofDelivery
