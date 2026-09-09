"""Render the documentation-sources report as a PDF.

Covers both registries in one document: every place documentation can come
from, what each one actually is, and how to obtain it for a specific version.
Plain language throughout -- the reader wants to know what to download.
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
                   "documentation-sources-report.pdf")

INK = colors.HexColor("#14212e")
MUTED = colors.HexColor("#5b6b7a")
RULE = colors.HexColor("#d6dee6")
BAND = colors.HexColor("#eef3f8")
ACCENT = colors.HexColor("#1f3a5f")
RUBY = colors.HexColor("#8c2f39")
CSH = colors.HexColor("#3b5c8f")
GOOD = colors.HexColor("#e8f2ea")
WARN = colors.HexColor("#fdf0e3")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold",
                    fontSize=20, leading=25, textColor=INK, alignment=TA_LEFT,
                    spaceAfter=3)
SUB = ParagraphStyle("SUB", fontName="Helvetica", fontSize=10, leading=14,
                     textColor=MUTED, spaceAfter=16)
H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13, leading=17,
                    textColor=ACCENT, spaceBefore=16, spaceAfter=6)
HR = ParagraphStyle("HR", parent=H2, textColor=RUBY)
HC = ParagraphStyle("HC", parent=H2, textColor=CSH)
H3 = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=10.4, leading=14,
                    textColor=INK, spaceBefore=11, spaceAfter=3)
BODY = ParagraphStyle("BODY", fontName="Helvetica", fontSize=9.6, leading=14.2,
                      textColor=INK, spaceAfter=7)
LEAD = ParagraphStyle("LEAD", parent=BODY, fontSize=10.4, leading=15.4,
                      spaceAfter=9)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=13, spaceAfter=4)
CODE = ParagraphStyle("CODE", fontName="Courier", fontSize=8.3, leading=11.8,
                      textColor=INK, backColor=BAND, borderPadding=7,
                      spaceBefore=4, spaceAfter=9)
KEY = ParagraphStyle("KEY", fontName="Helvetica", fontSize=9.8, leading=14.4,
                     textColor=INK, backColor=GOOD, borderPadding=9,
                     spaceBefore=6, spaceAfter=10)
ALERT = ParagraphStyle("ALERT", parent=KEY, backColor=WARN)
NOTE = ParagraphStyle("NOTE", parent=BODY, fontSize=8.8, textColor=MUTED,
                      spaceBefore=3)


def table(rows, widths, colour=ACCENT):
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
          ("BACKGROUND", (0, 0), (-1, 0), colour)]
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
        title="Where package documentation comes from",
        author="agrawalsnehal3")
    W = doc.width
    s = []
    P = lambda t, st=BODY: s.append(Paragraph(t, st))

    P("Where package documentation comes from", H1)
    P("Every source, what it really is, and how to get it for a particular "
      "version — RubyGems and NuGet", SUB)

    P("We have 2,814 Ruby gems and 3,352 NuGet packages, and between them "
      "471,930 published versions. For any one of those versions we want its "
      "documentation. This explains where it can come from and which sources "
      "are worth using.", LEAD)

    # =================================================================
    P("Ruby: the six places to look", HR)
    s.append(table([
        ["Source", "What it actually is", "Old versions?", "Have it"],
        ["Doc comments",
         "Comments written above each method, inside the code",
         b("Yes"), "76% of gems"],
        ["README",
         "A file shipped in the gem archive", b("Yes"), "76%"],
        ["docs/ folder",
         "Guide files shipped in the gem archive", b("Yes"), "5%"],
        ["rubydoc.info",
         "A website that runs YARD over the gem and publishes the result",
         "Yes", "93%"],
        ["GitHub docs/",
         "A folder in the source repository", "If tagged", "1%"],
        ["A project website",
         "A site the maintainers wrote themselves", b("Usually not"), "20%"],
    ], [W * .17, W * .43, W * .17, W * .23], RUBY))
    s.append(Spacer(1, 9))

    P("What YARD does", H3)
    P("YARD reads the comments in the code and turns them into web pages. "
      "rubydoc.info runs it over every gem published, automatically. Nobody "
      "asks for this and nobody can decline it.")
    P("So a rubydoc.info page existing means nothing on its own. If the author "
      "wrote no comments, the page still appears — it just lists method names "
      "with nothing beside them.")
    s.append(Paragraph(
        b("532 gems have a rubydoc.info page and not one documented method.") +
        " That is why we measure the comments in the code rather than counting "
        "whether a documentation link exists.", ALERT))

    P("What “48% of methods documented” means", H3)
    P("We look at each method and ask whether a comment sits directly above "
      "it:")
    P("# Parses the config file and returns a Rack app.&nbsp;&nbsp;&larr; a doc comment<br/>"
      "def parse_file(path)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
      "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&larr; documented<br/>"
      "end<br/><br/>"
      "def helper(x)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
      "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
      "&nbsp;&nbsp;&nbsp;&larr; not documented<br/>"
      "end", CODE)
    P("Across all gems: " + b("453,995 of 938,947 methods carry a comment — "
      "48%") + ". The median gem manages only 24%.")

    # =================================================================
    P("C#: the four places to look", HC)
    s.append(table([
        ["Source", "What it actually is", "Old versions?", "Have it"],
        ["XML doc file",
         "The compiler turns /// comments into a file shipped beside the assembly",
         b("Yes"), "65% of packages"],
        ["README",
         "A file shipped inside the .nupkg", b("Yes"), "35%"],
        ["GitHub docs/",
         "A folder in the source repository", "If tagged", "small"],
        ["A project website",
         "Usually a landing page rather than documentation",
         b("Usually not"), "37%"],
    ], [W * .17, W * .43, W * .17, W * .23], CSH))
    s.append(Spacer(1, 9))

    P("The C# compiler does the same job YARD does, but its output is a file "
      "placed inside the package rather than pages on a website. Each public "
      "member gets a structured entry:")
    P("&lt;member name=\"M:Serilog.Log.Information(System.String)\"&gt;<br/>"
      "&nbsp;&nbsp;&lt;summary&gt;Write a log event at Information level."
      "&lt;/summary&gt;<br/>"
      "&nbsp;&nbsp;&lt;param name=\"messageTemplate\"&gt;The message template."
      "&lt;/param&gt;<br/>"
      "&lt;/member&gt;", CODE)
    P("Two differences from Ruby matter. The file " + b("ships with the "
      "package") + ", so it is versioned automatically and needs no website. "
      "But it is " + b("optional") + " — the author must switch on a build "
      "setting, and 35% never do. For those packages nothing is generated at "
      "all, and there is no NuGet equivalent of rubydoc.info to fall back on.")

    s.append(PageBreak())

    # =================================================================
    P("How to get documentation for a particular version", H2)
    P("Three of the sources come free with the package. Download the version "
      "you want and its documentation is already inside.", LEAD)

    P("Ruby — one download per version", H3)
    P("curl -O https://rubygems.org/downloads/rack-3.2.7.gem<br/>"
      "tar -xf rack-3.2.7.gem&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
      "# gives data.tar.gz<br/>"
      "tar -xzf data.tar.gz&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
      "# comments, README and docs/ are all in here", CODE)

    P("C# — read only the part you need", H3)
    P("curl -O https://api.nuget.org/v3-flatcontainer/serilog/4.4.0/"
      "serilog.4.4.0.nupkg<br/>"
      "unzip serilog.4.4.0.nupkg&nbsp;&nbsp;&nbsp;# XML file sits beside each "
      "assembly", CODE)
    P("A .nupkg is a zip, and a zip keeps its index at the end. One ranged "
      "request reads that index, a second reads just the XML file. That is how "
      "3,352 packages were surveyed while transferring 298 MB instead of "
      "14 GB.")

    P("GitHub docs folder — only if the release was tagged", H3)
    P("https://api.github.com/repos/&lt;owner&gt;/&lt;repo&gt;/contents/docs"
      "?ref=v1.2.3", CODE)
    P("This works when the project tagged that release. Gem version 1.2.3 "
      "might be tagged v1.2.3, 1.2.3, rel-1.2.3, or not tagged at all — so try "
      "each and record which one matched. Monorepos are a further catch: "
      "rails/rails tags once for seven gems, so the tag exists but its docs "
      "folder is not specific to the gem you asked about.")

    P("A project website — usually only one version", H3)
    P("bundler.io documents whatever bundler is today. There is normally no "
      "way to see what it said three years ago. A few sites keep old versions "
      "at addresses like /v2.4/, but they are the exception.")
    s.append(Paragraph(
        b("So a website counts for one version only.") + " Every other version "
        "of that gem is marked “documented somewhere, version unknown” — not "
        "counted as documented, and not counted as missing. Saying today's "
        "bundler.io documents bundler 1.16 would claim that version had "
        "features it did not have.", ALERT))

    # =================================================================
    P("The recipe", H2)
    s.append(table([
        ["Step", "Do this", "Covers"],
        ["1", "Download each version and read what is inside it",
         b("96% of gems, 75% of NuGet packages")],
        ["2", "For the rest, check GitHub at the release tag",
         "a small number more"],
        ["3", "For what is still left, record the website against one version",
         "~3%"],
        ["4", "Record the remainder as not found", "~1%"],
    ], [W * .08, W * .56, W * .36]))
    s.append(Spacer(1, 9))
    P("Never merge those four into a single percentage. Step 1 is exact "
      "evidence; step 3 is one version's worth of evidence stretched over "
      "many. Reporting them together would hide which is which.")

    P("What it costs to do every version", H2)
    s.append(table([
        ["How many versions", "Downloads", "Time", "Disk"],
        ["Newest only (what we have now)", "6,166", "~30 min", "10 GB"],
        ["One per major version", "~25,000", "~2 h", "~40 GB"],
        [b("One per minor version") + " &nbsp;← recommended",
         b("~90,000"), b("~7 h"), b("~120 GB")],
        ["Every version", "471,930", "~60 h", "up to 1.3 TB"],
    ], [W * .36, W * .20, W * .20, W * .24]))
    s.append(Spacer(1, 9))
    P("Patch releases are bug fixes and their documentation is nearly always "
      "identical, so a full run mostly confirms that 1.2.3 and 1.2.4 match. "
      "Documentation changes when the API changes, and that happens at minor "
      "versions.")

    P("Things you cannot get", H2)
    P("• " + b("A website's older versions.") + " Once a site is updated the "
      "previous text is gone, unless someone archived it.", BULLET)
    P("• " + b("Documentation for a version that was never published.") +
      " Yanked releases disappear from the registry.", BULLET)
    P("• " + b("C# coverage as a percentage.") + " The compiler records only "
      "what was written, so there is no count of undocumented members to "
      "divide by. Ruby's 48% has no C# counterpart.", BULLET)

    s.append(Spacer(1, 14))
    P("All figures are measured from the 2,814 gems and 3,352 NuGet packages "
      "selected in this repository.", NOTE)

    def furniture(canvas, d):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(21 * mm, 12 * mm, A4[0] - 21 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7.8)
        canvas.setFillColor(MUTED)
        canvas.drawString(21 * mm, 8 * mm,
                          "Where package documentation comes from")
        canvas.drawRightString(A4[0] - 21 * mm, 8 * mm,
                               str(canvas.getPageNumber()))
        canvas.restoreState()

    doc.build(s, onFirstPage=furniture, onLaterPages=furniture)
    print("wrote", os.path.abspath(OUT),
          "(" + str(round(os.path.getsize(OUT) / 1024)) + " KB)")


if __name__ == "__main__":
    sys.exit(build())
