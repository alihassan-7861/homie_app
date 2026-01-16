import frappe
from frappe import _

@frappe.whitelist()
def get_admin_kpis():
    """
    Return KPI totals for workspace dashboard
    """
    total = frappe.db.sql("""SELECT SUM(total) FROM `tabDonation`""")[0][0] or 0

    return {
        "total_products": frappe.db.count("Product Details"),
        "total_donations": frappe.db.count("Donation"),
        "total_amount": total,
        "out_of_stock": frappe.db.count(
            "Product Details",
            {"product_status": "Out of stock"}
        ),
        "active_organizations": frappe.db.count(
            "Organization Details",
            {"status": "Active"}
        )
    }



@frappe.whitelist()
def get_organizations():
    """
    Return latest products data
    """
    return frappe.get_all(
        "Organization Details",
        fields=[
            "logo",
            "organization_name",
            "organization_email",
            "organization_contact_no",
            "status",
            "country",
            "organization_city",
        ],
        order_by="modified desc",
        limit=10
    )


@frappe.whitelist()
def get_products():
    """
    Return latest products data
    """
    return frappe.get_all(
        "Product Details",
        fields=[
            "product_image_desktop",
            "name",
            "product_name",
            "product_price",
            "product_status",
            "product_category",
            "type"
        ],
        order_by="modified desc",
        limit=10
    )




@frappe.whitelist()
def get_persons():
    """
    """
    return frappe.get_all(
        "Person Details",
        fields=[
            "full_name",
            "email",
            "contact_no",
            "person_country",
            "person_city",
            "street"
        ],
        order_by="modified desc",
        limit=10

    )

@frappe.whitelist()
def get_donations():
    return frappe.get_all(
        "Donation",
        fields=["name", "donated_at", "total", "donated_to"],  # <-- updated fields
        order_by="donated_at desc",
        limit=10
    )

