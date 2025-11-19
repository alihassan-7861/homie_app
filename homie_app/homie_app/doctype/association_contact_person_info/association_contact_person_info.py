# Copyright (c) 2025, Anonymous and contributors
# For license information, please see license.txt
import frappe
import re
# import frappe
from frappe.model.document import Document

class AssociationContactPersoninfo(Document):
	def validate(self):
         if self.email:
            # simple regex check
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', self.email):
                frappe.throw("Invalid email address: {0}".format(self.email))

