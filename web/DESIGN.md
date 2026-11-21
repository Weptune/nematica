# The site's design system ("the atlas")

Read this before changing anything under `web/`. The home page shows results only: the main question, the
seven sub-questions, how each is tested, what was seen. Process and progress live on the inner pages.

## The idea
A celestial atlas of one question, staged as a scroll-driven showcase. One fixed scene (`assets/sky.js`)
lives behind the whole page, made of the worm's 279 connected neurons. The same 279 points are every
figure: the living worm in a glass body with its anatomy (skin rings, pharynx, nerve ring, gut, the nerve
cord along the belly; real wiring, signals running down the cord), the layered artificial network it can
be turned into, an orrery of the seven questions, a brass balance with a small worm in one pan and a small
network in the other, each question's planet as a rendered globe whose night side carries the neurons as
lights, and the seven-pointed star for the answer. Between figures the points drift as stars, and a far
cloud moves slowly behind everything. The seven sub-questions sit under the seven classical planets whose meaning fits them. The symbolism
is visual only: all copy stays plain and exact.

## Rules
- **A figure lives in a stage.** Every section that has a figure has an empty `.stage` box in its layout.
  The scene reads those boxes: a figure is drawn inside its stage and travels with it, so it can never lie
  over the words beside it. A figure is "in" by as much as its stage is in view; points leave their stars
  for it as the stage arrives and go back as it leaves. Line work appears only once the points have
  landed. The picture is a function of scroll position and the clock, with no remembered state beyond a
  little smoothing, so reloading mid-page, resizing and fast scrolling all agree. Do not add timed,
  one-shot transitions to the scene, and do not put a background over a stage (it would dim the figure).
- **Rendered, not default.** Every graphic is made for its subject, and anything that stands for a body is
  rendered as one. The planets (in the scene, the orrery, the star, the cards, the great seal, the moons of
  The Waning and The Journey, the sun of The Inner Light) are painted by one WebGL shader (`assets/orbs.js`):
  surfaces from layered noise, a soft terminator, air, Saturn's rings with their shadows, a corona. The
  balance is polished, lathe-turned brass. Where WebGL is missing, drawn forms take over.
- **Plates are lit.** A data figure is an SVG of hairline scales with graduated ticks, serif numerals and
  notes written beside what they describe (no side legends), lying over a canvas of light
  (`assets/lumen.js`). The canvas holds the marks themselves (polished beads that throw a glow and glint
  now and then; a plain copy is a glass ring), the gold dust that fills the span between real animals, and
  light that moves where the result has a direction: it falls from what a copy predicted to what happened
  and the mark it lands on flares (The Push), rays stream from the sun (The Inner Light), embers leave a
  curve that is losing something (The Face), a slow swell passes along the marks of the slow drive (The
  Long Memory). `atlas.js` says where things are and what they mean; `lumen.js` only makes them shine, and
  without it `atlas.js` draws the marks itself (`mark.real`, `mark.ring`, `mark.full`, hatching). Motion on
  a plate must say something the caption says; do not add motion that decorates. Positions never move.
- **Depth and light, never fuzz.** Everything painted is painted at the screen's own pixel density. The
  only bitmaps are the rendered planets, made in the page at the size they are shown.
- **Openings and panels.** Each section starts with an opening (`.open`: words on one side, the stage on
  the other) and then holds its reading in a panel (`.panel`).
- **Two prints.** Home page: deep night ground with light (`assets/atlas.css`; the cinematic layer near
  the end overrides the earlier print). Inner pages: bone paper, blue ink, night masthead
  (`assets/theme.css` over `site.css`).
- **Colour has jobs.** Gold/brass is real animals (their spread is a band of gold dust between two brass
  lines; a pale mist is a spread that is not the yardstick, such as what light alone does); carmine is
  their artificial copies; a ring is a plain copy, a filled carmine mark is a copy given what it lacked.
  Data pairs pass the colour-blind checks: `#b68f1b` / `#e03063` on the dark ground, `#8a6d12` / `#a90959`
  on paper; the lit marks shade from those toward a bright centre, and are always told apart by shape as
  well (filled, ring, band). Planets are shown in their own colours (emblems, not data).
- **Type.** Cormorant for display, questions, numerals and home-page prose; Schibsted Grotesk for data,
  controls and captions; Newsreader only for long running text on inner pages. Chart text is never in a
  series colour: a small key mark beside the label carries identity.
- **No verdict labels.** The site does not sort questions into closed, open or anything else, and has no
  tally of them (the owner's decision, 21 Nov 2026: a public showcase states what was found). Each chapter
  opens with one plain line under its title and ends with one plain line and its limits; the ledger row says
  the same in a few words. Say what was seen and what the data cannot say, in ordinary sentences. On the
  great seal and the masthead seal every planet has the same gold ring.
- **The old order.** The orrery's spheres run Moon, Mercury, Venus, Sun, Mars, Jupiter, Saturn from the
  centre out. The star of seven (in the sky and on the great seal) has the planets round its circle in
  that order reversed, so its lines join them in the order of the days of the week.
- **Motion**: the scene, words rising (`.kin`), numbers counting, cards tilting, marks springing in and the
  light on the plates, the three small instruments. All of it honours `prefers-reduced-motion` (plates are
  then painted once, fully lit). On slow machines the scene first paints the planets at fewer pixels, then
  lowers its own resolution; it judges by average frame pace and ignores pauses. Measured on an integrated
  GPU (Radeon 660M), a planet at its largest costs 10 to 14 ms a frame.
- No em dashes anywhere.

## Files
- `index.html`: the page, plus the SVG sprite: planet signs, a small star, and the gradients and patterns
  the keys and the fallback marks use. Scripts load in this order: data, `orbs.js`, `sky.js`, `lumen.js`,
  `atlas.js`, `emblems.js`, `bench.js`. Each is cached by its `?v=` number: raise it when the file changes.
- `assets/atlas.css`: tokens and components, in page order.
- `assets/sky.js`: the scene behind the page (reads `data/wiring.js`). A section chooses its figure with
  `data-sky="..."` (`hero`, `orrery`, `balance`, a planet name, `star`) and gives it room with a `.stage`.
  `window.NEMATICA_SKY` lets the deck light a sphere of the orrery and hear which sphere the pointer is on.
- `assets/orbs.js`: the shader that renders the planets and the far cloud. `window.NEMATICA_ORBS` offers
  `draw` (into a 2D canvas, each frame), `sprite` (painted once) and `quality`. It is `null` without WebGL.
- `assets/lumen.js`: the canvas of light under each plate. `window.NEMATICA_LUMEN.layer(host, w, h)` gives
  `star`, `beam`, `band`, `arcBand`, `ribbon`, `shed`. One clock paints only the layers in view.
- `assets/atlas.js`: seals (on a card the seal holds its planet in small), the seven figures, the ledger,
  the great seal, and the page's small behaviours. Figures read `data/results.js` (exported by
  `scripts/export_site.py`).
- `assets/emblems.js`: the three small living instruments under "How we ask".
- `assets/bench.js`: the watch-then-touch bench (simulated in the page; no recorded data).
- `assets/theme.css`, `assets/img/seal.svg`: the inner pages' print and masthead seal (the seal embeds the
  seven rendered planets as small pictures; it is generated, not hand-edited).
- `assets/charts.js`: inner-page figures (reads the theme's CSS variables).
- The files left over from the earlier design (`assets/home.css`, `assets/showcase.js`,
  `assets/specimen.js`, two `assets/img/fig-*.png`) were removed on 21 Nov 2026 with the owner's say-so.
- The site is signed "Weptune", linking to weptune.dev, in every footer and in each page's author tag.

## Publishing
- The site is live at https://nematica.weptune.dev. `.github/workflows/pages.yml` publishes `web/` as it is
  in git on every push to `main` that changes `web/` (and can be started by hand). Anything pushed there
  goes live, so keep unfinished work on another branch.
- Only files in git are published. `data/local.js`, `data/echo.js`, `data/brain.js`, `data/sim/` and
  `lab/data/` hold third-party recordings or positions and stay local, so `sim.html` and `lab/` work only
  when served locally; they are not linked from the published navigation.
- The scene uses `data/wiring.js` (committed): the Kunert et al. 2014 wiring (BSD 3-Clause) with schematic,
  anatomy-only positions. Rebuild with `python -I scripts/export_site.py`.
- `test/index.html` is the open test's static page (reference board, how to run it). When the site runs
  with its server (`web/serve.sh`), the live test is mounted at `/test/` instead.
- The site's address is `https://nematica.weptune.dev` (a subdomain of the owner's own domain; its DNS is
  at Spaceship). It needs one DNS record, a CNAME from `nematica` to `weptune.github.io`, and the same
  name entered as the custom domain under the repository's Pages settings. No `CNAME` file is needed when
  Pages is fed by the workflow. The address is written into each page's `og:url`, canonical link and
  `og:image`, and into `robots.txt` and `sitemap.xml`: change all of them together if it ever moves.
- `404.html` uses paths from the site's root, so it works for a missing page at any depth.
- Social preview: `assets/img/og.jpg` (1200 x 630).
- To check what will be published: copy `git ls-files -co --exclude-standard web` to a folder, serve it,
  and look for 404s.

## Adding a result
Add a card to `.arcana` (its `.back` holds the headline number and one sentence, shown on hover), a plate
(`section.plate` with an `.open` holding the chapter header and a `.stage`, then a panel with "How we asked",
"What we saw", numbers, a figure and one closing line), and a row in the ledger (`ledger()` in `atlas.js`). Numbers come from committed result tables through `export_site.py`, never typed by hand
into a figure.

## Small rules learned the hard way (21 Nov 2026)
- The header's open-menu state is the class `menu-open`. Never `open`: `.open` is every section's opening
  screen, and once gave the phone menu a header a whole screen tall.
- A card's two faces (question and answer) share one grid cell, so the card grows to the taller face. Do not
  go back to laying the answer over the question with absolute positioning: it ran into the card's foot.
- Plates whose labels sit beside their marks (The Waning, The Journey) stack the labels above the marks once
  the plate is too narrow to hold both. Check 1,000 to 1,300 px wide when changing a label.
- A ledger row can carry a second band of real animals (`band2` in the exported data); each band is then
  named under the line.
- When removing a rule from `atlas.css`, remove the exact text. A pattern once cut through a media query and
  left every later rule inside it. After any stylesheet edit, check that the braces balance and that a phone
  page is as wide as its screen.
- Inner-page figures wider than a phone scroll sideways, and their caption then opens with a swipe hint
  (added by `charts.js`, not written in the HTML).


## Motion, speed and sizes (21 Nov 2026, second pass)
- **One motion switch.** `assets/motion.js` is loaded in the head of the home page. Motion follows the
  visitor's system setting ("reduce motion"; on Windows that is Settings, Accessibility, Visual effects,
  Animation effects) until they press the round button in the header, or the play button beside the opening's
  links, which shows only while motion is off. The choice is kept on the device. This exists because the
  worm stood still on Windows machines with animation effects turned off, with no way to start it.
  - Scripts read `NEMATICA_MOTION.on` and listen with `NEMATICA_MOTION.sub(fn)`. Do not read the media query
    directly in a script again.
  - Styles follow `html.still` (off) and `html.moving` (on). The media query is kept only as a fallback for a
    page whose scripts did not run, scoped to `html:not(.moving)`.
  - Pausing stops everything at once: signals in flight are dropped and the scene does not lean after the
    pointer. A visitor can still touch a neuron to send one signal.
- **Planet pictures are made after the page is up.** `orbImage()` in `atlas.js` places each picture's box at
  once and queues the painting (a WebGL paint and a PNG each, about forty of them). The far cloud in `sky.js`
  is painted the same way and faded in. Do not go back to painting them while the page loads: it held the
  title back by seconds on a slow machine.
- **Laptop windows.** Check 1366x650, 1280x600, 1536x730 and 1024x768 as well as the usual sizes.
  - Below 820 px tall the opening's title also scales with the window's height, so the first screen holds the
    whole opening.
  - The header's links never wrap; the menu button takes over at 1060 px.
  - Up to 1500 px wide the worm's caption has its own line under the worm.
  - Above 1920 px wide the page's type grows with the screen.
- **The worm is fitted as a whole body.** Its glass runs from 2.78 units before the middle to 3.02 after it
  (the neurons only span 2.6 either side), so the box is 3.0 units each way and the body is shifted to sit
  centred. Smaller numbers let the tail run off narrow screens.
- **One Tab stop per figure.** Inner-page figures and the try-it networks can hold hundreds of named marks.
  Tab reaches one of them; the arrow keys move between the rest (`rove()` in `charts.js`, and the same idea
  in `bench.js`). A named mark gets `role="img"` from `el()`, since a name is not allowed without a role.
- **Gold ink on paper is `#745b0b`.** The lighter gold used before was below the contrast floor on every
  paper tone.
- **Publishing can fail for no reason of ours.** The deploy step sometimes cannot see the artifact uploaded a
  moment before; the workflow waits and tries once more.
