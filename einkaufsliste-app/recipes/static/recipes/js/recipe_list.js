document.addEventListener("DOMContentLoaded", () => {
    const modalOverlay = document.getElementById("modal-overlay");
    const modalBody = document.getElementById("modal-body");

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
            const trigger = event.target.closest(".open-edit-modal, .open-delete-modal");
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