# import frappe

# def execute():
#     # Create or update workspace for Homie App
#     ws = frappe.get_doc({
#         "doctype": "Workspace",
#         "name": "Homie App",
#         "label": "Homie App",
#         "module": "Homie App",
#         "for_user": "",
#         "public": 1,
#         "is_hidden": 0,
#         "links": [
#             {"link_type": "DocType", "link_to": "Donation", "label": "Donation"},
#             {"link_type": "DocType", "link_to": "Donation Payment", "label": "Donation Payment"},
#             {"link_type": "DocType", "link_to": "Donation Item", "label": "Donation Item"},
#         ],
#     })

#     # If exists, update instead of insert
#     if frappe.db.exists("Workspace", "Homie App"):
#         old = frappe.get_doc("Workspace", "Homie App")
#         old.delete(ignore_permissions=True)

#     ws.insert(ignore_permissions=True)
#     frappe.db.commit()
#     print("✅ Homie App Workspace created with doctypes")
