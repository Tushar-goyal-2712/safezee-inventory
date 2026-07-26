"use strict";

/* ============================================================
   SAFEZEE Inventory — dashboard behaviour
   Vanilla JS only. Uses the Fetch API. No frameworks.
   ============================================================ */

(function () {
    /* ---------------- CSRF helper ---------------- */
    function getCookie(name) {
        const match = document.cookie.match(
            new RegExp("(^| )" + name + "=([^;]+)")
        );
        return match ? decodeURIComponent(match[2]) : null;
    }
    const CSRF_TOKEN = getCookie("csrftoken");

    /* ---------------- Toast helper ---------------- */
    function showToast(message, variant) {
        variant = variant || "success";
        const container = document.getElementById("sz-toast-container");
        const wrapper = document.createElement("div");
        wrapper.className =
            "toast sz-toast align-items-center text-bg-" +
            (variant === "success" ? "dark" : "danger") +
            " border-0";
        wrapper.setAttribute("role", "alert");
        wrapper.innerHTML =
            '<div class="d-flex">' +
            '<div class="toast-body">' +
            (variant === "success"
                ? '<i class="bi bi-check-circle-fill me-2"></i>'
                : '<i class="bi bi-exclamation-triangle-fill me-2"></i>') +
            escapeHtml(message) +
            "</div>" +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
            "</div>";
        container.appendChild(wrapper);
        const toast = new bootstrap.Toast(wrapper, { delay: 3500 });
        toast.show();
        wrapper.addEventListener("hidden.bs.toast", () => wrapper.remove());
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    /* ---------------- Locate the Godown card ---------------- */
    function getGodownCard() {
        return document.querySelector('.sz-card[data-is-godown="true"]');
    }

    function getGodownQtyEl(itemId) {
        const godownCard = getGodownCard();
        if (!godownCard) return null;
        const row = godownCard.querySelector(
            '.sz-item-row[data-item-id="' + itemId + '"]'
        );
        return row ? row.querySelector(".sz-qty-display") : null;
    }

    /* ============================================================
       EDIT / SAVE / CANCEL per location card
       ============================================================ */
    document.querySelectorAll(".sz-card").forEach((card) => {
        const editBtn = card.querySelector(".js-edit-btn");
        const editActions = card.querySelector(".sz-edit-actions");
        const saveBtn = card.querySelector(".js-save-btn");
        const cancelBtn = card.querySelector(".js-cancel-btn");
        const rows = Array.from(card.querySelectorAll(".sz-item-row"));
        const isGodown = card.dataset.isGodown === "true";
        const locationId = card.dataset.locationId;

        // Tracks Godown on-screen deltas caused by editing THIS
        // (non-Godown) card, so Cancel can precisely undo them.
        let godownDeltaByItem = {};

        function enterEditMode() {
            editBtn.classList.add("d-none");
            editActions.classList.remove("d-none");
            rows.forEach((row) => {
                row.classList.add("sz-row-editing");
                row.querySelector(".sz-qty-display").classList.add("d-none");
                const editor = row.querySelector(".sz-qty-editor");
                editor.classList.remove("d-none");
                editor.classList.add("d-flex");
            });
            // Lock every OTHER card's edit button while this one is open.
            document.querySelectorAll(".sz-card").forEach((other) => {
                if (other !== card) {
                    other.querySelector(".js-edit-btn").disabled = true;
                }
            });
        }

        function exitEditMode() {
            editBtn.classList.remove("d-none");
            editActions.classList.add("d-none");
            rows.forEach((row) => {
                row.classList.remove("sz-row-editing");
                row.querySelector(".sz-qty-display").classList.remove("d-none");
                const editor = row.querySelector(".sz-qty-editor");
                editor.classList.add("d-none");
                editor.classList.remove("d-flex");
            });
            document.querySelectorAll(".sz-card").forEach((other) => {
                other.querySelector(".js-edit-btn").disabled = false;
            });
        }

        editBtn.addEventListener("click", () => {
            godownDeltaByItem = {};
            enterEditMode();
        });

        cancelBtn.addEventListener("click", () => {
            // Restore this card's displayed + staged values.
            rows.forEach((row) => {
                const original = parseInt(row.dataset.originalQuantity, 10);
                row.querySelector(".sz-qty-value").textContent = original;
                row.querySelector(".sz-qty-value").classList.remove("sz-qty-dirty");
                row.querySelector(".sz-qty-display").textContent = original;
            });

            // Undo any mirrored Godown display changes this card caused.
            if (!isGodown) {
                Object.keys(godownDeltaByItem).forEach((itemId) => {
                    const el = getGodownQtyEl(itemId);
                    if (!el) return;
                    const current = parseInt(el.textContent, 10);
                    el.textContent = current - godownDeltaByItem[itemId];
                });
            }
            godownDeltaByItem = {};
            exitEditMode();
        });

        rows.forEach((row) => {
            const itemId = row.dataset.itemId;
            const minusBtn = row.querySelector(".js-qty-minus");
            const plusBtn = row.querySelector(".js-qty-plus");
            const valueEl = row.querySelector(".sz-qty-value");

            function currentValue() {
                return parseInt(valueEl.textContent, 10);
            }

            function markDirty() {
                const original = parseInt(row.dataset.originalQuantity, 10);
                valueEl.classList.toggle("sz-qty-dirty", currentValue() !== original);
            }

            function applyGodownMirror(delta) {
                if (isGodown) return; // editing Godown itself never mirrors
                const godownEl = getGodownQtyEl(itemId);
                if (!godownEl) return;
                godownEl.textContent = parseInt(godownEl.textContent, 10) - delta;
                godownDeltaByItem[itemId] = (godownDeltaByItem[itemId] || 0) - delta;
            }

            plusBtn.addEventListener("click", () => {
                // Increasing a non-Godown location consumes 1 from Godown.
                if (!isGodown) {
                    const godownEl = getGodownQtyEl(itemId);
                    const godownQty = godownEl ? parseInt(godownEl.textContent, 10) : 0;
                    if (godownQty <= 0) {
                        showToast("Not enough stock available in Godown", "error");
                        return;
                    }
                }
                valueEl.textContent = currentValue() + 1;
                markDirty();
                applyGodownMirror(1);
            });

            minusBtn.addEventListener("click", () => {
                if (currentValue() <= 0) return;
                valueEl.textContent = currentValue() - 1;
                markDirty();
                applyGodownMirror(-1);
            });
        });

        saveBtn.addEventListener("click", () => {
            const changes = rows
                .map((row) => ({
                    item_id: parseInt(row.dataset.itemId, 10),
                    quantity: parseInt(
                        row.querySelector(".sz-qty-value").textContent,
                        10
                    ),
                    original: parseInt(row.dataset.originalQuantity, 10),
                }))
                .filter((c) => c.quantity !== c.original);

            if (changes.length === 0) {
                exitEditMode();
                return;
            }

            saveBtn.disabled = true;
            cancelBtn.disabled = true;

            fetch(window.SZ_URLS.saveInventory, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": CSRF_TOKEN,
                },
                body: JSON.stringify({
                    location_id: locationId,
                    items: changes.map((c) => ({
                        item_id: c.item_id,
                        quantity: c.quantity,
                    })),
                }),
            })
                .then((res) => res.json().then((data) => ({ status: res.status, data })))
                .then(({ status, data }) => {
                    if (status !== 200 || !data.ok) {
                        throw new Error(data.message || "Could not save changes.");
                    }

                    // Commit new baseline values for this card.
                    rows.forEach((row) => {
                        const itemId = row.dataset.itemId;
                        if (data.location_rows[itemId] !== undefined) {
                            const qty = data.location_rows[itemId];
                            row.dataset.originalQuantity = qty;
                            row.querySelector(".sz-qty-display").textContent = qty;
                            row.querySelector(".sz-qty-value").textContent = qty;
                        }
                        row.querySelector(".sz-qty-value").classList.remove("sz-qty-dirty");
                    });

                    // Commit new baseline values for Godown (if mirrored).
                    if (data.godown_rows && Object.keys(data.godown_rows).length) {
                        const godownCard = getGodownCard();
                        Object.keys(data.godown_rows).forEach((itemId) => {
                            const qty = data.godown_rows[itemId];
                            const gRow = godownCard.querySelector(
                                '.sz-item-row[data-item-id="' + itemId + '"]'
                            );
                            if (gRow) {
                                gRow.dataset.originalQuantity = qty;
                                gRow.querySelector(".sz-qty-display").textContent = qty;
                                gRow.querySelector(".sz-qty-value").textContent = qty;
                            }
                        });
                    }

                    godownDeltaByItem = {};
                    exitEditMode();
                    showToast("Inventory updated.");
                })
                .catch((err) => {
                    showToast(err.message, "error");
                    // Revert on-screen changes since the transaction failed.
                    cancelBtn.click();
                })
                .finally(() => {
                    saveBtn.disabled = false;
                    cancelBtn.disabled = false;
                });
        });
    });

    /* ============================================================
       ADD ITEM
       ============================================================ */
    const addItemForm = document.getElementById("addItemForm");
    if (addItemForm) {
        const errorBox = document.getElementById("addItemError");
        addItemForm.addEventListener("submit", (e) => {
            e.preventDefault();
            errorBox.classList.add("d-none");
            const submitBtn = addItemForm.querySelector('button[type="submit"]');
            toggleSpinner(submitBtn, true);

            const formData = new FormData(addItemForm);
            fetch(window.SZ_URLS.addItem, {
                method: "POST",
                headers: { "X-CSRFToken": CSRF_TOKEN },
                body: formData,
            })
                .then((res) => res.json().then((data) => ({ status: res.status, data })))
                .then(({ status, data }) => {
                    if (status !== 200 || !data.ok) {
                        const msg = data.errors
                            ? Object.values(data.errors).flat().join(" ")
                            : "Could not add item.";
                        throw new Error(msg);
                    }
                    window.location.reload();
                })
                .catch((err) => {
                    errorBox.textContent = err.message;
                    errorBox.classList.remove("d-none");
                    toggleSpinner(submitBtn, false);
                });
        });
    }

    /* ============================================================
       ADD LOCATION
       ============================================================ */
    const addLocationForm = document.getElementById("addLocationForm");
    if (addLocationForm) {
        const errorBox = document.getElementById("addLocationError");
        addLocationForm.addEventListener("submit", (e) => {
            e.preventDefault();
            errorBox.classList.add("d-none");
            const submitBtn = addLocationForm.querySelector('button[type="submit"]');
            toggleSpinner(submitBtn, true);

            const formData = new FormData(addLocationForm);
            fetch(window.SZ_URLS.addLocation, {
                method: "POST",
                headers: { "X-CSRFToken": CSRF_TOKEN },
                body: formData,
            })
                .then((res) => res.json().then((data) => ({ status: res.status, data })))
                .then(({ status, data }) => {
                    if (status !== 200 || !data.ok) {
                        const msg = data.errors
                            ? Object.values(data.errors).flat().join(" ")
                            : "Could not add location.";
                        throw new Error(msg);
                    }
                    window.location.reload();
                })
                .catch((err) => {
                    errorBox.textContent = err.message;
                    errorBox.classList.remove("d-none");
                    toggleSpinner(submitBtn, false);
                });
        });
    }

    function toggleSpinner(button, loading) {
        button.disabled = loading;
        button.querySelector(".btn-label").classList.toggle("d-none", loading);
        button.querySelector(".spinner-border").classList.toggle("d-none", !loading);
    }

    /* ============================================================
       DELETE ITEM
       ============================================================ */
    document.querySelectorAll(".js-delete-item").forEach((btn) => {
        btn.addEventListener("click", () => {
            const itemId = btn.dataset.itemId;
            const itemName = btn.dataset.itemName;
            if (!window.confirm(`Delete "${itemName}" from all locations? This cannot be undone.`)) {
                return;
            }
            fetch(window.SZ_URLS.deleteItem + itemId + "/delete/", {
                method: "POST",
                headers: { "X-CSRFToken": CSRF_TOKEN },
            })
                .then((res) => res.json().then((data) => ({ status: res.status, data })))
                .then(({ status, data }) => {
                    if (status !== 200 || !data.ok) {
                        throw new Error(data.message || "Could not delete item.");
                    }
                    document
                        .querySelectorAll('.sz-item-row[data-item-id="' + itemId + '"]')
                        .forEach((row) => row.remove());
                    showToast(data.message);
                })
                .catch((err) => showToast(err.message, "error"));
        });
    });

    /* ============================================================
       SEARCH (instant, client-side, across all cards)
       ============================================================ */
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        searchInput.addEventListener("input", () => {
            const query = searchInput.value.trim().toLowerCase();
            let anyCardVisible = false;

            document.querySelectorAll(".sz-location-col").forEach((col) => {
                const rows = col.querySelectorAll(".sz-item-row");
                let visibleCount = 0;

                rows.forEach((row) => {
                    const matches = !query || row.dataset.itemName.includes(query);
                    row.classList.toggle("sz-row-hidden", !matches);
                    if (matches) visibleCount += 1;
                });

                const cardHasRows = rows.length > 0;
                const shouldShowCard = !cardHasRows || visibleCount > 0;
                col.classList.toggle("d-none", !shouldShowCard);
                if (shouldShowCard) anyCardVisible = true;
            });

            document
                .getElementById("searchEmptyState")
                .classList.toggle("d-none", anyCardVisible || !query);
        });
    }
})();
