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




