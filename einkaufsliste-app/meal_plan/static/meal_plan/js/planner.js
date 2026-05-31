document.addEventListener("DOMContentLoaded", function () {
/* ── State ── */
const configEl = document.getElementById("meal-plan-config");
const recipesEl = document.getElementById("meal-plan-recipes");

if (!configEl || !recipesEl) {
    throw new Error("Meal plan configuration is missing.");
}

const recipes = JSON.parse(recipesEl.textContent || "[]");
const csrfToken = configEl.dataset.csrfToken;
const urls = {
    slots: configEl.dataset.slotsUrl,
    create: configEl.dataset.createUrl,
    update: configEl.dataset.updateUrl.replace("/0/", "/{id}/"),
    del: configEl.dataset.deleteUrl.replace("/0/", "/{id}/"),
    shopping: configEl.dataset.shoppingUrl,
    recipeDetail: configEl.dataset.recipeDetailUrl.replace("/0/", "/{id}/"),
};
const MEALS = ["breakfast", "lunch", "dinner"];
const MEAL_LABELS = { breakfast: "Früh", lunch: "Mittag", dinner: "Abend" };
const MEAL_ICONS = { breakfast: "☀️", lunch: "🌤️", dinner: "🌙" };
const DAY_NAMES = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const MONTH_NAMES = ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"];

let currentView = "week";
let currentDate = new Date();
let slots = [];
let dragSlot = null;
let pendingAdd = null;
let editingSlot = null;

/* ── API helpers ── */
const api = {
    async get(url) {
        const r = await fetch(url); return r.json();
    },
    async post(url, body) {
        const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken }, body: JSON.stringify(body) });
        return r.json();
    },
    async patch(url, body) {
        const r = await fetch(url, { method: "PATCH", headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken }, body: JSON.stringify(body) });
        return r.json();
    },
    async del(url) {
        const r = await fetch(url, { method: "DELETE", headers: { "X-CSRFToken": csrfToken } });
        return r.json();
    },
};

/* ── Date helpers ── */
function isoDate(d) {
    return d.toISOString().split("T")[0];
}

function startOfWeek(d) {
    const day = new Date(d);
    const dow = day.getDay();
    const diff = dow === 0 ? -6 : 1 - dow;
    day.setDate(day.getDate() + diff);
    return day;
}

function addDays(d, n) {
    const r = new Date(d);
    r.setDate(r.getDate() + n);
    return r;
}

function isToday(d) {
    const t = new Date();
    return d.getFullYear() === t.getFullYear() && d.getMonth() === t.getMonth() && d.getDate() === t.getDate();
}

function weekRange() {
    const mon = startOfWeek(currentDate);
    const sun = addDays(mon, 6);
    return { start: mon, end: sun };
}

function monthRange() {
    const y = currentDate.getFullYear(), m = currentDate.getMonth();
    return { start: new Date(y, m, 1), end: new Date(y, m + 1, 0) };
}

/* ── Load slots ── */
async function loadSlots(start, end) {
    const data = await api.get(`${urls.slots}?start=${isoDate(start)}&end=${isoDate(end)}`);
    slots = data;
}

/* ── Render ── */
async function render() {
    if (currentView === "week") {
        const { start, end } = weekRange();
        await loadSlots(start, end);
        renderWeek(start);
        renderPeriodLabel();
    } else {
        const { start, end } = monthRange();
        await loadSlots(addDays(start, -7), addDays(end, 7));
        renderMonth();
        renderPeriodLabel();
    }
}

function renderPeriodLabel() {
    const el = document.getElementById("period-label");
    if (currentView === "week") {
        const { start, end } = weekRange();
        const s = `${start.getDate()}. ${MONTH_NAMES[start.getMonth()].slice(0,3)}`;
        const e = `${end.getDate()}. ${MONTH_NAMES[end.getMonth()].slice(0,3)} ${end.getFullYear()}`;
        el.textContent = `${s} – ${e}`;
    } else {
        const y = currentDate.getFullYear(), m = currentDate.getMonth();
        el.textContent = `${MONTH_NAMES[m]} ${y}`;
    }
}

function slotsFor(dateStr, meal) {
    return slots.filter(s => s.date === dateStr && s.meal === meal);
}

/* ── Week View ── */
function renderWeek(mon) {
    const grid = document.getElementById("week-view");
    grid.innerHTML = "";

    const corner = mkEl("div", "corner-cell");
    grid.appendChild(corner);

    for (let i = 0; i < 7; i++) {
        const day = addDays(mon, i);
        const hdr = mkEl("div", `day-header${isToday(day) ? " today" : ""}`);
        hdr.innerHTML = `<div class="day-header-name">${DAY_NAMES[i]}</div><div class="day-header-date">${day.getDate()}</div>`;
        grid.appendChild(hdr);
    }

    MEALS.forEach((meal, mi) => {
        const isLastRow = mi === MEALS.length - 1;

        const lbl = mkEl("div", `meal-label-cell${isLastRow ? " last-row" : ""}`);
        lbl.textContent = MEAL_LABELS[meal];
        grid.appendChild(lbl);

        for (let i = 0; i < 7; i++) {
            const day = addDays(mon, i);
            const dateStr = isoDate(day);
            const isLastCol = i === 6;
            const cell = mkEl("div", `slot-cell${isLastCol ? " last-col" : ""}${isLastRow ? " last-row" : ""}`);
            cell.dataset.date = dateStr;
            cell.dataset.meal = meal;

            slotsFor(dateStr, meal).forEach(slot => {
                cell.appendChild(makeChip(slot));
            });

            const addBtn = mkEl("button", "slot-add-btn");
            addBtn.textContent = "+";
            addBtn.title = `${MEAL_LABELS[meal]} hinzufügen`;
            addBtn.addEventListener("click", () => openAddModal(dateStr, meal));
            cell.appendChild(addBtn);

            cell.addEventListener("dragover", onDragOver);
            cell.addEventListener("dragleave", onDragLeave);
            cell.addEventListener("drop", onDrop);

            grid.appendChild(cell);
        }
    });
}

/* ── Month View ── */
function renderMonth() {
    const grid = document.getElementById("month-view");
    grid.innerHTML = "";
    const y = currentDate.getFullYear(), m = currentDate.getMonth();

    DAY_NAMES.forEach(n => {
        const h = mkEl("div", "month-day-header");
        h.textContent = n;
        grid.appendChild(h);
    });

    const firstDay = new Date(y, m, 1);
    const startDow = firstDay.getDay();
    const startOffset = startDow === 0 ? 6 : startDow - 1;

    for (let i = 0; i < startOffset; i++) {
        const prev = new Date(y, m, 1 - startOffset + i);
        const cell = mkEl("div", "month-day-cell other-month");
        const num = mkEl("div", "month-day-num");
        num.textContent = prev.getDate();
        cell.appendChild(num);
        grid.appendChild(cell);
    }

    const daysInMonth = new Date(y, m + 1, 0).getDate();
    for (let d = 1; d <= daysInMonth; d++) {
        const day = new Date(y, m, d);
        const dateStr = isoDate(day);
        const cell = mkEl("div", `month-day-cell${isToday(day) ? " today" : ""}`);
        cell.dataset.date = dateStr;

        const num = mkEl("div", "month-day-num");
        num.textContent = d;
        cell.appendChild(num);

        MEALS.forEach(meal => {
            slotsFor(dateStr, meal).forEach(slot => {
                const chip = mkEl("div", "month-chip");
                chip.textContent = `${MEAL_ICONS[meal]} ${slot.recipe_name}`;
                chip.title = slot.recipe_name;
                chip.addEventListener("click", () => openSlotModal(slot));
                cell.appendChild(chip);
            });
        });

        const addBtn = mkEl("button", "month-add-btn");
        addBtn.textContent = "+ Hinzufügen";
        addBtn.addEventListener("click", () => openAddModal(dateStr, "lunch"));
        cell.appendChild(addBtn);

        grid.appendChild(cell);
    }

    const totalCells = startOffset + daysInMonth;
    const remainder = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
    for (let i = 1; i <= remainder; i++) {
        const next = new Date(y, m + 1, i);
        const cell = mkEl("div", "month-day-cell other-month");
        const num = mkEl("div", "month-day-num");
        num.textContent = next.getDate();
        cell.appendChild(num);
        grid.appendChild(cell);
    }
}

/* ── Chip builder ── */
function makeChip(slot) {
    const chip = mkEl("div", "recipe-chip");
    chip.dataset.slotId = slot.id;
    chip.draggable = true;

    if (slot.recipe_image) {
        const img = document.createElement("img");
        img.src = slot.recipe_image;
        img.className = "recipe-chip-thumb";
        chip.appendChild(img);
    } else {
        const icon = mkEl("span", "recipe-chip-icon");
        icon.textContent = MEAL_ICONS[slot.meal] || "🍽️";
        chip.appendChild(icon);
    }

    const name = mkEl("span", "recipe-chip-name");
    name.textContent = slot.recipe_name;
    chip.appendChild(name);

    if (slot.recurrence !== "none") {
        const badge = mkEl("span", "recurrence-badge");
        badge.textContent = slot.recurrence === "weekly" ? "W" : "M";
        badge.title = slot.recurrence === "weekly" ? "Wöchentlich" : "Monatlich";
        chip.appendChild(badge);
    }

    const settingsBtn = mkEl("button", "recipe-chip-settings");
    settingsBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>`;
    settingsBtn.title = "Einstellungen";
    settingsBtn.addEventListener("click", e => { e.stopPropagation(); openSlotModal(slot); });
    chip.appendChild(settingsBtn);

    chip.addEventListener("dragstart", e => {
        dragSlot = slot;
        chip.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
    });
    chip.addEventListener("dragend", () => {
        dragSlot = null;
        chip.classList.remove("dragging");
    });

    name.addEventListener("click", () => {
        window.location.href = urls.recipeDetail.replace("{id}", slot.recipe_id);
    });
    name.style.cursor = "pointer";

    return chip;
}

/* ── Drag & Drop ── */
function onDragOver(e) {
    if (!dragSlot) return;
    e.preventDefault();
    e.currentTarget.classList.add("drag-over");
}

function onDragLeave(e) {
    e.currentTarget.classList.remove("drag-over");
}

async function onDrop(e) {
    e.preventDefault();
    const cell = e.currentTarget;
    cell.classList.remove("drag-over");
    if (!dragSlot) return;

    const newDate = cell.dataset.date;
    const newMeal = cell.dataset.meal;

    if (newDate === dragSlot.date && newMeal === dragSlot.meal) return;

    const updateUrl = urls.update.replace("{id}", dragSlot.id);
    await api.patch(updateUrl, { date: newDate, meal: newMeal });
    await render();
}

/* ── Add Modal ── */
let selectedRecipe = null;

function openAddModal(dateStr, meal) {
    pendingAdd = { date: dateStr, meal };
    selectedRecipe = null;

    const modal = document.getElementById("add-modal");
    const meta = document.getElementById("add-modal-meta");
    meta.textContent = `${formatDateLabel(dateStr)} · ${MEAL_LABELS[meal]}`;

    document.getElementById("recipe-search").value = "";
    document.getElementById("add-recurrence").value = "none";
    document.getElementById("add-note").value = "";
    document.getElementById("recipe-dropdown").classList.add("hidden");

    modal.classList.remove("hidden");
    setTimeout(() => document.getElementById("recipe-search").focus(), 50);
}

function formatDateLabel(dateStr) {
    const d = new Date(dateStr + "T00:00:00");
    return `${DAY_NAMES[(d.getDay() + 6) % 7]}, ${d.getDate()}. ${MONTH_NAMES[d.getMonth()]}`;
}

document.getElementById("add-cancel").addEventListener("click", () => {
    document.getElementById("add-modal").classList.add("hidden");
});

document.getElementById("add-modal").addEventListener("click", e => {
    if (e.target === document.getElementById("add-modal")) {
        document.getElementById("add-modal").classList.add("hidden");
    }
});

document.getElementById("add-confirm").addEventListener("click", async () => {
    if (!selectedRecipe || !pendingAdd) return;
    const result = await api.post(urls.create, {
        recipe_id: selectedRecipe.id,
        date: pendingAdd.date,
        meal: pendingAdd.meal,
        recurrence: document.getElementById("add-recurrence").value,
        note: document.getElementById("add-note").value,
    });
    if (result.id) {
        document.getElementById("add-modal").classList.add("hidden");
        await render();
    }
});

/* Recipe search */
const recipeSearch = document.getElementById("recipe-search");
const recipeDropdown = document.getElementById("recipe-dropdown");

recipeSearch.addEventListener("input", () => {
    const q = recipeSearch.value.toLowerCase().trim();
    const matches = q.length === 0
        ? recipes
        : recipes.filter(r => r.name.toLowerCase().includes(q));

    recipeDropdown.innerHTML = "";
    if (matches.length === 0) {
        recipeDropdown.classList.add("hidden");
        return;
    }

    matches.slice(0, 10).forEach(r => {
        const opt = mkEl("div", "recipe-option");
        if (r.image) {
            const img = document.createElement("img");
            img.src = r.image;
            opt.appendChild(img);
        } else {
            const icon = mkEl("span", "recipe-option-icon");
            icon.textContent = "🍽️";
            opt.appendChild(icon);
        }
        const name = document.createElement("span");
        name.textContent = r.name;
        opt.appendChild(name);
        opt.addEventListener("click", () => {
            selectedRecipe = r;
            recipeSearch.value = r.name;
            recipeDropdown.classList.add("hidden");
        });
        recipeDropdown.appendChild(opt);
    });

    recipeDropdown.classList.remove("hidden");
});

recipeSearch.addEventListener("focus", () => {
    if (recipeSearch.value === "" && selectedRecipe) return;
    recipeSearch.dispatchEvent(new Event("input"));
});

document.addEventListener("click", e => {
    if (!recipeDropdown.contains(e.target) && e.target !== recipeSearch) {
        recipeDropdown.classList.add("hidden");
    }
});

/* ── Slot Settings Modal ── */
function openSlotModal(slot) {
    editingSlot = slot;
    document.getElementById("slot-modal-title").textContent = slot.recipe_name;
    document.getElementById("slot-modal-date").textContent = `${formatDateLabel(slot.date)} · ${slot.meal_label}`;
    document.getElementById("slot-recurrence").value = slot.recurrence;
    document.getElementById("slot-note").value = slot.note || "";
    document.getElementById("slot-modal").classList.remove("hidden");
}

document.getElementById("slot-cancel").addEventListener("click", () => {
    document.getElementById("slot-modal").classList.add("hidden");
    editingSlot = null;
});

document.getElementById("slot-modal").addEventListener("click", e => {
    if (e.target === document.getElementById("slot-modal")) {
        document.getElementById("slot-modal").classList.add("hidden");
        editingSlot = null;
    }
});

document.getElementById("slot-save").addEventListener("click", async () => {
    if (!editingSlot) return;
    const updateUrl = urls.update.replace("{id}", editingSlot.id);
    await api.patch(updateUrl, {
        recurrence: document.getElementById("slot-recurrence").value,
        note: document.getElementById("slot-note").value,
    });
    document.getElementById("slot-modal").classList.add("hidden");
    editingSlot = null;
    await render();
});

document.getElementById("slot-delete").addEventListener("click", async () => {
    if (!editingSlot) return;
    if (!confirm(`"${editingSlot.recipe_name}" aus dem Plan entfernen?`)) return;
    const deleteUrl = urls.del.replace("{id}", editingSlot.id);
    await api.del(deleteUrl);
    document.getElementById("slot-modal").classList.add("hidden");
    editingSlot = null;
    await render();
});

/* ── Shopping list ── */
document.getElementById("create-shopping-btn").addEventListener("click", async () => {
    const { start, end } = currentView === "week" ? weekRange() : monthRange();
    const btn = document.getElementById("create-shopping-btn");
    btn.textContent = "Wird erstellt…";
    btn.disabled = true;
    try {
        const result = await api.post(urls.shopping, {
            start: isoDate(start),
            end: isoDate(end),
        });
        if (result.shopping_list_id) {
            window.location.href = `/shopping/${result.shopping_list_id}/`;
        }
    } finally {
        btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg> Einkaufsliste`;
        btn.disabled = false;
    }
});

/* ── View toggle ── */
document.querySelectorAll(".view-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".view-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentView = btn.dataset.view;
        document.getElementById("week-view").classList.toggle("hidden", currentView !== "week");
        document.getElementById("month-view").classList.toggle("hidden", currentView !== "month");
        render();
    });
});

/* ── Navigation ── */
document.getElementById("prev-btn").addEventListener("click", () => {
    if (currentView === "week") {
        currentDate = addDays(currentDate, -7);
    } else {
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1);
    }
    render();
});

document.getElementById("next-btn").addEventListener("click", () => {
    if (currentView === "week") {
        currentDate = addDays(currentDate, 7);
    } else {
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
    }
    render();
});

/* ── Helper ── */
function mkEl(tag, cls) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    return e;
}

/* ── Init ── */
render();

});