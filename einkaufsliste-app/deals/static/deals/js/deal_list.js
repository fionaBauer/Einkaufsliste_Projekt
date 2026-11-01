/**
 * Rabatte: Aktualisieren mit Ladebalken.
 *
 * Der Server lädt die Angebote in einem Hintergrund-Thread und schreibt den Fortschritt
 * (erledigte / alle Suchbegriffe) in die Datenbank. Hier wird er jede Sekunde abgefragt,
 * bis der Lauf fertig ist – danach wird die Seite still neu eingemorpht.
 */
document.addEventListener("DOMContentLoaded", () => {
    const page = document.getElementById("deals-page");
    if (!page) return;

    const progress = document.getElementById("syncProgress");
    const progressText = document.getElementById("syncProgressText");
    const progressBar = document.getElementById("syncProgressBar");
    const POLL_MS = 1000;
    let polling = false;

    function refreshButton() {
        return document.getElementById("dealsRefreshBtn");
    }

    function showProgress(done, total) {
        progress.classList.remove("hidden");
        // Live-Sync pausieren, solange geladen wird (sonst halb fertige Liste)
        progress.setAttribute("data-blocks-live", "");
        const percent = total > 0 ? Math.max(4, Math.round((done / total) * 100)) : 4;
        progressBar.style.width = `${percent}%`;
        progressText.textContent = total > 0
            ? `Suche Angebote … ${done} von ${total}`
            : "Angebote werden geladen …";
        refreshButton()?.classList.add("is-busy");
    }

    function hideProgress() {
        progress.classList.add("hidden");
        progress.removeAttribute("data-blocks-live");
        progressBar.style.width = "0";
        refreshButton()?.classList.remove("is-busy");
    }

    async function poll() {
        if (polling) return;
        polling = true;
        let sawRunning = false;
        let idleChecks = 0;

        try {
            for (;;) {
                const res = await fetch(page.dataset.statusUrl, { cache: "no-store", credentials: "same-origin" });
                const status = await res.json();

                if (status.syncing) {
                    sawRunning = true;
                    showProgress(status.done, status.total);
                } else if (!sawRunning && idleChecks < 3) {
                    // Thread ist evtl. noch nicht gestartet – kurz warten, bevor wir aufgeben
                    idleChecks += 1;
                    showProgress(0, 0);
                } else {
                    progressBar.style.width = "100%";
                    if (status.error) {
                        App.toast("Angebote konnten nicht geladen werden.", "error");
                    } else {
                        App.toast(`${status.count} Angebote geladen`);
                    }
                    await App.refresh();
                    hideProgress();
                    return;
                }
                await new Promise((r) => setTimeout(r, POLL_MS));
            }
        } catch (err) {
            console.error(err);
            hideProgress();
        } finally {
            polling = false;
        }
    }

    async function startSync() {
        if (polling) return;
        showProgress(0, 0);
        const body = new FormData();
        body.append("csrfmiddlewaretoken", App.csrf());
        try {
            const res = await fetch(page.dataset.syncUrl, {
                method: "POST",
                body,
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: "same-origin",
            });
            const data = await res.json();
            if (!data.ok) {
                hideProgress();
                App.toast(data.error || "Aktualisieren nicht möglich.", "error");
                if (data.redirect) setTimeout(() => window.location.assign(data.redirect), 1200);
                return;
            }
            poll();
        } catch (err) {
            console.error(err);
            hideProgress();
            App.toast("Keine Verbindung – bitte nochmal versuchen.", "error");
        }
    }

    document.addEventListener("click", (event) => {
        if (event.target.closest("#dealsRefreshBtn")) {
            startSync();
            return;
        }

        const imageButton = event.target.closest(".deal-image-button:not(.broken)");
        if (imageButton) {
            const image = imageButton.querySelector("img");
            const modalImage = document.getElementById("image-modal-content");
            modalImage.src = image.src;
            modalImage.alt = image.alt;
            document.getElementById("image-modal").classList.add("active");
        }
    });

    if (page.dataset.syncing) {
        // Läuft schon (z.B. von einem anderen Gerät gestartet) → Fortschritt anzeigen
        poll();
    } else if (page.dataset.autoRefresh) {
        // Angebote älter als ein Tag → still im Hintergrund neu laden
        startSync();
    }
});
