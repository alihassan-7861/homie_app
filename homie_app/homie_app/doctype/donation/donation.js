frappe.ui.form.on('Donation Item', {
    product: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        if (!row.product) return;

        // Product ID (autoname)
        frappe.model.set_value(cdt, cdn, 'product_id', row.product);

        // Fetch BOTH name and price
        frappe.db.get_value(
            'Product Details',
            row.product,
            ['product_name', 'product_price']
        ).then(r => {
            if (!r.message) return;

            frappe.model.set_value(
                cdt,
                cdn,
                'product_name',
                r.message.product_name || ''
            );

            frappe.model.set_value(
                cdt,
                cdn,
                'amount',
                r.message.product_price || 0
            );

            let total = (row.quantity || 0) * (r.message.product_price || 0);
            frappe.model.set_value(cdt, cdn, 'total', total);

            update_parent_total(frm);
        });
    },

    quantity: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        let total = (row.quantity || 0) * (row.amount || 0);

        frappe.model.set_value(cdt, cdn, 'total', total);
        update_parent_total(frm);
    }
});




frappe.ui.form.on('Donation', {
    contact_person: function(frm) {
        if (frm.doc.contact_person) {
            frappe.db.get_doc('Association Contact Person info', frm.doc.contact_person)
                .then(doc => {
                    frm.set_value('person_first_name', doc.first_name);
                    frm.set_value('person_last_name', doc.last_name);
                    frm.set_value('person_email', doc.email);
                });
        } else {
            frm.set_value('person_first_name', '');
            frm.set_value('person_last_name', '');
            frm.set_value('person_email', '');
        }
    },

    organization: function(frm) {
        if (frm.doc.organization) {
            frappe.db.get_doc('Organization Details', frm.doc.organization)
                .then(doc => {
                    frm.set_value('organization_name', doc.organization_name);
                });
        } else {
            frm.set_value('organization_name', '');
        }
    }
});


