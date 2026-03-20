document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const editModal = document.getElementById("editModal");

    const openCreateModalBtn = document.getElementById("openCreateModalBtn");
    const closeCreateModalBtn = document.getElementById("closeCreateModalBtn");
    const closeEditModalBtn = document.getElementById("closeEditModalBtn");

    const editIngredientIdInput = document.getElementById("editIngredientId");
    const editNameInput = document.getElementById("edit_name");
    const editUnitInput = document.getElementById("edit_default_unit");

    if (openCreateModalBtn) {
        openCreateModalBtn.addEventListener("click", () => {
            createModal.classList.add("active");
        });
    }

    if (closeCreateModalBtn) {
        closeCreateModalBtn.addEventListener("click", () => {
            createModal.classList.remove("active");
        });
    }

    if (closeEditModalBtn) {
        closeEditModalBtn.addEventListener("click", () => {
            editModal.classList.remove("active");
        });
    }

    if (createModal) {
        createModal.addEventListener("click", (event) => {
            if (event.target === createModal) {
                createModal.classList.remove("active");
            }
        });
    }

    if (editModal) {
        editModal.addEventListener("click", (event) => {
            if (event.target === editModal) {
                editModal.classList.remove("active");
            }
        });
    }

    document.querySelectorAll(".open-edit-modal-btn").forEach((button) => {
        button.addEventListener("click", () => {
            const ingredientId = button.dataset.id;
            const ingredientName = button.dataset.name;
            const ingredientUnit = button.dataset.unit;

            editIngredientIdInput.value = ingredientId;
            editNameInput.value = ingredientName;
            editUnitInput.value = ingredientUnit;

            editModal.classList.add("active");
        });
    });
});