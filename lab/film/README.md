# Film renders

Cinematic renders of the project's real data for the write-up: no interface, a scripted camera,
time driven by a controlled clock. The shots in the blog post (9 Nov 2026) came from here.

| Shot | What it shows | Data |
|---|---|---|
| `hero` | A real worm meets the copper boundary and turns back (real time) | copper recording 2024-06-18-12 |
| `brain` | Close-up of the same worm's head neurons | same |
| `pair` | A held-out real worm next to a model worm (2x) | `which2/round_1_*` |
| `path` | The worm's tracked path as a time-lapse inside the copper ring | same as `hero` |
| `swarm` | 32 closed-loop model worms in one arena (8x) | `swarm1` |
| `echo` | One stimulation of AVE: real atlas worm vs model learned from rest (2x) | `poke1`, atlas positions |

Run (Windows or Linux, a GPU makes it real-time):

```
python scripts/export_replay.py ...           # the lab's data, as for the lab viewer
python scripts/film/export_film_echo.py       # only for the echo shot
cd lab && npm install && npm run film         # serves film.html on :8090
python scripts/film/render.py hero out/hero --seconds 12 --size 1920x1080 --grade
```

The palette (indigo, lilac body, pink activity, amber copper) lives in `FilmArena.jsx`,
`FilmWorm.jsx`, `FilmNeurons.jsx` and `Film.jsx`; the lab viewer itself is unchanged.
Labelling rule kept from the lab: body and path are measured, neuron positions are inferred from an
atlas, body width and glow are assumed. Any caption should say so.
