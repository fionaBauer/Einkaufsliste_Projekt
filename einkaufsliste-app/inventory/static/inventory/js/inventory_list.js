document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const editModal = document.getElementById("editModal");

    const openCreateModalBtn = document.getElementById("openCreateModalBtn");
    const closeCreateModalBtn = document.getElementById("closeCreateModalBtn");
    const closeEditModalBtn = document.getElementById("closeEditModalBtn");

    const editButtons = document.querySelectorAll(".open-edit-modal-btn");

    const editItemIdInput = document.getElementById("editItemId");

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
            const editIngredient = editModal.querySelector('[name="ingredient"]');
            const editQuantity = editModal.querySelector('[name="quantity"]');
            const editUnit = editModal.querySelector('[name="unit"]');

            editItemIdInput.value = button.dataset.id;
            editIngredient.value = button.dataset.ingredient;
            editQuantity.value = button.dataset.quantity;
            editUnit.value = button.dataset.unit;

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
});