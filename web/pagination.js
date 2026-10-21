// Warm one same-origin document after initial resources finish. Navigation is
// ordinary HTML and remains available without JavaScript or prefetch support.
(() => {
  const prepare = () => {
    const connection = navigator.connection;
    if (connection?.saveData || /(^|-)2g$/.test(connection?.effectiveType ?? "")) return;
    const next = document.querySelector('.pagination a[rel="next"]');
    if (!next) return;
    const url = new URL(next.href, location.href);
    if (url.origin !== location.origin || !url.pathname.startsWith("/kaname/") || url.search || url.hash) return;
    const hint = document.createElement("link");
    hint.rel = "prefetch";
    hint.as = "document";
    hint.href = url.href;
    hint.fetchPriority = "low";
    document.head.append(hint);
  };
  const schedule = () => {
    if ("requestIdleCallback" in window) window.requestIdleCallback(prepare, { timeout: 2000 });
    else window.setTimeout(prepare, 1500);
  };
  if (document.readyState === "complete") schedule();
  else window.addEventListener("load", schedule, { once: true });
})();
