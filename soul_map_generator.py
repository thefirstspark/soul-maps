#!/usr/bin/env python3
"""
Soul Map Generator — The First Spark
============================================
Generates complete Soul Map HTML pages from birth data,
then auto-pushes to the soul-maps GitHub Pages repo.

Usage:
    python soul_map_generator.py --name "Joshua Rivera" --date 1990-03-15 --time 14:30 --city "Columbus"

Minimal (no birth time = no Rising sign):
    python soul_map_generator.py --name "Joshua Rivera" --date 1990-03-15
"""

import os
import sys
import subprocess
import argparse
import csv
from datetime import datetime, date
from pathlib import Path
from string import Template

# ============================================================
# 1. NUMEROLOGY ENGINE
# ============================================================

MASTER_NUMBERS = {11, 22, 33}

PYTHAGOREAN_MAP = {
    'A':1,'B':2,'C':3,'D':4,'E':5,'F':6,'G':7,'H':8,'I':9,
    'J':1,'K':2,'L':3,'M':4,'N':5,'O':6,'P':7,'Q':8,'R':9,
    'S':1,'T':2,'U':3,'V':4,'W':5,'X':6,'Y':7,'Z':8
}

VOWELS = set('AEIOU')


def reduce_number(n, preserve_masters=True):
    """Reduce to single digit, preserving master numbers if flagged."""
    while n > 9:
        if preserve_masters and n in MASTER_NUMBERS:
            return n
        n = sum(int(d) for d in str(n))
    return n


def life_path(birth_date):
    """Calculate Life Path number from birth date."""
    d = birth_date
    month = reduce_number(d.month, preserve_masters=True)
    day = reduce_number(d.day, preserve_masters=True)
    year = reduce_number(sum(int(c) for c in str(d.year)), preserve_masters=True)
    total = month + day + year
    return reduce_number(total, preserve_masters=True)


def name_to_number(name, filter_fn=None):
    """Convert name to numerological number, optionally filtering letters."""
    clean = name.upper().replace(' ', '')
    if filter_fn:
        clean = ''.join(c for c in clean if filter_fn(c))
    total = sum(PYTHAGOREAN_MAP.get(c, 0) for c in clean)
    return reduce_number(total, preserve_masters=True)


def expression_number(full_name):
    return name_to_number(full_name)


def soul_urge_number(full_name):
    return name_to_number(full_name, filter_fn=lambda c: c in VOWELS)


def personality_number(full_name):
    return name_to_number(full_name, filter_fn=lambda c: c not in VOWELS)


def birthday_number(birth_date):
    return reduce_number(birth_date.day, preserve_masters=True)


def personal_year(birth_date, current_year=None):
    """Calculate Personal Year cycle."""
    if current_year is None:
        current_year = date.today().year
    month = reduce_number(birth_date.month, preserve_masters=False)
    day = reduce_number(birth_date.day, preserve_masters=False)
    year = reduce_number(sum(int(c) for c in str(current_year)), preserve_masters=False)
    return reduce_number(month + day + year, preserve_masters=True)


def personal_month(birth_date, current_year=None, current_month=None):
    """Calculate Personal Month."""
    if current_year is None:
        current_year = date.today().year
    if current_month is None:
        current_month = date.today().month
    py = personal_year(birth_date, current_year)
    return reduce_number(py + current_month, preserve_masters=True)


def maturity_number(full_name, birth_date):
    """Calculate Maturity Number: Expression + Life Path, reduced.
    Traits that emerge in maturity (typically after age 35).
    """
    expr = expression_number(full_name)
    lp = life_path(birth_date)
    return reduce_number(expr + lp, preserve_masters=True)


def hidden_passion(full_name):
    """Find the most frequent digit (1-9) in full name.
    Represents deepest unconscious motivation.
    """
    clean = full_name.upper().replace(' ', '')
    digit_counts = {str(i): 0 for i in range(1, 10)}
    for c in clean:
        digit = PYTHAGOREAN_MAP.get(c)
        if digit:
            digit_counts[str(digit)] += 1
    # Get most frequent; if tie, return lowest digit
    most_frequent = max(digit_counts.items(), key=lambda x: (x[1], -int(x[0])))[0]
    return int(most_frequent)


def karmic_lessons(full_name):
    """Find which digits (1-9) are ABSENT from the name.
    These represent the lessons you came to learn.
    """
    clean = full_name.upper().replace(' ', '')
    present_digits = set()
    for c in clean:
        digit = PYTHAGOREAN_MAP.get(c)
        if digit:
            present_digits.add(digit)
    missing = [i for i in range(1, 10) if i not in present_digits]
    return missing


def karmic_debt(life_path_num, expression_num, soul_urge_num, personality_num, birthday_num):
    """Check if any core number contains a karmic debt number (13, 14, 16, 19 before reduction).
    Returns a dict of debts found.
    """
    # Check before reduction to find unreduced karmic debt numbers
    core_nums = {
        'life_path': life_path_num,
        'expression': expression_num,
        'soul_urge': soul_urge_num,
        'personality': personality_num,
        'birthday': birthday_num,
    }

    # We need to track unreduced numbers; for now, check if the reduced number came from a debt
    # This requires calculating the unreduced intermediate sums
    # Simplified: flag if reduced number is in [4, 5, 7, 8] and has karmic debt pattern
    debts_found = {}

    # Karmic debt numbers: 13→4, 14→5, 16→7, 19→1 (when reduced without preservation)
    karmic_patterns = {
        13: ('13/4', 'Impulsiveness. Indiscipline. Break the same patterns.'),
        14: ('14/5', 'Abuse of freedom. Scatter energy. Ground yourself.'),
        16: ('16/7', 'Betrayal. Self-undoing. Ego-driven choices backfire.'),
        19: ('19/1', 'Dependence masquerading as independence. Build true autonomy.'),
    }

    return debts_found


def pinnacles(birth_date):
    """Calculate 4 pinnacle numbers representing major life phases.
    P1: Month + Day | P2: Day + Year | P3: P1 + P2 | P4: Month + Year
    Ages: P1 (0-34ish), P2 (35-ish to 48-ish), P3 (49-ish to 56-ish), P4 (57+)
    """
    month = reduce_number(birth_date.month, preserve_masters=False)
    day = reduce_number(birth_date.day, preserve_masters=False)
    year = reduce_number(sum(int(c) for c in str(birth_date.year)), preserve_masters=False)

    p1 = reduce_number(month + day, preserve_masters=True)
    p2 = reduce_number(day + year, preserve_masters=True)
    p3 = reduce_number(p1 + p2, preserve_masters=True)
    p4 = reduce_number(month + year, preserve_masters=True)

    return {
        'pinnacle_1': p1,
        'pinnacle_2': p2,
        'pinnacle_3': p3,
        'pinnacle_4': p4,
    }


def challenges(birth_date):
    """Calculate 4 challenge numbers (absolute difference of pinnacle components).
    C1: abs(Month - Day) | C2: abs(Day - Year) | C3: abs(C1 - C2) | C4: abs(Month - Year)
    """
    month = reduce_number(birth_date.month, preserve_masters=False)
    day = reduce_number(birth_date.day, preserve_masters=False)
    year = reduce_number(sum(int(c) for c in str(birth_date.year)), preserve_masters=False)

    c1 = reduce_number(abs(month - day), preserve_masters=True)
    c2 = reduce_number(abs(day - year), preserve_masters=True)
    c3 = reduce_number(abs(c1 - c2), preserve_masters=True)
    c4 = reduce_number(abs(month - year), preserve_masters=True)

    return {
        'challenge_1': c1,
        'challenge_2': c2,
        'challenge_3': c3,
        'challenge_4': c4,
    }


def personal_day(birth_date, current_year=None, current_month=None, current_day=None):
    """Calculate Personal Day: Personal Month + current day, reduced.
    Provides daily micro-cycle guidance.
    """
    if current_year is None:
        current_year = date.today().year
    if current_month is None:
        current_month = date.today().month
    if current_day is None:
        current_day = date.today().day

    pm = personal_month(birth_date, current_year, current_month)
    day_reduced = reduce_number(current_day, preserve_masters=False)
    return reduce_number(pm + day_reduced, preserve_masters=True)


# ============================================================
# 2. CHINESE ZODIAC ENGINE
# ============================================================

CHINESE_ANIMALS = [
    'Rat', 'Ox', 'Tiger', 'Rabbit', 'Dragon', 'Snake',
    'Horse', 'Goat', 'Monkey', 'Rooster', 'Dog', 'Pig'
]

CHINESE_ELEMENTS = ['Wood', 'Wood', 'Fire', 'Fire', 'Earth', 'Earth',
                     'Metal', 'Metal', 'Water', 'Water']


def chinese_zodiac(year):
    """Return (animal, element) tuple for a given year."""
    animal = CHINESE_ANIMALS[(year - 4) % 12]
    element = CHINESE_ELEMENTS[(year - 4) % 10]
    return animal, element


# ============================================================
# 3. WESTERN ASTROLOGY (Sun sign always; Moon/Rising if time given)
# ============================================================

ZODIAC_DATES = [
    ((3,21), (4,19), 'Aries', '\u2648'),
    ((4,20), (5,20), 'Taurus', '\u2649'),
    ((5,21), (6,20), 'Gemini', '\u264a'),
    ((6,21), (7,22), 'Cancer', '\u264b'),
    ((7,23), (8,22), 'Leo', '\u264c'),
    ((8,23), (9,22), 'Virgo', '\u264d'),
    ((9,23), (10,22), 'Libra', '\u264e'),
    ((10,23), (11,21), 'Scorpio', '\u264f'),
    ((11,22), (12,21), 'Sagittarius', '\u2650'),
    ((12,22), (1,19), 'Capricorn', '\u2651'),
    ((1,20), (2,18), 'Aquarius', '\u2652'),
    ((2,19), (3,20), 'Pisces', '\u2653'),
]


def sun_sign(birth_date):
    m, d = birth_date.month, birth_date.day
    for (sm, sd), (em, ed), name, symbol in ZODIAC_DATES:
        if sm > em:  # Capricorn wraps
            if (m == sm and d >= sd) or (m == em and d <= ed) or (m == 12 and m > sm):
                return name, symbol
        else:
            if (m == sm and d >= sd) or (m == em and d <= ed) or (sm < m < em):
                return name, symbol
    return 'Unknown', '?'


def get_full_chart(name, year, month, day, hour, minute, city, country='US'):
    """Get Moon + Rising using kerykeion. Returns dict or None on failure."""
    try:
        from kerykeion import AstrologicalSubject
        s = AstrologicalSubject(name, year, month, day, hour, minute, city, country)

        SIGN_MAP = {
            'Ari': 'Aries', 'Tau': 'Taurus', 'Gem': 'Gemini', 'Can': 'Cancer',
            'Leo': 'Leo', 'Vir': 'Virgo', 'Lib': 'Libra', 'Sco': 'Scorpio',
            'Sag': 'Sagittarius', 'Cap': 'Capricorn', 'Aqu': 'Aquarius', 'Pis': 'Pisces'
        }

        return {
            'moon_sign': SIGN_MAP.get(s.moon['sign'], s.moon['sign']),
            'rising_sign': SIGN_MAP.get(s.first_house['sign'], s.first_house['sign']),
            'mercury': SIGN_MAP.get(s.mercury['sign'], s.mercury['sign']),
            'venus': SIGN_MAP.get(s.venus['sign'], s.venus['sign']),
            'mars': SIGN_MAP.get(s.mars['sign'], s.mars['sign']),
            'jupiter': SIGN_MAP.get(s.jupiter['sign'], s.jupiter['sign']),
            'saturn': SIGN_MAP.get(s.saturn['sign'], s.saturn['sign']),
        }
    except Exception as e:
        print(f"[WARN] Kerykeion chart failed: {e}", file=sys.stderr)
        return None


# ============================================================
# 4. SELECTOR MODEL MAPPING
# ============================================================

def selector_layer(life_path_num):
    """Map Life Path to dominant Selector Model layer."""
    mapping = {
        1: ('Temporal', 'Pioneer frequency \u2014 you initiate timelines'),
        2: ('Relational', 'Bridge frequency \u2014 you weave connection fields'),
        3: ('Metaphysical', 'Expression frequency \u2014 you transmit through creation'),
        4: ('Physics', 'Structure frequency \u2014 you build the architecture of reality'),
        5: ('Temporal', 'Freedom frequency \u2014 you collapse fixed timelines'),
        6: ('Relational', 'Harmony frequency \u2014 you calibrate collective fields'),
        7: ('Metaphysical', 'Seeker frequency \u2014 you decode hidden patterns'),
        8: ('Physics', 'Power frequency \u2014 you materialize abstract into concrete'),
        9: ('Relational', 'Completion frequency \u2014 you integrate all signal layers'),
        11: ('Metaphysical', 'Master Intuitive \u2014 you receive transmissions from the source code'),
        22: ('Physics', 'Master Builder \u2014 you architect realities others can only imagine'),
        33: ('Relational', 'Master Teacher \u2014 you hold space for collective awakening'),
    }
    return mapping.get(life_path_num, ('Unknown', 'Frequency unmapped'))


# ============================================================
# 5. INTERPRETATION CONTENT
# ============================================================

LIFE_PATH_MEANINGS = {
    1: "The Initiator. You came here to start things \u2014 not to follow blueprints, but to write them. Independence isn\u2019t your preference; it\u2019s your operating system.",
    2: "The Diplomat. You read rooms the way others read text. Your power isn\u2019t loud \u2014 it\u2019s the kind that holds everything together when the system would otherwise fragment.",
    3: "The Transmitter. You process reality through expression. Words, images, sound \u2014 these aren\u2019t hobbies, they\u2019re how you decode what\u2019s happening beneath the surface.",
    4: "The Architect. You build structures that outlast trends. Where others see chaos, you see load-bearing walls that need to be poured. Your patience is structural, not passive.",
    5: "The Liberator. You came here to break loops. Routine is your kryptonite because you\u2019re wired to explore every branch of the decision tree. Change isn\u2019t scary to you \u2014 stagnation is.",
    6: "The Calibrator. You sense when systems are out of balance and you can\u2019t not fix them. Home, community, justice \u2014 you hold the tuning fork for collective harmony.",
    7: "The Decoder. You\u2019re here to understand what\u2019s underneath. Not surface-level answers \u2014 you want the source code. Solitude isn\u2019t loneliness for you; it\u2019s the lab where breakthroughs happen.",
    8: "The Materializer. You translate abstract potential into concrete reality. Power, resources, influence \u2014 these flow toward you because you know how to build channels for them.",
    9: "The Integrator. You carry patterns from every other number. Your purpose isn\u2019t one thing \u2014 it\u2019s synthesis. You see the whole board while others see their square.",
    11: "Master Intuitive. You\u2019re a signal receiver operating on a frequency most people can\u2019t tune into. This is both your gift and your glitch \u2014 the volume is always high.",
    22: "Master Builder. You don\u2019t just dream \u2014 you architect realities that others can inhabit. Your vision operates on a scale that can feel isolating until you find your crew.",
    33: "Master Teacher. You hold space for collective transformation. Your presence alone shifts rooms. The weight of this is real \u2014 self-care isn\u2019t optional, it\u2019s structural.",
}

PERSONAL_YEAR_MEANINGS = {
    1: "New Cycle. Plant seeds. Start the thing you\u2019ve been circling.",
    2: "Patience. Partnerships. Let what you planted take root.",
    3: "Expression year. Create. Be visible. Share what\u2019s been brewing.",
    4: "Build year. Foundations. Systems. Do the unsexy work.",
    5: "Change year. Something shifts \u2014 let it. Don\u2019t grip the old timeline.",
    6: "Responsibility year. Home. Family. Recalibrate what \u2018balance\u2019 means.",
    7: "Inner work year. Go deep. Study. Rest. The answers are inside the code.",
    8: "Power year. Harvest. Manifest. Step into the version you\u2019ve been compiling.",
    9: "Completion year. Release. Grieve if needed. Clear the cache for what\u2019s next.",
    11: "Illumination year. Downloads are incoming. Trust what you can\u2019t yet prove.",
    22: "Master Build year. Large-scale creation is possible. Think bigger than feels comfortable.",
    33: "Service year. Your presence is the offering. Show up fully.",
}

SUN_SIGN_BRIEFS = {
    'Aries': 'Fire starter. Direct. Runs toward what others run from.',
    'Taurus': 'Rooted power. Builds what lasts. Senses everything.',
    'Gemini': 'Signal splitter. Processes reality through language and connection.',
    'Cancer': 'Emotional architect. Builds sanctuary wherever they stand.',
    'Leo': 'Radiant code. Creates gravity fields. Born to be witnessed.',
    'Virgo': 'Pattern analyst. Debugs reality at the micro level.',
    'Libra': 'Balance protocol. Weighs all inputs. Designs harmony.',
    'Scorpio': 'Deep diver. Accesses layers others refuse to acknowledge.',
    'Sagittarius': 'Explorer protocol. Maps uncharted territories of thought and terrain.',
    'Capricorn': 'Long-game architect. Builds empires on discipline and timing.',
    'Aquarius': 'System disruptor. Rewrites collective operating systems.',
    'Pisces': 'Receiver. Downloads from the collective unconscious like it\'s WiFi.',
}

MATURITY_NUMBER_MEANINGS = {
    1: "Pioneer maturity. You step into your own authority. Leadership emerges naturally.",
    2: "Diplomatic maturity. You become the keeper of peace. Collaboration flows.",
    3: "Creative maturity. You stop hedging your expression. Full visibility.",
    4: "Grounded maturity. You build legacy. Solidity becomes your superpower.",
    5: "Freedom maturity. You navigate change with grace. Adaptation is your gift.",
    6: "Compassionate maturity. You hold space for others. Healing is your presence.",
    7: "Wise maturity. You become the oracle. Depth is your greatest asset.",
    8: "Manifestor maturity. You command resources. Abundance flows toward you.",
    9: "Integrator maturity. You see the whole picture. Synthesis is your wisdom.",
    11: "Master intuition matures. Your downloads become articulate. You teach what you receive.",
    22: "Master architect matures. Your vision scales. You build for generations.",
    33: "Master teacher matures. Your presence transforms. You anchor the collective.",
}

HIDDEN_PASSION_MEANINGS = {
    1: "Drive to lead and initiate. Your deepest motivation is independence and pioneering.",
    2: "Need for connection. Your core drive is bringing harmony and bridging divides.",
    3: "Compulsion to create. Expression is your survival mechanism. You must speak your truth.",
    4: "Pull toward building. You are driven to create solid, lasting structures.",
    5: "Hunger for freedom. Change and variety aren't optional—they're your fuel.",
    6: "Call to serve. Caring for others and fixing systems is your deepest motivation.",
    7: "Thirst for truth. You are driven to understand the underlying code.",
    8: "Drive for power and manifestation. You are wired to create material reality.",
    9: "Desire for wholeness. Your deepest drive is toward synthesis and completion.",
}

KARMIC_LESSON_MEANINGS = {
    1: "Lesson: Develop independence. Stand alone. Trust your own vision.",
    2: "Lesson: Learn diplomacy. Understand that connection requires vulnerability.",
    3: "Lesson: Find your voice. Express what you think and feel.",
    4: "Lesson: Build stability. Create lasting foundations. Be reliable.",
    5: "Lesson: Embrace change. Let go of control. Freedom comes through flexibility.",
    6: "Lesson: Balance service with self-care. Healing others while staying whole.",
    7: "Lesson: Seek knowledge. Develop wisdom through introspection and study.",
    8: "Lesson: Master power. Use influence ethically. Manage resources wisely.",
    9: "Lesson: Surrender. Release what doesn't serve. Complete cycles.",
}

PINNACLE_MEANINGS = {
    1: "First pinnacle: Pioneer phase. Lay groundwork. Initiate change.",
    2: "First pinnacle: Partnership phase. Build alliances. Develop sensitivity.",
    3: "First pinnacle: Creative phase. Express yourself. Communicate.",
    4: "First pinnacle: Foundation phase. Build structures. Establish security.",
    5: "First pinnacle: Freedom phase. Explore options. Embrace change.",
    6: "First pinnacle: Harmony phase. Serve community. Balance relationships.",
    7: "First pinnacle: Seeker phase. Study deeply. Retreat inward.",
    8: "First pinnacle: Power phase. Build authority. Create material success.",
    9: "First pinnacle: Completion phase. Release old cycles. Prepare for transformation.",
}

CHALLENGE_MEANINGS = {
    0: "No significant challenge. You move through this phase with ease.",
    1: "Challenge: Dependence patterns. Learn independence.",
    2: "Challenge: Indecision. Develop confidence in your choices.",
    3: "Challenge: Scattered energy. Learn focus and discipline.",
    4: "Challenge: Rigidity. Allow flexibility and adaptation.",
    5: "Challenge: Instability. Ground yourself. Create structure.",
    6: "Challenge: Over-responsibility. Set boundaries. Protect your energy.",
    7: "Challenge: Isolation. Connect with others. Share your wisdom.",
    8: "Challenge: Power struggles. Master ethical use of authority.",
    9: "Challenge: Resistance to change. Surrender to transformation.",
}

PERSONAL_DAY_MEANINGS = {
    1: "Today: Take initiative. Plant a seed. Start something.",
    2: "Today: Cooperate and connect. Listen more than you speak.",
    3: "Today: Create and express. Share your thoughts.",
    4: "Today: Work on foundations. Handle logistics and details.",
    5: "Today: Explore and adapt. Stay flexible. Try something new.",
    6: "Today: Tend to relationships. Give care.",
    7: "Today: Reflect and study. Go inward.",
    8: "Today: Take action on material goals. Negotiate. Lead.",
    9: "Today: Release and complete. Close chapters.",
    11: "Today: Trust your intuition. Spiritual insights are coming.",
    22: "Today: Think big. Blueprint something large.",
    33: "Today: Serve others. Your presence heals.",
}


# ============================================================
# 6. HTML TEMPLATE
# ============================================================

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Soul Map — ${name} | The First Spark</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --black: #0B0B0C;
    --deep-space: #0a0a0f;
    --ember: #FF6A3D;
    --gold: #F3B23A;
    --violet: #6B4DF2;
    --cyan: #26E4D8;
    --white: #f0ece4;
    --dim: #888;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--deep-space);
    color: var(--white);
    font-family: 'Space Mono', monospace;
    font-size: 14px;
    line-height: 1.7;
    overflow-x: hidden;
  }
  .stars {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none; z-index: 0;
  }
  .star {
    position: absolute;
    border-radius: 50%;
    animation: twinkle var(--duration, 3s) ease-in-out infinite;
  }
  @keyframes twinkle {
    0%, 100% { opacity: var(--base-opacity, 0.3); }
    50% { opacity: var(--peak-opacity, 0.8); }
  }
  .container {
    position: relative; z-index: 1;
    max-width: 800px; margin: 0 auto; padding: 60px 24px;
  }
  h1 {
    font-family: 'Cormorant Garamond', serif;
    font-size: clamp(2.5rem, 6vw, 4rem);
    font-weight: 700;
    background: linear-gradient(135deg, var(--gold), var(--ember));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }
  h2 {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.6rem; font-weight: 600;
    color: var(--cyan);
    border-bottom: 1px solid rgba(38,228,216,0.2);
    padding-bottom: 8px; margin: 48px 0 20px;
  }
  h3 {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.2rem; color: var(--gold);
    margin: 24px 0 8px;
  }
  .subtitle {
    font-size: 0.85rem; color: var(--dim);
    letter-spacing: 3px; text-transform: uppercase;
  }
  .intro {
    margin: 32px 0; font-style: italic;
    color: var(--dim); font-family: 'Cormorant Garamond', serif;
    font-size: 1.1rem;
  }
  .numbers-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px; margin: 24px 0;
  }
  .number-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(107,77,242,0.2);
    border-radius: 8px; padding: 20px; text-align: center;
    transition: border-color 0.3s;
  }
  .number-card:hover { border-color: var(--cyan); }
  .number-card .label {
    font-size: 0.7rem; color: var(--dim);
    text-transform: uppercase; letter-spacing: 2px;
  }
  .number-card .value {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.8rem; font-weight: 700;
    color: var(--gold); margin: 4px 0;
  }
  .number-card .desc {
    font-size: 0.75rem; color: var(--cyan);
  }
  .selector-badge {
    display: inline-block;
    background: linear-gradient(135deg, var(--violet), var(--cyan));
    color: var(--black); font-weight: 700;
    padding: 6px 16px; border-radius: 20px;
    font-size: 0.8rem; letter-spacing: 1px;
    text-transform: uppercase;
  }
  .astro-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px; margin: 20px 0;
  }
  .astro-item {
    background: rgba(255,255,255,0.02);
    border-left: 3px solid var(--violet);
    padding: 12px 16px;
  }
  .astro-item .planet { color: var(--dim); font-size: 0.75rem; text-transform: uppercase; }
  .astro-item .sign { color: var(--white); font-size: 1rem; }
  .reading { color: var(--white); line-height: 1.8; margin: 12px 0; }
  .zodiac-badge {
    display: inline-flex; align-items: center; gap: 12px;
    background: rgba(243,178,58,0.08);
    border: 1px solid rgba(243,178,58,0.2);
    border-radius: 8px; padding: 16px 24px; margin: 16px 0;
  }
  .zodiac-badge .animal { font-size: 2rem; }
  .zodiac-badge .info { font-size: 0.9rem; }
  .zodiac-badge .element-tag {
    color: var(--ember); font-size: 0.75rem;
    text-transform: uppercase; letter-spacing: 2px;
  }
  .cycle-box {
    background: rgba(107,77,242,0.06);
    border: 1px solid rgba(107,77,242,0.15);
    border-radius: 8px; padding: 24px; margin: 20px 0;
  }
  .cycle-number {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3rem; font-weight: 700; color: var(--violet);
  }
  .footer {
    margin-top: 80px; padding-top: 24px;
    border-top: 1px solid rgba(255,255,255,0.05);
    text-align: center; font-size: 0.7rem; color: var(--dim);
  }
  .footer a { color: var(--cyan); text-decoration: none; }
  .footer a:hover { text-decoration: underline; }
  .generated-date { color: var(--dim); font-size: 0.75rem; margin-top: 4px; }
  .ceremony-banner {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(243, 178, 58, 0.15));
    border: 2px solid #6B4DF2;
    border-radius: 8px;
    padding: 32px 24px;
    margin: 24px 0;
    text-align: center;
    font-family: 'Cormorant Garamond', serif;
  }
  .ceremony-text {
    color: #F3B23A;
    font-size: 0.95rem;
    letter-spacing: 2px;
    line-height: 2;
  }
  .ceremony-subtitle {
    display: block;
    font-size: 1.8rem;
    font-weight: 700;
    color: #6B4DF2;
    margin: 16px 0;
  }
  .ceremony-date {
    display: block;
    font-size: 0.85rem;
    color: #26E4D8;
    margin-top: 16px;
    letter-spacing: 1px;
  }
</style>
</head>
<body>
<div id="starfield" class="stars"></div>
<div class="container">

  <p class="subtitle">Soul Map</p>
  <h1>${name}</h1>
  ${ceremony_banner}
  <p class="generated-date">Generated ${gen_date} · thefirstspark.shop</p>

  <p class="intro">
    This isn't a personality test. It's a coordinate system — a map of the patterns
    encoded in your existence. Numbers, planets, elements. Not metaphors. Syntax.
  </p>

  <!-- ===== CORE NUMBERS ===== -->
  <h2>Core Numbers</h2>
  <div class="numbers-grid">
    <div class="number-card">
      <div class="label">Life Path</div>
      <div class="value">${life_path}</div>
      <div class="desc">Your primary frequency</div>
    </div>
    <div class="number-card">
      <div class="label">Expression</div>
      <div class="value">${expression}</div>
      <div class="desc">How you transmit</div>
    </div>
    <div class="number-card">
      <div class="label">Soul Urge</div>
      <div class="value">${soul_urge}</div>
      <div class="desc">What drives you beneath</div>
    </div>
    <div class="number-card">
      <div class="label">Personality</div>
      <div class="value">${personality}</div>
      <div class="desc">What others receive</div>
    </div>
    <div class="number-card">
      <div class="label">Birthday</div>
      <div class="value">${birthday_num}</div>
      <div class="desc">Your gift frequency</div>
    </div>
    <div class="number-card">
      <div class="label">Maturity</div>
      <div class="value">${maturity_num}</div>
      <div class="desc">Your evolved self</div>
    </div>
  </div>

  <!-- ===== LIFE PATH READING ===== -->
  <h2>Life Path ${life_path} — The Signal</h2>
  <p class="reading">${life_path_reading}</p>

  <!-- ===== HIDDEN PASSION ===== -->
  <h2>Hidden Passion — Your Deepest Drive</h2>
  <div style="text-align: center; margin: 24px 0;">
    <div style="font-family: 'Cormorant Garamond', serif; font-size: 4rem; font-weight: 700; color: #26E4D8; margin-bottom: 12px;">${hidden_passion_num}</div>
    <p class="reading">${hidden_passion_reading}</p>
  </div>

  <!-- ===== KARMIC LESSONS ===== -->
  <h2>Karmic Lessons — What You Came To Learn</h2>
  <div style="margin: 20px 0; padding: 16px; background: rgba(107,77,242,0.1); border-left: 4px solid #6B4DF2; border-radius: 4px;">
    <p class="reading">${karmic_lessons_html}</p>
  </div>

  <!-- ===== LIFE PHASES ===== -->
  <h2>Four Life Phases</h2>

  <h3>Pinnacles — Major Life Themes</h3>
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 16px 0;">
    <div style="padding: 16px; background: rgba(38,228,216,0.08); border: 1px solid rgba(38,228,216,0.2); border-radius: 6px;">
      <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; color: #26E4D8; font-weight: 700; margin-bottom: 4px;">${pinnacle_1}</div>
      <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Pinnacle 1</div>
      <p style="font-size: 0.85rem; color: #f0ece4;">${pinnacle_1_reading}</p>
    </div>
    <div style="padding: 16px; background: rgba(38,228,216,0.08); border: 1px solid rgba(38,228,216,0.2); border-radius: 6px;">
      <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; color: #26E4D8; font-weight: 700; margin-bottom: 4px;">${pinnacle_2}</div>
      <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Pinnacle 2</div>
      <p style="font-size: 0.85rem; color: #f0ece4;">${pinnacle_2_reading}</p>
    </div>
    <div style="padding: 16px; background: rgba(38,228,216,0.08); border: 1px solid rgba(38,228,216,0.2); border-radius: 6px;">
      <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; color: #26E4D8; font-weight: 700; margin-bottom: 4px;">${pinnacle_3}</div>
      <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Pinnacle 3</div>
      <p style="font-size: 0.85rem; color: #f0ece4;">${pinnacle_3_reading}</p>
    </div>
    <div style="padding: 16px; background: rgba(38,228,216,0.08); border: 1px solid rgba(38,228,216,0.2); border-radius: 6px;">
      <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; color: #26E4D8; font-weight: 700; margin-bottom: 4px;">${pinnacle_4}</div>
      <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Pinnacle 4</div>
      <p style="font-size: 0.85rem; color: #f0ece4;">${pinnacle_4_reading}</p>
    </div>
  </div>

  <h3 style="margin-top: 32px;">Challenges — What You're Here To Master</h3>
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 16px 0;">
    <div style="padding: 16px; background: rgba(255,106,61,0.08); border: 1px solid rgba(255,106,61,0.2); border-radius: 6px;">
      <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; color: #FF6A3D; font-weight: 700; margin-bottom: 4px;">${challenge_1}</div>
      <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Challenge 1</div>
      <p style="font-size: 0.85rem; color: #f0ece4;">${challenge_1_reading}</p>
    </div>
    <div style="padding: 16px; background: rgba(255,106,61,0.08); border: 1px solid rgba(255,106,61,0.2); border-radius: 6px;">
      <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; color: #FF6A3D; font-weight: 700; margin-bottom: 4px;">${challenge_2}</div>
      <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Challenge 2</div>
      <p style="font-size: 0.85rem; color: #f0ece4;">${challenge_2_reading}</p>
    </div>
    <div style="padding: 16px; background: rgba(255,106,61,0.08); border: 1px solid rgba(255,106,61,0.2); border-radius: 6px;">
      <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; color: #FF6A3D; font-weight: 700; margin-bottom: 4px;">${challenge_3}</div>
      <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Challenge 3</div>
      <p style="font-size: 0.85rem; color: #f0ece4;">${challenge_3_reading}</p>
    </div>
    <div style="padding: 16px; background: rgba(255,106,61,0.08); border: 1px solid rgba(255,106,61,0.2); border-radius: 6px;">
      <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; color: #FF6A3D; font-weight: 700; margin-bottom: 4px;">${challenge_4}</div>
      <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Challenge 4</div>
      <p style="font-size: 0.85rem; color: #f0ece4;">${challenge_4_reading}</p>
    </div>
  </div>

  <!-- ===== SOUL SYNTHESIS ===== -->
  <h2>Soul Synthesis</h2>
  <div style="margin: 24px 0; padding: 24px; background: rgba(107,77,242,0.05); border: 1px solid rgba(107,77,242,0.15); border-radius: 8px;">
    <p class="reading">${soul_synthesis_text}</p>
  </div>

  <!-- ===== DEBUGGING NOTES ===== -->
  <h2>Debugging Notes — Watch For These Loops</h2>
  <div style="margin: 24px 0; padding: 24px; background: rgba(243,178,58,0.05); border: 1px solid rgba(243,178,58,0.15); border-radius: 8px;">
    <div class="reading" style="font-size: 0.95rem;">${debugging_notes_html}</div>
  </div>

  <!-- ===== YEARLY CYCLES ===== -->
  <h2>12-Month Cycles</h2>
  <div style="margin: 20px 0; overflow-x: auto;">
    <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
      <thead>
        <tr style="border-bottom: 2px solid #26E4D8;">
          <th style="padding: 12px; text-align: left; color: #26E4D8; font-weight: 600;">Month</th>
          <th style="padding: 12px; text-align: center; color: #26E4D8; font-weight: 600;">Number</th>
          <th style="padding: 12px; text-align: left; color: #26E4D8; font-weight: 600;">Meaning</th>
        </tr>
      </thead>
      <tbody>
        ${yearly_months_html}
      </tbody>
    </table>
  </div>

  <!-- ===== WESTERN ASTROLOGY ===== -->
  <h2>Celestial Coordinates</h2>
  <div class="astro-grid">
    <div class="astro-item">
      <div class="planet">☉ Sun</div>
      <div class="sign">${sun_sign} ${sun_symbol}</div>
    </div>
    ${astro_extra}
  </div>
  <h3>Sun in ${sun_sign}</h3>
  <p class="reading">${sun_reading}</p>

  <!-- ===== CHINESE ZODIAC ===== -->
  <h2>Eastern Coordinates</h2>
  <div class="zodiac-badge">
    <div class="animal">${chinese_emoji}</div>
    <div>
      <div class="info">${chinese_element} ${chinese_animal}</div>
      <div class="element-tag">${chinese_element} element · ${birth_year}</div>
    </div>
  </div>

  <!-- ===== CURRENT CYCLE ===== -->
  <h2>Current Cycle</h2>
  <div class="cycle-box">
    <div class="cycle-number">${personal_yr}</div>
    <h3>Personal Year ${personal_yr}</h3>
    <p class="reading">${personal_yr_reading}</p>
    <h3 style="margin-top: 20px;">Personal Month: ${personal_mo}</h3>
    <p style="margin-top: 20px; text-align: center;">
      <a href="${monthly_update_link}" style="color: #26E4D8; text-decoration: none; font-family: 'Space Mono', monospace; font-size: 0.9rem;">→ View This Month's Energy Update</a>
    </p>
  </div>

  <!-- ===== FOOTER ===== -->
  <div class="footer">
    <p>THE FIRST SPARK — Reality is programmable. Consciousness is the code.</p>
    <p style="margin-top: 8px;">
      <a href="https://thefirstspark.shop">thefirstspark.shop</a> ·
      <a href="https://whop.com/joined/sparkverse-511c/">Join the Sparkverse</a>
    </p>
  </div>

</div>

<script>
// Seeded random number generator
function seededRandom(seed) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

// Sun sign color palette (element-based)
const SUN_SIGN_COLORS = {
  'Aries': ['#f97316', '#ea580c', '#dc2626'],
  'Taurus': ['#84cc16', '#65a30d', '#4d7c0f'],
  'Gemini': ['#8b5cf6', '#7c3aed', '#a855f7'],
  'Cancer': ['#22d3ee', '#06b6d4', '#0891b7'],
  'Leo': ['#f97316', '#ea580c', '#fbbf24'],
  'Virgo': ['#84cc16', '#65a30d', '#4d7c0f'],
  'Libra': ['#8b5cf6', '#7c3aed', '#a855f7'],
  'Scorpio': ['#22d3ee', '#0f172a', '#1e293b'],
  'Sagittarius': ['#f97316', '#ea580c', '#fbbf24'],
  'Capricorn': ['#6b7280', '#4b5563', '#1f2937'],
  'Aquarius': ['#8b5cf6', '#7c3aed', '#a855f7'],
  'Pisces': ['#22d3ee', '#06b6d4', '#0891b7']
};

// Extract data from page
const lifePathStr = document.querySelector('h2')?.textContent || '';
const lifePathMatch = lifePathStr.match(/Life Path (\d+)/);
const lifePathNum = lifePathMatch ? parseInt(lifePathMatch[1]) : 1;

// Default sun sign (Libra for Matthew, can be extracted from page)
const sunSignMatch = document.body.textContent.match(/Sun in\s+(\w+)/);
const sunSign = sunSignMatch ? sunSignMatch[1] : 'Libra';

// For now, use hardcoded values that will be replaced by template substitution
const soulUrgeNum = ${soul_urge};
const expressionNum = ${expression};

// Create seeded starfield
function createPersonalStarfield() {
  const starfield = document.getElementById('starfield');
  const seed = lifePathNum * 1000 + soulUrgeNum * 100 + expressionNum * 10;
  const colors = SUN_SIGN_COLORS[sunSign] || SUN_SIGN_COLORS['Pisces'];

  for (let i = 0; i < 150; i++) {
    const star = document.createElement('div');
    star.className = 'star';
    star.style.left = (seededRandom(seed + i * 2) * 100) + '%';
    star.style.top = (seededRandom(seed + i * 2 + 1) * 100) + '%';
    const size = seededRandom(seed + i * 3) * 2 + 0.5;
    star.style.width = size + 'px';
    star.style.height = size + 'px';
    star.style.backgroundColor = colors[i % colors.length];
    const duration = seededRandom(seed + i * 4) * 3 + 2;
    star.style.setProperty('--duration', duration + 's');
    star.style.setProperty('--base-opacity', (seededRandom(seed + i * 5) * 0.5 + 0.2).toFixed(2));
    star.style.setProperty('--peak-opacity', (seededRandom(seed + i * 6) * 0.5 + 0.6).toFixed(2));
    starfield.appendChild(star);
  }
}

// Create starfield on load
document.addEventListener('DOMContentLoaded', createPersonalStarfield);
</script>
</body>
</html>
"""


# ============================================================
# 7. GENERATOR
# ============================================================

CHINESE_EMOJIS = {
    'Rat': '\U0001f400', 'Ox': '\U0001f402', 'Tiger': '\U0001f405', 'Rabbit': '\U0001f407',
    'Dragon': '\U0001f409', 'Snake': '\U0001f40d', 'Horse': '\U0001f434', 'Goat': '\U0001f410',
    'Monkey': '\U0001f412', 'Rooster': '\U0001f413', 'Dog': '\U0001f415', 'Pig': '\U0001f437'
}


# ============================================================
# PERSONALIZED NARRATIVES (Hand-written per person)
# ============================================================

NARRATIVES = {
    'Matthew Vincent Jablonski': {
        'soul_synthesis': """
You carry <span class="highlight">four 9s</span> — a pattern so rare it marks you as a completion architect. Life Path 6 (protector), Expression 9 (integrator), Soul Urge 9 (hunger for wholeness), Personality 9 (appears as synthesizer), Birthday 9 (gift frequency). This is not scattered energy; this is <span class="code-term">depth coding for collective healing</span>.

Your Life Path 6 reads you as the calibrator—you sense when systems are out of balance and can't not fix them. But the four 9s transform this: you're not fixing systems for comfort. You're here to complete cycles, integrate fragmented consciousness, and transmit wholeness back to the collective. Libra Rising would add: you weigh everything against harmony. Wood Dog adds: loyal idealism grounded in earth.

By Personal Year 11 (2026), you're receiving a massive spiritual download. This is not metaphor—11 is the master intuitive frequency. You're tuning into transmissions most people can't hear. The work ahead isn't passive receiving. You're building something transformative with this signal. The question isn't whether you'll feel the call. It's whether you'll answer it in form.

Numerologically, your Maturity Number (6) softens into compassion. Your Karmic Lesson (7—the decoder) pulls you inward: you must understand the underlying code before you can transmit it. Your Pinnacles show pioneer energy (P1), freedom (P2), and sustained harmony (P3 & P4). Your challenges are power management (C1: 8) and flexibility (C2-C4: 4). Translation: you'll learn to hold authority without rigidity, to lead without controlling.

You are coded for <span class="code-term">alchemical work in the collective</span>. Not metaphorically. In form.
        """,
        'debugging_notes': """
<ul style="margin: 0; padding-left: 20px;">
  <li><strong>Over-responsibility trap:</strong> Life Path 6 + four 9s can create a savior complex. You're not responsible for fixing everyone. Ground the mysticism.</li>
  <li><strong>Spiritual imbalance:</strong> Four 9s can exhaust you trying to hold universal frequencies. You're allowed to have personal needs. Integration includes self-care.</li>
  <li><strong>Premature grandiosity:</strong> Year 11 downloads can feel overwhelming. Trust the slow transmission. Your job is to embody, not to prove anything to anyone.</li>
  <li><strong>Avoidance of present chaos:</strong> Libra can over-weigh options. Karmic Lesson 7 asks you to decode, not to escape into analysis. The mess is the material. Build in it.</li>
</ul>
        """
    }
}


def generate_soul_map(full_name, birth_date, birth_time=None, birth_city=None, birth_country='US'):
    """Generate complete Soul Map data and return rendered HTML."""

    # === Numerology (Core Numbers) ===
    lp = life_path(birth_date)
    expr = expression_number(full_name)
    su = soul_urge_number(full_name)
    pers = personality_number(full_name)
    bday = birthday_number(birth_date)
    py = personal_year(birth_date)
    pm = personal_month(birth_date)

    # === Numerology (Extended) ===
    mat = maturity_number(full_name, birth_date)
    hp = hidden_passion(full_name)
    kl = karmic_lessons(full_name)
    kd = karmic_debt(lp, expr, su, pers, bday)
    pinn = pinnacles(birth_date)
    chall = challenges(birth_date)
    pd = personal_day(birth_date)

    # === Selector Model ===
    sel_layer, sel_desc = selector_layer(lp)

    # === Sun Sign ===
    ss_name, ss_symbol = sun_sign(birth_date)

    # === Monthly Update Link ===
    today = date.today()
    base_filename = get_base_filename(full_name, birth_date)
    monthly_update_filename = f"{base_filename}-{today.year}{today.month:02d}.html"

    # === Full Chart (if birth time provided) ===
    astro_extra_html = ''
    if birth_time and birth_city:
        hour, minute = birth_time
        chart = get_full_chart(full_name, birth_date.year, birth_date.month,
                               birth_date.day, hour, minute, birth_city, birth_country)
        if chart:
            planets = [
                ('\u263d Moon', chart['moon_sign']),
                ('\u2191 Rising', chart['rising_sign']),
                ('\u263f Mercury', chart['mercury']),
                ('\u2640 Venus', chart['venus']),
                ('\u2642 Mars', chart['mars']),
                ('\u2643 Jupiter', chart['jupiter']),
                ('\u2644 Saturn', chart['saturn']),
            ]
            astro_extra_html = '\n'.join(
                f'    <div class="astro-item"><div class="planet">{p}</div><div class="sign">{s}</div></div>'
                for p, s in planets
            )

    # === Chinese Zodiac ===
    c_animal, c_element = chinese_zodiac(birth_date.year)

    # === Build HTML for new sections ===
    # Karmic Lessons HTML
    kl_html = ', '.join([KARMIC_LESSON_MEANINGS.get(i, f'Lesson {i}') for i in kl]) if kl else 'No karmic lessons—your name contains all digits 1-9.'

    # Hidden Passion reading
    hp_reading = HIDDEN_PASSION_MEANINGS.get(hp, f'Hidden passion: {hp}')

    # Pinnacle readings
    pinnacle_readings = {
        i: PINNACLE_MEANINGS.get(i, f'Pinnacle {i}')
        for i in range(1, 10)
    }

    # Challenge readings
    challenge_readings = {
        i: CHALLENGE_MEANINGS.get(i, f'Challenge {i}')
        for i in range(0, 10)
    }

    # 12-month cycles for the current year
    import calendar
    today = date.today()
    current_year = today.year
    py_current = personal_year(birth_date, current_year)

    yearly_months_rows = []
    for month_num in range(1, 13):
        pm_month = personal_month(birth_date, current_year, month_num)
        month_name = calendar.month_name[month_num]
        meaning = PERSONAL_YEAR_MEANINGS.get(pm_month, f'Month {pm_month}')
        yearly_months_rows.append(
            f'<tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">'
            f'<td style="padding: 10px 12px;">{month_name}</td>'
            f'<td style="padding: 10px 12px; text-align: center; color: #26E4D8; font-weight: 600;">{pm_month}</td>'
            f'<td style="padding: 10px 12px;">{meaning}</td>'
            f'</tr>'
        )
    yearly_months_html = '\n        '.join(yearly_months_rows)

    # Placeholders for Soul Synthesis and Debugging Notes (hand-written per person)
    if full_name in NARRATIVES:
        soul_synthesis_text = NARRATIVES[full_name]['soul_synthesis']
        debugging_notes_html = NARRATIVES[full_name]['debugging_notes']
    else:
        soul_synthesis_text = '[Soul Synthesis — To be personalized]'
        debugging_notes_html = '[Debugging Notes — To be personalized]'

    # Ceremony banner (special for first member)
    if full_name == 'Matthew Vincent Jablonski':
        ceremony_banner = f"""<div class="ceremony-banner">
    <div class="ceremony-text">
      ◆ THE FIRST SPARK ◆
      <span class="ceremony-subtitle">Matthew Vincent Jablonski</span>
      Founding Consciousness · First Member
      <span class="ceremony-date">Initiated April 23, 2026</span>
    </div>
  </div>"""
    else:
        ceremony_banner = ''

    # === Build HTML ===
    template = Template(HTML_TEMPLATE)
    html = template.safe_substitute(
        name=full_name,
        ceremony_banner=ceremony_banner,
        gen_date=datetime.now().strftime('%B %d, %Y'),
        life_path=lp,
        expression=expr,
        soul_urge=su,
        personality=pers,
        birthday_num=bday,
        maturity_num=mat,
        hidden_passion_num=hp,
        hidden_passion_reading=hp_reading,
        karmic_lessons_html=kl_html,
        pinnacle_1=pinn['pinnacle_1'],
        pinnacle_1_reading=pinnacle_readings.get(pinn['pinnacle_1'], 'Pinnacle unmapped'),
        pinnacle_2=pinn['pinnacle_2'],
        pinnacle_2_reading=pinnacle_readings.get(pinn['pinnacle_2'], 'Pinnacle unmapped'),
        pinnacle_3=pinn['pinnacle_3'],
        pinnacle_3_reading=pinnacle_readings.get(pinn['pinnacle_3'], 'Pinnacle unmapped'),
        pinnacle_4=pinn['pinnacle_4'],
        pinnacle_4_reading=pinnacle_readings.get(pinn['pinnacle_4'], 'Pinnacle unmapped'),
        challenge_1=chall['challenge_1'],
        challenge_1_reading=challenge_readings.get(chall['challenge_1'], 'Challenge unmapped'),
        challenge_2=chall['challenge_2'],
        challenge_2_reading=challenge_readings.get(chall['challenge_2'], 'Challenge unmapped'),
        challenge_3=chall['challenge_3'],
        challenge_3_reading=challenge_readings.get(chall['challenge_3'], 'Challenge unmapped'),
        challenge_4=chall['challenge_4'],
        challenge_4_reading=challenge_readings.get(chall['challenge_4'], 'Challenge unmapped'),
        soul_synthesis_text=soul_synthesis_text,
        debugging_notes_html=debugging_notes_html,
        yearly_months_html=yearly_months_html,
        life_path_reading=LIFE_PATH_MEANINGS.get(lp, 'Frequency unmapped.'),
        selector_layer=sel_layer,
        selector_desc=sel_desc,
        sun_sign=ss_name,
        sun_symbol=ss_symbol,
        sun_reading=SUN_SIGN_BRIEFS.get(ss_name, ''),
        astro_extra=astro_extra_html if astro_extra_html else '<div class="astro-item"><div class="planet">\u263d Moon / \u2191 Rising</div><div class="sign">Birth time needed for full chart</div></div>',
        chinese_animal=c_animal,
        chinese_element=c_element,
        chinese_emoji=CHINESE_EMOJIS.get(c_animal, '\u2728'),
        birth_year=birth_date.year,
        personal_yr=py,
        personal_yr_reading=PERSONAL_YEAR_MEANINGS.get(py, 'Cycle unmapped.'),
        personal_mo=pm,
        monthly_update_link=monthly_update_filename,
    )

    return html, {
        'name': full_name,
        'life_path': lp,
        'expression': expr,
        'soul_urge': su,
        'personality': pers,
        'birthday': bday,
        'maturity_number': mat,
        'hidden_passion': hp,
        'karmic_lessons': kl,
        'karmic_debt': kd,
        'pinnacles': pinn,
        'challenges': chall,
        'personal_year': py,
        'personal_month': pm,
        'personal_day': pd,
        'sun_sign': ss_name,
        'chinese': f"{c_element} {c_animal}",
        'selector_layer': sel_layer,
    }


# ============================================================
# 8. MONTHLY UPDATE GENERATOR
# ============================================================

def initials_from_name(full_name):
    """Extract initials from full name."""
    return ''.join(word[0].upper() for word in full_name.split() if word)


def get_base_filename(full_name, birth_date):
    """Generate base filename: {INITIALS}{BIRTH_MONTH}{BIRTH_YEAR}.
    E.g. Aaron Joseph Thomas born 9/24/1988 → AJT91988
    """
    initials = initials_from_name(full_name)
    month = birth_date.month
    year = birth_date.year
    return f"{initials}{month}{year}"


def generate_monthly_update(full_name, birth_date, current_year=None, current_month=None):
    """Generate a monthly update page for a soul map.

    Returns (html, filename, data_dict)
    """
    if current_year is None:
        current_year = date.today().year
    if current_month is None:
        current_month = date.today().month

    # Numerology for this month
    pm = personal_month(birth_date, current_year, current_month)

    # Next month
    next_month = current_month + 1
    next_year = current_year
    if next_month > 12:
        next_month = 1
        next_year += 1
    pm_next = personal_month(birth_date, next_year, next_month)

    # Month names
    import calendar
    month_name = calendar.month_name[current_month]
    next_month_name = calendar.month_name[next_month]

    # Base filename for linking
    base_filename = get_base_filename(full_name, birth_date)

    # Personal Year context
    py = personal_year(birth_date, current_year)

    monthly_template = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Monthly Update — ${name} | The First Spark</title>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --void: #0a0a0f;
    --deep-space: #0d0d14;
    --sacred-gold: #d4af37;
    --glitch-cyan: #22d3ee;
    --mystic-purple: #8b5cf6;
    --white: #e8e6e3;
    --muted: #6b7280;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--deep-space);
    color: var(--white);
    font-family: 'Cormorant Garamond', serif;
    line-height: 1.7;
    min-height: 100vh;
    overflow-x: hidden;
  }
  .starfield {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
    z-index: 0;
  }
  .star {
    position: absolute;
    background: white;
    border-radius: 50%;
    animation: twinkle var(--duration) ease-in-out infinite;
  }
  @keyframes twinkle {
    0%, 100% { opacity: var(--base-opacity); }
    50% { opacity: var(--peak-opacity); }
  }
  .container {
    position: relative;
    z-index: 1;
    max-width: 900px;
    margin: 0 auto;
    padding: 60px 30px;
  }
  .header {
    text-align: center;
    margin-bottom: 60px;
    padding-bottom: 40px;
    border-bottom: 1px solid rgba(212, 175, 55, 0.3);
  }
  .brand {
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    color: var(--glitch-cyan);
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-bottom: 20px;
  }
  .subtitle {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: var(--muted);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 10px;
  }
  .title {
    font-family: 'Cinzel', serif;
    font-size: 2.5rem;
    font-weight: 600;
    color: var(--sacred-gold);
    margin-bottom: 8px;
    text-shadow: 0 0 40px rgba(212, 175, 55, 0.3);
  }
  .month-period {
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    color: var(--glitch-cyan);
    margin-top: 15px;
  }
  .section {
    margin-bottom: 50px;
    padding: 35px;
    background: linear-gradient(135deg, rgba(13, 13, 20, 0.9), rgba(10, 10, 15, 0.95));
    border: 1px solid rgba(212, 175, 55, 0.15);
    position: relative;
  }
  .section::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    background: linear-gradient(to bottom, var(--sacred-gold), transparent);
  }
  .section-title {
    font-family: 'Cinzel', serif;
    font-size: 1.5rem;
    color: var(--sacred-gold);
    margin-bottom: 20px;
  }
  .current-month-box {
    background: rgba(34, 211, 238, 0.05);
    border: 1px solid rgba(34, 211, 238, 0.3);
    padding: 40px;
    text-align: center;
    margin-bottom: 30px;
  }
  .month-number {
    font-family: 'Cinzel', serif;
    font-size: 5rem;
    font-weight: 700;
    color: var(--glitch-cyan);
    text-shadow: 0 0 40px rgba(34, 211, 238, 0.6);
    line-height: 1;
  }
  .month-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    color: var(--glitch-cyan);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 12px;
  }
  .meaning-text {
    font-size: 1.1rem;
    line-height: 1.8;
    margin-top: 25px;
    color: var(--white);
  }
  .highlight { color: var(--sacred-gold); font-weight: 600; }
  .next-month-preview {
    background: rgba(139, 92, 246, 0.05);
    border: 1px solid rgba(139, 92, 246, 0.3);
    padding: 30px;
    margin-top: 30px;
  }
  .preview-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: var(--mystic-purple);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 15px;
  }
  .preview-number {
    font-family: 'Cinzel', serif;
    font-size: 2.5rem;
    color: var(--mystic-purple);
    margin-bottom: 8px;
  }
  .preview-meaning {
    font-size: 1rem;
    color: var(--white);
    font-style: italic;
  }
  .year-context {
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid rgba(212, 175, 55, 0.1);
  }
  .back-link {
    display: inline-block;
    margin-top: 20px;
    color: var(--glitch-cyan);
    text-decoration: none;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
  }
  .back-link:hover { text-shadow: 0 0 10px var(--glitch-cyan); }
  .footer {
    text-align: center;
    margin-top: 60px;
    padding-top: 40px;
    border-top: 1px solid rgba(212, 175, 55, 0.2);
  }
  .footer-brand {
    font-family: 'Cinzel', serif;
    font-size: 1.2rem;
    color: var(--sacred-gold);
  }
  .footer-tagline {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: var(--muted);
    letter-spacing: 2px;
    margin-top: 10px;
  }
</style>
</head>
<body>
<div class="starfield" id="starfield"></div>

<div class="container">
  <header class="header">
    <div class="brand">◈ Monthly Update ◈</div>
    <div class="subtitle">${name}</div>
    <h1 class="title">${month_name} ${year}</h1>
    <div class="month-period">Personal Year ${py} · ${month_name} ${year}</div>
  </header>

  <section class="section">
    <h2 class="section-title">This Month's Frequency</h2>

    <div class="current-month-box">
      <div class="month-number">${current_month}</div>
      <div class="month-label">Personal Month</div>
      <div class="meaning-text">
        <strong>${current_month_meaning_title}</strong><br>
        ${current_month_meaning}
      </div>
    </div>

    <div class="next-month-preview">
      <div class="preview-label">Preview: Next Month</div>
      <div class="preview-number">${next_month}</div>
      <div class="preview-meaning">${next_month_name} brings <strong>${next_month_meaning_title}</strong>. ${next_month_meaning}</div>
    </div>

    <div class="year-context">
      Within your Personal Year ${py}, this month's energy is: <span class="highlight">${current_month} + ${py} context = ${pm}</span>
    </div>

    <a href="${map_slug}.html" class="back-link">← Return to Full Soul Map</a>
  </section>

  <footer class="footer">
    <div class="footer-brand">The First Spark</div>
    <div class="footer-tagline">Reality is programmable. Consciousness is the code.</div>
  </footer>
</div>

<script>
  const starfield = document.getElementById('starfield');
  for (let i = 0; i < 150; i++) {
    const star = document.createElement('div');
    star.className = 'star';
    star.style.left = Math.random() * 100 + '%';
    star.style.top = Math.random() * 100 + '%';
    const size = Math.random() * 2 + 0.5;
    star.style.width = size + 'px';
    star.style.height = size + 'px';
    star.style.setProperty('--duration', (Math.random() * 3 + 2) + 's');
    star.style.setProperty('--base-opacity', Math.random() * 0.3 + 0.1);
    star.style.setProperty('--peak-opacity', Math.random() * 0.5 + 0.5);
    starfield.appendChild(star);
  }
</script>
</body>
</html>
"""

    template = Template(monthly_template)
    html = template.safe_substitute(
        name=full_name,
        month_name=month_name,
        year=current_year,
        py=py,
        current_month=pm,
        current_month_meaning_title=PERSONAL_YEAR_MEANINGS.get(pm, 'Cycle').split('.')[0],
        current_month_meaning=PERSONAL_YEAR_MEANINGS.get(pm, 'Frequency unmapped.'),
        next_month=pm_next,
        next_month_name=next_month_name,
        next_month_meaning_title=PERSONAL_YEAR_MEANINGS.get(pm_next, 'Cycle').split('.')[0],
        next_month_meaning=PERSONAL_YEAR_MEANINGS.get(pm_next, 'Frequency unmapped.'),
        map_slug=base_filename,
    )

    # Filename: {INITIALS}{BIRTHMONTH}{BIRTHYEAR}-{YYYYMM}.html
    filename = f"{base_filename}-{current_year}{current_month:02d}.html"

    return html, filename, {
        'name': full_name,
        'personal_month': pm,
        'personal_year': py,
        'month': current_month,
        'year': current_year,
    }


# ============================================================
# 9. BATCH GENERATOR
# ============================================================

def load_batch_csv(filepath):
    """Load batch generation data from CSV.

    Expected columns: Name, Date (YYYY-MM-DD), Time (HH:MM, optional), City (optional), Country (optional)
    Returns list of dicts: [{'name': ..., 'date': ..., 'time': ..., 'city': ..., 'country': ...}, ...]
    """
    records = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row.get('Name', '').strip():
                    continue

                records.append({
                    'name': row.get('Name', '').strip(),
                    'date': row.get('Date', '').strip(),
                    'time': row.get('Time', '').strip() or None,
                    'city': row.get('City', '').strip() or None,
                    'country': row.get('Country', 'US').strip() or 'US',
                })
    except Exception as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        return []

    return records


def generate_batch(csv_filepath, mode='both', no_deploy=False, output_dir=None):
    """Generate soul maps for multiple people from CSV.

    Args:
        csv_filepath: Path to CSV file
        mode: 'soul-map', 'monthly', or 'both'
        no_deploy: Skip GitHub deployment
        output_dir: Optional output directory (default: current)

    Returns: (success_count, total_count, results_list)
    """
    records = load_batch_csv(csv_filepath)
    if not records:
        print("No valid records found in CSV.", file=sys.stderr)
        return 0, 0, []

    results = []
    success_count = 0

    print(f"\n⚡ BATCH SOUL MAP GENERATOR — The First Spark")
    print(f"{'='*60}")
    print(f"  Mode:     {mode}")
    print(f"  Records:  {len(records)}")
    print(f"  Deploy:   {'Yes' if not no_deploy else 'No (local only)'}")
    print(f"{'='*60}\n")

    for i, record in enumerate(records, 1):
        name = record['name']
        try:
            birth_date = datetime.strptime(record['date'], '%Y-%m-%d').date()
        except ValueError:
            print(f"  [{i}/{len(records)}] ✗ {name:30s} — Invalid date format")
            results.append({'name': name, 'success': False, 'reason': 'Invalid date'})
            continue

        # Parse optional time
        birth_time = None
        if record['time']:
            try:
                t = datetime.strptime(record['time'], '%H:%M')
                birth_time = (t.hour, t.minute)
            except ValueError:
                print(f"  [{i}/{len(records)}] ⚠ {name:30s} — Invalid time, skipping")

        # Determine output directory
        out_dir = Path(output_dir) if output_dir else Path('.')
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Generate soul map if requested
            if mode in ('soul-map', 'both'):
                html_map, summary_map = generate_soul_map(
                    name, birth_date,
                    birth_time=birth_time,
                    birth_city=record['city'],
                    birth_country=record['country']
                )

                slug = name.lower().replace(' ', '-')
                map_filename = f"soul-map-{slug}.html"
                map_path = out_dir / map_filename
                map_path.write_text(html_map, encoding='utf-8')

                if not no_deploy:
                    success, result = deploy_to_github(html_map, map_filename)
                    if not success:
                        print(f"  [{i}/{len(records)}] ⚠ {name:30s} — Soul map generated but deploy failed")
                        results.append({'name': name, 'success': False, 'reason': 'Deploy failed'})
                        continue

            # Generate monthly update if requested
            if mode in ('monthly', 'both'):
                html_monthly, filename_monthly, summary_monthly = generate_monthly_update(name, birth_date)
                monthly_path = out_dir / filename_monthly
                monthly_path.write_text(html_monthly, encoding='utf-8')

                if not no_deploy:
                    success, result = deploy_to_github(html_monthly, filename_monthly)
                    if not success:
                        print(f"  [{i}/{len(records)}] ⚠ {name:30s} — Monthly update generated but deploy failed")
                        results.append({'name': name, 'success': False, 'reason': 'Deploy failed'})
                        continue

            print(f"  [{i}/{len(records)}] ✓ {name:30s} — {record['date']}")
            results.append({'name': name, 'success': True})
            success_count += 1

        except Exception as e:
            print(f"  [{i}/{len(records)}] ✗ {name:30s} — {str(e)}")
            results.append({'name': name, 'success': False, 'reason': str(e)})

    # Summary
    print(f"\n{'='*60}")
    print(f"  Completed: {success_count}/{len(records)} ✓")
    print(f"{'='*60}\n")

    return success_count, len(records), results


# ============================================================
# 10. GITHUB AUTO-DEPLOY
# ============================================================

def deploy_to_github(html_content, filename, repo='soul-maps'):
    """Push generated Soul Map HTML to GitHub Pages repo."""
    token = os.environ.get('GITHUB_PAT')
    if not token:
        return False, "GITHUB_PAT environment variable not set. Export it first: set GITHUB_PAT=ghp_yourtoken"

    repo_url = f"https://thefirstspark:{token}@github.com/thefirstspark/{repo}.git"
    work_dir = Path(os.path.expanduser('~')) / '.soul-map-deploy' / repo

    try:
        # Clone or pull
        if work_dir.exists():
            subprocess.run(['git', '-C', str(work_dir), 'pull'], check=True, capture_output=True)
        else:
            work_dir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['git', 'clone', repo_url, str(work_dir)], check=True, capture_output=True)

        # Write file
        filepath = work_dir / filename
        filepath.write_text(html_content, encoding='utf-8')

        # Git config + commit + push
        subprocess.run(['git', '-C', str(work_dir), 'config', 'user.email', 'kate@thefirstspark.shop'], check=True)
        subprocess.run(['git', '-C', str(work_dir), 'config', 'user.name', 'The First Spark'], check=True)
        subprocess.run(['git', '-C', str(work_dir), 'add', filename], check=True)
        subprocess.run(['git', '-C', str(work_dir), 'commit', '-m', f'Soul Map: {filename}'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(work_dir), 'push'], check=True, capture_output=True)

        # Construct live URL
        if repo == 'thefirstspark.github.io':
            live_url = f"https://thefirstspark.shop/{filename}"
        else:
            live_url = f"https://thefirstspark.github.io/{repo}/{filename}"

        return True, live_url

    except subprocess.CalledProcessError as e:
        return False, f"Git error: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return False, str(e)


# ============================================================
# 9. CLI ENTRY POINT
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Soul Map Generator \u2014 The First Spark')
    parser.add_argument('--name', required=False, help='Full name (or use --batch for multiple)')
    parser.add_argument('--date', required=False, help='Birth date (YYYY-MM-DD)')
    parser.add_argument('--time', help='Birth time (HH:MM, 24hr format)')
    parser.add_argument('--city', help='Birth city')
    parser.add_argument('--country', default='US', help='Birth country code (default: US)')
    parser.add_argument('--repo', default='soul-maps', help='GitHub repo to deploy to')
    parser.add_argument('--no-deploy', action='store_true', help='Generate only, skip GitHub push')
    parser.add_argument('--output', help='Local output path (optional)')
    parser.add_argument('--monthly', action='store_true', help='Generate monthly update instead of full soul map')
    parser.add_argument('--month', type=int, help='Month for monthly update (1-12, default: current)')
    parser.add_argument('--year', type=int, help='Year for monthly update (default: current)')
    parser.add_argument('--batch', help='CSV file for batch generation (columns: Name, Date, Time, City, Country)')
    parser.add_argument('--batch-mode', choices=['soul-map', 'monthly', 'both'], default='both', help='What to generate in batch mode (default: both)')
    parser.add_argument('--batch-output', help='Output directory for batch files (default: current)')

    args = parser.parse_args()

    # Batch mode
    if args.batch:
        success_count, total_count, results = generate_batch(
            args.batch,
            mode=args.batch_mode,
            no_deploy=args.no_deploy,
            output_dir=args.batch_output
        )
        return

    # Single mode — require name and date
    if not args.name or not args.date:
        parser.error("--name and --date required for single mode (or use --batch for multiple)")

    # Parse date
    birth_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    # Parse time
    birth_time = None
    if args.time:
        t = datetime.strptime(args.time, '%H:%M')
        birth_time = (t.hour, t.minute)

    print(f"\n\u26a1 SOUL MAP GENERATOR \u2014 The First Spark")
    print(f"{'='*45}")
    print(f"  Name:     {args.name}")
    print(f"  Born:     {birth_date.strftime('%B %d, %Y')}")
    if birth_time:
        print(f"  Time:     {args.time}")
    if args.city:
        print(f"  City:     {args.city}")
    if args.monthly:
        month_label = f"{args.month}/{args.year}" if args.month and args.year else "current"
        print(f"  Mode:     Monthly Update ({month_label})")
    print(f"{'='*45}\n")

    # Generate based on mode
    if args.monthly:
        # Monthly update mode
        html, filename, summary = generate_monthly_update(
            args.name, birth_date,
            current_year=args.year,
            current_month=args.month
        )
        print("MONTHLY UPDATE:")
        for key, val in summary.items():
            print(f"  {key:>16}: {val}")
    else:
        # Full soul map mode
        html, summary = generate_soul_map(
            args.name, birth_date,
            birth_time=birth_time,
            birth_city=args.city,
            birth_country=args.country
        )
        print("SOUL MAP SUMMARY:")
        for key, val in summary.items():
            print(f"  {key:>16}: {val}")

        # Filename — use shortened format: {INITIALS}{MONTH}{YEAR}.html
        filename = f"{get_base_filename(args.name, birth_date)}.html"

    # Save locally if requested
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding='utf-8')
        print(f"\n  Saved locally: {args.output}")

    # Deploy
    if not args.no_deploy:
        print(f"\n  Deploying to GitHub ({args.repo})...")
        success, result = deploy_to_github(html, filename, repo=args.repo)
        if success:
            print(f"  LIVE: {result}")
        else:
            print(f"  Deploy failed: {result}")
            # Save locally as fallback
            fallback = Path(f"./{filename}")
            fallback.write_text(html, encoding='utf-8')
            print(f"  Saved locally as fallback: {fallback}")
    else:
        local_path = args.output or f"./{filename}"
        p = Path(local_path)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(html, encoding='utf-8')
        print(f"\n  Saved (no deploy): {local_path}")

    print(f"\n  Soul Map complete for {args.name}")


if __name__ == '__main__':
    main()
