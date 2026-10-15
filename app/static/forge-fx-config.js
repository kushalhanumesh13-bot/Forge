/* Which elements get which feedback strength. Later lines win. */
(function () {
  const FX = window.ForgeFX; if (!FX) return;

  // STRONG: icons and small icon buttons
  FX.add('.rail-button, .activity-rail .rail-button, #help', 'strong');
  FX.add('#command-open, #refresh, #sidebar-close, #settings-close, #keys-close, #context-close, #palette-close, #file-find-close, .panel-heading .icon-button', 'strong');

  // MEDIUM: normal buttons and step items
  FX.add('#quick-open, #save, #find-file, .empty-action, .plan-action, #run-command, #ai-save, #ai-test, #ai-remove, #home', 'medium');
  FX.add('.journey-step, .journey .journey-step', 'medium');
  FX.add('#dock-toggle, .dock-bar, .dock-tab', 'medium');

  // SOFT: rows and tabs (tiny feedback only)
  FX.add('.tree-row, .tree-item', 'soft');
  FX.add('#tabs .tab, .tab', 'soft');

  // NONE: never animate these
  FX.add('#editor, #code-scroller, .code-highlight, .editor-surface, textarea, input, select, .palette-results, .dock-content, ::-webkit-scrollbar', 'none');
})();
