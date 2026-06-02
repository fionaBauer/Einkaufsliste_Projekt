document.addEventListener("DOMContentLoaded", () => {
    const modalOverlay = document.getElementById("modal-overlay");
    const modalBody = document.getElementById("modal-body");

    const ingredientModalOverlay = document.getElementById("ingredient-modal-overlay");
    const ingredientModalBody = document.getElementById("ingredient-modal-body");

    const targetServingsInput = document.getElementById("target-servings");
    const decreaseButton = document.getElementById("decrease-servings");
    const increaseButton = document.getElementById("increase-servings");
    const resetButton = document.getElementById("reset-servings");

    const baseServings = window.recipeData?.baseServings || 1;
    const quantityElements = document.querySelectorAll(".scaled-quantity");

    function openModal() {
        modalOverlay.classList.add("active");
    }

    function closeModal() {
        modalOverlay.classList.remove("active");
        modalBody.innerHTML = "";
    }

    function openIngredientModal() {
        ingredientModalOverlay.classList.add("active");
    }

    function closeIngredientModal() {
        ingredientModalOverlay.classList.remove("active");
        ingredientModalBody.innerHTML = "";
    }

    async function loadModalContent(url) {
        try {
            const response = await fetch(url, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!response.ok) {
                throw new Error("Modal-Inhalt konnte nicht geladen werden.");
            }

            const html = await response.text();
            modalBody.innerHTML = html;
            initializeIngredientSearch();
            setTimeout(initInlineIngredients, 0);
            openModal();
        } catch (error) {
            modalBody.innerHTML = "<p>Beim Laden ist ein Fehler aufgetreten.</p>";
            openModal();
            console.error(error);
        }
    }

    function initializeIngredientSearch() {
        const searchInput = modalBody.querySelector(".ingredient-search-input");
        const hiddenIngredientInput = modalBody.querySelector('input[name="ingredient"]');
        const dropdown = modalBody.querySelector("#recipeIngredientDropdown");

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
            if (!modalBody.contains(event.target)) {
                dropdown.classList.add("hidden");
            }
        });

        syncIngredientId();
        dropdown.classList.add("hidden");
    }

    async function loadIngredientCreateModal(url) {
        try {
            const response = await fetch(url, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!response.ok) {
                throw new Error("Ingredient-Modal konnte nicht geladen werden.");
            }

            const data = await response.json();
            ingredientModalBody.innerHTML = data.html;
            openIngredientModal();
        } catch (error) {
            ingredientModalBody.innerHTML = "<p>Beim Laden ist ein Fehler aufgetreten.</p>";
            openIngredientModal();
            console.error(error);
        }
    }

    async function submitModalForm(form) {
        const formData = new FormData(form);

        try {
            const response = await fetch(form.action, {
                method: form.method || "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            const contentType = response.headers.get("content-type") || "";

            if (contentType.includes("application/json")) {
                const data = await response.json();

                if (data.success) {
                    closeModal();
                    window.location.reload();
                    return;
                }
            }

            const html = await response.text();
            modalBody.innerHTML = html;
            openModal();
        } catch (error) {
            modalBody.innerHTML = "<p>Beim Speichern ist ein Fehler aufgetreten.</p>";
            openModal();
            console.error(error);
        }
    }

    async function submitIngredientCreateForm(form) {
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
                const hiddenIngredientInput = modalBody.querySelector('input[name="ingredient"]');
                const ingredientSearchInput = modalBody.querySelector('.ingredient-search-input');
                const dropdown = modalBody.querySelector('#recipeIngredientDropdown');
                const unitSelect = modalBody.querySelector('select[name="unit"]');

                if (hiddenIngredientInput) {
                    hiddenIngredientInput.value = String(data.ingredient.id);
                }

                if (ingredientSearchInput) {
                    ingredientSearchInput.value = data.ingredient.name;
                }

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

                closeIngredientModal();
                return;
            }

            ingredientModalBody.innerHTML = data.html;
            openIngredientModal();
        } catch (error) {
            ingredientModalBody.innerHTML = "<p>Beim Speichern ist ein Fehler aufgetreten.</p>";
            openIngredientModal();
            console.error(error);
        }
    }

    function formatQuantity(value) {
        const rounded = Math.round(value * 100) / 100;

        if (Number.isInteger(rounded)) {
            return String(rounded);
        }

        return rounded.toFixed(2).replace(/\.?0+$/, "");
    }

    function updateScaledQuantities() {
        if (!targetServingsInput) {
            return;
        }

        let targetServings = parseInt(targetServingsInput.value, 10);

        if (isNaN(targetServings) || targetServings < 1) {
            targetServings = 1;
            targetServingsInput.value = 1;
        }

        const factor = targetServings / baseServings;

        quantityElements.forEach((element) => {
            const baseQuantity = parseFloat(element.dataset.baseQuantity);
            const unit = element.dataset.unit || "";

            if (isNaN(baseQuantity)) {
                return;
            }

            const scaledQuantity = baseQuantity * factor;

            // Stück und Packung: immer aufrunden auf ganze Zahlen
            if (unit === "pcs" || unit === "pkg") {
                element.textContent = String(Math.ceil(scaledQuantity));
            } else {
                element.textContent = formatQuantity(scaledQuantity);
            }
        });
    }

    document.addEventListener("click", (event) => {
        const trigger = event.target.closest(".open-modal-btn");
        if (trigger) {
            loadModalContent(trigger.dataset.url);
            return;
        }

        const ingredientCreateTrigger = event.target.closest(".open-ingredient-create-btn");
        if (ingredientCreateTrigger) {
            loadIngredientCreateModal(ingredientCreateTrigger.dataset.url);
            return;
        }

        const closeButton = event.target.closest(".modal-close-btn");
        if (closeButton) {
            closeModal();
            return;
        }

        const ingredientCloseButton = event.target.closest(".ingredient-modal-close-btn");
        if (ingredientCloseButton) {
            closeIngredientModal();
        }
    });

    document.addEventListener("submit", (event) => {
        const form = event.target;

        if (ingredientModalBody.contains(form)) {
            event.preventDefault();
            submitIngredientCreateForm(form);
            return;
        }

        if (modalBody.contains(form)) {
            event.preventDefault();
            submitModalForm(form);
        }
    });

    modalOverlay?.addEventListener("click", (event) => {
        if (event.target === modalOverlay) {
            closeModal();
        }
    });

    ingredientModalOverlay?.addEventListener("click", (event) => {
        if (event.target === ingredientModalOverlay) {
            closeIngredientModal();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            if (ingredientModalOverlay?.classList.contains("active")) {
                closeIngredientModal();
                return;
            }

            if (modalOverlay?.classList.contains("active")) {
                closeModal();
            }
        }
    });

    if (targetServingsInput) {
        targetServingsInput.addEventListener("input", updateScaledQuantities);
        targetServingsInput.addEventListener("change", updateScaledQuantities);
    }

    if (decreaseButton && targetServingsInput) {
        decreaseButton.addEventListener("click", () => {
            let currentValue = parseInt(targetServingsInput.value, 10) || baseServings;
            currentValue = Math.max(1, currentValue - 1);
            targetServingsInput.value = currentValue;
            updateScaledQuantities();
        });
    }

    if (increaseButton && targetServingsInput) {
        increaseButton.addEventListener("click", () => {
            let currentValue = parseInt(targetServingsInput.value, 10) || baseServings;
            currentValue += 1;
            targetServingsInput.value = currentValue;
            updateScaledQuantities();
        });
    }

    if (resetButton && targetServingsInput) {
        resetButton.addEventListener("click", () => {
            targetServingsInput.value = baseServings;
            updateScaledQuantities();
        });
    }

    updateScaledQuantities();
});function initInlineIngredients() {
    const list = document.getElementById("inline-ingredients-list");
    const addBtn = document.getElementById("add-inline-ingredient");
    const form = document.getElementById("recipe-main-form");
    if (!list || !addBtn || !form) return;

    const UNITS = [
        ["g", "g"], ["kg", "kg"], ["ml", "ml"], ["l", "l"],
        ["pcs", "Stück"], ["pkg", "Packung"], ["el", "EL"], ["tl", "TL"]
    ];

    // Fetch existing ingredients for autocomplete
    let ingredientSuggestions = [];
    fetch("/ingredients/api/list/").then(r => r.ok ? r.json() : []).then(data => {
        ingredientSuggestions = data;
    }).catch(() => {});

    function createRow() {
        const row = document.createElement("div");
        row.className = "inline-ingredient-row";

        const nameWrap = document.createElement("div");
        nameWrap.style.position = "relative";
        nameWrap.style.flex = "1";
        nameWrap.style.minWidth = "0";

        const nameInput = document.createElement("input");
        nameInput.type = "text";
        nameInput.placeholder = "Zutat";
        nameInput.autocomplete = "off";
        nameInput.style.width = "100%";

        const suggestions = document.createElement("div");
        suggestions.style.cssText = "position:absolute;top:100%;left:0;right:0;background:white;border:1.5px solid #e5e5e5;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.1);z-index:100;max-height:160px;overflow-y:auto;display:none;";

        nameInput.addEventListener("input", () => {
            const q = nameInput.value.toLowerCase().trim();
            suggestions.innerHTML = "";
            if (!q || !ingredientSuggestions.length) { suggestions.style.display = "none"; return; }
            const matches = ingredientSuggestions.filter(i => i.name.toLowerCase().includes(q)).slice(0, 6);
            if (!matches.length) { suggestions.style.display = "none"; return; }
            matches.forEach(ing => {
                const opt = document.createElement("div");
                opt.textContent = ing.name;
                opt.style.cssText = "padding:8px 12px;cursor:pointer;font-size:13px;";
                opt.addEventListener("mousedown", e => { e.preventDefault(); nameInput.value = ing.name; suggestions.style.display = "none"; });
                opt.addEventListener("mouseover", () => opt.style.background = "#f5f5f5");
                opt.addEventListener("mouseout", () => opt.style.background = "");
                suggestions.appendChild(opt);
            });
            suggestions.style.display = "block";
        });

        nameInput.addEventListener("blur", () => setTimeout(() => { suggestions.style.display = "none"; }, 150));
        nameWrap.appendChild(nameInput);
        nameWrap.appendChild(suggestions);

        const qtyInput = document.createElement("input");
        qtyInput.type = "number";
        qtyInput.placeholder = "Menge";
        qtyInput.min = "0";
        qtyInput.step = "0.01";
        qtyInput.style.width = "70px";

        const unitSelect = document.createElement("select");
        UNITS.forEach(([val, label]) => {
            const opt = document.createElement("option");
            opt.value = val;
            opt.textContent = label;
            unitSelect.appendChild(opt);
        });

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "inline-remove-btn";
        removeBtn.innerHTML = "×";
        removeBtn.addEventListener("click", () => row.remove());

        row.appendChild(nameWrap);
        row.appendChild(qtyInput);
        row.appendChild(unitSelect);
        row.appendChild(removeBtn);
        list.appendChild(row);
        nameInput.focus();
    }

    addBtn.addEventListener("click", createRow);

    form.addEventListener("submit", async function(e) {
        const rows = list.querySelectorAll(".inline-ingredient-row");
        if (rows.length === 0) return;

        e.preventDefault();

        const formData = new FormData(form);
        const existingRecipeId = form.dataset.recipeId || null;
        let recipeId = existingRecipeId;

        // Save recipe metadata first
        try {
            const res = await fetch(window.location.href, {
                method: "POST",
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (res.headers.get("content-type")?.includes("application/json")) {
                const data = await res.json();
                if (!data.success) return;
                recipeId = data.recipe_id || existingRecipeId;
            }
            if (!recipeId) { form.submit(); return; }
        } catch(err) { form.submit(); return; }

        const csrfToken = form.querySelector("[name=csrfmiddlewaretoken]").value;

        // Track which existing IDs are still present
        const presentExistingIds = new Set();

        for (const row of rows) {
            const nameInput = row.querySelector("input[type=text]");
            const name = nameInput ? nameInput.value.trim() : "";
            const qty = row.querySelector("input[type=number]")?.value.trim();
            const unit = row.querySelector("select")?.value;
            const existingId = row.dataset.existingId;

            if (!name) {
                // Delete if it was existing
                if (existingId) {
                    await fetch(`/recipes/${recipeId}/ingredients/inline-delete/${existingId}/`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
                        body: JSON.stringify({}),
                    });
                }
                continue;
            }

            if (existingId) {
                // Update existing
                presentExistingIds.add(existingId);
                await fetch(`/recipes/${recipeId}/ingredients/inline-update/${existingId}/`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
                    body: JSON.stringify({ name, quantity: qty || "1", unit: unit || "g" }),
                });
            } else {
                // Create new
                await fetch(`/recipes/${recipeId}/ingredients/inline-create/`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
                    body: JSON.stringify({ name, quantity: qty || "1", unit: unit || "g", notes: "" }),
                });
            }
        }

        window.location.href = `/recipes/${recipeId}/`;
    });
}