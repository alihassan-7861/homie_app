frappe.ui.form.on('Donation Item', {
    product: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        if(row.product) {
            // Fetch product price from Product Details
            frappe.db.get_value('Product Details', row.product, 'product_price')
            .then(r => {
                let price = r.message.product_price || 0;
                row.amount = price;
                row.total = (row.quantity || 0) * row.amount;
                frm.refresh_field('items');

                // Update parent donation total
                update_parent_total(frm);
            });
        }
    },
    quantity: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        row.total = (row.quantity || 0) * (row.amount || 0);
        frm.refresh_field('items');

        // Update parent donation total
        update_parent_total(frm);
    }
});

function update_parent_total(frm) {
    let donation_total = 0;
    frm.doc.items.forEach(function(item) {
        donation_total += item.total || 0;
    });
    frm.set_value('total', donation_total);
}
