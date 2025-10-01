# apps/homie_app/homie_app/api.py
import frappe
import json
from frappe import _
from frappe.utils import get_datetime


def _parse_request_json():
    """Parse JSON body and merge with query params (form_dict)."""
    data = {}
    try:
        if frappe.request.data:
            data = json.loads(frappe.request.data) or {}
    except Exception:
        pass
    return {**frappe.form_dict, **data}


def normalize_bool(val):
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, str):
        return 1 if val.lower() in ["true", "1", "yes"] else 0
    return 0



    
@frappe.whitelist(allow_guest=True)   # allow_guest=True lets you call without login
def create_donation():
    """
    Create a Donation and child Donation Items.
    Idempotency: if a Donation with same 'hash' or 'donation_number' exists, returns it (no duplicate).
    """
    payload = _parse_request_json()

    # idempotency check
    existing = None
    if payload.get("hash"):
        existing = frappe.db.get_value("Donation", {"hash": payload.get("hash")}, "name")

    if not existing and payload.get("donation_number"):
        existing = frappe.db.get_value("Donation", {"donation_number": payload.get("donation_number")}, "name")

    if existing:
        doc = frappe.get_doc("Donation", existing)
        return {"status": "exists", "donation": doc.as_dict()}

    # build donation items for child table
    items = []
    for it in payload.get("items", []):
        items.append({
            "doctype": "Donation Item",
            "wishlist_item": it.get("wishlist_item"),
            "quantity": it.get("quantity") or 1,
            "total": it.get("total") or 0
        })

    doc = frappe.get_doc({
        "doctype": "Donation",
        "hash": payload.get("hash"),
        "donation_number": payload.get("donation_number"),
        "email": payload.get("email"),
        "first_name": payload.get("first_name"),
        "last_name": payload.get("last_name"),
        "is_anonymous": normalize_bool(payload.get("is_anonymous")),
        "donated_at": get_datetime(payload.get("donated_at")) if payload.get("donated_at") else None,
        "total": float(payload.get("total") or 0),
        "currency": payload.get("currency"),
        "wishlist": payload.get("wishlist"),
        "source": payload.get("source"),
        "company": payload.get("company"),
        "ip_address": payload.get("ip_address"),
        "user_agent": payload.get("user_agent"),
        "is_subscription": normalize_bool(payload.get("is_subscription")),
        "items": payload.get("items", []),
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok", "donation": doc.as_dict()}



@frappe.whitelist(allow_guest=True)   # allow_guest=True lets you call without login
def create_payment():
    """
    Create a Donation Payment and link to Donation if possible.
    Idempotency: if 'number' (transaction id) or 'hash' already exists, returns existing.
    Accepts optional donation reference: donation_hash OR donation_number.
    """
    payload = _parse_request_json()

    # idempotency - avoid duplicate payments by 'number' OR 'hash'
    existing = None
    if payload.get("number"):
        existing = frappe.db.get_value("Donation Payment", {"number": payload.get("number")}, "name")
    if not existing and payload.get("hash"):
        existing = frappe.db.get_value("Donation Payment", {"hash": payload.get("hash")}, "name")

    if existing:
        doc = frappe.get_doc("Donation Payment", existing)
        return {"status": "exists", "payment": doc.as_dict()}

    # try linking to donation
    donation_name = None
    if payload.get("donation_hash"):
        res = frappe.get_all("Donation", filters={"hash": payload.get("donation_hash")}, fields=["name"], limit=1)
        if res:
            donation_name = res[0].name
    elif payload.get("donation_number"):
        res = frappe.get_all("Donation", filters={"donation_number": payload.get("donation_number")}, fields=["name"], limit=1)
        if res:
            donation_name = res[0].name

    payment_doc = frappe.get_doc({
        "doctype": "Donation Payment",
        "hash": payload.get("hash"),
        "type": payload.get("type"),
        "amount": payload.get("amount") or 0,
        "info_1": payload.get("info_1"),
        "info_2": payload.get("info_2"),
        "info_3": payload.get("info_3"),
        "number": payload.get("number"),
        "provider": payload.get("provider"),
        "payment_at": get_datetime(payload.get("payment_at")) if payload.get("payment_at") else None,
        "donation": donation_name,
        "created_from_payload": 1
    })

    payment_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "ok", "payment": payment_doc.as_dict()}
