# The site's design system ("the atlas")

Read this before changing anything under `web/`. The home page shows results only: the main question, the
seven sub-questions, how each is tested, what was seen. Process and progress live on the inner pages.

## The idea
A celestial atlas of one question. The worm's real 300-neuron wiring is the opening diagram; the seven
sub-questions are seven "spheres", each under a classical planet whose meaning fits it (Mercury the
messenger for the echo of a poke, Saturn the slow one for slow memory, and so on). The symbolism is a
visual layer only: all copy stays plain and exact.

## Rules
- **Every graphic is hairline vector (SVG).** No blur, no glow, no drop shadows, no raster charts.
- **Two prints of one sheet.** Home page: cyanotype negative (`assets/atlas.css`, blue ground, bone
  line work). Inner pages: positive (`assets/theme.css` over `site.css`, bone paper, blue ink, blue masthead).
- **Colour has jobs.** Brass is real animals; carmine is their artificial copies; a ring is a plain
  copy, a filled carmine mark is a copy given what it lacked. Bone/ink is text. Gilt (`--gilt`) is for
  ornament and emphasis only, never data. Both data pairs pass the colour-blind checks on their own
  ground: `#b68f1b` / `#e03063` on blue, `#8a6d12` / `#a90959` on paper. Do not swap them.
- **Type.** Cormorant for display, questions, numerals and home-page prose; Schibsted Grotesk for data,
  controls and captions; Newsreader only for long running text on inner pages. Chart text is never in a
  series colour: a small key mark beside the label carries identity.
- **Verdicts are shapes** (`#v-closed`, `#v-open`, `#v-none` in the sprite in `index.html`): a carmine
  ring over the brass disc, apart from it, or on both sides of it.
- **Motion is sparse**: the opening diagram, one reveal per figure, the seals' dials turning with scroll.
  Everything honours `prefers-reduced-motion`; the hero has a Pause control.
- No em dashes anywhere.

## Files
- `index.html`: the page, plus the SVG sprite of planet signs and verdict marks.
- `assets/atlas.css`: tokens and components, in page order.
- `assets/atlas.js`: the opening diagram, seals, emblems, the seven figures, the ledger, the great seal.
  Figures read `data/results.js` (exported by `scripts/export_site.py`) and `data/brain.js`.
- `assets/bench.js`: the watch-then-touch bench (simulated in the page; no recorded data).
- `assets/theme.css`, `assets/img/seal.svg`: the inner pages' print and masthead seal.
- `assets/charts.js`: inner-page figures (reads the theme's CSS variables).
- Unused since the redesign, kept until someone confirms removal: `assets/home.css`,
  `assets/showcase.js`, `assets/specimen.js`, `assets/img/fig-*.png`.

## Adding a result
Add a card to `.arcana`, a plate (`section.plate` with a seal, "How we asked", "What we saw", numbers, a
figure and a verdict), a row in the ledger (`ledger()` in `atlas.js`), and update the tally and the great
seal's count. Numbers come from committed result tables through `export_site.py`, never typed by hand
into a figure.
