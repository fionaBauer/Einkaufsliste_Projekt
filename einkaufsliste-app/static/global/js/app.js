/**
 * Prepio – App-Shell
 *
 * - Stille Updates: Formulare, die auf die aktuelle Seite zurückleiten, werden im
 *   Hintergrund abgeschickt. Die neue Seite wird per DOM-Morphing eingespielt –
 *   kein Reload, Scrollposition, offene Kategorien und Eingaben bleiben erhalten.
 * - Live-Sync: Seiten mit data-live="morph" aktualisieren sich regelmäßig (und beim
 *   Zurückkehren in die App) selbst, damit Änderungen anderer Haushaltsmitglieder
 *   ohne manuellen Reload erscheinen.
 * - Navigation: schwebende Tab-Pille mit gleitendem Indikator, "Mehr"-Bottom-Sheet,
 *   Prefetching beim Antippen.
 *
 * Markup-Hooks für Seiten:
 *   data-key="…"             stabile Identität für Listeneinträge beim Morphen
 *   data-morph-skip          Inhalt wird von Seiten-JS verwaltet → nie anfassen
 *   data-morph-keep-class    class-Attribut bleibt (UI-Zustand wie "hidden"/"selected")
 *   data-native              Formular normal abschicken (kein stilles Update)
 *   data-ajax                auch Formulare mit anderer action still abschicken
 */
(function () {
    "use strict";

    const App = (window.App = window.App || {});
    const main = document.getElementById("app-main");
    const LIVE_INTERVAL_MS = 15000;

    let inflight = 0;
    let lastInteraction = 0;
    const liveHandlers = [];

    /* ───────────────────────── Helpers ───────────────────────── */

    App.csrf = function () {
        const row = document.cookie.split("; ").find((r) => r.startsWith("csrftoken="));
        return row ? decodeURIComponent(row.split("=")[1]) : "";
    };

    function emit(name, detail) {
        document.dispatchEvent(new CustomEvent(name, { detail }));
    }

    /* ───────────────────────── Toasts ───────────────────────── */

    const toastContainer = document.getElementById("toast-container");

    function scheduleToastHide(toast) {
        if (toast.dataset.scheduled) return;
        toast.dataset.scheduled = "1";
        setTimeout(() => {
            toast.classList.add("hide");
            setTimeout(() => toast.remove(), 260);
        }, 2600);
    }

    App.toast = function (message, type = "success") {
        if (!toastContainer) return;
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        const icon = document.createElement("span");
        icon.className = "toast-icon";
        icon.textContent = type === "error" || type === "warning" ? "!" : "✓";
        const text = document.createElement("span");
        text.className = "toast-text";
        text.textContent = message;
        toast.append(icon, text);
        toastContainer.appendChild(toast);
        scheduleToastHide(toast);
    };

    function adoptToasts(doc) {
        const incoming = doc.getElementById("toast-container");
        if (!incoming || !toastContainer) return;
        incoming.querySelectorAll(".toast").forEach((t) => {
            const toast = document.importNode(t, true);
            toastContainer.appendChild(toast);
            scheduleToastHide(toast);
        });
    }

    toastContainer?.querySelectorAll(".toast").forEach(scheduleToastHide);

    /* ───────────────────────── Fortschrittsbalken ───────────────────────── */

    const progress = document.createElement("div");
    progress.className = "app-progress";
    document.body.appendChild(progress);
    let progressTimer = null;

    function startProgress() {
        clearTimeout(progressTimer);
        // Erst nach kurzer Zeit zeigen – schnelle Updates sollen gar nicht "blinken"
        progressTimer = setTimeout(() => {
            progress.classList.remove("done");
            void progress.offsetWidth;
            progress.classList.add("running");
        }, 180);
    }

    function stopProgress() {
        clearTimeout(progressTimer);
        if (progress.classList.contains("running")) {
            progress.classList.remove("running");
            progress.classList.add("done");
        }
    }

    /* ───────────────────────── DOM-Morphing ───────────────────────── */

    function nodeKey(node) {
        if (node.nodeType !== 1) return null;
        return node.id || node.getAttribute("data-key") || null;
    }

    function isFormControl(el) {
        return el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT";
    }

    function selectDefaultValue(select) {
        const opts = Array.from(select.options);
        const def = opts.find((o) => o.defaultSelected) || opts[0];
        return def ? def.value : "";
    }

    // "Dirty" = vom Nutzer (oder Seiten-JS) verändert und noch nicht vom Server bestätigt.
    // Solche Felder lässt das Morphing in Ruhe, saubere Felder folgen dem Server.
    function isDirty(el) {
        if (el.tagName === "INPUT") {
            if (el.type === "checkbox" || el.type === "radio") return el.checked !== el.defaultChecked;
            if (el.type === "hidden" || el.type === "file") return false;
            return el.value !== el.defaultValue;
        }
        if (el.tagName === "TEXTAREA") return el.value !== el.defaultValue;
        if (el.tagName === "SELECT") return !el.multiple && el.value !== selectDefaultValue(el);
        return false;
    }

    function syncAttributes(from, to) {
        const keepClass = from.hasAttribute("data-morph-keep-class");
        for (const attr of Array.from(from.attributes)) {
            if (keepClass && attr.name === "class") continue;
            if (!to.hasAttribute(attr.name)) from.removeAttribute(attr.name);
        }
        for (const attr of Array.from(to.attributes)) {
            if (keepClass && attr.name === "class") continue;
            if (from.getAttribute(attr.name) !== attr.value) from.setAttribute(attr.name, attr.value);
        }
    }

    function morphElement(from, to) {
        if (from.hasAttribute("data-morph-skip")) return;

        const control = isFormControl(from);
        const dirty = control && (isDirty(from) || from === document.activeElement);

        syncAttributes(from, to);

        if (from.tagName === "TEMPLATE") {
            if (from.innerHTML !== to.innerHTML) from.innerHTML = to.innerHTML;
            return;
        }

        if (from.tagName === "TEXTAREA") {
            if (!dirty) {
                from.defaultValue = to.textContent;
                from.value = to.textContent;
            }
            return;
        }

        if (from.tagName !== "SELECT" || !dirty) {
            morphChildren(from, to);
        }

        if (control && !dirty) {
            if (from.tagName === "INPUT") {
                if (from.type === "checkbox" || from.type === "radio") {
                    from.checked = to.hasAttribute("checked");
                } else if (from.type !== "file") {
                    from.value = to.getAttribute("value") ?? "";
                }
            } else if (from.tagName === "SELECT") {
                Array.from(from.options).forEach((o) => { o.selected = o.defaultSelected; });
                if (!Array.from(from.options).some((o) => o.defaultSelected) && from.options.length) {
                    from.selectedIndex = 0;
                }
            }
        }
    }

    function morphNode(from, to) {
        if (from.nodeType === 1) {
            morphElement(from, to);
        } else if (from.nodeValue !== to.nodeValue) {
            from.nodeValue = to.nodeValue;
        }
    }

    function compatible(a, b) {
        return a.nodeType === b.nodeType && a.nodeName === b.nodeName;
    }

    function morphChildren(fromParent, toParent) {
        const keyed = new Map();
        for (const child of Array.from(fromParent.childNodes)) {
            const key = nodeKey(child);
            if (key) keyed.set(key, child);
        }

        let cursor = fromParent.firstChild;

        for (const toChild of Array.from(toParent.childNodes)) {
            const key = nodeKey(toChild);
            let match = null;

            if (key) {
                const candidate = keyed.get(key);
                if (candidate && compatible(candidate, toChild)) {
                    match = candidate;
                    keyed.delete(key);
                }
            } else if (cursor && !nodeKey(cursor) && compatible(cursor, toChild)) {
                match = cursor;
            }

            if (match) {
                if (match !== cursor) fromParent.insertBefore(match, cursor);
                morphNode(match, toChild);
                cursor = match.nextSibling;
            } else {
                fromParent.insertBefore(document.importNode(toChild, true), cursor);
            }
        }

        while (cursor) {
            const next = cursor.nextSibling;
            fromParent.removeChild(cursor);
            cursor = next;
        }
    }

    function applyDocument(doc, { url } = {}) {
        const newMain = doc.getElementById("app-main");
        if (!newMain || !main) return false;

        const scrollX = window.scrollX;
        const scrollY = window.scrollY;

        syncAttributes(main, newMain);
        morphChildren(main, newMain);
        if (doc.title) document.title = doc.title;
        adoptToasts(doc);

        // Höhe kann sich geändert haben – Scrollposition ausdrücklich halten
        if (window.scrollY !== scrollY) window.scrollTo(scrollX, scrollY);

        emit("app:morphed", { url });
        return true;
    }

    App.morph = function (html, opts) {
        const doc = new DOMParser().parseFromString(html, "text/html");
        return applyDocument(doc, opts);
    };

    /* ───────────────────────── Laden & Aktualisieren ───────────────────────── */

    async function fetchPage(url, init = {}) {
        inflight += 1;
        startProgress();
        try {
            const res = await fetch(url, {
                credentials: "same-origin",
                cache: "no-store",
                ...init,
                headers: { "X-App-Morph": "1", ...(init.headers || {}) },
            });
            const type = res.headers.get("content-type") || "";
            const html = type.includes("text/html") ? await res.text() : null;
            return { res, html };
        } finally {
            inflight -= 1;
            stopProgress();
        }
    }

    function samePath(a, b) {
        return new URL(a, location.href).pathname === new URL(b, location.href).pathname;
    }

    /**
     * Aktuelle Seite still neu laden und einmorphen.
     * Ersetzt window.location.reload() in den Seiten-Skripten.
     */
    App.refresh = async function ({ silent = false } = {}) {
        try {
            const { res, html } = await fetchPage(location.href);
            if (!samePath(res.url, location.href)) {
                // z.B. Session abgelaufen → Login
                location.assign(res.url);
                return;
            }
            if (html) App.morph(html, { url: location.href });
        } catch (err) {
            if (!silent) {
                console.error(err);
                location.reload();
            }
        }
    };

    /**
     * Zu einer URL wechseln. Gleiche Seite → still morphen, sonst normale Navigation.
     */
    let visitSeq = 0;

    App.visit = async function (url, { replace = false } = {}) {
        const target = new URL(url, location.href);
        const seq = ++visitSeq;
        if (!samePath(target.href, location.href)) {
            location.assign(target.href);
            return;
        }
        try {
            const { res, html } = await fetchPage(target.href);
            if (seq !== visitSeq) return; // inzwischen neuere Anfrage (z.B. weitergetippt)
            if (!samePath(res.url, target.href) || !html) {
                location.assign(res.url);
                return;
            }
            if (res.url !== location.href) {
                history[replace ? "replaceState" : "pushState"]({ appMorph: true }, "", res.url);
            }
            App.morph(html, { url: res.url });
        } catch (err) {
            console.error(err);
            location.assign(target.href);
        }
    };

    /* ───────────────────────── Formulare still abschicken ───────────────────────── */

    function setBusy(button, busy) {
        if (!button) return;
        button.disabled = busy;
        button.classList.toggle("is-loading", busy && button.classList.contains("btn"));
    }

    async function submitForm(form, submitter, method, action) {
        // POST nur einmal gleichzeitig (Doppelklick); GET (Suche) darf überholen
        if (method === "post" && form.dataset.submitting) return;
        form.dataset.submitting = "1";
        setBusy(submitter, true);

        let formData;
        try {
            formData = new FormData(form, submitter || undefined);
        } catch (_) {
            // Ältere Browser kennen den submitter-Parameter nicht
            formData = new FormData(form);
            if (submitter?.name) formData.append(submitter.name, submitter.value);
        }

        try {
            if (method === "get") {
                const url = new URL(action.href);
                url.search = new URLSearchParams(formData).toString();
                // replace: Tippen in der Suche soll nicht jeden Buchstaben in den Verlauf legen
                await App.visit(url.href, { replace: true });
                return;
            }

            const { res, html } = await fetchPage(action.href, { method: "POST", body: formData });

            if (!html) {
                location.assign(res.url);
                return;
            }

            if (samePath(res.url, location.href)) {
                // Erfolgreich (Redirect zurück): Formular zurücksetzen, damit die
                // Felder wieder "sauber" sind und den Server-Werten folgen.
                if (res.redirected) form.reset();
                if (res.url !== location.href) history.replaceState({ appMorph: true }, "", res.url);
                App.morph(html, { url: res.url });
                emit("app:submitted", { form, ok: res.ok });
            } else if (res.redirected) {
                location.assign(res.url);
            } else {
                // Antwort für eine andere Seite ohne Redirect: wie ein normaler Submit anzeigen
                document.open();
                document.write(html);
                document.close();
            }
        } catch (err) {
            console.error(err);
            App.toast("Keine Verbindung – bitte nochmal versuchen.", "error");
        } finally {
            delete form.dataset.submitting;
            if (submitter?.isConnected) setBusy(submitter, false);
        }
    }

    // Bubble-Phase auf window: läuft NACH allen Seiten-Handlern. Wer preventDefault()
    // aufruft (eigene AJAX-Logik, confirm() abgebrochen), wird hier nicht angefasst.
    window.addEventListener("submit", (event) => {
        if (event.defaultPrevented || !main) return;
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !main.contains(form)) return;
        if (form.hasAttribute("data-native")) return;
        if (form.target && form.target !== "_self") return;

        const submitter = event.submitter || null;
        const method = (submitter?.getAttribute("formmethod") || form.getAttribute("method") || "get").toLowerCase();
        const action = new URL(submitter?.getAttribute("formaction") || form.getAttribute("action") || location.href, location.href);

        if (action.origin !== location.origin) return;
        if (!samePath(action.href, location.href) && !form.hasAttribute("data-ajax")) return;
        if (method !== "get" && method !== "post") return;

        event.preventDefault();
        submitForm(form, submitter, method, action);
    });

    // Zurück/Vor innerhalb derselben Seite (z.B. nach einer Suche) → passenden Stand einmorphen
    window.addEventListener("popstate", () => App.refresh({ silent: true }));

    /* ───────────────────────── Live-Suche ───────────────────────── */

    let searchTimer = null;
    document.addEventListener("input", (event) => {
        const input = event.target;
        if (!input.matches?.(".filter-bar .search-input")) return;
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => input.form?.requestSubmit(), 320);
    });

    /* ───────────────────────── Live-Sync ───────────────────────── */

    App.onLive = function (fn) { liveHandlers.push(fn); };

    function overlayOpen() {
        return Boolean(document.querySelector(
            ".modal-overlay.active, .tab-more-menu.open, [data-blocks-live]"
        ));
    }

    function userBusy() {
        const el = document.activeElement;
        const typing = el && (el.tagName === "TEXTAREA" || el.tagName === "SELECT" ||
            (el.tagName === "INPUT" && !["checkbox", "radio", "button", "submit"].includes(el.type)));
        return typing || Date.now() - lastInteraction < 2500;
    }

    function liveTick() {
        if (document.hidden || inflight > 0 || overlayOpen() || userBusy()) return;
        if (main?.dataset.live === "morph") App.refresh({ silent: true });
        liveHandlers.forEach((fn) => {
            try { fn(); } catch (err) { console.error(err); }
        });
    }

    ["pointerdown", "keydown"].forEach((type) => {
        window.addEventListener(type, () => { lastInteraction = Date.now(); }, { passive: true, capture: true });
    });

    setInterval(liveTick, LIVE_INTERVAL_MS);

    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) setTimeout(liveTick, 50);
    });

    window.addEventListener("pageshow", (event) => {
        if (event.persisted) setTimeout(liveTick, 50);
    });

    /* ───────────────────────── Mitlaufende Kopfzeile ───────────────────────── */

    // Trennlinie unter dem Kopf erst, sobald etwas darunter durchscrollt
    function updateScrolled() {
        document.body.classList.toggle("is-scrolled", window.scrollY > 4);
    }
    window.addEventListener("scroll", updateScrolled, { passive: true });
    updateScrolled();

    // Höhe des Seitenkopfs als CSS-Variable → die "Zurück"-Leiste der Kategorien
    // bleibt direkt darunter hängen
    const headerObserver = "ResizeObserver" in window
        ? new ResizeObserver((entries) => {
            const height = entries[0].target.getBoundingClientRect().height;
            document.documentElement.style.setProperty("--header-h", `${Math.round(height)}px`);
        })
        : null;
    let observedHeader = null;

    function observeHeader() {
        const header = main?.querySelector(".page-header");
        if (!headerObserver || header === observedHeader) return;
        if (observedHeader) headerObserver.unobserve(observedHeader);
        observedHeader = header;
        if (header) headerObserver.observe(header);
    }
    observeHeader();
    document.addEventListener("app:morphed", observeHeader);

    /* ───────────────────────── Kategorie-Drilldown (Inventar & Zutaten) ───────────────────────── */

    let gridScrollY = 0;

    function showCategory(value) {
        const grid = document.getElementById("category-grid");
        const details = document.querySelectorAll(".category-detail");
        let shown = null;
        details.forEach((d) => {
            const match = value != null && d.dataset.category === value;
            d.classList.toggle("hidden", !match);
            if (match) shown = d;
        });
        grid?.classList.toggle("hidden", Boolean(shown));
        return shown;
    }

    document.addEventListener("click", (event) => {
        const card = event.target.closest(".category-card[data-category]");
        if (card) {
            gridScrollY = window.scrollY;
            if (showCategory(card.dataset.category)) window.scrollTo({ top: 0 });
            return;
        }
        if (event.target.closest(".detail-back-btn")) {
            showCategory(null);
            // zurück an die Stelle der Übersicht, an der man war
            window.scrollTo({ top: gridScrollY });
        }
    });

    // Nach dem Morphen: wurde die offene Kategorie leer (letzter Eintrag gelöscht),
    // zurück zur Übersicht statt einer leeren Seite.
    document.addEventListener("app:morphed", () => {
        const grid = document.getElementById("category-grid");
        if (grid?.classList.contains("hidden") && !document.querySelector(".category-detail:not(.hidden)")) {
            showCategory(null);
        }
    });

    /* ───────────────────────── Tab-Pille ───────────────────────── */

    const tabBar = document.getElementById("bottom-tab-bar");
    const indicator = tabBar?.querySelector(".tab-indicator");

    function moveIndicator(target, animate = true) {
        if (!indicator || !target || !tabBar.offsetParent) return;
        const barRect = tabBar.getBoundingClientRect();
        const rect = target.getBoundingClientRect();
        indicator.classList.toggle("no-anim", !animate);
        indicator.style.width = `${rect.width}px`;
        indicator.style.transform = `translateX(${rect.left - barRect.left}px)`;
        indicator.classList.add("ready");
    }

    function activeTab() {
        return tabBar?.querySelector(".tab-item.active, .tab-more-btn.active");
    }

    if (tabBar) {
        const tabs = Array.from(tabBar.querySelectorAll(".tab-item, .tab-more-btn"));
        tabs.forEach((t) => { t.dataset.initialActive = t.classList.contains("active") ? "1" : ""; });

        requestAnimationFrame(() => moveIndicator(activeTab(), false));
        window.addEventListener("resize", () => moveIndicator(activeTab(), false));

        // Aus dem Back-Forward-Cache zurück: Tab-Zustand der Seite wiederherstellen
        window.addEventListener("pageshow", (event) => {
            if (!event.persisted) return;
            tabs.forEach((t) => t.classList.toggle("active", t.dataset.initialActive === "1"));
            moveIndicator(activeTab(), false);
            setMoreOpen(false);
        });

        tabBar.addEventListener("click", (event) => {
            const tab = event.target.closest(".tab-item");
            if (!tab) return;
            if (tab.classList.contains("active")) {
                // Wie bei Instagram: aktiven Tab nochmal antippen → nach oben scrollen
                event.preventDefault();
                window.scrollTo({ top: 0, behavior: "smooth" });
                return;
            }
            tabBar.querySelectorAll(".tab-item, .tab-more-btn").forEach((t) => t.classList.toggle("active", t === tab));
            moveIndicator(tab);
        });
    }

    /* ───────────────────────── "Mehr"-Sheet ───────────────────────── */

    const moreTrigger = document.getElementById("tab-more-trigger");
    const moreMenu = document.getElementById("tab-more-menu");
    const moreOverlay = document.getElementById("tab-more-overlay");

    function setMoreOpen(open) {
        if (!moreMenu) return;
        moreMenu.style.transform = "";
        moreMenu.classList.toggle("open", open);
        moreOverlay.classList.toggle("open", open);
        moreTrigger.setAttribute("aria-expanded", String(open));
    }

    if (moreTrigger && moreMenu) {
        moreTrigger.addEventListener("click", () => setMoreOpen(!moreMenu.classList.contains("open")));
        moreOverlay.addEventListener("click", () => setMoreOpen(false));
        document.addEventListener("keydown", (e) => { if (e.key === "Escape") setMoreOpen(false); });

        // Nach unten wischen zum Schließen
        let startY = null;
        let delta = 0;
        moreMenu.addEventListener("touchstart", (e) => {
            startY = e.touches[0].clientY;
            delta = 0;
            moreMenu.classList.add("dragging");
        }, { passive: true });
        moreMenu.addEventListener("touchmove", (e) => {
            if (startY == null) return;
            delta = Math.max(0, e.touches[0].clientY - startY);
            moreMenu.style.transform = `translateY(${delta}px)`;
        }, { passive: true });
        moreMenu.addEventListener("touchend", () => {
            moreMenu.classList.remove("dragging");
            if (delta > 70) setMoreOpen(false);
            else moreMenu.style.transform = "";
            startY = null;
        });
    }

    /* ───────────────────────── Modals: Klick auf Hintergrund / Escape ───────────────────────── */

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        const open = Array.from(document.querySelectorAll(".modal-overlay.active")).pop();
        if (open && open.hasAttribute("data-generic-close")) open.classList.remove("active");
    });

    document.addEventListener("click", (event) => {
        const overlay = event.target.classList?.contains("modal-overlay") ? event.target : null;
        if (overlay && overlay.hasAttribute("data-generic-close")) overlay.classList.remove("active");
        const closer = event.target.closest("[data-close-modal]");
        if (closer) closer.closest(".modal-overlay")?.classList.remove("active");
    });

    /* ───────────────────────── Prefetching (Safari & Co.) ───────────────────────── */

    // Chrome/Edge erledigen das über <script type="speculationrules"> in base.html
    const hasSpeculationRules = Boolean(HTMLScriptElement.supports?.("speculationrules"));

    function prefetch(link) {
        const sw = navigator.serviceWorker?.controller;
        if (hasSpeculationRules || !sw || !link || link.hasAttribute("data-no-prefetch")) return;
        const url = new URL(link.href, location.href);
        if (url.origin !== location.origin || url.pathname === location.pathname) return;
        if (url.pathname.startsWith("/accounts/") || url.pathname.startsWith("/admin/")) return;
        sw.postMessage({ type: "prefetch", url: url.href });
    }

    document.addEventListener("touchstart", (e) => prefetch(e.target.closest?.("a[href]")), { passive: true });
    document.addEventListener("mousedown", (e) => prefetch(e.target.closest?.("a[href]")));

    let hoverTimer = null;
    document.addEventListener("mouseover", (e) => {
        const link = e.target.closest?.("a[href]");
        clearTimeout(hoverTimer);
        if (link) hoverTimer = setTimeout(() => prefetch(link), 70);
    });

    /* ───────────────────────── Service Worker ───────────────────────── */

    if ("serviceWorker" in navigator) {
        window.addEventListener("load", () => {
            navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((err) => {
                console.warn("Service Worker nicht registriert:", err);
            });
            // Alte Registrierung (lag unter /static/global/js/ und hat nie eine Seite kontrolliert)
            navigator.serviceWorker.getRegistrations().then((regs) => {
                regs.filter((r) => r.scope.includes("/static/")).forEach((r) => r.unregister());
            }).catch(() => {});
        });
    }
})();
