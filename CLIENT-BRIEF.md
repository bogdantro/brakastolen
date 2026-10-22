# CLIENT BRIEF – Brakastølen (Vaset i Valdres)

Research for the new website, done 20.10.2026 from the current website, Brønnøysundregistrene
(brreg.no), OpenStreetMap, Finn.no and web searches. Raw text of the old site: `docs/old-site/`.
Design reference for nav + hero: `docs/design-reference-hero.png`.

---

## 1. Business facts

| Fact | Value | Source |
|---|---|---|
| Brand | **Brakastølen** – "Vaset i Valdres" | website |
| Company (developer + landowner) | **Tranberg Utvikling AS** | website, brreg |
| Legal name | TRANBERG UTVIKLING AS | brreg |
| Org. number | **925 233 498** | brreg, privacy page |
| Type | Aksjeselskap (AS), not VAT-registered | brreg |
| Industry code | 68.120 Utvikling og salg av byggeprosjekter | brreg |
| Purpose | Investering i eiendom (kjøp, utvikling, salg, utleie) og verdipapirer | brreg |
| Founded | 09.06.2020 (registered 22.06.2020) | brreg |
| Daily manager / chair | **Haakon Bernhard Edland** (also sole board member) | brreg roles |
| Founder | Not public | – |
| Employees | Not registered in brreg | brreg |
| Phone | **482 58 000** (E.164 `+4748258000`) | website, brreg (mobil) |
| E-mail | **post@brakastolen.no** | website, brreg |
| Business address | Tranbergvegen 31, 2819 Gjøvik | brreg, privacy page |
| Postal address | Same as business address (no separate one registered) | brreg |
| The cabin area | Brakastølen, Brakastølvegen, 2960 Røn – Vaset, Vestre Slidre kommune, Innlandet | website, Finn |
| Coordinates | 60.9955 N, 8.9879 E (Vaset centre, OpenStreetMap) | OSM |
| Opening hours | None – viewings by appointment ("kontakt grunneier/utbygger") | website |
| Area served | Vaset, Vestre Slidre, Valdres | website |
| Services | Hyttetomter, nøkkelferdige hytter/hytteprosjekter (with partners) | website |
| Prices | Tomter fra 900 000 kr + omkostninger | website |
| Altitude | 900–1050 moh. (Finn ad says 950–1050) | website / Finn |
| Distances | ca. 18 km NW of Fagernes, ca. 200 km from Oslo | website |
| Accountant / auditor | Azets Insight AS / Unic Revisjon AS | brreg |
| Website made by | Svarthaug Media (svarthaug.com) – WordPress, Uncode theme | footer |
| Social media | **None found** (no Facebook, Instagram or Google Business profile) | searches |

**Source differences** (brreg wins):
- brreg lists the homepage as `www.brakastolen.no`; the site actually runs on **www.brakastølen.no**
  (`www.xn--brakastlen-6cb.no`), and `brakastolen.no` redirects there. Both domains go in `ALLOWED_HOSTS`.
- The old privacy page names Svarthaug Media as data processor and contact for privacy questions;
  the new privacy page uses the client's own e-mail instead (confirm).

**Related companies in brreg** (not used, for context): Brakastølen Invest AS (930 152 765, Oslo),
Brakastølen Vel (995 563 738), Brakastølen Øst Hyttegrend (989 852 531), Tranberg Panorama AS (Gjøvik).

---

## 2. Branding

### Logo
- `static/images/logo/logo-brakastolen-hvit.png` – 500×500 PNG, **white** mountain mark + "Brakastølen /
  Vaset i Valdres" on transparent. Only a white version exists on the site; **no SVG** found.
- `static/images/favicon/favicon-brakastolen-svart.png` – 512×512 black mountain mark (original).
  Generated from it: `favicon-32.png`, `favicon-192.png`, `apple-touch-icon.png` (cream background).
- The mark is three simple triangles – easy to redraw as SVG in the design phase (dark + light versions).

### Colours
From the **current site** (theme CSS):

| Role | Hex | Where |
|---|---|---|
| Page/footer background | `#002223` | deep teal – `body.custom-background`, nav, footer |
| Buttons | `#90AE8C` | sage green – `btn-color-200287` |
| Text on dark | `#FFFFFF` | |

From the **design reference** (`docs/design-reference-hero.png`, sampled):

| Role | Hex |
|---|---|
| Page background (cream) | `#F1EBDF` |
| Card background | `#EEE8DA` |
| Headings / text | `#141616` (hero H1 `#0D0C0B`) |
| Body text (muted) | `#5C5956` |
| Accent line (copper) | `#AC742C` |
| Script text | `#756353` |
| Nav glass | `#3D464D` at ~55 % over the photo |
| Light button | `#F6F3E9` |

**Decision:** the main colour is the current site's green. Mapped in `static/scss/global/_variables.scss`:
`$primaryColor #002223` (brand green), `$secondColor #001819` (footer), `$sage #90AE8C` / `$sageDeep #5E7D5A`
(accents, "i fjellet" in the hero), `$black #141616`, `$white #F6F3E9`, `$background #F1EBDF` (cream from the reference).
The copper from the reference image was replaced by sage.

### Fonts
- Current site: **Abhaya Libre** (headings, `font-840908`), **Poppins** (menu/UI). The theme also loads
  Droid Serif, Dosis, Playfair Display, Oswald, Roboto, Nunito and Open Sans (theme leftovers).
- Design reference: a high-contrast serif for headings/nav (closest Google Font: **Playfair Display**),
  a serif body and a handwritten script ("Mer enn et sted.").
- **Chosen** (matched to the design reference): **DM Serif Display** (headings, price), **Newsreader** (nav, body), **La Belle Aurore** (the one handwritten line).

### Style / feel
Current site: dark teal, full-width photos, Revolution/Layer sliders, one long one-pager with anchors.
Design reference: calm, editorial, Nordic luxury – cream paper, big serif type, golden-hour mountain
photos, thin copper rules, vertical labels, coordinates, a handwritten accent.

---

## 3. Downloaded images (`static/images/`)

All shrunk with `optimize_images` (max 2000 px, hero 2400 px, map 3200 px). Full-size originals are in
`originals/static-images/` (git-ignored).

| File | Content | Notes |
|---|---|---|
| `logo/logo-brakastolen-hvit.png` | White logo | only version on site |
| `favicon/favicon-brakastolen-svart.png` (+ 32/192/apple) | Black mountain mark | |
| `hero/hero-1-tranberg-utvikling-vaset.jpg` | Aerial of Brakastølen/Vaset, summer | orig. 5272×3948 "Tranberg-Utvikling-Vaset-Haakon-Edland" – photographer likely Haakon Edland |
| `projects/tinde-vaset-3939/3992/4030.jpg` | Tinde cabin interiors at Vaset | "Foto: Pål Harald Uthus, Uthus Photography" |
| `projects/tinde-hytte-01…09-<id>.jpg` | Grass-roof cabin, ext. + interior | in the Tinde section; see uncertainties |
| `projects/leve-hytter-vy-overblikk.jpg` | Leve Vy cabin in winter | file name says www.mir.no (render) |
| `projects/leve-hytter-interior.jpg`, `-interior-hellerud.jpg`, `-ildsted-hellerud.jpg` | Leve interiors | supplier photos |
| `projects/leve-hytte-utsikt-til-syndin.jpg` | View to lake Syndin from a Leve cabin | |
| `projects/leve-hytter-lyivy.jpg` | Leve cabin, winter evening | only 400×226 |
| `misc/langrenn-vaset.jpg` | Cross-country trails | |
| `misc/kiting-pa-vaset.jpg` | Snow kiting | |
| `misc/tomtekart-2022-02-01.png` | **Plot map** with legend (see §6) | palette-compressed, still sharp |
| `misc/annonse-2024-07-05.png`, `misc/annonse-2023-07-samarbeidspartnere.png` | Print ads | contain text – not for hero use |
| `misc/rsz-ext-ra106.jpg` | Rendered cabin in snow | from a theme demo page; origin unknown |
| `blog/reguleringsplan.png`, `blog/hogst.jpg` | Featured images of 2 old posts | |
| `og/og-default.jpg` | 1200×630 share image (from hero) | generated |
| `team/` | – | no people photos on the site |

Skipped: theme icons, gravatar, theme demo/portfolio images, the Finn listing's photos (broker's copyright).

---

## 4. Page map (old URL → new URL)

All old URLs come from the WordPress sitemaps (`docs/old-site/sitemap-urls.txt`). Redirects are
permanent (301) in `config/urls.py` and tested in `RedirectTests`.

| Old URL | New URL | Why |
|---|---|---|
| `/` | `/` | |
| `/#tomter` | `/tomter/` | one-pager anchor (anchors never reach the server – linked in nav) |
| `/#hytter` | `/hytter/` | anchor |
| `/#vaset` | `/aktiviteter/` (+ `/om-vaset/`) | anchor |
| `/#nyheter` | `/nyheter/` | anchor |
| `/#kontakt` | `/kontakt/` | anchor |
| `/oversiktskart/` | `/tomter/` (map at `#tomtekart`) | 301 |
| `/vare-finn-annonser/` | `/hytter/` | 301 |
| `/personvernerklaering/` | `/personvern/` | 301 |
| `/reguleringsplan-vedtatt/` | `/nyheter/` | 301 – post is a draft until it gets real text |
| `/skogsavvirkning-pabegynt/` | `/nyheter/` | 301 – same |
| `/baerar-i-ar/` | `/nyheter/` | 301 – same |
| `/category/ukategorisert/`, `/author/webmaster/`, `/feed/` | `/nyheter/` | 301 |
| `/wp-sitemap.xml`, `/wp-sitemap-*.xml` | `/sitemap.xml` | 301 |
| `/portfolio/<demo>/` (16 pages), `/portfolio_cat/<x>/` (5) | `/hytter/` | theme demo leftovers |
| `/classic-help-center/`, `/page-404-custom/`, `/page_category/classic/` | `/` | theme demo leftovers |

New pages: `/tomter/`, `/hytter/` (the cabin suppliers, as on the old site), `/om-vaset/`,
`/aktiviteter/`, `/om-oss/`, `/nyheter/` (+ `/nyheter/<id>/<slug>/`), `/kontakt/`, `/personvern/`,
plus `/sitemap.xml`, `/robots.txt`, `/llms.txt`, `/llms-full.txt`, `/dashboard/`.

---

## 5. Content per page (old site)

The old site is a one-pager. Full extracted text: `docs/old-site/forside.txt`.

### Hero / slider
Slider images load via JavaScript (Slider Revolution) and could not be read. Hero text in the design
reference: "Din plass i fjellet." / "Brakastølen, Vaset · Valdres" / "Storslått natur. Egen hyttedrøm.
Noen steder føles bare riktige." / "Se ledige tomter" / "Tomter fra 900 000 kr + omk." /
"Mer enn et sted." / "Fjell · Natur · Frihet · Hele året" / "Sol fra morgen til kveld".

### Tomter
> KAMPANJE – DE SOM KJØPER HYTTETOMT NÅ, FÅR MED 2 GRATIS EL-SYKLER TIL EN VERDI PÅ CA KR. 60.000.
> EL-SYKLENE ER AV SAMME TYPE ELLER LIGNENDE SOM DE SOM ER KÅRET "BEST I TEST". SYKLENE LEVERES AV
> INTERSPORT PÅ VASET. VI HAR STORT UTVALG I FANTASTISKE TOMTER! ALLE TOMTENE HAR SPEKTAKULÆR UTSIKT I
> 180 GRADER, SAMT SOL FRA MORGEN TIL KVELD! DET ER IKKE BYGGEKLAUSUL PÅ TOMTENE.
>
> Visninger – for visning, kontakt grunneier/utbygger – 482 58 000
>
> Brakastølen – Vaset i Valdres ligger høyt og flott ved Panoramavegen mellom Valdres og Hemsedal.
> Området er en naturperle og byr på et flott og variert fjellterreng med et levende stølsmiljø,
> varierte aktiviteter, butikker og hyggelige serveringssteder. Her er det åpent og vilt landskap med
> flott utsyn mot den ville Jotunheimen.
>
> Nye prospekt – ta kontakt for prospekt på nye tomter og prosjekterte nøkkelferdige hytter.
> Tomtene i Brakastølen fordeler seg på mindre hyttegrender. Alle tomtene ligger på 900–1050 m.o.h. med
> fantastisk utsikt og unike solforhold fra morgen til kveld. Det er ingen byggeklausul på tomtene, men vi
> bistår gjerne med et nøkkelferdig hytteprosjekt, hvis det er ønskelig. Tomtene har pris fra kr. 900.000 + omk.
>
> Vil du oppfylle din hyttedrøm? Ta kontakt for en personlig visning av Brakastølen.

### Hytter
> Prosjekterte hytter skreddersydd for den enkelte familie. På tomtene i Brakastølen kan man velge blant
> flere norske kvalitetsleverandører av hytter. Vi vil kunne levere nøkkelferdige hytteprosjekter sammen
> med våre utvalgte samarbeidspartnere. Dersom kunden har egne tegninger, så benytter vi lokalt
> byggemesterfirma til gjennomføringen. Det er bare for kunden å velge seg ut tomt og hyttemodell, og vi
> vil ta oss av hele byggeprosessen frem til hytta står ferdig.
>
> **Tinde Hytter – stedet for dine beste stunder.** Tinde Hytter vet at det finnes like mange tinder som det
> er mennesker. Derfor har Tinde utviklet gode serier av kvalitetshytter – alle med hver sine særtrekk og
> egenskaper. Tinde bygger din hytte spesielt for deg og dine, slik blir den et sted der du kan dyrke de
> gode opplevelser i livet. (www.tindehytter.no) – Fotos: Pål Harald Uthus, Uthus Photography
>
> **Leve Hytter – tidløst design og solid håndverk.** Leve Hytter lager moderne kvalitetshytter med god
> arkitektur. Ei hytte skal vare i mange generasjoner. Derfor er Leve Hytter opptatt av at den skal
> fremstå som tidløs, i motsetning til gammaldags. Leve Hytter sin hytteserie heter Vy, og er utviklet i
> samarbeid med en av Norges fremste arkitekter. Den kommer i flere grunnmodeller og størrelser, med gode
> valgmuligheter. Du får ei gjennomtenkt hytte, akkurat tilpasset deg. (www.levehytter.no)

### Aktiviteter
> Vaset er et av de mest attraktive hytteområdene i Valdres og kan tilby spennende aktiviteter både sommer
> og vinter. Vaset ligger i Vestre Slidre kommune og grenser mot Hemsedal, ca. 18 km nord-vest for
> regionsenteret Fagernes og 200 km fra Oslo. Panoramavegen over til Hemsedal gjør tilgjengeligheten til
> Vaset god, også mot vest, samtidig som en kjøretur langs denne legendariske veien er en opplevelse i seg selv.
>
> **Alpint** – Vaset skiheiser har 9 nedfarter i ulike vanskelighetsgrader. Vaset er et flott alternativ
> for barnefamilier og de som vil øve seg på rails eller hopp.
>
> **Langrenn** – Løypenettet på Vaset er på ca. 120 kilometer, og prepareres av Vasetløypene SA. […] mulighet
> for å komme opp på fjellet «Syni» på 1137 moh. (full text in `aktiviteter.html`)
>
> **Sykkel** – Vaset ligger midt i et eldorado for syklister i alle aldre og på alle nivåer. […] Fra Gomobu
> finnes det flere titalls flotte og merkede sykkelløyper som passer for hele familien.

### Nyheter (front page)
> **Ulven hyttegrend** – Feltet ligger på oversiden av Brakastølen. Adkomsten er via Nye Øyevegen, og man
> følger videre Ulsetbekkvegen til feltet. Feltet ligger i enden på vegen og består kun av 10 tomter. Her
> er 9 av tomtene solgt pr i dag. Langrennssporet går rett forbi feltet. Kontakt oss for prospekt på feltet.
>
> **Våre samarbeidspartnere på Brakastølen** – Hytteleverandører: Tinde Hytter; FAUN Gruppen: Leve Hytter,
> Telemarkhytter, Øverbygg, Nordlyshytter, Familiehytta; Slidre Bygg & Prosjektering. Opparbeidelse av
> tomt og grunnmur – VA Entreprenør as. Planlegging av hytte på tomt – Plan og Oppmåling Valdres as.
> Finansiering – Sparebanken 1 Hallingdal Valdres. Oppgjørsmegler – EIE Fjellmegleren Fagernes.
> Byggesak – Vestre Slidre Kommune.

### Blog posts (WordPress, 30.06.2020)
"Reguleringsplan vedtatt", "Skogsavvirkning påbegynt", "Bærår i år?" – **title only, body is Lorem ipsum**.

### Kontakt
> Er du interessert i ei unik tomt, og/eller et hytteprosjekt på Brakastølen? Be om prospekt for de ulike
> tomte- og hytteområdene. Fyll ut skjemaet nedenfor. Eller du kan sende oss en epost på
> post@brakastolen.no. Du kan også ringe oss på tlf 482 58 000.

Old form fields: Navn*, Epost*, Telefon, "Jeg ønsker å bli kontaktet ang Brakastølen", Evt beskjed,
consent checkbox; protected by reCAPTCHA (Contact Form 7, sent by e-mail).

### Vår Finn-annonse (`/vare-finn-annonser/`)
One link: FINN 371502243 – "Innflyttingsklar LEVE familiehytte i vakre omgivelser". The ad is now
**sold**: Brakastølvegen 116, 2960 Røn, built 2023 by LEVE Hytter AS, 109 m² BRA-i, terrace 28 m²,
plot 2 053 m² (owned), 4 bedrooms / 5 rooms, energy C, asking price 5 350 000 kr, broker Ida Follinglo,
PrivatMegleren Valdres. Full text: `docs/old-site/finn-371502243-brakastolvegen-116.txt`.
Not seeded as a project (no photos we may use).

### Personvernerklæring
Full old text: `docs/old-site/personvernerklaering.txt`. The new `/personvern/` keeps its structure but
describes what the new site actually does (no reCAPTCHA, no Contact Form 7, inquiries stored in the dashboard).

### Testimonials / reviews / FAQ / team
None on the site. The FAQ in `seo.py` is built only from facts stated on the site.

---

## 6. Plot map legend (tomtekart per 01.02.2022)

| Activity | Plot numbers | Colour |
|---|---|---|
| Byggetrinn 1 | 1–34 | light blue |
| Byggetrinn 2 | 35–66 | light green |
| Byggetrinn 3 | 68–79 | dark green |
| Ulven Hyttegrend | T1–T9 + T32 | dark blue |
| Hytte bygges for salg | 18, 22, 23 | yellow |
| Tindes visningshytte | **19** | purple |
| Solgte prosjekt | 1–6, 8, 9, 10, 13, 28, T1–3, T6, T9, T32 | red |

This is 2022 data and conflicts with the newer front-page text (Ulven: 9 of 10 sold). **Not loaded** into
the plot table – the client should confirm current status per plot, then enter it in Dashboard → Tomter.

---

## 7. What was built from this

- `seo.py`: `BUSINESS`, `PARTNERS`, `FAQ` (7 questions, answers only from the client's own text).
- No project pages: like the old site, the cabin suppliers (Tinde Hytter, Leve Hytter) and partners are
  presented on `/hytter/` and on the homepage. `/prosjekter/…` URLs redirect there (301).
- Plots (`seed_plots`): the 54 plots on the old site's plot map, with size, price, sold status and outline.
- Seeded news (`seed_blog`): published – "Ulven hyttegrend", "Våre samarbeidspartnere på Brakastølen";
  drafts – "Kampanje: to gratis el-sykler med hyttetomta" (end date unknown) and the three old posts
  with only a title (original dates 30.06.2020 kept).

---

## 8. Missing or uncertain – ask the client

1. ~~**Current plot list**~~ – answered: the 54 plots on the old site's live plot map (size, price, sold) are loaded by `seed_plots`. Ask the client to confirm the categories (Byggetrinn 1: plots 11–34, Byggetrinn 2: 35–66, from the 2022 map).
2. **El-bike campaign**: still running? End date? (Seeded as a draft.)
3. **Text for the three old posts** (reguleringsplan, skogsavvirkning, bærår) – or delete them.
4. **Tinde photos** `tinde-hytte-01…09`: they sit in the Tinde section on the old site, and the map shows
   Tinde's show cabin on plot 19, but the photographer/cabin isn't stated. Confirm they show a Tinde cabin
   at Brakastølen and who took them (credit).
5. **Aerial hero photo**: the file name suggests Haakon Edland took it – confirm the photo credit.
6. **Logo as SVG**, and a dark version (only a white PNG exists).
7. **Hero slider photos** – the old slider loads its images by script; ask for the originals.
8. **Social media / Google Business profile** – none found. Worth creating a Google Business profile.
9. **Altitude**: site says 900–1050 moh., one Finn ad says 950–1050.
10. **Who should receive inquiry e-mails**, and the SMTP account to send them (set in `.env`).
11. **Hosting provider name** for the privacy page (data processor), and whether Svarthaug Media is still involved.
12. **Domain**: keep www.brakastølen.no as main (and redirect brakastolen.no), or switch? Email domain is brakastolen.no.
13. **Coordinates in the design reference** say "61.1°N 9.1°E" – Brakastølen is ≈ 61.0°N 9.0°E;
    the template uses "61,0° N · 9,0° Ø".
14. Typo in the design reference: "Mer ennet sted." → used **"Mer enn et sted."**
15. Analytics: does the client want Google Analytics? (Off until `GA_MEASUREMENT_ID` is set.)
16. **Supplier photos and texts on the homepage** («Våre hytteleverandører»): Telemarkhytter, Øverbygg,
    Nordlyshytter, Familiehytta, Slidre Bygg & Prosjektering and RH Kvalitetsbygg – texts written from
    their own websites, photos taken from those sites (22.10.2026, originals in `originals/suppliers/`).
    Confirm the partners are happy for their photos to be used, and that Nordlyshytter and Familiehytta
    are still in FAUN Gruppen and part of Brakastølen.
17. **What «+ omk.*» covers**: the asterisk is in place on every price; write the explanation in
    `PRICE_FOOTNOTE` in `apps/core/seo.py` and it shows under «Finn din plass på fjellet».
18. **Height, view and Finn link per plot**: the fields are in Dashboard → Tomter → a plot
    («Beliggenhet og annonse»); the old site has no per-plot values, so they start empty.
