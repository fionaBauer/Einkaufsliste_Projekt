/**
 * Barcode Scanner using html5-qrcode (works on Safari, Chrome, iOS, Android)
 */

let barcodeMode = null;
let barcodeShoppingListId = null;
let html5QrCode = null;

const UNITS = [
    ["g", "g"], ["kg", "kg"], ["ml", "ml"], ["l", "l"],
    ["pcs", "Stück"], ["pkg", "Packung"], ["el", "EL"], ["tl", "TL"]
];

function openBarcodeScanner(mode, shoppingListId) {
    barcodeMode = mode;
    barcodeShoppingListId = shoppingListId || null;
    document.getElementById("barcodeScannerModal").classList.remove("hidden");
    loadHtml5QrCode();
}

function closeBarcodeScanner() {
    stopScanner();
    document.getElementById("barcodeScannerModal").classList.add("hidden");
    document.getElementById("barcodeResultModal").classList.add("hidden");
}

function loadHtml5QrCode() {
    if (window.Html5Qrcode) {
        startScanner();
        return;
    }
    const script = document.createElement("script");
    script.src = "/static/global/js/vendor/html5-qrcode.min.js";
    script.onload = () => startScanner();
    script.onerror = () => {
        document.querySelector(".barcode-hint").textContent = "Scanner nicht verfügbar — bitte manuell eingeben";
    };
    document.head.appendChild(script);
}

function startScanner() {
    const container = document.getElementById("barcodeQrReader");
    if (!container) return;

    // Clear previous instance
    container.innerHTML = "";

    try {
        html5QrCode = new Html5Qrcode("barcodeQrReader");
        html5QrCode.start(
            { facingMode: "environment" },
            {
                fps: 10,
                qrbox: { width: 250, height: 120 },
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.UPC_E,
                    Html5QrcodeSupportedFormats.CODE_128,
                ],
            },
            (decodedText) => {
                stopScanner();
                document.getElementById("barcodeScannerModal").classList.add("hidden");
                handleBarcode(decodedText);
            },
            (errorMessage) => { /* ignore scan errors */ }
        ).catch(err => {
            document.querySelector(".barcode-hint").textContent = "Kamera nicht verfügbar — bitte manuell eingeben";
        });
    } catch(e) {
        document.querySelector(".barcode-hint").textContent = "Scanner nicht verfügbar — bitte manuell eingeben";
    }
}

function stopScanner() {
    if (html5QrCode) {
        html5QrCode.stop().catch(() => {});
        html5QrCode = null;
    }
}

async function handleBarcode(barcode) {
    try {
        const res = await fetch(`/api/barcode/?barcode=${encodeURIComponent(barcode)}`);
        const data = await res.json();
        showBarcodeResult(data);
    } catch(e) {
        alert("Fehler beim Nachschlagen des Barcodes.");
    }
}

function showBarcodeResult(data) {
    const modal = document.getElementById("barcodeResultModal");
    const title = document.getElementById("barcodeResultTitle");
    const body = document.getElementById("barcodeResultBody");
    const actions = document.getElementById("barcodeResultActions");

    if (!data.found) {
        title.textContent = "Produkt nicht gefunden";
        body.innerHTML = `
            <p style="color:#888;font-size:14px;">Barcode: ${data.barcode}</p>
            <p style="font-size:14px;">Produkt konnte nicht identifiziert werden.</p>
        `;
        actions.innerHTML = `<button class="btn btn-secondary" onclick="document.getElementById('barcodeResultModal').classList.add('hidden')">Schließen</button>`;
        modal.classList.remove("hidden");
        return;
    }

    // Parse quantity from product info e.g. "200g" → qty=200, unit=g
    let preQty = "1";
    let preUnit = "pcs";
    if (data.quantity) {
        const match = data.quantity.match(/^(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l|cl)/i);
        if (match) {
            preQty = match[1].replace(",", ".");
            const u = match[2].toLowerCase();
            preUnit = u === "cl" ? "ml" : u;
            if (u === "cl") preQty = String(parseFloat(preQty) * 10);
        }
    }

    const unitOptions = UNITS.map(([v, l]) =>
        `<option value="${v}" ${v === preUnit ? "selected" : ""}>${l}</option>`
    ).join("");

    let inventoryInfo = "";
    if (data.in_inventory) {
        inventoryInfo = `
            <div class="barcode-result-inventory">
                📦 Im Inventar: ${data.inventory_quantity || "Vorhanden"} ${data.inventory_unit || ""}
            </div>`;
    }

    const brandInfo = data.brand ? `<span style="font-size:12px;color:#888;">${data.brand}</span>` : "";

    body.innerHTML = `
        <div class="barcode-result-fields">
            <div class="barcode-field-group">
                <label style="font-size:12px;font-weight:600;color:#666;display:block;margin-bottom:4px;">Name</label>
                <input type="text" id="barcode-name" value="${data.matched_name}"
                    style="width:100%;padding:8px 10px;border:1.5px solid #e5e5e5;border-radius:8px;font-size:14px;box-sizing:border-box;font-family:inherit;">
            </div>
            ${data.product_name !== data.matched_name ? `<p style="font-size:12px;color:#aaa;margin:4px 0 8px;">Produktname: ${data.product_name} ${brandInfo}</p>` : brandInfo ? `<p style="font-size:12px;color:#aaa;margin:4px 0 8px;">${brandInfo}</p>` : ""}
            ${inventoryInfo}
            <div class="barcode-qty-row" style="margin-top:8px;">
                <div>
                    <label style="font-size:12px;font-weight:600;color:#666;display:block;margin-bottom:4px;">Menge</label>
                    <input type="number" id="barcode-qty" value="${preQty}" min="0" step="0.01"
                        style="width:80px;padding:8px 10px;border:1.5px solid #e5e5e5;border-radius:8px;font-size:14px;font-family:inherit;">
                </div>
                <div>
                    <label style="font-size:12px;font-weight:600;color:#666;display:block;margin-bottom:4px;">Einheit</label>
                    <select id="barcode-unit" style="padding:8px 10px;border:1.5px solid #e5e5e5;border-radius:8px;font-size:14px;font-family:inherit;">${unitOptions}</select>
                </div>
            </div>
        </div>
    `;

    title.textContent = "Produkt gefunden";

    if (barcodeMode === "inventory") {
        actions.innerHTML = `
            <button class="btn btn-secondary" onclick="document.getElementById('barcodeResultModal').classList.add('hidden')">Abbrechen</button>
            <button class="btn btn-primary" onclick='addBarcodeToInventory(${JSON.stringify(data)})'>Zum Inventar</button>
        `;
    } else {
        let removeBtn = data.in_inventory
            ? `<button class="btn btn-secondary" onclick="removeFromInventory(${data.inventory_id})">Aus Inventar entfernen</button>`
            : "";
        actions.innerHTML = `
            <button class="btn btn-secondary" onclick="document.getElementById('barcodeResultModal').classList.add('hidden')">Abbrechen</button>
            ${removeBtn}
            <button class="btn btn-primary" onclick='addBarcodeToShopping(${JSON.stringify(data)})'>Zur Einkaufsliste</button>
        `;
    }

    modal.classList.remove("hidden");
}

async function addBarcodeToInventory(data) {
    const qty = document.getElementById("barcode-qty")?.value || "1";
    const unit = document.getElementById("barcode-unit")?.value || "g";
    const name = document.getElementById("barcode-name")?.value.trim() || data.matched_name;
    const res = await fetch("/inventory/barcode-add/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        body: JSON.stringify({ matched_name: name, product_name: data.product_name, quantity: qty, unit }),
    });
    const result = await res.json();
    if (result.success) {
        document.getElementById("barcodeResultModal").classList.add("hidden");
        showGlobalToast(`${name} zum Inventar hinzugefügt`, "success");
        setTimeout(() => window.location.reload(), 800);
    }
}

async function addBarcodeToShopping(data) {
    const qty = document.getElementById("barcode-qty")?.value || "1";
    const unit = document.getElementById("barcode-unit")?.value || "g";
    const name = document.getElementById("barcode-name")?.value.trim() || data.matched_name;
    const res = await fetch("/shopping/barcode-add/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        body: JSON.stringify({ matched_name: name, product_name: data.product_name, quantity: qty, unit, shopping_list_id: barcodeShoppingListId }),
    });
    const result = await res.json();
    if (result.success) {
        document.getElementById("barcodeResultModal").classList.add("hidden");
        showGlobalToast(`${name} zur Einkaufsliste hinzugefügt`, "success");
        setTimeout(() => window.location.reload(), 800);
    }
}

async function removeFromInventory(inventoryId) {
    const res = await fetch(`/inventory/barcode-remove/${inventoryId}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        body: JSON.stringify({}),
    });
    const result = await res.json();
    if (result.success) {
        document.querySelector(".barcode-result-inventory")?.remove();
        showGlobalToast("Aus Inventar entfernt", "success");
    }
}

function getCsrfToken() {
    return document.cookie.split("; ").find(r => r.startsWith("csrftoken="))?.split("=")[1] || "";
}

function showGlobalToast(message, type = "success") {
    const container = document.querySelector(".toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-icon">✔</span><span class="toast-text">${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => { toast.classList.add("hide"); setTimeout(() => toast.remove(), 250); }, 2500);
}

document.addEventListener("DOMContentLoaded", () => {
    // Ensure modals start closed
    document.getElementById("barcodeScannerModal")?.classList.add("hidden");
    document.getElementById("barcodeResultModal")?.classList.add("hidden");

    document.getElementById("barcodeCloseBtn")?.addEventListener("click", closeBarcodeScanner);

window.addEventListener("pageshow", () => {
    document.getElementById("barcodeScannerModal")?.classList.add("hidden");
    document.getElementById("barcodeResultModal")?.classList.add("hidden");
    stopScanner();
});
    document.getElementById("barcodeScannerModal")?.addEventListener("click", e => {
        if (e.target === document.getElementById("barcodeScannerModal")) closeBarcodeScanner();
    });
    document.getElementById("barcodeManualBtn")?.addEventListener("click", () => {
        const val = document.getElementById("barcodeManualInput").value.trim();
        if (val) handleBarcode(val);
    });
    document.getElementById("barcodeManualInput")?.addEventListener("keydown", e => {
        if (e.key === "Enter") {
            const val = e.target.value.trim();
            if (val) handleBarcode(val);
        }
    });
    document.getElementById("shoppingScanBtn")?.addEventListener("click", function() {
        openBarcodeScanner("shopping", this.dataset.listId || null);
    });
});