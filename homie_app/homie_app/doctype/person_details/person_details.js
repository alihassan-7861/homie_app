// Copyright (c) 2025
// License: see license.txt

frappe.ui.form.on('Person Details', {
    first_name: update_full_name,
    last_name: update_full_name,

    refresh(frm) {
        update_full_name(frm);
    }
});

function update_full_name(frm) {
    const first = frm.doc.first_name || '';
    const last = frm.doc.last_name || '';

    const fullName = `${first} ${last}`.trim();

    // Only set if changed (avoids unnecessary dirty state)
    if (frm.doc.full_name !== fullName) {
        frm.set_value('full_name', fullName);
    }
}



