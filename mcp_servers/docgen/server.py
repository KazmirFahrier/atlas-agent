"""docgen MCP server: turn analysis results into deliverables.

Tools:
  * pdf_brief(title, summary, bullets)  -> one-page PDF
  * slide_deck(title, slides)           -> .pptx deck
Files are written to ./out and the path is returned to the agent.
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

OUT_DIR = os.environ.get("ATLAS_OUT_DIR", "out")
mcp = FastMCP("docgen")


def _ensure_out() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)


@mcp.tool()
def pdf_brief(title: str, summary: str, bullets: list[str]) -> str:
    """Generate a one-page PDF brief. Returns the file path."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

    _ensure_out()
    path = os.path.join(OUT_DIR, "brief.pdf")
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=letter)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12),
             Paragraph(summary, styles["BodyText"]), Spacer(1, 12)]
    story.append(ListFlowable([ListItem(Paragraph(b, styles["BodyText"])) for b in bullets], bulletType="bullet"))
    doc.build(story)
    return os.path.abspath(path)


@mcp.tool()
def slide_deck(title: str, slides: list[dict]) -> str:
    """Generate a .pptx deck. `slides` = [{"heading": str, "bullets": [str]}]. Returns path."""
    from pptx import Presentation
    from pptx.util import Pt

    _ensure_out()
    path = os.path.join(OUT_DIR, "deck.pptx")
    prs = Presentation()
    title_layout, bullet_layout = prs.slide_layouts[0], prs.slide_layouts[1]
    s0 = prs.slides.add_slide(title_layout)
    s0.shapes.title.text = title
    for spec in slides:
        s = prs.slides.add_slide(bullet_layout)
        s.shapes.title.text = spec.get("heading", "")
        body = s.placeholders[1].text_frame
        body.clear()
        for i, b in enumerate(spec.get("bullets", [])):
            p = body.paragraphs[0] if i == 0 else body.add_paragraph()
            p.text = b
            p.font.size = Pt(18)
    prs.save(path)
    return os.path.abspath(path)


if __name__ == "__main__":
    mcp.run()
