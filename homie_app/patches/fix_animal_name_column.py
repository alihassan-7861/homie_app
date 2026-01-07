import frappe

def execute():
    table = "tabAnimal Information"

    col = frappe.db.sql("""
        SELECT DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = %s
        AND COLUMN_NAME = 'name'
    """, table, as_dict=True)

    # Convert INT → VARCHAR safely
    if col and col[0]["DATA_TYPE"] != "varchar":
        frappe.db.sql(f"""
            ALTER TABLE `{table}`
            MODIFY COLUMN `name` VARCHAR(140)
        """)

    frappe.db.commit()
