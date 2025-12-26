# homie_app/patches/add_organization_dashboard_page.py
import frappe

def execute():
    if not frappe.db.exists("Page", "organization-dashboard"):
        frappe.get_doc({
            "doctype": "Page",
            "page_name": "organization-dashboard",
            "title": "Organization Dashboard",
            "module": "Homie App",
            "standard": "Yes"
        }).insert(ignore_permissions=True)
