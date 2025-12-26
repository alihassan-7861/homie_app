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
/* ================= PAGE BASE ================= */
.page-body {
    background: linear-gradient(180deg, #0f172a, #020617);
    color: #e5e7eb;
}

/* ================= LOADING SPINNER ================= */
.spinner {
    border: 4px solid rgba(255,255,255,0.15);
    border-top: 4px solid #60a5fa;
    border-radius: 50%;
    width: 42px;
    height: 42px;
    animation: spin 0.9s linear infinite;
    margin: 40px auto;
}
@keyframes spin {
    to { transform: rotate(360deg); }
}

.fade {
    transition: opacity 0.35s ease;
}

/* ================= HEADER ================= */
#org-header h2 {
    color: #f8fafc;
    font-weight: 700;
    margin-bottom: 4px;
}

#org-header p {
    color: #94a3b8;
    font-size: 13px;
}

/* ================= KPI CARDS ================= */
#kpis {
    flex-wrap: wrap;
}

.kpi-card {
    background: linear-gradient(145deg, #111827, #0f172a);
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 16px;
    min-width: 180px;
    text-align: center;
    box-shadow: 0 8px 22px rgba(0,0,0,0.45);
    transition: transform .2s ease, box-shadow .2s ease;
}

.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 14px 32px rgba(0,0,0,0.6);
}

.kpi-title {
    font-size: 13px;
    color: #cbd5f5;
    margin-bottom: 6px;
    font-weight: 600;
}

.kpi-value {
    font-size: 24px;
    font-weight: 700;
    color: #f8fafc;
}

/* ================= TABLES ================= */
table {
    width: 100%;
    border-collapse: collapse;
    background: #0f172a;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid #1e293b;
    box-shadow: 0 10px 26px rgba(0,0,0,.45);
    margin-top: 12px;
}

/* Table Header */
thead th {
    background: linear-gradient(135deg, #1e293b, #020617);
    color: #e5e7eb;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .05em;
    padding: 12px;
    border-bottom: 1px solid #1e293b;
}

/* Rows */
tbody tr {
    background: #0f172a;
    transition: background .2s ease;
}

tbody tr:hover {
    background: #020617;
}

/* Cells */
td {
    padding: 12px;
    font-size: 14px;
    color: #f1f5f9;
    border-top: 1px solid #1e293b;
}

/* Empty text */
#donations p,
#deliveries p {
    color: #94a3b8;
    font-size: 14px;
    padding: 20px;
    text-align: center;
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
                <div class="kpi-title">👤 Donations to Persons</div>
                <div class="kpi-value">${data.kpis.donation_to_person_count}</div>
            </div>

            <div class="card kpi-card">
                <div class="kpi-title">🐾 Donations to Shelters</div>
                <div class="kpi-value">${data.kpis.donation_to_shelter_count}</div>
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
