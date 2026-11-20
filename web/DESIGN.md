# The site's design system ("the atlas")

Read this before changing anything under `web/`. The home page shows results only: the main question, the
seven sub-questions, how each is tested, what was seen. Process and progress live on the inner pages.

## The idea
A celestial atlas of one question, staged as a scroll-driven showcase. One fixed scene (`assets/sky.js`)
lives behind the whole page, made of the worm's 279 connected neurons. The same 279 points are every
figure: the living worm in a glass body (real wiring, signals running down its nerve cord), the layered
artificial network it can be turned into, an orrery of the seven questions, a balance, each question's
planet as a lit globe, and the seven-pointed star for the answer. Between figures the points drift as
stars. The seven sub-questions sit under the seven classical planets whose meaning fits them. The symbolism
is visual only: all copy stays plain and exact.

## Rules
- **A figure lives in a stage.** Every section that has a figure has an empty `.stage` box in its layout.
  The scene reads those boxes: a figure is drawn inside its stage and travels with it, so it can never lie
  over the words beside it. A figure is "in" by as much as its stage is in view; points leave their stars
  for it as the stage arrives and go back as it leaves. Line work appears only once the points have
  landed. The picture is a function of scroll position and the clock, with no remembered state beyond a
  little smoothing, so reloading mid-page, resizing and fast scrolling all agree. Do not add timed,
  one-shot transitions to the scene, and do not put a background over a stage (it would dim the figure).
- **Drawn, not default.** Every graphic is made for its subject. Data figures are engraved plates: hairline
  rules with graduated ticks, serif numerals, notes written on the figure beside what they describe (no
  side legends), and marks that are small lights (`mark.real`, `mark.ring`, `mark.full` in `atlas.js`;
  their gradients are in the sprite at the top of `index.html`). Where a subject suggests a form, use it:
  The Inner Light is a sun on the horizon with one ray per mouse; The Waning is moons.
- **Depth and light, never fuzz.** The scene and the small instruments are canvases drawn at the screen's
  own pixel density; charts are SVG; nothing is a bitmap.
- **Openings and panels.** Each section starts with an opening (`.open`: words on one side, the stage on
  the other) and then holds its reading in a panel (`.panel`).
- **Two prints.** Home page: deep night ground with light (`assets/atlas.css`; the cinematic layer near
  the end overrides the earlier print). Inner pages: bone paper, blue ink, night masthead
  (`assets/theme.css` over `site.css`).
- **Colour has jobs.** Gold/brass is real animals (their spread is drawn as brass hatching, `url(#hatch)`);
  carmine is their artificial copies; a ring is a plain copy, a filled carmine mark is a copy given what
  it lacked. Data pairs pass the colour-blind checks: `#b68f1b` / `#e03063` on the dark ground,
  `#8a6d12` / `#a90959` on paper; the lit marks shade from those toward a bright centre, and are always
  told apart by shape as well (filled, ring, hatching). Planets shine in their metals (emblems, not data).
- **Type.** Cormorant for display, questions, numerals and home-page prose; Schibsted Grotesk for data,
  controls and captions; Newsreader only for long running text on inner pages. Chart text is never in a
  series colour: a small key mark beside the label carries identity.
- **Verdicts are shapes** (`#v-closed`, `#v-open`, `#v-none` in the sprite in `index.html`).
- **The old order.** The orrery's spheres run Moon, Mercury, Venus, Sun, Mars, Jupiter, Saturn from the
  centre out. The star of seven (in the sky and on the great seal) has the planets round its circle in
  that order reversed, so its lines join them in the order of the days of the week.
- **Motion**: the scene, words rising (`.kin`), numbers counting, cards tilting, marks springing in, the
  three small instruments. All of it honours `prefers-reduced-motion`; the scene lowers its own resolution
  on slow machines.
- No em dashes anywhere.

## Files
- `index.html`: the page, plus the SVG sprite: planet signs, verdict marks, and the gradients and hatching
  the marks and small planets use.
- `assets/atlas.css`: tokens and components, in page order.
- `assets/sky.js`: the scene behind the page (reads `data/wiring.js`). A section chooses its figure with
  `data-sky="..."` (`hero`, `orrery`, `balance`, a planet name, `star`) and gives it room with a `.stage`.
  `window.NEMATICA_SKY` lets the deck light a sphere of the orrery and hear which sphere the pointer is on.
- `assets/atlas.js`: seals (on a card the seal holds its planet in small), the seven figures, the ledger,
  the great seal, and the page's small behaviours. Figures read `data/results.js` (exported by
  `scripts/export_site.py`).
- `assets/emblems.js`: the three small living instruments under "How we ask".
- `assets/bench.js`: the watch-then-touch bench (simulated in the page; no recorded data).
- `assets/theme.css`, `assets/img/seal.svg`: the inner pages' print and masthead seal.
- `assets/charts.js`: inner-page figures (reads the theme's CSS variables).
- Unused since the redesign, kept until someone confirms removal: `assets/home.css`,
  `assets/showcase.js`, `assets/specimen.js`, `assets/img/fig-*.png`.

## Publishing
- Publish `web/` as it is in git: `.github/workflows/pages.yml` runs only when started by hand.
- Only files in git are published. `data/local.js`, `data/echo.js`, `data/brain.js`, `data/sim/` and
  `lab/data/` hold third-party recordings or positions and stay local, so `sim.html` and `lab/` work only
  when served locally; they are not linked from the published navigation.
- The scene uses `data/wiring.js` (committed): the Kunert et al. 2014 wiring (BSD 3-Clause) with schematic,
  anatomy-only positions. Rebuild with `python -I scripts/export_site.py`.
- `test/index.html` is the open test's static page (reference board, how to run it). When the site runs
  with its server (`web/serve.sh`), the live test is mounted at `/test/` instead.
- Social preview: `assets/img/og.jpg` (1200 x 630), referenced relatively; once the site has a domain,
  make `og:image` an absolute URL.
- To check what will be published: copy `git ls-files -co --exclude-standard web` to a folder, serve it,
  and look for 404s.

## Adding a result
Add a card to `.arcana` (its `.back` holds the headline number and one sentence, shown on hover), a plate
(`section.plate` with an `.open` holding the chapter header and a `.stage`, then a panel with "How we asked",
"What we saw", numbers, a figure and a verdict), a row in the ledger (`ledger()` in `atlas.js`), and update the tally and the great
seal's count. Numbers come from committed result tables through `export_site.py`, never typed by hand
into a figure.
