"""Render the per-version documentation report as a PDF.

Plain language on purpose. The report explains a practical decision -- where
to get documentation for every version of a gem -- so it reads as a sequence
of questions and answers rather than a specification.
"""
from __future__ import annotations

import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                   "Third_party_packages", "docs",
                   "per-version-documentation-report.pdf")

INK = colors.HexColor("#14212e")
MUTED = colors.HexColor("#5b6b7a")
RULE = colors.HexColor("#d6dee6")
BAND = colors.HexColor("#eef3f8")
ACCENT = colors.HexColor("#1f3a5f")
GOOD = colors.HexColor("#e8f2ea")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold",
                    fontSize=20, leading=25, textColor=INK, alignment=TA_LEFT,
                    spaceAfter=3)
SUB = ParagraphStyle("SUB", fontName="Helvetica", fontSize=10, leading=14,
                     textColor=MUTED, spaceAfter=16)
H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13, leading=17,
                    textColor=ACCENT, spaceBefore=17, spaceAfter=6)
BODY = ParagraphStyle("BODY", fontName="Helvetica", fontSize=9.6, leading=14.2,
                      textColor=INK, spaceAfter=7)
LEAD = ParagraphStyle("LEAD", parent=BODY, fontSize=10.4, leading=15.4,
                      spaceAfter=9)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=13, spaceAfter=4)
CODE = ParagraphStyle("CODE", fontName="Courier", fontSize=8.4, leading=12,
                      textColor=INK, backColor=BAND, borderPadding=7,
                      spaceBefore=4, spaceAfter=9)
KEY = ParagraphStyle("KEY", fontName="Helvetica", fontSize=9.8, leading=14.4,
                     textColor=INK, backColor=GOOD, borderPadding=9,
                     spaceBefore=6, spaceAfter=10)
NOTE = ParagraphStyle("NOTE", parent=BODY, fontSize=8.8, textColor=MUTED,
                      spaceBefore=3)


def table(rows, widths):
    data = [[Paragraph(str(c), ParagraphStyle(
        "c", fontName="Helvetica-Bold" if i == 0 else "Helvetica",
        fontSize=8.8, leading=12,
        textColor=colors.white if i == 0 else INK))
        for c in row] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
          ("LEFTPADDING", (0, 0), (-1, -1), 7),
          ("RIGHTPADDING", (0, 0), (-1, -1), 7),
          ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
          ("BACKGROUND", (0, 0), (-1, 0), ACCENT)]
    for r in range(2, len(data), 2):
        st.append(("BACKGROUND", (0, r), (-1, r), BAND))
    t.setStyle(TableStyle(st))
    return t


def b(t):
    return "<b>" + t + "</b>"


def build():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc = SimpleDocTemplate(
        OUT, pagesize=A4, leftMargin=21 * mm, rightMargin=21 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Getting documentation for every version of a gem",
        author="agrawalsnehal3")
    W = doc.width
    s = []
    P = lambda t, st=BODY: s.append(Paragraph(t, st))

    P("Getting documentation for every version of a gem", H1)
    P("Where it comes from, what is missing, and what it costs", SUB)

    # ---------------------------------------------------------------
    P("What we are trying to do", H2)
    P("We have 2,814 gems. Each one has published many versions — 30 on "
      "average, and 202,083 in total. We want the documentation for every one "
      "of those versions, not just the newest.", LEAD)
    P("That is harder than it sounds, because documentation lives in four "
      "different places and only some of them keep old versions around.")

    # ---------------------------------------------------------------
    P("The four places documentation lives", H2)
    s.append(table([
        ["Where", "Does it keep old versions?", "How many gems have it"],
        ["Inside the gem file<br/>(comments, README, docs folder)",
         b("Yes, always"), "96%"],
        ["rubydoc.info", "Yes", "93%"],
        ["A docs folder on GitHub", "Only if the project tags releases", "1%"],
        ["A website someone wrote", b("Usually not"), "20%"],
    ], [W * .34, W * .38, W * .28]))
    s.append(Spacer(1, 10))

    P("The first row is the important one. When you download version 1.2.3 of "
      "a gem, the documentation for version 1.2.3 comes with it — the comments "
      "are in the code, and the README is in the same archive.")

    s.append(Paragraph(
        b("This means most of the problem solves itself.") + " There is no "
        "guessing and no scraping. If you can download a version, you have "
        "that version's documentation. That covers 96% of gems.", KEY))

    P("rubydoc.info also has old versions, at addresses like "
      "rubydoc.info/gems/rack/3.2.7. But it builds those pages by reading the "
      "gem file itself. Scraping it would mean about 50 page requests per "
      "version to get back something already sitting in one download. So we "
      "ignore it.")

    # ---------------------------------------------------------------
    P("Where to look, in order", H2)
    P("Try each source in turn and write down which one answered. That way an "
      "uncertain answer never gets mistaken for a certain one.")
    s.append(table([
        ["", "Look here", "How good is the answer"],
        ["1", "Inside the gem file", b("Exact") + " — it is the version itself"],
        ["2", "GitHub docs folder at the release tag", "Exact, if the project tagged that release"],
        ["3", "The project's website", "Only describes one version, usually today's"],
        ["4", "Nothing found", "Record the gap"],
    ], [W * .06, W * .40, W * .54]))
    s.append(Spacer(1, 10))

    P("Step 1 needs no new code:", BODY)
    P("python count-methods.py --versions all&nbsp;&nbsp;&nbsp;# or minor / major<br/>"
      "python export-method-inventory.py<br/>"
      "rm _docs_scan.csv &amp;&amp; python measure-doc-coverage.py", CODE)
    P("The coverage script already labels its results by gem <i>and</i> "
      "version, so once more versions are downloaded, per-version numbers "
      "appear on their own.")

    # ---------------------------------------------------------------
    P("The part that does not work cleanly", H2)
    P("A website someone wrote by hand almost always shows one version: the "
      "current one. bundler.io documents whatever bundler is today.", LEAD)
    P("So we cannot use it to describe old versions. Saying that today's "
      "bundler.io documents bundler 1.16 would be claiming that version had "
      "features it did not have.")
    P(b("The rule:") + " a website counts for one version only. Every other "
      "version of that gem is marked <i>“documented somewhere, version "
      "unknown”</i> — not counted as documented, and not counted as missing.")
    P("A few sites do keep old versions, with addresses like /v2.4/. Those are "
      "worth checking for, but they are rare.")
    P("Old snapshots exist on the Wayback Machine, but matching a snapshot "
      "date to a release date is a guess. If used at all, it should be kept "
      "separate and labelled as such.")

    s.append(PageBreak())

    # ---------------------------------------------------------------
    P("How we know the answer is complete", H2)
    P("Count in (gem, version) pairs, and keep the three kinds of answer "
      "apart:")
    s.append(table([
        ["Answer", "Meaning", "Expected"],
        ["Exact", "Came from the gem file or a tagged release", b("~96%")],
        ["Approximate", "A website, describing one version only", "~3%"],
        ["Missing", "Nothing found anywhere", "~1%"],
    ], [W * .22, W * .58, W * .20]))
    s.append(Spacer(1, 10))
    P("Two rules keep this honest:")
    P("• " + b("Never merge the three into one number.") + " “97% documented” "
      "hides that some of it is a guess.", BULLET)
    P("• " + b("Always show how many versions were checked.") + " A gem with "
      "500 versions where one was measured is not “done”. Record versions "
      "checked against versions published.", BULLET)

    # ---------------------------------------------------------------
    P("What it costs", H2)
    s.append(table([
        ["How many versions", "Downloads", "Time", "Disk"],
        ["Newest only (what we have now)", "2,814", "20 min", "1.4 GB"],
        ["One per major version", "~9,000", "1 hour", "~10 GB"],
        [b("One per minor version") + " &nbsp;← recommended", b("~35,000"), b("4–5 hours"), b("~40 GB")],
        ["Every version", "202,083", "26 hours", "up to 250 GB"],
    ], [W * .38, W * .19, W * .21, W * .22]))
    s.append(Spacer(1, 10))
    P(b("One per minor version is the sensible choice.") + " Patch releases "
      "(1.2.3 to 1.2.4) are bug fixes and their documentation is nearly always "
      "identical. Spending 26 hours to confirm that would tell us little. "
      "Documentation changes when the API changes, and that happens at minor "
      "versions.")
    P("There is also one gem that would distort a full run: " +
      b("sorbet-static has 13,376 versions") + ", almost all of them the same "
      "code rebuilt for different platforms. On its own it would take a large "
      "share of the time and add nothing.")

    # ---------------------------------------------------------------
    P("Why per-version numbers are worth having", H2)
    P("Measuring every version shows things a single snapshot cannot:")
    P("• A gem that " + b("started documenting itself") + " at version 2.0 — "
      "the moment it happened is invisible otherwise.", BULLET)
    P("• A gem whose documentation is " + b("falling behind") + ", because new "
      "methods keep arriving undocumented.", BULLET)
    P("• Whether documentation " + b("keeps up with the API") + " at all. We "
      "already record how many methods each version added or removed, so "
      "putting the two together shows the gap growing or closing.", BULLET)
    P("The last one is the measurement that does not exist anywhere else, and "
      "it needs both numbers at the same version granularity.")

    # ---------------------------------------------------------------
    P("In short", H2)
    P("Download the gems. The documentation is already inside them, correct "
      "for each version, and that handles 96% of the work with no scraping at "
      "all.", LEAD)
    P("For the small remainder, check GitHub at the release tag. For the "
      "handful left after that, record the website against a single version "
      "and be honest that the rest are unknown.")

    s.append(Spacer(1, 16))
    P("All figures are measured from the 2,814-gem selection in this "
      "repository. Times assume 12 downloads at once, the rate measured "
      "against rubygems.org during collection.", NOTE)

    def furniture(canvas, d):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(21 * mm, 12 * mm, A4[0] - 21 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7.8)
        canvas.setFillColor(MUTED)
        canvas.drawString(21 * mm, 8 * mm,
                          "Documentation for every version of a gem")
        canvas.drawRightString(A4[0] - 21 * mm, 8 * mm,
                               str(canvas.getPageNumber()))
        canvas.restoreState()

    doc.build(s, onFirstPage=furniture, onLaterPages=furniture)
    print("wrote", os.path.abspath(OUT),
          "(" + str(round(os.path.getsize(OUT) / 1024)) + " KB)")


if __name__ == "__main__":
    sys.exit(build())
