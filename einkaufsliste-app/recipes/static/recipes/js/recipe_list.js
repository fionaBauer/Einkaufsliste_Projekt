document.addEventListener("DOMContentLoaded", () => {
    const modalOverlay = document.getElementById("modal-overlay");
    const modalBody = document.getElementById("modal-body");

    // ── Card selected effect ──
    document.addEventListener("change", (event) => {
        const checkbox = event.target;
        if (checkbox.name !== "recipes") return;
        const card = checkbox.closest(".recipe-card");
        if (!card) return;
        card.classList.toggle("selected", checkbox.checked);
    });

    const shoppingModal = document.getElementById("shoppingCreateModal");
    const openShoppingModalBtn = document.getElementById("openShoppingModalBtn");
    const closeShoppingModalBtn = document.getElementById("closeShoppingModalBtn");
    const selectedRecipesContainer = document.getElementById("selected-recipes-container");
    const applyServingsToAllBtn = document.getElementById("applyServingsToAllBtn");
    const servingsForAllInput = document.getElementById("servings-for-all");
    const shoppingCreateForm = document.getElementById("shopping-create-form");

    const recipeReviewModal = document.getElementById("recipeReviewModal");
    const closeRecipeReviewModalBtn = document.getElementById("closeRecipeReviewModalBtn");
    const recipeReviewForm = document.getElementById("recipe-review-form");
    const reviewTitleInput = document.getElementById("review-title");
    const reviewServingsInput = document.getElementById("review-servings");
    const reviewInstructionsInput = document.getElementById("review-instructions");
    const reviewIngredientsContainer = document.getElementById("review-ingredients-container");

    const linkCreateModal = document.getElementById("linkCreateModal");
    const openLinkModalBtn = document.getElementById("openLinkModalBtn");
    const closeLinkModalBtn = document.getElementById("closeLinkModalBtn");
    const recipeLinkInput = document.getElementById("recipe-link-input");
    const createFromLinkBtn = document.getElementById("create-from-link-btn");

let extractedRecipeData = null;

    if (modalOverlay && modalBody) {
        function openModal() {
            modalOverlay.classList.add("active");
        }

        function closeModal() {
            modalOverlay.classList.remove("active");
            modalBody.innerHTML = "";
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
                openModal();
                setTimeout(initInlineIngredients, 0);
            } catch (error) {
                modalBody.innerHTML = "<p>Beim Laden ist ein Fehler aufgetreten.</p>";
                openModal();
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

        const createButton = document.getElementById("open-create-modal");
        if (createButton) {
            createButton.addEventListener("click", () => {
                loadModalContent(createButton.dataset.url);
            });
        }

        document.addEventListener("click", (event) => {
            const trigger = event.target.closest(".open-edit-modal, .open-delete-modal, .open-modal-btn");
            if (!trigger) {
                return;
            }

            loadModalContent(trigger.dataset.url);
        });

        document.addEventListener("submit", (event) => {
            const form = event.target;

            if (!modalBody.contains(form)) {
                return;
            }

            // If recipe-main-form, let initInlineIngredients handle it
            if (form.id === "recipe-main-form") {
                return;
            }

            event.preventDefault();
            submitModalForm(form);
        });

        document.addEventListener("click", (event) => {
            const closeButton = event.target.closest(".modal-close-btn");
            if (closeButton) {
                closeModal();
            }
        });

        modalOverlay.addEventListener("click", (event) => {
            if (event.target === modalOverlay) {
                closeModal();
            }
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && modalOverlay.classList.contains("active")) {
                closeModal();
            }
        });
    }

    function openShoppingModal() {
        if (shoppingModal) {
            shoppingModal.classList.add("active");
        }
    }

    function closeShoppingModal() {
        if (shoppingModal) {
            shoppingModal.classList.remove("active");
        }
    }

    function getSelectedRecipes() {
        const checkedBoxes = document.querySelectorAll('input[name="recipes"]:checked');

        return Array.from(checkedBoxes).map((checkbox) => ({
            id: checkbox.value,
            name: checkbox.dataset.recipeName,
            baseServings: checkbox.dataset.recipeServings,
        }));
    }

    function renderSelectedRecipes() {
        const selectedRecipes = getSelectedRecipes();

        if (!selectedRecipesContainer || !shoppingCreateForm) {
            return;
        }

        selectedRecipesContainer.innerHTML = "";

        shoppingCreateForm.querySelectorAll('input[name="recipes"], input[data-serving-input="true"]').forEach((input) => {
            input.remove();
        });

        if (selectedRecipes.length === 0) {
            selectedRecipesContainer.innerHTML = '<p class="empty-state">Keine Rezepte ausgewählt.</p>';
            return;
        }

        selectedRecipes.forEach((recipe) => {
            const hiddenRecipeInput = document.createElement("input");
            hiddenRecipeInput.type = "hidden";
            hiddenRecipeInput.name = "recipes";
            hiddenRecipeInput.value = recipe.id;
            shoppingCreateForm.appendChild(hiddenRecipeInput);

            const servingsInputHiddenMarker = document.createElement("input");
            servingsInputHiddenMarker.type = "hidden";
            servingsInputHiddenMarker.name = `servings_${recipe.id}`;
            servingsInputHiddenMarker.value = recipe.baseServings;
            servingsInputHiddenMarker.setAttribute("data-serving-input", "true");
            shoppingCreateForm.appendChild(servingsInputHiddenMarker);

            const row = document.createElement("div");
            row.className = "selected-recipe-row";
            row.innerHTML = `
                <div>
                    <div class="selected-recipe-name">${recipe.name}</div>
                </div>
                <div class="selected-recipe-base">Basis: ${recipe.baseServings} Portion(en)</div>
                <div class="selected-recipe-servings">
                    <input
                        type="number"
                        min="1"
                        value="${recipe.baseServings}"
                        data-recipe-id="${recipe.id}"
                        class="recipe-servings-input"
                    >
                </div>
            `;
            selectedRecipesContainer.appendChild(row);
        });

        bindRecipeServingInputs();
    }

    function bindRecipeServingInputs() {
        const visibleInputs = document.querySelectorAll(".recipe-servings-input");

        visibleInputs.forEach((input) => {
            input.addEventListener("input", () => {
                const recipeId = input.dataset.recipeId;
                const hiddenInput = shoppingCreateForm.querySelector(`input[name="servings_${recipeId}"]`);

                if (hiddenInput) {
                    hiddenInput.value = input.value || 1;
                }
            });
        });
    }

    if (openShoppingModalBtn) {
        openShoppingModalBtn.addEventListener("click", () => {
            renderSelectedRecipes();
            openShoppingModal();
        });
    }

    if (closeShoppingModalBtn) {
        closeShoppingModalBtn.addEventListener("click", () => {
            closeShoppingModal();
        });
    }

    if (shoppingModal) {
        shoppingModal.addEventListener("click", (event) => {
            if (event.target === shoppingModal) {
                closeShoppingModal();
            }
        });
    }

    if (applyServingsToAllBtn && servingsForAllInput) {
        applyServingsToAllBtn.addEventListener("click", () => {
            const value = servingsForAllInput.value;

            if (!value || parseInt(value, 10) < 1) {
                return;
            }

            document.querySelectorAll(".recipe-servings-input").forEach((input) => {
                input.value = value;

                const recipeId = input.dataset.recipeId;
                const hiddenInput = shoppingCreateForm.querySelector(`input[name="servings_${recipeId}"]`);

                if (hiddenInput) {
                    hiddenInput.value = value;
                }
            });
        });
    }

    if (closeRecipeReviewModalBtn) {
        closeRecipeReviewModalBtn.addEventListener("click", () => {
            closeRecipeReviewModal();
        });
    }

    if (recipeReviewModal) {
        recipeReviewModal.addEventListener("click", (event) => {
            if (event.target === recipeReviewModal) {
                closeRecipeReviewModal();
            }
        });
    }

    if (recipeReviewForm) {
        recipeReviewForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const payload = collectReviewedRecipeData();

            if (!payload.title) {
                alert("Bitte gib einen Rezeptnamen an.");
                return;
            }

            try {
                const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value
                    || getCsrfTokenFromCookie();

                const response = await fetch("/recipes/create-from-extracted/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify(payload),
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Speichern fehlgeschlagen.");
                }

                window.location.href = data.redirect_url;
            } catch (error) {
                console.error(error);
                alert(error.message || "Beim Speichern ist ein Fehler aufgetreten.");
            }
        });
    }

    if (openLinkModalBtn) {
        openLinkModalBtn.addEventListener("click", () => {
            openLinkModal();
        });
    }

    if (closeLinkModalBtn) {
        closeLinkModalBtn.addEventListener("click", () => {
            closeLinkModal();
        });
    }

    if (linkCreateModal) {
        linkCreateModal.addEventListener("click", (event) => {
            if (event.target === linkCreateModal) {
                closeLinkModal();
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && shoppingModal?.classList.contains("active")) {
            closeShoppingModal();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && recipeReviewModal?.classList.contains("active")) {
            closeRecipeReviewModal();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && linkCreateModal?.classList.contains("active")) {
            closeLinkModal();
        }
    });

    if (createFromLinkBtn && recipeLinkInput) {
        createFromLinkBtn.addEventListener("click", async () => {
            const url = recipeLinkInput.value.trim();

            if (!url) {
                alert("Bitte füge zuerst einen Rezept-Link ein.");
                return;
            }

            createFromLinkBtn.disabled = true;
            const originalButtonText = createFromLinkBtn.textContent;
            createFromLinkBtn.textContent = "Wird extrahiert...";

            try {
                const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value
                    || getCsrfTokenFromCookie();

                const response = await fetch("/recipes/extract-from-link/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ url }),
                });

                const contentType = response.headers.get("content-type") || "";

                if (!contentType.includes("application/json")) {
                    const text = await response.text();
                    console.error("Server returned HTML instead of JSON:", text);
                    throw new Error("Der Server hat keine JSON-Antwort zurückgegeben.");
                }

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Extraktion fehlgeschlagen.");
                }

                closeLinkModal();
                renderExtractedRecipe(data.recipe);
                openRecipeReviewModal();
            } catch (error) {
                console.error(error);
                alert(error.message || "Beim Extrahieren ist ein Fehler aufgetreten.");
            } finally {
                createFromLinkBtn.disabled = false;
                createFromLinkBtn.textContent = originalButtonText;
            }
        });
    }

    function getCsrfTokenFromCookie() {
        const cookieValue = document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrftoken="));

        return cookieValue ? cookieValue.split("=")[1] : "";
    }

    function openRecipeReviewModal() {
        if (recipeReviewModal) {
            recipeReviewModal.classList.add("active");
        }
    }

    function closeRecipeReviewModal() {
        if (recipeReviewModal) {
            recipeReviewModal.classList.remove("active");
        }
    }

    function renderExtractedRecipe(recipe) {
        extractedRecipeData = recipe;

        if (!reviewTitleInput || !reviewServingsInput || !reviewInstructionsInput || !reviewIngredientsContainer) {
            return;
        }

        reviewTitleInput.value = recipe.title || "";
        reviewServingsInput.value = extractServingsNumber(recipe.servings) || 1;

        const steps = Array.isArray(recipe.steps) ? recipe.steps : [];
        reviewInstructionsInput.value = steps
            .map((step) => step.instruction || "")
            .filter(Boolean)
            .join("\n\n");

        reviewIngredientsContainer.innerHTML = "";

        const ingredients = Array.isArray(recipe.ingredients) ? recipe.ingredients : [];

        if (ingredients.length === 0) {
            reviewIngredientsContainer.innerHTML = '<p class="empty-state">Keine Zutaten erkannt.</p>';
            return;
        }

        ingredients.forEach((ingredient, index) => {
            const row = document.createElement("div");
            row.className = "review-ingredient-row";
            row.innerHTML = `
                <input type="text" value="${ingredient.name || ""}" data-field="name" data-index="${index}" placeholder="Name">
                <input type="text" value="${ingredient.amount ?? ""}" data-field="amount" data-index="${index}" placeholder="Menge">
                <input type="text" value="${ingredient.unit || ""}" data-field="unit" data-index="${index}" placeholder="Einheit">
                <input type="text" value="${ingredient.notes || ""}" data-field="notes" data-index="${index}" placeholder="Notiz">
            `;
            reviewIngredientsContainer.appendChild(row);
        });
    }

    function extractServingsNumber(servingsValue) {
        if (!servingsValue) {
            return 1;
        }

        const match = String(servingsValue).match(/\d+/);
        return match ? parseInt(match[0], 10) : 1;
    }

    function collectReviewedRecipeData() {
        const ingredientRows = reviewIngredientsContainer.querySelectorAll(".review-ingredient-row");

        const ingredients = Array.from(ingredientRows).map((row) => {
            const inputs = row.querySelectorAll("input");

            return {
                name: inputs[0]?.value.trim() || "",
                amount: inputs[1]?.value.trim() || "",
                unit: inputs[2]?.value.trim() || "",
                notes: inputs[3]?.value.trim() || "",
            };
        }).filter((item) => item.name);

        return {
            title: reviewTitleInput.value.trim(),
            servings: reviewServingsInput.value,
            instructions: reviewInstructionsInput.value.trim(),
            ingredients: ingredients,
        };
    }

    // ── Tab switching ──
    const importTabs = document.querySelectorAll(".import-tab");
    const importPanels = document.querySelectorAll(".import-tab-panel");
    importTabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            importTabs.forEach((t) => t.classList.remove("active"));
            importPanels.forEach((p) => p.classList.add("hidden"));
            tab.classList.add("active");
            document.getElementById(`import-panel-${tab.dataset.tab}`)?.classList.remove("hidden");
        });
    });

    // ── Close buttons for both panels ──
    document.getElementById("closeLinkModalBtnText")?.addEventListener("click", () => closeLinkModal());

    // ── Extract from text ──
    const createFromTextBtn = document.getElementById("create-from-text-btn");
    const recipeTextInput = document.getElementById("recipe-text-input");

    if (createFromTextBtn && recipeTextInput) {
        createFromTextBtn.addEventListener("click", async () => {
            const text = recipeTextInput.value.trim();
            if (!text) {
                recipeTextInput.focus();
                return;
            }

            const originalText = createFromTextBtn.textContent;
            createFromTextBtn.disabled = true;
            createFromTextBtn.textContent = "Wird analysiert…";

            try {
                const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value
                    || getCsrfTokenFromCookie();

                const response = await fetch("/recipes/extract-from-text/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ text }),
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Extraktion fehlgeschlagen.");
                }

                closeLinkModal();
                renderExtractedRecipe(data.recipe);
                openRecipeReviewModal();
            } catch (error) {
                console.error(error);
                alert(error.message || "Beim Analysieren ist ein Fehler aufgetreten.");
            } finally {
                createFromTextBtn.disabled = false;
                createFromTextBtn.textContent = originalText;
            }
        });
    }

    function openLinkModal() {
        if (linkCreateModal) {
            linkCreateModal.classList.add("active");
        }
    }

    function closeLinkModal() {
        if (linkCreateModal) {
            linkCreateModal.classList.remove("active");
        }
    }
});


function initInlineIngredients() {
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
            const res = await fetch(form.action, {
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