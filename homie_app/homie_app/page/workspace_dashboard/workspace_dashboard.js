frappe.pages["workspace-dashboard"] = frappe.pages["workspace-dashboard"] || {};

frappe.pages["workspace-dashboard"].on_page_load = function(wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "VETO Workspace",
        single_column: true
    });

    const main = $(page.main);

    /* =========================
       PAGE LAYOUT
    ==========================*/
    main.html(`
        <div style="padding:16px; background:#f8fafc;">

            <!-- KPI ROW -->
            <div id="kpis" style="
                display:flex;
                gap:16px;
                margin-bottom:24px;
                flex-wrap:wrap;
            "></div>



             <!-- Organizations -->
            <div style="margin-bottom:28px;">
                <h4>Organizations</h4>
                <div id="organizations_table" style="
                    background:#ffffff;
                    border:1px solid #e5e7eb;
                    border-radius:10px;
                    padding:12px;
                "></div>
            </div>

            <!-- PRODUCTS -->
            <div style="margin-bottom:28px;">
                <h4>Products</h4>
                <div id="products_table" style="
                    background:#ffffff;
                    border:1px solid #e5e7eb;
                    border-radius:10px;
                    padding:12px;
                "></div>
            </div>


            <!-- PERSONS -->

            <div style="margin-bottom:28px;">
                <h4>Person Details</h4>
                <div id="person_table" style="
                    background:#ffffff;
                    border:1px solid #e5e7eb;
                    border-radius:10px;
                    padding:12px;
                "></div>
            </div>

            <!-- DONATIONS -->
            <div style="margin-bottom:28px;">
                <h4>Donations</h4>
                <div id="donations_table" style="
                    background:#ffffff;
                    border:1px solid #e5e7eb;
                    border-radius:10px;
                    padding:12px;
                "></div>
            </div>

        </div>
    `);

    /* =========================
       KPI CARD (INLINE CSS)
    ==========================*/
    function kpi_card(icon, label, value) {
        return `
            <div style="
                display:flex;
                align-items:center;
                background:#ffffff;
                border:1px solid #e5e7eb;
                border-radius:10px;
                padding:14px 18px;
                min-width:220px;
                box-shadow:0 1px 2px rgba(0,0,0,0.05);
            ">
                <div style="
                    width:42px;
                    height:42px;
                    background:#e0f2fe;
                    border-radius:8px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    margin-right:12px;
                    font-size:20px;
                ">
                    ${icon}
                </div>

                <div style="
                    display:flex;
                    flex-direction:column;
                ">
                    <div style="
                        font-size:12px;
                        color:#6b7280;
                        font-weight:600;
                    ">
                        ${label}
                    </div>
                    <div style="
                        font-size:18px;
                        font-weight:700;
                        color:#111827;
                    ">
                        ${value}
                    </div>
                </div>
            </div>
        `;
    }

    /* =========================
       LOAD KPIs
    ==========================*/
    function load_kpis() {
        frappe.call({
            method: "homie_app.homie_app.page.workspace_dashboard.workspace_dashboard.get_admin_kpis",
            callback(r) {
                const kpis = r.message || {};
                $("#kpis").empty()
                    .append(kpi_card("📦", "Total Products", kpis.total_products || 0))
                    .append(kpi_card("💰", "Total Donations", kpis.total_donations || 0))
                    .append(kpi_card("€", "Total Amount", kpis.total_amount || 0))
                    .append(kpi_card("⚠️", "Out of Stock", kpis.out_of_stock || 0))
                    .append(kpi_card("🏢", "Active Organizations", kpis.active_organizations || 0));

            }
        });
    }



     /* =========================
       LOAD PERSONS
    ==========================*/
     function load_organizations() {
        frappe.call({
            method: "homie_app.homie_app.page.workspace_dashboard.workspace_dashboard.get_organizations",
            callback(r) {
                $("#organizations_table").html(make_table(r.message || []));
            }
        });
    }

    /* =========================
       LOAD PRODUCTS
    ==========================*/
    function load_products() {
        frappe.call({
            method: "homie_app.homie_app.page.workspace_dashboard.workspace_dashboard.get_products",
            callback(r) {
                $("#products_table").html(make_table(r.message || []));
            }
        });
    }

    /* =========================
       LOAD PERSONS
    ==========================*/
     function load_person() {
        frappe.call({
            method: "homie_app.homie_app.page.workspace_dashboard.workspace_dashboard.get_persons",
            callback(r) {
                $("#person_table").html(make_table(r.message || []));
            }
        });
    }

    /* =========================
       LOAD DONATIONS
    ==========================*/
    function load_donations() {
        frappe.call({
            method: "homie_app.homie_app.page.workspace_dashboard.workspace_dashboard.get_donations",
            callback(r) {
                $("#donations_table").html(make_table(r.message || []));
            }
        });
    }


function is_image_field(field) {
    return [
        "image",
        "product_image",
        "product_image_desktop",
        "logo",
        "organization_logo",
        "org_logo"
    ].includes(field);
}



function get_image_url(path) {
    if (!path) return null;

    // Already absolute
    if (path.startsWith("http")) return path;

    // Private files
    if (path.startsWith("private/")) return `/${path}`;

    // Public files
    if (path.startsWith("/files")) return path;

    // Fallback
    return `/files/${path}`;
}

function render_cell(field, value, row) {

    if (is_image_field(field)) {

        const img_url = get_image_url(value);

        return `
            <div style="
                display:flex;
                align-items:center;
                gap:12px;
            ">
                <div style="
                    width:42px;
                    height:42px;
                    border-radius:8px;
                    overflow:hidden;
                    flex-shrink:0;
                    background:#f3f4f6;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                ">
                    ${
                        img_url
                        ? `<img src="${img_url}"
                               style="width:100%;
                                      height:100%;
                                      object-fit:cover;">`
                        : `<span style="color:#9ca3af;">🏢</span>`
                    }
                </div>

                <div style="display:flex; flex-direction:column;">
                    <span style="font-weight:600;">
                        ${row.organization_name || row.product_name || row.name || "Unnamed"}
                    </span>
                    <span style="font-size:12px;color:#6b7280;">
                        ${row.organization_type || row.product_category || ""}
                    </span>
                </div>
            </div>
        `;
    }

    return value ?? "-";
}




    function titleCase(str) {
            return str
                .replace(/_/g, " ")
                .replace(/\w\S*/g, w => w.charAt(0).toUpperCase() + w.slice(1));
        }

    /* =========================
       TABLE RENDERER (INLINE SAFE)
    ==========================*/
    function make_table(data) {
    if (!data.length) {
        return `<div style="color:#6b7280;">No data available</div>`;
    }

    const headers = Object.keys(data[0]);

    return `
        <table class="table table-hover table-bordered">
            <thead>
                <tr>
                    ${headers.map(h => `<th>${titleCase(h)}</th>`).join("")}
                </tr>
            </thead>
            <tbody>
                ${data.map(row => `
                    <tr>
                        ${headers.map(h => `
                            <td>
                                ${render_cell(h, row[h], row)}
                            </td>
                        `).join("")}
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}



    /* =========================
       INITIAL LOAD
    ==========================*/
    load_kpis();
    load_organizations();
    load_products();
    load_person();
    load_donations();
};
