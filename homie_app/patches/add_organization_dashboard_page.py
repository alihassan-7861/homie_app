import frappe

def execute():
    if not frappe.db.exists("Page", "organization-dashboard"):
        frappe.get_doc({
            "doctype": "Page",
            "name": "organization-dashboard",
            "page_name": "organization-dashboard",
            "module": "Homie App",
            "title": "Organization Dashboard",
            "roles": [],
            "content": None,
            "script": None,
            "style": None,
            "system_page": 0
        }).insert(ignore_permissions=True)
