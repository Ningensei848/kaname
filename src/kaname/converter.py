from io import BytesIO
from threading import local
from markitdown import MarkItDown, StreamInfo

class Converter:
    def __init__(self):
        self._engines = local()

    @property
    def engine(self):
        # MarkItDown converter/plugin instances are isolated per worker.
        if not hasattr(self._engines, 'engine'):
            self._engines.engine = MarkItDown(enable_plugins=False)
        return self._engines.engine

    def convert(self, cleaned_html: bytes) -> str:
        return self.engine.convert_stream(
            BytesIO(cleaned_html),
            stream_info=StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
        ).text_content
