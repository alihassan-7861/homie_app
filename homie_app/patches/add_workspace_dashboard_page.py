# homie_app/patches/add_workspace_dashboard_page.py

import frappe

def execute():
    page_name = "workspace-dashboard"
    
    if frappe.db.exists("Page", page_name):
        frappe.db.set_value("Page", page_name, "title", "VETO Workspace")
        frappe.db.set_value("Page", page_name, "icon", "octicon octicon-database")
        print("Page already exists. Updated title and icon.")
    else:
        page = frappe.get_doc({
            "doctype": "Page",
            "page_name": page_name,
            "title": "VETO Workspace",
            "icon": "octicon octicon-database",
            "module": "Homie App",
            "roles": [
            {"role": "System Manager"}
        ] # add roles as required
        })
        page.insert(ignore_permissions=True)
        print("Page inserted successfully.")
