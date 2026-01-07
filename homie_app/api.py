# apps/homie_app/homie_app/api.py
import frappe
import json
import re
from frappe import _, cint
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


def _req():
    return frappe.request.get_json() or {}

def parse_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except:
        frappe.throw(f"Invalid number: {value}")

def validate_person(person_name):
    if person_name and not frappe.db.exists("Person Details", person_name):
        frappe.throw(f"Person '{person_name}' does not exist in Person Details")

def validate_shelter(shelter_name):
    if shelter_name and not frappe.db.exists("Animal Shelters", shelter_name):
        frappe.throw(f"Shelter '{shelter_name}' does not exist")

def fetch_person_details(person_name):
    if not person_name:
        return {"first_name": "", "last_name": ""}
    doc = frappe.get_doc("Person Details", person_name)
    return {"first_name": doc.first_name, "last_name": doc.last_name}


# -----------------------------
# CREATE ANIMAL
# -----------------------------
@frappe.whitelist()
def create_animal():
    require_login()
    data = _req()

    source = data.get("source")
    animal_type = data.get("animal_type")

    if source not in ("Person", "Animal Shelter"):
        frappe.throw("Source must be 'Person' or 'Animal Shelter'")

    if animal_type not in ("Dog", "Cat"):
        frappe.throw("Animal Type must be 'Dog' or 'Cat'")

    docdata = {
        "doctype": "Animal Information",
        "source": source,
        "animal_type": animal_type
    }

    # -------------------- SOURCE TOGGLE --------------------
    if source == "Person":
        person = data.get("person_details")
        if not person:
            frappe.throw("Person Details is required")

        validate_person(person)
        p = frappe.get_doc("Person Details", person)

        docdata.update({
            "person_details": person,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "shelter_detail": None,
            "shelter_name": ""
        })

    else:
        shelter = data.get("shelter_detail")
        if not shelter:
            frappe.throw("Shelter Detail is required")

        validate_shelter(shelter)
        s = frappe.get_doc("Animal Shelters", shelter)

        docdata.update({
            "shelter_detail": shelter,
            "shelter_name": s.shelter_name,
            "person_details": None,
            "first_name": "",
            "last_name": ""
        })

    # -------------------- ANIMAL TYPE --------------------
    if animal_type == "Dog":
        docdata.update({
            "adult_dogs": parse_int(data.get("adult_dogs")),
            "puppies": parse_int(data.get("puppies")),
            "senior_sick_dogs": parse_int(data.get("senior_sick_dogs")),
            "adult_cats": None,
            "kittens": None,
            "senior_sick_cats": None
        })
    else:
        docdata.update({
            "adult_cats": parse_int(data.get("adult_cats")),
            "kittens": parse_int(data.get("kittens")),
            "senior_sick_cats": parse_int(data.get("senior_sick_cats")),
            "adult_dogs": None,
            "puppies": None,
            "senior_sick_dogs": None
        })

    doc = frappe.get_doc(docdata)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    display = f"{doc.first_name} {doc.last_name}".strip() or doc.shelter_name

    return {
        "status": "success",
        "message": f"🐾 Animal information for '{display}' created successfully.",
        "animal": doc.as_dict()
    }


# -----------------------------
# READ ALL ANIMALS
# -----------------------------
@frappe.whitelist()
def get_all_animals():
    require_login()

    animals = frappe.get_all(
        "Animal Information",
        fields=[
            "name", "animal_type", "source",
            "person_details", "first_name", "last_name",
            "shelter_detail", "shelter_name", "modified"
        ],
        order_by="modified desc"
    )

    for a in animals:
        a["display_name"] = a["first_name"] + " " + a["last_name"] if a["source"] == "Person" else a["shelter_name"]

    return {
        "status": "success",
        "count": len(animals),
        "message": "Animal records fetched successfully.",
        "data": animals
    }


# -----------------------------
# READ SINGLE ANIMAL
# -----------------------------
@frappe.whitelist()
def get_animal(name=None, person_details=None, shelter_detail=None):
    require_login()
    if not any([name, person_details, shelter_detail]):
        frappe.throw("Provide at least one identifier: name, person_details, or shelter_detail")

    if name:
        if not frappe.db.exists("Animal Information", name):
            frappe.throw(f"Animal record '{name}' not found")
        doc = frappe.get_doc("Animal Information", name)
    elif person_details:
        docs = frappe.get_all("Animal Information", filters={"person_details": person_details}, limit_page_length=1)
        if not docs:
            frappe.throw(f"No animal record found for the given person_details")
        doc = frappe.get_doc("Animal Information", docs[0].name)
    else:
        docs = frappe.get_all("Animal Information", filters={"shelter_detail": shelter_detail}, limit_page_length=1)
        if not docs:
            frappe.throw(f"No animal record found for the given shelter_detail")
        doc = frappe.get_doc("Animal Information", docs[0].name)

    display_name = doc.first_name + " " + doc.last_name if doc.source == "Person" else doc.shelter_name

    return {
        "status": "success",
        "message": f"Animal information fetched successfully for '{display_name}'.",
        "animal": doc.as_dict()
    }


# -----------------------------
# UPDATE ANIMAL
# -----------------------------
@frappe.whitelist()
def update_animal():
    require_login()
    data = _req()

    name = data.get("name")
    if not name:
        frappe.throw("Animal record name is required")

    doc = frappe.get_doc("Animal Information", name)

    source = data.get("source", doc.source)
    animal_type = data.get("animal_type", doc.animal_type)

    if source not in ("Person", "Animal Shelter"):
        frappe.throw("Invalid source value")

    if animal_type not in ("Dog", "Cat"):
        frappe.throw("Invalid animal type")

    doc.db_set("source", source)
    doc.db_set("animal_type", animal_type)

    # -------------------- SOURCE TOGGLE --------------------
    if source == "Person":
        person = data.get("person_details", doc.person_details)
        validate_person(person)
        p = frappe.get_doc("Person Details", person)

        doc.db_set("person_details", person)
        doc.db_set("first_name", p.first_name)
        doc.db_set("last_name", p.last_name)
        doc.db_set("shelter_detail", None)
        doc.db_set("shelter_name", "")

    else:
        shelter = data.get("shelter_detail", doc.shelter_detail)
        validate_shelter(shelter)
        s = frappe.get_doc("Animal Shelters", shelter)

        doc.db_set("shelter_detail", shelter)
        doc.db_set("shelter_name", s.shelter_name)
        doc.db_set("person_details", None)
        doc.db_set("first_name", "")
        doc.db_set("last_name", "")

    # -------------------- ANIMAL TYPE --------------------
    if animal_type == "Dog":
        doc.db_set("adult_dogs", parse_int(data.get("adult_dogs")))
        doc.db_set("puppies", parse_int(data.get("puppies")))
        doc.db_set("senior_sick_dogs", parse_int(data.get("senior_sick_dogs")))
        # doc.db_set("adult_cats", None)
        # doc.db_set("kittens", None)
        # doc.db_set("senior_sick_cats", None)

    else:
        doc.db_set("adult_cats", parse_int(data.get("adult_cats")))
        doc.db_set("kittens", parse_int(data.get("kittens")))
        doc.db_set("senior_sick_cats", parse_int(data.get("senior_sick_cats")))
        # doc.db_set("adult_dogs", None)
        # doc.db_set("puppies", None)
        # doc.db_set("senior_sick_dogs", None)

    frappe.db.commit()

    return {
        "status": "success",
        "message": f"✨ Animal information '{doc.name}' updated successfully.",
        "animal": doc.as_dict()
    }



# -----------------------------
# DELETE ANIMAL
# -----------------------------
@frappe.whitelist()
def delete_animal(name=None):
    require_login()
    if not name:
        frappe.throw("Provide 'name' of the animal record to delete")
    if not frappe.db.exists("Animal Information", name):
        frappe.throw(f"Animal record '{name}' not found")
    doc = frappe.get_doc("Animal Information", name)
    doc.delete(ignore_permissions=True)
    frappe.db.commit()
    return {
        "status": "success",
        "message": f"Animal information record '{name}' has been deleted successfully."
    }


# ----------------------------- PERSON DETAILS API'S -----------------------------

# -----------------------------
# CREATE PERSONS
# -----------------------------
@frappe.whitelist()
def create_person():
    require_login()
    data = _req()

    required = ["first_name", "last_name", "email", "contact_no"]
    for f in required:
        if not data.get(f):
            frappe.throw(f"'{f}' is required")

    validate_email(data["email"])

    if frappe.db.exists("Person Details", {"email": data["email"]}):
        frappe.throw(f"Person with email '{data['email']}' already exists")

    doc = frappe.get_doc({
        "doctype": "Person Details",
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "email": data["email"],
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
def get_person(name=None, email=None, first_name=None):
    require_login()

    # -----------------------------
    # VALIDATION: at least one input
    # -----------------------------
    if not any([name, email, first_name]):
        frappe.throw(
            "Please provide at least one identifier: name, email, or first name."
        )

    # -----------------------------
    # FIND PERSON NAME
    # -----------------------------
    person_name = None

    if name:
        if not frappe.db.exists("Person Details", name):
            frappe.throw(f"No person found with name '{name}'.")
        person_name = name

    elif email:
        validate_email(email)
        person_name = frappe.db.get_value(
            "Person Details",
            {"email": email},
            "name"
        )
        if not person_name:
            frappe.throw(f"No person found with email '{email}'.")

    else:  # first_name
        matches = frappe.get_all(
            "Person Details",
            filters={"first_name": first_name},
            fields=["name", "full_name"],
            limit_page_length=2
        )

        if not matches:
            frappe.throw(f"No person found with first name '{first_name}'.")

        if len(matches) > 1:
            frappe.throw(
                f"Multiple persons found with first name '{first_name}'. "
                "Please search using email or name instead."
            )

        person_name = matches[0]["name"]

    # -----------------------------
    # FETCH DOCUMENT
    # -----------------------------
    doc = frappe.get_doc("Person Details", person_name)

    return {
        "status": "success",
        "message": f"Person '{doc.full_name}' fetched successfully.",
        "data": doc.as_dict()
    }




# -----------------------------
# READ ALL PERSON
# -----------------------------
@frappe.whitelist()
def get_all_persons():
    require_login()
    records = frappe.get_all(
        "Person Details",
        fields=["email", "first_name", "last_name", "contact_no", "street", "street_number", "person_country", "person_city", "zip_code", "modified"],
        order_by="modified desc"
    )

    result = [frappe.get_doc("Person Details", r["email"]).as_dict() for r in records]

    return {"status": "success", "count": len(result), "data": result}


# -----------------------------
# UPDATE PERSON
# -----------------------------
@frappe.whitelist()
def update_person():
    require_login()
    data = _req()

    name = data.get("name")
    email = data.get("email")
    first_name = data.get("first_name_lookup")

    # -----------------------------
    # VALIDATION: identifier
    # -----------------------------
    if not any([name, email, first_name]):
        frappe.throw(
            "Please provide at least one identifier: name, email, or first name."
        )

    # -----------------------------
    # RESOLVE PERSON NAME
    # -----------------------------
    person_name = None

    if name:
        if not frappe.db.exists("Person Details", name):
            frappe.throw(f"No person found with name '{name}'.")
        person_name = name

    elif email:
        validate_email(email)
        person_name = frappe.db.get_value(
            "Person Details",
            {"email": email},
            "name"
        )
        if not person_name:
            frappe.throw(f"No person found with email '{email}'.")

    else:  # first_name
        matches = frappe.get_all(
            "Person Details",
            filters={"first_name": first_name},
            fields=["name"],
            limit_page_length=2
        )

        if not matches:
            frappe.throw(f"No person found with first name '{first_name}'.")

        if len(matches) > 1:
            frappe.throw(
                f"Multiple persons found with first name '{first_name}'. "
                "Please use email or name instead."
            )

        person_name = matches[0]["name"]

    # -----------------------------
    # UPDATE DOCUMENT
    # -----------------------------
    doc = frappe.get_doc("Person Details", person_name)

    updatable_fields = [
        "first_name", "last_name", "contact_no",
        "street", "street_number",
        "person_country", "person_city", "zip_code"
    ]

    updated = False
    for field in updatable_fields:
        if field in data:
            doc.set(field, data.get(field))
            updated = True

    if not updated:
        frappe.throw("No valid fields provided to update.")

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Person '{doc.full_name}' updated successfully.",
        "data": doc.as_dict()
    }



# -----------------------------
# DELETE PERSON
# -----------------------------
@frappe.whitelist()
def delete_person(name=None, email=None, first_name=None):
    require_login()

    # -----------------------------
    # VALIDATION: identifier
    # -----------------------------
    if not any([name, email, first_name]):
        frappe.throw(
            "Please provide at least one identifier: name, email, or first name."
        )

    # -----------------------------
    # RESOLVE PERSON NAME
    # -----------------------------
    person_name = None

    if name:
        if not frappe.db.exists("Person Details", name):
            frappe.throw(f"No person found with name '{name}'.")
        person_name = name

    elif email:
        validate_email(email)
        person_name = frappe.db.get_value(
            "Person Details",
            {"email": email},
            "name"
        )
        if not person_name:
            frappe.throw(f"No person found with email '{email}'.")

    else:  # first_name
        matches = frappe.get_all(
            "Person Details",
            filters={"first_name": first_name},
            fields=["name", "full_name"],
            limit_page_length=2
        )

        if not matches:
            frappe.throw(f"No person found with first name '{first_name}'.")

        if len(matches) > 1:
            frappe.throw(
                f"Multiple persons found with first name '{first_name}'. "
                "Please use email or name instead."
            )

        person_name = matches[0]["name"]

    # -----------------------------
    # DELETE DOCUMENT
    # -----------------------------
    doc = frappe.get_doc("Person Details", person_name)
    person_full_name = doc.full_name

    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Person '{person_full_name}' deleted successfully."
    }



# ----------------------------- ANIMAL SHELTER API'S -----------------------------



def validate_contact_person(name):
    """Ensure linked Contact Person exists"""
    if name and not frappe.db.exists("Person Details", name):
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

    # Validate forklift
    if data.get("forklift") not in (0, 1, "0", "1", None):
        frappe.throw("'forklift' must be 0 or 1.")

    # Validate truck_access
    if data.get("truck_access") not in ("Yes", "No"):
        frappe.throw("'truck_access' must be 'Yes' or 'No'.")

    docdata = {
        "doctype": "Animal Shelters",
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

    docs = frappe.get_all("Animal Shelters", filters=filters, limit_page_length=1)
    if not docs:
        frappe.throw("Shelter not found with the provided identifier.")

    doc = frappe.get_doc("Animal Shelters", docs[0].name)
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
        "Animal Shelters",
        fields=["name", "shelter_name", "country", "city", "truck_access", "modified"],
        order_by="modified desc"
    )

    result = [frappe.get_doc("Animal Shelters", r["name"]).as_dict() for r in records]

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

    docs = frappe.get_all("Animal Shelters", filters=filters, limit_page_length=1)
    if not docs:
        frappe.throw("Shelter not found.")

    doc = frappe.get_doc("Animal Shelters", docs[0].name)

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

    docs = frappe.get_all("Animal Shelters", filters=filters, limit_page_length=1)
    if not docs:
        frappe.throw("Shelter not found.")

    doc = frappe.get_doc("Animal Shelters", docs[0].name)
    doc_name = doc.shelter_name
    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"Shelter '{doc_name}' has been deleted successfully from the system."
    }


# ----------------------------- FOOD DEMAND APIs  -----------------------------

import frappe
from frappe import _
from frappe.utils import flt

# -----------------------------
# HELPERS
# -----------------------------
def _req():
    return frappe.request.get_json() or {}

def parse_float(value):
    if value in (None, ""):
        return None
    try:
        return flt(value)
    except Exception:
        frappe.throw(f"Invalid currency value: {value}")

def validate_person(person_name):
    if person_name and not frappe.db.exists("Person Details", person_name):
        frappe.throw(f"Person '{person_name}' does not exist.")

def validate_shelter(shelter_name):
    if shelter_name and not frappe.db.exists("Animal Shelters", shelter_name):
        frappe.throw(f"Shelter '{shelter_name}' does not exist.")

# -----------------------------
# CREATE FOOD DEMAND
# -----------------------------
@frappe.whitelist()
def create_food_demand():
    require_login()
    data = _req()

    # -----------------------------
    # Validate dropdown
    # -----------------------------
    order_by = data.get("order_by")
    if order_by not in ("Person", "Animal Shelters"):
        frappe.throw("'order_by' must be either 'Person' or 'Animal Shelters'.")

    # -----------------------------
    # Conditional required fields
    # -----------------------------
    if order_by == "Person" and not data.get("person_details"):
        frappe.throw("Person Details is required when order_by is 'Person'.")
    if order_by == "Animal Shelters" and not data.get("contacted_animal_shelter"):
        frappe.throw("Animal Shelter is required when order_by is 'Animal Shelters'.")

    # -----------------------------
    # Auto-fill linked data
    # -----------------------------
    person_details = data.get("person_details")
    contacted_animal_shelter = data.get("contacted_animal_shelter")

    # Person info
    if person_details:
        validate_person(person_details)
        person = frappe.get_doc("Person Details", person_details)
        first_name = person.first_name or ""
        last_name = person.last_name or ""
    else:
        first_name = ""
        last_name = ""

    # Shelter info
    if contacted_animal_shelter:
        validate_shelter(contacted_animal_shelter)
        shelter_name = (
            frappe.db.get_value("Animal Shelters", contacted_animal_shelter, "shelter_name")
            or contacted_animal_shelter
        )
    else:
        shelter_name = ""

    # -----------------------------
    # Create document
    # -----------------------------
    doc = frappe.get_doc({
        "doctype": "Food Demands",
        "order_by": order_by,

        "person_details": person_details,
        "first_name": first_name,
        "last_name": last_name,

        "contacted_animal_shelter": contacted_animal_shelter,
        "shelter_name": shelter_name,

        "castration_costs": parse_float(data.get("castration_costs")),
        "castration_costs_in": parse_float(data.get("castration_costs_in")),
        "exemption_notice": data.get("exemption_notice"),
        "notice_issue_date": data.get("notice_issue_date"),
        "food_requirements_dogs": data.get("food_requirements_dogs"),
        "food_requirements_cats": data.get("food_requirements_cats"),
        "animal_shelter_statues": data.get("animal_shelter_statues"),
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"✅ Food demand '{doc.name}' created successfully.",
        "data": doc.as_dict()
    }

# -----------------------------
# READ SINGLE
# -----------------------------
@frappe.whitelist()
def get_food_demand(name=None):
    require_login()
    if not name:
        frappe.throw("'name' (DEM-.######) is required.")

    if not frappe.db.exists("Food Demands", name):
        frappe.throw("Food demand record not found.")

    doc = frappe.get_doc("Food Demands", name)

    return {
        "status": "success",
        "message": f"📦 Food demand '{name}' fetched successfully.",
        "data": doc.as_dict()
    }

# -----------------------------
# READ ALL
# -----------------------------
@frappe.whitelist()
def get_all_food_demands():
    require_login()

    records = frappe.get_all(
        "Food Demands",
        fields=["name"],
        order_by="modified desc"
    )

    data = [frappe.get_doc("Food Demands", r.name).as_dict() for r in records]

    return {
        "status": "success",
        "count": len(data),
        "message": f"📋 {len(data)} food demand records retrieved successfully.",
        "data": data
    }

# -----------------------------
# UPDATE FOOD DEMAND
# -----------------------------
@frappe.whitelist()
def update_food_demand():
    require_login()
    data = _req()

    name = data.get("name")
    if not name:
        frappe.throw("'name' (DEM-.######) is required for update.")

    if not frappe.db.exists("Food Demands", name):
        frappe.throw("Food demand record not found.")

    doc = frappe.get_doc("Food Demands", name)

    # -----------------------------
    # Validate dropdown
    # -----------------------------
    order_by = data.get("order_by") or doc.order_by
    if order_by not in ("Person", "Animal Shelters"):
        frappe.throw("'order_by' must be either 'Person' or 'Animal Shelters'.")

    # -----------------------------
    # Conditional required fields
    # -----------------------------
    if order_by == "Person" and not (data.get("person_details") or doc.person_details):
        frappe.throw("Person Details is required when order_by is 'Person'.")
    if order_by == "Animal Shelters" and not (data.get("contacted_animal_shelter") or doc.contacted_animal_shelter):
        frappe.throw("Animal Shelter is required when order_by is 'Animal Shelters'.")

    # -----------------------------
    # Auto-fill & validate links
    # -----------------------------
    person_details = data.get("person_details") or doc.person_details
    contacted_animal_shelter = data.get("contacted_animal_shelter") or doc.contacted_animal_shelter

    if person_details:
        validate_person(person_details)
        person = frappe.get_doc("Person Details", person_details)
        doc.first_name = person.first_name or ""
        doc.last_name = person.last_name or ""
    else:
        doc.first_name = ""
        doc.last_name = ""

    if contacted_animal_shelter:
        validate_shelter(contacted_animal_shelter)
        doc.shelter_name = (
            frappe.db.get_value("Animal Shelters", contacted_animal_shelter, "shelter_name")
            or contacted_animal_shelter
        )
    else:
        doc.shelter_name = ""

    # -----------------------------
    # Update fields
    # -----------------------------
    update_fields = [
        "order_by",
        "person_details",
        "contacted_animal_shelter",
        "exemption_notice",
        "notice_issue_date",
        "food_requirements_dogs",
        "food_requirements_cats",
        "animal_shelter_statues",
        "castration_costs",
        "castration_costs_in",
    ]

    for field in update_fields:
        if field in data:
            value = parse_float(data[field]) if field in ("castration_costs", "castration_costs_in") else data[field]
            doc.db_set(field, value, update_modified=True)

    return {
        "status": "success",
        "message": f"✅ Food demand '{doc.name}' updated successfully.",
        "data": doc.as_dict()
    }

# -----------------------------
# DELETE FOOD DEMAND
# -----------------------------
@frappe.whitelist()
def delete_food_demand(name=None):
    require_login()
    if not name:
        frappe.throw("'name' (DEM-.######) is required for deletion.")

    if not frappe.db.exists("Food Demands", name):
        frappe.throw("Food demand record not found.")

    frappe.delete_doc("Food Demands", name, ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"🗑️ Food demand '{name}' deleted successfully."
    }


# ----------------------------- Delivery Information API -----------------------------

import frappe
from frappe.utils import cint, flt
from frappe import _

# -----------------------------
# HELPERS
# -----------------------------
def _req():
    """Get request JSON data safely"""
    return frappe.request.get_json() or {}

def validate_person(person_name):
    if person_name and not frappe.db.exists("Person Details", person_name):
        frappe.throw(f"Person '{person_name}' does not exist.")

def validate_shelter(shelter_name):
    if shelter_name and not frappe.db.exists("Animal Shelters", shelter_name):
        frappe.throw(f"Shelter '{shelter_name}' does not exist.")

def validate_organization(org_name):
    if org_name and not frappe.db.exists("Organization Details", org_name):
        frappe.throw(f"Organization '{org_name}' does not exist.")

def update_display_title(deleivery_type, person, organization):
    if deleivery_type == "Own Purchase" and person:
        return f"Purchased by {person}"
    elif deleivery_type == "Donated From Organization" and organization:
        return f"Donated by {organization}"
    else:
        return ""

# -----------------------------
# CREATE DELIVERY INFO
# -----------------------------
@frappe.whitelist()
def create_delivery_info():
    require_login()
    data = _req()

    # -----------------------------
    # Validate dropdowns
    # -----------------------------
    deleivery_type = data.get("deleivery_type")
    deleiver_to = data.get("deleiver_to")

    if deleivery_type not in ("Own Purchase", "Donated From Organization"):
        frappe.throw("Delivery type must be either 'Own Purchase' or 'Donated From Organization'.")
    if deleiver_to and deleiver_to not in ("Person", "Animal Shelter"):
        frappe.throw("Deliver To must be either 'Person' or 'Animal Shelter'.")

    # -----------------------------
    # Conditional required fields
    # -----------------------------
    if deleivery_type == "Own Purchase" and not data.get("person_details"):
        frappe.throw("Person Details is required for 'Own Purchase'.")
    if deleivery_type == "Donated From Organization" and not data.get("organization_detail"):
        frappe.throw("Organization Detail is required for 'Donated From Organization'.")
    if deleiver_to == "Person" and not data.get("person_details"):
        frappe.throw("Person Details is required for Deliver To Person.")
    if deleiver_to == "Animal Shelter" and not data.get("shleter_details"):
        frappe.throw("Shelter Details is required for Deliver To Animal Shelter.")

    # -----------------------------
    # Auto-fill linked fields
    # -----------------------------
    person_details = data.get("person_details")
    shleter_details = data.get("shleter_details")
    organization_detail = data.get("organization_detail")

    # Person info
    if person_details:
        validate_person(person_details)
        person_doc = frappe.get_doc("Person Details", person_details)
        first_name = person_doc.first_name or ""
        last_name = person_doc.last_name or ""
    else:
        first_name = last_name = ""

    # Shelter info
    if shleter_details:
        validate_shelter(shleter_details)
        shleter_name = frappe.db.get_value("Animal Shelters", shleter_details, "shelter_name") or shleter_details
    else:
        shleter_name = ""

    # Organization info
    if organization_detail:
        validate_organization(organization_detail)
        organization_name = frappe.db.get_value("Organization Details", organization_detail, "organization_name") or organization_detail
    else:
        organization_name = ""

    # -----------------------------
    # Insert record
    # -----------------------------
    docdata = {
        "doctype": "Deleivery Informations",
        "deleivery_type": deleivery_type,
        "deleiver_to": deleiver_to,
        "person_details": person_details,
        "first_name": first_name,
        "last_name": last_name,
        "shleter_details": shleter_details,
        "shleter_name": shleter_name,
        "organization_detail": organization_detail,
        "organization_name": organization_name,
        "no_of_pallets": cint(data.get("no_of_pallets")) if data.get("no_of_pallets") else 0,
        "no_of_kilogram": flt(data.get("no_of_kilogram")) if data.get("no_of_kilogram") else 0.0,
        "deleivery_date": data.get("deleivery_date"),
        "arrival_proof": data.get("arrival_proof"),
        "deleivery_note": data.get("deleivery_note"),
        "display_title": update_display_title(deleivery_type, person_details or shleter_details, organization_detail)
    }

    doc = frappe.get_doc(docdata)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"🚚 Delivery record '{doc.name}' created successfully for '{doc.display_title}'.",
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
    if not frappe.db.exists("Deleivery Informations", name):
        frappe.throw("Delivery record not found.")

    doc = frappe.get_doc("Deleivery Informations", name)
    return {
        "status": "success",
        "message": f"📦 Delivery record '{doc.name}' fetched successfully.",
        "record": doc.as_dict()
    }

# -----------------------------
# READ ALL RECORDS
# -----------------------------
@frappe.whitelist()
def get_all_delivery_info():
    require_login()
    records = frappe.get_all("Deleivery Informations", fields=["name"], order_by="modified desc")
    result = [frappe.get_doc("Deleivery Informations", r.name).as_dict() for r in records]

    return {
        "status": "success",
        "message": f"📋 {len(result)} delivery records retrieved successfully.",
        "records": result
    }

# -----------------------------
# UPDATE DELIVERY INFO
# -----------------------------
@frappe.whitelist()
def update_delivery_info():
    require_login()
    data = _req()
    name = data.get("name")

    if not name:
        frappe.throw("'name' is required to update delivery information.")
    if not frappe.db.exists("Deleivery Informations", name):
        frappe.throw("Delivery record not found.")

    doc = frappe.get_doc("Deleivery Informations", name)

    deleivery_type = data.get("deleivery_type") or doc.deleivery_type
    deleiver_to = data.get("deleiver_to") or doc.deleiver_to

    # -----------------------------
    # Validate dropdowns
    # -----------------------------
    if deleivery_type not in ("Own Purchase", "Donated From Organization"):
        frappe.throw("Delivery type must be either 'Own Purchase' or 'Donated From Organization'.")
    if deleiver_to and deleiver_to not in ("Person", "Animal Shelter"):
        frappe.throw("Deliver To must be either 'Person' or 'Animal Shelter'.")

    # -----------------------------
    # Conditional required fields
    # -----------------------------
    if deleivery_type == "Own Purchase" and not (data.get("person_details") or doc.person_details):
        frappe.throw("Person Details is required for 'Own Purchase'.")
    if deleivery_type == "Donated From Organization" and not (data.get("organization_detail") or doc.organization_detail):
        frappe.throw("Organization Detail is required for 'Donated From Organization'.")
    if deleiver_to == "Person" and not (data.get("person_details") or doc.person_details):
        frappe.throw("Person Details is required for Deliver To Person.")
    if deleiver_to == "Animal Shelter" and not (data.get("shleter_details") or doc.shleter_details):
        frappe.throw("Shelter Details is required for Deliver To Animal Shelter.")

    # -----------------------------
    # Validate links and auto-fill
    # -----------------------------
    person_details = data.get("person_details") or doc.person_details
    shleter_details = data.get("shleter_details") or doc.shleter_details
    organization_detail = data.get("organization_detail") or doc.organization_detail

    if person_details:
        validate_person(person_details)
        person_doc = frappe.get_doc("Person Details", person_details)
        doc.first_name = person_doc.first_name or ""
        doc.last_name = person_doc.last_name or ""
    else:
        doc.first_name = ""
        doc.last_name = ""

    if shleter_details:
        validate_shelter(shleter_details)
        doc.shleter_name = frappe.db.get_value("Animal Shelters", shleter_details, "shelter_name") or shleter_details
    else:
        doc.shleter_name = ""

    if organization_detail:
        validate_organization(organization_detail)
        doc.organization_name = frappe.db.get_value("Organization Details", organization_detail, "organization_name") or organization_detail
    else:
        doc.organization_name = ""

    # -----------------------------
    # Update other fields
    # -----------------------------
    fields_to_update = [
        "deleivery_type", "deleiver_to", "person_details", "shleter_details",
        "organization_detail", "no_of_pallets", "no_of_kilogram", "deleivery_date",
        "arrival_proof", "deleivery_note"
    ]
    for f in fields_to_update:
        if f in data:
            value = cint(data[f]) if f == "no_of_pallets" else flt(data[f]) if f == "no_of_kilogram" else data[f]
            doc.db_set(f, value, update_modified=True)

    # Update display title
    doc.db_set("display_title", update_display_title(doc.deleivery_type, doc.person_details or doc.shleter_details, doc.organization_detail), update_modified=True)

    return {
        "status": "success",
        "message": f"✅ Delivery record '{doc.name}' updated successfully.",
        "record": doc.as_dict()
    }

# -----------------------------
# DELETE DELIVERY INFO
# -----------------------------
@frappe.whitelist()
def delete_delivery_info(name=None):
    require_login()
    if not name:
        frappe.throw("'name' is required for deletion.")
    if not frappe.db.exists("Deleivery Informations", name):
        frappe.throw("Delivery record not found.")

    doc = frappe.get_doc("Deleivery Informations", name)
    doc.delete(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": f"🗑️ Delivery record '{name}' has been deleted successfully."
    }



# -----------------------------Product API's  -----------------------------
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
from frappe.utils import now_datetime, flt

# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def require_login():
    if frappe.session.user == "Guest":
        frappe.throw(_("Authentication required"), frappe.PermissionError)

def _req():
    return frappe.request.get_json() or {}

def validate_person(person):
    if person and not frappe.db.exists("Person Details", person):
        frappe.throw(_("Person '{}' does not exist").format(person))

def validate_shelter(shelter):
    if shelter and not frappe.db.exists("Animal Shelters", shelter):
        frappe.throw(_("Shelter '{}' does not exist").format(shelter))

def validate_organization(org):
    if org and not frappe.db.exists("Organization Details", org):
        frappe.throw(_("Organization '{}' does not exist").format(org))

def fetch_person_fields(person):
    doc = frappe.get_doc("Person Details", person)
    return {
        "person_first_name": doc.first_name or "",
        "person_last_name": doc.last_name or "",
        "person_email": doc.email or ""
    }

def fetch_shelter_name(shelter):
    return frappe.db.get_value("Animal Shelters", shelter, "shelter_name") or shelter

def fetch_organization_name(org):
    return frappe.db.get_value("Organization Details", org, "organization_name") or org


# ---------------------------------------------------
# CREATE DONATION
# ---------------------------------------------------
@frappe.whitelist()
def create_donation():
    require_login()
    data = _req()

    # -----------------------------
    # Required & dropdown validation
    # -----------------------------
    donated_to = data.get("donated_to")
    if donated_to not in ("Person", "Animal Shelter"):
        frappe.throw(_("donated_to must be 'Person' or 'Animal Shelter'"))

    items = data.get("items")
    if not items:
        frappe.throw(_("Donation items are required"))

    contact_person = data.get("contact_person")
    shelter_details = data.get("shelter_details")

    if donated_to == "Person" and not contact_person:
        frappe.throw(_("contact_person is required when donated_to is Person"))

    if donated_to == "Animal Shelter" and not shelter_details:
        frappe.throw(_("shelter_details is required when donated_to is Animal Shelter"))

    # -----------------------------
    # Validate links
    # -----------------------------
    validate_person(contact_person)
    validate_shelter(shelter_details)
    validate_organization(data.get("organization"))

    # -----------------------------
    # Create parent document
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
    doc.bacs_paid = flt(data.get("bacs_paid", 0))
    doc.should_reprocessing = int(data.get("should_reprocessing", 0))
    doc.reprocessing_number = data.get("reprocessing_number")
    doc.organization = data.get("organization")
    doc.donated_to = donated_to

    # -----------------------------
    # Auto-fill donor fields
    # -----------------------------
    if donated_to == "Person":
        doc.contact_person = contact_person
        person = fetch_person_fields(contact_person)
        doc.person_first_name = person["person_first_name"]
        doc.person_last_name = person["person_last_name"]
        doc.person_email = person["person_email"]
        doc.shelter_details = None
        doc.shelter_name = ""
    else:
        doc.shelter_details = shelter_details
        doc.shelter_name = fetch_shelter_name(shelter_details)
        doc.contact_person = None
        doc.person_first_name = ""
        doc.person_last_name = ""
        doc.person_email = ""

    if doc.organization:
        doc.organization_name = fetch_organization_name(doc.organization)

    # -----------------------------
    # Child items + price calculation
    # -----------------------------
    total = 0
    for row in items:
        product = row.get("product")
        qty = int(row.get("quantity", 0))

        if not product or not frappe.db.exists("Product Details", product):
            frappe.throw(_("Invalid product in items"))

        if qty <= 0:
            frappe.throw(_("Quantity must be greater than 0"))

        product_doc = frappe.get_doc("Product Details", product)
        amount = flt(product_doc.product_price)
        line_total = qty * amount

        doc.append("items", {
            "product": product,
            "product_id": product,
            "product_name": product_doc.product_name,
            "quantity": qty,
            "amount": amount,
            "total": line_total,
            "wishlist_item": row.get("wishlist_item")
        })

        total += line_total

    doc.total = total
    doc.insert(ignore_permissions=True)

    return {
        "status": "success",
        "message": f"🎉 Donation '{doc.name}' created successfully!",
        "donation": doc.as_dict()
    }


# ---------------------------------------------------
# GET SINGLE DONATION
# ---------------------------------------------------
@frappe.whitelist()
def get_donation(name):
    require_login()

    if not frappe.db.exists("Donation", name):
        frappe.throw(_("Donation '{}' not found").format(name))

    doc = frappe.get_doc("Donation", name)
    return {
        "status": "success",
        "message": f"📦 Donation '{name}' fetched successfully.",
        "donation": doc.as_dict()
    }


# ---------------------------------------------------
# LIST DONATIONS
# ---------------------------------------------------
@frappe.whitelist()
def list_donations():
    require_login()

    data = frappe.get_all(
        "Donation",
        fields=["name", "donated_to", "organization_name", "total", "donated_at"],
        order_by="creation desc"
    )

    return {
        "status": "success",
        "count": len(data),
        "message": "📋 Donations list retrieved successfully.",
        "data": data
    }


# ---------------------------------------------------
# UPDATE DONATION
# ---------------------------------------------------
@frappe.whitelist()
def update_donation():
    require_login()
    data = _req()

    name = data.get("name")
    if not name or not frappe.db.exists("Donation", name):
        frappe.throw(_("Donation not found"))

    doc = frappe.get_doc("Donation", name)

    donated_to = data.get("donated_to", doc.donated_to)
    if donated_to not in ("Person", "Animal Shelter"):
        frappe.throw(_("donated_to must be 'Person' or 'Animal Shelter'"))

    doc.donated_to = donated_to

    # Auto-fill logic
    if donated_to == "Person":
        contact_person = data.get("contact_person")
        if not contact_person:
            frappe.throw(_("contact_person is required"))
        validate_person(contact_person)
        person = fetch_person_fields(contact_person)
        doc.contact_person = contact_person
        doc.person_first_name = person["person_first_name"]
        doc.person_last_name = person["person_last_name"]
        doc.person_email = person["person_email"]
        doc.shelter_details = None
        doc.shelter_name = ""
    else:
        shelter_details = data.get("shelter_details")
        if not shelter_details:
            frappe.throw(_("shelter_details is required"))
        validate_shelter(shelter_details)
        doc.shelter_details = shelter_details
        doc.shelter_name = fetch_shelter_name(shelter_details)
        doc.contact_person = None
        doc.person_first_name = ""
        doc.person_last_name = ""
        doc.person_email = ""

    # Update items if provided
    if data.get("items"):
        doc.items = []
        total = 0
        for row in data["items"]:
            product = row.get("product")
            qty = int(row.get("quantity", 0))

            product_doc = frappe.get_doc("Product Details", product)
            amount = flt(product_doc.product_price)
            line_total = qty * amount

            doc.append("items", {
                "product": product,
                "product_id": product,
                "product_name": product_doc.product_name,
                "quantity": qty,
                "amount": amount,
                "total": line_total,
                "wishlist_item": row.get("wishlist_item")
            })
            total += line_total

        doc.total = total

    doc.save(ignore_permissions=True)

    return {
        "status": "success",
        "message": f"✅ Donation '{doc.name}' updated successfully!",
        "donation": doc.as_dict()
    }


# ---------------------------------------------------
# DELETE DONATION
# ---------------------------------------------------
@frappe.whitelist()
def delete_donation(name):
    require_login()

    if not frappe.db.exists("Donation", name):
        frappe.throw(_("Donation '{}' not found").format(name))

    frappe.delete_doc("Donation", name, ignore_permissions=True)

    return {
        "status": "success",
        "message": f"🗑️ Donation '{name}' deleted successfully."
    }


# # homie_app/api.py
# import frappe
# from frappe import _

# def get_organization_stats():
#     """
#     Return chart-friendly data for Organization status breakdown and counts.

#     Format returned must be:
#     {
#       "labels": ["Active", "Inactive"],
#       "datasets": [
#          {"name": "Organizations", "values": [active_count, inactive_count]}
#       ]
#     }
#     """
#     # counts
#     active = frappe.db.count("Organizations", {"status": "Active"})
#     inactive = frappe.db.count("Organizations", {"status": "Inactive"})
#     total = active + inactive

#     # The structure expected by ERPNext chart Data Source = API:
#     return {
#         "labels": ["Active", "Inactive"],
#         "datasets": [
#             {"name": "Organizations", "values": [active, inactive]}
#         ],
#         # optional: you can return extra fields for a custom card if needed
#         "meta": {
#             "total": total
#         }
#     }





