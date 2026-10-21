// Keep the pinned Quartz search implementation, including its Japanese
// tokenizer, ranking, previews and keyboard controls. Only defer its startup.
export function lazySearchScript(source) {
  const startup = /document\.addEventListener\("nav",(\w+)\);document\.addEventListener\("render",\1\);\s*$/;
  if (!startup.test(source)) throw Error('upstream_search_startup_changed');
  const initialize = source.replace(startup, 'return $1();');
  return `(() => {
    let ready, complete = false;
    const initialize = () => { ${initialize} };
    const start = () => ready ??= initialize().then(() => { complete = true; });
    const open = async (event, button, replay = () => button.click()) => {
      if (complete) return;
      event.preventDefault(); event.stopImmediatePropagation();
      if (ready) return;
      button.setAttribute('aria-busy', 'true');
      let status = button.parentElement.querySelector('.search-load-status');
      if (!status) {
        status = document.createElement('span');
        status.className = 'search-load-status'; status.setAttribute('role', 'status');
        button.parentElement.append(status);
      }
      status.textContent = '検索を準備しています…';
      try {
        await start(); status.textContent = ''; replay();
      } catch {
        ready = null; status.textContent = '検索を読み込めません。もう一度お試しください。';
      } finally { button.removeAttribute('aria-busy'); }
    };
    document.addEventListener('click', event => {
      const button = event.target.closest?.('.search-button');
      if (button) open(event, button);
    }, true);
    document.addEventListener('keydown', event => {
      if (!complete && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        const button = document.querySelector('.search-button');
        if (button) open(event, button, () => document.dispatchEvent(new KeyboardEvent('keydown', {
          key: event.key, code: event.code, ctrlKey: event.ctrlKey, metaKey: event.metaKey,
          shiftKey: event.shiftKey, altKey: event.altKey, bubbles: true, cancelable: true,
        })));
      }
    }, true);
  })();`;
}
