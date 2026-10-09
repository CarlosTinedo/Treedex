/* Commit current fields and page changes together, without a server round trip. */
window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.treedex = Object.assign({}, window.dash_clientside.treedex, {
  updateBasicOptions: function(clicks, values, ids, pages, stored) {
    const updated = Object.assign({}, stored || {});
    (ids || []).forEach((id, index) => {
      updated[id.plot] = Object.assign({}, updated[id.plot] || {});
      updated[id.plot][id.name] = values[index] === "" ? null : values[index];
    });
    const trigger = window.dash_clientside.callback_context.triggered_id;
    let nextPages = window.dash_clientside.no_update;
    if (trigger && trigger.type === "basic-page-button" && (clicks || []).some(Boolean)) {
      nextPages = Object.assign({}, pages || {}, {[trigger.plot]: trigger.page});
    }
    return [nextPages, updated];
  }
});
