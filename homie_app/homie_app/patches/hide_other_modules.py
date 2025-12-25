import frappe

def execute():
    module_name = "Homie App"

    # Hide all workspaces
    frappe.db.sql("UPDATE `tabWorkspace` SET public = 0")

    # Unhide only your custom workspace
    if frappe.db.exists("Workspace", module_name):
        frappe.db.set_value("Workspace", module_name, "public", 1)
    else:
        ws = frappe.new_doc("Workspace")
        ws.label = module_name
        ws.title = module_name   # required
        ws.module = module_name
        ws.public = 1
        ws.save(ignore_permissions=True)

    frappe.db.commit()
    print(f"✅ Only '{module_name}' workspace is visible, others hidden.")
