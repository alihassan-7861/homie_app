// Copyright (c) 2025, Anonymous and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deleivery Informations', {

    refresh(frm) {
        toggle_delivery_fields(frm);
    },

    deleiver_to(frm) {
        toggle_delivery_fields(frm);
    },

    // ---------------- PERSON DETAILS ----------------
    person_details(frm) {
        if (frm.doc.person_details) {
            frappe.db.get_doc('Person Details', frm.doc.person_details)
                .then(doc => {
                    frm.set_value('first_name', doc.first_name || '');
                    frm.set_value('last_name', doc.last_name || '');
                });
        } else {
            frm.set_value('first_name', '');
            frm.set_value('last_name', '');
        }
    },

    // ---------------- SHELTER DETAILS ----------------
    shleter_details(frm) {
        if (frm.doc.shleter_details) {
            frappe.db.get_doc('Animal Shelters', frm.doc.shleter_details)
                .then(doc => {
                    frm.set_value('shleter_name', doc.shelter_name || doc.name);
                });
        } else {
            frm.set_value('shleter_name', '');
        }
    }
});


// ================= FIELD TOGGLING =================
function toggle_delivery_fields(frm) {
    const deliverTo = frm.doc.deleiver_to;

    // ---------- PERSON ----------
    if (deliverTo === "Person") {
        show_fields(frm, [
            'person_details',
            'first_name',
            'last_name'
        ]);

        hide_fields(frm, [
            'shleter_details',
            'shleter_name'
        ]);

        frm.set_value('shleter_details', null);
        frm.set_value('shleter_name', '');
    }

    // ---------- ANIMAL SHELTER ----------
    else if (deliverTo === "Animal Shelter") {
        show_fields(frm, [
            'shleter_details',
            'shleter_name'
        ]);

        hide_fields(frm, [
            'person_details',
            'first_name',
            'last_name'
        ]);

        frm.set_value('person_details', null);
        frm.set_value('first_name', '');
        frm.set_value('last_name', '');
    }

    // ---------- NOTHING SELECTED ----------
    else {
        hide_fields(frm, [
            'person_details',
            'first_name',
            'last_name',
            'shleter_details',
            'shleter_name'
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



