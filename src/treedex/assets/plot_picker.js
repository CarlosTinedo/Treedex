/* Native disclosure keyboard support, plus Escape and outside-click dismissal. */
(() => {
  function closePicker(restoreFocus) {
    const picker = document.getElementById("plot-picker");
    if (!picker || !picker.open) return;
    picker.open = false;
    if (restoreFocus) picker.querySelector("summary").focus();
  }
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") closePicker(true);
  });
  document.addEventListener("pointerdown", event => {
    const picker = document.getElementById("plot-picker");
    if (picker && !picker.contains(event.target)) closePicker(false);
  });
  document.addEventListener("click", event => {
    if (event.target.closest("#plot-picker-items button")) {
      // Submenu buttons are replaced by Dash. Keep focus on a stable element
      // so the top bar remains expanded when the clicked button disappears.
      document.getElementById("plot-picker-label").focus();
    }
  });
})();
