# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import json
import requests
import frappe
from frappe import _
from frappe.utils import now_datetime, format_datetime

BITESHIP_API_BASE_URL = "https://api.biteship.com/v1"

STATUS_MAP = {
	"confirmed": "Pending",
	"allocated": "Pending",
	"manifested": "Pending",
	"ready_to_ship": "Pending",
	"pending": "Pending",
	"picking_up": "In Transit",
	"picked": "In Transit",
	"dropping_off": "In Transit",
	"sorting": "In Transit",
	"in_transit": "In Transit",
	"departed": "In Transit",
	"arrived": "In Transit",
	"with_courier": "In Transit",
	"on_hold": "In Transit",
	"delivered": "Delivered",
	"returned": "Returned",
	"cancelled": "Cancelled",
	"disposed": "Failed",
}


def get_gateway_settings():
	"""Fetch single Delivery Gateway Settings doc."""
	settings = frappe.get_single("Delivery Gateway Settings")
	return settings


def get_api_key():
	"""Get decrypted Biteship API key from settings."""
	settings = get_gateway_settings()
	if not settings.enabled:
		frappe.throw(_("Biteship integration is currently disabled in Delivery Gateway Settings."))

	api_key = settings.get_password("api_key", raise_exception=False)
	if not api_key:
		frappe.throw(_("Biteship API Key is missing in Delivery Gateway Settings."))

	return api_key.strip()


@frappe.whitelist()
def test_connection():
	"""Verify Biteship API credentials."""
	try:
		settings = get_gateway_settings()
		api_key = settings.get_password("api_key", raise_exception=False)
		if not api_key:
			return {"success": False, "error": _("API Key is empty. Please enter your Biteship API Key.")}

		headers = {
			"Authorization": f"Bearer {api_key.strip()}",
			"Content-Type": "application/json",
		}
		# Check couriers list endpoint as a lightweight auth check
		resp = requests.get(f"{BITESHIP_API_BASE_URL}/couriers", headers=headers, timeout=15)
		if resp.status_code == 200:
			data = resp.json()
			return {"success": True, "account_name": settings.environment}
		elif resp.status_code == 401 or resp.status_code == 403:
			return {"success": False, "error": _("Authentication failed. Invalid API Key (HTTP {0})").format(resp.status_code)}
		else:
			return {"success": False, "error": f"Biteship API Error: {resp.text}"}
	except Exception as e:
		return {"success": False, "error": str(e)}


def map_biteship_status(raw_status: str) -> str:
	if not raw_status:
		return "Pending"
	cleaned = raw_status.strip().lower()
	return STATUS_MAP.get(cleaned, "In Transit")


def fetch_biteship_tracking(waybill_id: str, courier_code: str) -> dict:
	"""Call Biteship Public Tracking API for given waybill and courier."""
	api_key = get_api_key()
	# Courier code may come as 'jne: JNE Express' -> extract prefix 'jne'
	courier = courier_code.split(":")[0].strip().lower()
	waybill = waybill_id.strip()

	url = f"{BITESHIP_API_BASE_URL}/trackings/{waybill}/couriers/{courier}"
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}

	try:
		response = requests.get(url, headers=headers, timeout=20)
		data = response.json()
	except requests.RequestException as exc:
		return {
			"success": False,
			"error": f"Network error contacting Biteship API: {exc}",
			"raw_status": None,
			"status": "Failed",
			"history": [],
		}

	if not response.ok or not data.get("success", False):
		err_msg = data.get("error") or data.get("message") or response.text
		return {
			"success": False,
			"error": err_msg,
			"code": data.get("code"),
			"raw_status": None,
			"status": "Pending",
			"history": [],
		}

	raw_status = data.get("status") or "pending"
	mapped_status = map_biteship_status(raw_status)

	return {
		"success": True,
		"waybill_id": data.get("waybill_id") or waybill,
		"courier_name": (data.get("courier") or {}).get("name") or courier.upper(),
		"courier_code": courier,
		"raw_status": raw_status,
		"status": mapped_status,
		"link": data.get("link"),
		"history": data.get("history") or [],
	}


def render_error_timeline_html(waybill_id: str, courier_name: str, error_msg: str, error_code=None, current_status="Pending") -> str:
	"""Render honest status when Biteship returns no data or API error (strictly no fabricated events)."""
	status = current_status or "Pending"
	code_str = f" (Kode: {error_code})" if error_code else ""
	return f"""
	<div class="frappe-delivery-tracking-card" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin: 10px 0;">
		<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 16px;">
			<div>
				<span style="font-size: 15px; font-weight: 700; color: #0f172a;">{courier_name}</span>
				<span style="margin-left: 8px; font-family: monospace; font-size: 13px; color: #475569; background: #f8fafc; padding: 3px 8px; border-radius: 4px; border: 1px solid #e2e8f0;">{waybill_id}</span>
			</div>
			<span style="background-color: #f59e0b; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
				{status}
			</span>
		</div>
		<div style="padding: 24px 16px; text-align: center; color: #64748b;">
			<div style="font-weight: 600; color: #0f172a; font-size: 13px; margin-bottom: 6px;">
				Data Pelacakan Belum Ditemukan di Biteship
			</div>
			<div style="font-size: 12px; color: #64748b; line-height: 1.5; max-width: 420px; margin: 0 auto;">
				Respon resmi Biteship: <b>{error_msg}</b>{code_str}.
			</div>
			<div style="font-size: 11px; color: #94a3b8; margin-top: 10px;">
				Pastikan nomor resi valid dan paket sudah diserahkan / di-scan pertama kali oleh kurir.
			</div>
		</div>
	</div>
	"""


def render_tracking_timeline_html(tracking_info: dict) -> str:
	"""Render vertical responsive HTML timeline for real tracking history from Biteship."""
	history = tracking_info.get("history") or []
	status = tracking_info.get("status") or "Pending"
	courier_name = tracking_info.get("courier_name") or tracking_info.get("courier_code", "").upper()
	waybill_id = tracking_info.get("waybill_id") or ""

	badge_color = {
		"Delivered": "#10b981", # Green
		"In Transit": "#3b82f6", # Blue
		"Pending": "#f59e0b",   # Amber
		"Returned": "#ef4444",  # Red
		"Failed": "#ef4444",
		"Cancelled": "#6b7280",
	}.get(status, "#3b82f6")

	timeline_items_html = ""
	if not history:
		timeline_items_html = f"""
		<div style="padding: 16px; color: #64748b; font-style: italic; text-align: center;">
			{_("Belum ada riwayat pergerakan untuk resi ini dari kurir.")}
		</div>
		"""
	else:
		# Show newest event at top if already reversed, or maintain chronological
		for idx, item in enumerate(history):
			note = item.get("note") or item.get("message") or "-"
			raw_time = item.get("updated_at") or item.get("timestamp") or ""
			item_status = item.get("status") or ""
			is_latest = idx == 0

			dot_border = badge_color if is_latest else "#cbd5e1"
			dot_bg = badge_color if is_latest else "#f8fafc"

			timeline_items_html += f"""
			<li style="position: relative; padding-bottom: 20px; padding-left: 28px; list-style: none;">
				<div style="position: absolute; left: 0; top: 4px; width: 14px; height: 14px; border-radius: 50%; border: 3px solid {dot_border}; background-color: {dot_bg};"></div>
				{f'<div style="position: absolute; left: 6px; top: 20px; bottom: 0; width: 2px; background-color: #e2e8f0;"></div>' if idx < len(history) - 1 else ''}
				<div style="font-weight: {600 if is_latest else 400}; color: #1e293b; font-size: 13px;">
					{note}
				</div>
				<div style="font-size: 11px; color: #64748b; margin-top: 3px;">
					<span style="color: #64748b;">Waktu: {raw_time}</span>
					{f'<span style="margin-left: 8px; text-transform: capitalize; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">{item_status.replace("_", " ")}</span>' if item_status else ''}
				</div>
			</li>
			"""

	html = f"""
	<div class="frappe-delivery-tracking-card" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin: 10px 0;">
		<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 16px;">
			<div>
				<span style="font-size: 15px; font-weight: 700; color: #0f172a;">{courier_name}</span>
				<span style="margin-left: 8px; font-family: monospace; font-size: 13px; color: #475569; background: #f8fafc; padding: 3px 8px; border-radius: 4px; border: 1px solid #e2e8f0;">{waybill_id}</span>
			</div>
			<span style="background-color: {badge_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
				{status}
			</span>
		</div>
		<ul style="padding: 0; margin: 0;">
			{timeline_items_html}
		</ul>
	</div>
	"""
	return html


@frappe.whitelist()
def track_delivery_note(delivery_note_name: str = None, delivery_note: str = None) -> dict:
	"""Desk and API method to live-track a Delivery Note resi and update document status from Biteship."""
	name = delivery_note_name or delivery_note
	if not name:
		frappe.throw(_("Delivery Note name is required."))

	dn = frappe.get_doc("Delivery Note", name)
	if dn.custom_delivery_method != "Ekspedisi":
		frappe.throw(_("Delivery Note {0} is not set to 'Ekspedisi' delivery method.").format(name))

	if not dn.custom_waybill_no or not dn.custom_courier_code:
		frappe.throw(_("Please provide Courier and Waybill Number (Resi) before tracking."))

	courier_prefix = dn.custom_courier_code.split(":")[0].strip().lower()
	courier_name = dn.custom_courier_code.split(":")[-1].strip() if ":" in dn.custom_courier_code else courier_prefix.upper()

	tracking_result = None
	try:
		tracking_result = fetch_biteship_tracking(dn.custom_waybill_no, dn.custom_courier_code)
	except Exception as exc:
		frappe.log_error(f"Live tracking error for {dn.name}: {exc}", "Delivery App Biteship")
		return {
			"success": False,
			"error": str(exc),
			"waybill_id": dn.custom_waybill_no,
			"courier_name": courier_name,
			"status": dn.custom_tracking_status or "Pending",
			"history": [],
			"timeline_html": render_error_timeline_html(dn.custom_waybill_no, courier_name, str(exc)),
		}

	# 1. When Biteship returns live tracking data successfully
	if tracking_result and tracking_result.get("success"):
		timeline_html = render_tracking_timeline_html(tracking_result)
		dn.custom_tracking_status = tracking_result.get("status") or dn.custom_tracking_status
		dn.custom_last_tracking_update = now_datetime()
		dn.custom_tracking_history_html = timeline_html
		dn.flags.ignore_validate_update_after_submit = True
		dn.flags.ignore_permissions = True
		dn.save()
		frappe.db.commit()

		tracking_result["timeline_html"] = timeline_html
		return tracking_result

	# 2. When Biteship returns an error (e.g. Data is not found): do NOT fabricate fake events
	error_msg = tracking_result.get("error") if tracking_result else _("Data tracking tidak ditemukan di Biteship")
	error_code = tracking_result.get("code") if tracking_result else None

	timeline_html = render_error_timeline_html(
		waybill_id=dn.custom_waybill_no,
		courier_name=courier_name,
		error_msg=error_msg,
		error_code=error_code,
		current_status=dn.custom_tracking_status,
	)

	return {
		"success": False,
		"error": error_msg,
		"code": error_code,
		"waybill_id": dn.custom_waybill_no,
		"courier_name": courier_name,
		"courier_code": courier_prefix,
		"status": dn.custom_tracking_status or "Pending",
		"history": [],
		"timeline_html": timeline_html,
	}


def sync_active_shipments():
	"""Background task: Polling all In Transit waybills."""
	settings = get_gateway_settings()
	if not settings.enabled or not settings.auto_tracking:
		return

	# Fetch pending/in transit Delivery Notes
	active_dns = frappe.get_all(
		"Delivery Note",
		filters={
			"docstatus": 1,
			"custom_delivery_method": "Ekspedisi",
			"custom_tracking_status": ["in", ["Pending", "In Transit", ""]],
			"custom_waybill_no": ["is", "set"],
			"custom_courier_code": ["is", "set"],
		},
		fields=["name", "custom_waybill_no", "custom_courier_code"],
		limit=50,
	)

	for entry in active_dns:
		try:
			track_delivery_note(entry.name)
		except Exception as e:
			frappe.log_error(f"Error auto-tracking DN {entry.name}: {e}", "Delivery App Auto-Track")


@frappe.whitelist(allow_guest=True)
def handle_webhook():
	"""Inbound webhook handler from Biteship."""
	settings = get_gateway_settings()
	if not settings.enabled:
		return {"status": "ignored", "reason": "integration disabled"}

	# Verify secret if configured (raise_exception=False avoids crashing on unset password)
	secret = settings.get_password("webhook_secret", raise_exception=False)
	if secret:
		auth_header = (
			frappe.get_request_header("Authorization")
			or frappe.get_request_header("X-Biteship-Secret")
			or frappe.get_request_header("X-Biteship-Signature")
			or frappe.get_request_header("biteship-signature")
			or ""
		)
		if auth_header != secret and auth_header != f"Bearer {secret}":
			frappe.throw(_("Unauthorized webhook request"), exc=frappe.PermissionError)

	payload = {}
	if hasattr(frappe, "request") and frappe.request:
		if frappe.request.data:
			try:
				raw = frappe.request.data.decode("utf-8") if isinstance(frappe.request.data, bytes) else frappe.request.data
				payload = json.loads(raw)
			except Exception:
				pass
		if not payload:
			try:
				payload = frappe.request.get_json(silent=True) or {}
			except Exception:
				pass

	if not payload and hasattr(frappe, "form_dict"):
		payload = dict(frappe.form_dict)

	if not payload:
		# Health check / ping acknowledgment
		return {"status": "ok", "message": "Delivery App Biteship Webhook receiver is active"}

	event = payload.get("event") or ""
	waybill_id = (
		payload.get("courier_waybill_id")
		or payload.get("waybill_id")
		or payload.get("courier_tracking_id")
		or payload.get("tracking_id")
	)
	order_id = payload.get("order_id")
	raw_status = payload.get("status")
	courier_code = payload.get("courier_company") or payload.get("courier_code") or ""

	if not waybill_id and not order_id:
		return {"status": "ignored", "reason": "no waybill_id or order_id in payload"}

	# Find matching Delivery Note(s)
	dns = []
	if waybill_id:
		dns = frappe.get_all(
			"Delivery Note",
			filters={"custom_waybill_no": str(waybill_id).strip()},
			pluck="name",
		)
		if not dns:
			dns = frappe.db.sql_list(
				"""
				SELECT name FROM `tabDelivery Note`
				WHERE TRIM(UPPER(custom_waybill_no)) = %s
				""",
				(str(waybill_id).strip().upper(),)
			)

	if not dns and order_id:
		dns = frappe.get_all(
			"Delivery Note",
			filters={"custom_waybill_no": str(order_id).strip()},
			pluck="name",
		)

	if not dns:
		return {
			"status": "ignored",
			"reason": f"No Delivery Note found for waybill {waybill_id}",
			"waybill_id": waybill_id,
		}

	mapped_status = map_biteship_status(raw_status) if raw_status else None
	updated = []

	for dn_name in dns:
		try:
			dn = frappe.get_doc("Delivery Note", dn_name)
			if mapped_status:
				dn.custom_tracking_status = mapped_status
			dn.custom_last_tracking_update = now_datetime()

			# Format event note
			event_note = payload.get("note") or payload.get("message")
			if not event_note:
				if raw_status:
					event_note = f"Status ekspedisi diperbarui: {raw_status.replace('_', ' ').capitalize()}"
				else:
					event_note = f"Update status pengiriman dari kurir {courier_code or ''}"

			if payload.get("courier_driver_name"):
				event_note += f" (Kurir: {payload.get('courier_driver_name')})"

			# Check if full tracking can be refreshed or construct append
			tracking_result = None
			if dn.custom_waybill_no and dn.custom_courier_code:
				try:
					tracking_result = fetch_biteship_tracking(dn.custom_waybill_no, dn.custom_courier_code)
				except Exception:
					tracking_result = None

			if tracking_result and tracking_result.get("success") and tracking_result.get("history"):
				dn.custom_tracking_status = tracking_result.get("status") or dn.custom_tracking_status
				dn.custom_tracking_history_html = render_tracking_timeline_html(tracking_result)
			else:
				# Use webhook payload event
				now_str = format_datetime(now_datetime(), "yyyy-MM-dd HH:mm:ss")
				courier_name = (dn.custom_courier_code or courier_code or "EKSPEDISI").split(":")[-1].strip()
				single_event_info = {
					"success": True,
					"waybill_id": dn.custom_waybill_no or waybill_id,
					"courier_name": courier_name,
					"courier_code": (dn.custom_courier_code or courier_code or "").split(":")[0].strip().lower(),
					"status": dn.custom_tracking_status or mapped_status or "In Transit",
					"raw_status": raw_status,
					"history": [
						{
							"note": event_note,
							"updated_at": now_str,
							"status": raw_status or "in_transit",
						}
					],
				}
				dn.custom_tracking_history_html = render_tracking_timeline_html(single_event_info)

			dn.flags.ignore_validate_update_after_submit = True
			dn.flags.ignore_permissions = True
			dn.save()
			frappe.db.commit()
			updated.append(dn.name)
		except Exception as e:
			frappe.log_error(f"Webhook update failed for {dn_name}: {e}", "Delivery Webhook Error")

	return {
		"status": "success",
		"updated_count": len(updated),
		"delivery_notes": updated,
		"waybill_id": waybill_id,
		"tracking_status": mapped_status,
	}
