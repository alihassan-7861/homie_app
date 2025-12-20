# Copyright (c) 2025, Anonymous and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PersonDetails(Document):
    def validate(self):
        self.set_full_name()

    def set_full_name(self):
        parts = [self.first_name, self.last_name]
        self.full_name = " ".join(p for p in parts if p)



