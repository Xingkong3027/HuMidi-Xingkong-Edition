// Read-only test bridge: execute product TypeScript converters against IPC details.
const fs = require('fs'), path = require('path'), vm = require('vm');
const { stripTypeScriptTypes } = require('node:module');
const root = path.resolve(__dirname, '../src');
const cache = new Map();
function load(filename) {
  filename = path.resolve(filename);
  if (!filename.endsWith('.ts')) filename += '.ts';
  if (!filename.startsWith(root + path.sep)) throw new Error('Outside product source');
  if (cache.has(filename)) return cache.get(filename).exports;
  const module = { exports: {} }; cache.set(filename, module);
  const source = fs.readFileSync(filename, 'utf8');
  let code = stripTypeScriptTypes(source, { mode: 'transform' });
  const exports = [];
  code = code.replace(/export (async )?(function|const|let)\s+([A-Za-z0-9_]+)/g, (_all, async, kind, name) => {
    exports.push(name); return `${async || ''}${kind} ${name}`;
  });
  code = code.replace(/import\s*\{([^}]+)\}\s*from\s*["']([^"']+)["'];?/g, (_all, names, spec) => `const {${names.replace(/\bas\b/g, ':')}} = require(${JSON.stringify(spec)});`);
  code += '\nObject.assign(module.exports, {' + exports.join(',') + '});';
  const requireSource = spec => spec.startsWith('.') ? load(path.resolve(path.dirname(filename), spec)) : { invoke() {}, getVersion() {}, listen() {} };
  const wrapper = vm.runInNewContext('(function(require,module,exports){' + code + '\n})', { crypto: globalThis.crypto }, { filename });
  wrapper(requireSource, module, module.exports);
  return module.exports;
}

const assert = require("assert");
const { songConfig } = load(path.join(root,"lib/playlist.ts"));
const { toBackendConfig } = load(path.join(root,"lib/tauri.ts"));
const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const output = input.map(detail => {
  const restored = songConfig(detail.song.playback_settings);
  const backend = toBackendConfig(restored, detail.midi_path || '');
  const json = JSON.parse(JSON.stringify(backend));
  assert(Array.isArray(restored.pedal_curve_on) && Array.isArray(restored.pedal_curve_off));
  assert(Array.isArray(json.pedal_curve_on) && Array.isArray(json.pedal_curve_off));
  assert.equal(json.performance_optimization, false);
  return { id: detail.metadata.id, name: detail.metadata.name, config: json, selectedTracksInfo: detail.song.selected_tracks.map(t => [t.index, t.role]) };
});
fs.writeFileSync(process.argv[3], JSON.stringify(output));
