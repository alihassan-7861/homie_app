// Copyright (c) 2025, Anonymous and contributors
// For license information, please see license.txt

frappe.ui.form.on('Animal Information', {
    animal_type(frm) {
        frm.toggle_display(['adult_dogs', 'puppies', 'senior_sick_dogs'], frm.doc.animal_type === 'Dog');
        frm.toggle_display(['adult_cats', 'kittens', 'senior_sick_cats'], frm.doc.animal_type === 'Cat');
    },

    refresh(frm) {
        frm.trigger('animal_type');
    }
});

