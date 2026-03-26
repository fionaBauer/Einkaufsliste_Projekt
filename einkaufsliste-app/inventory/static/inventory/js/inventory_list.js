document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const editModal = document.getElementById("editModal");

    const ingredientCreateModal = document.getElementById("ingredientCreateModal");
    const ingredientCreateModalBody = document.getElementById("ingredientCreateModalBody");

    const openCreateModalBtn = document.getElementById("openCreateModalBtn");
    const closeCreateModalBtn = document.getElementById("closeCreateModalBtn");
    const closeEditModalBtn = document.getElementById("closeEditModalBtn");

    const editButtons = document.querySelectorAll(".open-edit-modal-btn");
    const editItemIdInput = document.getElementById("editItemId");

    let activeInventoryFormContainer = null;

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

    document.addEventListener("click", async (event) => {
        const ingredientCreateTrigger = event.target.closest(".open-ingredient-create-btn");
        if (ingredientCreateTrigger) {
            activeInventoryFormContainer = ingredientCreateTrigger.closest(".modal");

            try {
                const response = await fetch(ingredientCreateTrigger.dataset.url, {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });

                const data = await response.json();
                ingredientCreateModalBody.innerHTML = data.html;
                ingredientCreateModal.classList.add("active");
            } catch (error) {
                console.error(error);
                alert("Ingredient-Modal konnte nicht geladen werden.");
            }
        }

        const ingredientCloseButton = event.target.closest(".ingredient-modal-close-btn");
        if (ingredientCloseButton) {
            ingredientCreateModal.classList.remove("active");
            ingredientCreateModalBody.innerHTML = "";
        }
    });

    document.addEventListener("submit", async (event) => {
        const form = event.target;

        if (!ingredientCreateModalBody.contains(form)) {
            return;
        }

        event.preventDefault();

        const formData = new FormData(form);

        try {
            const response = await fetch(form.action, {
                method: form.method || "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            const data = await response.json();

            if (data.success) {
                const ingredientSelect = activeInventoryFormContainer?.querySelector('select[name="ingredient"]');

                if (ingredientSelect) {
                    const option = document.createElement("option");
                    option.value = data.ingredient.id;
                    option.textContent = data.ingredient.name;
                    option.selected = true;
                    ingredientSelect.appendChild(option);
                    ingredientSelect.value = String(data.ingredient.id);
                }

                ingredientCreateModal.classList.remove("active");
                ingredientCreateModalBody.innerHTML = "";
                return;
            }

            ingredientCreateModalBody.innerHTML = data.html;
            ingredientCreateModal.classList.add("active");
        } catch (error) {
            console.error(error);
            alert("Beim Speichern der neuen Zutat ist ein Fehler aufgetreten.");
        }
    });

    [createModal, editModal, ingredientCreateModal].forEach((modal) => {
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
            ingredientCreateModal?.classList.remove("active");
        }
    });
});