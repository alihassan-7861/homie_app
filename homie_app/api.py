# apps/homie_app/homie_app/api.py
import frappe
import json
import re
from frappe import _
from frappe.model.naming import now_datetime


def require_login():
    if frappe.session.user == "Guest":
        frappe.throw("Authentication required. Please login first.", frappe.PermissionError)


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



def validate_email(email):
    """Check email format"""
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        frappe.throw("Invalid email format.")
# ----------------------------- ORGANIZATION DETAILS API'S -----------------------------

#4d9cee910c562c1

# -----------------------------
# CREATE ORGANIZATION
# -----------------------------
@frappe.whitelist()
def create_organization():
    require_login()
    data = _req()

    required = ["organization_name", "organization_email", "organization_contact_no", "iban_no"]
    for f in required:
        if not data.get(f):
            frappe.throw(f"'{f}' is required.")

    # Email validation
    if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", data.get("organization_email")):
        frappe.throw("Invalid email format.")

    # Normalize phone
    data["organization_contact_no"] = parse_phone(data.get("organization_contact_no"))

    # Check if organization exists
    org_name = frappe.db.get_value("Organization Details", {"organization_email": data.get("organization_email")}, "name")
    if org_name:
        org_doc = frappe.get_doc("Organization Details", org_name)
    else:
        org_doc = frappe.get_doc({
            "doctype": "Organization Details",
            "organization_name": data.get("organization_name"),
            "organization_email": data.get("organization_email"),
            "organization_contact_no": data.get("organization_contact_no"),
            "status": data.get("status"),
            "country": data.get("country"),
            "organization_city": data.get("organization_city"),
            "organization_street": data.get("organization_street"),
            "organization_street_number": data.get("organization_street_number"),
            "zip_code": data.get("zip_code"),
            "logo": data.get("logo"),  # added logo
        })
        org_doc.insert(ignore_permissions=True)

    # Bank Details
    iban_doc_name = frappe.db.get_value("Bank Details", {"iban_no": data.get("iban_no")}, "name")
    if iban_doc_name:
        bank_doc = frappe.get_doc("Bank Details", iban_doc_name)
        # Update bank details if provided
        if data.get("bank_name"):
            bank_doc.bank_name = data.get("bank_name")
        if data.get("account_title"):
            bank_doc.account_title = data.get("account_title")
        bank_doc.save(ignore_permissions=True)
    else:
        bank_doc = frappe.get_doc({
            "doctype": "Bank Details",
            "iban_no": data.get("iban_no"),
            "bank_name": data.get("bank_name"),
            "account_title": data.get("account_title"),
            "link_field": org_doc.name,
        })
        bank_doc.insert(ignore_permissions=True)

    # Link bank to organization
    org_doc.bank_details = bank_doc.name
    org_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Organization '{org_doc.organization_name}' created successfully",
        "organization": org_doc.as_dict(),
        "bank_details": bank_doc.as_dict(),
    }


# -----------------------------
# GET ALL ORGANIZATIONS
# -----------------------------
@frappe.whitelist()
def get_all_organizations():
    require_login()
    orgs = frappe.get_all(
        "Organization Details",
        fields=[
            "name", "organization_name", "organization_email", "organization_contact_no",
            "status", "country", "organization_city", "organization_street",
            "organization_street_number", "zip_code", "logo", "bank_details"
        ],
        order_by="modified desc"
    )

    result = []
    for org in orgs:
        org_doc = frappe.get_doc("Organization Details", org["name"])
        bank_doc = frappe.get_doc("Bank Details", org_doc.bank_details) if org_doc.bank_details else None

        result.append({
            "organization": {
                **org_doc.as_dict(),
                "logo_url": frappe.utils.get_url(org_doc.logo) if org_doc.logo else None
            },
            "bank_details": bank_doc.as_dict() if bank_doc else None
        })

    return {"status": "success",
            "count": len(result),
            "data": result
            }


# -----------------------------
# GET SPECIFIC ORGANIZATION
# -----------------------------
@frappe.whitelist()
def get_organization(name=None, email=None, organization_name=None):
    require_login()

    if not any([name, email, organization_name]):
        frappe.throw("Provide 'name', 'email', or 'organization_name' to fetch the organization.")

    if name:
        org_doc = frappe.get_doc("Organization Details", name)
    elif email:
        org_list = frappe.get_all("Organization Details", filters={"organization_email": email}, fields=["name"], limit=1)
        if not org_list:
            frappe.throw(f"Organization not found for email '{email}'")
        org_doc = frappe.get_doc("Organization Details", org_list[0]["name"])
    else:  # organization_name
        org_list = frappe.get_all("Organization Details", filters={"organization_name": organization_name}, fields=["name"], limit=1)
        if not org_list:
            frappe.throw(f"Organization not found for name '{organization_name}'")
        org_doc = frappe.get_doc("Organization Details", org_list[0]["name"])

    bank_doc = frappe.get_doc("Bank Details", org_doc.bank_details) if org_doc.bank_details else None

    return {
        "status": "success",
        "organization": {
            **org_doc.as_dict(),
            "logo_url": frappe.utils.get_url(org_doc.logo) if org_doc.logo else None
        },
        "bank_details": bank_doc.as_dict() if bank_doc else None
    }



# -----------------------------
# UPDATE ORGANIZATION
# -----------------------------
@frappe.whitelist()
def update_organization():
    require_login()
    data = _req()

    name = data.get("name")
    email = data.get("organization_email_lookup")
    org_name = data.get("organization_name_lookup")

    if not any([name, email, org_name]):
        frappe.throw("Provide 'name', 'organization_email_lookup', or 'organization_name_lookup' to update the organization.")

    # Fetch by single identifier
    if name:
        org_doc = frappe.get_doc("Organization Details", name)
    elif email:
        org_list = frappe.get_all("Organization Details", filters={"organization_email": email}, fields=["name"], limit=1)
        if not org_list:
            frappe.throw(f"Organization not found for email '{email}'")
        org_doc = frappe.get_doc("Organization Details", org_list[0]["name"])
    else:
        org_list = frappe.get_all("Organization Details", filters={"organization_name": org_name}, fields=["name"], limit=1)
        if not org_list:
            frappe.throw(f"Organization not found for name '{org_name}'")
        org_doc = frappe.get_doc("Organization Details", org_list[0]["name"])

    updatable_fields = [
        "organization_name", "organization_email", "organization_contact_no",
        "status", "country", "organization_city", "organization_street",
        "organization_street_number", "zip_code", "logo"
    ]

    for field in updatable_fields:
        if data.get(field):
            if field == "organization_contact_no":
                org_doc.organization_contact_no = parse_phone(data.get(field))
            else:
                setattr(org_doc, field, data.get(field))

    if org_doc.bank_details:
        bank_doc = frappe.get_doc("Bank Details", org_doc.bank_details)
        if data.get("iban_no"):
            bank_doc.iban_no = data.get("iban_no")
        if data.get("bank_name"):
            bank_doc.bank_name = data.get("bank_name")
        if data.get("account_title"):
            bank_doc.account_title = data.get("account_title")
        bank_doc.save(ignore_permissions=True)

    org_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Organization '{org_doc.organization_name}' updated successfully",
        "organization": org_doc.as_dict()
    }



# -----------------------------
# DELETE ORGANIZATION
# -----------------------------
@frappe.whitelist()
def delete_organization(name=None, email=None, organization_name=None):
    require_login()

    if not any([name, email, organization_name]):
        frappe.throw("Provide 'name', 'email', or 'organization_name' to delete the organization.")

    # Fetch by single identifier
    if name:
        org_doc = frappe.get_doc("Organization Details", name)
    elif email:
        org_list = frappe.get_all("Organization Details", filters={"organization_email": email}, fields=["name", "bank_details"], limit=1)
        if not org_list:
            frappe.throw(f"Organization not found for email '{email}'")
        org_doc = frappe.get_doc("Organization Details", org_list[0]["name"])
    else:
        org_list = frappe.get_all("Organization Details", filters={"organization_name": organization_name}, fields=["name", "bank_details"], limit=1)
        if not org_list:
            frappe.throw(f"Organization not found for name '{organization_name}'")
        org_doc = frappe.get_doc("Organization Details", org_list[0]["name"])

    bank_doc = frappe.get_doc("Bank Details", org_doc.bank_details) if org_doc.bank_details else None

    if bank_doc:
        bank_doc.link_field = None
        bank_doc.save(ignore_permissions=True)

    org_doc.bank_details = None
    org_doc.save(ignore_permissions=True)
    org_doc.delete(ignore_permissions=True)
    if bank_doc:
        bank_doc.delete(ignore_permissions=True)

    frappe.db.commit()

    return {"status": "success", "message": f"Organization '{org_doc.name}' and its linked bank details deleted."}





# ----------------------------- ANIMAL INFORMATION API'S -----------------------------



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

def fetch_person_details(person_name):
    """Fetch first_name and last_name from person details"""
    if not person_name:
        return {"first_name": "", "last_name": ""}
    doc = frappe.get_doc("Association Contact Person info", person_name)
    return {"first_name": doc.first_name, "last_name": doc.last_name}


# -----------------------------
# CREATE ANIMAL
# -----------------------------
@frappe.whitelist()
def create_animal():
    require_login()
    data = _req()

    # Required fields
    person_name = data.get("person_name")
    if not person_name:
        frappe.throw("'person_name' is required")
    validate_person_exists(person_name)

    animal_type = data.get("animal_type")
    if not animal_type:
        frappe.throw("'animal_type' is required")
    if animal_type not in ("Dog", "Cat"):
        frappe.throw("'animal_type' must be 'Dog' or 'Cat'")

    # Build doc data
    docdata = {
        "doctype": "Animal Information",
        "animal_type": animal_type,
        "person_name": person_name,
    }

    # Set type-specific fields
    if animal_type == "Dog":
        docdata.update({
            "adult_dogs": parse_int(data.get("adult_dogs")),
            "puppies": parse_int(data.get("puppies")),
            "senior_sick_dogs": parse_int(data.get("senior_sick_dogs"))
        })
        if any([data.get("adult_cats"), data.get("kittens"), data.get("senior_sick_cats")]):
            frappe.throw("You cannot submit Cat fields when animal_type is 'Dog'")

    if animal_type == "Cat":
        docdata.update({
            "adult_cats": parse_int(data.get("adult_cats")),
            "kittens": parse_int(data.get("kittens")),
            "senior_sick_cats": parse_int(data.get("senior_sick_cats"))
        })
        if any([data.get("adult_dogs"), data.get("puppies"), data.get("senior_sick_dogs")]):
            frappe.throw("You cannot submit Dog fields when animal_type is 'Cat'")

    # Insert record
    doc = frappe.get_doc(docdata)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    person_info = fetch_person_details(person_name)
    result = doc.as_dict()
    result.update(person_info)

    return {
        "status": "success",
        "message": f"Animal information for '{person_name}' created successfully.",
        "animal": result
    }


# -----------------------------
# READ ALL ANIMALS
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
        person_info = fetch_person_details(doc.person_name)
        doc_dict = doc.as_dict()
        doc_dict.update(person_info)
        result.append(doc_dict)

    return {
        "status": "success",
        "count": len(result),
        "message": "Animal records fetched successfully.",
        "data": result
    }


# -----------------------------
# READ ONE ANIMAL
# -----------------------------
@frappe.whitelist()
def get_animal(name=None, person_name=None, first_name=None, email=None):
    require_login()

    if not any([name, person_name, first_name, email]):
        frappe.throw("Provide at least one identifier: name, person_name, first_name, or email")

    # Determine which identifier to use
    if name:
        doc = frappe.get_doc("Animal Information", name)
    elif person_name:
        docs = frappe.get_all("Animal Information", filters={"person_name": person_name}, limit_page_length=1)
        if not docs:
            frappe.throw(f"Animal not found for person_name '{person_name}'")
        doc = frappe.get_doc("Animal Information", docs[0].name)
    elif first_name:
        person_docs = frappe.get_all("Association Contact Person info", filters={"first_name": first_name}, fields=["name"])
        if not person_docs:
            frappe.throw(f"No person found with first_name '{first_name}'")
        docs = frappe.get_all("Animal Information", filters={"person_name": person_docs[0].name}, limit_page_length=1)
        if not docs:
            frappe.throw(f"Animal not found for first_name '{first_name}'")
        doc = frappe.get_doc("Animal Information", docs[0].name)
    else:  # email
        person_docs = frappe.get_all("Association Contact Person info", filters={"email": email}, fields=["name"])
        if not person_docs:
            frappe.throw(f"No person found with email '{email}'")
        docs = frappe.get_all("Animal Information", filters={"person_name": person_docs[0].name}, limit_page_length=1)
        if not docs:
            frappe.throw(f"Animal not found for email '{email}'")
        doc = frappe.get_doc("Animal Information", docs[0].name)

    person_info = fetch_person_details(doc.person_name)
    doc_dict = doc.as_dict()
    doc_dict.update(person_info)

    return {
        "status": "success",
        "message": f"Animal information fetched successfully for '{doc.person_name}'.",
        "animal": doc_dict
    }



# -----------------------------
# UPDATE ANIMAL
# -----------------------------
@frappe.whitelist()
def update_animal():
    require_login()
    data = _req()

    # Fetch identifier
    name = data.get("name")
    person_name_lookup = data.get("person_name_lookup")
    first_name = data.get("first_name")
    email = data.get("email")

    if not any([name, person_name_lookup, first_name, email]):
        frappe.throw("Provide at least one identifier: name, person_name_lookup, first_name, or email")

    # Determine which identifier to use
    if name:
        doc = frappe.get_doc("Animal Information", name)
    elif person_name_lookup:
        docs = frappe.get_all("Animal Information", filters={"person_name": person_name_lookup}, limit_page_length=1)
        if not docs:
            frappe.throw("Animal not found for the given person_name_lookup")
        doc = frappe.get_doc("Animal Information", docs[0].name)
    elif first_name:
        # Join with person_details table to get person_name
        person_docs = frappe.get_all("Association Contact Person info", filters={"first_name": first_name}, fields=["name"])
        if not person_docs:
            frappe.throw(f"No person found with first_name '{first_name}'")
        docs = frappe.get_all("Animal Information", filters={"person_name": person_docs[0].name}, limit_page_length=1)
        if not docs:
            frappe.throw("Animal not found for the given first_name")
        doc = frappe.get_doc("Animal Information", docs[0].name)
    else:  # email
        person_docs = frappe.get_all("Association Contact Person info", filters={"email": email}, fields=["name"])
        if not person_docs:
            frappe.throw(f"No person found with email '{email}'")
        docs = frappe.get_all("Animal Information", filters={"person_name": person_docs[0].name}, limit_page_length=1)
        if not docs:
            frappe.throw("Animal not found for the given email")
        doc = frappe.get_doc("Animal Information", docs[0].name)

    current_type = doc.animal_type
    new_type = data.get("animal_type", current_type)

    if new_type not in ("Dog", "Cat"):
        frappe.throw("Invalid animal_type. Allowed: Dog, Cat")

    # Validate person_name if updated
    if data.get("person_name"):
        validate_person_exists(data.get("person_name"))

    # Type-specific validation
    if new_type == "Dog" and any([data.get("adult_cats"), data.get("kittens"), data.get("senior_sick_cats")]):
        frappe.throw("Cannot update Cat fields when animal_type is Dog")
    if new_type == "Cat" and any([data.get("adult_dogs"), data.get("puppies"), data.get("senior_sick_dogs")]):
        frappe.throw("Cannot update Dog fields when animal_type is Cat")

    # Update allowed fields
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

    person_info = fetch_person_details(doc.person_name)
    doc_dict = doc.as_dict()
    doc_dict.update(person_info)

    return {
        "status": "success",
        "message": f"Animal information for '{doc.person_name}' updated successfully.",
        "animal": doc_dict
    }



# -----------------------------
# DELETE ANIMAL
# -----------------------------
@frappe.whitelist()
def delete_animal(name=None, person_name=None, first_name=None, email=None):
    require_login()

    if not any([name, person_name, first_name, email]):
        frappe.throw("Provide at least one identifier for deletion: name, person_name, first_name, or email")

    # Determine which identifier to use
    if name:
        doc = frappe.get_doc("Animal Information", name)
    elif person_name:
        docs = frappe.get_all("Animal Information", filters={"person_name": person_name}, limit_page_length=1)
        if not docs:
            frappe.throw(f"Animal not found for person_name '{person_name}'")
        doc = frappe.get_doc("Animal Information", docs[0].name)
    elif first_name:
        person_docs = frappe.get_all("Association Contact Person info", filters={"first_name": first_name}, fields=["name"])
        if not person_docs:
            frappe.throw(f"No person found with first_name '{first_name}'")
        docs = frappe.get_all("Animal Information", filters={"person_name": person_docs[0].name}, limit_page_length=1)
        if not docs:
            frappe.throw(f"Animal not found for first_name '{first_name}'")
        doc = frappe.get_doc("Animal Information", docs[0].name)
    else:  # email
        person_docs = frappe.get_all("Association Contact Person info", filters={"email": email}, fields=["name"])
        if not person_docs:
            frappe.throw(f"No person found with email '{email}'")
        docs = frappe.get_all("Animal Information", filters={"person_name": person_docs[0].name}, limit_page_length=1)
        if not docs:
            frappe.throw(f"Animal not found for email '{email}'")
        doc = frappe.get_doc("Animal Information", docs[0].name)

    doc_name = doc.name
    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Animal information record '{doc_name}' deleted successfully."
    }


# ----------------------------- PERSON DETAILS API'S -----------------------------

# -----------------------------
# CREATE PERSONS
# -----------------------------
@frappe.whitelist()
def create_person():
    require_login()
    data = _req()

    required_fields = ["first_name", "last_name", "email", "contact_no"]
    for f in required_fields:
        if not data.get(f):
            frappe.throw(f"'{f}' is required.")

    validate_email(data["email"])

    if frappe.db.exists("Association Contact Person info", data["email"]):
        frappe.throw(f"A record with email '{data['email']}' already exists.")

    doc = frappe.get_doc({
        "doctype": "Association Contact Person info",
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "email": data["email"],  # unique name
        "contact_no": data["contact_no"],
        "street": data.get("street"),
        "street_number": data.get("street_number"),
        "person_country": data.get("person_country"),
        "person_city": data.get("person_city"),
        "zip_code": data.get("zip_code")
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success",      
            "message": f"Person Details for '{doc.first_name}' created successfully.",
            "data": doc.as_dict()}


# -----------------------------
# READ PERSON
# -----------------------------
@frappe.whitelist()
def get_person(email=None, first_name=None, last_name=None):
    require_login()

    if not any([email, first_name, last_name]):
        frappe.throw("Provide at least one identifier: email, first_name, or last_name")

    if email:
        validate_email(email)
        docs = frappe.get_all("Association Contact Person info", filters={"email": email}, limit_page_length=1)
    elif first_name:
        docs = frappe.get_all("Association Contact Person info", filters={"first_name": first_name}, limit_page_length=1)
    else:
        docs = frappe.get_all("Association Contact Person info", filters={"last_name": last_name}, limit_page_length=1)

    if not docs:
        frappe.throw("Contact person not found")

    doc = frappe.get_doc("Association Contact Person info", docs[0].email)
    return {"status": "success", "data": doc.as_dict()}



# -----------------------------
# READ ALL PERSON
# -----------------------------
@frappe.whitelist()
def get_all_persons():
    require_login()
    records = frappe.get_all(
        "Association Contact Person info",
        fields=["email", "first_name", "last_name", "contact_no", "street", "street_number", "person_country", "person_city", "zip_code", "modified"],
        order_by="modified desc"
    )

    result = [frappe.get_doc("Association Contact Person info", r["email"]).as_dict() for r in records]

    return {"status": "success", "count": len(result), "data": result}


# -----------------------------
# UPDATE PERSON
# -----------------------------
@frappe.whitelist()
def update_person():
    require_login()
    data = _req()

    email_lookup = data.get("email")  # unique identifier
    first_name_lookup = data.get("first_name_lookup")
    last_name_lookup = data.get("last_name_lookup")

    if not any([email_lookup, first_name_lookup, last_name_lookup]):
        frappe.throw("Provide at least one identifier for update: email, first_name_lookup, or last_name_lookup")

    # Fetch record
    if email_lookup:
        validate_email(email_lookup)
        docs = frappe.get_all("Association Contact Person info", filters={"email": email_lookup}, limit_page_length=1)
    elif first_name_lookup:
        docs = frappe.get_all("Association Contact Person info", filters={"first_name": first_name_lookup}, limit_page_length=1)
    else:
        docs = frappe.get_all("Association Contact Person info", filters={"last_name": last_name_lookup}, limit_page_length=1)

    if not docs:
        frappe.throw("Contact person not found")

    doc = frappe.get_doc("Association Contact Person info", docs[0].email)

    allowed_fields = ["first_name", "last_name", "contact_no", "street", "street_number", "person_country", "person_city", "zip_code"]
    for f in allowed_fields:
        if f in data and data.get(f) is not None:
            doc.db_set(f, data.get(f), update_modified=True)

    return {"status": "success", 
            "message": f"Person Details for '{doc.first_name}' updated successfully.",
            "data": doc.as_dict()}


# -----------------------------
# DELETE PERSON
# -----------------------------
@frappe.whitelist()
def delete_person(email=None, first_name=None, last_name=None):
    require_login()

    if not any([email, first_name, last_name]):
        frappe.throw("Provide at least one identifier for deletion: email, first_name, or last_name")

    if email:
        validate_email(email)
        docs = frappe.get_all("Association Contact Person info", filters={"email": email}, limit_page_length=1)
    elif first_name:
        docs = frappe.get_all("Association Contact Person info", filters={"first_name": first_name}, limit_page_length=1)
    else:
        docs = frappe.get_all("Association Contact Person info", filters={"last_name": last_name}, limit_page_length=1)

    if not docs:
        frappe.throw("Contact person not found")

    doc = frappe.get_doc("Association Contact Person info", docs[0].email)
    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "message": f"Contact person '{doc.first_name}' deleted successfully."}



# ----------------------------- ANIMAL SHELTER API'S -----------------------------



def validate_contact_person(name):
    """Ensure linked Contact Person exists"""
    if name and not frappe.db.exists("Association Contact Person info", name):
        frappe.throw(f"Contact person '{name}' does not exist.")




# -----------------------------
# CREATE
# -----------------------------
@frappe.whitelist()
@frappe.whitelist()
def create_shelter():
    require_login()
    data = _req()

    # Required: shelter_name
    if not data.get("shelter_name"):
        frappe.throw("'shelter_name' is required.")

    # Validate forklift
    if data.get("forklift") not in (0, 1, "0", "1", None):
        frappe.throw("'forklift' must be 0 or 1.")

    # Validate truck_access
    if data.get("truck_access") not in ("Yes", "No"):
        frappe.throw("'truck_access' must be 'Yes' or 'No'.")

    docdata = {
        "doctype": "Animal Shelter Partners",
        "shelter_name": data.get("shelter_name"),
        "forklift": int(data.get("forklift", 0)),
        "truck_access": data.get("truck_access", "No"),
        "country": data.get("country"),
        "city": data.get("city"),
        "street": data.get("street"),
        "street_number": data.get("street_number"),
    }

    doc = frappe.get_doc(docdata)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Shelter '{doc.shelter_name}' has been successfully created!",
        "shelter": doc.as_dict()
    }



@frappe.whitelist()
def get_shelter(shelter_name=None, name=None):
    require_login()

    if not any([shelter_name, name]):
        frappe.throw("Provide 'shelter_name' or 'name' to fetch the shelter.")

    filters = {}
    if shelter_name:
        filters["shelter_name"] = shelter_name
    if name:
        filters["name"] = name

    docs = frappe.get_all("Animal Shelter Partners", filters=filters, limit_page_length=1)
    if not docs:
        frappe.throw("Shelter not found with the provided identifier.")

    doc = frappe.get_doc("Animal Shelter Partners", docs[0].name)
    return {
        "status": "success",
        "message": f"Shelter '{doc.shelter_name}' details retrieved successfully!",
        "shelter": doc.as_dict()
    }




# -----------------------------
# READ ALL
# -----------------------------

@frappe.whitelist()
def get_all_shelters():
    require_login()

    records = frappe.get_all(
        "Animal Shelter Partners",
        fields=["name", "shelter_name", "country", "city", "truck_access", "modified"],
        order_by="modified desc"
    )

    result = [frappe.get_doc("Animal Shelter Partners", r["name"]).as_dict() for r in records]

    return {
        "status": "success",
        "message": f"{len(result)} shelters retrieved successfully!",
        "shelters": result
    }

# -----------------------------
# UPADTE
# -----------------------------


@frappe.whitelist()
def update_shelter():
    require_login()
    data = _req()

    if not any([data.get("shelter_name"), data.get("name")]):
        frappe.throw("Provide 'shelter_name' or 'name' to update the shelter.")

    filters = {}
    if data.get("shelter_name"):
        filters["shelter_name"] = data.get("shelter_name")
    if data.get("name"):
        filters["name"] = data.get("name")

    docs = frappe.get_all("Animal Shelter Partners", filters=filters, limit_page_length=1)
    if not docs:
        frappe.throw("Shelter not found.")

    doc = frappe.get_doc("Animal Shelter Partners", docs[0].name)

    # Validate forklift
    if "forklift" in data and data["forklift"] not in (0, 1, "0", "1"):
        frappe.throw("'forklift' must be 0 or 1.")

    # Validate truck_access
    if "truck_access" in data and data["truck_access"] not in ("Yes", "No"):
        frappe.throw("'truck_access' must be 'Yes' or 'No'.")

    update_fields = ["shelter_name", "forklift", "truck_access", "country", "city", "street", "street_number"]

    for f in update_fields:
        if f in data and data[f] is not None:
            value = int(data[f]) if f == "forklift" else data[f]
            doc.db_set(f, value, update_modified=True)

    return {
        "status": "success",
        "message": f"Shelter '{doc.shelter_name}' has been updated successfully!",
        "shelter": doc.as_dict()
    }



# -----------------------------
# DELETE
# -----------------------------



@frappe.whitelist()
def delete_shelter(shelter_name=None, name=None):
    require_login()

    if not any([shelter_name, name]):
        frappe.throw("Provide 'shelter_name' or 'name' to delete the shelter.")

    filters = {}
    if shelter_name:
        filters["shelter_name"] = shelter_name
    if name:
        filters["name"] = name

    docs = frappe.get_all("Animal Shelter Partners", filters=filters, limit_page_length=1)
    if not docs:
        frappe.throw("Shelter not found.")

    doc = frappe.get_doc("Animal Shelter Partners", docs[0].name)
    doc_name = doc.shelter_name
    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Shelter '{doc_name}' has been deleted successfully from the system."
    }







# ----------------------------- PERSON DEMANDS API'S -----------------------------


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

    if data.get("person_details"):
        validate_person(data.get("person_details"))

    doc = frappe.get_doc({
        "doctype": "Person Demands",
        "castration_costs": parse_float(data.get("castration_costs")),
        "exemption_notice": data.get("exemption_notice"),
        "notice_issue_date": data.get("notice_issue_date"),
        "animal_shelter_statues": data.get("animal_shelter_statues"),
        "food_requirements_dogs": data.get("food_requirements_dogs"),
        "food_requirements_cats": data.get("food_requirements_cats"),
        "castration_costs_in": parse_float(data.get("castration_costs_in")),
        "person_details": data.get("person_details"),
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Person demand record '{doc.name}' created successfully.",
        "data": doc.as_dict()
    }



# -----------------------------
# READ
# -----------------------------

@frappe.whitelist()
def get_person_demand(name=None):
    require_login()
    if not name:
        frappe.throw("'name' (DEM-xxxxxx) is required.")

    try:
        doc = frappe.get_doc("Person Demands", name)
    except frappe.DoesNotExistError:
        frappe.throw("Person demand record not found.")

    return {
        "status": "success",
        "message": f"Person demand '{name}' fetched successfully.",
        "data": doc.as_dict()
    }

# -----------------------------
# READ ALL
# -----------------------------

@frappe.whitelist()
def get_all_person_demands():
    require_login()

    records = frappe.get_all(
        "Person Demands",
        fields=["name"],
        order_by="modified desc"
    )

    data = [frappe.get_doc("Person Demands", r.name).as_dict() for r in records]

    return {
        "status": "success",
        "count": len(data),
        "data": data
    }


# -----------------------------
# UPDATE
# -----------------------------

@frappe.whitelist()
def update_person_demand():
    require_login()
    data = _req()

    if not data.get("name"):
        frappe.throw("'name' (DEM-xxxxxx) is required for update.")

    try:
        doc = frappe.get_doc("Person Demands", data.get("name"))
    except frappe.DoesNotExistError:
        frappe.throw("Person demand record not found.")

    if data.get("person_details"):
        validate_person(data.get("person_details"))

    fields = [
        "castration_costs",
        "exemption_notice",
        "notice_issue_date",
        "animal_shelter_statues",
        "food_requirements_dogs",
        "food_requirements_cats",
        "castration_costs_in",
        "person_details",
    ]

    for f in fields:
        if data.get(f) is not None:
            value = parse_float(data.get(f)) if f in ["castration_costs", "castration_costs_in"] else data.get(f)
            doc.db_set(f, value, update_modified=True)

    return {
        "status": "success",
        "message": f"Person demand '{doc.name}' updated successfully.",
        "data": doc.as_dict()
    }


# -----------------------------
# DELETE
# -----------------------------

@frappe.whitelist()
def delete_person_demand(name=None):
    require_login()
    if not name:
        frappe.throw("'name' (DEM-xxxxxx) is required for deletion.")

    try:
        doc = frappe.get_doc("Person Demands", name)
    except frappe.DoesNotExistError:
        frappe.throw("Person demand record not found.")

    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Person demand record '{name}' deleted successfully."
    }




# -----------------------------Deleivery Information API's  -----------------------------



# -----------------------------
# HELPERS
# -----------------------------

def _req():
    return frappe.local.form_dict

def validate_contact_person(person_name):
    if person_name and not frappe.db.exists("Association Contact Person info", person_name):
        frappe.throw(f"Contact person '{person_name}' does not exist.")




# -----------------------------
# CREATE
# -----------------------------
@frappe.whitelist()
def create_delivery_info():
    require_login()
    data = _req()

    if data.get("deleivery_type") not in ("Own Purchase", "Donated From Homie"):
        frappe.throw("Delivery type must be either 'Own Purchase' or 'Donated From Homie'.")

    if data.get("person_details"):
        validate_contact_person(data.get("person_details"))

        person = frappe.get_doc("Association Contact Person info", data.get("person_details"))
        first_name = person.first_name
        last_name = person.last_name
    else:
        first_name = last_name = None

    doc = frappe.get_doc({
        "doctype": "Deleivery Informations",
        "order_date": data.get("order_date"),
        "no_of_pallets": frappe.utils.cint(data.get("no_of_pallets")) if data.get("no_of_pallets") else None,
        "deleivery_type": data.get("deleivery_type"),
        "no_of_kilogram": float(data.get("no_of_kilogram")) if data.get("no_of_kilogram") else None,
        "deleivery_date": data.get("deleivery_date"),
        "arrival_proof": data.get("arrival_proof"),
        "deleivery_note": data.get("deleivery_note"),
        "person_details": data.get("person_details"),
        "first_name": first_name,
        "last_name": last_name,
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"🚚 Delivery record '{doc.name}' has been created successfully.",
        "record": doc.as_dict()
    }


# -----------------------------
# READ SINGLE RECORD
# -----------------------------

@frappe.whitelist()
def get_delivery_info(name=None):
    require_login()
    if not name:
        frappe.throw("'name' (DEL-.######) is required.")

    try:
        doc = frappe.get_doc("Deleivery Informations", name)
    except frappe.DoesNotExistError:
        frappe.throw("Delivery record not found.")

    return {
        "status": "success",
        "message": "📦 Delivery record fetched successfully.",
        "record": doc.as_dict()
    }



# -----------------------------
# READ ALL
# -----------------------------

@frappe.whitelist()
def get_all_delivery_info():
    require_login()

    records = frappe.get_all(
        "Deleivery Informations",
        fields=["name"],
        order_by="modified desc"
    )

    result = [frappe.get_doc("Deleivery Informations", r.name).as_dict() for r in records]

    return {
        "status": "success",
        "message": f"📋 {len(result)} delivery records retrieved successfully.",
        "records": result
    }


# -----------------------------
# UPDATE
# -----------------------------

@frappe.whitelist()
def update_delivery_info():
    require_login()
    data = _req()

    if not data.get("name"):
        frappe.throw("'name' is required to update delivery information.")

    try:
        doc = frappe.get_doc("Deleivery Informations", data.get("name"))
    except frappe.DoesNotExistError:
        frappe.throw("Delivery record not found.")

    if data.get("deleivery_type") and data.get("deleivery_type") not in (
        "Own Purchase", "Donated From Homie"
    ):
        frappe.throw("Delivery type must be 'Own Purchase' or 'Donated From Homie'.")

    if data.get("person_details"):
        validate_contact_person(data.get("person_details"))
        person = frappe.get_doc("Association Contact Person info", data.get("person_details"))
        doc.first_name = person.first_name
        doc.last_name = person.last_name

    update_fields = [
        "order_date",
        "no_of_pallets",
        "deleivery_type",
        "no_of_kilogram",
        "deleivery_date",
        "arrival_proof",
        "deleivery_note",
        "person_details",
    ]

    for f in update_fields:
        if data.get(f) is not None:
            value = (
                frappe.utils.cint(data.get(f)) if f == "no_of_pallets"
                else float(data.get(f)) if f == "no_of_kilogram"
                else data.get(f)
            )
            doc.db_set(f, value, update_modified=True)

    return {
        "status": "success",
        "message": f"✅ Delivery record '{doc.name}' updated successfully.",
        "record": doc.as_dict()
    }


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
        frappe.throw("Delivery record not found.")

    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"🗑️ Delivery record '{name}' has been deleted successfully."
    }









# -----------------------------
# HELPERS
# -----------------------------


def _req():
    return frappe.request.get_json() or {}

def parse_price(value):
    if value in (None, ""):
        frappe.throw("'product_price' is required.")
    try:
        return float(value)
    except:
        frappe.throw("Invalid price value.")






# -----------------------------
# CREATE PRODUCT
# -----------------------------


@frappe.whitelist()
def create_product():
    require_login()
    data = _req()

    required_fields = ["product_name", "product_status", "product_price"]
    for f in required_fields:
        if not data.get(f):
            frappe.throw(f"'{f}' is required.")

    if data.get("product_status") not in ("Instock", "Out of stock"):
        frappe.throw("Product status must be 'Instock' or 'Out of stock'.")

    if data.get("product_category") and data.get("product_category") not in ("Cat", "Dog"):
        frappe.throw("Product category must be 'Cat' or 'Dog'.")

    if data.get("type") and data.get("type") not in ("Food", "Money"):
        frappe.throw("Type must be 'Food' or 'Money'.")

    doc = frappe.get_doc({
        "doctype": "Product Details",
        "product_name": data.get("product_name"),
        "product_description": data.get("product_description"),
        "product_description_2": data.get("product_description_2"),
        "product_status": data.get("product_status"),
        "product_image_mobile": data.get("product_image_mobile"),
        "product_image_desktop": data.get("product_image_desktop"),
        "product_price": parse_price(data.get("product_price")),
        "product_category": data.get("product_category"),
        "type": data.get("type"),
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"🛍️ Product '{doc.product_name}' has been created successfully.",
        "product": doc.as_dict()
    }



# -----------------------------
# READ PRODUCT
# -----------------------------


@frappe.whitelist()
def get_product(name=None, product_name=None):
    require_login()

    if not name and not product_name:
        frappe.throw("Provide 'name' or 'product_name' to fetch product.")

    filters = {}
    if name:
        filters["name"] = name
    if product_name:
        filters["product_name"] = product_name

    products = frappe.get_all("Product Details", filters=filters, limit=1)
    if not products:
        frappe.throw("Product not found.")

    doc = frappe.get_doc("Product Details", products[0].name)

    return {
        "status": "success",
        "message": "📦 Product fetched successfully.",
        "product": doc.as_dict()
    }




# -----------------------------
# READ ALL PRODUCTS
# -----------------------------

@frappe.whitelist()
def get_all_products():
    require_login()

    records = frappe.get_all(
        "Product Details",
        fields=["name"],
        order_by="modified desc"
    )

    result = [frappe.get_doc("Product Details", r.name).as_dict() for r in records]

    return {
        "status": "success",
        "message": f"📋 {len(result)} products retrieved successfully.",
        "products": result
    }




# -----------------------------
# UPDATE PRODUCT
# -----------------------------


@frappe.whitelist()
def update_product():
    require_login()
    data = _req()

    if not data.get("name") and not data.get("product_name"):
        frappe.throw("Provide 'name' or 'product_name' to update product.")

    filters = {}
    if data.get("name"):
        filters["name"] = data.get("name")
    if data.get("product_name"):
        filters["product_name"] = data.get("product_name")

    products = frappe.get_all("Product Details", filters=filters, limit=1)
    if not products:
        frappe.throw("Product not found.")

    doc = frappe.get_doc("Product Details", products[0].name)

    if data.get("product_status") and data.get("product_status") not in ("Instock", "Out of stock"):
        frappe.throw("Product status must be 'Instock' or 'Out of stock'.")

    if data.get("product_category") and data.get("product_category") not in ("Cat", "Dog"):
        frappe.throw("Product category must be 'Cat' or 'Dog'.")

    if data.get("type") and data.get("type") not in ("Food", "Money"):
        frappe.throw("Type must be 'Food' or 'Money'.")

    update_fields = [
        "product_name",
        "product_description",
        "product_description_2",
        "product_status",
        "product_image_mobile",
        "product_image_desktop",
        "product_price",
        "product_category",
        "type",
    ]

    for f in update_fields:
        if data.get(f) is not None:
            value = parse_price(data.get(f)) if f == "product_price" else data.get(f)
            doc.db_set(f, value, update_modified=True)

    return {
        "status": "success",
        "message": f"✅ Product '{doc.product_name}' updated successfully.",
        "product": doc.as_dict()
    }





# -----------------------------
# DELETE PRODUCT
# -----------------------------


@frappe.whitelist()
def delete_product(name=None, product_name=None):
    require_login()

    if not name and not product_name:
        frappe.throw("Provide 'name' or 'product_name' to delete product.")

    filters = {}
    if name:
        filters["name"] = name
    if product_name:
        filters["product_name"] = product_name

    products = frappe.get_all("Product Details", filters=filters, limit=1)
    if not products:
        frappe.throw("Product not found.")

    doc = frappe.get_doc("Product Details", products[0].name)
    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"🗑️ Product '{doc.product_name}' has been deleted successfully."
    }




# ----------------------------- DONATIONS API'S -----------------------------

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.model.document import Document

def require_login():
    if frappe.session.user == "Guest":
        frappe.throw(_("Authentication required"), frappe.PermissionError)

def _req():
    return frappe.local.form_dict

# ---------------------------------------------------
# CREATE DONATION
# ---------------------------------------------------
# ---------------------------------------------------
# CREATE DONATION
# ---------------------------------------------------
@frappe.whitelist()
def create_donation():
    require_login()
    data = _req()

    items_dict = data.get("items")
    if not items_dict:
        frappe.throw(_("Donation items are required"))

    # -----------------------------
    # Validate organization and contact person
    # -----------------------------
    organization = data.get("organization")
    contact_person = data.get("contact_person")

    if organization and not frappe.db.exists("Organization Details", organization):
        frappe.throw(_("Organization '{}' does not exist").format(organization))

    if contact_person and not frappe.db.exists("Association Contact Person info", contact_person):
        frappe.throw(_("Contact person '{}' does not exist").format(contact_person))

    # -----------------------------
    # Validate products
    # -----------------------------
    for key, row in items_dict.items():
        product_id = row.get("product_id") or key
        if not frappe.db.exists("Product Details", product_id):
            frappe.throw(_("Product '{}' does not exist").format(product_id))

    # -----------------------------
    # Create Donation Doc
    # -----------------------------
    doc = frappe.new_doc("Donation")
    doc.donation_number = data.get("donation_number")
    doc.local_number = data.get("local_number")
    doc.is_anonymous = int(data.get("is_anonymous", 0))
    doc.is_subscription = int(data.get("is_subscription", 0))
    doc.donated_at = data.get("donated_at") or now_datetime()
    doc.currency = data.get("currency")
    doc.source = data.get("source")
    doc.ip_address = data.get("ip_address")
    doc.user_agent = data.get("user_agent")
    doc.tracking_facebook_fbc = data.get("tracking_facebook_fbc")
    doc.tracking_facebook_fbp = data.get("tracking_facebook_fbp")
    doc.wishlist = data.get("wishlist")
    doc.local_wishlist = data.get("local_wishlist")
    doc.local_wishlist_title = data.get("local_wishlist_title")
    doc.bacs_paid = data.get("bacs_paid", 0)
    doc.should_reprocessing = int(data.get("should_reprocessing", 0))
    doc.reprocessing_number = data.get("reprocessing_number")
    doc.organization = organization
    doc.contact_person = contact_person

    # -----------------------------
    # Populate read-only fields
    # -----------------------------
    if organization:
        doc.organization_name = frappe.get_value("Organization Details", organization, "organization_name")
    if contact_person:
        contact = frappe.get_doc("Association Contact Person info", contact_person)
        doc.person_first_name = contact.first_name
        doc.person_last_name = contact.last_name
        doc.person_email = contact.email

    # -----------------------------
    # Child Items
    # -----------------------------
    total = 0
    for key, row in items_dict.items():
        product_id = row.get("product_id") or key
        product_price = frappe.get_value("Product Details", product_id, "product_price") or 0
        product_name = frappe.get_value("Product Details", product_id, "product_name") or ""
        qty = int(row.get("quantity", 0))
        line_total = qty * product_price

        doc.append("items", {
            "product": product_id,
            "product_id": product_id,
            "product_name": product_name,
            "quantity": qty,
            "amount": product_price,
            "total": line_total
        })

        total += line_total

    doc.total = total
    doc.insert(ignore_permissions=True)

    return {
        "message": "Donation created successfully",
        "name": doc.name,
        "total": doc.total
    }
# ---------------------------------------------------
# GET SINGLE DONATION
# ---------------------------------------------------
@frappe.whitelist()
def get_donation(name):
    require_login()

    doc = frappe.get_doc("Donation", name)

    # Convert child table to dict keyed by product_id
    items_dict = {row.product_id: {
        "wishlist_item": getattr(row, "wishlist_item", None),
        "product_id": row.product_id,
        "quantity": row.quantity,
        "total": row.total
    } for row in doc.items}

    return {
        "name": doc.name,
        "donation_number": doc.donation_number,
        "local_number": doc.local_number,
        "is_anonymous": doc.is_anonymous,
        "is_subscription": doc.is_subscription,
        "donated_at": doc.donated_at,
        "currency": doc.currency,
        "source": doc.source,
        "organization": doc.organization,
        "organization_name": doc.organization_name,
        "contact_person": doc.contact_person,
        "person_first_name": doc.person_first_name,
        "person_last_name": doc.person_last_name,
        "person_email": doc.person_email,
        "total": doc.total,
        "items": items_dict
    }

# ---------------------------------------------------
# LIST DONATIONS
# ---------------------------------------------------
@frappe.whitelist()
def list_donations():
    require_login()

    return frappe.get_all(
        "Donation",
        fields=[
            "name",
            "donation_number",
            "organization",
            "total",
            "donated_at"
        ],
        order_by="creation desc"
    )


# ---------------------------------------------------
# UPDATE DONATION
# ---------------------------------------------------
@frappe.whitelist()
def update_donation():
    require_login()
    data = _req()

    donation_name = data.get("name")
    if not donation_name:
        frappe.throw(_("Donation name is required"))

    doc = frappe.get_doc("Donation", donation_name)

    # -----------------------------
    # Validate organization and contact person
    # -----------------------------
    organization = data.get("organization")
    contact_person = data.get("contact_person")

    if organization and not frappe.db.exists("Organization Details", organization):
        frappe.throw(_("Organization '{}' does not exist").format(organization))

    if contact_person and not frappe.db.exists("Association Contact Person info", contact_person):
        frappe.throw(_("Contact person '{}' does not exist").format(contact_person))

    # -----------------------------
    # Update parent fields
    # -----------------------------
    doc.is_anonymous = int(data.get("is_anonymous", doc.is_anonymous))
    doc.is_subscription = int(data.get("is_subscription", doc.is_subscription))
    doc.organization = organization or doc.organization
    doc.contact_person = contact_person or doc.contact_person

    # Update read-only fields from links
    if doc.organization:
        doc.organization_name = frappe.get_value("Organization Details", doc.organization, "organization_name")
    if doc.contact_person:
        contact = frappe.get_doc("Association Contact Person info", doc.contact_person)
        doc.person_first_name = contact.first_name
        doc.person_last_name = contact.last_name
        doc.person_email = contact.email

    # -----------------------------
    # Update items if provided
    # -----------------------------
    items_dict = data.get("items")
    if items_dict:
        total = 0
        doc.items = []
        for key, row in items_dict.items():
            product_id = row.get("product_id") or key
            if not product_id or not frappe.db.exists("Product Details", product_id):
                frappe.throw(_("Product '{}' does not exist").format(product_id))

            product_price = frappe.get_value("Product Details", product_id, "product_price") or 0
            product_name = frappe.get_value("Product Details", product_id, "product_name") or ""
            qty = int(row.get("quantity", 0))
            line_total = qty * product_price

            doc.append("items", {
                "product": product_id,
                "product_id": product_id,
                "product_name": product_name,
                "quantity": qty,
                "amount": product_price,
                "total": line_total
            })
            total += line_total
        doc.total = total

    doc.save(ignore_permissions=True)

    return {
        "message": "Donation updated successfully",
        "name": doc.name,
        "total": doc.total
    }

# ---------------------------------------------------
# DELETE DONATION
# ---------------------------------------------------
@frappe.whitelist()
def delete_donation(name):
    require_login()

    if not frappe.db.exists("Donation", name):
        frappe.throw(_("Donation '{}' does not exist").format(name))

    frappe.delete_doc("Donation", name, ignore_permissions=True)
    return {"message": "Donation deleted successfully"}



# homie_app/api.py
import frappe
from frappe import _

def get_organization_stats():
    """
    Return chart-friendly data for Organization status breakdown and counts.

    Format returned must be:
    {
      "labels": ["Active", "Inactive"],
      "datasets": [
         {"name": "Organizations", "values": [active_count, inactive_count]}
      ]
    }
    """
    # counts
    active = frappe.db.count("Organizations", {"status": "Active"})
    inactive = frappe.db.count("Organizations", {"status": "Inactive"})
    total = active + inactive

    # The structure expected by ERPNext chart Data Source = API:
    return {
        "labels": ["Active", "Inactive"],
        "datasets": [
            {"name": "Organizations", "values": [active, inactive]}
        ],
        # optional: you can return extra fields for a custom card if needed
        "meta": {
            "total": total
        }
    }





