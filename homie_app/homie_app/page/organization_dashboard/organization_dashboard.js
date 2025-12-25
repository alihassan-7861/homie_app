frappe.pages['organization-dashboard'].on_page_load = function(wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Organization Dashboard',
        single_column: true
    });

    const main = $(page.main);

    /* ---------------- SPINNER STYLE ---------------- */
    if (!document.getElementById("org-spinner-style")) {
        const style = document.createElement("style");
        style.id = "org-spinner-style";
        style.innerHTML = `
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .fade {
                transition: opacity .3s ease;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                font-size: 13px;
            }
            th {
                background: #f7f7f7;
                text-align: left;
            }


            .kpi-card {
    text-align: center;
    padding: 16px;
}

.kpi-title {
    font-weight: 600;
    margin-bottom: 6px;
}

.kpi-value {
    font-size: 22px;
    font-weight: bold;
}

        `;
        document.head.appendChild(style);
    }

    /* ---------------- PAGE LAYOUT ---------------- */
    function setup_page() {
        main.html(`
            <div id="loading-spinner" style="display:none">
                <div class="spinner"></div>
            </div>

            <div id="content" class="fade" style="opacity:0">
                <div id="org-header"></div>

                <div id="kpis" style="display:flex; gap:16px; margin:20px 0;"></div>

                <h4>Donations</h4>
                <div id="donations"></div>

                <h4 style="margin-top:20px;">Deliveries</h4>
                <div id="deliveries"></div>
            </div>
        `);
    }

    /* ---------------- LOAD ORGANIZATION ---------------- */
    function load_organization(org_name) {
        $("#content").css("opacity", 0);
        $("#loading-spinner").show();

        frappe.call({
            method: "homie_app.homie_app.page.organization_dashboard.organization_dashboard.get_organization_dashboard",
            args: { organization: org_name },
            callback(r) {
                $("#loading-spinner").hide();
                if (r.message) {
                    render_dashboard(r.message);
                } else {
                    $("#org-header").html("<p>No data found.</p>");
                }
            },
            error(err) {
                console.error(err);
                $("#loading-spinner").hide();
                frappe.msgprint("Failed to load organization data");
            }
        });
    }

    /* ---------------- RENDER DASHBOARD ---------------- */
    function render_dashboard(data) {

        /* HEADER */
        $("#org-header").html(`
            <h2>${data.organization.organization_name}</h2>
            <p><b>ID:</b> ${data.organization.name}</p>
        `);

        /* KPIs */
        $("#kpis").html(`
            <div class="card kpi-card">
                <div class="kpi-title">💰 Total Donated</div>
                <div class="kpi-value">₹${data.kpis.total_donated}</div>
            </div>

            <div class="card kpi-card">
                <div class="kpi-title">📦 Donations</div>
                <div class="kpi-value">${data.kpis.donation_count}</div>
            </div>

            <div class="card kpi-card">
                <div class="kpi-title">🚚 Deliveries</div>
                <div class="kpi-value">${data.kpis.delivery_count}</div>
            </div>
`);


        /* DONATIONS TABLE */
       /* DONATIONS TABLE */
let donation_html = `<p>No donations found</p>`;

if (data.donations?.length) {
    donation_html = `
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Donated To</th>
                    <th>Person Name</th>
                    <th>Shelter Name</th>
                    <th>Product</th>
                    <th>Qty</th>
                    <th>Amount</th>
                    <th>Line Total</th>
                    <th>Donation Total</th>
                </tr>
            </thead>
            <tbody>
                ${data.donations.map(d => {

                    const person_name =
                        `${d.person_first_name || ""} ${d.person_last_name || ""}`.trim();

                    const shelter_name = d.shelter_name || "";

                    if (!d.items || !d.items.length) {
                        return `
                            <tr>
                                <td>${d.donated_at || ""}</td>
                                <td>${d.donated_to || ""}</td>
                                <td>${person_name || "-"}</td>
                                <td>${shelter_name || "-"}</td>
                                <td colspan="4">No items</td>
                                <td>₹${d.total || 0}</td>
                            </tr>
                        `;
                    }

                    return d.items.map((i, idx) => `
                        <tr>
                            ${idx === 0 ? `
                                <td rowspan="${d.items.length}">${d.donated_at || ""}</td>
                                <td rowspan="${d.items.length}">${d.donated_to || ""}</td>
                                <td rowspan="${d.items.length}">${person_name || "-"}</td>
                                <td rowspan="${d.items.length}">${shelter_name || "-"}</td>
                            ` : ""}

                            <td>${i.product_name || ""}</td>
                            <td>${i.quantity || 0}</td>
                            <td>₹${i.amount || 0}</td>
                            <td>₹${i.total || 0}</td>

                            ${idx === 0 ? `
                                <td rowspan="${d.items.length}">₹${d.total || 0}</td>
                            ` : ""}
                        </tr>
                    `).join("");

                }).join("")}
            </tbody>
        </table>
    `;
}

$("#donations").html(donation_html);


        /* DELIVERIES */
        /* ---------------- DELIVERIES TABLE ---------------- */
let delivery_html = `<p>No deliveries found</p>`;

if (data.deliveries?.length) {
    delivery_html = `
        <table>
            <thead>
                <tr>
                    <th>Organization</th>
                    <th>Recipient</th>
                    <th>Delivery Type</th>
                    <th>Order Date</th>
                    <th>Delivery Date</th>
                </tr>
            </thead>
            <tbody>
                ${data.deliveries.map(d => {
                    // Recipient display
                    let recipient = "";
                    if (d.deleiver_to === "Person") {
                        recipient = `${d.first_name || ""} ${d.last_name || ""}`.trim() || d.person_details || "";
                    } else if (d.deleiver_to === "Animal Shelter") {
                        recipient = d.shleter_name || d.shleter_details || "";
                    }

                    return `
                        <tr>
                            <td>${d.organization_name || d.organization_detail || ""}</td>
                            <td>${recipient}</td>
                            <td>${d.deleivery_type || ""}</td>
                            <td>${d.order_date || ""}</td>
                            <td>${d.deleivery_date || ""}</td>
                        </tr>
                    `;
                }).join("")}
            </tbody>
        </table>
    `;
}

$("#deliveries").html(delivery_html);


        $("#content").css("opacity", 1);
    }

    function getRecipient(d) {
        if (d.donated_to === "Person") {
            return `${d.person_first_name || ""} ${d.person_last_name || ""}`;
        }
        return d.shelter_name || "";
    }

    /* ---------------- ROUTE HANDLING (FIXES OLD DATA ISSUE) ---------------- */
    frappe.router.on("change", () => {
        const route = frappe.get_route();
        if (route[0] === "organization-dashboard" && route[1]) {
            setup_page();
            load_organization(route[1]);
        }
    });

    /* FIRST LOAD */
    setup_page();
    const initial = frappe.get_route()[1];
    if (initial) load_organization(initial);
};
