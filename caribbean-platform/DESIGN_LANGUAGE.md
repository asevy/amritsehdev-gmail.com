# Design Language — Power with Elegance

> **Status: v1 draft (2026-09-09), from the founder's design direction.**
> Governs the site, the Intelligence interface, print and the physical
> award objects. Product examples below use [NAME] pending the naming
> round.

## The philosophy (write this into the brand guidelines)

> **We are not trying to look luxurious. We are trying to look
> important.**

Luxury brands become dated; institutions rarely do. The timelessness
test: if someone discovers the website in 2045, it should feel like it
could have been designed in 2027 or 2045.

The visual design itself should disappear. The stories, photography and
data are what people remember.

The positioning, by feeling: Forbes is *money*. AD is *beauty*.
Bloomberg is *information*. Monocle is *taste*. This publication is
**power with elegance** — the Financial Times married to Architectural
Digest, with the editorial confidence of Forbes and the narrative
richness of great long-form journalism. Not flashy. Not black-and-gold
"luxury." Not yacht-magazine aesthetics. When someone opens the
homepage, they should think: *"This feels expensive because it is
restrained."*

## Homepage — a daily intelligence briefing about Caribbean power

Not a newspaper. Not a magazine.

**Hero story.** One extraordinary image, large typography, no clutter:

> **The Family That Built Punta Cana**
> A fifty-year story of land, aviation, tourism and one of the
> Caribbean's great fortunes.
> *Continue reading.*

**Today's Intelligence.** A Bloomberg terminal — but beautiful. Very
minimal, tiny sparklines, not screaming:

```
WEALTH
▲ Corripio      +1.8%
▼ ANSA McAL     −0.9%

NEW FILING
Grupo Puntacana — Acquired…
```

**Latest stories.** Large image cards, almost magazine-like, narrative
headlines: *The Quiet Empire Behind Caribbean Banking · Why Jamaica's
Next Generation Is Different · Inside Nassau's Most Expensive Home · Who
Actually Owns This Resort? · The New Hotel Changing Barbados.*

**Rhythm:** story · data · story · story · market · story · photo essay ·
wealth mover · interview · ranking. Not endless clickbait.

**Navigation — extremely restrained, exactly six items:**

> WEALTH · BUSINESS · PROPERTY · LIFE · CULTURE · RANKINGS

## Page templates

**Family page — where we become Bloomberg.** Large portrait, small
country flag, estimated wealth, influence ranking, one sentence. Tabs:
Overview · Companies · Properties · Transactions · People · Timeline ·
News · Philanthropy · Methodology. Below: a beautifully written
narrative first — only then the data. Right column:

```
ESTIMATED WEALTH   US$2.7–3.2B
EVIDENCE           HIGH
VALUATION          MODERATE
LAST UPDATED       Sept 8
```

Then charts, timeline, relationship graph, companies.

**Company page — very Bloomberg, minimal.** Ownership · History · Latest
News · Transactions · Executives · Related Families · Financials ·
Properties · Timeline.

**Property page — where AD comes in.** Huge photography, white space,
minimal captions, beautiful typography. Then: ownership, developer,
architect, purchase history, value, construction timeline.

**Hotel page — a story, not a review.** No star rows, no amenity grids
up top. One cinematic photograph, then the story: who built it, who owns
it, why it matters, how much capital — golf, real estate, transactions,
awards, development timeline. Practical information last.

**Articles.** Narrative long-form per [HOUSE_STYLE.md](HOUSE_STYLE.md):
beautiful opening, history, characters, conflict — then ownership,
money, business.

## The signature feature — the relationship map

Every family, company, property and institution page carries an
**interactive relationship map**: family members, companies, hotels,
airports, foundations, golf courses, developers, architects, banks,
joint ventures, connected families. Click any node and continue
exploring.

Over time this becomes the thing people remember: not isolated articles
but **the living map of Caribbean capital** — the perfect expression of
the company's core idea, and the direct UI of the verified graph. Rules:

- The map renders **approved claims only** (verified graph, never the
  research layer); edges carry their as-of dates.
- Unknowns render honestly as unknowns — an unresolved intermediary shows
  as `unknown`, not as a guessed link.
- Restricted fields (residences, minors, security-relevant data) are
  never rendered, per [EDITORIAL_STANDARDS.md](EDITORIAL_STANDARDS.md).

## Typography

Spend money here. No trendy fonts. A classic serif — candidates: Canela,
Lyon, Tiempos, Freight — paired with a clean sans: Inter, Helvetica or
Graphik. Timeless over fashionable; license properly for web, app and
print.

## Photography — the most important design element

**No stock photos. Ever.** Original photography: portraits,
architecture, landscapes, aerials; old family archives, documents, maps,
historic photos. Museum quality throughout.

## Color

Almost monochrome: white, cream, warm gray, black, very dark green, deep
navy, perhaps one muted burgundy. **No gold. No gradients. No luxury
clichés.**

## Motion

Very subtle. Articles fade; charts animate; nothing slides around. No
carousels. No autoplay.

## The Intelligence interface

A separate product surface with no magazine feeling — almost Bloomberg,
very clean: search, filters, ownership graph, timeline, source
documents, downloads (PDF, Excel).

## Mobile

Reading a beautiful newspaper: one column, huge photos, elegant
typography.

## Award objects

Never cheesy. Engraved bronze, simple typography, museum quality:

> [NAME]
> Caribbean Hotel of the Year
> 2032

No stars. No ribbons. No flames. No gradients. (Scarcity rules in
[AWARDS_ECOSYSTEM.md](AWARDS_ECOSYSTEM.md) apply to the objects too.)
