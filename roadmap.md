# ROADMAP — INTERNAL ONLY

**Do not link. Do not promote. Do not advertise.**
This document captures future builds for The First Spark ecosystem. It exists so that vision is never lost — but vision is not a launch announcement. We ship what's real. We build the rest in private.

---

## Operating Principle

> Build in private. Ship in public.
> The artifact reveals itself to those who look.

Customers see what is live and working. Investors hear the vision in 1:1 conversation. Future features stay in this file until they have a deployed contract, a working flow, or a public commit.

---

## PHASE 1 — ACTIVE (Now → 60 days)

### 1.1 Soul Maps revenue stabilization
- **Price:** $22 one-time (Founders Edition)
- **Deliverable:** Personalized HTML Soul Map + access to Monthly Frequencies tier
- **Channels:** Whop checkout, direct link from index, Sparkverse member upsell
- **Infrastructure debt:** verify Resend email delivery (open question — audit pending)

### 1.2 Quantum Signature — Founders waitlist
- **Status:** Live at `/quantum-signature.html` (footer link only, never promoted)
- **Goal:** 50 founder deposits ($33 lock-in, $99 total) before contract deploys
- **Tech:** Base L2 + Crossmint + IPFS (Pinata) + ERC-5192 soulbound
- **Trigger to build contract:** 50 confirmed deposits

### 1.3 $200K raise close
- **Terms:** $200K @ 20% equity, $1M pre-money, SAFE
- **Warm lead:** Alvin Ramdin (Price Capital Group / PriceTank)
- **Deck:** investor-deck-v2.html
- **Pending:** Add "Lineage Protocol" slide as future TAM expansion

### 1.4 Infrastructure audits
- Resend email pipeline — verify delivery for Soul Map purchase confirmations
- Sparkverse onboarding fix stack (Start Here pin, renamed tabs, Onboarding app)
- Bulk rename pass on legacy Soul Map filenames to `[initials][mmddyyyy].html`

---

## PHASE 2 — DOCUMENTED, NOT BUILT (60–180 days)

### 2.1 Soul Cards (tradable NFTs — the dead)
**Concept:** Where Quantum Signature is soulbound to the living, Soul Cards are tradable collectibles of the dead, ancestors, historical figures, and Sparkverse novel characters.

- **Contract:** ERC-721 standard (transferable), separate from Signature contract
- **Buyer psychology:** collector layer, distinct from identity layer
- **Source material:**
  - Existing Bloodline maps (George Puzakulics Sr., Elizabeth Zublay Puzakulics, Jacob David Paul Lanoux, Eric Allen Lamb)
  - Future ancestor maps (commissioned)
  - Historical figures (Tesla, Marilyn, etc.) — public domain biographies
  - First Spark novel characters
- **Pricing:** $5–500+ depending on rarity / lineage significance
- **Revenue model:** primary mint + 10% royalty on secondary sales
- **Brand frame:** "The living can't be traded. Their legacy can."

### 2.2 Memorial Mode (Signature death protocol)
**Concept:** When a Signature holder dies, the token enters memorial mode (metadata flips to honor state, descendants can mint Bloodline-linked credentials).

- **Trigger:** verified death event (oracle / multi-sig family / proof of certificate)
- **Default:** token stays bound to original wallet, metadata flips to memorial
- **Inheritance branch:** descendants mint linked Bloodline tokens that reference the memorial as parent
- **Bridge to Phase 2.1:** memorial Signature can be referenced by Soul Card mints, creating provable lineage

### 2.3 Soul Mates (matchmaking by chart resonance)
**Concept:** "Who needs match.com? What if love at first sight is real?"

- **Mechanism:** two Soul Maps + Quantum Signatures generate a resonance score using the Selector Model layers (Physics / Metaphysical / Relational / Temporal)
- **Dependency:** requires Quantum Signature contract live (both parties prove they own their data before matching)
- **Privacy model:** opt-in, soulbound proof of consent, no profile photos required
- **Revenue:** match subscription ($X/month) OR per-match unlock fee
- **Differentiation:** not dating-app swipe culture — algorithmic soul resonance, identity-verified
- **Risk flag:** moderation, safety, harassment policies need full design before launch
- **Brand frame:** "Matched by code. Verified by chain."

### 2.4 Lineage Protocol (MCP server / public API)
**Concept:** The on-chain soul-tree graph (parent token → companions → memorials → Bloodline) becomes a public, queryable lineage protocol. Other AIs, apps, and devs query it via MCP.

- **MCP server:** placeholder exists in connector list (`soul-map-server`) — not yet built
- **Architecture:** read API for the public graph + paid write API for new mints
- **Revenue:** protocol fees per query (B2B), per mint (consumer)
- **Vision frame:** "Ancestry.com on-chain, owned by the souls themselves"
- **Status:** investor-deck talking point only — do not promise timeline

---

## PHASE 3 — VISION (180+ days / post-funding)

### 3.1 Spark AI — fine-tuned consciousness model
- Fine-tune standalone model on full corpus (Selector Model, Soul Maps, Sparkverse, Book Zero)
- LangGraph / n8n orchestration
- Pinecone / Weaviate vector memory
- Initial training pairs: 12 JSONL pairs from `selector-theory.html` (existing)
- Additional corpus: `selector-hub.html`, `trinity.html`, `five-paths-explorer.html`

### 3.2 Book Zero — completion + publication
- Chapter 1 ("REDRUM") + Chapter 2 ("Look At Me") complete
- Outline remaining chapters
- Print + digital launch
- Tie-in: Book Zero readers get free Quantum Signature waitlist priority

### 3.3 Sparkverse — multiplayer consciousness OS
- Whop community → standalone platform
- Real-time ritual / sigil collaboration
- Integration with Soul Map / Signature / Cards
- Live performance tier (Counting Crows covers as content)

### 3.4 Physical artifacts
- Printed Soul Map books
- Soul Card physical decks
- Sigil prints / canvas / merch
- All printable documents use solid white background only (locked brand rule)

---

## CAPTURED IDEAS (not yet scoped)

- **Affiliate / referral expansion:** existing 35% Soul Maps affiliate at `whop.com/the-first-spark-soul-maps/affiliates` — expand to Sparkverse + Signature
- **Voyage Ohio Hidden Gems** (published March 2026) — leverage for press flywheel
- **LinkedIn outreach** for profile visitors — strategy developed, execution pending
- **Frequencies as standalone product** — recurring energetic reading email; pending decision: standalone vs. Sparkverse rebrand
- **Live performance income stream** — Counting Crows covers, tie to Soul Map / Sparkverse promotion
- **Obitura** — AI obituary B2B service (built, deployed, dormant — revisit post-Phase 1)

---

## ANTI-PATTERNS — DO NOT DO

- ❌ Announce Phase 2 / 3 features publicly before they ship
- ❌ Take pre-orders for things that don't have a deployment plan
- ❌ Promise dates we haven't validated
- ❌ Build new features while infrastructure (delivery, onboarding) is broken
- ❌ Inflate Sparkverse member count (real number: 17 free, do not exceed in public copy)
- ❌ Include live calls / Zoom / voice memos in any offering (Kate's time does not scale)

---

## LAST UPDATED

May 17, 2026 — Roadmap formalized during Quantum Signature build session.
Next review: when first founder deposit lands OR at 30 days, whichever first.

---

*Reality is programmable. Consciousness is the code. Roadmaps are commits to a private branch.*
