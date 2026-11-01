const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { create } = require('../web/assets/swarm-engine.js');

const source = fs.readFileSync(path.join(__dirname, '../web/data/sim/swarm-profiles.js'), 'utf8');
const data = JSON.parse(source.split(' = ')[1].trim().slice(0, -1));
const options = { profiles: data.profiles, radius: data.radius_mm, length: data.length_mm };
const positions = run => run.agents.map(a => [a.x, a.y, a.reversing]);

test('the same seed can be replayed and scrubbed backward exactly', () => {
  const a = create({ ...options, seed: 7 });
  const first = positions(a.seek(800));
  a.seek(1200);
  assert.deepEqual(positions(a.seek(800)), first);
  assert.deepEqual(positions(create({ ...options, seed: 7 }).seek(800)), first);
  assert.notDeepEqual(positions(create({ ...options, seed: 8 }).seek(800)), first);
});

test('heads stay inside the declared outer tolerance across the run', () => {
  const engine = create({ ...options, seed: 7 });
  let greatest = 0;
  for (let i = 0; i < 1600; i++) {
    const state = engine.step();
    for (const a of state.agents) greatest = Math.max(greatest, Math.hypot(a.x, a.y));
  }
  assert.ok(greatest <= data.radius_mm + .120001);
  assert.equal(engine.snapshot().time, 960);
});

test('contact response changes the crowd rather than only the label', () => {
  const on = create({ ...options, seed: 7, interact: true }).seek(1600).summary;
  const off = create({ ...options, seed: 7, interact: false }).seek(1600).summary;
  assert.ok(on.contact < off.contact);
  assert.ok(on.cluster < off.cluster);
  assert.ok(on.rev2 > off.rev2);
  assert.ok(on.contact > 0 && off.contact > 0);
});
