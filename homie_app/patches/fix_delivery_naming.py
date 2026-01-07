import frappe

def execute():
    frappe.reload_doctype("Deleivery Informations")

    bad_docs = frappe.db.sql("""
        SELECT name
        FROM `tabDeleivery Informations`
        WHERE name REGEXP '^[0-9]+$'
    """, as_dict=True)

    for d in bad_docs:
        old = str(d.name)
        new = f"DEL-{int(old):06d}"

        if not frappe.db.exists("Deleivery Informations", new):
            frappe.rename_doc(
                "Deleivery Informations",
                old,
                new,
                force=True
            )

    frappe.db.commit()
