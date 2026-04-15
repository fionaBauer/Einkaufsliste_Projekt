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

    const consumeRecipeModal = document.getElementById("consumeRecipeModal");
    const openConsumeRecipeModalBtn = document.getElementById("openConsumeRecipeModalBtn");
    const closeConsumeRecipeModalBtn = document.getElementById("closeConsumeRecipeModalBtn");
    const loadConsumeRecipePreviewBtn = document.getElementById("loadConsumeRecipePreviewBtn");
    const consumeRecipeSearchInput = document.getElementById("consume_recipe_search");
    const consumeRecipeIdInput = document.getElementById("consume_recipe_id");
    const consumeRecipeOptions = document.getElementById("consume-recipe-options");
    const consumeServingsInput = document.getElementById("consume_servings");
    const consumeRecipePreviewContainer = document.getElementById("consumeRecipePreviewContainer");

    const applyConsumeRecipeBtn = document.getElementById("applyConsumeRecipeBtn");

    let activeInventoryFormContainer = null;

    function initializeIngredientSearch(modalElement, dropdownId) {
        const searchInput = modalElement?.querySelector(".ingredient-search-input");
        const hiddenIngredientInput = modalElement?.querySelector('input[name="ingredient"]');
        const dropdown = modalElement?.querySelector(`#${dropdownId}`);

        if (!searchInput || !hiddenIngredientInput || !dropdown) {
            return;
        }

        const allOptions = Array.from(dropdown.querySelectorAll(".custom-search-option"));

        function renderFilteredOptions() {
            const typedValue = searchInput.value.trim().toLowerCase();
            let visibleCount = 0;

            allOptions.forEach((option) => {
                const name = (option.dataset.name || option.textContent || "").toLowerCase();
                const matches = !typedValue || name.includes(typedValue);

                option.classList.toggle("hidden", !matches);

                if (matches) {
                    visibleCount += 1;
                }
            });

            dropdown.classList.toggle("hidden", visibleCount === 0);
        }

        function syncIngredientId() {
            const typedValue = searchInput.value.trim().toLowerCase();

            const match = allOptions.find(
                (option) =>
                    ((option.dataset.name || option.textContent || "").trim().toLowerCase() === typedValue)
            );

            if (match) {
                hiddenIngredientInput.value = match.dataset.id || "";
            } else {
                hiddenIngredientInput.value = "";
            }
        }

        searchInput.onfocus = () => {
            renderFilteredOptions();
        };

        searchInput.oninput = () => {
            syncIngredientId();
            renderFilteredOptions();
        };

        searchInput.onchange = () => {
            syncIngredientId();
            renderFilteredOptions();
        };

        allOptions.forEach((option) => {
            option.onclick = () => {
                searchInput.value = option.dataset.name || option.textContent || "";
                hiddenIngredientInput.value = option.dataset.id || "";
                dropdown.classList.add("hidden");
            };
        });

        document.addEventListener("click", (event) => {
            if (!modalElement.contains(event.target)) {
                dropdown.classList.add("hidden");
            }
        });

        syncIngredientId();
        dropdown.classList.add("hidden");
    }

    if (openCreateModalBtn) {
        openCreateModalBtn.addEventListener("click", () => {
            createModal.classList.add("active");
            initializeIngredientSearch(createModal, "inventoryIngredientDropdownCreate");
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

    if (openConsumeRecipeModalBtn) {
        openConsumeRecipeModalBtn.addEventListener("click", () => {
            openConsumeRecipeModal();
        });
    }

    if (closeConsumeRecipeModalBtn) {
        closeConsumeRecipeModalBtn.addEventListener("click", () => {
            closeConsumeRecipeModal();
        });
    }

    if (loadConsumeRecipePreviewBtn) {
        loadConsumeRecipePreviewBtn.addEventListener("click", async () => {
            const recipeId = consumeRecipeIdInput?.value;
            const servings = consumeServingsInput?.value || "1";

            if (!recipeId) {
                showToast("Bitte wähle ein Rezept aus.", "error");
                return;
            }

            try {
                const response = await fetch(
                    `/inventory/consume-recipe-preview/?recipe_id=${recipeId}&servings=${servings}`
                );

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Vorschau konnte nicht geladen werden.");
                }

                renderConsumeRecipePreview(data);
            } catch (error) {
                console.error(error);
                showToast(error.message || "Beim Laden der Vorschau ist ein Fehler aufgetreten.", "error");
            }
        });
    }

    if (applyConsumeRecipeBtn) {
        applyConsumeRecipeBtn.addEventListener("click", async () => {
            const recipeId = consumeRecipeIdInput?.value;
            const servings = consumeServingsInput?.value || "1";

            if (!recipeId) {
                showToast("Bitte wähle ein Rezept aus.", "error");
                return;
            }

            const selectedIngredientIds = Array.from(
                document.querySelectorAll(".consume-ingredient-checkbox:checked")
            ).map((checkbox) => checkbox.value);

            if (selectedIngredientIds.length === 0) {
                showToast("Bitte wähle mindestens eine Zutat aus.", "error");
                return;
            }

            try {
                const csrfToken = getCsrfTokenFromCookie();

                const response = await fetch("/inventory/apply-recipe-consumption/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({
                        recipe_id: recipeId,
                        servings: servings,
                        ingredient_ids: selectedIngredientIds,
                    }),
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Verbrauch konnte nicht angewendet werden.");
                }

                showToast(data.message || "Verbrauch wurde angewendet.", "success");
                setTimeout(() => {
                    window.location.reload();
                }, 700);
                window.location.reload();
            } catch (error) {
                console.error(error);
                showToast(error.message || "Beim Anwenden ist ein Fehler aufgetreten.", "error");
            }
        });
    }

    function getCsrfTokenFromCookie() {
        const cookieValue = document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrftoken="));

        return cookieValue ? cookieValue.split("=")[1] : "";
    }

    function showToast(message, type = "success") {
        const container = document.querySelector(".toast-container");
        if (!container) {
            alert(message);
            return;
        }

        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">✔</span>
            <span class="toast-text">${message}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add("hide");

            setTimeout(() => {
                toast.remove();
            }, 250);
        }, 2000);
    }

    consumeRecipeModal?.addEventListener("click", (event) => {
        if (event.target === consumeRecipeModal) {
            closeConsumeRecipeModal();
        }
    });

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
            initializeIngredientSearch(editModal, "inventoryIngredientDropdownEdit");
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
                const createDropdown = activeInventoryFormContainer?.querySelector("#inventoryIngredientDropdownCreate");
                const editDropdown = activeInventoryFormContainer?.querySelector("#inventoryIngredientDropdownEdit");
                const activeDropdown = createDropdown || editDropdown;

                if (hiddenIngredientInput) {
                    hiddenIngredientInput.value = String(data.ingredient.id);
                }

                if (ingredientSearchInput) {
                    ingredientSearchInput.value = data.ingredient.name;
                }

                if (activeDropdown) {
                    const option = document.createElement("button");
                    option.type = "button";
                    option.className = "custom-search-option";
                    option.dataset.name = data.ingredient.name;
                    option.dataset.id = data.ingredient.id;
                    option.textContent = data.ingredient.name;
                    activeDropdown.appendChild(option);
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

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            if (consumeRecipeModal?.classList.contains("active")) {
                closeConsumeRecipeModal();
            }
        }
    });

    function openConsumeRecipeModal() {
        consumeRecipeModal?.classList.add("active");
        initializeConsumeRecipeSearch();
    }

    function closeConsumeRecipeModal() {
        consumeRecipeModal?.classList.remove("active");

        if (consumeRecipePreviewContainer) {
            consumeRecipePreviewContainer.innerHTML = "";
            consumeRecipePreviewContainer.classList.add("hidden");
        }

        applyConsumeRecipeBtn?.classList.add("hidden");

        if (consumeRecipeSearchInput) {
            consumeRecipeSearchInput.value = "";
        }

        if (consumeRecipeIdInput) {
            consumeRecipeIdInput.value = "";
        }

        if (consumeServingsInput) {
            consumeServingsInput.value = "1";
        }
    }

    function initializeConsumeRecipeSearch() {
        if (!consumeRecipeSearchInput || !consumeRecipeIdInput || !consumeRecipeOptions) {
            return;
        }

        consumeRecipeSearchInput.setAttribute("list", "consume-recipe-options");

        function syncRecipeId() {
            const typedValue = consumeRecipeSearchInput.value.trim().toLowerCase();
            const options = Array.from(consumeRecipeOptions.querySelectorAll("option"));

            const match = options.find(
                (option) => option.value.trim().toLowerCase() === typedValue
            );

            if (match) {
                consumeRecipeIdInput.value = match.dataset.id || "";
            } else {
                consumeRecipeIdInput.value = "";
            }
        }

        consumeRecipeSearchInput.addEventListener("input", syncRecipeId);
        consumeRecipeSearchInput.addEventListener("change", syncRecipeId);

        syncRecipeId();
    }

    function renderConsumeRecipePreview(data) {
        if (!consumeRecipePreviewContainer) {
            return;
        }

        if (!data.items || data.items.length === 0) {
            consumeRecipePreviewContainer.innerHTML = '<p class="empty-state">Keine Zutaten gefunden.</p>';
            consumeRecipePreviewContainer.classList.remove("hidden");
            applyConsumeRecipeBtn?.classList.add("hidden");
            return;
        }

        const itemsHtml = data.items.map((item) => `
            <li class="consume-preview-item ${item.disabled ? "disabled-row" : ""}">
                <input
                    type="checkbox"
                    class="consume-ingredient-checkbox"
                    value="${item.ingredient_id}"
                    ${item.checked ? "checked" : ""}
                    ${item.disabled ? "disabled" : ""}
                >
                <div class="consume-preview-main">
                    <span class="consume-preview-name">${item.ingredient_name}</span>
                    <span class="consume-preview-meta">
                        Benötigt: ${item.recipe_quantity} ${item.recipe_unit}
                    </span>
                </div>
                <div class="consume-preview-right">
                    <span class="consume-preview-meta">${item.inventory_display}</span>
                    <span class="consume-preview-status ${item.status_type}">
                        ${item.status_label}
                    </span>
                </div>
            </li>
        `).join("");

        consumeRecipePreviewContainer.innerHTML = `
            <h3 class="consume-preview-heading">${data.recipe.name} – ${data.servings} Portion(en)</h3>
            <p class="consume-preview-subtext">
                Nur ausgewählte und kompatible Zutaten werden vom Inventar abgezogen.
            </p>
            <ul class="consume-preview-list">
                ${itemsHtml}
            </ul>
        `;
        consumeRecipePreviewContainer.classList.remove("hidden");
        applyConsumeRecipeBtn?.classList.remove("hidden");
    }
});