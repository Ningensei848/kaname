class Dedupe:
    def __init__(self, rows=()):
        success = [r for r in rows if r["status"] == "success"]
        self.raw = {r["raw_html_sha256"] for r in success}
        self.content = {r["content_sha256"] for r in success}

    def add(self, row):
        self.raw.add(row["raw_html_sha256"])
        self.content.add(row["content_sha256"])
