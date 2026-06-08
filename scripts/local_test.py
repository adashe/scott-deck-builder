"""Local test of the deck + script generation pipeline.

Run from the repo root:
    python3 scripts/local_test.py

Produces test_output/ containing the deck and script (and the zip the API
would have returned).
"""
import os
import sys
import json
import shutil
import zipfile
import tempfile

# Resolve the repo root and make lib/ importable
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from lib.deck_builder import build_deck
from lib.script_builder import build_script


# Synthetic form submission representing a real-world rep's input
SAMPLE_META = {
    "customerMode": "name",
    "customerName": "Acme Manufacturing",
    "customerLogoFilename": "",
    "painPoint": (
        "Operators on the press line keep getting wrist and shoulder injuries. "
        "Three OSHA-recordable claims this year. The team is short two positions "
        "you can't fill, overtime is climbing, and every claim adds another tick "
        "to your experience mod rate."
    ),
    "valueDrivers": ["safety", "labor", "throughput"],
    "successState": (
        "A press line that runs three shifts without overtime. Zero recordable "
        "injuries from operator handling. 18% more parts out the door each week "
        "— and your best operators promoted to roles that use their judgment, "
        "not their joints."
    ),
    "plan": {
        "step1": {
            "title": "Design and build",
            "body": "We engineer a robotic tending cell around your existing press — 3D CAD layout in two weeks, full design review with your team before fabrication.",
        },
        "step2": {
            "title": "Integrate and commission",
            "body": "We install and validate on-site without disrupting current production. Acceptance testing against agreed cycle-time and quality targets.",
        },
        "step3": {
            "title": "Train and support",
            "body": "Operator and maintenance training built in. Backed by SCOTT's service network and the same engineering team that built it.",
        },
    },
    "callToAction": (
        "Walk the press line with our engineering team next Thursday. We'll bring "
        "a draft 3D CAD layout the following week — no commitment, just a clear "
        "picture of what's possible."
    ),
    "sections": {
        "history":          {"enabled": True, "subslides": [4, 5]},
        "capabilities":     {"enabled": True, "subslides": [6, 7, 8, 9, 10]},
        "previousProjects": {"enabled": True, "subslides": None},
        "hpu":              {"enabled": True, "subslides": [22, 23, 24, 25]},
        "controls":         {"enabled": True, "subslides": [26, 27, 28, 29, 30]},
        "engineered":       {"enabled": True, "subslides": [31, 32]},
        "testStands":       {"enabled": True, "subslides": [33, 34]},
        "realResults":      {"enabled": True, "subslides": None},
    },
    "projects": ["p11", "p12", "p21"],
    "proposals": [
        {
            "title": "Proposed solution — Phase 1",
            "body": (
                "Replace manual loading with a robotic tending cell to increase "
                "throughput and free three operators for higher-value work.\n\n"
                "Estimated timeline: 7 months, concept to commissioning."
            ),
            "mediaKind": "none",
            "mediaFileIndex": None,
            "videoUrl": "",
        },
        {
            "title": "Investment & next steps",
            "body": (
                "SCOTT Automation will deliver the proposed machine tending cell "
                "on a fixed-fee basis, with progress payments tied to design "
                "approval, fabrication, and on-site acceptance testing."
            ),
            "mediaKind": "video",
            "mediaFileIndex": None,
            "videoUrl": "https://example.com/walkthrough-video",
        },
    ],
}


def main():
    template_path = os.path.join(ROOT, "templates", "source_deck.pptx")
    assert os.path.exists(template_path), f"Template not found at {template_path}"

    out_dir = os.path.join(ROOT, "test_output")
    os.makedirs(out_dir, exist_ok=True)

    deck_path = os.path.join(out_dir, "SCOTT_Acme_Deck.pptx")
    script_path = os.path.join(out_dir, "SCOTT_Acme_Script.docx")
    bundle_path = os.path.join(out_dir, "SCOTT_Acme_Bundle.zip")

    print("Building deck...")
    build_deck(template_path, deck_path, SAMPLE_META, customer_logo_path=None, proposal_image_paths={})
    print(f"  Wrote {deck_path} ({os.path.getsize(deck_path)/1024/1024:.1f} MB)")

    print("Building selling script...")
    build_script(SAMPLE_META, script_path)
    print(f"  Wrote {script_path} ({os.path.getsize(script_path)/1024:.1f} KB)")

    print("Zipping bundle...")
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(deck_path, arcname=os.path.basename(deck_path))
        z.write(script_path, arcname=os.path.basename(script_path))
    print(f"  Wrote {bundle_path} ({os.path.getsize(bundle_path)/1024/1024:.1f} MB)")

    print("\n✓ All done. Outputs in", out_dir)


if __name__ == "__main__":
    main()
