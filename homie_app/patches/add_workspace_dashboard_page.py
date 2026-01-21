# homie_app/patches/add_workspace_dashboard_page.py

import frappe

def execute():
    page_name = "workspace-dashboard"

    # If page exists → safe to update even on Cloud
    if frappe.db.exists("Page", page_name):
        frappe.db.set_value("Page", page_name, {
            "title": "VETO Workspace",
            "icon": "octicon octicon-database"
        })
        return

    # Only create page in developer mode
    if not getattr(frappe.conf, "developer_mode", 0):
        frappe.log_error(
            f"Skipped Page creation '{page_name}' (Developer Mode disabled)",
            "Patch Skipped"
        )
        return

    page = frappe.get_doc({
        "doctype": "Page",
        "page_name": page_name,
        "title": "VETO Workspace",
        "icon": "octicon octicon-database",
        "module": "Homie App"
    })

    page.insert(ignore_permissions=True)
