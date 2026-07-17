"""Turn a template's Markdown body + merge variables into signed-ready HTML.

Merge variables use Python ``string.Template`` (``${var}``) so they never
collide with DocuSeal's ``{{Field;...}}`` interactive-field tags, which are
passed through untouched for DocuSeal to render at signing time.
"""
from string import Template

import markdown as md

_PAGE_CSS = """
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial,
       sans-serif; color: #1a1a1a; line-height: 1.5; max-width: 720px;
       margin: 0 auto; padding: 40px; }
h1, h2, h3 { line-height: 1.25; }
h1 { font-size: 1.8em; border-bottom: 2px solid #eee; padding-bottom: .3em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
blockquote { border-left: 4px solid #ddd; margin: 1em 0; padding: 0 1em;
             color: #555; }
code { background: #f6f8fa; padding: .2em .4em; border-radius: 3px; }
pre { background: #f6f8fa; padding: 1em; border-radius: 6px; overflow: auto; }
"""


def render_merge(body_markdown: str, context: dict) -> str:
    """Substitute ${var} merge fields. Unknown vars are left as-is."""
    stringified = {k: ("" if v is None else str(v)) for k, v in context.items()}
    return Template(body_markdown).safe_substitute(stringified)


def markdown_to_document(merged_markdown: str, title: str) -> str:
    """Convert merged Markdown to a standalone, print-friendly HTML document.

    DocuSeal ``{{...}}`` field tags survive the Markdown pass as plain text.
    """
    body_html = md.markdown(
        merged_markdown,
        extensions=["extra", "sane_lists", "nl2br", "tables"],
    )
    # Escape the title for the <title> tag only; body is trusted admin content.
    safe_title = (
        title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<title>{safe_title}</title>"
        f"<style>{_PAGE_CSS}</style></head><body>{body_html}</body></html>"
    )


def render_contract(contract) -> str:
    """Full render pipeline for a Contract instance -> HTML string."""
    merged = render_merge(contract.template.body_markdown, contract.merge_context())
    return markdown_to_document(merged, contract.title)
