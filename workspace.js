/* Dash loads assets before the layout is necessarily mounted. */
(() => {
  "use strict";

  function initializeDivider() {
    const divider = document.getElementById("workspace-divider");
    if (!divider) return false;
    const workspace = divider.parentElement;
    const narrowScreen = window.matchMedia("(max-width: 760px)");
    let pointerId = null;
    let grabOffset = 0;
    let frame = null;

    function resize(percent) {
      if (narrowScreen.matches) return;
      const width = Math.min(80, Math.max(20, percent));
      workspace.style.setProperty("--tree-panel-width", `${width}%`);
      divider.setAttribute("aria-valuenow", String(Math.round(width)));
      // Notify responsive plots without sending any server callbacks.
      if (frame === null) {
        frame = requestAnimationFrame(() => {
          frame = null;
          window.dispatchEvent(new Event("resize"));
        });
      }
    }

    function finishDrag(event) {
      if (pointerId === null || (event && event.pointerId !== pointerId)) return;
      const previousPointer = pointerId;
      pointerId = null;
      workspace.classList.remove("is-resizing");
      if (divider.hasPointerCapture(previousPointer)) {
        divider.releasePointerCapture(previousPointer);
      }
    }

    divider.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || pointerId !== null || narrowScreen.matches) return;
      event.preventDefault();
      grabOffset = event.clientX - divider.getBoundingClientRect().left;
      pointerId = event.pointerId;
      divider.setPointerCapture(pointerId);
      divider.focus({preventScroll: true});
      workspace.classList.add("is-resizing");
    });
    divider.addEventListener("pointermove", (event) => {
      if (event.pointerId !== pointerId) return;
      const bounds = workspace.getBoundingClientRect();
      if (bounds.width > 0) {
        resize(100 * (event.clientX - bounds.left - grabOffset) / bounds.width);
      }
    });
    divider.addEventListener("pointerup", finishDrag);
    divider.addEventListener("pointercancel", finishDrag);
    divider.addEventListener("lostpointercapture", finishDrag);
    window.addEventListener("blur", () => finishDrag());
    narrowScreen.addEventListener("change", () => finishDrag());
    divider.addEventListener("dblclick", () => resize(35));
    divider.addEventListener("keydown", (event) => {
      const current = parseFloat(workspace.style.getPropertyValue("--tree-panel-width")) || 35;
      const step = event.shiftKey ? 10 : 2;
      const widths = {ArrowLeft: current - step, ArrowRight: current + step, Home: 20, End: 80};
      if (Object.prototype.hasOwnProperty.call(widths, event.key)) {
        event.preventDefault();
        resize(widths[event.key]);
      }
    });
    return true;
  }

  if (!initializeDivider()) {
    const observer = new MutationObserver(() => {
      if (initializeDivider()) observer.disconnect();
    });
    observer.observe(document.documentElement, {childList: true, subtree: true});
  }
})();
