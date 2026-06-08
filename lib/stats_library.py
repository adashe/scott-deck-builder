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
        "source": "Source: U.S. Bureau of Labor Statistics, Survey of Occupational Injuries and Illnesses, 2024",
    },
    "labor": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE LABOR CRUNCH",
        "big_number": "1.9M",
        "supporting": (
            "U.S. manufacturing jobs may go unfilled by 2033 if current trends hold. "
            "65% of manufacturers say attracting and retaining talent is their top business challenge."
        ),
        "source": "Source: Deloitte & The Manufacturing Institute, Taking Charge of Manufacturing's Workforce Crisis, 2024",
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
        "source": "Source: McKinsey & Company, The next frontier of automation in manufacturing, 2022",
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
        "source": "Source: Siemens / Senseye, True Cost of Downtime Report, 2024",
    },
    "quality": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE QUALITY DIVIDEND",
        "big_number": "60\u201370%",
        "supporting": (
            "Reduction in scrap and false-reject rates documented in published case studies for "
            "automated inspection. McKinsey research shows automation cuts errors by roughly 50% "
            "in digitized workflows overall."
        ),
        "source": "Source: McKinsey & Company, The state of AI in manufacturing, 2024",
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
        "source": "Source: McKinsey & Company, The next frontier of automation in manufacturing, 2024",
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
        "source": "Source: U.S. Bureau of Labor Statistics, 2023\u201324 data",
    },
    "compliance": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE COST OF A CITATION",
        "big_number": "$16,131",
        "supporting": (
            "Maximum penalty for a serious OSHA violation in 2024. Each cUL/UL 508A and 698A "
            "certification SCOTT carries on its control packages removes a common audit finding "
            "before an inspector even arrives."
        ),
        "source": "Source: U.S. Occupational Safety and Health Administration, penalty schedule effective 2024",
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
        "source": "Source: U.S. Department of Energy, Industrial Assessment Center benchmarking data",
    },
    "floorspace": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "RECLAIMING THE FLOOR",
        "big_number": "30\u201340%",
        "supporting": (
            "Typical footprint reduction when legacy layouts are replaced with vertical-reservoir HPUs "
            "and integrated control packages. The reclaimed space often pays for the project on its own "
            "in plants where expansion is constrained."
        ),
        "source": "Source: Industry-typical range \u2014 validated per project against your facility plan",
    },
    "retention": {
        "eyebrow": "WHAT'S AT STAKE",
        "headline": "THE RETENTION FACTOR",
        "big_number": "2.7\u00d7",
        "supporting": (
            "Manufacturing employees with modern, automated tools are 2.7\u00d7 less likely to leave "
            "than those without. Average sector turnover sits above 40% in many segments \u2014 a number "
            "automation can move."
        ),
        "source": "Source: Deloitte, Workforce Experience in Manufacturing, 2024",
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
        "source": "Source: NCCI Experience Rating Plan Manual, industry-typical range",
    },
}


def get_stat(tag_id: str) -> dict:
    """Return the stat record for a value-driver tag, or None if unknown."""
    return STATS.get(tag_id)


def all_tags() -> list:
    """Return the list of known tag ids (for validation)."""
    return list(STATS.keys())
