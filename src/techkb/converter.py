from io import BytesIO
from markitdown import MarkItDown, StreamInfo

class Converter:
    def __init__(self):
        self.engine = MarkItDown(enable_plugins=False)

    def convert(self, cleaned_html: bytes) -> str:
        return self.engine.convert_stream(
            BytesIO(cleaned_html),
            stream_info=StreamInfo(mimetype="text/html", extension=".html", charset="utf-8"),
        ).text_content
