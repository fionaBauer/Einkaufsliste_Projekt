document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("homeLinkModal");
    const openBtn = document.getElementById("homeLinkBtn");
    const closeBtn = document.getElementById("closeHomeLinkModal");
    const submitBtn = document.getElementById("submitHomeLink");
    const input = document.getElementById("home-link-input");

    function openModal() {
        if (modal) {
            modal.classList.add("active");
        }
    }

    function closeModal() {
        if (modal) {
            modal.classList.remove("active");
        }
    }

    if (openBtn) {
        openBtn.addEventListener("click", openModal);
    }

    if (closeBtn) {
        closeBtn.addEventListener("click", closeModal);
    }

    if (modal) {
        modal.addEventListener("click", (event) => {
            if (event.target === modal) {
                closeModal();
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modal?.classList.contains("active")) {
            closeModal();
        }
    });

    if (submitBtn) {
        submitBtn.addEventListener("click", async () => {
            const url = input?.value.trim();

            if (!url) {
                alert("Bitte Link eingeben.");
                return;
            }

            submitBtn.disabled = true;
            const originalText = submitBtn.textContent;
            submitBtn.textContent = "Wird extrahiert...";

            try {
                const csrf = getCsrfTokenFromCookie();

                const response = await fetch("/recipes/extract-from-link/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf,
                    },
                    body: JSON.stringify({ url }),
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Extraktion fehlgeschlagen.");
                }

                alert("Rezept erkannt: " + (data.recipe?.title || "Unbekannt"));
                closeModal();
            } catch (error) {
                console.error(error);
                alert(error.message || "Beim Extrahieren ist ein Fehler aufgetreten.");
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }

    function getCsrfTokenFromCookie() {
        const cookieValue = document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrftoken="));

        return cookieValue ? cookieValue.split("=")[1] : "";
    }
});