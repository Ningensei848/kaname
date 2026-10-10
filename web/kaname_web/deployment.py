"""Read the served Pages version and original Note bytes; stdlib only."""
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .validation import valid_deployment_version, verify_pages_bytes


def verify(url, commit, dataset, artifact, notes):
    address = urlsplit(url)
    if (address.scheme != 'https' and not (address.scheme == 'http' and address.hostname == '127.0.0.1')) or address.username or address.password:
        raise ValueError('invalid_pages_url')
    if not valid_deployment_version(commit, dataset, artifact):
        raise ValueError('invalid_pages_version')
    def get(name):
        request = Request(url.rstrip('/') + '/' + name, headers={'Cache-Control': 'no-cache'})
        with urlopen(request, timeout=20) as response:
            data = response.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise ValueError('oversized_pages_response')
            return data
    return verify_pages_bytes(get, commit, dataset, artifact, notes)
