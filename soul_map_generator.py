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
    background: radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,0.3), transparent),
                radial-gradient(1px 1px at 80% 10%, rgba(255,255,255,0.2), transparent),
                radial-gradient(1.5px 1.5px at 50% 80%, rgba(107,77,242,0.4), transparent),
                radial-gradient(1px 1px at 10% 60%, rgba(38,228,216,0.3), transparent),
                radial-gradient(1px 1px at 90% 50%, rgba(243,178,58,0.2), transparent);
    pointer-events: none; z-index: 0;
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
</style>
</head>
<body>
<div class="stars"></div>
<div class="container">

  <p class="subtitle">Soul Map</p>
  <h1>${name}</h1>
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
  </div>

  <!-- ===== LIFE PATH READING ===== -->
  <h2>Life Path ${life_path} — The Signal</h2>
  <p class="reading">${life_path_reading}</p>

  <!-- ===== SELECTOR MODEL ===== -->
  <h2>Selector Model Layer</h2>
  <p style="margin-bottom: 12px;">
    <span class="selector-badge">${selector_layer}</span>
  </p>
  <p class="reading">${selector_desc}</p>

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
      <a href="https://whop.com/sparkverse/">Join the Sparkverse</a>
    </p>
  </div>

</div>
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


def generate_soul_map(full_name, birth_date, birth_time=None, birth_city=None, birth_country='US'):
    """Generate complete Soul Map data and return rendered HTML."""

    # === Numerology ===
    lp = life_path(birth_date)
    expr = expression_number(full_name)
    su = soul_urge_number(full_name)
    pers = personality_number(full_name)
    bday = birthday_number(birth_date)
    py = personal_year(birth_date)
    pm = personal_month(birth_date)

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

    # === Build HTML ===
    template = Template(HTML_TEMPLATE)
    html = template.safe_substitute(
        name=full_name,
        gen_date=datetime.now().strftime('%B %d, %Y'),
        life_path=lp,
        expression=expr,
        soul_urge=su,
        personality=pers,
        birthday_num=bday,
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
        'personal_year': py,
        'personal_month': pm,
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

    <a href="soul-map-${map_slug}.html" class="back-link">← Return to Full Soul Map</a>
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
        map_slug=full_name.lower().replace(' ', '-'),
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
# 9. GITHUB AUTO-DEPLOY
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
    parser.add_argument('--name', required=True, help='Full name')
    parser.add_argument('--date', required=True, help='Birth date (YYYY-MM-DD)')
    parser.add_argument('--time', help='Birth time (HH:MM, 24hr format)')
    parser.add_argument('--city', help='Birth city')
    parser.add_argument('--country', default='US', help='Birth country code (default: US)')
    parser.add_argument('--repo', default='soul-maps', help='GitHub repo to deploy to')
    parser.add_argument('--no-deploy', action='store_true', help='Generate only, skip GitHub push')
    parser.add_argument('--output', help='Local output path (optional)')
    parser.add_argument('--monthly', action='store_true', help='Generate monthly update instead of full soul map')
    parser.add_argument('--month', type=int, help='Month for monthly update (1-12, default: current)')
    parser.add_argument('--year', type=int, help='Year for monthly update (default: current)')

    args = parser.parse_args()

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

        # Filename
        slug = args.name.lower().replace(' ', '-')
        filename = f"soul-map-{slug}.html"

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
