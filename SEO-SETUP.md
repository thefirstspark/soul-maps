# Search Console & Sitemap Setup

Written 2026-08-27. Everything below marked **YOU** needs a Google/Bing login and
cannot be done from the repo.

## Sitemap URLs

| site | sitemap URL | status |
|---|---|---|
| Soul Maps | `https://soul-maps.thefirstspark.shop/sitemap.xml` | ✅ 22 URLs |
| The First Spark | `https://thefirstspark.shop/sitemap.xml` | ✅ 21 URLs, 0 dead |
| Sigilcraft | `https://sigilcraft.thefirstspark.shop/sitemap.xml` | ✅ 6 URLs |
| Sparkverse | `https://sparkverse.thefirstspark.shop/sitemap.xml` | ❌ **none — see warning** |
| raise | `https://raise.thefirstspark.shop/sitemap.xml` | ❌ **none — not deployed from any repo found** |

## YOU — Google Search Console

1. Go to https://search.google.com/search-console
2. **Add property** → choose **Domain** and enter `thefirstspark.shop`.
   A Domain property covers every subdomain at once (soul-maps, sigilcraft,
   sparkverse, raise, frequency) so you only verify once. The alternative,
   URL-prefix, needs a separate property per subdomain.
3. Verification: it will give you a **DNS TXT record**. Add it at whoever hosts
   your DNS for `thefirstspark.shop`. Propagation is usually minutes.
   - If you'd rather use an HTML file instead, paste me the token and I'll
     commit `google<token>.html` to whichever repo serves that subdomain.
4. Once verified → **Sitemaps** in the left nav → submit each URL from the table
   above, one at a time.
5. **URL Inspection** (top search bar) → paste `https://soul-maps.thefirstspark.shop/`
   → **Request indexing**. Do the same for `color-codex.html`. This nudges the
   first crawl instead of waiting.

Expect nothing for days, then partial coverage over 2–6 weeks. A new domain does
not rank quickly no matter what is submitted.

## YOU — Bing Webmaster Tools

1. https://www.bing.com/webmasters
2. There is an **Import from Google Search Console** button — use it, it copies
   the properties and verification across.
3. Submit the same sitemap URLs.

Worth doing: Bing's index feeds Copilot and ChatGPT search, which is a real
traffic source now and much less contested than Google.

## YOU — Links into the domain

Google has to find the site before it can rank it. Right now very little points
at `soul-maps.thefirstspark.shop`. Add a link from:

- your Whop store description / product pages
- `thefirstspark.shop` (the main site)
- your socials' bio links
- the Sparkverse member area

## ⚠️ Sparkverse — do not blanket-submit

The repo has **111 HTML files**, including `TFS-Investor-OneSheet.html`,
`The_First_Spark_Pitch_Deck_200K.html` and several other decks. A sitemap that
includes everything would hand your investor material to Google.

Before a Sparkverse sitemap exists, decide which pages are public. Then it can
be generated from that list only, with a `robots.txt` disallowing the rest.

## ⚠️ Person maps are deliberately excluded

`sitemap.xml` for Soul Maps lists only concept and commercial pages — never the
individual `INITIALS+MONTH+YEAR.html` maps. Those publish full names and exact
birth dates for private people, **including five minors** (born 2026, 2023,
2013, 2011, 2010 — one with birth time). They stay reachable by direct link,
which is how they're actually shared, but they are not advertised to crawlers.

`robots.txt` also has `Disallow: /media/` so family memorial photographs stay
out of image search. That is a crawler courtesy, not access control — the files
remain fetchable by direct URL, which is inherent to GitHub Pages on a public
repo.

## Regenerating the Soul Maps sitemap

There is no script yet; it was written by hand. If pages are added or removed,
the list lives in `sitemap.xml` and the rule is: concept and commercial pages
only, all eleven `<colour>-soul-journey.html` pages, no person maps.
