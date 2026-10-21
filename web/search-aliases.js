// The reviewed alias map is prepended by the builder from kaname.tags.
(() => {
  const spelling = value => value.normalize("NFKC").toLowerCase().trim().replace(/\s+/gu, "-");
  const canonical = value => Object.hasOwn(kanameTagAliases, spelling(value)) ? kanameTagAliases[spelling(value)] : null;
  const normalize = event => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || !input.matches(".search-bar") || event.isComposing) return;
    const raw = input.value.trim();
    const whole = raw.startsWith('#') && !/\s$/u.test(input.value) && canonical(raw.slice(1));
    const query = whole ? "#" + whole : input.value.replace(/#([^\s]+)/gu,
      (match, value) => "#" + (canonical(value) ?? value));
    // Capture runs before Quartz reads the input. Show the canonical tag so
    // keyboard navigation, highlighting and result filtering share one query.
    if (query !== input.value) input.value = query;
  };
  document.addEventListener("input", normalize, true);
  document.addEventListener("compositionend", event => {
    normalize(event);
    if (event.target instanceof HTMLInputElement && event.target.matches(".search-bar")) {
      event.target.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }, true);
})();
