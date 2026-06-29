// ------------------------------------------------------------
// Popup helpers
// ------------------------------------------------------------

function openPopup() {
    const overlay = document.getElementById("popup-overlay");
    if (overlay) {
        overlay.style.display = "flex";
        overlay.classList.remove("hidden");
    }
}

function closePopup() {
    const overlay = document.getElementById("popup-overlay");
    if (overlay) {
        overlay.style.display = "none";
        overlay.classList.add("hidden");
    }
}

function openPopupFromTemplate(templateId) {
    const tpl = document.getElementById(templateId);
    if (!tpl) return;
    const content = document.getElementById("popup-content");
    content.innerHTML = tpl.innerHTML;
    openPopup();
}

// Close popup when clicking outside the box
document.addEventListener("click", function (e) {
    const overlay = document.getElementById("popup-overlay");
    const box = document.getElementById("popup-box");
    if (!overlay || !box) return;
    if (overlay.classList.contains("hidden")) return;
    if (!box.contains(e.target) && e.target.id !== "popup-close") {
        closePopup();
    }
});
