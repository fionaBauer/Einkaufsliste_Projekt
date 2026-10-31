document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const ingredientCreateModal = document.getElementById("ingredientCreateModal");
    const ingredientCreateModalBody = document.getElementById("ingredientCreateModalBody");

    function openCreateModal() {
        createModal?.classList.add("active");
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

    /* ── Zutatensuche im Hinzufügen-Modal (delegiert, überlebt stille Updates) ── */

    function searchParts() {
        return {
            searchInput: createModal?.querySelector(".ingredient-search-input"),
            hiddenInput: createModal?.querySelector('input[name="ingredient"]'),
            dropdown: createModal?.querySelector("#shoppingIngredientDropdown"),
        };
    }

    function renderFilteredOptions() {
        const { searchInput, dropdown } = searchParts();
        if (!searchInput || !dropdown) return;

        const typedValue = searchInput.value.trim().toLowerCase();
        let visibleCount = 0;

        dropdown.querySelectorAll(".custom-search-option").forEach((option) => {
            const matches = !typedValue || (option.dataset.name || "").toLowerCase().includes(typedValue);
            option.classList.toggle("hidden", !matches);
            if (matches) visibleCount += 1;
        });

        dropdown.classList.toggle("hidden", visibleCount === 0);
    }

    function syncIngredientId() {
        const { searchInput, hiddenInput, dropdown } = searchParts();
        if (!searchInput || !hiddenInput || !dropdown) return;

        const typedValue = searchInput.value.trim().toLowerCase();
        const match = Array.from(dropdown.querySelectorAll(".custom-search-option")).find(
            (option) => (option.dataset.name || "").trim().toLowerCase() === typedValue
        );
        hiddenInput.value = match ? match.dataset.id || "" : "";
    }

    document.addEventListener("focusin", (event) => {
        if (event.target.matches?.("#createModal .ingredient-search-input")) renderFilteredOptions();
    });

    document.addEventListener("input", (event) => {
        if (event.target.matches?.("#createModal .ingredient-search-input")) {
            syncIngredientId();
            renderFilteredOptions();
        }
    });

    /* ── Abhaken sofort speichern ── */

    document.addEventListener("change", async (event) => {
        const checkbox = event.target;
        if (!checkbox.matches?.(".shopping-check")) return;

        const formData = new FormData();
        formData.append("csrfmiddlewaretoken", App.csrf());
        formData.append("action", "toggle_item");
        formData.append("item_id", checkbox.value);
        formData.append("checked", checkbox.checked ? "1" : "0");

        try {
            const response = await fetch(window.location.href, {
                method: "POST",
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await response.json();
            if (data.success) {
                // Server kennt jetzt den Stand → Checkbox gilt nicht mehr als "ungespeichert"
                checkbox.defaultChecked = checkbox.checked;
            }
        } catch (error) {
            console.error(error);
            App.toast("Konnte nicht gespeichert werden.", "error");
        }
    });

    /* ── Klicks ── */

    document.addEventListener("click", async (event) => {
        // Info-/Rabatt-Bubbles: Antippen öffnet (Hover gibt's am Handy nicht)
        const infoButton = event.target.closest(".info-button");
        document.querySelectorAll(".shopping-info-wrapper.open").forEach((wrapper) => {
            if (!infoButton || wrapper !== infoButton.parentElement) wrapper.classList.remove("open");
        });
        if (infoButton) {
            event.preventDefault();
            infoButton.parentElement.classList.toggle("open");
            return;
        }

        const option = event.target.closest("#shoppingIngredientDropdown .custom-search-option");
        if (option) {
            const { searchInput, hiddenInput, dropdown } = searchParts();
            searchInput.value = option.dataset.name || "";
            hiddenInput.value = option.dataset.id || "";
            dropdown.classList.add("hidden");
            return;
        }

        if (!event.target.closest("#createModal .form-group")) {
            searchParts().dropdown?.classList.add("hidden");
        }

        if (event.target.closest("#openCreateModalBtn")) {
            openCreateModal();
            return;
        }

        if (event.target.closest("#closeCreateModalBtn") || event.target === createModal) {
            closeCreateModal();
            return;
        }

        if (event.target === ingredientCreateModal || event.target.closest(".ingredient-modal-close-btn")) {
            closeIngredientCreateModal();
            return;
        }

        const savingsCard = event.target.closest(".savings-card");
        if (savingsCard) {
            const template = document.getElementById(savingsCard.dataset.savingsDetail);
            const body = document.getElementById("savingsDetailBody");
            document.getElementById("savingsDetailTitle").textContent = savingsCard.dataset.storeName;
            body.innerHTML = "";
            if (template) body.appendChild(template.content.cloneNode(true));
            document.getElementById("savingsDetailModal").classList.add("active");
            return;
        }

        const ingredientCreateTrigger = event.target.closest(".open-ingredient-create-btn");
        if (ingredientCreateTrigger) {
            try {
                const response = await fetch(ingredientCreateTrigger.dataset.url, {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await response.json();
                ingredientCreateModalBody.innerHTML = data.html;
                openIngredientCreateModal();
            } catch (error) {
                console.error(error);
                App.toast("Formular konnte nicht geladen werden.", "error");
            }
        }
    });

    /* ── Neue Zutat aus dem Modal anlegen ── */

    document.addEventListener("submit", async (event) => {
        const form = event.target;
        if (!ingredientCreateModalBody?.contains(form)) return;

        event.preventDefault();

        try {
            const response = await fetch(form.action, {
                method: form.method || "POST",
                body: new FormData(form),
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await response.json();

            if (data.success) {
                const { searchInput, hiddenInput, dropdown } = searchParts();
                const unitSelect = createModal?.querySelector('select[name="unit"]');

                if (hiddenInput) hiddenInput.value = String(data.ingredient.id);
                if (searchInput) searchInput.value = data.ingredient.name;

                if (dropdown) {
                    const option = document.createElement("button");
                    option.type = "button";
                    option.className = "custom-search-option";
                    option.dataset.name = data.ingredient.name;
                    option.dataset.id = data.ingredient.id;
                    option.textContent = data.ingredient.name;
                    dropdown.appendChild(option);
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
            App.toast("Beim Speichern der Zutat ist ein Fehler aufgetreten.", "error");
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        if (ingredientCreateModal?.classList.contains("active")) {
            closeIngredientCreateModal();
            return;
        }
        closeCreateModal();
    });
});
