document.addEventListener("DOMContentLoaded", () => {
    const modalOverlay = document.getElementById("modal-overlay");
    const modalBody = document.getElementById("modal-body");

    if (!modalOverlay || !modalBody) {
        return;
    }

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

    document.addEventListener("click", (event) => {
        const closeButton = event.target.closest(".modal-close-btn");
        if (closeButton) {
            closeModal();
        }
    });

    document.addEventListener("submit", (event) => {
        const form = event.target;

        if (!modalBody.contains(form)) {
            return;
        }

        event.preventDefault();
        submitModalForm(form);
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
});