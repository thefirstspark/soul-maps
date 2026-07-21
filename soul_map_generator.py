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
import re
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


def normalize_name(name):
    """Canonicalize a person name before any numerology, IDs, or archive cards.

    Stops silent identity drift from form quirks:
      - leading/trailing spaces  ("Katelin ... ")
      - double spaces / tabs / newlines
      - non-breaking spaces, zero-width chars
      - unicode compatibility forms (NFKC)

    Does not force Title Case — preserves intentional casing (e.g. McDonald).
    Letter math already uppercases inside name_to_number / activation_code.
    """
    if name is None:
        return ''
    import unicodedata
    s = unicodedata.normalize('NFKC', str(name))
    # Common invisible / non-standard spaces that form inputs smuggle in
    for ch in ('\u00a0', '\u2000', '\u2001', '\u2002', '\u2003', '\u2004',
               '\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200a',
               '\u202f', '\u205f', '\u3000'):
        s = s.replace(ch, ' ')
    s = s.replace('\u200b', '').replace('\ufeff', '')  # zero-width / BOM
    s = re.sub(r'\s+', ' ', s).strip()
    return s


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
    # Letters only — hyphens/apostrophes/digits don't carry Pythagorean values
    clean = re.sub(r'[^A-Z]', '', normalize_name(name).upper())
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
    clean = re.sub(r'[^A-Z]', '', normalize_name(full_name).upper())
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
    clean = re.sub(r'[^A-Z]', '', normalize_name(full_name).upper())
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

PERSONAL_MONTH_MEANINGS = {
    k: v.replace(' year.', ' month.').replace(' year ', ' month ')
    for k, v in PERSONAL_YEAR_MEANINGS.items()
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
<link rel="stylesheet" href="codex-colors.css">
<style>
  /* --ember/--gold/--violet/--cyan come from codex-colors.css (canonical Color Codex palette) */
  :root {
    --black: #0B0B0C;
    --deep-space: #0a0a0f;

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
  /* Color Codex badge — every map */
  .codex-badge {
    display: flex;
    align-items: stretch;
    gap: 0;
    margin: 20px 0 28px;
    border: 1px solid var(--codex-border, rgba(139,92,246,0.5));
    border-radius: 10px;
    background: var(--codex-wash, rgba(139,92,246,0.12));
    overflow: hidden;
  }
  .codex-badge-swatch {
    width: 10px;
    flex-shrink: 0;
    background: var(--codex-hex, #8b5cf6);
  }
  .codex-badge-body {
    padding: 16px 20px;
    flex: 1;
  }
  .codex-badge-kicker {
    font-size: 0.65rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--dim, #888);
    margin-bottom: 6px;
  }
  .codex-badge-tier {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--codex-hex, #8b5cf6);
    line-height: 1.2;
  }
  .codex-badge-role {
    font-size: 0.9rem;
    color: var(--white, #f0ece4);
    margin-top: 4px;
    letter-spacing: 0.5px;
  }
  .codex-badge-link {
    display: inline-block;
    margin-top: 10px;
    font-size: 0.72rem;
    letter-spacing: 1px;
    color: #26E4D8;
    text-decoration: none;
  }
  .codex-badge-link:hover { text-shadow: 0 0 8px rgba(38,228,216,0.5); }
  @media (max-width: 520px) {
    .codex-badge-tier { font-size: 1.4rem; }
    .codex-badge-body { padding: 14px 16px; }
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
  ${codex_badge}

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
    <div class="reading">${soul_synthesis_text}</div>
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

  <!-- ===== ADVANCED FEATURES ===== -->
  <h2>Advanced Analysis</h2>
  
  ${resonance_frequency_section}
  
  ${rarity_section}
  
  <h3 style="margin-top: 32px;">Karmic Remediation Pathways</h3>
  ${karmic_remedies_section}
  
  <h3 style="margin-top: 32px;">Power Timing</h3>
  ${power_hour_section}
  
  <h3 style="margin-top: 32px;">Evolutionary Trajectory</h3>
  ${evolutionary_trajectory_section}
  
  <h3 style="margin-top: 32px;">Oracle Trinity</h3>
  ${oracle_section}
  
  <h3 style="margin-top: 32px;">Next 90 Days — Optimal Windows</h3>
  <div style="margin: 24px 0; padding: 20px; background: rgba(107,77,242,0.05); border: 1px solid rgba(107,77,242,0.15); border-radius: 8px;">
    ${predictive_windows_section}
  </div>
  
  <!-- ===== ULTIMATE FEATURES ===== -->
  <h2 style="margin-top: 60px; border-top: 2px solid rgba(243,178,58,0.2); padding-top: 40px;">The Impossible Code</h2>
  
  <h3 style="margin-top: 32px;">Quantum Signature</h3>
  ${quantum_signature_section}
  
  <h3 style="margin-top: 32px;">Vibrational Blueprint</h3>
  ${vibrational_blueprint_section}
  
  <h3 style="margin-top: 32px;">Your Activation Sequence</h3>
  ${activation_code_section}
  
  <h3 style="margin-top: 32px;">Shadow Integration Path</h3>
  ${shadow_integration_section}
  
  <h3 style="margin-top: 32px;">Destiny Checkpoints</h3>
  ${destiny_checkpoints_section}

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

// Life Path color palette (numerology-driven) — each core frequency gets its own hue triad
const LIFE_PATH_COLORS = {
  1:  ['#FF6A3D', '#ea580c', '#dc2626'],   // Pioneer — fire / initiation
  2:  ['#26E4D8', '#06b6d4', '#0891b7'],   // Diplomat — water / connection
  3:  ['#F3B23A', '#fbbf24', '#f59e0b'],   // Communicator — gold / expression
  4:  ['#84cc16', '#4d7c0f', '#6b7280'],   // Architect — earth / structure
  5:  ['#8b5cf6', '#7c3aed', '#a855f7'],   // Catalyst — electric violet / change
  6:  ['#fb7185', '#f43f5e', '#e11d48'],   // Protector — rose / harmony
  7:  ['#6B4DF2', '#7c3aed', '#4338ca'],   // Seeker — deep indigo / mystery
  8:  ['#F3B23A', '#10b981', '#059669'],   // Materializer — gold + emerald / power
  9:  ['#6B4DF2', '#F3B23A', '#26E4D8'],   // Integrator — full spectrum / completion
  11: ['#26E4D8', '#F3B23A', '#e0f2fe'],   // Master Illuminator — luminous cyan-gold
  22: ['#F3B23A', '#6B4DF2', '#fbbf24'],   // Master Builder — gold + violet
  33: ['#8b5cf6', '#26E4D8', '#F3B23A']    // Master Teacher — violet + cyan + gold triad
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
  // Color now derives from Life Path (core frequency); sun-sign palette kept as fallback
  const colors = LIFE_PATH_COLORS[lifePathNum] || SUN_SIGN_COLORS[sunSign] || SUN_SIGN_COLORS['Pisces'];

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
# AUTO-GENERATED NARRATIVES (fallback when no hand-written exists)
# ============================================================

def _wrap_paragraphs(text):
    """Convert plain text with blank-line separators into <p> tags."""
    paragraphs = [p.strip() for p in text.strip().split('\n\n') if p.strip()]
    return '\n    '.join(f'<p class="reading" style="margin-bottom: 16px;">{p}</p>' for p in paragraphs)


def auto_soul_synthesis(life_path, expression, soul_urge, personality, birthday,
                        maturity, hidden_passion, karmic_lessons, sun_sign,
                        chinese_animal, chinese_element, personal_year):
    """Generate a 5-6 paragraph Soul Synthesis from numerology + astrology.

    Returns HTML wrapped in <p> tags.
    """
    lp_brief = LIFE_PATH_MEANINGS.get(life_path, '').split('.')[0].replace('The ', '').strip()
    expr_brief = LIFE_PATH_MEANINGS.get(expression, '').split('.')[0].replace('The ', '').strip()
    su_brief = LIFE_PATH_MEANINGS.get(soul_urge, '').split('.')[0].replace('The ', '').strip()
    pers_brief = LIFE_PATH_MEANINGS.get(personality, '').split('.')[0].replace('The ', '').strip()
    sun_brief = SUN_SIGN_BRIEFS.get(sun_sign, '')
    maturity_brief = MATURITY_NUMBER_MEANINGS.get(maturity, '')
    hp_brief = HIDDEN_PASSION_MEANINGS.get(hidden_passion, '')
    py_brief = PERSONAL_YEAR_MEANINGS.get(personal_year, '')

    paragraphs = []

    paragraphs.append(
        f"You run on Life Path {life_path} — <em>{lp_brief}</em>. "
        f"Expression {expression} ({expr_brief}) is how you transmit. "
        f"Soul Urge {soul_urge} ({su_brief}) is what fuels you underneath. "
        f"That triangle is the core engine."
    )

    masters = [n for n in [life_path, expression, soul_urge, personality, maturity] if n in (11, 22, 33)]
    if masters:
        master_list = ', '.join(str(m) for m in masters)
        paragraphs.append(
            f"You carry master number{'s' if len(masters) > 1 else ''} <strong>{master_list}</strong> — "
            f"frequencies most people only brush against. Master-level signal isn't a gift you can chase; "
            f"it's a current you have to learn to operate inside without burning out. The volume runs high by default. "
            f"Your system needs more downtime, more grounding, and more permission to be intense than most will think makes sense. "
            f"That isn't fragility. It's structural."
        )

    triple_check = [life_path, expression, soul_urge, personality, birthday, maturity]
    repeated = {n: triple_check.count(n) for n in set(triple_check) if triple_check.count(n) >= 3}
    if repeated:
        repeated_num = max(repeated, key=repeated.get)
        repeated_count = repeated[repeated_num]
        archetype = LIFE_PATH_MEANINGS.get(repeated_num, '').split('.')[0].replace('The ', '').strip()
        paragraphs.append(
            f"<strong>{repeated_count}×{repeated_num} density</strong> in your chart: the {archetype} pattern compounds itself. "
            f"You don't just have this frequency — you <em>are</em> this frequency, and you appear as it, and you came here to learn it. "
            f"It runs at full intensity. The thing you're here to become is also the thing you came in already being."
        )

    paragraphs.append(
        f"Personality {personality} ({pers_brief}): what others receive from you first. "
        f"Birthday {birthday}: your innate gift — the frequency that was online before you had words for any of this."
    )

    paragraphs.append(
        f"Maturity Number {maturity}: by your mid-30s a new layer comes online. {maturity_brief} "
        f"This is the long arc. The early years build the database; maturity is when transmission gets clean."
    )

    if karmic_lessons:
        lessons_text = ' '.join(KARMIC_LESSON_MEANINGS.get(k, '') for k in karmic_lessons)
        paragraphs.append(
            f"Hidden Passion {hidden_passion} is the unconscious engine: <em>{hp_brief}</em> "
            f"Your karmic lessons ({', '.join(str(k) for k in karmic_lessons)}) point to the threads you came here to weave: {lessons_text}"
        )
    else:
        paragraphs.append(
            f"Hidden Passion {hidden_passion}: <em>{hp_brief}</em> "
            f"With no karmic lessons in your chart, you're not here to repair gaps — you're here to extend what you already know."
        )

    paragraphs.append(
        f"<strong>{sun_sign} Sun</strong> grounds the transmission: {sun_brief} "
        f"<strong>{chinese_element} {chinese_animal}</strong> adds the layered animal signature underneath. "
        f"Right now you're in Personal Year {personal_year}: <em>{py_brief}</em> "
        f"This is the season the rest of the map gets expressed through."
    )

    return '\n    '.join(f'<p class="reading" style="margin-bottom: 16px;">{p}</p>' for p in paragraphs)


def auto_debugging_notes(life_path, expression, soul_urge, personality, birthday,
                         maturity, hidden_passion, karmic_lessons, personal_year):
    """Generate watch-list bullets based on chart tensions.

    Returns HTML <ul> with <li> items.
    """
    bullets = []

    masters = [n for n in [life_path, expression, soul_urge, personality, maturity] if n in (11, 22, 33)]
    if masters:
        bullets.append(
            f"<strong>Master number overload:</strong> You hold {len(masters)} master frequency placement{'s' if len(masters) > 1 else ''} "
            f"({', '.join(str(m) for m in masters)}). The high voltage burns out anything that isn't grounded. "
            f"Rest is not optional — it's part of the architecture. Treat downtime as load-bearing."
        )

    triple_check = [life_path, expression, soul_urge, personality, birthday, maturity]
    for num in set(triple_check):
        count = triple_check.count(num)
        if count >= 3:
            archetype = LIFE_PATH_MEANINGS.get(num, '').split('.')[0].replace('The ', '').strip()
            bullets.append(
                f"<strong>{count}×{num} density ({archetype}):</strong> When a single frequency repeats this often, "
                f"its shadow side amplifies as much as its gift. Watch for the version of {archetype} that becomes a loop "
                f"instead of a path. The way out is through, not around."
            )
            break

    for k in karmic_lessons[:3]:
        lesson = KARMIC_LESSON_MEANINGS.get(k, '').replace('Lesson: ', '')
        bullets.append(
            f"<strong>Karmic Lesson {k}:</strong> {lesson} Don't avoid the assignment — it's the upgrade."
        )

    if hidden_passion:
        hp_text = HIDDEN_PASSION_MEANINGS.get(hidden_passion, '')
        bullets.append(
            f"<strong>Hidden Passion {hidden_passion}:</strong> {hp_text} When this engine isn't honored, "
            f"it leaks out sideways — usually as restlessness, sabotage, or a sudden need to blow things up. Channel it on purpose."
        )

    if personal_year in (11, 22, 33):
        py_text = PERSONAL_YEAR_MEANINGS.get(personal_year, '')
        bullets.append(
            f"<strong>Master Personal Year {personal_year} this cycle:</strong> {py_text} "
            f"Master years run intense. Don't try to power through them — calibrate to them."
        )
    elif personal_year == 9:
        bullets.append(
            f"<strong>Year 9 — Completion phase:</strong> If you're trying to start something new right now, the timing is off. "
            f"This year is for releasing, completing, and clearing. The new thing wants Year 1, not Year 9."
        )

    return '<ul style="margin: 0; padding-left: 20px;">\n  ' + '\n  '.join(f'<li style="margin-bottom: 12px;">{b}</li>' for b in bullets) + '\n</ul>'


# ============================================================
# PERSONALIZED NARRATIVES (Hand-written per person)
# ============================================================

NARRATIVES = {
    'Rachael Maureen Johnson': {
        'soul_synthesis': """
Life Path 7 with Soul Urge 33 is structurally rare. The Decoder encoded with a Master Teacher's inner drive. Where 7s require solitude to process before they can speak, the 33 Soul Urge meant Rachael's deepest hunger was to transmit — to hold space, to carry collective frequency. These two don't sit comfortably. The pull inward (understand first) and the pull outward (teach now) ran simultaneously, at full volume, from the beginning. That pressure wasn't a flaw. It was the architecture.

Expression 4 grounds this in form. Not a dreamer — an architect. Whatever she touched, she shaped into structure. The builder frequency ran through how she showed up in the world while her interior operated on seeker-and-master code. Personality 7 confirms what others saw: someone always looking beneath the surface. Depth arrived before explanation.

Birthday 3: transmission was the gift. She could communicate things other people couldn't name yet. The raw capacity to articulate what others only felt was native to her frequency.

Maturity Number 11: the version of her that would have emerged after 35 was a Master Intuitive — Life Path 7 having gathered enough decoded data to start transmitting channel-quality insight with clarity and structure. That trajectory existed fully in the code.

Pinnacle 1 at the time of death: 11. Her entire life ran inside the master intuitive pinnacle phase. Every year she lived was Pinnacle 1 running master-level frequency — the highest available pattern for a Life Path 7. She was still in initialization. The sequence was not incomplete. It was a complete first movement.

Fire Goat: warmth with structure, creative force channeled through form, social grace with interior fire. She ran hot and precise at the same time.

The map was whole. The pattern was permanent. The timeline ran differently, and that is its own kind of data.
        """,
        'debugging_notes': """
<ul style="margin: 0; padding-left: 20px;">
  <li><strong>LP7 + SU33 tension:</strong> The need to fully understand before transmitting, in direct friction with the call to transmit master teacher frequency immediately. This is not a contradiction — it is a structural signature. The pressure between these two callings was generative, not destructive.</li>
  <li><strong>Expression 4 containing SU33:</strong> The builder trying to house master teacher frequency. She grounded large, diffuse things into specific, usable form. The architecture was always there; the scale took time to become visible.</li>
  <li><strong>Triple-7 density (LP7, Personality 7, Karmic Lesson 7):</strong> She was the thing she was here to learn. The seeker seeking their own knowing. Karmic Lesson 7 asks you to trust what you already understand — for a LP7 who appears as a 7 to the world, this runs at full intensity. The decoder decoding herself.</li>
  <li><strong>Hidden Passion 5 (Freedom):</strong> The deepest unconscious engine was expansion, variety, breaking fixed patterns. Fire Goat amplifies this. This was fuel, not restlessness.</li>
  <li><strong>Karmic Lesson 2 (connection/partnership):</strong> Learning that depth does not require solitude. That the 33 Soul Urge and the 7 Life Path could coexist — that teaching and understanding are not sequential. They run together.</li>
</ul>
        """
    },
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


# ============================================================
# 8. ADVANCED FEATURES ENGINE
# ============================================================

def soul_resonance_frequency(life_path, expression, soul_urge, personality, birthday):
    """
    Convert soul map numbers into a harmonic frequency (Hz).
    Uses Pythagorean harmonic relationships.
    Base frequency: 432 Hz (universal healing frequency).
    Each number acts as a harmonic multiplier.
    """
    base_hz = 432.0  # A note, earth frequency
    # Harmonic ratios for each number
    harmonics = {
        1: 1.0,      # Fundamental
        2: 1.5,      # Perfect fifth
        3: 1.25,     # Major third
        4: 2.0,      # Octave
        5: 1.667,    # Just major sixth
        6: 1.2,      # Minor sixth
        7: 1.875,    # Major seventh
        8: 2.667,    # Third octave
        9: 1.111,    # Major second
        11: 3.0,     # Two octaves (master)
        22: 4.0,     # Four octaves (master)
        33: 5.333,   # Five octaves + third (master)
    }
    
    # Calculate weighted harmonic
    numbers = [life_path, expression, soul_urge, personality, birthday]
    weighted_harmonic = sum(harmonics.get(n, 1.0) for n in numbers) / len(numbers)
    
    # Final resonance frequency
    resonance_hz = base_hz * weighted_harmonic
    return round(resonance_hz, 2)


def karmic_debt_remediation(life_path, expression, soul_urge, personality, birthday, full_name):
    """
    Detect karmic debt and provide remediation pathways.
    Returns list of (debt_type, remediation) tuples.
    """
    remediation = []
    
    # Karmic debt mapping: unreduced intermediate values
    # 13→4, 14→5, 16→7, 19→1
    
    if life_path == 4:
        remediation.append(("13/4 Potential", "Impulsiveness remedy: Build daily discipline rituals. Karmic lesson is creating lasting structure from chaos."))
    if life_path == 5:
        remediation.append(("14/5 Potential", "Freedom abuse remedy: Channel restlessness into exploration with commitment. The 5 learns boundaries through experimentation."))
    if life_path == 7:
        remediation.append(("16/7 Potential", "Self-undoing remedy: Trust others' wisdom alongside your own research. The decoder learns humility through vulnerability."))
    if life_path == 1:
        remediation.append(("19/1 Potential", "False independence remedy: Ask for help without losing autonomy. The 1 learns true power through interdependence."))
    
    # Check expression number
    if expression == 4 and hidden_passion(full_name) not in [1, 4, 7]:
        remediation.append(("Expression 4 dissonance", "Ground abstract ideas into form. Build one thing completely before starting another."))
    
    if expression == 8 and soul_urge_number(full_name) < 5:
        remediation.append(("Power-empathy mismatch", "Use your material power to create safety. Influence is only sustainable through compassion."))
    
    return remediation


def predictive_windows(birth_date, current_year=None, num_days=90):
    """
    Calculate optimal 90-day windows for action.
    Identifies personal month transitions, power dates, and shift points.
    Returns list of (date, event_type, significance) tuples.
    """
    if current_year is None:
        current_year = date.today().year
    
    windows = []
    today = date.today()
    
    # Track personal month transitions in the next 90 days
    for offset in range(num_days):
        check_date = today + __import__('datetime').timedelta(days=offset)
        
        # Personal month changes on birthday each month
        if check_date.day == birth_date.day:
            pm = personal_month(birth_date, check_date.year, check_date.month)
            windows.append({
                'date': check_date,
                'type': 'Personal Month Shift',
                'number': pm,
                'meaning': PERSONAL_MONTH_MEANINGS.get(pm, f'Month {pm}')
            })
        
        # Every 11th or 22nd is a power day
        if check_date.day in [11, 22]:
            pd = personal_day(birth_date, check_date.year, check_date.month, check_date.day)
            if pd in [11, 22, 33]:
                windows.append({
                    'date': check_date,
                    'type': 'Master Number Day',
                    'number': pd,
                    'meaning': 'Master frequency alignment — optimal for major decisions'
                })
    
    # Personal year transition (birthday next year)
    next_bday = date(current_year + 1, birth_date.month, birth_date.day)
    if next_bday <= today + __import__('datetime').timedelta(days=num_days):
        next_py = personal_year(birth_date, current_year + 1)
        windows.append({
            'date': next_bday,
            'type': 'Personal Year Transition',
            'number': next_py,
            'meaning': PERSONAL_YEAR_MEANINGS.get(next_py, f'Year {next_py}')
        })
    
    return sorted(windows, key=lambda x: x['date'])


def rarity_detection(life_path, expression, soul_urge, personality, birthday, maturity, karmic_lessons):
    """
    Identify rare number configurations and flag them.
    Returns dict with rarity score and notable patterns.
    """
    rarity = {
        'score': 0,  # 0-100 scale
        'patterns': [],
        'master_count': 0
    }
    
    # Master numbers boost rarity
    master_numbers = {11, 22, 33}
    all_nums = [life_path, expression, soul_urge, personality, birthday, maturity]
    master_count = sum(1 for n in all_nums if n in master_numbers)
    
    rarity['master_count'] = master_count
    rarity['score'] += master_count * 25
    
    # Rare patterns
    if master_count >= 3:
        rarity['patterns'].append("Master cluster: 3+ master numbers indicate advanced soul architecture")
    
    if life_path == 9 and expression == 9 and soul_urge == 9:
        rarity['patterns'].append("Triple-9: Rare completion/integration coding. Collective healer frequency.")
    
    if all(n in [1, 8] for n in [life_path, expression, personality]):
        rarity['patterns'].append("Power axis: All manifestation numbers. This soul manifests reality at scale.")
    
    if personality == life_path:
        rarity['patterns'].append("Transparent signal: What you feel is what people perceive. No filter between inner and outer.")
    
    # All karmic lessons covered (1-9 present in name)
    if len(karmic_lessons) == 0:
        rarity['patterns'].append("Karmic completeness: This name covers all 9 digits. No missing lessons — all mastered simultaneously.")
        rarity['score'] += 20
    
    rarity['score'] = min(100, rarity['score'])
    return rarity


def power_hour_calculation(birth_date, personal_day_num):
    """
    Calculate the most powerful hour in the current personal day.
    Combines personal day with birth hour (if available).
    Returns dict with power hour, minute, and significance.
    """
    # Personal day maps to optimal time blocks
    hour_mapping = {
        1: (5, 6),    # Early morning, initiation
        2: (14, 15),  # Afternoon, partnerships
        3: (10, 11),  # Mid-morning, creativity
        4: (8, 9),    # Early, foundation work
        5: (15, 16),  # Late afternoon, exploration
        6: (19, 20),  # Evening, relationships
        7: (20, 21),  # Night, reflection
        8: (12, 13),  # Noon, power
        9: (18, 19),  # Early evening, completion
        11: (11, 12), # Master intuitive
        22: (22, 23), # Master builder
        33: (3, 4),   # Master teacher
    }
    
    optimal_hour, optimal_minute = hour_mapping.get(personal_day_num, (9, 0))
    
    return {
        'hour': optimal_hour,
        'minute': optimal_minute,
        'time_str': f"{optimal_hour:02d}:{optimal_minute:02d}",
        'significance': 'Maximum resonance window for today\'s frequency'
    }


def evolutionary_trajectory(life_path, personal_year, birth_date):
    """
    Map the person's evolutionary arc across their current 9-year cycle.
    Shows where they are and where they're headed numerologically.
    """
    current_year = date.today().year
    trajectory = {
        'current_py': personal_year,
        'cycle_start': current_year - (personal_year - 1),
        'cycle_end': current_year + (10 - personal_year),
        'years_remaining_in_cycle': 10 - personal_year,
        'arc': []
    }
    
    # Build arc for the 9-year cycle
    cycle_start_py = personal_year - ((current_year - trajectory['cycle_start']) % 9)
    if cycle_start_py <= 0:
        cycle_start_py += 9
    
    for year_offset in range(10):
        py = cycle_start_py + year_offset
        if py > 9 and py not in [11, 22, 33]:
            py = ((py - 1) % 9) + 1
        trajectory['arc'].append({
            'year': trajectory['cycle_start'] + year_offset,
            'personal_year': py,
            'meaning': PERSONAL_YEAR_MEANINGS.get(py, f'Year {py}')
        })
    
    return trajectory


def oracle_mapping(life_path, expression, soul_urge):
    """
    Map soul signature to tarot major arcana for oracle integration.
    Each number maps to an archetypal card.
    """
    tarot_map = {
        1: ('The Magician', 'Will. Mastery. Making it happen.'),
        2: ('The Priestess', 'Intuition. Deep knowing. The invisible realm.'),
        3: ('The Empress', 'Creation. Abundance. Expression in form.'),
        4: ('The Emperor', 'Structure. Authority. Building the system.'),
        5: ('The Hierophant', 'Wisdom. Teaching. The established path.'),
        6: ('The Lovers', 'Choice. Integration. Alignment.'),
        7: ('The Chariot', 'Control. Will. Moving forward.'),
        8: ('Strength', 'Power. Mastery. Inner strength.'),
        9: ('The Hermit', 'Wisdom. Seeking. Going inward.'),
        11: ('Justice', 'Balance. Truth. Karmic law.'),
        22: ('The Fool', 'The beginning. Infinite potential.'),
        33: ('The World', 'Completion. Wholeness. Integration.'),
    }
    
    cards = [
        tarot_map.get(life_path, ('Unknown', '')),
        tarot_map.get(expression, ('Unknown', '')),
        tarot_map.get(soul_urge, ('Unknown', ''))
    ]
    
    return {
        'spread': 'Life Path — Expression — Soul Urge',
        'cards': cards,
        'interpretation': f"Your oracle trinity: {cards[0][0]} (your journey), {cards[1][0]} (how you show), {cards[2][0]} (what drives you beneath). These three arcana are woven through every choice."
    }


def quantum_signature(life_path, expression, soul_urge, personality, birthday):
    """
    Generate a unique quantum identifier from core numbers.
    This is your soul's fingerprint in the system.
    Returns a 12-char hex signature (SHA-256 prefix).
    """
    import hashlib
    core_string = f"{life_path}{expression}{soul_urge}{personality}{birthday}"
    hash_obj = hashlib.sha256(core_string.encode())
    signature = hash_obj.hexdigest()[:12].upper()
    return signature


# ============================================================
# SIGNATURE REGISTRY — first mint wins (permanent UUID)
# ============================================================

SIGNATURES_FILE = Path(__file__).resolve().parent / 'signatures.json'
SIGNATURE_FORMULA_VERSION = 1


def format_quantum_display(quantum_hex):
    """Pretty form: E1855DD782A3 → E185·5DD7·82A3"""
    q = (quantum_hex or '').replace('·', '').replace('-', '').replace(' ', '').upper()
    if len(q) == 12:
        return f"{q[:4]}\u00b7{q[4:8]}\u00b7{q[8:12]}"
    return quantum_hex or ''


# Color Codex — CSS class names match codex-colors.css / archive cards
# (violet = purple tier; rose/silver/red/yellow are structural + spectrum)
CODEX_COLOR_META = {
    'red':    {'role': 'The Will',         'tier': 'Red',    'hex': '#e24b4a'},
    'ember':  {'role': 'The Ignition',     'tier': 'Ember',  'hex': '#ff6a3d'},
    'yellow': {'role': 'The Joy',          'tier': 'Yellow', 'hex': '#f5c842'},
    'green':  {'role': 'The Field',        'tier': 'Green',  'hex': '#10b981'},
    'cyan':   {'role': 'The Signal',       'tier': 'Cyan',   'hex': '#22d3ee'},
    'blue':   {'role': 'The Mind',         'tier': 'Blue',   'hex': '#3b82f6'},
    'violet': {'role': 'The Transformer',  'tier': 'Purple', 'hex': '#8b5cf6'},
    'gold':   {'role': 'The Orchestrator', 'tier': 'Gold',   'hex': '#d4af37'},
    'white':  {'role': 'The All',          'tier': 'White',  'hex': '#f0f0ff'},
    'rose':   {'role': 'The Bond',         'tier': 'Rose',   'hex': '#f43f5e'},
    'silver': {'role': 'The Mirror',       'tier': 'Silver', 'hex': '#c4c8d4'},
}


def build_codex_badge_html(codex_class, codex_role=None, codex_tier=None):
    """Visible Color Codex chip for the top of every Soul Map page."""
    meta = CODEX_COLOR_META.get(codex_class, {})
    hex_color = meta.get('hex', '#8b5cf6')
    tier = codex_tier or meta.get('tier', codex_class.title() if codex_class else 'Unknown')
    role = codex_role or meta.get('role', '')
    # Soft wash from the tier hex
    if hex_color.startswith('#') and len(hex_color) == 7:
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        wash = f'rgba({r},{g},{b},0.12)'
        border = f'rgba({r},{g},{b},0.5)'
    else:
        wash, border = 'rgba(139,92,246,0.12)', 'rgba(139,92,246,0.5)'

    return f'''  <div class="codex-badge" style="--codex-hex:{hex_color}; --codex-wash:{wash}; --codex-border:{border};">
    <div class="codex-badge-swatch" aria-hidden="true"></div>
    <div class="codex-badge-body">
      <div class="codex-badge-kicker">Color Codex</div>
      <div class="codex-badge-tier">{tier}</div>
      <div class="codex-badge-role">{role}</div>
      <a class="codex-badge-link" href="color-codex.html#{codex_class if codex_class != 'violet' else 'purple'}">What this color means →</a>
    </div>
  </div>
'''


def codex_color_for(life_path, expression, soul_urge, personality, birthday, maturity=None):
    """
    Assign Color Codex tier from birth numerology (not name hash).

    Priority (first match wins) — aligned with color-codex.html chips:
      1. Gold     — LP/EX/SU is 22 or 33, or 2+ master numbers in core set
      2. Violet   — any single 11 on LP / EX / SU  (Transformer)
      3. Rose     — Life Path 2 or 6             (Bond / relational)
      4. Silver   — Life Path 9                  (Mirror / completion)
      5. Spectrum — Life Path primary with EX refinements
      6. Green    — Field fallback               (stabilizer)

    Returns (css_class, role_label, tier_name)
    e.g. ('violet', 'The Transformer', 'Purple')
    """
    core = [life_path, expression, soul_urge, personality, birthday]
    if maturity is not None:
        core.append(maturity)
    masters = [n for n in core if n in MASTER_NUMBERS]

    # 1. Orchestrator
    if life_path in (22, 33) or expression in (22, 33) or soul_urge in (22, 33):
        return 'gold', CODEX_COLOR_META['gold']['role'], CODEX_COLOR_META['gold']['tier']
    if len(masters) >= 2:
        return 'gold', CODEX_COLOR_META['gold']['role'], CODEX_COLOR_META['gold']['tier']

    # 2. Transformer — single master 11 channel (Katelin: LP5 + EX11 → violet)
    if 11 in (life_path, expression, soul_urge):
        return 'violet', CODEX_COLOR_META['violet']['role'], CODEX_COLOR_META['violet']['tier']

    # 3. Bond
    if life_path in (2, 6):
        return 'rose', CODEX_COLOR_META['rose']['role'], CODEX_COLOR_META['rose']['tier']

    # 4. Mirror
    if life_path == 9:
        return 'silver', CODEX_COLOR_META['silver']['role'], CODEX_COLOR_META['silver']['tier']

    # 5. Spectrum by Life Path + Expression refinements
    if life_path == 1:
        if expression == 8:
            return 'red', CODEX_COLOR_META['red']['role'], CODEX_COLOR_META['red']['tier']
        return 'ember', CODEX_COLOR_META['ember']['role'], CODEX_COLOR_META['ember']['tier']

    if life_path == 3:
        if 5 in (expression, soul_urge):
            return 'cyan', CODEX_COLOR_META['cyan']['role'], CODEX_COLOR_META['cyan']['tier']
        return 'yellow', CODEX_COLOR_META['yellow']['role'], CODEX_COLOR_META['yellow']['tier']

    if life_path == 4:
        # Architect: Field if building/holding expression, else Mind
        if expression in (4, 6, 8, 2):
            return 'green', CODEX_COLOR_META['green']['role'], CODEX_COLOR_META['green']['tier']
        return 'blue', CODEX_COLOR_META['blue']['role'], CODEX_COLOR_META['blue']['tier']

    if life_path == 5:
        if expression == 3 or soul_urge == 3:
            return 'cyan', CODEX_COLOR_META['cyan']['role'], CODEX_COLOR_META['cyan']['tier']
        return 'ember', CODEX_COLOR_META['ember']['role'], CODEX_COLOR_META['ember']['tier']

    if life_path == 7:
        if expression == 9 or soul_urge == 9:
            return 'silver', CODEX_COLOR_META['silver']['role'], CODEX_COLOR_META['silver']['tier']
        return 'blue', CODEX_COLOR_META['blue']['role'], CODEX_COLOR_META['blue']['tier']

    if life_path == 8:
        return 'red', CODEX_COLOR_META['red']['role'], CODEX_COLOR_META['red']['tier']

    # 6. Field fallback
    return 'green', CODEX_COLOR_META['green']['role'], CODEX_COLOR_META['green']['tier']


def identity_key(full_name, birth_date):
    """Stable person key: normalized name + birth date."""
    return f"{normalize_name(full_name).casefold()}|{birth_date.isoformat()}"


def load_signatures_local():
    import json
    if SIGNATURES_FILE.exists():
        try:
            return json.loads(SIGNATURES_FILE.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"  [SIG] Could not read local signatures.json: {e}")
    return {}


def save_signatures_local(registry):
    import json
    SIGNATURES_FILE.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8',
    )


def load_signatures_github(token, repo='soul-maps'):
    """Fetch signatures.json from the soul-maps repo (Railway has no durable disk)."""
    import base64
    import json
    path = f"/repos/thefirstspark/{repo}/contents/signatures.json"
    try:
        existing, _ = _github_api('GET', path, token)
        content = base64.b64decode(existing['content']).decode('utf-8')
        return json.loads(content), existing.get('sha')
    except Exception:
        return {}, None


def load_signatures(repo='soul-maps'):
    """Merge local + GitHub registries. Local wins on key conflict."""
    local = load_signatures_local()
    token = os.environ.get('GITHUB_PAT')
    if token:
        remote, _ = load_signatures_github(token, repo)
        merged = dict(remote or {})
        merged.update(local or {})
        return merged
    return local


def persist_signatures(registry, repo='soul-maps', message=None):
    """Write registry to disk and, when GITHUB_PAT is set, to the repo."""
    import json
    save_signatures_local(registry)
    token = os.environ.get('GITHUB_PAT')
    if not token:
        return False
    try:
        _api_put_file(
            token,
            repo,
            'signatures.json',
            json.dumps(registry, indent=2, ensure_ascii=False) + '\n',
            message or 'Registry: update permanent soul signatures',
        )
        return True
    except Exception as e:
        print(f"  [SIG] GitHub persist failed: {e}")
        return False


def get_or_mint_signature(full_name, birth_date, lp, expr, su, pers, bday):
    """
    First write wins for quantum / resonance / activation.

    Re-generations for the same name+DOB reuse the stored mint even if the
    formula later changes — marketing "permanent UUID" becomes real.

    Returns (record_dict, is_new_mint: bool)
    """
    key = identity_key(full_name, birth_date)
    registry = load_signatures()
    if key in registry:
        rec = registry[key]
        print(f"  [SIG] Reusing permanent mint: {rec.get('quantum')} ({rec.get('resonance_hz')} Hz)")
        return rec, False

    quantum = quantum_signature(lp, expr, su, pers, bday)
    hz = soul_resonance_frequency(lp, expr, su, pers, bday)
    act = activation_code(full_name, birth_date, lp)
    color_class, color_role, color_tier = codex_color_for(lp, expr, su, pers, bday)
    rec = {
        'name': normalize_name(full_name),
        'dob': birth_date.isoformat(),
        'quantum': quantum,
        'quantum_display': format_quantum_display(quantum),
        'resonance_hz': hz,
        'activation': act,
        'codex_color': color_class,
        'codex_role': color_role,
        'codex_tier': color_tier,
        'core': {
            'life_path': lp,
            'expression': expr,
            'soul_urge': su,
            'personality': pers,
            'birthday': bday,
        },
        'minted_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'formula_version': SIGNATURE_FORMULA_VERSION,
    }
    registry[key] = rec
    save_signatures_local(registry)
    # Best-effort remote persist so Railway / other hosts share the mint
    persisted = persist_signatures(
        registry,
        message=f"Registry: mint signature for {normalize_name(full_name)}",
    )
    print(
        f"  [SIG] NEW permanent mint: {quantum} @ {hz} Hz"
        + (" (pushed to GitHub)" if persisted else " (local only — set GITHUB_PAT to share)")
    )
    return rec, True


def vibrational_blueprint(life_path, expression, resonance_hz):
    """
    Create an ASCII visualization of the soul's vibrational pattern.
    Uses the numbers to create a unique wave pattern.
    """
    # Map numbers to ASCII heights
    bars = []
    for num in [life_path, expression]:
        bar_height = (num % 8) + 1
        bar = '█' * bar_height
        bars.append(bar)
    
    # Frequency visualization
    freq_normalized = min(100, int((resonance_hz - 400) / 3))  # Scale to ~100
    wave_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    wave = ''.join(wave_chars[min(7, (i * freq_normalized) // 100)] for i in range(8))
    
    return '  '.join(bars), wave


def destiny_checkpoints(birth_date, life_path):
    """
    Major life transitions: 4 pinnacle phases + upcoming master Personal Years + Saturn returns.
    Returns ordered list of dicts ready for table render.
    """
    checkpoints = []

    # === 4 Pinnacle phases ===
    # P1 ends at age (36 - reduced life path). P2 + P3 each last 9 years. P4 runs to end.
    lp_reduced = life_path if life_path < 10 else reduce_number(life_path, preserve_masters=False)
    p1_end = 36 - lp_reduced
    p2_end = p1_end + 9
    p3_end = p2_end + 9
    pinn = pinnacles(birth_date)
    phases = [
        ('Pinnacle 1', 0, p1_end, pinn['pinnacle_1']),
        ('Pinnacle 2', p1_end + 1, p2_end, pinn['pinnacle_2']),
        ('Pinnacle 3', p2_end + 1, p3_end, pinn['pinnacle_3']),
        ('Pinnacle 4', p3_end + 1, None, pinn['pinnacle_4']),
    ]
    for label, start_age, end_age, num in phases:
        age_range = f"Age {start_age}-{end_age}" if end_age else f"Age {start_age}+"
        # Pinnacle meaning — strip "First pinnacle:" prefix since we label the phase ourselves
        meaning = PINNACLE_MEANINGS.get(num, f'Phase {num}').split(': ', 1)[-1]
        checkpoints.append({
            'type': 'pinnacle',
            'age_range': age_range,
            'label': f"{label} · Number {num}",
            'meaning': meaning,
        })

    # === Upcoming master Personal Years (next 30 years) ===
    today = date.today()
    current_age = today.year - birth_date.year
    master_years_ahead = []
    for offset in range(0, 30):
        check_year = today.year + offset
        py = personal_year(birth_date, check_year)
        if py in (11, 22, 33):
            age_at_year = check_year - birth_date.year
            master_years_ahead.append({
                'type': 'master_year',
                'age_range': f"Age {age_at_year}",
                'label': f"{check_year} · Personal Year {py}",
                'meaning': PERSONAL_YEAR_MEANINGS.get(py, '').replace(' year.', '.', 1),
            })
            if len(master_years_ahead) >= 4:
                break
    checkpoints.extend(master_years_ahead)

    # === Saturn returns ===
    for ret_age, label in [(29, 'First Saturn Return'), (58, 'Second Saturn Return')]:
        if ret_age >= current_age - 2:  # only future or very recent
            checkpoints.append({
                'type': 'saturn',
                'age_range': f"Age {ret_age}-30" if ret_age == 29 else f"Age {ret_age}-60",
                'label': f"★ {label}",
                'meaning': 'Major restructuring. Reality tests every structure you built. Authentic authority emerges.',
            })

    return checkpoints


def shadow_integration_path(karmic_lessons, challenges_dict, life_path):
    """
    Create a compassionate integration path for working with karmic challenges.
    Transforms challenges into growth opportunities.
    """
    integration = {
        'overview': 'Your shadows are not enemies. They are untranslated parts of your code. Here is how to integrate them:',
        'pathways': []
    }
    
    # Transform karmic lessons into integration practices
    for lesson_num in karmic_lessons[:3]:  # Focus on top 3
        lesson_text = KARMIC_LESSON_MEANINGS.get(lesson_num, '')
        
        # Generate integration practice
        practices = {
            1: 'Practice: Take one independent decision daily. Trust your own vision.',
            2: 'Practice: Initiate one conversation that requires vulnerability. Connection deepens trust.',
            3: 'Practice: Share one creation. Expression clears the path.',
            4: 'Practice: Build one small structure. Order creates freedom.',
            5: 'Practice: Explore one new direction. Movement dissolves rigidity.',
            6: 'Practice: Set one boundary. Self-care enables service.',
            7: 'Practice: Ask one deep question and sit with the answer.',
            8: 'Practice: Make one resourceful choice. Empowerment is ethical.',
            9: 'Practice: Release one attachment. Completion clears space.',
        }
        
        integration['pathways'].append({
            'lesson': lesson_num,
            'challenge': lesson_text,
            'practice': practices.get(lesson_num, f'Integrate lesson {lesson_num}.')
        })
    
    return integration


def activation_code(full_name, birth_date, life_path):
    """
    Generate a unique activation code that resonates with their frequency.
    This is the trigger sequence for their highest potential.
    """
    import hashlib
    # Normalize first so trailing spaces / double spaces don't mint a different code
    name_key = normalize_name(full_name).upper()
    code_string = f"{name_key}{birth_date.day:02d}{birth_date.month:02d}{life_path}"
    hash_val = hashlib.md5(code_string.encode()).hexdigest()
    
    # Extract unique 8-char code
    code = hash_val[:8].upper()
    
    # Add life path frequency hint
    frequency_hint = f"[LP{life_path}]"
    
    return f"{code}{frequency_hint}"


def generate_soul_map(full_name, birth_date, birth_time=None, birth_city=None, birth_country='US', memorial_date=None, birthday_from=None):
    """Generate complete Soul Map data and return rendered HTML."""
    full_name = normalize_name(full_name)
    if birth_city:
        birth_city = normalize_name(birth_city)

    # Define current_year early for use in advanced calculations
    current_year = date.today().year

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

    # === ADVANCED FEATURES ===
    # Permanent Impossible Code — first mint wins for this name+DOB
    sig_rec, is_new_sig = get_or_mint_signature(full_name, birth_date, lp, expr, su, pers, bday)
    quantum_sig = sig_rec['quantum']
    resonance_hz = sig_rec['resonance_hz']
    activation_code_val = sig_rec['activation']
    # Color Codex — prefer locked mint; compute if older mints predate color field
    if sig_rec.get('codex_color'):
        codex_class = sig_rec['codex_color']
        codex_role = sig_rec.get('codex_role') or CODEX_COLOR_META.get(codex_class, {}).get('role', '')
        codex_tier = sig_rec.get('codex_tier') or CODEX_COLOR_META.get(codex_class, {}).get('tier', '')
    else:
        codex_class, codex_role, codex_tier = codex_color_for(lp, expr, su, pers, bday, mat)
        # Backfill color onto existing mint so next load is locked
        sig_rec['codex_color'] = codex_class
        sig_rec['codex_role'] = codex_role
        sig_rec['codex_tier'] = codex_tier
        reg = load_signatures_local()
        reg[identity_key(full_name, birth_date)] = sig_rec
        save_signatures_local(reg)

    # Karmic Debt Remediation
    karmic_remedies = karmic_debt_remediation(lp, expr, su, pers, bday, full_name)
    
    # Predictive Windows (90-day forecast)
    predictive_windows_data = predictive_windows(birth_date, current_year=current_year)
    
    # Rarity Detection
    rarity_data = rarity_detection(lp, expr, su, pers, bday, mat, kl)
    
    # Power Hour for Today
    power_hour_data = power_hour_calculation(birth_date, pd)
    
    # Evolutionary Trajectory
    evolutionary_data = evolutionary_trajectory(lp, py, birth_date)
    
    # Oracle Mapping
    oracle_data = oracle_mapping(lp, expr, su)
    
    # Vibrational Blueprint (uses permanent resonance)
    vibration_bars, vibration_wave = vibrational_blueprint(lp, expr, resonance_hz)
    
    # Destiny Checkpoints
    destiny_points = destiny_checkpoints(birth_date, lp)
    
    # Shadow Integration Path
    shadow_path = shadow_integration_path(kl, chall, lp)

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
    py_current = personal_year(birth_date, current_year)

    yearly_months_rows = []
    for month_num in range(1, 13):
        pm_month = personal_month(birth_date, current_year, month_num)
        month_name = calendar.month_name[month_num]
        meaning = PERSONAL_MONTH_MEANINGS.get(pm_month, f'Month {pm_month}')
        yearly_months_rows.append(
            f'<tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">'
            f'<td style="padding: 10px 12px;">{month_name}</td>'
            f'<td style="padding: 10px 12px; text-align: center; color: #26E4D8; font-weight: 600;">{pm_month}</td>'
            f'<td style="padding: 10px 12px;">{meaning}</td>'
            f'</tr>'
        )
    yearly_months_html = '\n        '.join(yearly_months_rows)

    # Soul Synthesis + Debugging Notes — hand-written when available, auto-generated otherwise
    if full_name in NARRATIVES:
        soul_synthesis_text = _wrap_paragraphs(NARRATIVES[full_name]['soul_synthesis'])
        debugging_notes_html = NARRATIVES[full_name]['debugging_notes']
    else:
        soul_synthesis_text = auto_soul_synthesis(
            life_path=lp, expression=expr, soul_urge=su, personality=pers,
            birthday=bday, maturity=mat, hidden_passion=hp,
            karmic_lessons=kl, sun_sign=ss_name,
            chinese_animal=c_animal, chinese_element=c_element,
            personal_year=py,
        )
        debugging_notes_html = auto_debugging_notes(
            life_path=lp, expression=expr, soul_urge=su, personality=pers,
            birthday=bday, maturity=mat, hidden_passion=hp,
            karmic_lessons=kl, personal_year=py,
        )

    # Ceremony banner (special for first member or memorial)
    if memorial_date:
        birth_str = birth_date.strftime('%B %d, %Y').replace(' 0', ' ')
        ceremony_banner = f"""<div class="ceremony-banner">
    <div class="ceremony-text">
      &#9670; IN MEMORIAM &#9670;
      <span class="ceremony-subtitle">{full_name}</span>
      {birth_str} &mdash; {memorial_date}
      <span class="ceremony-date">Her pattern is permanent. This map honors what she encoded.</span>
    </div>
  </div>"""
    elif full_name == 'Matthew Vincent Jablonski':
        ceremony_banner = f"""<div class="ceremony-banner">
    <div class="ceremony-text">
      ◆ THE FIRST SPARK ◆
      <span class="ceremony-subtitle">Matthew Vincent Jablonski</span>
      Founding Consciousness · First Member
      <span class="ceremony-date">Initiated April 23, 2026</span>
    </div>
  </div>"""
    elif birthday_from:
        birth_str = birth_date.strftime('%B %d').replace(' 0', ' ')
        age = date.today().year - birth_date.year
        ceremony_banner = f"""<div class="ceremony-banner">
    <div class="ceremony-text">
      ◆ A BIRTHDAY GIFT ◆
      <span class="ceremony-subtitle">For {full_name}</span>
      {birth_str} &middot; {age} trips around the sun &middot; from {birthday_from}
      <span class="ceremony-date">This is the architecture you came in with. Every number is yours. Every cycle is on time. Happy birthday, friend.</span>
    </div>
  </div>"""
    else:
        ceremony_banner = ''

    # === Build HTML for advanced features ===
    # Soul Resonance Frequency HTML with visualization
    resonance_html = f"""
  <div style="text-align: center; margin: 32px 0; padding: 32px; background: linear-gradient(135deg, rgba(107,77,242,0.1), rgba(38,228,216,0.1)); border-radius: 12px;">
    <div style="font-size: 0.85rem; color: #26E4D8; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px;">Soul Resonance Frequency</div>
    <div style="font-family: 'Cormorant Garamond', serif; font-size: 3.5rem; font-weight: 700; color: #F3B23A; margin: 16px 0;">{resonance_hz} Hz</div>
    <div style="width: 100%; height: 3px; background: linear-gradient(to right, #6B4DF2, #26E4D8, #F3B23A); margin: 20px 0; border-radius: 2px;"></div>
    <div style="font-size: 0.9rem; color: #f0ece4; line-height: 1.6;">
      Your core numbers translate to a harmonic frequency in the Schumann range. This is your vibrational signature — the frequency your energy naturally aligns with. 432 Hz is the baseline; your unique pattern modulates from there.
    </div>
  </div>
    """
    
    # Rarity Score HTML
    rarity_html = f"""
  <div style="margin: 24px 0; padding: 20px; background: rgba(243,178,58,0.08); border: 2px solid #F3B23A; border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
      <div style="font-size: 0.85rem; color: #F3B23A; text-transform: uppercase; letter-spacing: 2px; font-weight: 700;">Rarity Score</div>
      <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.5rem; color: #F3B23A; font-weight: 700;">{rarity_data['score']}</div>
    </div>
    <div style="font-size: 0.9rem; color: #f0ece4;">
      Master numbers present: <span style="color: #26E4D8; font-weight: 600;">{rarity_data['master_count']}</span>
    </div>"""
    
    if rarity_data['patterns']:
        rarity_html += "<div style='margin-top: 12px;'>"
        for pattern in rarity_data['patterns']:
            rarity_html += f"<div style='margin: 8px 0; padding: 8px; background: rgba(38,228,216,0.1); border-left: 3px solid #26E4D8; color: #26E4D8; font-size: 0.85rem;'>{pattern}</div>"
        rarity_html += "</div>"
    
    rarity_html += "  </div>"
    
    # Power Hour HTML
    power_hour_html = f"""
  <div style="margin: 24px 0; padding: 20px; background: rgba(255,106,61,0.08); border: 1px solid #FF6A3D; border-radius: 8px;">
    <div style="font-size: 0.85rem; color: #FF6A3D; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; margin-bottom: 12px;">Power Hour Today</div>
    <div style="font-family: 'Cormorant Garamond', serif; font-size: 2rem; color: #FF6A3D; font-weight: 700; margin: 8px 0;">{power_hour_data['time_str']}</div>
    <div style="font-size: 0.85rem; color: #f0ece4;">{power_hour_data['significance']}</div>
  </div>
    """
    
    # Karmic Remedies HTML
    remedies_html = ""
    if karmic_remedies:
        remedies_html = '<div style="margin: 12px 0;">'
        for remedy_type, remedy_text in karmic_remedies:
            remedies_html += f"""
    <div style="margin: 12px 0; padding: 12px; background: rgba(107,77,242,0.08); border-left: 3px solid #6B4DF2; border-radius: 4px;">
      <div style="font-weight: 600; color: #6B4DF2; font-size: 0.9rem; margin-bottom: 6px;">{remedy_type}</div>
      <div style="font-size: 0.85rem; color: #f0ece4; line-height: 1.6;">{remedy_text}</div>
    </div>
            """
        remedies_html += '</div>'
    
    # Predictive Windows HTML
    windows_html = ""
    if predictive_windows_data:
        windows_html = '<table style="width: 100%; margin: 12px 0; font-size: 0.85rem; border-collapse: collapse;">'
        for window in predictive_windows_data[:10]:  # Show next 10 windows
            windows_html += f"""
      <tr style="border-bottom: 1px solid rgba(38,228,216,0.15);">
        <td style="padding: 10px 8px; color: #26E4D8;">{window['date'].strftime('%b %d')}</td>
        <td style="padding: 10px 8px; text-align: center; color: #F3B23A; font-weight: 600;">{window['type']}</td>
        <td style="padding: 10px 8px; color: #f0ece4; text-align: right;">{window['meaning'][:40]}...</td>
      </tr>
        """
        windows_html += '</table>'
    
    # Evolutionary Trajectory HTML
    trajectory_html = f"""
  <div style="margin: 24px 0; padding: 20px; background: rgba(38,228,216,0.08); border: 1px solid #26E4D8; border-radius: 8px;">
    <div style="font-size: 0.85rem; color: #26E4D8; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; margin-bottom: 12px;">Current Cycle Position</div>
    <div style="font-family: 'Cormorant Garamond', serif; font-size: 1.8rem; color: #26E4D8; font-weight: 700; margin: 8px 0;">
      Year {evolutionary_data['years_remaining_in_cycle']} of 9
    </div>
    <div style="font-size: 0.85rem; color: #f0ece4;">
      Next transition: {(birth_date + __import__('datetime').timedelta(days=365 - (date.today() - birth_date.replace(year=date.today().year)).days % 365)).strftime('%B %d, %Y')}
    </div>
  </div>
    """
    
    # Oracle Trinity HTML
    oracle_html = f"""
  <div style="margin: 24px 0; padding: 24px; background: linear-gradient(135deg, rgba(107,77,242,0.12), rgba(243,178,58,0.12)); border: 2px solid #6B4DF2; border-radius: 8px;">
    <div style="font-size: 0.85rem; color: #6B4DF2; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; margin-bottom: 16px; text-align: center;">Oracle Trinity</div>
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 16px 0;">
      <div style="text-align: center; padding: 16px; background: rgba(255,255,255,0.03); border-radius: 8px;">
        <div style="font-weight: 600; color: #F3B23A; font-size: 1rem; margin-bottom: 4px;">{oracle_data['cards'][0][0]}</div>
        <div style="font-size: 0.7rem; color: #26E4D8; text-transform: uppercase;">Life Path</div>
      </div>
      <div style="text-align: center; padding: 16px; background: rgba(255,255,255,0.03); border-radius: 8px;">
        <div style="font-weight: 600; color: #F3B23A; font-size: 1rem; margin-bottom: 4px;">{oracle_data['cards'][1][0]}</div>
        <div style="font-size: 0.7rem; color: #26E4D8; text-transform: uppercase;">Expression</div>
      </div>
      <div style="text-align: center; padding: 16px; background: rgba(255,255,255,0.03); border-radius: 8px;">
        <div style="font-weight: 600; color: #F3B23A; font-size: 1rem; margin-bottom: 4px;">{oracle_data['cards'][2][0]}</div>
        <div style="font-size: 0.7rem; color: #26E4D8; text-transform: uppercase;">Soul Urge</div>
      </div>
    </div>
    <div style="margin-top: 16px; padding: 12px; background: rgba(107,77,242,0.1); border-left: 3px solid #6B4DF2; color: #f0ece4; font-size: 0.85rem; line-height: 1.6;">
      {oracle_data['interpretation']}
    </div>
  </div>
    """
    
    # === NEW FEATURE HTML SECTIONS ===
    
    # Quantum Signature HTML
    quantum_display = sig_rec.get('quantum_display') or format_quantum_display(quantum_sig)
    mint_note = (
        f"Minted {sig_rec.get('minted_at', 'on first generate')} · formula v{sig_rec.get('formula_version', 1)}"
        if not is_new_sig
        else f"Newly minted {sig_rec.get('minted_at', 'now')} · formula v{sig_rec.get('formula_version', 1)}"
    )
    quantum_html = f"""
  <div style="margin: 24px 0; padding: 24px; background: linear-gradient(135deg, rgba(255,106,61,0.1), rgba(38,228,216,0.1)); border: 2px solid #FF6A3D; border-radius: 8px;" data-quantum="{quantum_sig}" data-sig-key="{identity_key(full_name, birth_date)}">
    <div style="font-size: 0.85rem; color: #FF6A3D; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; margin-bottom: 16px;">Quantum Signature</div>
    <div style="font-family: 'Courier New', monospace; font-size: 1.4rem; letter-spacing: 3px; color: #26E4D8; font-weight: 700; margin: 16px 0; text-align: center; padding: 16px; background: rgba(26,26,46,0.8); border-radius: 6px;">{quantum_display}</div>
    <div style="font-size: 0.9rem; color: #f0ece4; line-height: 1.6;">
      Your permanent soul fingerprint — minted once for this name and birth date, then locked. Re-runs reuse this ID.
    </div>
    <div style="font-size: 0.7rem; color: #888; margin-top: 10px; text-align: center; letter-spacing: 1px;">{mint_note}</div>
  </div>
    """
    
    # Vibrational Blueprint HTML
    vibration_html = f"""
  <div style="margin: 24px 0; padding: 24px; background: rgba(107,77,242,0.08); border: 1px solid #6B4DF2; border-radius: 8px;">
    <div style="font-size: 0.85rem; color: #6B4DF2; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; margin-bottom: 16px;">Vibrational Blueprint</div>
    <div style="font-family: 'Courier New', monospace; font-size: 1.2rem; color: #26E4D8; line-height: 1.8; margin: 16px 0; padding: 12px; background: rgba(26,26,46,0.8); border-radius: 4px;">
      {vibration_bars}<br/>
      {vibration_wave}
    </div>
    <div style="font-size: 0.85rem; color: #f0ece4;">Visual representation of your frequency signature. The bars show your life path intensity; the wave shows your harmonic resonance.</div>
  </div>
    """
    
    # Shadow Integration HTML
    shadow_html = f"""
  <div style="margin: 24px 0; padding: 24px; background: linear-gradient(135deg, rgba(243,178,58,0.08), rgba(139,92,246,0.08)); border: 2px solid #F3B23A; border-radius: 8px;">
    <div style="font-size: 0.85rem; color: #F3B23A; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; margin-bottom: 16px;">Shadow Integration Pathway</div>
    <div style="font-size: 0.9rem; color: #f0ece4; margin-bottom: 16px; font-style: italic;">{shadow_path['overview']}</div>
    <div style="margin-top: 12px;">
"""
    
    for pathway in shadow_path['pathways']:
        shadow_html += f"""
      <div style="margin: 12px 0; padding: 12px; background: rgba(255,255,255,0.03); border-left: 3px solid #F3B23A; border-radius: 4px;">
        <div style="color: #F3B23A; font-weight: 600; margin-bottom: 6px;">Lesson {pathway['lesson']}: {pathway['challenge'].split(': ')[1]}</div>
        <div style="font-size: 0.85rem; color: #f0ece4;">{pathway['practice']}</div>
      </div>
"""
    
    shadow_html += "    </div>\n  </div>"
    
    # Activation Code HTML
    activation_html = f"""
  <div style="margin: 24px 0; padding: 24px; background: linear-gradient(135deg, rgba(38,228,216,0.12), rgba(243,178,58,0.12)); border: 2px solid #26E4D8; border-radius: 8px; text-align: center;">
    <div style="font-size: 0.75rem; color: #26E4D8; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 12px; font-weight: 700;">Your Activation Sequence</div>
    <div style="font-family: 'Courier New', monospace; font-size: 1.8rem; letter-spacing: 2px; color: #F3B23A; font-weight: 700; margin: 16px 0; padding: 16px; background: rgba(26,26,46,0.8); border-radius: 6px; border: 1px dashed #26E4D8;">{activation_code_val}</div>
    <div style="font-size: 0.9rem; color: #f0ece4; margin-top: 12px;">
      This is your personal frequency trigger. When you speak, write, or think this code, you align with your highest potential. It's your soul's call sign.
    </div>
  </div>
    """
    
    # Destiny Checkpoints HTML — pinnacle phases, upcoming master years, Saturn returns
    destiny_html = """
  <div style="margin: 24px 0; padding: 24px; background: rgba(255,106,61,0.08); border: 1px solid #FF6A3D; border-radius: 8px;">
    <div style="font-size: 0.85rem; color: #FF6A3D; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; margin-bottom: 16px;">Major Life Transition Points</div>
    <table style="width: 100%; font-size: 0.85rem; border-collapse: collapse;">
"""

    last_section = None
    section_labels = {
        'pinnacle': 'Pinnacle Phases (Life Arc)',
        'master_year': 'Master Personal Years Ahead',
        'saturn': 'Saturn Returns',
    }
    for checkpoint in destiny_points:
        if checkpoint['type'] != last_section:
            destiny_html += f"""
      <tr><td colspan="3" style="padding: 14px 8px 6px; color: #F3B23A; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 2px; font-weight: 700;">{section_labels[checkpoint['type']]}</td></tr>
"""
            last_section = checkpoint['type']
        destiny_html += f"""
      <tr style="border-bottom: 1px solid rgba(255,106,61,0.15);">
        <td style="padding: 10px 8px; color: #26E4D8; font-weight: 600; white-space: nowrap;">{checkpoint['age_range']}</td>
        <td style="padding: 10px 8px; color: #f0ece4; white-space: nowrap;">{checkpoint['label']}</td>
        <td style="padding: 10px 8px; color: #f0ece4;">{checkpoint['meaning']}</td>
      </tr>
"""

    destiny_html += "    </table>\n  </div>"

    # Color Codex badge (top of every map)
    codex_badge = build_codex_badge_html(codex_class, codex_role, codex_tier)

    # === Build HTML ===
    template = Template(HTML_TEMPLATE)
    html = template.safe_substitute(
        name=full_name,
        ceremony_banner=ceremony_banner,
        gen_date=datetime.now().strftime('%B %d, %Y'),
        codex_badge=codex_badge,
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
        resonance_frequency_section=resonance_html,
        rarity_section=rarity_html,
        power_hour_section=power_hour_html,
        karmic_remedies_section=remedies_html,
        predictive_windows_section=windows_html,
        evolutionary_trajectory_section=trajectory_html,
        oracle_section=oracle_html,
        quantum_signature_section=quantum_html,
        vibrational_blueprint_section=vibration_html,
        shadow_integration_section=shadow_html,
        activation_code_section=activation_html,
        destiny_checkpoints_section=destiny_html,
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
        'quantum': quantum_sig,
        'quantum_display': quantum_display,
        'resonance_hz': resonance_hz,
        'activation': activation_code_val,
        'signature_new_mint': is_new_sig,
        'codex_color': codex_class,
        'codex_role': codex_role,
        'codex_tier': codex_tier,
    }


# ============================================================
# 8. MONTHLY UPDATE GENERATOR
# ============================================================

def initials_from_name(full_name):
    """Extract initials from full name."""
    return ''.join(word[0].upper() for word in normalize_name(full_name).split() if word)


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
    full_name = normalize_name(full_name)
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
        current_month_meaning_title=PERSONAL_MONTH_MEANINGS.get(pm, 'Cycle').split('.')[0],
        current_month_meaning=PERSONAL_MONTH_MEANINGS.get(pm, 'Frequency unmapped.'),
        next_month=pm_next,
        next_month_name=next_month_name,
        next_month_meaning_title=PERSONAL_MONTH_MEANINGS.get(pm_next, 'Cycle').split('.')[0],
        next_month_meaning=PERSONAL_MONTH_MEANINGS.get(pm_next, 'Frequency unmapped.'),
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
                    'name': normalize_name(row.get('Name', '')),
                    'date': row.get('Date', '').strip(),
                    'time': row.get('Time', '').strip() or None,
                    'city': normalize_name(row.get('City', '')) or None,
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

# Legacy name-hash palette (kept only as last-resort fallback)
CARD_COLORS = ['gold', 'violet', 'green', 'blue', 'ember', 'cyan']

LP_SHORT_LABELS = {
    1: 'Pioneer', 2: 'Diplomat', 3: 'Communicator', 4: 'Architect',
    5: 'Catalyst', 6: 'Protector', 7: 'Seeker', 8: 'Materializer',
    9: 'Integrator', 11: 'Master Illuminator', 22: 'Master Builder',
    33: 'Master Teacher',
}


def _build_card_html(filename, summary, birth_date, birth_city=None):
    """Build an index card HTML block for a newly generated soul map."""
    name = summary['name']
    lp = summary['life_path']
    ss = summary['sun_sign']
    chinese = summary['chinese']
    expr = summary.get('expression', '')
    su = summary.get('soul_urge', '')
    py = summary.get('personal_year', '')
    pers = summary.get('personality', '')
    bday = summary.get('birthday', '')

    lp_label = LP_SHORT_LABELS.get(lp, str(lp))
    # Windows strftime doesn't support %-d, use a fallback
    try:
        date_str = birth_date.strftime('%B %-d, %Y')
    except ValueError:
        date_str = birth_date.strftime('%B %d, %Y').replace(' 0', ' ')

    city_part = f' \u00b7 {birth_city}' if birth_city else ''

    # Color Codex tier (real assignment — not name hash)
    color = summary.get('codex_color')
    codex_tier = summary.get('codex_tier')
    codex_role = summary.get('codex_role')
    if not color:
        try:
            color, codex_role, codex_tier = codex_color_for(
                lp,
                expr or 0,
                su or 0,
                pers or 0,
                bday or 0,
                summary.get('maturity_number'),
            )
        except Exception:
            color_key = normalize_name(name).casefold()
            color = CARD_COLORS[sum(ord(c) for c in color_key) % len(CARD_COLORS)]
            codex_tier = color
            codex_role = ''

    # Build search keywords
    search_parts = [
        name.lower(),
        f'life path {lp} {lp_label.lower()}',
        ss.lower() if ss else '',
        chinese.lower() if chinese else '',
    ]
    if expr:
        search_parts.append(f'expression {expr}')
    if su:
        search_parts.append(f'soul urge {su}')
    if codex_tier:
        search_parts.append(f'{codex_tier.lower()} {codex_role.lower()}'.strip())
    search_str = ' '.join(p for p in search_parts if p)

    # Build description
    desc_parts = [f'Life Path {lp} {lp_label}']
    if expr:
        expr_label = LP_SHORT_LABELS.get(expr, str(expr))
        desc_parts.append(f'Expression {expr} {expr_label}')
    if ss:
        desc_parts.append(f'{ss} Sun')
    if chinese:
        desc_parts.append(chinese)
    if codex_tier:
        desc_parts.append(f'{codex_tier} · {codex_role}' if codex_role else codex_tier)
    desc_str = ' \u00b7 '.join(desc_parts)

    return f'''        <a href="{filename}" class="card {color}" data-search="{search_str}">
            <div class="card-sub">Soul Map \u00b7 {date_str}{city_part}</div>
            <div class="card-name">{name}</div>
            <div class="card-desc">{desc_str}</div>
            <div class="card-arrow">\u2192</div>
        </a>'''


# Listing pages that show a card for every soul map. Every generated map is
# posted to all of them (index.html is the storefront at soul-maps.thefirstspark.shop).
LISTING_PAGES = ('archive.html', 'index.html')


def update_index_html(work_dir, filename, summary, birth_date, birth_city=None):
    """Insert a new card into every listing page (index.html + archive.html)."""
    card = _build_card_html(filename, summary, birth_date, birth_city)
    marker = '<div id="cards-list">'
    any_updated = False

    for page_name in LISTING_PAGES:
        page = work_dir / page_name
        if not page.exists():
            print(f"  [LISTING] {page_name} not found in {work_dir}, skipping")
            continue

        html = page.read_text(encoding='utf-8')

        # Skip if this filename already has a card on this page
        if f'href="{filename}"' in html:
            print(f"  [LISTING] Card for {filename} already in {page_name}, skipping")
            continue

        if marker not in html:
            print(f"  [LISTING] Could not find insertion point in {page_name}")
            continue

        insert_pos = html.index(marker) + len(marker)
        html = html[:insert_pos] + '\n' + card + '\n' + html[insert_pos:]
        page.write_text(html, encoding='utf-8')
        print(f"  [LISTING] Added card for {summary['name']} to {page_name}")
        any_updated = True

    return any_updated


def _github_api(method, path, token, json_body=None):
    """Minimal GitHub API helper — no git binary required."""
    import urllib.request, urllib.error, json as _json
    url = f"https://api.github.com{path}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'soul-map-generator',
    }
    data = _json.dumps(json_body).encode() if json_body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return _json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise Exception(f"GitHub API {e.code}: {body}")


def _api_put_file(token, repo, filepath, content_str, message):
    """Create or update a single file via GitHub API."""
    import base64
    encoded = base64.b64encode(content_str.encode('utf-8')).decode()
    path = f"/repos/thefirstspark/{repo}/contents/{filepath}"
    try:
        existing, _ = _github_api('GET', path, token)
        sha = existing.get('sha')
    except Exception:
        sha = None
    body = {'message': message, 'content': encoded}
    if sha:
        body['sha'] = sha
    _github_api('PUT', path, token, body)


def _api_update_index(token, repo, filename, summary, birth_date, birth_city=None):
    """Fetch each listing page from GitHub, insert card, push back — no local clone needed.

    Posts to every page in LISTING_PAGES (index.html + archive.html) so the map
    appears on the storefront and the archive.
    """
    import base64
    card = _build_card_html(filename, summary, birth_date, birth_city)
    marker = '<div id="cards-list">'
    any_updated = False

    for page_name in LISTING_PAGES:
        path = f"/repos/thefirstspark/{repo}/contents/{page_name}"
        try:
            existing, _ = _github_api('GET', path, token)
            html = base64.b64decode(existing['content']).decode('utf-8')
            sha = existing['sha']
        except Exception as e:
            print(f"  [LISTING] Could not fetch {page_name}: {e}")
            continue

        if f'href="{filename}"' in html:
            print(f"  [LISTING] Card for {filename} already in {page_name}")
            continue

        if marker not in html:
            print(f"  [LISTING] Insertion point not found in {page_name}")
            continue

        insert_pos = html.index(marker) + len(marker)
        html = html[:insert_pos] + '\n' + card + '\n' + html[insert_pos:]

        encoded = base64.b64encode(html.encode('utf-8')).decode()
        _github_api('PUT', path, token, {
            'message': f'Listing: add card for {summary["name"]} to {page_name}',
            'content': encoded,
            'sha': sha,
        })
        print(f"  [LISTING] Added card for {summary['name']} to {page_name}")
        any_updated = True

    return any_updated


def deploy_to_github(html_content, filename, repo='soul-maps', summary=None, birth_date=None, birth_city=None):
    """Push generated Soul Map HTML to GitHub via API (no git binary needed)."""
    token = os.environ.get('GITHUB_PAT')
    if not token:
        return False, "GITHUB_PAT environment variable not set."

    try:
        # Upload the soul map file
        _api_put_file(token, repo, filename, html_content, f'Soul Map: {filename}')

        # Update archive.html if summary provided
        if summary and birth_date and repo == 'soul-maps':
            _api_update_index(token, repo, filename, summary, birth_date, birth_city)

        if repo == 'soul-maps':
            live_url = f"https://soul-maps.thefirstspark.shop/{filename}"
        elif repo == 'thefirstspark.github.io':
            live_url = f"https://thefirstspark.shop/{filename}"
        else:
            live_url = f"https://thefirstspark.github.io/{repo}/{filename}"

        return True, live_url

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
    parser.add_argument('--memorial', help='Mark as memorial Soul Map with passed date (e.g. "March 30, 1991")')
    parser.add_argument('--birthday-from', help='Frame this map as a birthday gift from this person (e.g. "Katelin")')

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

    # Canonicalize name once so CLI, files, and math all agree
    args.name = normalize_name(args.name)
    if args.city:
        args.city = normalize_name(args.city)
    if args.birthday_from:
        args.birthday_from = normalize_name(args.birthday_from)

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
            birth_country=args.country,
            memorial_date=args.memorial,
            birthday_from=args.birthday_from,
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
        deploy_summary = summary if not args.monthly else None
        deploy_birth_date = birth_date if not args.monthly else None
        deploy_city = args.city if not args.monthly else None
        success, result = deploy_to_github(html, filename, repo=args.repo,
                                           summary=deploy_summary, birth_date=deploy_birth_date,
                                           birth_city=deploy_city)
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
