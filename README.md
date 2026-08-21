 Soul Map
The commercial surface of The First Spark canon. One product, one page, one screenshot.

$22 one-time · 12 monthly updates · 6-section arc · Whop checkout

"Reality is programmable. Consciousness is the code."


What this repo is
Everything that generates, renders, and ships a Soul Map. The canon (mythology, archetypes, color codex, numerology rules) lives upstream — this repo consumes canon, it never defines it. If code in here disagrees with the canon-freeze, the code is wrong.

Authoritative canon sources (do not fork values into this repo):

sparkverse-canon-freeze.html — the locked skeleton (§01–§06)
CANON-DECISION-LOG.md — every canon change and conflict resolution
Consolidated Master Document (v1.1) — current unified reference
The 6-section schema is a contract, not a guideline
Every generated map has exactly these six sections, in this order:

Signature
Core Numbers
The Signs
Your Pattern
This Year
The Verdict

This is enforced in soul_map_generator.py — the generator should fail loudly on any output that adds, removes, or reorders sections. Do not add sections to the base map. New section ideas go to /_lab or the paid "Deep Scan" tier. This rule exists because the product was deliberately recompiled from 25 sections down to 6; drift back toward 25 is the known failure mode.
Suggested layout
/

├── soul_map_generator.py    # Generator — enforces the 6-section schema

├── /templates               # Section templates (copy lives here, canon does not)

├── /data                    # Canon-derived lookup tables (archetypes, colors, numerology)

├── /_lab                    # Parked concepts, cut sections, Deep Scan candidates — never live

├── /archive                 # Example maps (Einstein, Tesla, Bowie, Tupac, etc.)

└── README.md

(Adjust to match reality — the load-bearing conventions are /_lab as the parking lot and the generator as the schema enforcer.)
Canon rules that bind this repo
These are the rules most likely to be broken by well-intentioned contributions:

Protocol order. Witness → Release → Select, always in that order — even in micro-copy. Never teach or imply Select first.
The roster is 12. Ember, Fracture, Wanderer, Maker, Cipher, Catalyst, Mirror, Conduit, Sovereign, Oracle, Trickster Nova, Phoenix Node. No 13th archetype, no 12th color, no filling empty matrix cells as new classes.
Mirror = RELEASE (Relational). Resolved in CDL-001. The old "discovered resonance / crossover" framing from the archetype wheel is deprecated — do not reuse it in any map copy.
Orthogonality. Color (amplitude) and Numerology (timing) are independent of archetype. A lookup table or template that makes one imply the other collapses the framework — never map a Color tier to an archetype.
Bridges are fixed. Conduit and Fracture only. Do not reassign.
Claims. Doctrine is architecture, not guaranteed outcome. Map copy frames metaphysical claims as practice, never as health/medical/"this will change your reality" promises.
Language. Approved: "Debugging Notes," "cursor," "render." Parked (do not use on live surfaces): "vibrational blueprint," "oracle trinity," "karmic remediation." Sales-surface copy must work without a glossary.
Contributing / shipping checklist
Before any template, copy, or generator change ships:

Run the Part Six content-owner questionnaire (see the Framework Audit) — classification, layer mapping, protocol check, archetype check, orthogonality check, product check, claim check, audience check, governance check.
Does it touch a locked value (§01–§06)? → It requires an unfreeze and a CANON-DECISION-LOG.md entry before the change lands here.
Does it add a section? → /_lab or Deep Scan. Not the base map. No exceptions.
Monthly-update content must be generated through the template system, not hand-edited — hand edits are how the generator and the canon drift apart.
Tag it: Canon / Lore / UX / Ritual / Marketing / _lab. Untagged content doesn't ship.
Product facts
Price: $22 one-time, includes 12 monthly updates ("This Year" is the recurring hook)
One CTA on the sales page
Checkout: Whop (Sparkverse community layer)
The Verdict is the shareable section — treat it as the screenshot



The First Spark Inc · thefirstspark.shop
