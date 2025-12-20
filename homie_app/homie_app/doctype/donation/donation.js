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
            frappe.db.get_doc('Person Details', frm.doc.contact_person)
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




// Copyright (c) 2025, Anonymous and contributors
// For license information, please see license.txt

frappe.ui.form.on('Donation', {

    refresh(frm) {
        toggle_donated_fields(frm);
    },

    donated_to(frm) {
        toggle_donated_fields(frm);
    },

    // ---------------- PERSON DETAILS ----------------
    contact_person(frm) {
        if (frm.doc.contact_person) {
            frappe.db.get_doc('Person Details', frm.doc.contact_person)
                .then(doc => {
                    frm.set_value('person_first_name', doc.first_name || '');
                    frm.set_value('person_last_name', doc.last_name || '');
                    frm.set_value('person_email', doc.email || '');
                });
        } else {
            frm.set_value('person_first_name', '');
            frm.set_value('person_last_name', '');
            frm.set_value('person_email', '');
        }
    },

    // ---------------- SHELTER DETAILS ----------------
    shelter_details(frm) {
        if (frm.doc.shelter_details) {
            frappe.db.get_doc('Animal Shelters', frm.doc.shelter_details)
                .then(doc => {
                    frm.set_value('shelter_name', doc.shelter_name || doc.name);
                });
        } else {
            frm.set_value('shelter_name', '');
        }
    }

});

// ================= FIELD TOGGLING =================
function toggle_donated_fields(frm) {
    const donatedTo = frm.doc.donated_to;

    // ---------- PERSON ----------
    if (donatedTo === "Person") {
        show_fields(frm, [
            'contact_person',
            'person_first_name',
            'person_last_name',
            'person_email'
        ]);

        hide_fields(frm, [
            'shelter_details',
            'shelter_name'
        ]);

        frm.set_value('shelter_details', null);
        frm.set_value('shelter_name', '');
    }

    // ---------- ANIMAL SHELTER ----------
    else if (donatedTo === "Animal Shelter") {
        show_fields(frm, [
            'shelter_details',
            'shelter_name'
        ]);

        hide_fields(frm, [
            'contact_person',
            'person_first_name',
            'person_last_name',
            'person_email'
        ]);

        frm.set_value('contact_person', null);
        frm.set_value('person_first_name', '');
        frm.set_value('person_last_name', '');
        frm.set_value('person_email', '');
    }

    // ---------- NOTHING SELECTED ----------
    else {
        hide_fields(frm, [
            'contact_person',
            'person_first_name',
            'person_last_name',
            'person_email',
            'shelter_details',
            'shelter_name'
        ]);
    }
}

// ================= HELPERS =================
function show_fields(frm, fields) {
    fields.forEach(field => {
        frm.set_df_property(field, 'hidden', 0);
    });
}

function hide_fields(frm, fields) {
    fields.forEach(field => {
        frm.set_df_property(field, 'hidden', 1);
    });
}

