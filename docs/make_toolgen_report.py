"""Render the tool-generated documentation report as a PDF.

Its own document because it answers a different question from the per-version
report: not "where do I get the docs" but "when a tool produced these docs
automatically, what does their existence actually tell me".
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
                   "tool-generated-documentation-report.pdf")

INK = colors.HexColor("#14212e")
MUTED = colors.HexColor("#5b6b7a")
RULE = colors.HexColor("#d6dee6")
BAND = colors.HexColor("#eef3f8")
ACCENT = colors.HexColor("#1f3a5f")
WARN = colors.HexColor("#fdf0e3")
GOOD = colors.HexColor("#e8f2ea")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold",
                    fontSize=20, leading=25, textColor=INK, alignment=TA_LEFT,
                    spaceAfter=3)
SUB = ParagraphStyle("SUB", fontName="Helvetica", fontSize=10, leading=14,
                     textColor=MUTED, spaceAfter=16)
H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13, leading=17,
                    textColor=ACCENT, spaceBefore=17, spaceAfter=6)
H3 = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=10.4, leading=14,
                    textColor=INK, spaceBefore=11, spaceAfter=4)
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
ALERT = ParagraphStyle("ALERT", parent=KEY, backColor=WARN)
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
        title="Tool-generated documentation in Ruby and C#",
        author="agrawalsnehal3")
    W = doc.width
    s = []
    P = lambda t, st=BODY: s.append(Paragraph(t, st))

    P("Tool-generated documentation", H1)
    P("What YARD and the C# compiler produce, and why their output means "
      "different things", SUB)

    # ---------------------------------------------------------------
    P("The idea", H2)
    P("In both languages you write a comment above a method, and a tool turns "
      "those comments into documentation. Nobody writes the documentation "
      "page — a program builds it from the code.", LEAD)
    P("That is convenient, and it creates a problem for anyone trying to "
      "measure whether packages are documented. The tool runs whether or not "
      "the author wrote anything. An empty result still looks like a result.")

    # ---------------------------------------------------------------
    P("The same idea, two very different outcomes", H2)
    s.append(table([
        ["", "Ruby", "C#"],
        ["The tool", "YARD", "The compiler itself"],
        ["It reads", "# comments above a method",
         "/// comments above a member"],
        ["It produces", "HTML pages", "An XML file"],
        ["Which end up", b("On a website (rubydoc.info)"),
         b("Inside the package")],
        ["Who switches it on", "Nobody — automatic for every gem",
         "The author, via a build setting"],
        ["How many have it", "93% of gems", "65% of packages"],
    ], [W * .21, W * .40, W * .39]))
    s.append(Spacer(1, 10))
    P("One line in that table decides everything else: " + b("where the output "
      "ends up") + ". Ruby's goes to a website. C#'s goes into the package. "
      "That single difference changes whether the generated documentation is "
      "useful to us, and whether its existence means anything.")

    # ---------------------------------------------------------------
    P("Ruby: the page always exists", H2)
    P("rubydoc.info runs YARD over every gem published to RubyGems. Publish a "
      "gem and you get a page, automatically, forever. You do not ask for it "
      "and you cannot decline it.", LEAD)
    P("So the page existing tells you nothing at all about whether the gem is "
      "documented. If the author wrote no comments, the page still appears — "
      "it just lists method names with nothing beside them.")

    s.append(Paragraph(
        b("Measured across the 2,814 gems studied:") + "<br/>"
        "&nbsp;&nbsp;• 93% have a rubydoc.info page<br/>"
        "&nbsp;&nbsp;• " + b("532 of them have a page and zero documented "
        "methods") + "<br/>"
        "&nbsp;&nbsp;• 687 gems have no documented methods at all, yet most "
        "still publish a documentation link", ALERT))

    P("This is why a documentation URL is weak evidence. Counting gems that "
      "“have a documentation link” would report something close to "
      "93%. Counting gems where somebody actually wrote documentation gives a "
      "very different answer:")
    s.append(table([
        ["What you measure", "Result"],
        ["Has a documentation link", "93%"],
        ["Ships a README", "76%"],
        ["Has at least one documented method", "76%"],
        [b("Methods that carry a comment"), b("48%")],
        [b("Has a documentation site a person wrote"), b("20%")],
    ], [W * .62, W * .38]))
    s.append(Spacer(1, 10))
    P("The gap between the first row and the last is the whole point. Both are "
      "true; they answer different questions.")

    P("There is a second consequence. Because rubydoc.info builds its pages "
      "from the gem file, scraping it is pointless — roughly 50 page requests "
      "per version to recover comments that came free with one download. The "
      "generated site is a rendering of something we already have.")

    s.append(PageBreak())

    # ---------------------------------------------------------------
    P("C#: the file ships with the package", H2)
    P("The C# compiler does the same job, but the output is a file placed "
      "beside the assembly inside the .nupkg. There is no website involved.", LEAD)
    P("For each public type and member it writes a structured entry:")
    P("&lt;member name=\"M:Serilog.Log.Information(System.String)\"&gt;<br/>"
      "&nbsp;&nbsp;&lt;summary&gt;Write a log event at Information "
      "level.&lt;/summary&gt;<br/>"
      "&nbsp;&nbsp;&lt;param name=\"messageTemplate\"&gt;The message "
      "template.&lt;/param&gt;<br/>"
      "&lt;/member&gt;", CODE)
    P("This is better than Ruby's arrangement in three ways, and worse in one.")

    P("Better", H3)
    P("• " + b("It is versioned automatically.") + " The file ships with the "
      "package, so version 3.1.0's documentation is inside version 3.1.0.", BULLET)
    P("• " + b("It is structured.") + " Summary, parameters and return value "
      "are separate fields, not prose to be parsed.", BULLET)
    P("• " + b("It needs no scraping.") + " One ranged request reads the "
      "package index; a second reads just this file.", BULLET)

    P("Worse", H3)
    P("• " + b("It is optional.") + " The author must switch on a build "
      "setting. 35% of packages never do, and for those there is nothing "
      "generated at all — no file, and no website either, because the site "
      "that used to render NuGet APIs is gone.", BULLET)

    s.append(Paragraph(
        b("So the presence of the file does mean something in C#.") + " Unlike "
        "rubydoc.info, it appears only when the author enabled it, which is a "
        "weak but genuine signal of intent. 65% of packages carry one.", KEY))

    # ---------------------------------------------------------------
    P("What this means in practice", H2)
    s.append(table([
        ["", "Ruby", "C#"],
        ["Use the generated output?", b("No"),
         b("Yes — it is the main source")],
        ["Because", "It is a website built from the gem we already download",
         "It is a file inside the package we already download"],
        ["Instead, read", "The comments in the gem's source",
         "The XML file beside the assembly"],
        ["Does its existence prove documentation?", b("No — it is automatic"),
         "Partly — the author had to enable it"],
    ], [W * .28, W * .36, W * .36]))
    s.append(Spacer(1, 10))

    P("Both roads lead to the same place: " + b("download the package and read "
      "what is inside it") + ". In Ruby that means parsing comments out of the "
      "source. In C# it means reading a file the compiler already wrote. "
      "Neither requires visiting a documentation website.")

    # ---------------------------------------------------------------
    P("The one number to carry forward", H2)
    P("If a single figure is needed for how well documented an ecosystem is, "
      "it should be the share of methods carrying a comment, not the share of "
      "packages carrying a link.", LEAD)
    P("For Ruby that is " + b("48%") + " of 938,947 methods, with a median gem "
      "at only 24%. For C# the equivalent count is not directly comparable, "
      "because the compiler records only what was written and gives no "
      "denominator of undocumented members — which is itself worth stating "
      "rather than papering over.")

    s.append(Spacer(1, 16))
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
                          "Tool-generated documentation in Ruby and C#")
        canvas.drawRightString(A4[0] - 21 * mm, 8 * mm,
                               str(canvas.getPageNumber()))
        canvas.restoreState()

    doc.build(s, onFirstPage=furniture, onLaterPages=furniture)
    print("wrote", os.path.abspath(OUT),
          "(" + str(round(os.path.getsize(OUT) / 1024)) + " KB)")


if __name__ == "__main__":
    sys.exit(build())
