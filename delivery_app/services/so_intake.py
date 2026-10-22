# Copyright (c) 2026, Muhammad Ardhan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from delivery_app.services.fleet_monitoring import _clean_coord


def get_eligible_sales_orders(
	company: str = None,
	date_from: str = None,
	date_to: str = None,
	search: str = None,
	status_filter: str = "all",
	page: int = 1,
	page_size: int = 20,
):
	"""
	List submitted Sales Orders eligible for Delivery Note intake.
	Filterable by company, date range, search query, and intake eligibility status.
	"""
	page = max(1, cint(page))
	page_size = max(1, cint(page_size))
	offset = (page - 1) * page_size

	conditions = ["so.docstatus = 1", "so.status NOT IN ('Closed', 'Cancelled')"]
	params = {}

	if company:
		conditions.append("so.company = %(company)s")
		params["company"] = company

	if date_from:
		conditions.append("so.transaction_date >= %(date_from)s")
		params["date_from"] = date_from

	if date_to:
		conditions.append("so.transaction_date <= %(date_to)s")
		params["date_to"] = date_to

	if search:
		conditions.append("""(
			so.name LIKE %(search)s
			OR so.customer LIKE %(search)s
			OR so.customer_name LIKE %(search)s
			OR so.shipping_address LIKE %(search)s
		)""")
		params["search"] = f"%{search}%"

	if status_filter == "ready":
		conditions.append("so.per_delivered = 0")
	elif status_filter == "partial":
		conditions.append("so.per_delivered > 0 AND so.per_delivered < 100")
	elif status_filter == "delivered":
		conditions.append("so.per_delivered >= 100")

	where_clause = " AND ".join(conditions)

	total_count = frappe.db.sql(f"""
		SELECT COUNT(so.name)
		FROM `tabSales Order` so
		WHERE {where_clause}
	""", params)[0][0] or 0

	query = f"""
		SELECT
			so.name, so.customer, so.customer_name, so.company,
			so.transaction_date, so.delivery_date, so.grand_total,
			so.status, so.per_delivered, so.shipping_address_name,
			so.shipping_address
		FROM `tabSales Order` so
		WHERE {where_clause}
		ORDER BY so.transaction_date DESC, so.creation DESC
		LIMIT {page_size} OFFSET {offset}
	"""

	orders = frappe.db.sql(query, params, as_dict=True)

	so_names = [o.name for o in orders]
	existing_dns_map = {}
	if so_names:
		dn_records = frappe.db.sql("""
			SELECT DISTINCT dni.against_sales_order, dn.name, dn.docstatus, dn.status,
			       dn.custom_delivery_method, dn.posting_date, dn.grand_total
			FROM `tabDelivery Note Item` dni
			INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
			WHERE dni.against_sales_order IN %(so_names)s AND dn.docstatus IN (0, 1)
			ORDER BY dn.creation DESC
		""", {"so_names": tuple(so_names)}, as_dict=True)
		for r in dn_records:
			if r.against_sales_order not in existing_dns_map:
				existing_dns_map[r.against_sales_order] = r

	customers = list({o.customer for o in orders if o.customer})
	cust_coords_map = {}
	if customers:
		cust_records = frappe.get_all(
			"Customer",
			filters={"name": ["in", customers]},
			fields=["name", "custom_latitude", "custom_longitude"]
		)
		for c in cust_records:
			cust_coords_map[c.name] = (
				_clean_coord(c.get("custom_latitude")),
				_clean_coord(c.get("custom_longitude"))
			)

	item_stats_map = {}
	if so_names:
		stats = frappe.db.sql("""
			SELECT parent, COUNT(name) as total_items, SUM(qty) as total_qty
			FROM `tabSales Order Item`
			WHERE parent IN %(so_names)s
			GROUP BY parent
		""", {"so_names": tuple(so_names)}, as_dict=True)
		for s in stats:
			item_stats_map[s.parent] = s

	results = []
	for o in orders:
		so_name = o.name
		per_del = flt(o.per_delivered)
		existing_dn = existing_dns_map.get(so_name)
		stats = item_stats_map.get(so_name) or {}
		c_lat, c_lng = cust_coords_map.get(o.customer, (None, None))

		is_eligible = bool(per_del == 0.0 and existing_dn is None)

		if existing_dn:
			intake_status = "already_created"
			intake_status_label = f"DN Dibuat ({existing_dn.name})"
		elif per_del >= 100.0:
			intake_status = "completed"
			intake_status_label = "Selesai Kirim"
		elif per_del > 0.0:
			intake_status = "partial"
			intake_status_label = f"Parsial ({round(per_del, 1)}%)"
		else:
			intake_status = "ready"
			intake_status_label = "Siap Diproses"

		clean_addr = (o.shipping_address or "").replace("<br>", ", ").replace("\n", ", ").strip()
		clean_addr = ", ".join([part.strip() for part in clean_addr.split(",") if part.strip()])

		results.append({
			"name": o.name,
			"customer": o.customer,
			"customer_name": o.customer_name or o.customer,
			"company": o.company,
			"transaction_date": o.transaction_date,
			"delivery_date": o.delivery_date,
			"grand_total": o.grand_total,
			"status": o.status,
			"per_delivered": per_del,
			"is_eligible": is_eligible,
			"intake_status": intake_status,
			"intake_status_label": intake_status_label,
			"existing_dn": existing_dn.name if existing_dn else None,
			"existing_dn_docstatus": existing_dn.docstatus if existing_dn else None,
			"existing_dn_method": existing_dn.custom_delivery_method if existing_dn else None,
			"shipping_address": clean_addr,
			"shipping_address_name": o.shipping_address_name,
			"has_coordinates": bool(c_lat is not None and c_lng is not None),
			"lat": c_lat,
			"lng": c_lng,
			"total_items": stats.get("total_items", 0),
			"total_qty": stats.get("total_qty", 0.0),
		})

	return {
		"items": results,
		"total_count": total_count,
		"page": page,
		"page_size": page_size,
	}


def get_sales_order_intake_detail(sales_order: str):
	"""
	Fetch comprehensive detail of a single Sales Order for intake verification and modal review.
	"""
	if not sales_order:
		frappe.throw(_("Sales Order harus ditentukan."))

	so = frappe.get_doc("Sales Order", sales_order)
	if so.docstatus != 1:
		frappe.throw(_("Sales Order {0} belum berstatus Submitted.").format(sales_order))

	items = []
	for it in so.items:
		items.append({
			"name": it.name,
			"item_code": it.item_code,
			"item_name": it.item_name,
			"description": it.description,
			"qty": it.qty,
			"uom": it.uom,
			"rate": it.rate,
			"amount": it.amount,
			"warehouse": it.warehouse,
			"delivered_qty": it.delivered_qty,
		})

	cust_lat, cust_lng = frappe.db.get_value("Customer", so.customer, ["custom_latitude", "custom_longitude"]) or (None, None)
	comp_lat, comp_lng = frappe.db.get_value("Company", so.company, ["custom_latitude", "custom_longitude"]) or (None, None)

	existing_dn = frappe.db.sql("""
		SELECT DISTINCT dn.name, dn.docstatus, dn.status, dn.custom_delivery_method, dn.grand_total
		FROM `tabDelivery Note Item` dni
		INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
		WHERE dni.against_sales_order = %s AND dn.docstatus IN (0, 1)
		ORDER BY dn.creation DESC
		LIMIT 1
	""", (sales_order,), as_dict=True)

	existing = existing_dn[0] if existing_dn else None

	clean_addr = (so.shipping_address or "").replace("<br>", ", ").replace("\n", ", ").strip()
	clean_addr = ", ".join([part.strip() for part in clean_addr.split(",") if part.strip()])

	return {
		"name": so.name,
		"customer": so.customer,
		"customer_name": so.customer_name or so.customer,
		"company": so.company,
		"transaction_date": so.transaction_date,
		"delivery_date": so.delivery_date,
		"grand_total": so.grand_total,
		"status": so.status,
		"per_delivered": flt(so.per_delivered),
		"shipping_address": clean_addr,
		"shipping_address_name": so.shipping_address_name,
		"customer_lat": _clean_coord(cust_lat),
		"customer_lng": _clean_coord(cust_lng),
		"has_customer_coordinates": bool(_clean_coord(cust_lat) is not None and _clean_coord(cust_lng) is not None),
		"company_lat": _clean_coord(comp_lat),
		"company_lng": _clean_coord(comp_lng),
		"has_company_coordinates": bool(_clean_coord(comp_lat) is not None and _clean_coord(comp_lng) is not None),
		"items": items,
		"existing_dn": existing,
		"is_eligible": bool(flt(so.per_delivered) == 0.0 and not existing),
	}


def create_delivery_note_from_so(sales_order: str, delivery_method: str = "Armada Sendiri", custom_warehouse: str = None):
	"""
	Atomic intake: creates 1 full Delivery Note from 1 submitted Sales Order.
	Locks the Sales Order row to avoid duplicate creation or race conditions.
	"""
	if not sales_order:
		frappe.throw(_("Sales Order harus ditentukan."))

	clean_method = (delivery_method or "Armada Sendiri").strip()
	if clean_method not in ["Armada Sendiri", "Ekspedisi"]:
		frappe.throw(_("Metode tracking tidak valid. Pilih Checkpoint Scanner atau Resi Ekspedisi."))

	so_locked = frappe.db.sql("""
		SELECT name, docstatus, status, per_delivered, company
		FROM `tabSales Order`
		WHERE name = %s
		FOR UPDATE
	""", (sales_order,), as_dict=True)

	if not so_locked:
		frappe.throw(_("Sales Order {0} tidak ditemukan.").format(sales_order))

	so_row = so_locked[0]

	if so_row.docstatus != 1:
		frappe.throw(_("Sales Order {0} belum berstatus Submitted.").format(sales_order))

	if so_row.status in ["Closed", "Cancelled"]:
		frappe.throw(_("Sales Order {0} tidak dapat diproses karena berstatus {1}.").format(sales_order, so_row.status))

	if flt(so_row.per_delivered) > 0.0:
		frappe.throw(
			_("Sales Order {0} sudah memiliki pengiriman parsial ({1}%). Alur intake ini hanya memproses Sales Order penuh 100%.").format(
				sales_order, round(flt(so_row.per_delivered), 1)
			)
		)

	existing_dn = frappe.db.sql("""
		SELECT DISTINCT dn.name, dn.docstatus
		FROM `tabDelivery Note Item` dni
		INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
		WHERE dni.against_sales_order = %s AND dn.docstatus IN (0, 1)
		LIMIT 1
	""", (sales_order,), as_dict=True)

	if existing_dn:
		dn_name = existing_dn[0].name
		dn_status = "Submitted" if existing_dn[0].docstatus == 1 else "Draft"
		frappe.throw(
			_("Sales Order {0} sudah memiliki Delivery Note aktif ({1} - {2}). Duplikasi tidak diizinkan.").format(
				sales_order, dn_name, dn_status
			)
		)

	dn = make_delivery_note(sales_order)

	so_items = frappe.get_all(
		"Sales Order Item",
		filters={"parent": sales_order},
		fields=["name", "item_code", "qty"]
	)
	so_qty_map = {item.name: flt(item.qty) for item in so_items}
	dn_items_so_details = {item.so_detail: flt(item.qty) for item in dn.items if getattr(item, "so_detail", None)}

	for so_detail_id, expected_qty in so_qty_map.items():
		mapped_qty = dn_items_so_details.get(so_detail_id, 0.0)
		if mapped_qty < expected_qty:
			frappe.throw(
				_("Kuantitas mapping tidak penuh untuk SO Item {0}. Dibutuhkan: {1}, terpetakan: {2}.").format(
					so_detail_id, expected_qty, mapped_qty
				)
			)

	if custom_warehouse:
		for item in dn.items:
			if not item.warehouse:
				item.warehouse = custom_warehouse

	dn.custom_delivery_method = clean_method
	dn.custom_pod_status = "Pending"

	savepoint = f"dn_intake_{frappe.generate_hash(length=8)}"
	frappe.db.savepoint(savepoint)
	try:
		dn.insert()
		dn.submit()
		frappe.db.commit()
	except Exception as err:
		frappe.db.rollback(save_point=savepoint)
		frappe.log_error(f"Gagal memproses DN untuk SO {sales_order}: {str(err)}", "Delivery App SO Intake")
		raise

	return {
		"success": True,
		"delivery_note": dn.name,
		"sales_order": sales_order,
		"customer": dn.customer,
		"company": dn.company,
		"grand_total": dn.grand_total,
		"total_qty": dn.total_qty,
		"custom_delivery_method": dn.custom_delivery_method,
		"message": _("Delivery Note {0} berhasil dibuat dan disubmit.").format(dn.name)
	}
