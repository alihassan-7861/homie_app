import frappe

def execute():
    frappe.reload_doctype("Animal Information")

    bad_docs = frappe.db.sql("""
        SELECT name
        FROM `tabAnimal Information`
        WHERE name REGEXP '^[0-9]+$'
    """, as_dict=True)

    for d in bad_docs:
        old = str(d.name)
        new = f"AND-{int(old):05d}"

        if not frappe.db.exists("Animal Information", new):
            frappe.rename_doc(
                "Animal Information",
                old,
                new,
                force=True
            )

    frappe.db.commit()
