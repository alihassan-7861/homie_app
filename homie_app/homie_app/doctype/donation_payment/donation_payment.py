# Copyright (c) 2025, Anonymous and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

import re
import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime

class DonationPayment(Document):
    def validate(self):
        errors = {}

        # Required fields
        required_fields = ["hash", "type", "amount", "number", "provider"]
        for field in required_fields:
            if not getattr(self, field, None):
                errors[field] = f"{field} is required"

        # Amount > 0
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Amount must be greater than 0"

        # Type validation
        valid_types = ["deposit", "withdraw", "refund"]
        if self.type and self.type.lower() not in valid_types:
            errors["type"] = f"Invalid type. Must be one of {valid_types}"

        # Provider validation
        valid_providers = ["paypal", "stripe", "bank", "cash"]
        if self.provider and self.provider.lower() not in valid_providers:
            errors["provider"] = f"Invalid provider. Must be one of {valid_providers}"

        # Datetime validation
        if self.payment_at:
            try:
                get_datetime(self.payment_at)
            except Exception:
                errors["payment_at"] = "Invalid datetime format. Use ISO8601 (e.g. 2025-07-20T00:00:00+00:01)"

        if errors:
            msg = "\n".join([f"{k}: {v}" for k, v in errors.items()])
            frappe.throw(f"Validation Error(s):\n{msg}")
