/* SCOTT Automation Deck Builder — form logic
 * Handles: section toggles with sub-slides, value-driver tag picker,
 * previous-project picker, proposal slides with drag-and-drop reorder,
 * live slide-count summary, form submission to /api/generate.
 */

// ============================================================================
// DATA — kept in sync with backend lib/stats_library.py and lib/deck_builder.py
// ============================================================================

const VALUE_DRIVERS = [
    {
        id: "safety",
        name: "Safety",
        desc: "Injuries, OSHA recordables, ergonomic risk",
    },
    {
        id: "labor",
        name: "Labor savings",
        desc: "Hard-to-fill positions, overtime spend",
    },
    {
        id: "throughput",
        name: "Throughput",
        desc: "Cycle time, parts per shift, OEE",
    },
    { id: "downtime", name: "Costly downtime", desc: "Unplanned stops, MTBF" },
    {
        id: "quality",
        name: "Quality & rework",
        desc: "Scrap, defects, customer returns",
    },
    {
        id: "leadtime",
        name: "Lead time",
        desc: "Time-to-ship, on-time delivery",
    },
    {
        id: "ergonomics",
        name: "Ergonomics",
        desc: "Repetitive motion, lifting strain, MSDs",
    },
    {
        id: "compliance",
        name: "Compliance",
        desc: "OSHA, UL/cUL, FDA, audit readiness",
    },
    {
        id: "energy",
        name: "Energy efficiency",
        desc: "Power draw, HPU cooling, idle load",
    },
    {
        id: "floorspace",
        name: "Floor space",
        desc: "Footprint, layout, expansion limits",
    },
    {
        id: "retention",
        name: "Skilled-labor retention",
        desc: "Turnover, recruiting cost",
    },
    {
        id: "insurance",
        name: "Workers comp / insurance",
        desc: "Premium loading, mod rate",
    },
];

// SCOTT capabilities sections — slide numbers refer to the source template (slides 4-36)
const SECTIONS = [
    {
        id: "history",
        title: "SCOTT History",
        summary: "2 slides — A Legacy of Innovation and Trust Since 1948",
        subslides: [
            {
                num: 4,
                title: "A Legacy of Innovation and Trust Since 1948",
                desc: "Origin story — Roger & Doris Scott, Dayton OH, 1948",
            },
            {
                num: 5,
                title: "A Legacy of Innovation and Trust Since 1948 (cont.)",
                desc: "Today — automation, assembly machines, team photo",
            },
        ],
    },
    {
        id: "capabilities",
        title: "Capabilities",
        summary: "5 slides — A Full-Service Integrator",
        subslides: [
            {
                num: 6,
                title: "A Full-Service Integrator",
                desc: "Single-source partner overview, 8 service pills",
            },
            {
                num: 7,
                title: "Built for Any Challenge",
                desc: "Concept to completion, full capability list",
            },
            {
                num: 8,
                title: "Solutions for Your Market & Business",
                desc: "Industries served — automotive, F&B, energy, etc.",
            },
            {
                num: 9,
                title: "Manufacturing Partners",
                desc: "Robotic + control equipment supplier logos",
            },
            {
                num: 10,
                title: "Automation Systems",
                desc: "Consult / engineer / design overview & offerings",
            },
        ],
    },
    {
        id: "previousProjects",
        title: "Previous Project Designs",
        summary: "Pick case studies — see Section 4 below",
        subslides: null, // Selected via project picker
    },
    {
        id: "hpu",
        title: "Hydraulic Power Units",
        summary: "4 slides — Custom Hydraulic Motion Control",
        subslides: [
            {
                num: 22,
                title: "Custom Hydraulic Motion Control Systems",
                desc: "Overview — retrofit, upgrade, replace; 3D CAD",
            },
            {
                num: 23,
                title: "Configurable HPUs — Sizing & Flow",
                desc: "1–30 gpm, up to 50 HP, 10–80 gal, 3,000 psi",
            },
            {
                num: 24,
                title: "Configurable HPUs — Services Offered",
                desc: "Configurator, drawings, schematics, QR code",
            },
            {
                num: 25,
                title: "Configurable HPUs — Standard Features & Competition",
                desc: "Standard features; competition",
            },
        ],
    },
    {
        id: "controls",
        title: "Control Panels",
        summary: "5 slides — Industrial control systems & motor starters",
        subslides: [
            {
                num: 26,
                title: "Industrial Custom Control Systems",
                desc: "Control systems/packages/panels; cUL/UL 508A & 698A",
            },
            {
                num: 27,
                title: "Industrial Custom Control Systems (detail)",
                desc: "Reliability, customization, safety, service & support",
            },
            {
                num: 28,
                title: "Motor Control Centers (MCC)",
                desc: "100% SCOTT-designed; VFD, PLCs, HMI packages",
            },
            {
                num: 29,
                title: "Configurable Motor Starter Control Packages",
                desc: "Up to 4 motors, overload & surge protection",
            },
            {
                num: 30,
                title: "Motor Starter Control Packages — Overview & Options",
                desc: "Voltage, enclosure, advantages, design options",
            },
        ],
    },
    {
        id: "engineered",
        title: "Engineered Expertise",
        summary: "2 slides — Design tools & engineering team",
        subslides: [
            {
                num: 31,
                title: "Engineered Expertise — Tools",
                desc: "ePlan & AutoCAD, CNC, wire processing, ERP",
            },
            {
                num: 32,
                title: "Engineered Expertise — Team",
                desc: "7 Controls, 8 Electrical, 8 Mech engineers; 400+ yrs",
            },
        ],
    },
    {
        id: "testStands",
        title: "Test Stands",
        summary: "2 slides — Testing capabilities & stand types",
        subslides: [
            {
                num: 33,
                title: "Testing Capabilities — Motor / Cast Iron Pump / Aluminum Pump",
                desc: "Flow, PSI, HP, RPM specs",
            },
            {
                num: 34,
                title: "Testing Capabilities — Pump & Manifold Test Stands",
                desc: "VFD, HMI, contamination monitoring",
            },
        ],
    },
    {
        id: "realResults",
        title: "Real Results",
        summary: "1 slide — Real Customers, Real Results, Real Cost Savings",
        subslides: null, // single-slide section
    },
];

const PROJECTS = [
    {
        id: "p11",
        tag: "Automation Systems",
        title: "Aluminum Manufacturer — Machine Tending",
        sub: "9 mo · 4× Kuka · Allen Bradley · MCS conveyors",
    },
    {
        id: "p12",
        tag: "Automation Systems",
        title: "Automated Deburring Cell",
        sub: "6 mo · 2× Motoman · Mitsubishi",
    },
    {
        id: "p13",
        tag: "Automotive",
        title: "Mission Case Bearing Press",
        sub: "4 mo · Mitsubishi · custom tooling",
    },
    {
        id: "p14",
        tag: "Truck Mfg",
        title: "Glue Application System",
        sub: "6 mo · Kuka · Allen Bradley",
    },
    {
        id: "p15",
        tag: "Appliance",
        title: "Gear Case Machining Line",
        sub: "12 mo · 10× Kuka · 4 drilling stations",
    },
    {
        id: "p16",
        tag: "Automotive",
        title: "Radiator Assembly Cell",
        sub: "9 mo · 2× Kuka · feeder bowls",
    },
    {
        id: "p17",
        tag: "Automotive",
        title: "Valve Cover Quality Tester",
        sub: "4 mo · Omron · custom tooling",
    },
    {
        id: "p18",
        tag: "Medical Device",
        title: "Positive Battery Contact Assembly",
        sub: "Custom-built · spring staking",
    },
    {
        id: "p19",
        tag: "Machine Tool",
        title: "Induction Hardening Tend & Test",
        sub: "Tending · Eddy current · laser marking",
    },
    {
        id: "p20",
        tag: "Medical Device",
        title: "Packing Nut Assembly & Packaging",
        sub: "Bulk feed · 0.8 sec cycle",
    },
    {
        id: "p21",
        tag: "Aerospace",
        title: "Auto Bellows Forming Machine",
        sub: '¾"–10" O.D. · multi-program convolutes',
    },
];

// ============================================================================
// INIT
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
    renderValueDrivers();
    renderSections();
    renderProjects();
    addProposal(); // Start with one empty proposal slide
    wireUpEvents();
    wireUpCustomerSection();
    updateSummary();
});

// ============================================================================
// CUSTOMER SECTION (name vs logo segmented control)
// ============================================================================

// Holds the encoded logo (data URL) when the user picks one
let customerLogoData = null;
let customerLogoFilename = null;

function wireUpCustomerSection() {
    const segName = document.getElementById("segName");
    const segLogo = document.getElementById("segLogo");
    const modeName = document.getElementById("modeName");
    const modeLogo = document.getElementById("modeLogo");
    const fileInput = document.getElementById("customerLogo");
    const zone = document.getElementById("logoUploadZone");
    const preview = document.getElementById("logoPreview");
    const removeBtn = document.getElementById("logoRemove");

    function setMode(mode) {
        if (mode === "name") {
            segName.classList.add("active");
            segLogo.classList.remove("active");
            modeName.classList.remove("hidden");
            modeLogo.classList.add("hidden");
        } else {
            segLogo.classList.add("active");
            segName.classList.remove("active");
            modeLogo.classList.remove("hidden");
            modeName.classList.add("hidden");
        }
    }
    segName.addEventListener("click", () => setMode("name"));
    segLogo.addEventListener("click", () => setMode("logo"));

    function handleFile(file) {
        if (!file) return;
        if (file.size > 2 * 1024 * 1024) {
            alert("Logo must be under 2 MB. Please choose a smaller file.");
            return;
        }
        if (!["image/png", "image/jpeg", "image/svg+xml"].includes(file.type)) {
            alert("Logo must be a PNG, JPG, or SVG.");
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            customerLogoData = e.target.result;
            customerLogoFilename = file.name;
            preview.src = customerLogoData;
            preview.classList.remove("hidden");
            removeBtn.classList.remove("hidden");
            zone.classList.add("has-file");
        };
        reader.readAsDataURL(file);
    }

    fileInput.addEventListener("change", (e) => handleFile(e.target.files[0]));
    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("drag-over");
    });
    zone.addEventListener("dragleave", () =>
        zone.classList.remove("drag-over"),
    );
    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("drag-over");
        handleFile(e.dataTransfer.files[0]);
    });
    removeBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        customerLogoData = null;
        customerLogoFilename = null;
        fileInput.value = "";
        preview.src = "";
        preview.classList.add("hidden");
        removeBtn.classList.add("hidden");
        zone.classList.remove("has-file");
    });

    setMode("name");
}

// ============================================================================
// VALUE DRIVERS
// ============================================================================

function renderValueDrivers() {
    const grid = document.getElementById("tagGrid");
    VALUE_DRIVERS.forEach((t) => {
        const lbl = document.createElement("label");
        lbl.className = "tag-opt";
        lbl.dataset.id = t.id;
        lbl.innerHTML = `
      <input type="checkbox" name="valueDriver" value="${t.id}" />
      <div>
        <div class="tag-name">${t.name}</div>
        <span class="tag-desc">${t.desc}</span>
      </div>`;
        grid.appendChild(lbl);
    });
    grid.addEventListener("change", (e) => {
        if (e.target.matches('input[name="valueDriver"]')) {
            const lbl = e.target.closest(".tag-opt");
            lbl.classList.toggle("checked", e.target.checked);
        }
        updateSummary();
    });
}

// ============================================================================
// SECTIONS (with sub-slide picking)
// ============================================================================

function renderSections() {
    const container = document.getElementById("sectionsContainer");
    SECTIONS.forEach((sec) => {
        const block = document.createElement("div");
        block.className = "section-block";
        block.dataset.sectionId = sec.id;

        let headerHtml = `
      <div class="section-block-head">
        <input type="checkbox" class="sec-master" data-section="${sec.id}" checked />
        <div class="t-body">
          <p class="t-title">${sec.title}</p>
          <p class="t-meta">${sec.summary}</p>
        </div>
    `;
        if (sec.subslides) {
            headerHtml += `<button type="button" class="expand-btn" data-toggle="${sec.id}" aria-label="Expand">▾</button>`;
        }
        headerHtml += `</div>`;

        let subHtml = "";
        if (sec.subslides) {
            subHtml = `<div class="sub-slides" id="sub-${sec.id}" style="display:none;"><div class="sub-slides-inner">`;
            sec.subslides.forEach((s) => {
                subHtml += `
          <label class="sub-slide">
            <input type="checkbox" class="sub-cb" data-parent="${sec.id}" data-slide="${s.num}" checked />
            <span class="ss-num">${s.num}</span>
            <div>
              <div class="ss-title">${s.title}</div>
              <div class="ss-desc">${s.desc}</div>
            </div>
          </label>`;
            });
            subHtml += `</div></div>`;
        }

        block.innerHTML = headerHtml + subHtml;
        container.appendChild(block);
    });
}

// ============================================================================
// PROJECTS PICKER
// ============================================================================

function renderProjects() {
    const grid = document.getElementById("projectsGrid");
    // Default: first 2 projects checked
    PROJECTS.forEach((p, i) => {
        const lbl = document.createElement("label");
        lbl.className = "proj";
        lbl.dataset.id = p.id;
        const checked = i < 2 ? "checked" : "";
        lbl.innerHTML = `
      <input type="checkbox" name="project" value="${p.id}" ${checked} />
      <div>
        <span class="proj-tag">${p.tag}</span>
        <p class="proj-title">${p.title}</p>
        <p class="proj-sub">${p.sub}</p>
      </div>`;
        if (checked) lbl.classList.add("checked");
        grid.appendChild(lbl);
    });

    grid.addEventListener("change", (e) => {
        if (e.target.matches('input[name="project"]')) {
            e.target
                .closest(".proj")
                .classList.toggle("checked", e.target.checked);
        }
        updateSummary();
    });
}

// ============================================================================
// PROPOSAL SLIDES (drag-and-drop)
// ============================================================================

let proposalIdCounter = 0;

// Embedded media is kept in JS state, indexed by the proposal-card data-id.
// We don't send big files as base64 — we let the browser upload them as multipart/form-data.
const proposalMediaState = {}; // { 'prop-1': { kind: 'image', file: File, dataUrl?: string, videoUrl?: string } }

function addProposal() {
    proposalIdCounter++;
    const id = `prop-${proposalIdCounter}`;
    proposalMediaState[id] = { kind: "none" };
    const card = document.createElement("div");
    card.className = "proposal-card";
    card.draggable = true;
    card.dataset.id = id;
    card.innerHTML = `
    <div class="proposal-head">
      <span class="drag-handle" aria-label="Drag to reorder">⠿</span>
      <strong class="p-title">Proposal slide</strong>
      <button type="button" class="icon-btn remove-btn" aria-label="Remove">✕</button>
    </div>
    <div class="field">
      <span class="label">Slide title</span>
      <input type="text" name="proposalTitle[]" placeholder="e.g. Proposed solution — Phase 1" />
    </div>
    <div class="field">
      <span class="label">Body content (optional)</span>
      <textarea name="proposalBody[]" rows="3" placeholder="Short description shown on the slide. Plain text is fine; blank lines separate paragraphs."></textarea>
    </div>
    <div class="field">
      <span class="label">Visual (optional)</span>
      <div class="media-row">
        <div class="media-tabs" role="tablist" aria-label="Media type">
          <button type="button" class="media-tab active" data-pane="none">None</button>
          <button type="button" class="media-tab" data-pane="image">Image / GIF</button>
          <button type="button" class="media-tab" data-pane="video">Video link</button>
        </div>

        <div class="media-pane active" data-kind="none">
          <p class="media-info" style="margin: 0;">Text-only slide.</p>
        </div>

        <div class="media-pane" data-kind="image">
          <label class="upload-zone media-upload-zone">
            <div class="upload-zone-inner">
              <div class="upload-icon">⬆</div>
              <div class="upload-msg">Drop a PNG, JPG, or GIF here</div>
              <div class="upload-sub">Up to 10 MB · larger files embed slowly</div>
            </div>
            <img class="media-thumb hidden" alt="" />
            <button type="button" class="logo-remove media-remove hidden" aria-label="Remove">✕</button>
            <input type="file" class="visually-hidden media-file-input" accept="image/png,image/jpeg,image/gif" />
          </label>
          <p class="media-info hidden"></p>
        </div>

        <div class="media-pane" data-kind="video">
          <input type="url" class="video-url-input" placeholder="https://youtu.be/... or SharePoint, Drive, Vimeo, etc." />
          <p class="media-info">A clickable thumbnail is added to the slide; the customer clicks to open the video.</p>
        </div>
      </div>
    </div>
  `;

    // Remove button
    card.querySelector(".remove-btn").addEventListener("click", () => {
        delete proposalMediaState[id];
        card.remove();
        renumberProposals();
        updateSummary();
    });

    // Media tabs
    card.querySelectorAll(".media-tab").forEach((tab) => {
        tab.addEventListener("click", () => {
            const targetKind = tab.dataset.pane;
            card.querySelectorAll(".media-tab").forEach((t) =>
                t.classList.toggle("active", t === tab),
            );
            card.querySelectorAll(".media-pane").forEach((p) =>
                p.classList.toggle("active", p.dataset.kind === targetKind),
            );
            if (proposalMediaState[id].kind !== targetKind) {
                // Reset state when switching modes
                proposalMediaState[id] = { kind: targetKind };
            }
        });
    });

    // Image upload handlers
    const imgPane = card.querySelector('.media-pane[data-kind="image"]');
    const uploadZone = imgPane.querySelector(".media-upload-zone");
    const fileInput = imgPane.querySelector(".media-file-input");
    const thumb = imgPane.querySelector(".media-thumb");
    const removeMediaBtn = imgPane.querySelector(".media-remove");
    const infoEl = imgPane.querySelector(".media-info");

    function handleMediaFile(file) {
        if (!file) return;
        const tenMB = 10 * 1024 * 1024;
        if (file.size > tenMB) {
            infoEl.textContent = `File is ${(file.size / 1024 / 1024).toFixed(1)} MB — too large to embed. Use a video link instead.`;
            infoEl.className = "media-info error";
            infoEl.classList.remove("hidden");
            return;
        }
        if (!["image/png", "image/jpeg", "image/gif"].includes(file.type)) {
            infoEl.textContent = "Must be PNG, JPG, or GIF.";
            infoEl.className = "media-info error";
            infoEl.classList.remove("hidden");
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            proposalMediaState[id] = {
                kind: "image",
                file,
                dataUrl: e.target.result,
            };
            thumb.src = e.target.result;
            thumb.classList.remove("hidden");
            removeMediaBtn.classList.remove("hidden");
            uploadZone.classList.add("has-file");
            const sizeMB = (file.size / 1024 / 1024).toFixed(1);
            infoEl.textContent = `${file.name} · ${sizeMB} MB`;
            infoEl.className = "media-info";
            infoEl.classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    }

    fileInput.addEventListener("change", (e) =>
        handleMediaFile(e.target.files[0]),
    );
    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.classList.add("drag-over");
    });
    uploadZone.addEventListener("dragleave", () =>
        uploadZone.classList.remove("drag-over"),
    );
    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("drag-over");
        handleMediaFile(e.dataTransfer.files[0]);
    });
    removeMediaBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        proposalMediaState[id] = { kind: "image" }; // reset (still in image mode)
        fileInput.value = "";
        thumb.src = "";
        thumb.classList.add("hidden");
        removeMediaBtn.classList.add("hidden");
        uploadZone.classList.remove("has-file");
        infoEl.classList.add("hidden");
    });

    // Video URL
    const videoInput = card.querySelector(".video-url-input");
    videoInput.addEventListener("input", () => {
        const url = videoInput.value.trim();
        if (url) {
            proposalMediaState[id] = { kind: "video", videoUrl: url };
        } else {
            proposalMediaState[id] = { kind: "video" };
        }
    });

    // Drag and drop reordering
    card.addEventListener("dragstart", (e) => {
        // Don't trigger card drag if dragging files into media zone
        if (e.target.closest(".media-upload-zone")) {
            e.preventDefault();
            return;
        }
        card.classList.add("dragging");
    });
    card.addEventListener("dragend", () => {
        card.classList.remove("dragging");
        document
            .querySelectorAll(".proposal-card")
            .forEach((c) => c.classList.remove("drag-over"));
        renumberProposals();
    });
    card.addEventListener("dragover", (e) => {
        e.preventDefault();
        const dragging = document.querySelector(".proposal-card.dragging");
        if (!dragging || dragging === card) return;
        const container = document.getElementById("proposalsContainer");
        const rect = card.getBoundingClientRect();
        const before = e.clientY - rect.top < rect.height / 2;
        document
            .querySelectorAll(".proposal-card")
            .forEach((c) => c.classList.remove("drag-over"));
        card.classList.add("drag-over");
        if (before) container.insertBefore(dragging, card);
        else container.insertBefore(dragging, card.nextSibling);
    });

    document.getElementById("proposalsContainer").appendChild(card);
    renumberProposals();
    updateSummary();
}

function renumberProposals() {
    document.querySelectorAll(".proposal-card").forEach((c, i) => {
        c.querySelector(".p-title").textContent = `Proposal slide ${i + 1}`;
    });
}

// ============================================================================
// EVENT WIRING (sections, projects, etc.)
// ============================================================================

function wireUpEvents() {
    // Expand/collapse sub-slide panels
    document.addEventListener("click", (e) => {
        if (e.target.matches(".expand-btn")) {
            const panel = document.getElementById(
                `sub-${e.target.dataset.toggle}`,
            );
            if (!panel) return;
            const open = panel.style.display !== "none";
            panel.style.display = open ? "none" : "block";
            e.target.textContent = open ? "▾" : "▴";
        }
    });

    // Master section toggle → all sub-slides on/off
    document.addEventListener("change", (e) => {
        if (e.target.matches(".sec-master")) {
            const id = e.target.dataset.section;
            const block = e.target.closest(".section-block");
            block.classList.toggle("disabled", !e.target.checked);
            document
                .querySelectorAll(`.sub-cb[data-parent="${id}"]`)
                .forEach((s) => {
                    s.checked = e.target.checked;
                });
            updateSummary();
        }
        if (e.target.matches(".sub-cb")) {
            const id = e.target.dataset.parent;
            const siblings = document.querySelectorAll(
                `.sub-cb[data-parent="${id}"]`,
            );
            const anyChecked = Array.from(siblings).some((s) => s.checked);
            const master = document.querySelector(
                `.sec-master[data-section="${id}"]`,
            );
            master.checked = anyChecked;
            master
                .closest(".section-block")
                .classList.toggle("disabled", !anyChecked);
            updateSummary();
        }
    });

    // Projects bulk actions
    document
        .getElementById("selectAllProjects")
        .addEventListener("click", () => {
            document.querySelectorAll('input[name="project"]').forEach((cb) => {
                cb.checked = true;
                cb.closest(".proj").classList.add("checked");
            });
            updateSummary();
        });
    document.getElementById("clearProjects").addEventListener("click", () => {
        document.querySelectorAll('input[name="project"]').forEach((cb) => {
            cb.checked = false;
            cb.closest(".proj").classList.remove("checked");
        });
        updateSummary();
    });

    // Add proposal slide
    document
        .getElementById("addProposalBtn")
        .addEventListener("click", addProposal);

    // Form submit
    document
        .getElementById("deckForm")
        .addEventListener("submit", handleSubmit);
}

// ============================================================================
// LIVE SLIDE COUNT
// ============================================================================

function updateSummary() {
    let total = 3; // Cover + Customer + Index
    // Why slides
    total += 4; // pain point, what you get, plan, CTA
    const tags = document.querySelectorAll(
        'input[name="valueDriver"]:checked',
    ).length;
    total += tags; // one stat slide per value driver
    // SCOTT sections
    const subChecked = document.querySelectorAll(".sub-cb:checked").length;
    total += subChecked;
    // Previous projects (master toggle on AND projects selected)
    const prevMaster = document.querySelector(
        '.sec-master[data-section="previousProjects"]',
    );
    if (prevMaster && prevMaster.checked) {
        total += document.querySelectorAll(
            'input[name="project"]:checked',
        ).length;
    }
    // Real Results (single-slide section)
    const realMaster = document.querySelector(
        '.sec-master[data-section="realResults"]',
    );
    if (realMaster && realMaster.checked) total += 1;
    // Proposal slides
    total += document.querySelectorAll(".proposal-card").length;
    // Contact (always)
    total += 1;

    document.getElementById("summaryBar").innerHTML =
        `<strong>${total} slides total</strong> &nbsp;·&nbsp; Cover + Customer + Index + ${4 + tags} Why + ${subChecked} content + ${document.querySelectorAll('input[name="project"]:checked').length} projects + ${document.querySelectorAll(".proposal-card").length} custom proposals + Contact`;
}

// ============================================================================
// SUBMIT
// ============================================================================

async function handleSubmit(e) {
    e.preventDefault();

    // Validate: customer must have a name OR a logo
    const activeMode = document
        .getElementById("segName")
        .classList.contains("active")
        ? "name"
        : "logo";
    const customerName = document
        .querySelector('input[name="customerName"]')
        .value.trim();
    if (activeMode === "name" && !customerName) {
        alert("Please enter a customer name (or switch to Upload a logo).");
        return;
    }
    if (activeMode === "logo" && !customerLogoData) {
        alert("Please upload a customer logo (or switch to Use a name).");
        return;
    }

    showOverlay("Building your deck…", "This usually takes 10–20 seconds.");

    // Build multipart form-data so we can include binary files
    const fd = new FormData();
    const meta = collectMetadata(activeMode, customerName);
    fd.append("meta", JSON.stringify(meta));

    // Customer logo as a file
    if (activeMode === "logo" && customerLogoData) {
        const blob = await fetch(customerLogoData).then((r) => r.blob());
        fd.append("customerLogo", blob, customerLogoFilename || "logo.png");
    }

    // Proposal media files
    document.querySelectorAll(".proposal-card").forEach((card, i) => {
        const id = card.dataset.id;
        const state = proposalMediaState[id] || {};
        if (state.kind === "image" && state.file) {
            fd.append(`proposalImage_${i}`, state.file, state.file.name);
        }
    });

    try {
        const response = await fetch(
            "https://scott-deck-builder.vercel.app/api/generate",
            {
                method: "POST",
                body: fd,
            },
        );

        if (!response.ok) {
            const errText = await response.text().catch(() => "Unknown error");
            throw new Error(`Server error ${response.status}: ${errText}`);
        }

        // Server now returns JSON with a Vercel Blob download URL instead of
        // streaming the zip directly — avoids the 4.5 MB response payload limit.
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        if (!data.downloadUrl) throw new Error("No download URL returned from server.");

        showOverlay("Done!", "Your download should start automatically.");

        const safeName =
            (customerName || "Customer").replace(/[^a-zA-Z0-9_-]+/g, "_") ||
            "Customer";
        const a = document.createElement("a");
        a.href = data.downloadUrl;
        a.download = `SCOTT_${safeName}_Deck_Bundle.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();

        setTimeout(hideOverlay, 2000);
    } catch (err) {
        console.error(err);
        showOverlay("Something went wrong", err.message);
        document.querySelector(".overlay-card .spinner").style.display = "none";
        setTimeout(() => {
            document.querySelector(".overlay-card .spinner").style.display = "";
            hideOverlay();
        }, 6000);
    }
}

function collectMetadata(customerMode, customerName) {
    const fd = new FormData(document.getElementById("deckForm"));

    // Gather checked sub-slides per section
    const sectionsData = {};
    SECTIONS.forEach((sec) => {
        const master = document.querySelector(
            `.sec-master[data-section="${sec.id}"]`,
        );
        sectionsData[sec.id] = {
            enabled: master ? master.checked : false,
            subslides: sec.subslides
                ? Array.from(
                      document.querySelectorAll(
                          `.sub-cb[data-parent="${sec.id}"]:checked`,
                      ),
                  ).map((cb) => parseInt(cb.dataset.slide, 10))
                : null,
        };
    });

    // Collect proposal slides in current DOM order
    const proposals = [];
    document.querySelectorAll(".proposal-card").forEach((card, i) => {
        const id = card.dataset.id;
        const state = proposalMediaState[id] || { kind: "none" };
        const title = card
            .querySelector('input[name="proposalTitle[]"]')
            .value.trim();
        const body = card
            .querySelector('textarea[name="proposalBody[]"]')
            .value.trim();
        proposals.push({
            title,
            body,
            mediaKind: state.kind || "none",
            // mediaFileIndex tells the backend "use the file uploaded as proposalImage_{i}"
            mediaFileIndex: state.kind === "image" && state.file ? i : null,
            videoUrl: state.kind === "video" ? state.videoUrl || "" : "",
        });
    });

    return {
        customerMode, // 'name' or 'logo'
        customerName: customerMode === "name" ? customerName : "",
        customerLogoFilename:
            customerMode === "logo" ? customerLogoFilename : "",
        painPoint: fd.get("painPoint") || "",
        valueDrivers: fd.getAll("valueDriver"),
        successState: fd.get("successState") || "",
        plan: {
            step1: {
                title: fd.get("step1Title") || "",
                body: fd.get("step1Body") || "",
            },
            step2: {
                title: fd.get("step2Title") || "",
                body: fd.get("step2Body") || "",
            },
            step3: {
                title: fd.get("step3Title") || "",
                body: fd.get("step3Body") || "",
            },
        },
        callToAction: fd.get("callToAction") || "",
        sections: sectionsData,
        projects: fd.getAll("project"),
        proposals,
    };
}

function showOverlay(msg, sub) {
    document.getElementById("overlayMsg").textContent = msg;
    document.getElementById("overlaySub").textContent = sub || "";
    document.getElementById("statusOverlay").classList.remove("hidden");
}
function hideOverlay() {
    document.getElementById("statusOverlay").classList.add("hidden");
}
