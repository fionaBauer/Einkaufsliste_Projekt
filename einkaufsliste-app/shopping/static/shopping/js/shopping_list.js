document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const openCreateModalBtn = document.getElementById("openCreateModalBtn");
    const closeCreateModalBtn = document.getElementById("closeCreateModalBtn");

    const ingredientCreateModal = document.getElementById("ingredientCreateModal");
    const ingredientCreateModalBody = document.getElementById("ingredientCreateModalBody");

    let activeShoppingForm = null;

    function openCreateModal() {
        createModal?.classList.add("active");
        initializeShoppingIngredientSearch();
    }

    function closeCreateModal() {
        createModal?.classList.remove("active");
    }

    function openIngredientCreateModal() {
        ingredientCreateModal?.classList.add("active");
    }

    function closeIngredientCreateModal() {
        ingredientCreateModal?.classList.remove("active");
        if (ingredientCreateModalBody) {
            ingredientCreateModalBody.innerHTML = "";
        }
    }

    function initializeShoppingIngredientSearch() {
        const formContainer = createModal;
        const searchInput = formContainer?.querySelector(".ingredient-search-input");
        const hiddenIngredientInput = formContainer?.querySelector('input[name="ingredient"]');
        const datalist = formContainer?.querySelector("#shopping-ingredient-options");

        if (!searchInput || !hiddenIngredientInput || !datalist) {
            return;
        }

        searchInput.setAttribute("list", "shopping-ingredient-options");

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
            openCreateModal();
        });
    }

    if (closeCreateModalBtn) {
        closeCreateModalBtn.addEventListener("click", () => {
            closeCreateModal();
        });
    }

    createModal?.addEventListener("click", (event) => {
        if (event.target === createModal) {
            closeCreateModal();
        }
    });

    ingredientCreateModal?.addEventListener("click", (event) => {
        if (event.target === ingredientCreateModal) {
            closeIngredientCreateModal();
        }
    });

    document.addEventListener("click", async (event) => {
        const ingredientCreateTrigger = event.target.closest(".open-ingredient-create-btn");
        if (ingredientCreateTrigger) {
            activeShoppingForm = createModal;

            try {
                const response = await fetch(ingredientCreateTrigger.dataset.url, {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });

                const data = await response.json();
                ingredientCreateModalBody.innerHTML = data.html;
                openIngredientCreateModal();
            } catch (error) {
                console.error(error);
                alert("Ingredient-Modal konnte nicht geladen werden.");
            }
            return;
        }

        const ingredientCloseButton = event.target.closest(".ingredient-modal-close-btn");
        if (ingredientCloseButton) {
            closeIngredientCreateModal();
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
                const hiddenIngredientInput = activeShoppingForm?.querySelector('input[name="ingredient"]');
                const ingredientSearchInput = activeShoppingForm?.querySelector(".ingredient-search-input");
                const datalist = activeShoppingForm?.querySelector("#shopping-ingredient-options");
                const unitSelect = activeShoppingForm?.querySelector('select[name="unit"]');

                if (hiddenIngredientInput) {
                    hiddenIngredientInput.value = String(data.ingredient.id);
                }

                if (ingredientSearchInput) {
                    ingredientSearchInput.value = data.ingredient.name;
                }

                if (datalist) {
                    const option = document.createElement("option");
                    option.value = data.ingredient.name;
                    option.dataset.id = data.ingredient.id;
                    datalist.appendChild(option);
                }

                if (unitSelect && data.ingredient.default_unit) {
                    unitSelect.value = data.ingredient.default_unit;
                }

                closeIngredientCreateModal();
                return;
            }

            ingredientCreateModalBody.innerHTML = data.html;
            openIngredientCreateModal();
        } catch (error) {
            console.error(error);
            alert("Beim Speichern der neuen Zutat ist ein Fehler aufgetreten.");
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            if (ingredientCreateModal?.classList.contains("active")) {
                closeIngredientCreateModal();
                return;
            }

            if (createModal?.classList.contains("active")) {
                closeCreateModal();
            }
        }
    });
});