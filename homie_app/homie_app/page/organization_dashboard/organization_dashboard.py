import frappe

@frappe.whitelist()
def get_organization_dashboard(organization):
    # 1️⃣ Organization
    org = frappe.get_doc("Organization Details", organization)

    # 2️⃣ Donations (parent)
    donations = frappe.get_all(
        "Donation",
        filters={"organization": organization},
        fields=[
            "name",
            "donated_at",
            "total",
            "donated_to",
            "contact_person",
            "person_first_name",
            "person_last_name",
            "shelter_details",
            "shelter_name",
            "organization_name"
        ],
        order_by="donated_at desc"
    )

    donation_names = [d.name for d in donations]

    # 3️⃣ Donation Items (child table)
    items = []
    if donation_names:
        items = frappe.get_all(
            "Donation Item",
            filters={
                "parent": ["in", donation_names],
                "parenttype": "Donation",
                "parentfield": "items"
            },
            fields=[
                "parent",
                "product",
                "product_name",
                "quantity",
                "amount",
                "total"
            ]
        )

    # 4️⃣ Group items by donation
    items_map = {}
    for i in items:
        items_map.setdefault(i.parent, []).append(i)

    # 5️⃣ Attach items to donations
    for d in donations:
        d["items"] = items_map.get(d.name, [])

    # 6️⃣ KPI totals
    total_donated = sum(d.total or 0 for d in donations)

    # ➕ Donation recipient counts (ADDED)
    donated_to_person = 0
    donated_to_shelter = 0

    for d in donations:
        if d.get("donated_to") == "Person":
            donated_to_person += 1
        elif d.get("donated_to") == "Animal Shelter":
            donated_to_shelter += 1

    # 7️⃣ Deliveries (show all relevant info)
    deliveries = frappe.get_all(
        "Deleivery Informations",
        filters={"organization_detail": organization},
        fields=[
            "name",
            "deleivery_type",
            "organization_detail",
            "organization_name",
            "deleiver_to",
            "person_details",
            "first_name",
            "last_name",
            "shleter_details",
            "shleter_name",
            # "order_date",
            "deleivery_date"
        ],
        order_by="deleivery_date desc"
    )

    # 8️⃣ Format recipient display
    for d in deliveries:
        if d.get("deleiver_to") == "Person" and d.get("person_details"):
            d["recipient_display"] = f"{d.get('first_name') or ''} {d.get('last_name') or ''}".strip()
        elif d.get("deleiver_to") == "Animal Shelter" and d.get("shleter_details"):
            d["recipient_display"] = d.get("shleter_name") or d.get("shleter_details")
        else:
            d["recipient_display"] = ""

    return {
        "organization": {
            "name": org.name,
            "organization_name": org.organization_name,
        },
        "kpis": {
            "total_donated": total_donated,
            "donation_count": len(donations),
            "donation_to_person_count": donated_to_person,
            "donation_to_shelter_count": donated_to_shelter,
            "delivery_count": len(deliveries),
        },
        "donations": donations,
        "deliveries": deliveries
    }
