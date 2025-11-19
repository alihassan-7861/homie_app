# Copyright (c) 2025, Anonymous and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

import re
import frappe
from frappe.model.document import Document

class Donation(Document):
    def validate(self):
        # 1. Hash validation
        if not self.hash or not re.fullmatch(r"[A-Za-z0-9]{32,33}", self.hash):
            frappe.throw("Invalid 'hash'. Must be 32 or 33 characters, only numbers and letters.")

        # 2. Donation number validation
        if self.donation_number and not re.fullmatch(r"[A-Za-z0-9\-_]+", self.donation_number):
            frappe.throw("Invalid 'donation_number'. Only letters, numbers, dashes and underscores allowed.")

        # 3. Email validation
        if self.email and not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", self.email):
            frappe.throw("Invalid 'email' format.")

        # 4. Currency validation
        if self.currency and not re.fullmatch(r"[A-Z]{3}", self.currency):
            frappe.throw("Invalid 'currency'. Must be a 3-letter code like USD, EUR, PKR.")

        # 5. First & last name validation
        if self.first_name and not re.fullmatch(r"[A-Za-z]+", self.first_name):
            frappe.throw("Invalid 'first_name'. Only alphabets allowed.")
        if self.last_name and not re.fullmatch(r"[A-Za-z]+", self.last_name):
            frappe.throw("Invalid 'last_name'. Only alphabets allowed.")

        # 6. Child table validation
        for idx, it in enumerate(self.items, start=1):
            if it.quantity is None or it.quantity <= 0:
                frappe.throw(f"Invalid quantity in item {idx}. Must be a positive integer.")
            if it.total is None or it.total <= 0:
                frappe.throw(f"Invalid total in item {idx}. Must be a positive number.")
            if it.wishlist_item and not re.fullmatch(r"[A-Za-z0-9\-]+", it.wishlist_item):
                frappe.throw(f"Invalid wishlist_item in item {idx}. Only letters, numbers, and dashes allowed.")
