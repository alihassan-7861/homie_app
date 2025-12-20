// Copyright (c) 2025, Anonymous and contributors
// For license information, please see license.txt

frappe.ui.form.on('Animal Information', {
    animal_type(frm) {
        frm.toggle_display(
            ['adult_dogs', 'puppies', 'senior_sick_dogs'],
            frm.doc.animal_type === 'Dog'
        );
        frm.toggle_display(
            ['adult_cats', 'kittens', 'senior_sick_cats'],
            frm.doc.animal_type === 'Cat'
        );
    },

    refresh(frm) {
        frm.trigger('animal_type');
    },

    // ✅ MUST match link field name
    person_details: function(frm) {
        if (frm.doc.person_details) {
            frappe.db.get_doc(
                'Person Details',
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



frappe.ui.form.on('Animal Information', {

    refresh(frm) {
        toggle_animal_fields(frm);
    },

    source(frm) {
        toggle_animal_fields(frm);
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
    shelter_detail(frm) {
        if (frm.doc.shelter_detail) {
            frappe.db.get_doc('Animal Shelters', frm.doc.shelter_detail)
                .then(doc => {
                    frm.set_value('shelter_name', doc.shelter_name || doc.name);
                });
        } else {
            frm.set_value('shelter_name', '');
        }
    }

});

// ================= FIELD TOGGLING =================
function toggle_animal_fields(frm) {
    const source = frm.doc.source;

    // ---------- PERSON ----------
    if (source === "Person") {
        show_fields(frm, [
            'person_details',
            'first_name',
            'last_name'
        ]);

        hide_fields(frm, [
            'shelter_detail',
            'shelter_name'
        ]);

        frm.set_value('shelter_detail', null);
        frm.set_value('shelter_name', '');
    }

    // ---------- ANIMAL SHELTER ----------
    else if (source === "Animal Shelter") {
        show_fields(frm, [
            'shelter_detail',
            'shelter_name'
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
            'shelter_detail',
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
