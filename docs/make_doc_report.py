"""Render the per-version documentation report as a PDF.

A small markdown-ish renderer rather than a dependency: the report is a fixed
document with headings, paragraphs, tables and code blocks, and reportlab is
already in the project.
"""
from __future__ import annotations

import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                   "Third_party_packages", "docs",
                   "per-version-documentation-report.pdf")

INK = colors.HexColor("#14212e")
MUTED = colors.HexColor("#5b6b7a")
RULE = colors.HexColor("#d6dee6")
BAND = colors.HexColor("#eef3f8")
ACCENT = colors.HexColor("#1f3a5f")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold",
                    fontSize=19, leading=24, textColor=INK, alignment=TA_LEFT,
                    spaceAfter=2)
SUB = ParagraphStyle("SUB", fontName="Helvetica", fontSize=9.5, leading=13,
                     textColor=MUTED, spaceAfter=14)
H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                    textColor=ACCENT, spaceBefore=15, spaceAfter=5)
H3 = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=10.2, leading=14,
                    textColor=INK, spaceBefore=10, spaceAfter=3)
BODY = ParagraphStyle("BODY", fontName="Helvetica", fontSize=9.4, leading=13.6,
                      textColor=INK, spaceAfter=6)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=11, bulletIndent=2,
                        spaceAfter=3)
CODE = ParagraphStyle("CODE", fontName="Courier", fontSize=8.2, leading=11.4,
                      textColor=INK, backColor=BAND, borderPadding=6,
                      leftIndent=2, spaceBefore=3, spaceAfter=8)
NOTE = ParagraphStyle("NOTE", parent=BODY, fontSize=8.8, textColor=MUTED,
                      leftIndent=8, borderPadding=0, spaceBefore=2)


def table(rows, widths, head=True):
    data = [[Paragraph(c if isinstance(c, str) else str(c),
                       ParagraphStyle("c", fontName=("Helvetica-Bold" if head and i == 0
                                                     else "Helvetica"),
                                      fontSize=8.6, leading=11.6,
                                      textColor=(colors.white if head and i == 0 else INK)))
             for c in row] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0, hAlign="LEFT")
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 4.5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 6),
             ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE)]
    if head:
        style += [("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                  ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white)]
        for r in range(2, len(data), 2):
            style.append(("BACKGROUND", (0, r), (-1, r), BAND))
    t.setStyle(TableStyle(style))
    return t


def b(t):
    return "<b>" + t + "</b>"


def build():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20 * mm,
                            rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm,
                            title="Per-Version Documentation for Ruby Gems",
                            author="agrawalsnehal3")
    W = doc.width
    s = []
    P = lambda t, st=BODY: s.append(Paragraph(t, st))

    P("Per-Version Documentation for Ruby Gems", H1)
    P("Sources, completeness, and handling variability across versions", SUB)

    P("1. Problem definition", H2)
    P("The unit of analysis is the " + b("(package, version) pair") + ", not the "
      "package. Across 2,814 selected gems there are " + b("202,083 stable "
      "versions") + " — median 30 per gem, mean 72.")
    P("Completeness means: for each pair, can documentation be obtained <i>as it "
      "stood at that version</i>? The answer depends on the source, because "
      "sources differ fundamentally in whether they are versioned at all.")

    P("2. Version fidelity by source", H2)
    s.append(table([
        ["Source", "Versioned", "Mechanism", "Present in"],
        ["Doc comments in .gem", b("Exact"), "Documentation <i>is</i> the artifact", "48.4% of methods"],
        ["README / docs/ in .gem", b("Exact"), "Same archive", "78.3% / 5.3%"],
        ["rubydoc.info", "Exact", "rubydoc.info/gems/&lt;gem&gt;/&lt;version&gt;", "93.4%"],
        ["GitHub docs/ folder", "Conditional", "?ref=&lt;tag&gt;, only if tagged", "0.6%"],
        ["GitHub wiki", b("No"), "Own history, no release link", "81% (mostly empty)"],
        ["Human-written site", b("Rarely"), "Usually current version only", "19.8%"],
    ], [W * .24, W * .14, W * .38, W * .24]))
    s.append(Spacer(1, 9))
    P("Two consequences determine the design.")
    P(b("The in-package tier is versioned by construction.") + " Downloading "
      "version 1.2.3's .gem yields version 1.2.3's documentation exactly — not "
      "an approximation. There is no completeness gap, only fetching. This "
      "covers " + b("96.4% of gems") + ".")
    P(b("rubydoc.info is redundant.") + " It offers per-version URLs but "
      "generates them by running YARD over the same .gem. Scraping costs ~50 "
      "requests per gem-version (rack alone has 42 class pages, and no bulk "
      "route exists) to recover data already inside one artifact.")

    P("3. Tiered acquisition strategy", H2)
    P("Rank by version fidelity and record which tier answered, so "
      "approximations are never counted as exact.")
    s.append(table([
        ["Tier", "Source", "Fidelity", "Method"],
        ["1", "In-package", b("Exact"), "Fetch &lt;gem&gt;-&lt;version&gt;.gem, parse"],
        ["2", "GitHub at tag", "Exact if tagged", "/contents/docs?ref=&lt;tag&gt;"],
        ["3", "Human site", "Current version only", "Fetch once, attribute to one version"],
        ["4", "None", "—", "Record the gap"],
    ], [W * .08, W * .22, W * .24, W * .46]))
    s.append(Spacer(1, 9))

    P("Tier 1 — apply to everything", H3)
    P("python count-methods.py --versions all&nbsp;&nbsp;&nbsp;# or minor / major / N<br/>"
      "python export-method-inventory.py<br/>"
      "rm _docs_scan.csv &amp;&amp; python measure-doc-coverage.py", CODE)
    P("measure-doc-coverage.py already keys on &lt;gem&gt;-&lt;version&gt;. "
      "Per-version rows appear automatically once the cache holds multiple "
      "versions — " + b("no new code required") + ".")
    s.append(table([
        ["Policy", "Fetches", "Time @12 workers", "Storage"],
        ["Latest (current state)", "2,814", "~20 min", "1.4 GB"],
        ["One per major", "~8–10k", "~1 h", "~10 GB"],
        ["One per major.minor", "~30–40k", "~4–5 h", "~40 GB"],
        ["Every version", "202,083", "~26 h", "≤250 GB"],
    ], [W * .32, W * .18, W * .28, W * .22]))
    s.append(Spacer(1, 9))

    P("Tier 2 — tag matching", H3)
    P("/repos/{owner}/{repo}/contents/docs?ref=&lt;tag&gt; retrieves a docs "
      "folder at any git ref. Gem version 1.2.3 may map to v1.2.3, 1.2.3, "
      "rel-1.2.3, &lt;gem&gt;-1.2.3, or no tag. Resolve by ordered candidates, "
      "recording which matched:")
    P('CANDIDATES = ["v{v}", "{v}", "{gem}-v{v}", "{gem}/v{v}",<br/>'
      '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"rel-{v}", "release-{v}"]', CODE)
    P("Two failure modes must be recorded rather than smoothed over:")
    P("• " + b("Untagged releases") + " — many gems publish without tagging. "
      "No tag, no Tier 2 answer.", BULLET)
    P("• " + b("Monorepos") + " — rails/rails tags once for seven gems. The tag "
      "exists but its docs/ folder is not specific to the queried gem.", BULLET)

    s.append(PageBreak())
    P("Tier 3 — where completeness genuinely breaks", H3)
    P("Human-written sites overwhelmingly present one version: the current one. "
      "Three sub-cases:")
    P("1. " + b("Version switcher present") + " (/v2.4/…, ReadTheDocs, "
      "Docusaurus). Rare but detectable by probing a versioned path.", BULLET)
    P("2. " + b("Site generated from a repo checkout-able at a tag") +
      " — already covered by Tier 2.", BULLET)
    P("3. " + b("Site shows only the present") + " — the large majority.", BULLET)
    P("For case 3, " + b("attribute the site to exactly one version and mark all "
      "others as “external documentation, version unknown.”") +
      " Attributing today's bundler.io to bundler 1.16 would assert an API that "
      "version did not have.")
    P("Wayback Machine snapshots can retrieve historical states, but mapping "
      "snapshot date to release date is inference, not evidence. If used, record "
      "as a distinct tier carrying the snapshot date; never merge with exact "
      "tiers.")

    P("4. Measuring completeness", H2)
    P("Report over (package, version) pairs with the answering tier:")
    P("coverage_tier &#8712; {in_package, github_tag, external_current,<br/>"
      "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
      "&nbsp;&nbsp;external_snapshot, none}", CODE)
    s.append(table([
        ["Metric", "Definition"],
        ["Exact coverage", "Pairs answered by Tier 1 or 2"],
        ["Approximate", "Tier 3 — one version documented, others inferred"],
        ["Absent", "Tier 4"],
    ], [W * .28, W * .72]))
    s.append(Spacer(1, 9))
    P("Projected from current data: " + b("~96% exact, ~3% approximate, ~1% "
      "absent") + ". The exact figure is attainable because it depends on no "
      "scraping.")
    P("Two required properties:")
    P("• " + b("Never average across tiers.") + " “97% documented” is "
      "misleading if 3% is inference. Report tiers separately.", BULLET)
    P("• " + b("Record the denominator.") + " A gem with 500 versions and one "
      "measured is 0.2% covered, not “covered”. Store "
      "versions_measured / versions_published per gem so partial runs remain "
      "visible.", BULLET)

    P("5. Analytical value of per-version data", H2)
    P("Per-version measurement captures change that latest-only data cannot:")
    P("• " + b("Documentation adoption") + " — a gem that adds docs at v2.0; "
      "the event is invisible otherwise.", BULLET)
    P("• " + b("Coverage decay") + " — new undocumented methods diluting an "
      "established gem.", BULLET)
    P("• " + b("Documentation debt over time") + " — the API census already "
      "produces added/removed per version. Joining both series at equal version "
      "granularity measures whether documentation tracks or lags API growth.", BULLET)
    P("The third is the novel measurement and requires both series at the same "
      "granularity.")

    P("6. Recommendation", H2)
    P(b("Use --versions minor") + " — approximately 30–40k fetches, 4–5 hours, "
      "~15% the cost of <i>all</i>.")
    P("Patch releases are overwhelmingly bug fixes with byte-identical "
      "documentation; 26 hours and 250 GB would largely confirm that 1.2.3 and "
      "1.2.4 match. Minor boundaries are where APIs, and therefore "
      "documentation, move.")
    P("One distortion to control: " + b("sorbet-static has 13,376 versions") +
      ", nearly all platform builds of identical code. Such packages would "
      "consume a disproportionate share of any <i>all</i> run while contributing "
      "nothing. --versions minor collapses them; --versions 20 caps them.")
    P("Handle the residue explicitly: Tier 2 for the ~100 gems with no "
      "in-package documentation but a tagged repository; Tier 3 recorded as "
      "single-version for the remainder; Tier 4 counted honestly.")

    s.append(Spacer(1, 14))
    P("Figures are measured from the 2,814-gem selection in this repository. "
      "Timings assume 12 concurrent workers, the rate measured against "
      "rubygems.org during collection.", NOTE)

    def furniture(canvas, d):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(20 * mm, 12 * mm, A4[0] - 20 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7.6)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 8 * mm,
                          "Per-Version Documentation for Ruby Gems")
        canvas.drawRightString(A4[0] - 20 * mm, 8 * mm, str(canvas.getPageNumber()))
        canvas.restoreState()

    doc.build(s, onFirstPage=furniture, onLaterPages=furniture)
    print("wrote", os.path.abspath(OUT),
          "(" + str(round(os.path.getsize(OUT) / 1024)) + " KB)")


if __name__ == "__main__":
    sys.exit(build())
