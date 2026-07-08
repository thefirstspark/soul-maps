/* ============================================================
   THE COLOR RESOLVER — v1.0 CANON (JS mirror of color_resolver.py)
   The First Spark — Numerology → Color Codex
   Must stay byte-for-byte logically identical to the Python.
   ============================================================ */

const BASE_TABLE = {
  1: 'Ember', 2: 'Rose', 3: 'Yellow', 4: 'Green', 5: 'Cyan',
  6: 'Rose', 7: 'Blue', 8: 'Red', 9: 'Silver',
  11: 'Purple', 22: 'Gold', 33: 'Gold',
};

const WEIGHTS = { lifePath: 100, expression: 30, soulUrge: 10, personality: 5 };

const TIER_NAMES = {
  Red: 'The Will', Ember: 'The Ignition', Yellow: 'The Joy',
  Green: 'The Field', Cyan: 'The Signal', Blue: 'The Mind',
  Purple: 'The Transformer', Gold: 'The Orchestrator',
  White: 'The All', Rose: 'The Bond', Silver: 'The Mirror',
};

function resolveColor(lifePath, expression, soulUrge, personality) {
  const core = { lifePath, expression, soulUrge, personality };
  for (const [pos, n] of Object.entries(core)) {
    if (!(n in BASE_TABLE)) throw new Error(`${pos}=${n} invalid; must be 1-9, 11, 22, or 33`);
  }
  const votes = {};
  for (const [pos, n] of Object.entries(core)) {
    const c = BASE_TABLE[n];
    votes[c] = (votes[c] || 0) + WEIGHTS[pos];
  }
  const primary = BASE_TABLE[lifePath];
  const others = Object.entries(votes).filter(([c]) => c !== primary);
  const isPure = others.length === 0;
  const undertone = isPure ? null : others.sort((a, b) => b[1] - a[1])[0][0];
  return {
    primary,
    primaryTier: TIER_NAMES[primary],
    undertone,
    undertoneTier: undertone ? TIER_NAMES[undertone] : null,
    isPure,
    votes,
    designation: isPure ? `Pure ${primary}` : `${primary} · ${undertone} undertone`,
  };
}

if (typeof module !== 'undefined') module.exports = { resolveColor, BASE_TABLE, WEIGHTS, TIER_NAMES };
