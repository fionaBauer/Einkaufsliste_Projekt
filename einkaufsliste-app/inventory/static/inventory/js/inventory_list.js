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

    function initializeIngredientSearch(modalElement, datalistId) {
        const searchInput = modalElement?.querySelector(".ingredient-search-input");
        const hiddenIngredientInput = modalElement?.querySelector('input[name="ingredient"]');
        const datalist = modalElement?.querySelector(`#${datalistId}`);

        if (!searchInput || !hiddenIngredientInput || !datalist) {
            return;
        }

        searchInput.setAttribute("list", datalistId);

        function syncIngredientId() {
            const typedValue = searchInput.value.trim().toLowerCase();
            const options = Array.from(datalist.querySelectorAll("option"));

            const match = options.find(
                (option) => option.value.trim().toLowerCase() === typedValue
            );

            if (match) {
                hiddenIngredientInput.value = match.dataset.id || "";
            } else {
                hiddenIngredientInput.value = "";
            }
        }

        searchInput.addEventListener("input", syncIngredientId);
        searchInput.addEventListener("change", syncIngredientId);

        syncIngredientId();
    }

    if (openCreateModalBtn) {
        openCreateModalBtn.addEventListener("click", () => {
            createModal.classList.add("active");
            initializeIngredientSearch(createModal, "inventory-ingredient-options-create");
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
            const editIngredientHidden = editModal.querySelector('input[name="ingredient"]');
            const editIngredientSearch = editModal.querySelector(".ingredient-search-input");
            const editQuantity = editModal.querySelector('[name="quantity"]');
            const editUnit = editModal.querySelector('[name="unit"]');

            if (editItemIdInput) {
                editItemIdInput.value = button.dataset.id;
            }

            if (editIngredientHidden) {
                editIngredientHidden.value = button.dataset.ingredient || "";
            }

            if (editIngredientSearch) {
                const selectedOption = editModal.querySelector(
                    `#inventory-ingredient-options-edit option[data-id="${button.dataset.ingredient}"]`
                );
                editIngredientSearch.value = selectedOption ? selectedOption.value : "";
            }

            if (editQuantity) {
                editQuantity.value = button.dataset.quantity || "";
            }

            if (editUnit) {
                editUnit.value = button.dataset.unit || "";
            }

            editModal.classList.add("active");
            initializeIngredientSearch(editModal, "inventory-ingredient-options-edit");
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
            return;
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
                const hiddenIngredientInput = activeInventoryFormContainer?.querySelector('input[name="ingredient"]');
                const ingredientSearchInput = activeInventoryFormContainer?.querySelector(".ingredient-search-input");
                const unitSelect = activeInventoryFormContainer?.querySelector('select[name="unit"]');
                const createDatalist = activeInventoryFormContainer?.querySelector("#inventory-ingredient-options-create");
                const editDatalist = activeInventoryFormContainer?.querySelector("#inventory-ingredient-options-edit");
                const activeDatalist = createDatalist || editDatalist;

                if (hiddenIngredientInput) {
                    hiddenIngredientInput.value = String(data.ingredient.id);
                }

                if (ingredientSearchInput) {
                    ingredientSearchInput.value = data.ingredient.name;
                }

                if (activeDatalist) {
                    const option = document.createElement("option");
                    option.value = data.ingredient.name;
                    option.dataset.id = data.ingredient.id;
                    activeDatalist.appendChild(option);
                }

                if (unitSelect && data.ingredient.default_unit) {
                    unitSelect.value = data.ingredient.default_unit;
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
            if (ingredientCreateModal?.classList.contains("active")) {
                ingredientCreateModal.classList.remove("active");
                ingredientCreateModalBody.innerHTML = "";
                return;
            }

            createModal?.classList.remove("active");
            editModal?.classList.remove("active");
        }
    });
});