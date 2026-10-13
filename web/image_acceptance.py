"""Exercise approved image requests offline, rejecting every other remote resource."""
from techkb.publication import note_frontmatter

PLACEHOLDER = b'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="600"><rect width="1200" height="600" fill="#dae8ed"/><text x="80" y="300" font-size="48" fill="#244853">Fixture article image</text></svg>'


def approved_images(manifest, files):
    return {entry['id']: note_frontmatter(files[entry['path']])[2].get('article_images', [])
            for entry in manifest['notes']}


def image_guard(route, origin, approved, external, images):
    request = route.request
    if request.url.startswith(origin + '/'):
        route.continue_()
    elif request.resource_type == 'image' and request.url in approved:
        images.append(request.url)
        route.fulfill(status=200, content_type='image/svg+xml', body=PLACEHOLDER)
    else:
        external.append(request.url)
        route.abort()


def check_images(page, images):
    viewport = page.viewport_size
    for image in images:
        # Use an argument rather than interpolating an untrusted URL into CSS/JS.
        page.evaluate('(url) => [...document.querySelectorAll("article img")].find(img => img.src === url)?.scrollIntoView()', image['url'])
        page.wait_for_function('(url) => [...document.querySelectorAll("article img")].some(img => img.src === url && img.complete && img.naturalWidth > 0)', arg=image['url'])
        assert page.evaluate('(url) => [...document.querySelectorAll("article img")].filter(img => img.src === url).length', image['url']) == 1
    if images:
        for width in (375, 768, 1024, 1440):
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth') <= width, 'image_horizontal_overflow'
        page.set_viewport_size(viewport)


def check_image_pages(origin, entries, workers=2):
    """Use at most two browsers; each thread owns its complete Playwright runtime."""
    from concurrent.futures import ThreadPoolExecutor
    from playwright.sync_api import sync_playwright

    if type(workers) is not int or workers not in (1, 2):
        raise ValueError('invalid_image_workers')
    selected = [(note_id, images) for note_id, images in entries.items() if images]
    if not selected:
        return dict(notes=0, requests=0, workers=0)
    count = min(workers, len(selected))
    approved = {image['url'] for _, images in selected for image in images}

    def inspect(group):
        errors, external, requests = [], [], []
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch()
            try:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                context.route('**/*', lambda route: image_guard(route, origin, approved, external, requests))
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda message: errors.append(message.type) if message.type == 'error' else None)
                for note_id, images in group:
                    page.goto(origin + '/kaname/notes/' + note_id)
                    check_images(page, images)
                assert not errors, 'pages_browser_error'
                assert not external, 'pages_external_resource_request'
                return len(requests)
            finally:
                browser.close()

    # Each Note is checked once, and all exceptions stop acceptance.
    with ThreadPoolExecutor(max_workers=count, thread_name_prefix='image-check') as pool:
        requests = list(pool.map(inspect, [selected[index::count] for index in range(count)]))
    return dict(notes=len(selected), requests=sum(requests), workers=count)
