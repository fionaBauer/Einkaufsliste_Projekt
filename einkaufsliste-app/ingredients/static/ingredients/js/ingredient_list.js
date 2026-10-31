// Kategorie-Übersicht/-Details und das stille Speichern der Formulare übernimmt
// global/js/app.js – hier nur noch die Modals.
document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const editModal = document.getElementById("editModal");

    document.addEventListener("click", (event) => {
        if (event.target.closest("#openCreateModalBtn")) {
            createModal.classList.add("active");
            setTimeout(() => document.getElementById("create_name")?.focus(), 80);
            return;
        }

        if (event.target.closest("#closeCreateModalBtn") || event.target === createModal) {
            createModal.classList.remove("active");
            return;
        }

        if (event.target.closest("#closeEditModalBtn") || event.target === editModal) {
            editModal.classList.remove("active");
            return;
        }

        const editButton = event.target.closest(".open-edit-modal-btn");
        if (editButton) {
            document.getElementById("editIngredientId").value = editButton.dataset.id;
            document.getElementById("edit_name").value = editButton.dataset.name || "";
            document.getElementById("edit_category").value = editButton.dataset.category || "";
            editModal.classList.add("active");
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            createModal?.classList.remove("active");
            editModal?.classList.remove("active");
        }
    });
});
