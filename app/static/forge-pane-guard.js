/* forge-pane-guard.js */
(function () {
  window.ForgePane = {
    /* The ONLY way app code may start a pane morph. Does nothing if the pane is already in that state. */
    set: function (flow, wantOpen, icon) {
      if (!flow) return false;
      var t = wantOpen ? 1 : 0;
      if (flow.p.target === t && (flow.live || flow.p.value === t)) return false;
      flow.to(t, icon);
      return true;
    }
  };
  /* Safety net (in addition to fixing the cause): if a flow is NOT running but its leftovers are still there, clean them. */
  setInterval(function () {
    var all = (window.ForgeFlow && ForgeFlow.all) || {};
    Object.keys(all).forEach(function (n) {
      var fl = all[n];
      if (fl.live) return;
      if (fl.svg && fl.svg.style.display !== 'none') fl.svg.style.display = 'none';
      if (fl.panel.classList.contains('ff-active') || fl.panel.style.clipPath) fl.cleanup();
    });
  }, 500);
})();
