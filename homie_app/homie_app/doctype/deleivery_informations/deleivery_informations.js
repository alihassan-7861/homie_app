// // Copyright (c) 2025, Anonymous and contributors
// // For license information, please see license.txt

// frappe.ui.form.on('Deleivery Informations', {

//     refresh(frm) {
//         toggle_delivery_fields(frm);
//     },

//     deleiver_to(frm) {
//         toggle_delivery_fields(frm);
//     },

//     // ---------------- PERSON DETAILS ----------------
//     person_details(frm) {
//         if (frm.doc.person_details) {
//             frappe.db.get_doc('Person Details', frm.doc.person_details)
//                 .then(doc => {
//                     frm.set_value('first_name', doc.first_name || '');
//                     frm.set_value('last_name', doc.last_name || '');
//                 });
//         } else {
//             frm.set_value('first_name', '');
//             frm.set_value('last_name', '');
//         }
//     },

//     // ---------------- SHELTER DETAILS ----------------
//     shleter_details(frm) {
//         if (frm.doc.shleter_details) {
//             frappe.db.get_doc('Animal Shelters', frm.doc.shleter_details)
//                 .then(doc => {
//                     frm.set_value('shleter_name', doc.shelter_name || doc.name);
//                 });
//         } else {
//             frm.set_value('shleter_name', '');
//         }
//     }
// });


// // ================= FIELD TOGGLING =================
// function toggle_delivery_fields(frm) {
//     const deliverTo = frm.doc.deleiver_to;

//     // ---------- PERSON ----------
//     if (deliverTo === "Person") {
//         show_fields(frm, [
//             'person_details',
//             'first_name',
//             'last_name'
//         ]);

//         hide_fields(frm, [
//             'shleter_details',
//             'shleter_name'
//         ]);

//         frm.set_value('shleter_details', null);
//         frm.set_value('shleter_name', '');
//     }

//     // ---------- ANIMAL SHELTER ----------
//     else if (deliverTo === "Animal Shelter") {
//         show_fields(frm, [
//             'shleter_details',
//             'shleter_name'
//         ]);

//         hide_fields(frm, [
//             'person_details',
//             'first_name',
//             'last_name'
//         ]);

//         frm.set_value('person_details', null);
//         frm.set_value('first_name', '');
//         frm.set_value('last_name', '');
//     }

//     // ---------- NOTHING SELECTED ----------
//     else {
//         hide_fields(frm, [
//             'person_details',
//             'first_name',
//             'last_name',
//             'shleter_details',
//             'shleter_name'
//         ]);
//     }
// }


// // ================= HELPERS =================
// function show_fields(frm, fields) {
//     fields.forEach(field => {
//         frm.set_df_property(field, 'hidden', 0);
//     });
// }

// function hide_fields(frm, fields) {
//     fields.forEach(field => {
//         frm.set_df_property(field, 'hidden', 1);
//     });
// }



// Copyright (c) 2025, Anonymous and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deleivery Informations', {

    refresh(frm) {
        toggle_source_fields(frm);
        toggle_delivery_fields(frm);
        update_display_title(frm);
    },

    deleivery_type(frm) {
        toggle_source_fields(frm);
        update_display_title(frm);
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
                    update_display_title(frm);
                });
        } else {
            frm.set_value('first_name', '');
            frm.set_value('last_name', '');
            update_display_title(frm);
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
    },

    // ---------------- ORGANIZATION DETAILS ----------------
   organization_detail(frm) {
    if (frm.doc.organization_detail) {
        frappe.db.get_doc('Organization Details', frm.doc.organization_detail)
            .then(doc => {
                // Use 'organization_name' from the linked doc instead of the ID
                frm.set_value('organization_name', doc.organization_name || doc.name);
                update_display_title(frm);
            });
    } else {
        frm.set_value('organization_name', '');
        update_display_title(frm);
    }
}

});

// ================= SOURCE FIELD TOGGLING =================
function toggle_source_fields(frm) {
    const type = frm.doc.deleivery_type;

    if (type === "Own Purchase") {
        frm.set_df_property("person_details", "reqd", 1);
        frm.set_df_property("person_details", "hidden", 0);

        frm.set_df_property("organization_detail", "reqd", 0);
        frm.set_df_property("organization_detail", "hidden", 1);
        frm.set_value("organization_detail", null);
        frm.set_value("organization_name", "");
    }
    else if (type === "Donated From Organization") {
        frm.set_df_property("organization_detail", "reqd", 1);
        frm.set_df_property("organization_detail", "hidden", 0);

        frm.set_df_property("person_details", "reqd", 0);
        frm.set_df_property("person_details", "hidden", 1);
        frm.set_value("person_details", null);
        frm.set_value("first_name", "");
        frm.set_value("last_name", "");
    }
    else {
        frm.set_df_property("person_details", "hidden", 1);
        frm.set_df_property("organization_detail", "hidden", 1);
    }
}

// ================= DELIVERY FIELD TOGGLING =================
function toggle_delivery_fields(frm) {
    const deliverTo = frm.doc.deleiver_to;

    if (deliverTo === "Person") {
        show_fields(frm, ['person_details', 'first_name', 'last_name']);
        hide_fields(frm, ['shleter_details', 'shleter_name']);
        frm.set_value('shleter_details', null);
        frm.set_value('shleter_name', '');
    }
    else if (deliverTo === "Animal Shelter") {
        show_fields(frm, ['shleter_details', 'shleter_name']);
        hide_fields(frm, ['person_details', 'first_name', 'last_name']);
        frm.set_value('person_details', null);
        frm.set_value('first_name', '');
        frm.set_value('last_name', '');
    }
    else {
        hide_fields(frm, ['person_details', 'first_name', 'last_name', 'shleter_details', 'shleter_name']);
    }
}

// ================= DISPLAY TITLE =================
function update_display_title(frm) {
    if (frm.doc.deleivery_type === "Own Purchase" && frm.doc.person_details) {
        frm.set_value("display_title", `Purchased by ${frm.doc.person_details}`);
    }
    else if (frm.doc.deleivery_type === "Donated From Organization" && frm.doc.organization_detail) {
        frm.set_value("display_title", `Donated by ${frm.doc.organization_detail}`);
    }
    else {
        frm.set_value("display_title", "");
    }
}

// ================= HELPERS =================
function show_fields(frm, fields) {
    fields.forEach(field => frm.set_df_property(field, 'hidden', 0));
}

function hide_fields(frm, fields) {
    fields.forEach(field => frm.set_df_property(field, 'hidden', 1));
}
