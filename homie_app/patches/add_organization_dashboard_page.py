import frappe

def execute():
    """
    Patch to add 'Organization Dashboard' page.
    Cloud-safe: Will only insert page if developer_mode is enabled.
    """

    page_name = "organization-dashboard"

    # Check if developer mode is enabled
    if getattr(frappe.conf, "developer_mode", 0):
        # Only create the page if it doesn't exist
        if not frappe.db.exists("Page", page_name):
            frappe.get_doc({
                "doctype": "Page",
                "page_name": page_name,
                "title": "Organization Dashboard",
                "module": "Homie App"
            }).insert(ignore_permissions=True)
            frappe.db.commit()
            frappe.msgprint(f"Page '{page_name}' created successfully.")
        else:
            frappe.msgprint(f"Page '{page_name}' already exists. Skipping creation.")
    else:
        # Developer mode not enabled → skip patch, safe for Cloud
        frappe.log_error(
            f"Skipped creating Page '{page_name}' because Developer Mode is disabled.",
            "Patch Skipped"
        )
