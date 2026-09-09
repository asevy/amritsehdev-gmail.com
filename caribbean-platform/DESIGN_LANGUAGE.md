# Design Language — Power with Elegance

> **Status: philosophy FROZEN (2026-09-09); identity deliberately open.**
> The principles below are settled. The exact typeface, the institutional
> color and the masthead treatment stay open until the name exists — and
> no screens get designed until the name and the first real family
> dataset exist. The first Mahfood or Goddard graph will tell us far more
> about what the interface needs than a fictional mockup will. Product
> examples use [NAME] pending the naming round.

## The philosophy (write this into the brand guidelines)

> **We are not trying to look luxurious. We are trying to look
> important.**

> **Beauty earns attention. Information earns trust. Restraint
> communicates authority.**

And the hierarchy that resolves almost every future design argument:

> Photography is emotional.
> Typography is institutional.
> Data is precise.
> Motion is functional.
> Decoration is almost nonexistent.

Luxury brands become dated; institutions rarely do. The timelessness
test: if someone discovers the website in 2045, it should feel like it
could have been designed in 2027 or 2045. The visual design itself should
disappear — the stories, photography and data are what people remember.

The positioning, by feeling: Forbes is *money*. AD is *beauty*.
Bloomberg is *information*. Monocle is *taste*. This publication is
**power with elegance** — the Financial Times married to Architectural
Digest, with the editorial confidence of Forbes and the narrative
richness of great long-form journalism. Not flashy. Not black-and-gold
"luxury." Not yacht-magazine aesthetics. *"This feels expensive because
it is restrained."*

## Homepage — alive today

A first-time visitor must understand within ten seconds: **this isn't a
beautiful quarterly magazine — this institution knows what happened to
Caribbean capital today.**

**Hero story.** One extraordinary image, large typography, no clutter:

> **The Family That Built Punta Cana**
> A fifty-year story of land, aviation, tourism and one of the
> Caribbean's great fortunes.

**Today's Intelligence — elevated, directly beneath the hero.** Very
restrained; no red CNBC ticker:

```
TODAY — SEPTEMBER 9

WEALTH      Corripio ↑ $42M
MARKETS     NCB Financial +3.1%
OWNERSHIP   New substantial-holder filing
DEAL        $180M resort financing closes
PROPERTY    Nassau record sale
PEOPLE      New CEO appointed
```

The juxtaposition is the distinctive move — a cinematic 3,000-word story,
then what changed in the last six hours. Neither Forbes nor AD gives you
that combination.

**Latest stories.** Large image cards, narrative headlines: *The Quiet
Empire Behind Caribbean Banking · Why Jamaica's Next Generation Is
Different · Inside Nassau's Most Expensive Home · Who Actually Owns This
Resort? · The New Hotel Changing Barbados.*

**Rhythm:** story · data · story · story · market · story · photo essay ·
wealth mover · interview · ranking. Not endless clickbait.

**Navigation — exactly six items:**

> WEALTH · BUSINESS · PROPERTY · LIFE · CULTURE · RANKINGS

## Page templates

**Family page — biography first, machine second.** The opening feels
almost biographical:

> **THE CORRIPIO FAMILY**
> DOMINICAN REPUBLIC · FAMILY BUSINESS · EST. 1930s
> *The empire behind some of the Dominican Republic's most familiar
> businesses.*
> [Extraordinary family/founder photograph]

Then 1,000–1,500 words of beautifully constructed narrative. Only after
the reader understands who these people are does the machine appear:

```
THE FORTUNE

Estimated wealth    $2.7–3.2 billion
Daily change        +$34 million   +1.1%
Evidence            HIGH
Live-priced         38%
Updated             14 minutes ago
```

Then holdings, the graph, transactions, methodology. Tabs: Overview ·
Companies · Properties · Transactions · People · Timeline · News ·
Philanthropy · Methodology.

**No flags as a visual language.** Country flags make a sophisticated
page look like a sports ranking, and Caribbean identity is complicated
(nationality, residence, origin, operating geography, diaspora). Use
beautifully typeset text — `DOMINICAN REPUBLIC · FAMILY BUSINESS · EST.
1930s`. Flags survive only as metadata/filter elements.

**Company page — very Bloomberg, minimal.** Ownership · History · Latest
News · Transactions · Executives · Related Families · Financials ·
Properties · Timeline.

**Property page — where AD comes in.** Huge photography, white space,
minimal captions. Then: ownership, developer, architect, purchase
history, value, construction timeline.

**Hotel page — a story, not a review.** One cinematic photograph, then:
who built it, who owns it, why it matters, how much capital — golf, real
estate, transactions, awards, development timeline. Practical
information last.

**Articles.** Narrative long-form per [HOUSE_STYLE.md](HOUSE_STYLE.md).

## The signature feature — the visual trademark

Every family, company, property and institution page carries the
interactive relationship map — and it is the thing people will remember:

```
                FAMILY
                  ↓ 72%
            HOLDING COMPANY
        ↙︎         ↓          ↘︎
      Bank    Hotel Group   Land Co.
                  ↓
                Resort
                  ↕ JV
             OTHER FAMILY
```

Click the other family and you're somewhere else. Click the hotel → the
developer → the architect → another project → the financing bank → the
bank's controlling family. Caribbean business history becomes
explorable; people will eventually spend forty minutes wandering the
graph. **After the masthead is chosen, this proprietary UI gets its own
name** — something with the weight of *The Map*, not "relationship map."

Rules: the map renders **approved claims only** (never the research
layer); edges carry their as-of dates; unknowns render honestly as
`unknown`; restricted fields (residences, minors, security-relevant
data) are never rendered, per
[EDITORIAL_STANDARDS.md](EDITORIAL_STANDARDS.md).

## Typography — explored, not picked from a list

Typography is institutional, so it deserves a commissioned exploration,
not a shortlist decision. Direction: classic serif + clean sans;
Lyon/Tiempos territory feels closer to *institution* than fashion — and
note that Canela, beautiful as it is, has become recognizable in
contemporary luxury branding, which conflicts with "important, not
luxurious." The masthead may ultimately deserve custom lettering. Decide
after the name exists.

## Photography — the most important design element

**No stock photos. Ever.** Original photography: portraits,
architecture, landscapes, aerials; old family archives, documents, maps,
historic photos. Museum quality throughout.

## Color — locked principle, open choice

Locked: **predominantly neutral + one institutional color.** No gold. No
gradients. No faux-luxury clichés.

Open: the institutional color itself is NOT chosen until the masthead
exists. FT has salmon; Bloomberg has black; The Economist owns red;
Tiffany owns blue — the name may tell us which unusual, restrained color
becomes unmistakably ours. (The dark green / navy / burgundy set used in
working documents is a provisional placeholder, not a decision.)

## Motion

Very subtle. Articles fade; charts animate; nothing slides around. No
carousels. No autoplay.

## The Intelligence interface — professional, never ugly

A separate product surface with no magazine feeling — but professional
does not mean plain. **Bloomberg's information density with Apple's
restraint:** the graph, tables and documents get exceptional typography
and spacing, so the professional product itself feels extraordinarily
valuable. Search, filters, ownership graph, timeline, source documents,
downloads (PDF, Excel).

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
