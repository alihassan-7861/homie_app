// Copyright (c) 2025, Anonymous and contributors
// For license information, please see license.txt

frappe.ui.form.on('Person Demands', {
	person_details: function(frm) {
        if (frm.doc.person_details) {
            frappe.db.get_doc(
                'Association Contact Person info',
                frm.doc.person_details
            ).then(doc => {
                // ✅ MUST match local fieldnames
                frm.set_value('first_name', doc.first_name || '');
                frm.set_value('last_name', doc.last_name || '');
            });
        } else {
            frm.set_value('first_name', '');
            frm.set_value('last_name', '');
        }
    }
});
