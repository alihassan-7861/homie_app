# Copyright (c) 2025, Anonymous and contributors
# For license information, please see license.txt



# donation.py
import frappe
from frappe.model.document import Document

class Donation(Document):
    def validate(self):
        donation_total = 0
        for item in self.items:
            if item.product:
                item.amount = frappe.get_value("Product Details", item.product, "product_price") or 0
            item.total = (item.quantity or 0) * (item.amount or 0)
            donation_total += item.total

        self.total = donation_total
