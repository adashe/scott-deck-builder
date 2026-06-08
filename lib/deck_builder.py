"""SCOTT Automation Deck Builder — deck builder module.

Given form data, produces a customized .pptx file by editing the source template.

The source template at templates/source_deck.pptx contains:
  - Slide 1: cover (locked, never modified)
  - Slide 2: customer slide (graphic at top, empty bottom for customer name/logo)
  - Slide 3: index slide (only the INDEX header; bullets generated dynamically)
  - Slides 4-5: SCOTT History
  - Slides 6-10: Capabilities
  - Slides 11-21: Previous project case studies
  - Slides 22-25: Hydraulic Power Units
  - Slides 26-30: Control Panels
  - Slides 31-32: Engineered Expertise
  - Slides 33-34: Test Stands
  - Slide 35: Real Results
  - Slide 36: Contact (locked, always last)
  - Slide 37: Blank template (not visible; used as source for Why slides + proposal slides)

The build process:
  1. Unpack the source pptx into a temporary directory
  2. Write the customer name/logo onto slide 2
  3. Write the dynamic index onto slide 3
  4. Build the 5 Why slides from slide 37 template, inserted between slides 3 and 4
  5. Build any project-proposal slides from slide 37 template, inserted after Previous Projects
  6. Build one stat slide per selected value driver from slide 37 template
  7. Reorder sldIdLst to match: cover, customer, index, [Why], history, capabilities,
     prev-projects, [proposals], HPU, controls, engineered, test, real-results, contact
  8. Remove any slides whose sub-slides were unchecked
  9. Remove slide 37 from sldIdLst (so it doesn't render in the final deck)
  10. Pack everything back into a fresh pptx
"""

import os
import re
import shutil
import zipfile
import tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image

from .stats_library import get_stat

# Constants from the source template
SLIDE_WIDTH_EMU = 18288000   # 20.0"
SLIDE_HEIGHT_EMU = 10287000  # 11.25"
EMU_PER_INCH = 914400

# Section -> slide-file mapping in the source template (slideN.xml numbers)
SECTION_SLIDES = {
    "history":           [4, 5],
    "capabilities":      [6, 7, 8, 9, 10],
    "previousProjects":  [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
    "hpu":               [22, 23, 24, 25],
    "controls":          [26, 27, 28, 29, 30],
    "engineered":        [31, 32],
    "testStands":        [33, 34],
    "realResults":       [35],
}

# Index labels — matches the existing deck style exactly (your requirement from earlier)
INDEX_LABELS = [
    "Automation Systems",
    "Custom Built Machine & Design",
    "Custom Hydraulic Motion Control Systems",
    "Industrial Custom Control Systems",
    "Motor Starter Controls Centers",
    "Engineered Solutions",
    "Testing Services",
    "Contact and Location Information",
]
# Which user-toggleable sections drive each index line. If ALL the sections in
# a row are turned off, that index line is dropped. The Contact line and any
# line tied only to always-on sections is always shown.
INDEX_LINE_TRIGGERS = {
    "Automation Systems":                       ["capabilities", "previousProjects"],
    "Custom Built Machine & Design":            ["capabilities", "previousProjects"],
    "Custom Hydraulic Motion Control Systems":  ["hpu"],
    "Industrial Custom Control Systems":        ["controls"],
    "Motor Starter Controls Centers":           ["controls"],
    "Engineered Solutions":                     ["engineered"],
    "Testing Services":                         ["testStands"],
    "Contact and Location Information":         None,  # always shown
}

# Map a project-id (from the form) to which slide-file it corresponds to.
# Must stay in sync with PROJECTS in public/js/form.js.
PROJECT_SLIDES = {
    "p11": 11, "p12": 12, "p13": 13, "p14": 14, "p15": 15, "p16": 16,
    "p17": 17, "p18": 18, "p19": 19, "p20": 20, "p21": 21,
}

# Brand tokens
SCOTT_BLUE = "00467F"
ACCENT_SLATE = "748FA6"
DARK_TEXT = "222222"


# ============================================================================
# Low-level pptx unpack / pack helpers
# ============================================================================

def unpack_pptx(pptx_path: str, dest_dir: str):
    """Extract a .pptx (which is a .zip) into a directory."""
    with zipfile.ZipFile(pptx_path, "r") as z:
        z.extractall(dest_dir)


def pack_pptx(src_dir: str, output_path: str):
    """Re-zip a directory of XML files back into a .pptx."""
    src = Path(src_dir)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in src.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(src).as_posix()
                z.write(path, arcname)


# ============================================================================
# Customer slide (slide 2)
# ============================================================================

def apply_customer(work_dir: str, customer_mode: str, customer_name: str, logo_file_path: str | None):
    """Place the customer name (text) or logo (image) on slide 2."""
    slide_path = os.path.join(work_dir, "ppt/slides/slide2.xml")
    with open(slide_path, encoding="utf-8") as f:
        xml = f.read()

    # If we're in logo mode and have a file, embed it as an image shape
    if customer_mode == "logo" and logo_file_path and os.path.exists(logo_file_path):
        media_filename = _add_media_to_pptx(work_dir, logo_file_path, prefix="customerlogo")
        rid = _add_slide_relationship(work_dir, "slide2.xml", media_filename)
        shape_xml = _build_logo_shape_xml(rid, slide_w_emu=SLIDE_WIDTH_EMU, slide_h_emu=SLIDE_HEIGHT_EMU)
    else:
        # Name mode (or logo mode failed for some reason) -> text shape
        shape_xml = _build_customer_name_shape_xml(customer_name or "Customer")

    # Inject the shape just before </p:spTree>
    xml = xml.replace("</p:spTree>", shape_xml + "\n    </p:spTree>", 1)
    with open(slide_path, "w", encoding="utf-8") as f:
        f.write(xml)


def _build_customer_name_shape_xml(name: str) -> str:
    """Raleway Bold black, ~54pt, centered horizontally, sitting in the bottom half."""
    safe_name = _xml_escape(name)
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="CustomerName" id="100"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0">
            <a:off x="914400" y="6858000"/>
            <a:ext cx="16459200" cy="1828800"/>
          </a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="ctr" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p>
            <a:pPr algn="ctr"><a:lnSpc><a:spcPts val="6000"/></a:lnSpc></a:pPr>
            <a:r>
              <a:rPr lang="en-US" b="true" sz="5400">
                <a:solidFill><a:srgbClr val="000000"/></a:solidFill>
                <a:latin typeface="Raleway"/><a:ea typeface="Raleway"/><a:cs typeface="Raleway"/>
              </a:rPr>
              <a:t>{safe_name}</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>'''


def _build_logo_shape_xml(rid: str, slide_w_emu: int, slide_h_emu: int) -> str:
    """Place a logo image, scaled to fit max 2.5" tall and max 12" wide, centered in the bottom half."""
    # Center vertically at y=8.75" (which is ~80% down the slide -- bottom half center)
    # Max box: 12" x 2.5"
    box_w = 12 * EMU_PER_INCH
    box_h = int(2.5 * EMU_PER_INCH)
    x = (slide_w_emu - box_w) // 2
    y = int(7.5 * EMU_PER_INCH)
    return f'''      <p:pic>
        <p:nvPicPr>
          <p:cNvPr name="CustomerLogo" id="100"/>
          <p:cNvPicPr><a:picLocks noChangeAspect="true"/></p:cNvPicPr>
          <p:nvPr/>
        </p:nvPicPr>
        <p:blipFill>
          <a:blip r:embed="{rid}"/>
          <a:stretch><a:fillRect/></a:stretch>
        </p:blipFill>
        <p:spPr>
          <a:xfrm>
            <a:off x="{x}" y="{y}"/>
            <a:ext cx="{box_w}" cy="{box_h}"/>
          </a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
      </p:pic>'''


# ============================================================================
# Index slide (slide 3) — dynamic bullets
# ============================================================================

def apply_index(work_dir: str, sections: dict):
    """Generate the index bullet list based on which sections are enabled.

    sections is a dict keyed by section id (e.g. 'history', 'hpu') with values
    like {'enabled': True, 'subslides': [4, 5]}.
    """
    slide_path = os.path.join(work_dir, "ppt/slides/slide3.xml")
    with open(slide_path, encoding="utf-8") as f:
        xml = f.read()

    # Build the list of index lines to include
    visible_lines = []
    for line in INDEX_LABELS:
        triggers = INDEX_LINE_TRIGGERS.get(line)
        if triggers is None:
            visible_lines.append(line)  # always show (Contact line)
            continue
        # Show if ANY of the trigger sections is enabled
        if any(sections.get(sec_id, {}).get("enabled", False) for sec_id in triggers):
            visible_lines.append(line)

    bullets_xml = "".join(_build_index_bullet_xml(line) for line in visible_lines)
    list_shape = f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="IndexList" id="200"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0">
            <a:off x="2553644" y="2900000"/>
            <a:ext cx="11584534" cy="6500000"/>
          </a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
{bullets_xml}        </p:txBody>
      </p:sp>'''

    xml = xml.replace("</p:spTree>", list_shape + "\n    </p:spTree>", 1)
    with open(slide_path, "w", encoding="utf-8") as f:
        f.write(xml)


def _build_index_bullet_xml(text: str) -> str:
    safe = _xml_escape(text)
    return f'''          <a:p>
            <a:pPr marL="285750" indent="-285750" algn="l">
              <a:lnSpc><a:spcPts val="4800"/></a:lnSpc>
              <a:spcBef><a:spcPts val="600"/></a:spcBef>
              <a:buFont typeface="Arial"/><a:buChar char="\u2022"/>
            </a:pPr>
            <a:r>
              <a:rPr lang="en-US" sz="2800">
                <a:solidFill><a:srgbClr val="{DARK_TEXT}"/></a:solidFill>
                <a:latin typeface="Raleway"/><a:ea typeface="Raleway"/><a:cs typeface="Raleway"/>
              </a:rPr>
              <a:t>{safe}</a:t>
            </a:r>
          </a:p>
'''


# ============================================================================
# Slide-37-based new slides (Why slides, stat slides, proposal slides)
# ============================================================================

def clone_template_slide(work_dir: str, new_slide_num: int) -> str:
    """Clone slide37.xml as a new slide with the given number. Returns the new slide filename."""
    src_xml = os.path.join(work_dir, "ppt/slides/slide37.xml")
    src_rels = os.path.join(work_dir, "ppt/slides/_rels/slide37.xml.rels")
    new_filename = f"slide{new_slide_num}.xml"
    dst_xml = os.path.join(work_dir, "ppt/slides", new_filename)
    dst_rels = os.path.join(work_dir, "ppt/slides/_rels", new_filename + ".rels")
    shutil.copy(src_xml, dst_xml)
    shutil.copy(src_rels, dst_rels)
    return new_filename


def inject_shapes(work_dir: str, slide_filename: str, shapes_xml: str):
    """Insert shape XML before the </p:spTree> closing tag in a slide."""
    path = os.path.join(work_dir, "ppt/slides", slide_filename)
    with open(path, encoding="utf-8") as f:
        xml = f.read()
    xml = xml.replace("</p:spTree>", shapes_xml + "\n    </p:spTree>", 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)


# ----- Why slide builders ---------------------------------------------------

def build_why_pain_point_shapes(pain_point: str) -> str:
    """Slide layout: eyebrow + League Spartan header + Raleway body pull-quote."""
    return (
        _eyebrow_xml("THE CHALLENGE", y_emu=1880000)
        + _header_xml("HERE\u2019S WHAT WE HEARD", y_emu=2385800)
        + _pullquote_xml(pain_point, y_emu=4400000, height_emu=4500000)
    )


def build_why_stat_shapes(stat: dict) -> str:
    return (
        _eyebrow_xml(stat["eyebrow"], y_emu=1480000)
        + _header_xml(stat["headline"], y_emu=1985800)
        + _big_number_xml(stat["big_number"], y_emu=3700000)
        + _supporting_xml(stat["supporting"], y_emu=6600000)
        + _source_xml(stat["source"], y_emu=9500000)
    )


def build_why_success_state_shapes(success_state: str) -> str:
    return (
        _eyebrow_xml("THE TRANSFORMATION", y_emu=1880000)
        + _header_xml("WHAT YOU GET", y_emu=2385800)
        + _pullquote_xml(success_state, y_emu=4400000, height_emu=4500000)
    )


def build_why_plan_shapes(steps: list) -> str:
    """steps is a list of 3 dicts: {'title': ..., 'body': ...}"""
    parts = [
        _eyebrow_xml("THE PLAN", y_emu=1180000),
        _header_xml("HOW WE GET YOU THERE", y_emu=1685800),
    ]
    base_id = 200
    base_y = 3900000
    for i, step in enumerate(steps[:3], start=1):
        parts.append(_step_xml(
            num=str(i),
            title=step.get("title", "") or f"Step {i}",
            body=step.get("body", ""),
            top_emu=base_y + (i - 1) * 2200000,
            sp_id_base=base_id + (i - 1) * 10,
        ))
    return "".join(parts)


def build_why_cta_shapes(cta_text: str) -> str:
    return (
        _eyebrow_xml("THE NEXT STEP", y_emu=2180000)
        + _header_xml("YOUR NEXT STEP", y_emu=2685800)
        + _pullquote_xml(cta_text, y_emu=4900000, height_emu=3500000)
    )


# ----- Proposal slide builder -----------------------------------------------

def build_proposal_shapes(title: str, body: str, media_kind: str,
                          media_rid: str | None, video_url: str | None) -> str:
    """Layout: title at top; left side has body text; right side has media or video link.

    media_kind is one of: 'none', 'image', 'video'.
    media_rid is the slide-rel ID if an image was embedded; otherwise None.
    video_url is the link if media_kind == 'video'.
    """
    parts = [_proposal_title_xml(title or "Project Proposal", y_emu=685800)]

    if media_kind == "none" or (media_kind == "image" and not media_rid) or (media_kind == "video" and not video_url):
        # Text-only: full-width body
        parts.append(_proposal_body_xml(body or "", left_emu=1066800, top_emu=2200000, width_emu=16154400))
    elif media_kind == "image":
        # Image on left, body on right
        parts.append(_proposal_image_xml(media_rid, left_emu=1066800, top_emu=2000000, width_emu=9000000, height_emu=5500000))
        if body:
            parts.append(_proposal_body_xml(body, left_emu=10500000, top_emu=2000000, width_emu=6700000))
    else:  # video
        # Video link card on left, body on right
        parts.append(_video_link_card_xml(video_url, left_emu=1066800, top_emu=2000000, width_emu=9000000, height_emu=5500000))
        if body:
            parts.append(_proposal_body_xml(body, left_emu=10500000, top_emu=2000000, width_emu=6700000))

    return "".join(parts)


# ============================================================================
# Shape-XML builders
# ============================================================================

def _eyebrow_xml(text: str, y_emu: int) -> str:
    """Small slate-blue all-caps label."""
    safe = _xml_escape(text)
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="Eyebrow" id="100"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="1066800" y="{y_emu}"/><a:ext cx="16154400" cy="350000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="l"/>
            <a:r><a:rPr lang="en-US" b="true" sz="1800" spc="200">
              <a:solidFill><a:srgbClr val="{ACCENT_SLATE}"/></a:solidFill>
              <a:latin typeface="Raleway"/><a:ea typeface="Raleway"/><a:cs typeface="Raleway"/>
            </a:rPr><a:t>{safe}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>'''


def _header_xml(text: str, y_emu: int) -> str:
    """Large blue League Spartan header."""
    safe = _xml_escape(text)
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="Header" id="101"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="1066800" y="{y_emu}"/><a:ext cx="16154400" cy="1300000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="l"><a:lnSpc><a:spcPts val="5800"/></a:lnSpc></a:pPr>
            <a:r><a:rPr lang="en-US" b="true" sz="5000">
              <a:solidFill><a:srgbClr val="{SCOTT_BLUE}"/></a:solidFill>
              <a:latin typeface="League Spartan"/><a:ea typeface="League Spartan"/><a:cs typeface="League Spartan"/>
            </a:rPr><a:t>{safe}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>'''


def _pullquote_xml(text: str, y_emu: int, height_emu: int = 4500000) -> str:
    safe = _xml_escape(text)
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="PullQuote" id="102"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="1066800" y="{y_emu}"/><a:ext cx="16154400" cy="{height_emu}"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="l"><a:lnSpc><a:spcPts val="5500"/></a:lnSpc></a:pPr>
            <a:r><a:rPr lang="en-US" sz="3600">
              <a:solidFill><a:srgbClr val="{DARK_TEXT}"/></a:solidFill>
              <a:latin typeface="Raleway"/><a:ea typeface="Raleway"/><a:cs typeface="Raleway"/>
            </a:rPr><a:t>{safe}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>'''


def _big_number_xml(num: str, y_emu: int) -> str:
    safe = _xml_escape(num)
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="BigNumber" id="201"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="1066800" y="{y_emu}"/><a:ext cx="16154400" cy="2500000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="l"><a:lnSpc><a:spcPts val="11000"/></a:lnSpc></a:pPr>
            <a:r><a:rPr lang="en-US" b="true" sz="10000">
              <a:solidFill><a:srgbClr val="{SCOTT_BLUE}"/></a:solidFill>
              <a:latin typeface="League Spartan"/><a:ea typeface="League Spartan"/><a:cs typeface="League Spartan"/>
            </a:rPr><a:t>{safe}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>'''


def _supporting_xml(text: str, y_emu: int) -> str:
    safe = _xml_escape(text)
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="Supporting" id="202"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="1066800" y="{y_emu}"/><a:ext cx="16154400" cy="2500000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="l"><a:lnSpc><a:spcPts val="4800"/></a:lnSpc></a:pPr>
            <a:r><a:rPr lang="en-US" sz="3200">
              <a:solidFill><a:srgbClr val="{DARK_TEXT}"/></a:solidFill>
              <a:latin typeface="Raleway"/><a:ea typeface="Raleway"/><a:cs typeface="Raleway"/>
            </a:rPr><a:t>{safe}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>'''


def _source_xml(text: str, y_emu: int) -> str:
    safe = _xml_escape(text)
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="Source" id="203"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="1066800" y="{y_emu}"/><a:ext cx="16154400" cy="500000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="l"/>
            <a:r><a:rPr lang="en-US" sz="1400" i="true">
              <a:solidFill><a:srgbClr val="888780"/></a:solidFill>
              <a:latin typeface="Raleway"/><a:ea typeface="Raleway"/><a:cs typeface="Raleway"/>
            </a:rPr><a:t>{safe}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>'''


def _step_xml(num: str, title: str, body: str, top_emu: int, sp_id_base: int) -> str:
    safe_title = _xml_escape(title)
    safe_body = _xml_escape(body)
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="StepNum{num}" id="{sp_id_base}"/>
          <p:cNvSpPr/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="1066800" y="{top_emu}"/><a:ext cx="900000" cy="900000"/></a:xfrm>
          <a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="{SCOTT_BLUE}"/></a:solidFill>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="ctr" rtlCol="false"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="ctr"/>
            <a:r><a:rPr lang="en-US" b="true" sz="3600">
              <a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>
              <a:latin typeface="League Spartan"/><a:ea typeface="League Spartan"/><a:cs typeface="League Spartan"/>
            </a:rPr><a:t>{num}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="StepTitle{num}" id="{sp_id_base + 1}"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="2200000" y="{top_emu}"/><a:ext cx="15000000" cy="500000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="l"/>
            <a:r><a:rPr lang="en-US" b="true" sz="2800">
              <a:solidFill><a:srgbClr val="{SCOTT_BLUE}"/></a:solidFill>
              <a:latin typeface="Raleway"/><a:ea typeface="Raleway"/><a:cs typeface="Raleway"/>
            </a:rPr><a:t>{safe_title}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="StepBody{num}" id="{sp_id_base + 2}"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="2200000" y="{top_emu + 550000}"/><a:ext cx="15000000" cy="1300000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="l"><a:lnSpc><a:spcPts val="3000"/></a:lnSpc></a:pPr>
            <a:r><a:rPr lang="en-US" sz="2200">
              <a:solidFill><a:srgbClr val="{DARK_TEXT}"/></a:solidFill>
              <a:latin typeface="Raleway"/><a:ea typeface="Raleway"/><a:cs typeface="Raleway"/>
            </a:rPr><a:t>{safe_body}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>'''


def _proposal_title_xml(text: str, y_emu: int) -> str:
    safe = _xml_escape(text.upper())
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="ProposalTitle" id="101"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="1066800" y="{y_emu}"/><a:ext cx="16154400" cy="900000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="l"><a:lnSpc><a:spcPts val="5000"/></a:lnSpc></a:pPr>
            <a:r><a:rPr lang="en-US" b="true" sz="4400">
              <a:solidFill><a:srgbClr val="{SCOTT_BLUE}"/></a:solidFill>
              <a:latin typeface="League Spartan"/><a:ea typeface="League Spartan"/><a:cs typeface="League Spartan"/>
            </a:rPr><a:t>{safe}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>'''


def _proposal_body_xml(body: str, left_emu: int, top_emu: int, width_emu: int) -> str:
    """Multi-paragraph body. Blank lines separate paragraphs."""
    paragraphs = body.split("\n\n") if body else [""]
    para_xml = ""
    for p in paragraphs:
        safe = _xml_escape(p.strip())
        para_xml += f'''          <a:p>
            <a:pPr algn="l"><a:lnSpc><a:spcPts val="3000"/></a:lnSpc><a:spcAft><a:spcPts val="800"/></a:spcAft></a:pPr>
            <a:r><a:rPr lang="en-US" sz="2000">
              <a:solidFill><a:srgbClr val="{DARK_TEXT}"/></a:solidFill>
              <a:latin typeface="Raleway"/><a:ea typeface="Raleway"/><a:cs typeface="Raleway"/>
            </a:rPr><a:t>{safe}</a:t></a:r>
          </a:p>
'''
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="ProposalBody" id="103"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm rot="0"><a:off x="{left_emu}" y="{top_emu}"/><a:ext cx="{width_emu}" cy="6000000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
{para_xml}        </p:txBody>
      </p:sp>'''


def _proposal_image_xml(rid: str, left_emu: int, top_emu: int, width_emu: int, height_emu: int) -> str:
    return f'''      <p:pic>
        <p:nvPicPr>
          <p:cNvPr name="ProposalImage" id="104"/>
          <p:cNvPicPr><a:picLocks noChangeAspect="true"/></p:cNvPicPr>
          <p:nvPr/>
        </p:nvPicPr>
        <p:blipFill>
          <a:blip r:embed="{rid}"/>
          <a:stretch><a:fillRect/></a:stretch>
        </p:blipFill>
        <p:spPr>
          <a:xfrm><a:off x="{left_emu}" y="{top_emu}"/><a:ext cx="{width_emu}" cy="{height_emu}"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
      </p:pic>'''


def _video_link_card_xml(url: str, left_emu: int, top_emu: int, width_emu: int, height_emu: int) -> str:
    """A play-button card the customer can click to open the video."""
    safe_url = _xml_escape(url)
    # Centered play triangle + URL caption
    center_x = left_emu + width_emu // 2
    center_y = top_emu + height_emu // 2
    triangle_size = 600000  # 0.66"
    return f'''      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="VideoCard" id="105">
            <a:hlinkClick xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="" tooltip="Open video" />
          </p:cNvPr>
          <p:cNvSpPr/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="{left_emu}" y="{top_emu}"/><a:ext cx="{width_emu}" cy="{height_emu}"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="0F2C44"/></a:solidFill>
          <a:ln w="12700"><a:solidFill><a:srgbClr val="{SCOTT_BLUE}"/></a:solidFill></a:ln>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="ctr" rtlCol="false"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="6000" b="true"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Raleway"/></a:rPr><a:t>\u25B6</a:t></a:r></a:p>
          <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1800"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Raleway"/></a:rPr><a:t>Click to open video</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr name="VideoUrl" id="106"/>
          <p:cNvSpPr txBox="true"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="{left_emu}" y="{top_emu + height_emu + 100000}"/><a:ext cx="{width_emu}" cy="400000"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="t" rtlCol="false" tIns="0" lIns="0" bIns="0" rIns="0"/>
          <a:lstStyle/>
          <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1200" i="true"><a:solidFill><a:srgbClr val="888780"/></a:solidFill><a:latin typeface="Raleway"/></a:rPr><a:t>{safe_url}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>'''


# ============================================================================
# Media + relationships
# ============================================================================

def _add_media_to_pptx(work_dir: str, src_image_path: str, prefix: str = "img") -> str:
    """Compress (if needed) and copy an image into ppt/media/. Returns the new filename."""
    media_dir = os.path.join(work_dir, "ppt/media")
    os.makedirs(media_dir, exist_ok=True)

    # Determine the extension and target media filename (use a unique prefix to avoid clashes)
    existing = set(os.listdir(media_dir))
    ext = os.path.splitext(src_image_path)[1].lower().lstrip(".") or "png"
    if ext == "jpg":
        ext = "jpeg"
    i = 1
    while True:
        candidate = f"{prefix}_{i}.{ext}"
        if candidate not in existing:
            break
        i += 1

    dst_path = os.path.join(media_dir, candidate)
    # For PNG/JPG, resize if huge to keep file size sensible. SVG: copy as-is.
    if ext == "svg":
        shutil.copy(src_image_path, dst_path)
    else:
        try:
            with Image.open(src_image_path) as im:
                # Cap dimensions at 1920px wide for slide rendering
                if im.width > 1920:
                    new_h = int(im.height * 1920 / im.width)
                    im = im.resize((1920, new_h), Image.LANCZOS)
                if ext == "jpeg":
                    if im.mode != "RGB":
                        im = im.convert("RGB")
                    im.save(dst_path, "JPEG", quality=85, optimize=True)
                elif ext == "gif":
                    # Keep GIF animations intact: copy through rather than re-saving
                    shutil.copy(src_image_path, dst_path)
                else:  # png
                    im.save(dst_path, "PNG", optimize=True)
        except Exception:
            # Fall back to raw copy if PIL chokes
            shutil.copy(src_image_path, dst_path)

    # Make sure the extension is registered in [Content_Types].xml
    _ensure_content_type(work_dir, ext)
    return candidate


def _ensure_content_type(work_dir: str, ext: str):
    """Ensure [Content_Types].xml has a Default entry for the given extension."""
    ct_path = os.path.join(work_dir, "[Content_Types].xml")
    with open(ct_path, encoding="utf-8") as f:
        ct = f.read()
    if f'Extension="{ext}"' in ct:
        return
    content_type_map = {
        "png": "image/png",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "svg": "image/svg+xml",
    }
    mime = content_type_map.get(ext)
    if not mime:
        return
    new_default = f'  <Default Extension="{ext}" ContentType="{mime}"/>\n'
    ct = ct.replace("</Types>", new_default + "</Types>")
    with open(ct_path, "w", encoding="utf-8") as f:
        f.write(ct)


def _add_slide_relationship(work_dir: str, slide_filename: str, media_filename: str) -> str:
    """Add an image relationship to a slide and return the new rId."""
    rels_path = os.path.join(work_dir, "ppt/slides/_rels", slide_filename + ".rels")
    with open(rels_path, encoding="utf-8") as f:
        rels = f.read()
    # Find next free rId
    existing_ids = [int(m.group(1)) for m in re.finditer(r'Id="rId(\d+)"', rels)]
    next_id = max(existing_ids, default=0) + 1
    rid = f"rId{next_id}"
    new_rel = (
        f'  <Relationship Id="{rid}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        f'Target="../media/{media_filename}"/>\n'
    )
    rels = rels.replace("</Relationships>", new_rel + "</Relationships>")
    with open(rels_path, "w", encoding="utf-8") as f:
        f.write(rels)
    return rid


# ============================================================================
# Slide registration (rels + content types + sldIdLst)
# ============================================================================

def register_new_slide(work_dir: str, slide_filename: str) -> str:
    """Register a newly-created slide file in presentation rels and content types.
    Returns the rId that the new slide is known by.
    """
    # Add to ppt/_rels/presentation.xml.rels
    pres_rels_path = os.path.join(work_dir, "ppt/_rels/presentation.xml.rels")
    with open(pres_rels_path, encoding="utf-8") as f:
        rels = f.read()
    existing_ids = [int(m.group(1)) for m in re.finditer(r'Id="rId(\d+)"', rels)]
    next_id = max(existing_ids, default=0) + 1
    rid = f"rId{next_id}"
    new_rel = (
        f'  <Relationship Id="{rid}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        f'Target="slides/{slide_filename}"/>\n'
    )
    rels = rels.replace("</Relationships>", new_rel + "</Relationships>")
    with open(pres_rels_path, "w", encoding="utf-8") as f:
        f.write(rels)

    # Add to [Content_Types].xml
    ct_path = os.path.join(work_dir, "[Content_Types].xml")
    with open(ct_path, encoding="utf-8") as f:
        ct = f.read()
    if f"slides/{slide_filename}" not in ct:
        new_ct = (
            f'  <Override PartName="/ppt/slides/{slide_filename}" '
            f'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>\n'
        )
        ct = ct.replace("</Types>", new_ct + "</Types>")
        with open(ct_path, "w", encoding="utf-8") as f:
            f.write(ct)

    return rid


def get_slide_rid(work_dir: str, slide_filename: str) -> str:
    """Find the rId that points to a given slide file in presentation rels."""
    pres_rels_path = os.path.join(work_dir, "ppt/_rels/presentation.xml.rels")
    with open(pres_rels_path, encoding="utf-8") as f:
        rels = f.read()
    target_substring = f'Target="slides/{slide_filename}"'
    # Find any <Relationship ...> tag containing the exact target attribute
    for m in re.finditer(r'<Relationship\s+([^>]+)/>', rels):
        attrs = m.group(1)
        if target_substring in attrs:
            id_match = re.search(r'Id="(rId\d+)"', attrs)
            if id_match:
                return id_match.group(1)
    raise RuntimeError(f"Could not find rId for {slide_filename}")


def set_slide_order(work_dir: str, ordered_rids: list):
    """Replace the sldIdLst in presentation.xml with the given rId list (in display order).
    Assigns sequential slide ids starting at 256 to ensure uniqueness.
    """
    pres_path = os.path.join(work_dir, "ppt/presentation.xml")
    with open(pres_path, encoding="utf-8") as f:
        pres = f.read()
    entries = []
    for i, rid in enumerate(ordered_rids):
        slide_id = 256 + i
        entries.append(f'    <p:sldId id="{slide_id}" r:id="{rid}"/>')
    new_block = "<p:sldIdLst>\n" + "\n".join(entries) + "\n  </p:sldIdLst>"
    pres = re.sub(r"<p:sldIdLst>.*?</p:sldIdLst>", new_block, pres, flags=re.DOTALL)
    with open(pres_path, "w", encoding="utf-8") as f:
        f.write(pres)


# ============================================================================
# Top-level build function
# ============================================================================

def build_deck(template_path: str, output_path: str, form_data: dict,
               customer_logo_path: str | None = None,
               proposal_image_paths: dict | None = None):
    """Generate a customized .pptx at output_path from the template + form data.

    proposal_image_paths is a dict keyed by proposal-index (int) mapping to local file paths.
    """
    proposal_image_paths = proposal_image_paths or {}

    with tempfile.TemporaryDirectory() as work_dir:
        unpack_pptx(template_path, work_dir)

        # 1) Customer slide
        apply_customer(
            work_dir,
            customer_mode=form_data.get("customerMode", "name"),
            customer_name=form_data.get("customerName", ""),
            logo_file_path=customer_logo_path,
        )

        # 2) Index slide (dynamic)
        apply_index(work_dir, form_data.get("sections", {}))

        # 3) Allocate slide-file numbers for all the new slides we'll create
        new_slide_counter = 100  # Start well above existing 1-37 to avoid clashes
        def next_slide_num():
            nonlocal new_slide_counter
            new_slide_counter += 1
            return new_slide_counter

        # 4) Build the 5 Why slides
        why_filenames = []
        pain_point = form_data.get("painPoint", "").strip()
        success_state = form_data.get("successState", "").strip()
        plan = form_data.get("plan", {})
        cta = form_data.get("callToAction", "").strip()
        value_drivers = form_data.get("valueDrivers", [])

        # Pain point
        if pain_point:
            fn = clone_template_slide(work_dir, next_slide_num())
            inject_shapes(work_dir, fn, build_why_pain_point_shapes(pain_point))
            why_filenames.append(fn)

        # Stat slides (one per selected value driver)
        for tag in value_drivers:
            stat = get_stat(tag)
            if not stat:
                continue
            fn = clone_template_slide(work_dir, next_slide_num())
            inject_shapes(work_dir, fn, build_why_stat_shapes(stat))
            why_filenames.append(fn)

        # Success state
        if success_state:
            fn = clone_template_slide(work_dir, next_slide_num())
            inject_shapes(work_dir, fn, build_why_success_state_shapes(success_state))
            why_filenames.append(fn)

        # Plan
        if any(plan.get(f"step{i}", {}).get("title") for i in (1, 2, 3)):
            steps = [plan.get(f"step{i}", {}) for i in (1, 2, 3)]
            fn = clone_template_slide(work_dir, next_slide_num())
            inject_shapes(work_dir, fn, build_why_plan_shapes(steps))
            why_filenames.append(fn)

        # CTA
        if cta:
            fn = clone_template_slide(work_dir, next_slide_num())
            inject_shapes(work_dir, fn, build_why_cta_shapes(cta))
            why_filenames.append(fn)

        # Register the Why slides
        for fn in why_filenames:
            register_new_slide(work_dir, fn)

        # 5) Build proposal slides
        proposal_filenames = []
        for i, proposal in enumerate(form_data.get("proposals", [])):
            title = proposal.get("title", "").strip()
            body = proposal.get("body", "").strip()
            kind = proposal.get("mediaKind", "none")
            # Must have at least a title to bother creating the slide
            if not title and not body and kind == "none":
                continue
            fn = clone_template_slide(work_dir, next_slide_num())
            register_new_slide(work_dir, fn)

            media_rid = None
            if kind == "image":
                img_path = proposal_image_paths.get(i)
                if img_path and os.path.exists(img_path):
                    media_filename = _add_media_to_pptx(work_dir, img_path, prefix="proposal")
                    media_rid = _add_slide_relationship(work_dir, fn, media_filename)
                else:
                    kind = "none"  # fall back to text-only
            video_url = proposal.get("videoUrl", "") if kind == "video" else None
            shapes = build_proposal_shapes(title, body, kind, media_rid, video_url)
            inject_shapes(work_dir, fn, shapes)
            proposal_filenames.append(fn)

        # 6) Build the new slide order
        sections = form_data.get("sections", {})
        projects = form_data.get("projects", [])
        ordered_rids = _build_slide_order(work_dir, sections, projects, why_filenames, proposal_filenames)
        set_slide_order(work_dir, ordered_rids)

        # 7) Pack
        pack_pptx(work_dir, output_path)


def _build_slide_order(work_dir: str, sections: dict, projects: list,
                       why_filenames: list, proposal_filenames: list) -> list:
    """Compute the final list of rIds in display order.

    Order:
      cover (slide1) -> customer (slide2) -> index (slide3) -> Why slides ->
      history -> capabilities -> previous projects -> proposal slides ->
      hpu -> controls -> engineered -> testStands -> realResults -> contact (slide36)
    """
    rid = lambda fn: get_slide_rid(work_dir, fn)
    order = []

    # Cover, customer, index — always shown
    order.append(rid("slide1.xml"))
    order.append(rid("slide2.xml"))
    order.append(rid("slide3.xml"))

    # Why slides
    for fn in why_filenames:
        order.append(rid(fn))

    # SCOTT sections in their fixed order
    section_order = [
        "history", "capabilities", "previousProjects",
        # "proposals" injection point is right after previousProjects
        "hpu", "controls", "engineered", "testStands", "realResults",
    ]
    proposals_injected = False
    for sec_id in section_order:
        sec_state = sections.get(sec_id, {})
        if not sec_state.get("enabled", False):
            # Still inject proposals at the right position even if previousProjects was off
            if sec_id == "previousProjects" and not proposals_injected:
                for fn in proposal_filenames:
                    order.append(rid(fn))
                proposals_injected = True
            continue

        if sec_id == "previousProjects":
            # Only the projects the rep checked
            for proj_id in projects:
                slide_num = PROJECT_SLIDES.get(proj_id)
                if slide_num:
                    order.append(rid(f"slide{slide_num}.xml"))
            # Then inject proposals
            for fn in proposal_filenames:
                order.append(rid(fn))
            proposals_injected = True
        else:
            slide_nums = sec_state.get("subslides")
            if slide_nums is None:
                # Section without sub-slides (realResults) — use all its slides
                slide_nums = SECTION_SLIDES[sec_id]
            for sn in slide_nums:
                order.append(rid(f"slide{sn}.xml"))

    # If proposals weren't injected anywhere (all preceding sections off), put them after Why slides
    if not proposals_injected and proposal_filenames:
        # Insert right after the Why slides (position 3 + len(why_filenames))
        insert_at = 3 + len(why_filenames)
        for offset, fn in enumerate(proposal_filenames):
            order.insert(insert_at + offset, rid(fn))

    # Contact slide is always last
    order.append(rid("slide36.xml"))

    return order


# ============================================================================
# Utilities
# ============================================================================

def _xml_escape(s: str) -> str:
    """Escape text for safe insertion into XML."""
    if s is None:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#39;"))
