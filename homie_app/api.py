# apps/homie_app/homie_app/api.py
import frappe
import json
from frappe import _
from frappe.utils import get_datetime


import re
import frappe
import json
from frappe.utils import get_datetime





def require_login():
    if frappe.session.user == "Guest":
        frappe.throw("Authentication required. Please login first.", frappe.PermissionError)


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


def validate_payload(payload):
    """Custom validation rules for donation payload"""

    # 1. Validate hash (must be 32 or 33 chars, only alphanumeric)
    hash_val = payload.get("hash")
    if not hash_val or not re.fullmatch(r"[A-Za-z0-9]{32,33}", hash_val):
        frappe.throw("Invalid 'hash'. Must be 32 or 33 characters, only numbers and letters.")

    # 2. Validate donation_number (optional, but no special chars except dash/underscore)
    if payload.get("donation_number") and not re.fullmatch(r"[A-Za-z0-9\-_]+", payload["donation_number"]):
        frappe.throw("Invalid 'donation_number'. Only letters, numbers, dashes and underscores allowed.")

    # 3. Validate email (basic pattern)
    if payload.get("email") and not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", payload["email"]):
        frappe.throw("Invalid 'email' format.")

    # 4. Validate items (each item must follow rules)
    for idx, it in enumerate(payload.get("items", []), start=1):
        # quantity must be integer > 0
        qty = it.get("quantity", 0)
        if not isinstance(qty, int) or qty <= 0:
            frappe.throw(f"Invalid quantity in item {idx}. Must be a positive integer.")

        # total must be positive float or int
        total = it.get("total", 0)
        if not isinstance(total, (int, float)) or total <= 0:
            frappe.throw(f"Invalid total in item {idx}. Must be a positive number.")

        # wishlist_item must be alphanumeric (UUID-style check here)
        wishlist_item = it.get("wishlist_item")
        if not wishlist_item or not re.fullmatch(r"[A-Za-z0-9\-]+", wishlist_item):
            frappe.throw(f"Invalid wishlist_item in item {idx}. Only letters, numbers, and dashes allowed.")

    # 5. Validate wishlist field itself (same as wishlist_item, if present)
    if payload.get("wishlist") and not re.fullmatch(r"[A-Za-z0-9\-]+", payload["wishlist"]):
        frappe.throw("Invalid 'wishlist'. Only letters, numbers, and dashes allowed.")

    # 6. Validate currency (3-letter code like USD, EUR, PKR)
    if payload.get("currency") and not re.fullmatch(r"[A-Z]{3}", payload["currency"]):
        frappe.throw("Invalid 'currency'. Must be a 3-letter code (e.g., USD, EUR, PKR).")

    # 7. Validate names (first and last name, only letters allowed)
    if payload.get("first_name") and not re.fullmatch(r"[A-Za-z]+", payload["first_name"]):
        frappe.throw("Invalid 'first_name'. Only alphabets allowed.")
    if payload.get("last_name") and not re.fullmatch(r"[A-Za-z]+", payload["last_name"]):
        frappe.throw("Invalid 'last_name'. Only alphabets allowed.")


@frappe.whitelist()
def create_donation():
    """
    Create a Donation and child Donation Items.
    Idempotency: if a Donation with same 'hash' or 'donation_number' exists, returns it (no duplicate).
    """
    require_login()

    payload = _parse_request_json()

    # ✅ Apply validation before inserting
    validate_payload(payload)

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
            "quantity": it.get("quantity"),
            "total": it.get("total")
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
        "items": items,
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok", "donation": doc.as_dict()}




@frappe.whitelist()
def create_payment():
    require_login()

    """
    Create a Donation Payment and link to Donation if possible.
    Idempotency: if 'number' (transaction id) or 'hash' already exists, returns existing.
    Accepts optional donation reference: donation_hash OR donation_number.
    """
    payload = frappe.local.form_dict  # works for JSON or query params

    # -------------------------
    # 🔹 VALIDATIONS
    # -------------------------
    required_fields = ["hash", "type", "amount", "number", "provider"]
    errors = {}

    # required fields check
    for field in required_fields:
        if not payload.get(field):
            errors[field] = f"{field} is required"

    # amount must be positive
    if payload.get("amount"):
        try:
            amount_val = float(payload.get("amount"))
            if amount_val <= 0:
                errors["amount"] = "Amount must be greater than 0"
        except ValueError:
            errors["amount"] = "Amount must be a valid number"

    # type validation (must be deposit / withdraw / refund)
    valid_types = ["deposit", "withdraw", "refund"]
    if payload.get("type") and payload.get("type").lower() not in valid_types:
        errors["type"] = f"Invalid type. Must be one of {valid_types}"

    # provider validation (paypal, stripe, bank, etc.)
    valid_providers = ["paypal", "stripe", "bank", "cash"]
    if payload.get("provider") and payload.get("provider").lower() not in valid_providers:
        errors["provider"] = f"Invalid provider. Must be one of {valid_providers}"

    # datetime format validation
    if payload.get("payment_at"):
        try:
            get_datetime(payload.get("payment_at"))
        except Exception:
            errors["payment_at"] = "Invalid datetime format. Use ISO8601 e.g. 2025-07-20T00:00:00+00:01"

    if errors:
        return {"status": "error", "errors": errors}

    # -------------------------
    # 🔹 Idempotency check
    # -------------------------
    existing = None
    if payload.get("number"):
        existing = frappe.db.get_value("Donation Payment", {"number": payload.get("number")}, "name")
    if not existing and payload.get("hash"):
        existing = frappe.db.get_value("Donation Payment", {"hash": payload.get("hash")}, "name")

    if existing:
        doc = frappe.get_doc("Donation Payment", existing)
        return {"status": "exists", "payment": doc.as_dict()}

    # -------------------------
    # 🔹 Try linking to Donation
    # -------------------------
    donation_name = None
    if payload.get("donation_hash"):
        res = frappe.get_all("Donation", filters={"hash": payload.get("donation_hash")}, fields=["name"], limit=1)
        if res:
            donation_name = res[0].name
    elif payload.get("donation_number"):
        res = frappe.get_all("Donation", filters={"donation_number": payload.get("donation_number")}, fields=["name"], limit=1)
        if res:
            donation_name = res[0].name

    # -------------------------
    # 🔹 Create Donation Payment
    # -------------------------
    payment_doc = frappe.get_doc({
        "doctype": "Donation Payment",
        "hash": payload.get("hash"),
        "type": payload.get("type"),
        "amount": float(payload.get("amount")) if payload.get("amount") else 0,
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



import frappe
import json
import re
from frappe.utils import validate_phone_number

def _req():
    """Helper: parse JSON body or form dict"""
    try:
        if frappe.request.data:
            return json.loads(frappe.request.data)
    except:
        pass
    return frappe.form_dict

def parse_phone(phone):
    if isinstance(phone, dict):
        # maybe the number is in a key inside the dict
        phone = phone.get("number") or phone.get("contact_no") or ""
    if phone:
        return str(phone).replace("-", " ").strip()
    return ""

# -----------------------------
# CREATE
# -----------------------------

#4d9cee910c562c1
@frappe.whitelist()
def create_association():
    require_login()

    data = _req()

    required = ["association_name", "email", "contact_no", "iban_no"]
    for f in required:
        if not data.get(f):
            frappe.throw(f"'{f}' is required.")

    # Email validation
    if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", data.get("email")):
        frappe.throw("Invalid email format.")

    # Normalize phone
    data["contact_no"] = parse_phone(data.get("contact_no"))

    # Check if association exists by email
    assoc_name = frappe.db.get_value(
        "Association Information",
        {"email": data.get("email")},
        "name"
    )

    if assoc_name:
        assoc_doc = frappe.get_doc("Association Information", assoc_name)
    else:
        assoc_doc = frappe.get_doc({
            "doctype": "Association Information",
            "association_name": data.get("association_name"),
            "association_address": data.get("association_address"),
            "email": data.get("email"),
            "contact_no": data.get("contact_no"),
        })
        assoc_doc.insert(ignore_permissions=True)

    # Bank details
    iban_doc_name = frappe.db.get_value(
        "Bank Details",
        {"iban_no": data.get("iban_no")},
        "name"
    )

    if iban_doc_name:
        iban_doc = frappe.get_doc("Bank Details", iban_doc_name)
    else:
        iban_doc = frappe.get_doc({
            "doctype": "Bank Details",
            "iban_no": data.get("iban_no"),
            "bank_name": data.get("bank_name"),
            "account_title": data.get("account_title"),
            "link_field": assoc_doc.name,
        })
        iban_doc.insert(ignore_permissions=True)

    assoc_doc.bank_details = iban_doc.name
    assoc_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "association": assoc_doc.as_dict(),
        "bank_details": iban_doc.as_dict(),
    }

# -----------------------------
# READ
# -----------------------------
# -----------------------------
# GET ALL ASSOCIATIONS
# -----------------------------
@frappe.whitelist()
def get_all_associations():
    """
    Fetch all associations with their linked bank details.
    """
    require_login()
    associations = frappe.get_all(
        "Association Information",
        fields=["name", "association_name", "association_address", "email", "contact_no", "bank_details"],
        order_by="modified desc"
    )

    result = []
    for assoc in associations:
        assoc_doc = frappe.get_doc("Association Information", assoc["name"])
        bank_doc = None
        if assoc_doc.bank_details:
            bank_doc = frappe.get_doc("Bank Details", assoc_doc.bank_details)
        result.append({
            "association": assoc_doc.as_dict(),
            "bank_details": bank_doc.as_dict() if bank_doc else None
        })

    return {
        "status": "success",
        "associations": result
    }

# -----------------------------
# GET SPECIFIC ASSOCIATION
# -----------------------------
@frappe.whitelist()
def get_association(name=None, email=None):

    """
    Get association by name or email.
    """
    require_login()
    if not name and not email:
        frappe.throw("'name' or 'email' is required to fetch the association.")

    filters = {}
    if name:
        filters["name"] = name
    if email:
        filters["email"] = email

    assoc_list = frappe.get_all(
        "Association Information",
        filters=filters,
        fields=["name"],
        limit=1
    )

    if not assoc_list:
        frappe.throw("Association not found.")

    assoc_doc = frappe.get_doc("Association Information", assoc_list[0]["name"])
    bank_doc = None
    if assoc_doc.bank_details:
        bank_doc = frappe.get_doc("Bank Details", assoc_doc.bank_details)

    return {
        "status": "success",
        "association": assoc_doc.as_dict(),
        "bank_details": bank_doc.as_dict() if bank_doc else None
    }


# -----------------------------
# UPDATE
# -----------------------------
@frappe.whitelist()
def update_association():
    """
    Update an existing association.
    Must provide 'name' or 'email' to identify the record.
    """
    require_login()
    data = _req()

    name = data.get("name")
    email = data.get("email")

    if not name and not email:
        frappe.throw("'name' or 'email' is required to update the association.")

    filters = {}
    if name:
        filters["name"] = name
    if email:
        filters["email"] = email

    assoc_list = frappe.get_all("Association Information", filters=filters, fields=["name"], limit=1)
    if not assoc_list:
        frappe.throw("Association not found.")

    assoc_doc = frappe.get_doc("Association Information", assoc_list[0]["name"])

    # Update fields if provided
    for field in ["association_name", "association_address", "email", "contact_no"]:
        if data.get(field):
            if field == "contact_no":
                assoc_doc.contact_no = parse_phone(data.get(field))
            else:
                setattr(assoc_doc, field, data.get(field))

    assoc_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "association": assoc_doc.as_dict()
    }

# -----------------------------
# DELETE
# -----------------------------
@frappe.whitelist()
def delete_association(name=None, email=None):
    """
    Delete an association and its linked bank details safely even with two-way links.
    """
    require_login()
    if not name and not email:
        frappe.throw("'name' or 'email' is required to delete the association.")

    # Find association
    filters = {}
    if name:
        filters["name"] = name
    if email:
        filters["email"] = email

    assoc_list = frappe.get_all("Association Information", filters=filters, fields=["name", "bank_details"], limit=1)
    if not assoc_list:
        frappe.throw("Association not found.")

    assoc_doc = frappe.get_doc("Association Information", assoc_list[0]["name"])

    bank_name = assoc_doc.bank_details
    bank_doc = None

    # If linked bank exists, unlink both sides
    if bank_name:
        bank_doc = frappe.get_doc("Bank Details", bank_name)

        # Unlink child from parent
        bank_doc.link_field = None
        bank_doc.save(ignore_permissions=True)

        # Unlink parent from child
        assoc_doc.bank_details = None
        assoc_doc.save(ignore_permissions=True)

    # Now safely delete both
    assoc_doc.delete(ignore_permissions=True)

    if bank_doc:
        bank_doc.delete(ignore_permissions=True)

    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Association '{assoc_doc.name}' and its linked bank details deleted."
    }



def _req():
    """Parse JSON body or form dict"""
    try:
        if frappe.request.data:
            return json.loads(frappe.request.data)
    except:
        pass
    return frappe.form_dict


def parse_int(val):
    try:
        return int(val)
    except:
        return None


# -----------------------------
# Helpers
# -----------------------------
def validate_person_exists(person_name):
    """Ensure person_name exists in Association Contact Person info"""
    if not frappe.db.exists("Association Contact Person info", person_name):
        frappe.throw(f"Person '{person_name}' does not exist in Association Contact Person info")

def parse_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except:
        frappe.throw(f"Invalid number: {value}")


# -----------------------------
# CREATE
# -----------------------------
@frappe.whitelist()
def create_animal():

    require_login()
    data = _req()

    # Required: person_name
    if not data.get("person_name"):
        frappe.throw("'person_name' is required")

    validate_person_exists(data.get("person_name"))

    # Required: animal_type
    if not data.get("animal_type"):
        frappe.throw("'animal_type' is required")

    animal_type = data.get("animal_type")
    if animal_type not in ("Dog", "Cat"):
        frappe.throw("'animal_type' must be 'Dog' or 'Cat'")

    # Build data
    docdata = {
        "doctype": "Animal Information",
        "animal_type": animal_type,
        "person_name": data.get("person_name"),
    }

    # Validate / Restrict wrong fields
    if animal_type == "Dog":
        docdata["adult_dogs"] = parse_int(data.get("adult_dogs"))
        docdata["puppies"] = parse_int(data.get("puppies"))
        docdata["senior_sick_dogs"] = parse_int(data.get("senior_sick_dogs"))

        # Restrict Cat fields
        if any([
            data.get("adult_cats"),
            data.get("kittens"),
            data.get("senior_sick_cats")
        ]):
            frappe.throw("You cannot submit Cat fields when animal_type is 'Dog'")

    if animal_type == "Cat":
        docdata["adult_cats"] = parse_int(data.get("adult_cats"))
        docdata["kittens"] = parse_int(data.get("kittens"))
        docdata["senior_sick_cats"] = parse_int(data.get("senior_sick_cats"))

        # Restrict Dog fields
        if any([
            data.get("adult_dogs"),
            data.get("puppies"),
            data.get("senior_sick_dogs")
        ]):
            frappe.throw("You cannot submit Dog fields when animal_type is 'Cat'")

    # Insert
    doc = frappe.get_doc(docdata)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "animal": doc.as_dict()}


# -----------------------------
# READ (ALL)
# -----------------------------
@frappe.whitelist()
def get_all_animals():
    require_login()

    animals = frappe.get_all(
        "Animal Information",
        fields=["name", "animal_type", "person_name", "modified"],
        order_by="modified desc"
    )

    result = []
    for a in animals:
        doc = frappe.get_doc("Animal Information", a["name"])
        result.append(doc.as_dict())

    return {"status": "success", "animals": result}


# -----------------------------
# READ (ONE)
# -----------------------------
@frappe.whitelist()

def get_animal(name=None, person_name=None):

    """
    Fetch Animal Information by either 'name' (autoname) or 'person_name'.
    """
    require_login()
    if not name and not person_name:
        frappe.throw("Either 'name' or 'person_name' is required.")

    try:
        if name:
            # Fetch by autoname
            doc = frappe.get_doc("Animal Information", name)
        else:
            # Fetch by person_name
            doc = frappe.get_all(
                "Animal Information",
                filters={"person_name": person_name},
                limit_page_length=1
            )
            if not doc:
                frappe.throw("Animal not found for the given person_name.")
            # Get full doc using name
            doc = frappe.get_doc("Animal Information", doc[0].name)

    except frappe.DoesNotExistError:
        frappe.throw("Animal not found.")

    return {"status": "success", "animal": doc.as_dict()}



# UPDATE
# -----------------------------
@frappe.whitelist()
def update_animal():
    require_login()
    data = _req()

    name = data.get("name")
    person_name = data.get("person_name_lookup")  # optional, for lookup by person_name

    if not name and not person_name:
        frappe.throw("Either 'name' or 'person_name_lookup' is required for update.")

    # Fetch the doc
    try:
        if name:
            doc = frappe.get_doc("Animal Information", name)
        else:
            docs = frappe.get_all(
                "Animal Information",
                filters={"person_name": person_name},
                limit_page_length=1
            )
            if not docs:
                frappe.throw("Animal not found for the given person_name.")
            doc = frappe.get_doc("Animal Information", docs[0].name)
    except frappe.DoesNotExistError:
        frappe.throw("Animal not found.")

    current_type = doc.animal_type
    new_type = data.get("animal_type", current_type)

    if new_type not in ("Dog", "Cat"):
        frappe.throw("Invalid animal_type. Allowed: Dog, Cat")

    # Validate person_name if updated
    if data.get("person_name"):
        validate_person_exists(data.get("person_name"))

    # DOG updating validation
    if new_type == "Dog" and any([
        data.get("adult_cats"),
        data.get("kittens"),
        data.get("senior_sick_cats")
    ]):
        frappe.throw("Cannot update Cat fields when animal_type is Dog")

    # CAT updating validation
    if new_type == "Cat" and any([
        data.get("adult_dogs"),
        data.get("puppies"),
        data.get("senior_sick_dogs")
    ]):
        frappe.throw("Cannot update Dog fields when animal_type is Cat")

    # Allowed update fields
    update_fields = [
        "animal_type",
        "adult_dogs", "puppies", "senior_sick_dogs",
        "adult_cats", "kittens", "senior_sick_cats",
        "person_name"
    ]

    for f in update_fields:
        if data.get(f) is not None:
            value = parse_int(data.get(f)) if f in (
                "adult_dogs", "puppies", "senior_sick_dogs",
                "adult_cats", "kittens", "senior_sick_cats"
            ) else data.get(f)
            doc.db_set(f, value, update_modified=True)

    return {"status": "success", "animal": doc.as_dict()}


# -----------------------------
# DELETE
# -----------------------------
@frappe.whitelist()
def delete_animal(name=None, person_name=None):
    require_login()
    if not name and not person_name:
        frappe.throw("Either 'name' or 'person_name' is required for deletion.")

    try:
        if name:
            doc = frappe.get_doc("Animal Information", name)
        else:
            docs = frappe.get_all(
                "Animal Information",
                filters={"person_name": person_name},
                limit_page_length=1
            )
            if not docs:
                frappe.throw("Animal not found for the given person_name.")
            doc = frappe.get_doc("Animal Information", docs[0].name)
    except frappe.DoesNotExistError:
        frappe.throw("Animal not found.")

    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "message": f"Animal '{doc.name}' deleted successfully."}







import frappe
import re

# -----------------------------
# HELPERS
# -----------------------------

def _req():
    """Return JSON body"""
    return frappe.request.get_json() or {}

def validate_email(email):
    """Check email format"""
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        frappe.throw("Invalid email format.")

# -----------------------------
# CREATE
# -----------------------------
@frappe.whitelist()
def create_contact_person():
    require_login()
    data = _req()

    # Required fields
    required_fields = ["person_name", "email", "contact_no"]

    for f in required_fields:
        if not data.get(f):
            frappe.throw(f"'{f}' is required.")

    validate_email(data["email"])

    # Check duplicate email
    if frappe.db.exists("Association Contact Person info", data["email"]):
        frappe.throw("A record with this email already exists.")

    doc = frappe.get_doc({
        "doctype": "Association Contact Person info",
        "person_name": data["person_name"],
        "email": data["email"],  # this becomes name
        "contact_no": data["contact_no"]
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "message": "Created successfully", "data": doc.as_dict()}


# -----------------------------
# READ
# -----------------------------
@frappe.whitelist()
def get_contact_person(email=None):
    require_login()
    if not email:
        frappe.throw("'email' is required")

    validate_email(email)

    doc = frappe.get_doc("Association Contact Person info", email)

    return {"status": "success", "data": doc.as_dict()}



# -----------------------------
# READ ALL
# -----------------------------
@frappe.whitelist()
def get_all_contact_persons():
    """Return all records in Association Contact Person info"""
    require_login()
    records = frappe.get_all(
        "Association Contact Person info",
        fields=["person_name", "email", "contact_no", "modified"],
        order_by="modified desc"
    )

    # Convert to full docs (optional but cleaner)
    result = []
    for r in records:
        doc = frappe.get_doc("Association Contact Person info", r["email"])
        result.append(doc.as_dict())

    return {"status": "success", "count": len(result), "data": result}


# -----------------------------
# UPDATE
# -----------------------------
@frappe.whitelist()

def update_contact_person():
    require_login()
    data = _req()

    if not data.get("email"):
        frappe.throw("'email' is required. This is the unique identifier.")

    email = data.get("email")
    validate_email(email)

    try:
        doc = frappe.get_doc("Association Contact Person info", email)
    except frappe.DoesNotExistError:
        frappe.throw("Record not found.")

    allowed_fields = ["person_name", "contact_no"]

    for f in allowed_fields:
        if f in data and data.get(f) is not None:
            doc.db_set(f, data.get(f), update_modified=True)

    return {"status": "success", "message": "Updated successfully", "data": doc.as_dict()}


# -----------------------------
# DELETE
# -----------------------------
@frappe.whitelist()
def delete_contact_person(email=None):
    require_login()
    if not email:
        frappe.throw("'email' is required for deletion.")

    validate_email(email)

    try:
        doc = frappe.get_doc("Association Contact Person info", email)
    except frappe.DoesNotExistError:
        frappe.throw("Record not found.")

    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "message": f"Record '{email}' deleted successfully."}





def parse_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except:
        frappe.throw(f"Invalid number: {value}")

def validate_contact_person(name):
    """Ensure linked Contact Person exists"""
    if name and not frappe.db.exists("Association Contact Person info", name):
        frappe.throw(f"Contact person '{name}' does not exist.")




# -----------------------------
# CREATE
# -----------------------------
@frappe.whitelist()
def create_shelter():
    require_login()
    data = _req()

    # Required: shelter_name
    if not data.get("shelter_name"):
        frappe.throw("'shelter_name' is required.")

    # Validate contact_person (optional)
    if data.get("contact_person"):
        validate_contact_person(data.get("contact_person"))

    # Required fields
    if data.get("forklift") not in ("0", "1", 0, 1):
        frappe.throw("'forklift' is required and must be 0 or 1.")

    if data.get("truck_access") not in ("Yes", "No"):
        frappe.throw("'truck_access' must be Yes or No.")

    docdata = {
        "doctype": "Animal Shelter Partners",
        "shelter_name": data.get("shelter_name"),
        "country_name": data.get("country_name"),
        "deleivery_address": data.get("deleivery_address"),
        "contact_person": data.get("contact_person"),
        "forklift": int(data.get("forklift")),
        "truck_access": data.get("truck_access"),
    }

    doc = frappe.get_doc(docdata)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "shelter": doc.as_dict()}



# -----------------------------
# READ
# -----------------------------

@frappe.whitelist()
def get_shelter(shelter_name=None):
    require_login()
    if not shelter_name:
        frappe.throw("'shelter_name' is required. Autoname is same as shelter_name.")

    try:
        doc = frappe.get_doc("Animal Shelter Partners", shelter_name)
    except frappe.DoesNotExistError:
        frappe.throw("Shelter not found.")

    return {"status": "success", "shelter": doc.as_dict()}





# -----------------------------
# READ ALL
# -----------------------------

@frappe.whitelist()
def get_all_shelters():
    require_login()
    records = frappe.get_all(
        "Animal Shelter Partners",
        fields=["name", "shelter_name", "country_name", "truck_access", "modified"],
        order_by="modified desc"
    )

    result = []
    for r in records:
        doc = frappe.get_doc("Animal Shelter Partners", r["name"])
        result.append(doc.as_dict())

    return {"status": "success", "shelters": result}



# -----------------------------
# UPADTE
# -----------------------------


@frappe.whitelist()
def update_shelter():
    require_login()
    data = _req()

    if not data.get("shelter_name"):
        frappe.throw("'shelter_name' is required to update.")

    name = data.get("shelter_name")

    try:
        doc = frappe.get_doc("Animal Shelter Partners", name)
    except frappe.DoesNotExistError:
        frappe.throw("Shelter not found.")

    # Validate contact_person if updated
    if data.get("contact_person"):
        validate_contact_person(data.get("contact_person"))

    # Validate truck_access
    if data.get("truck_access") and data.get("truck_access") not in ("Yes", "No"):
        frappe.throw("'truck_access' must be Yes or No.")

    # Validate forklift
    if data.get("forklift") not in (None, "0", "1", 0, 1):
        frappe.throw("'forklift' must be 0 or 1.")

    update_fields = [
        "country_name",
        "deleivery_address",
        "contact_person",
        "forklift",
        "truck_access",
    ]

    for f in update_fields:
        if data.get(f) is not None:
            value = int(data.get(f)) if f == "forklift" else data.get(f)
            doc.db_set(f, value, update_modified=True)

    return {"status": "success", "shelter": doc.as_dict()}




# -----------------------------
# DELETE
# -----------------------------



@frappe.whitelist()
def delete_shelter(shelter_name=None):
    require_login()
    if not shelter_name:
        frappe.throw("'shelter_name' is required for deletion.")

    try:
        doc = frappe.get_doc("Animal Shelter Partners", shelter_name)
    except frappe.DoesNotExistError:
        frappe.throw("Shelter not found.")

    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "message": f"Shelter '{shelter_name}' deleted successfully."}






def parse_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except:
        frappe.throw(f"Invalid currency value: {value}")

def validate_person(person_name):
    """Ensure linked Contact Person exists."""
    if person_name and not frappe.db.exists("Association Contact Person info", person_name):
        frappe.throw(f"Person '{person_name}' does not exist.")


# -----------------------------
# CREATE
# -----------------------------

@frappe.whitelist()
def create_person_demand():
    require_login()
    data = _req()

    # Validate link field
    if data.get("person_details"):
        validate_person(data.get("person_details"))

    docdata = {
        "doctype": "Person Demands",
        "castration_costs": parse_float(data.get("castration_costs")),
        "exemption_notice": data.get("exemption_notice"),
        "notice_issue_date": data.get("notice_issue_date"),
        "animal_shelter_statues": data.get("animal_shelter_statues"),
        "food_requirements_dogs": data.get("food_requirements_dogs"),
        "food_requirements_cats": data.get("food_requirements_cats"),
        "castration_costs_in": parse_float(data.get("castration_costs_in")),
        "person_details": data.get("person_details"),
    }

    doc = frappe.get_doc(docdata)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "record": doc.as_dict()}



# -----------------------------
# READ
# -----------------------------

@frappe.whitelist()
def get_person_demand(id=None):
    require_login()
    if not id:
        frappe.throw("'id' is required (autoincrement ID).")

    try:
        doc = frappe.get_doc("Person Demands", id)
    except frappe.DoesNotExistError:
        frappe.throw("Record not found.")

    return {"status": "success", "record": doc.as_dict()}

# -----------------------------
# READ ALL
# -----------------------------

@frappe.whitelist()
def get_all_person_demands():
    require_login()
    records = frappe.get_all(
        "Person Demands",
        fields=["name", "castration_costs", "person_details", "modified"],
        order_by="modified desc"
    )

    result = []
    for r in records:
        doc = frappe.get_doc("Person Demands", r["name"])
        result.append(doc.as_dict())

    return {"status": "success", "records": result}

# -----------------------------
# UPDATE
# -----------------------------

@frappe.whitelist()
def update_person_demand():
    require_login()
    data = _req()

    if not data.get("id"):
        frappe.throw("'id' is required to update Person Demands record.")

    name = data.get("id")

    try:
        doc = frappe.get_doc("Person Demands", name)
    except frappe.DoesNotExistError:
        frappe.throw("Record not found.")

    # Validate link field
    if data.get("person_details"):
        validate_person(data.get("person_details"))

    update_fields = [
        "castration_costs",
        "exemption_notice",
        "notice_issue_date",
        "animal_shelter_statues",
        "food_requirements_dogs",
        "food_requirements_cats",
        "castration_costs_in",
        "person_details",
    ]

    for f in update_fields:
        if data.get(f) is not None:
            value = parse_float(data.get(f)) if f in ["castration_costs", "castration_costs_in"] else data.get(f)
            doc.db_set(f, value, update_modified=True)

    return {"status": "success", "record": doc.as_dict()}


# -----------------------------
# DELETE
# -----------------------------

@frappe.whitelist()
def delete_person_demand(id=None):
    require_login()
    if not id:
        frappe.throw("'id' is required for deletion.")

    try:
        doc = frappe.get_doc("Person Demands", id)
    except frappe.DoesNotExistError:
        frappe.throw("Record not found.")

    # Safe delete (does not affect linked table)
    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "message": f"Person Demand '{id}' deleted successfully."}



import frappe

def _req():
    return frappe.local.form_dict

def validate_contact_person(name):
    """Ensure linked Contact Person exists"""
    if name and not frappe.db.exists("Association Contact Person info", name):
        frappe.throw(f"Contact person '{name}' does not exist.")



# -----------------------------
# CREATE
# -----------------------------

@frappe.whitelist()
def create_delivery_info():
    require_login()
    data = _req()

    # Required validation for select field
    if data.get("deleivery_type") not in ("Own Purchase", "Donated From Homie"):
        frappe.throw("'deleivery_type' must be 'Own Purchase' or 'Donated From Homie'.")

    # Validate contact person (optional field)
    if data.get("contacted_person"):
        validate_contact_person(data.get("contacted_person"))

    docdata = {
        "doctype": "Deleivery Informations",
        "date": data.get("date"),
        "no_of_pallets": frappe.utils.cint(data.get("no_of_pallets")) if data.get("no_of_pallets") else None,
        "deleivery_type": data.get("deleivery_type"),
        "no_of_kilogram": float(data.get("no_of_kilogram")) if data.get("no_of_kilogram") else None,
        "deleivery_date": data.get("deleivery_date"),
        "arrival_proof": data.get("arrival_proof"),
        "deleivery_note": data.get("deleivery_note"),
        "contacted_person": data.get("contacted_person"),
    }

    doc = frappe.get_doc(docdata)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "delivery_info": doc.as_dict()}


# -----------------------------
# READ
# -----------------------------

@frappe.whitelist()
def get_delivery_info(name=None):
    require_login()
    if not name:
        frappe.throw("'name' is required. This is the autoincrement ID.")

    try:
        doc = frappe.get_doc("Deleivery Informations", name)
    except frappe.DoesNotExistError:
        frappe.throw("Delivery info not found.")

    return {"status": "success", "delivery_info": doc.as_dict()}

# -----------------------------
# READ ALL
# -----------------------------


@frappe.whitelist()
def get_all_delivery_info():
    require_login()
    records = frappe.get_all(
        "Deleivery Informations",
        fields=["name", "deleivery_type", "deleivery_date", "modified"],
        order_by="modified desc"
    )

    result = []
    for r in records:
        doc = frappe.get_doc("Deleivery Informations", r["name"])
        result.append(doc.as_dict())

    return {"status": "success", "delivery_info": result}

# -----------------------------
# UPDATE
# -----------------------------


@frappe.whitelist()
def update_delivery_info():
    require_login()
    data = _req()

    if not data.get("name"):
        frappe.throw("'name' is required to update.")

    name = data.get("name")

    try:
        doc = frappe.get_doc("Deleivery Informations", name)
    except frappe.DoesNotExistError:
        frappe.throw("Delivery info not found.")

    if data.get("contacted_person"):
        validate_contact_person(data.get("contacted_person"))

    if data.get("deleivery_type") and data.get("deleivery_type") not in (
        "Own Purchase", "Donated From Homie"
    ):
        frappe.throw("'deleivery_type' must be 'Own Purchase' or 'Donated From Homie'.")

    update_fields = [
        "date",
        "no_of_pallets",
        "deleivery_type",
        "no_of_kilogram",
        "deleivery_date",
        "arrival_proof",
        "deleivery_note",
        "contacted_person",
    ]

    for f in update_fields:
        if data.get(f) is not None:
            value = int(data.get(f)) if f == "no_of_pallets" else (
                float(data.get(f)) if f == "no_of_kilogram" else data.get(f)
            )
            doc.db_set(f, value, update_modified=True)

    return {"status": "success", "delivery_info": doc.as_dict()}

# -----------------------------
# DELETE
# -----------------------------
@frappe.whitelist()
def delete_delivery_info(name=None):
    require_login()
    if not name:
        frappe.throw("'name' is required for deletion.")

    try:
        doc = frappe.get_doc("Deleivery Informations", name)
    except frappe.DoesNotExistError:
        frappe.throw("Delivery info not found.")

    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "message": f"Record '{name}' deleted successfully."}











import frappe

def _req():
    """Helper to get JSON request body"""
    return frappe.local.form_dict if frappe.local.form_dict else frappe.request.get_json()


# ---------------------------------------------------------
# 1. CREATE DONATION PRODUCT
# ---------------------------------------------------------
@frappe.whitelist()
def create_donation_product():
    require_login()
    data = _req()

    if not data.get("product_name"):
        frappe.throw("'product_name' is required.")

    docdata = {
        "doctype": "Donation Products",
        "product_name": data.get("product_name"),
        "product_price": float(data.get("product_price")) if data.get("product_price") else 0,
        "product_image": data.get("product_image")
    }

    doc = frappe.get_doc(docdata)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "product": doc.as_dict()
    }


# ---------------------------------------------------------
# 2. READ SINGLE PRODUCT
# ---------------------------------------------------------
@frappe.whitelist()
def get_donation_product(product_name):
    require_login()

    try:
        doc = frappe.get_doc("Donation Products", product_name)
        return doc.as_dict()
    except frappe.DoesNotExistError:
        return {"error": "Product not found", "product_name": product_name}


# ---------------------------------------------------------
# 3. LIST ALL PRODUCTS
# ---------------------------------------------------------
@frappe.whitelist()
def list_donation_products():
    require_login()
    docs = frappe.get_all(
        "Donation Products",
        fields=["*"],
        order_by="creation desc"
    )
    return docs


# ---------------------------------------------------------
# 4. UPDATE DONATION PRODUCT
# ---------------------------------------------------------
@frappe.whitelist()
def update_donation_product():
    require_login()
    data = _req()

    if not data.get("product_name"):
        frappe.throw("'product_name' is required to update record.")

    try:
        doc = frappe.get_doc("Donation Products", data.get("product_name"))
    except frappe.DoesNotExistError:
        return {"error": "Product not found"}

    # Update fields if provided
    for field in ["product_price", "product_image"]:
        if field in data:
            setattr(doc, field, data.get(field))

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "updated",
        "product": doc.as_dict()
    }


# ---------------------------------------------------------
# 5. DELETE PRODUCT
# ---------------------------------------------------------
@frappe.whitelist()
def delete_donation_product(product_name):
    require_login()
    try:
        frappe.delete_doc("Donation Products", product_name, ignore_permissions=True)
        frappe.db.commit()
        return {"status": "deleted", "product_name": product_name}
    except frappe.DoesNotExistError:
        return {"error": "Product not found"}
