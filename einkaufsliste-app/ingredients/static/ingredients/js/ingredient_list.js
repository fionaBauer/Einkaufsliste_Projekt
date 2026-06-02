document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const editModal = document.getElementById("editModal");

    const openCreateModalBtn = document.getElementById("openCreateModalBtn");
    const closeCreateModalBtn = document.getElementById("closeCreateModalBtn");
    const closeEditModalBtn = document.getElementById("closeEditModalBtn");

    const editIngredientId = document.getElementById("editIngredientId");
    const editName = document.getElementById("edit_name");
    const editCategory = document.getElementById("edit_category");

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
            try {
                const res = await fetch(window.location.href, {
                    method: "POST", body: formData,
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await res.json();
                if (data.success) {
                    editModal.classList.remove("active");
                    // Update name in the detail list
                    const ingId = form.querySelector('[name="ingredient_id"]')?.value;
                    const newName = form.querySelector('[name="name"]')?.value;
                    if (ingId && newName) {
                        document.querySelectorAll(`.open-edit-modal-btn[data-id="${ingId}"]`).forEach(b => {
                            b.dataset.name = newName;
                            const nameEl = b.closest(".ingredient-item")?.querySelector(".ingredient-name");
                            if (nameEl) nameEl.textContent = newName;
                        });
                    }
                }
            } catch(err) { console.error(err); }
            return;
        }

        // Delete form
        if (form.classList.contains("delete-form")) {
            e.preventDefault();
            if (!confirm("Zutat löschen?")) return;
            const formData = new FormData(form);
            try {
                const res = await fetch(window.location.href, {
                    method: "POST", body: formData,
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await res.json();
                if (data.success) {
                    form.closest(".ingredient-item")?.remove();
                }
            } catch(err) { console.error(err); }
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