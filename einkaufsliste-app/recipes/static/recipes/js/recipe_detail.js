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
            openModal();
        } catch (error) {
            modalBody.innerHTML = "<p>Beim Laden ist ein Fehler aufgetreten.</p>";
            openModal();
            console.error(error);
        }
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
                const ingredientSelect = modalBody.querySelector('select[name="ingredient"]');
                const unitSelect = modalBody.querySelector('select[name="unit"]');

                if (ingredientSelect) {
                    const option = document.createElement("option");
                    option.value = data.ingredient.id;
                    option.textContent = data.ingredient.name;
                    option.selected = true;
                    ingredientSelect.appendChild(option);
                    ingredientSelect.value = String(data.ingredient.id);
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

            if (isNaN(baseQuantity)) {
                return;
            }

            const scaledQuantity = baseQuantity * factor;
            element.textContent = formatQuantity(scaledQuantity);
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
});