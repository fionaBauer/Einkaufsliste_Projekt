function initCategoryToggle() {
    const grid = document.getElementById("category-grid");
    const details = document.querySelectorAll(".category-detail");

    function showGrid() {
        grid && grid.classList.remove("hidden");
        details.forEach(d => d.classList.add("hidden"));
    }

    function showDetail(categoryValue) {
        grid && grid.classList.add("hidden");
        details.forEach(d => d.classList.add("hidden"));
        const detail = document.querySelector(`.category-detail[data-category="${categoryValue}"]`);
        if (detail) detail.classList.remove("hidden");
    }

    document.querySelectorAll(".category-card").forEach(card => {
        card.addEventListener("click", () => showDetail(card.dataset.category));
    });

    document.querySelectorAll(".detail-back-btn").forEach(btn => {
        btn.addEventListener("click", showGrid);
    });
}

function getOpenCategory() {
    const openDetail = document.querySelector(".category-detail:not(.hidden)");
    return openDetail ? openDetail.dataset.category : null;
}

function showCategoryByValue(categoryValue) {
    const grid = document.getElementById("category-grid");
    const details = document.querySelectorAll(".category-detail");

    if (!categoryValue) {
        grid && grid.classList.remove("hidden");
        details.forEach(d => d.classList.add("hidden"));
        return;
    }

    const detail = document.querySelector(`.category-detail[data-category="${categoryValue}"]`);
    if (!detail) {
        // Kategorie hat jetzt keine Einträge mehr (z.B. letzte Zutat verschoben/gelöscht) -> zurück zur Übersicht
        grid && grid.classList.remove("hidden");
        details.forEach(d => d.classList.add("hidden"));
        return;
    }

    grid && grid.classList.add("hidden");
    details.forEach(d => d.classList.add("hidden"));
    detail.classList.remove("hidden");
}

function replaceIngredientListSection(html, previousCategory) {
    const sectionEl = document.getElementById("ingredient-list-section");
    if (!sectionEl) return;
    sectionEl.outerHTML = html;
    initCategoryToggle();
    showCategoryByValue(previousCategory);
}

document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const editModal = document.getElementById("editModal");

    const openCreateModalBtn = document.getElementById("openCreateModalBtn");
    const closeCreateModalBtn = document.getElementById("closeCreateModalBtn");
    const closeEditModalBtn = document.getElementById("closeEditModalBtn");

    const editIngredientId = document.getElementById("editIngredientId");
    const editName = document.getElementById("edit_name");
    const editCategory = document.getElementById("edit_category");

    initCategoryToggle();

    if (openCreateModalBtn) {
        openCreateModalBtn.addEventListener("click", () => createModal.classList.add("active"));
    }
    if (closeCreateModalBtn) {
        closeCreateModalBtn.addEventListener("click", () => createModal.classList.remove("active"));
    }
    if (closeEditModalBtn) {
        closeEditModalBtn.addEventListener("click", () => editModal.classList.remove("active"));
    }

    // Use event delegation for edit buttons (works after category-detail render)
    document.addEventListener("click", e => {
        const btn = e.target.closest(".open-edit-modal-btn");
        if (!btn) return;
        if (editIngredientId) editIngredientId.value = btn.dataset.id;
        if (editName) editName.value = btn.dataset.name || "";
        if (editCategory) editCategory.value = btn.dataset.category || "";
        editModal.classList.add("active");
    });

    // AJAX submit for edit and delete — stay on same category view
    document.addEventListener("submit", async e => {
        const form = e.target;

        // Edit form
        if (form.closest("#editModal")) {
            e.preventDefault();
            const formData = new FormData(form);
            const previousCategory = getOpenCategory();
            try {
                const res = await fetch(window.location.href, {
                    method: "POST", body: formData,
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                const ct = res.headers.get("content-type") || "";
                if (!ct.includes("application/json")) {
                    throw new Error(`Unerwartete Serverantwort (Status ${res.status}).`);
                }
                const data = await res.json();
                if (data.success) {
                    editModal.classList.remove("active");
                    if (data.section_html) {
                        replaceIngredientListSection(data.section_html, previousCategory);
                    }
                } else {
                    const messages = Object.values(data.errors || {})
                        .flat()
                        .map(err => err.message || err)
                        .join(" ");
                    alert(messages || "Speichern fehlgeschlagen. Bitte Eingaben prüfen.");
                }
            } catch(err) {
                console.error(err);
                alert("Beim Speichern ist ein Fehler aufgetreten. Bitte versuche es erneut.");
            }
            return;
        }

        // Delete form
        if (form.classList.contains("delete-form")) {
            e.preventDefault();
            if (!confirm("Zutat löschen?")) return;
            const formData = new FormData(form);
            const previousCategory = getOpenCategory();
            try {
                const res = await fetch(window.location.href, {
                    method: "POST", body: formData,
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                const ct = res.headers.get("content-type") || "";
                if (!ct.includes("application/json")) {
                    throw new Error(`Unerwartete Serverantwort (Status ${res.status}).`);
                }
                const data = await res.json();
                if (data.success && data.section_html) {
                    replaceIngredientListSection(data.section_html, previousCategory);
                }
            } catch(err) {
                console.error(err);
                alert("Beim Löschen ist ein Fehler aufgetreten. Bitte versuche es erneut.");
            }
            return;
        }
    });

    [createModal, editModal].forEach(modal => {
        if (!modal) return;
        modal.addEventListener("click", e => { if (e.target === modal) modal.classList.remove("active"); });
    });

    document.addEventListener("keydown", e => {
        if (e.key === "Escape") {
            createModal?.classList.remove("active");
            editModal?.classList.remove("active");
        }
    });
});
