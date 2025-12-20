// Copyright (c) 2025
// For license information, please see license.txt

frappe.ui.form.on('Food Demands', {
    refresh(frm) {
        toggle_fields(frm);
    },

    order_by(frm) {
        toggle_fields(frm);
    },

    person_details(frm) {
        if (!frm.doc.person_details) {
            frm.set_value('first_name', '');
            frm.set_value('last_name', '');
            return;
        }

        frappe.db.get_doc(
            'Person Details',
            frm.doc.person_details
        ).then(doc => {
            frm.set_value('first_name', doc.first_name || '');
            frm.set_value('last_name', doc.last_name || '');
        });
    },

    contacted_animal_shelter(frm) {
        if (!frm.doc.contacted_animal_shelter) {
            frm.set_value('shelter_name', '');
            return;
        }

        frappe.db.get_doc(
            'Animal Shelters',
            frm.doc.contacted_animal_shelter
        ).then(doc => {
            frm.set_value('shelter_name', doc.shelter_name || doc.name);
        });
    }
});

/* ---------------- Helper Function ---------------- */

function toggle_fields(frm) {
    const orderBy = frm.doc.order_by;

    // Hide everything first
    const all_fields = [
        'person_details', 'first_name', 'last_name',
        'contacted_animal_shelter', 'shelter_name', 'animal_shelter_statues'
    ];

    all_fields.forEach(field =>
        frm.set_df_property(field, 'hidden', 1)
    );

    // PERSON selected
    if (orderBy === "Person") {
        show_fields(frm, ['person_details', 'first_name', 'last_name']);

        // Clear shelter data
        frm.set_value('contacted_animal_shelter', null);
        frm.set_value('shelter_name', '');
        frm.set_value('animal_shelter_statues', null);
    }

    // ANIMAL SHELTER selected
    else if (orderBy === "Animal Shelters") {
        show_fields(frm, [
            'contacted_animal_shelter',
            'shelter_name',
            'animal_shelter_statues'
        ]);

        // Clear person data
        frm.set_value('person_details', null);
        frm.set_value('first_name', '');
        frm.set_value('last_name', '');
    }
}

/* -------- Utility -------- */

function show_fields(frm, fields) {
    fields.forEach(field =>
        frm.set_df_property(field, 'hidden', 0)
    );
}
