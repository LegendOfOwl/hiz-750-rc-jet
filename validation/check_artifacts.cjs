// Solver/Python gerektirmeyen artefakt denetimi; sayısal solver doğrulaması değildir.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert');
process.chdir(path.resolve(__dirname, '..'));
const read = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const roots = ['validation', 'cfd', 'fem', 'thermal'];
function collect(root) {
  return fs.readdirSync(root,{withFileTypes:true}).flatMap(entry => {
    if(['raw','work','__pycache__'].includes(entry.name) || entry.isSymbolicLink()) return [];
    const file=path.join(root,entry.name);
    return entry.isDirectory() ? collect(file) : [file];
  });
}
const files = roots.flatMap(collect);
files.push('docs/10_yuksek_dogruluk_dogrulama.md', 'README.md', 'CHANGELOG.md');
let jsonCount = 0, links = 0;
for (const file of files) {
  // Host solver ham klasörleri bu küçük artefakt denetiminin dışında kalır.
  if (file.split(path.sep).some(p => ['raw', 'work', '__pycache__'].includes(p))) continue;
  const text = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '');
  if (file.endsWith('.json')) { JSON.parse(text); jsonCount++; }
  if (file.endsWith('.md')) {
    for (const match of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
      const target = match[1].split('#')[0];
      if (!target || /^(https?:|mailto:)/.test(target)) continue;
      assert(fs.existsSync(path.resolve(path.dirname(file), target)), file + ': missing ' + target);
      links++;
    }
  }
  if (/\.(py|ps1|cjs|json|md|svg|msh)$/.test(file)) {
    assert(!text.split(/\r?\n/).some(line => /[ \t]+$/.test(line)), file + ': trailing whitespace');
  }
}
for (const root of roots) {
  const status = read(root + '/results/status.json');
  assert(['BLOCKED','PARTIAL'].includes(status.status));
  if(status.execution === 'NOT_RUN') {
    assert.equal(status.metrics, null);
    assert(status.cases.every(c => c.error_percent === null && c.gci === null));
  } else {
    assert.equal(status.execution,'RUNS_PRESENT');
    assert(status.cases.every(c => c.result_directory && fs.existsSync(c.result_directory)));
  }
}
const comparison = read('validation/results/comparison.json');
for (const [file, expected] of Object.entries(comparison.baseline.source_sha256)) {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'), expected);
}
assert.equal(comparison.baseline.drag_aerobuildup_N, read('aero/out/sonuclar.json').D_750);
const msh = fs.readFileSync('validation/meshes/thermal_1d_coarse.msh', 'utf8').trim().split(/\r?\n/);
let k = msh.indexOf('$Nodes'), n = Number(msh[++k]), nodes = {};
for (let i = 0; i < n; i++) {
  const [id, ...xyz] = msh[++k].split(' ').map(Number);
  nodes[id] = xyz;
}
k = msh.indexOf('$Elements');
const e = Number(msh[++k]);
assert.equal(n, 20); assert.equal(e, 4);
let volume = 0;
for (let i = 0; i < e; i++) {
  const row = msh[++k].split(' ').map(Number);
  assert.equal(row[1], 5);
  const p = row.slice(3).map(id => nodes[id]);
  const [a,b,c] = [1,3,4].map(j => p[j].map((x,d) => x - p[0][d]));
  const det = a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0]);
  assert(det > 0); volume += det;
}
assert(Math.abs(volume - 1e-5) < 1e-15);
console.log('PASS: ' + jsonCount + ' JSON; ' + links + ' local links; honest status manifests; baseline hashes; 20 nodes/4 positive bricks, volume 1e-5 m3; whitespace.');
