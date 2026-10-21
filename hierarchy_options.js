/* Save hierarchy drafts and page navigation in the same client-side update. */
window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.treedex = Object.assign({}, window.dash_clientside.treedex, {
  updateHierarchyOptions: function(clicks, values, ids, pages, stored) {
    const updated = Object.assign({}, stored || {});
    (ids || []).forEach((id, index) => {
      updated[id.plot] = Object.assign({}, updated[id.plot] || {});
      updated[id.plot][id.name] = values[index] === "" ? null : values[index];
    });
    const trigger = window.dash_clientside.callback_context.triggered_id;
    let nextPages = window.dash_clientside.no_update;
    if (trigger && trigger.type === "hierarchy-page-button" && (clicks || []).some(Boolean)) {
      nextPages = Object.assign({}, pages || {}, {[trigger.plot]: trigger.page});
    } else if (trigger && trigger.type === "hierarchy-option" && trigger.name === "hierarchy_mode") {
      const index = (ids || []).findIndex(id => id.plot === trigger.plot && id.name === "hierarchy_mode");
      const previousMode = ((stored || {})[trigger.plot] || {}).hierarchy_mode;
      if (index >= 0 && values[index] !== previousMode) {
        // Render the mode's enabled fields only after all visible drafts are saved.
        nextPages = Object.assign({}, pages || {}, {[trigger.plot]: (pages || {})[trigger.plot] || 1});
      }
    }
    return [nextPages, updated];
  }
});
