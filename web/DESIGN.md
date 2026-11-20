# The site's design system ("the atlas")

Read this before changing anything under `web/`. The home page shows results only: the main question, the
seven sub-questions, how each is tested, what was seen. Process and progress live on the inner pages.

## The idea
A celestial atlas of one question, staged as a scroll-driven showcase. One fixed scene (`assets/sky.js`)
lives behind the whole page. Its 300 points are the worm's 300 neurons. They open as the living worm
(real positions, real wiring, signals running), turn into a layered artificial network, and re-form for
every part of the page: the wiring ring behind the deck of seven cards, each question's planet sign in
that planet's metal, the seven-pointed star for the answer. The seven sub-questions sit under seven
classical planets whose meaning fits them. The symbolism is visual only: all copy stays plain and exact.

## Rules
- **Depth and light, never fuzz.** The scene is drawn at the screen's own pixel density with hard bright
  cores and soft halos; charts are SVG; nothing is a bitmap. No low-resolution canvases, no raster charts.
- **Openings and panels.** Each section starts with an opening that lets the scene show (`.chapter`,
  `.sec-head.opening`), then holds its reading in a panel (`.panel`) the scene dims behind.
- **Two prints.** Home page: deep night ground with light (`assets/atlas.css`; the cinematic layer is the
  last block and overrides the earlier one). Inner pages: bone paper, blue ink, night masthead
  (`assets/theme.css` over `site.css`).
- **Colour has jobs.** Gold/brass is real animals (their spread is drawn as brass hatching, `url(#hatch)`);
  carmine is their artificial copies; a ring is a plain copy, a filled carmine mark is a copy given what
  it lacked. Data pairs pass the colour-blind checks: `#b68f1b` / `#e03063` on the dark ground,
  `#8a6d12` / `#a90959` on paper. Planet signs shine in their metals (emblems, not data).
- **Type.** Cormorant for display, questions, numerals and home-page prose; Schibsted Grotesk for data,
  controls and captions; Newsreader only for long running text on inner pages. Chart text is never in a
  series colour: a small key mark beside the label carries identity.
- **Verdicts are shapes** (`#v-closed`, `#v-open`, `#v-none` in the sprite in `index.html`).
- **Motion**: the scene, words rising (`.kin`), numbers counting, cards tilting, marks springing in. All
  of it honours `prefers-reduced-motion`; the scene lowers its own resolution on slow machines.
- No em dashes anywhere.

## Files
- `index.html`: the page, plus the SVG sprite of planet signs and verdict marks.
- `assets/atlas.css`: tokens and components, in page order.
- `assets/sky.js`: the scene behind the page. A section chooses its figure with `data-sky="..."`
  (`hero`, `ring`, `wave`, a planet name, `star`, `scatter`).
- `assets/atlas.js`: the opening diagram, seals, emblems, the seven figures, the ledger, the great seal.
  Figures read `data/results.js` (exported by `scripts/export_site.py`) and `data/brain.js`.
- `assets/bench.js`: the watch-then-touch bench (simulated in the page; no recorded data).
- `assets/theme.css`, `assets/img/seal.svg`: the inner pages' print and masthead seal.
- `assets/charts.js`: inner-page figures (reads the theme's CSS variables).
- Unused since the redesign, kept until someone confirms removal: `assets/home.css`,
  `assets/showcase.js`, `assets/specimen.js`, `assets/img/fig-*.png`.

## Adding a result
Add a card to `.arcana` (its `.back` holds the headline number and one sentence, shown on hover), a plate (`section.plate` with a seal, "How we asked", "What we saw", numbers, a
figure and a verdict), a row in the ledger (`ledger()` in `atlas.js`), and update the tally and the great
seal's count. Numbers come from committed result tables through `export_site.py`, never typed by hand
into a figure.
