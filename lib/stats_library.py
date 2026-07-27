"""SCOTT Automation Deck Builder — stats library.

For each value-driver tag the rep selects, we auto-insert one slide showing
a credible national-level statistic. This module is the single source of truth
for the stats; the deck_builder reads from it.

Each stat has:
  - eyebrow: the small label above the headline (e.g. "WHAT'S AT STAKE")
  - headline: the large slide title
  - big_number: the hero number (e.g. "2.5M", "$260K")
  - supporting: the prose paragraph explaining context
  - source: citation line at the bottom of the slide
"""

STATS = {
    "safety": {
        "eyebrow": "YOU'RE NOT ALONE \u2014 HERE'S WHAT'S AT STAKE",
        "headline": "THE NATIONAL PICTURE",
        "big_number": "2.5M",
        "supporting": (
            "nonfatal workplace injuries reported by U.S. private industry in 2024. "
            "Median 8 days away from work per case. 946,000 cases driven by overexertion "
            "and repetitive motion \u2014 the same forces hitting your production line."
        ),
        "source": "📊 Industry Research: U.S. Bureau of Labor Statistics, Survey of Occupational Injuries and Illnesses, 2024 (released Jan. 22, 2026)",
    },
    "labor": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE LABOR CRUNCH",
        "big_number": "1.9M",
        "supporting": (
            "U.S. manufacturing jobs may go unfilled by 2033 if current trends hold. "
            "65% of manufacturers say attracting and retaining talent is their top business challenge."
        ),
        "source": "📊 Industry Research: Deloitte & The Manufacturing Institute, Taking Charge: Manufacturers Support Growth with Active Workforce Strategies, 2024",
    },
    "throughput": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "WHAT AUTOMATION DELIVERS",
        "big_number": "10\u201330%",
        "supporting": (
            "Typical throughput gains from manufacturing automation, with labor productivity "
            "improvements of 15\u201330% in the same studies. Numbers vary by line type and "
            "current state, but the direction is consistent."
        ),
        "source": "📊 Industry Research: Published manufacturing automation case studies; McKinsey & Company, The Next Frontier of Automation in Manufacturing, 2022",
    },
    "downtime": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE COST OF STOPPING",
        "big_number": "$260K/hr",
        "supporting": (
            "Average cost of unplanned downtime for industrial manufacturers \u2014 about $50 billion "
            "per year across U.S. manufacturing. A typical plant logs roughly 800 hours of unplanned "
            "downtime annually."
        ),
        "source": "📊 Industry Research: Siemens / Senseye, True Cost of Downtime 2024 — figure reflects larger manufacturers; costs vary by facility size and sector",
    },
    "quality": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE QUALITY DIVIDEND",
        "big_number": "60\u201370%",
        "supporting": (
            "Published automation and machine-vision case studies commonly report 60\u201370% reductions "
            "in scrap or inspection errors. Results vary by line type and baseline defect rate; "
            "SCOTT engineering validates specific projections against your process data."
        ),
        "source": "📊 Industry Research: Published automation and machine-vision case studies; range is representative, not a universal benchmark",
    },
    "leadtime": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "TIME TO PAYBACK",
        "big_number": "1\u20133 yrs",
        "supporting": (
            "Typical payback period for automation projects today \u2014 down from 5\u20138 years "
            "historically. The pace of integration has accelerated roughly 2\u00d7 as suppliers, "
            "tooling, and standards have matured."
        ),
        "source": "📊 Industry Research: Automation ROI literature broadly; McKinsey & Company, The Next Frontier of Automation in Manufacturing, 2024",
    },
    "ergonomics": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE ERGONOMIC TOLL",
        "big_number": "946K",
        "supporting": (
            "Days-away-from-work cases caused by overexertion and repetitive motion in U.S. "
            "private industry. These injuries are the leading category of musculoskeletal disorders "
            "in manufacturing settings \u2014 and the most addressable by automation."
        ),
        "source": "📊 Industry Research: U.S. Bureau of Labor Statistics, Survey of Occupational Injuries and Illnesses, 2024",
    },
    "compliance": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE COST OF A CITATION",
        "big_number": "$16,550",
        "supporting": (
            "Maximum penalty for a serious OSHA violation as of 2025–2026. Each cUL/UL 508A and 698A "
            "certification SCOTT carries on its control packages removes a common audit finding "
            "before an inspector even arrives."
        ),
        "source": "📊 Industry Research: U.S. Occupational Safety and Health Administration, penalty schedule effective Jan. 15, 2025 (current through 2026)",
    },
    "energy": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE ENERGY OPPORTUNITY",
        "big_number": "20\u201350%",
        "supporting": (
            "Motor energy savings achievable on hydraulic power units when fixed-displacement systems "
            "are replaced with variable-frequency drives. Savings persist for the life of the system "
            "and compound with utility rate increases."
        ),
        "source": "📊 Industry Research: U.S. Department of Energy / Hydraulic Institute — VFD energy savings guidance; 20–50% range is conservative relative to published studies",
    },
    "floorspace": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "RECLAIMING THE FLOOR",
        "big_number": "____%",
        "supporting": (
            "Estimated footprint reduction for this project, based on SCOTT Industrial Systems project experience. "
            "Enter the projected percentage above before presenting. "
            "Reclaimed floor space often pays for the project on its own in plants where expansion is constrained."
        ),
        "source": "🔧 SCOTT Project Experience: Typical range based on SCOTT Industrial Systems project history; validated per project against your facility plan",
    },
    "retention": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE RETENTION FACTOR",
        "big_number": "2.7\u00d7",
        "supporting": (
            "Employees who believe they can build future-ready skills are 2.7\u00d7 less likely to leave "
            "within 12 months. Modernization and automation create the skill-building environment that "
            "drives this outcome \u2014 and average sector turnover above 40% makes the stakes clear."
        ),
        "source": "📊 Industry Research: Deloitte & The Manufacturing Institute, Taking Charge: Manufacturers Support Growth with Active Workforce Strategies, 2024",
    },
    "insurance": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE MOD RATE COMPOUND",
        "big_number": "0.10\u20130.40",
        "supporting": (
            "Typical Experience Mod Rate increase from a single OSHA recordable injury, sustained "
            "across three years of premium calculations. Even one prevented claim can reset the "
            "trajectory."
        ),
        "source": "🔧 SCOTT Project Experience: Consistent with NCCI Experience Rating Plan actuarial methodology; no single published benchmark — present as industry-typical range",
    },
}


def get_stat(tag_id: str) -> dict:
    """Return the stat record for a value-driver tag, or None if unknown."""
    return STATS.get(tag_id)

def all_tags() -> list:
    """Return the list of known tag ids (for validation)."""
    return list(STATS.keys())