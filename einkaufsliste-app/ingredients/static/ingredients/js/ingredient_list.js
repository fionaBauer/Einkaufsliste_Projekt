document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const editModal = document.getElementById("editModal");

    const openCreateModalBtn = document.getElementById("openCreateModalBtn");
    const closeCreateModalBtn = document.getElementById("closeCreateModalBtn");
    const closeEditModalBtn = document.getElementById("closeEditModalBtn");

    const editButtons = document.querySelectorAll(".open-edit-modal-btn");

    const editIngredientId = document.getElementById("editIngredientId");
    const editName = document.getElementById("edit_name");
    const editCategory = document.getElementById("edit_category");

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

    editButtons.forEach((button) => {
        button.addEventListener("click", () => {
            if (editIngredientId) {
                editIngredientId.value = button.dataset.id;
            }
            if (editName) {
                editName.value = button.dataset.name || "";
            }
            if (editCategory) {
                editCategory.value = button.dataset.category || "";
            }

            editModal.classList.add("active");
        });
    });

    [createModal, editModal].forEach((modal) => {
        if (!modal) return;

        modal.addEventListener("click", (event) => {
            if (event.target === modal) {
                modal.classList.remove("active");
            }
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            createModal?.classList.remove("active");
            editModal?.classList.remove("active");
        }
    });
});