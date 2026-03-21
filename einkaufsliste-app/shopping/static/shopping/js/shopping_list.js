document.addEventListener("DOMContentLoaded", () => {
    const createModal = document.getElementById("createModal");
    const openCreateModalBtn = document.getElementById("openCreateModalBtn");
    const closeCreateModalBtn = document.getElementById("closeCreateModalBtn");

    if (openCreateModalBtn && createModal) {
        openCreateModalBtn.addEventListener("click", () => {
            createModal.classList.add("active");
        });
    }

    if (closeCreateModalBtn && createModal) {
        closeCreateModalBtn.addEventListener("click", () => {
            createModal.classList.remove("active");
        });
    }

    if (createModal) {
        createModal.addEventListener("click", (event) => {
            if (event.target === createModal) {
                createModal.classList.remove("active");
            }
        });
    }
});