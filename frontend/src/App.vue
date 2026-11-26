<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { t, lang, setLang, detectLang } from './i18n.js'

const TABS = ['pegasus', 'emuelec', 'folder']
// Inline outline icons (24x24 grid, stroke only) so nothing depends on an icon font.
const ICONS = {
  pegasus: '<line x1="6" x2="10" y1="11" y2="11"/><line x1="8" x2="8" y1="9" y2="13"/><line x1="15" x2="15.01" y1="12" y2="12"/><line x1="18" x2="18.01" y1="10" y2="10"/><path d="M17.32 5H6.68a4 4 0 0 0-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 0 1 9.828 16h4.344a2 2 0 0 1 1.414.586L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.545-.604-6.584-.685-7.258-.007-.05-.011-.1-.017-.151A4 4 0 0 0 17.32 5z"/>',
  emuelec: '<rect x="3" y="5" width="18" height="12" rx="2"/><path d="M8 21h8M12 17v4M8 9.5l2 1.5-2 1.5M13 13h3"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  source: '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  settings: '<path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/>',
  status: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v.01M11 11h1.2v5.2H13"/>',
}
const tab = ref('pegasus')
const slots = ref({
  pegasus: { path: '', trad: false },
  emuelec: { path: '', trad: false, overrides: {} },
  folder: { path: '', trad: false, engine: 'MAME', overrides: {} },
})
const stat = ref({ pegasus: { state: 'unset' }, emuelec: { state: 'unset' }, folder: { state: 'unset' } })
const res = ref({ pegasus: null, emuelec: null, folder: null })   // last result per tab
const platforms = ref([])
const theme = ref('system')
const loaded = ref(false)
const about = ref(null)
const showAbout = ref(false)

const slot = computed(() => slots.value[tab.value])
const st = computed(() => stat.value[tab.value])
const r = computed(() => res.value[tab.value])
const isZh = computed(() => lang.value === 'zh-CN' || lang.value === 'zh-TW')
const busy = computed(() => !!r.value && r.value.kind === 'busy')

const api = async (url, body) => {
  const resp = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {})
  if (!resp.ok) { const e = await resp.json().catch(() => ({})); throw new Error(e.detail || resp.statusText) }
  return resp.json()
}
// backend errors arrive as "err.key|argument"
const errText = e => {
  const [k, ...rest] = String(e.message).split('|')
  return k.startsWith('err.') ? t(k, { arg: rest.join('|') }) : e.message
}
// reasons / notes arrive as "code|a|b"
const why = c => {
  const [k, a, b] = String(c).split('|')
  const key = 'why.' + k
  const s = t(key, { a, b })
  return s === key ? c : s
}
const reviewText = it => {
  const k = 'review.' + it.kind
  const s = t(k, { ...it, reason: it.reason ? why(it.reason) : '', note: it.note ? why(it.note) : '',
    examples: Array.isArray(it.examples) ? it.examples.join(', ') : '' })
  return s === k ? JSON.stringify(it) : s
}
// Notes: group the "not a date / not a rating" warnings per folder and field, translate the rest.
const noteLines = notes => {
  const groups = new Map(), lines = []
  let grouped = false
  for (const e of notes || []) {
    if (e.kind !== 'unparsed') { lines.push(reviewText(e)); continue }
    grouped = true
    const k = e.rel + '\u0000' + e.key
    if (!groups.has(k)) groups.set(k, { rel: e.rel || '.', key: e.key, n: 0, ex: [] })
    const g = groups.get(k); g.n++
    if (g.ex.length < 3 && !g.ex.includes(e.value)) g.ex.push(e.value)
  }
  for (const g of groups.values()) {
    const kk = 'warn.unparsed_' + (g.key === 'release' || g.key === 'releasedate' ? 'release' : g.key === 'rating' ? 'rating' : 'other')
    lines.push(t(kk, { rel: g.rel, key: g.key, n: g.n, examples: g.ex.join('、') }))
  }
  return { lines, grouped }
}

const native = () => window.pywebview && window.pywebview.api
async function browse() {
  const p = await window.pywebview.api.pick_folder()
  if (p) slot.value.path = p
}

// ---- status of each tab: unset / offline / idle / done
async function refresh(src) {
  const s = slots.value[src]
  try { stat.value[src] = await api('/api/status', { source: src, path: s.path }) }
  catch (e) { stat.value[src] = { state: 'unset' } }
}
const refreshAll = () => Promise.all(TABS.map(refresh))
async function heartbeat() {                       // cheap: only checks whether each folder is still reachable
  for (const src of TABS) {
    const s = slots.value[src]
    if (!s.path || (res.value[src] && res.value[src].kind === 'busy')) continue
    try {
      const d = await api('/api/status', { source: src, path: s.path, quick: true })
      if (d.state === 'offline') stat.value[src] = { state: 'offline' }
      else if (stat.value[src].state === 'offline') await refresh(src)    // the drive is back
    } catch (e) { /* ignore */ }
  }
}

// ---- operations
const wantTrad = () => slot.value.trad && isZh.value
async function convert() {
  const src = tab.value, s = slots.value[src]
  res.value[src] = { kind: 'busy' }
  try {
    const d = await api('/api/convert', { source: src, path: s.path, trad: s.trad && isZh.value,
      engine: s.engine || 'MAME', overrides: s.overrides || {} })
    res.value[src] = { kind: 'ok', data: d }
  } catch (e) { res.value[src] = { kind: 'error', text: errText(e) } }
  await refresh(src)
}
async function remove() {
  const src = tab.value, s = slots.value[src]
  if (!window.confirm(t('act.confirm_delete', { path: s.path }))) return
  res.value[src] = { kind: 'busy' }
  try {
    const d = await api('/api/delete', { source: src, path: s.path })
    res.value[src] = { kind: 'info', text: t('st.deleted', { n: d.removed }) }
  } catch (e) { res.value[src] = { kind: 'error', text: errText(e) } }
  await refresh(src)
}
function setOverride(item, patch) {
  Object.assign(item, patch)
  const s = slots.value[tab.value]
  s.overrides = { ...(s.overrides || {}), [item.src]: { platform: item.platform, hack: item.hack } }
}

// ---- status card
const pill = computed(() => {
  if (r.value && r.value.kind === 'busy') return { cls: 'busy', text: t('st.busy') }
  if (r.value && r.value.kind === 'error') return { cls: 'err', text: t('st.error') }
  if (st.value.state === 'offline') return { cls: 'off', text: t('st.offline') }
  if (st.value.state === 'done') return { cls: 'ok', text: t('st.done') }
  return { cls: 'idle', text: t('st.ready') }
})
const statusLines = computed(() => {
  const x = r.value
  if (x && x.kind === 'busy') return []
  if (x && x.kind === 'error') return [x.text]
  if (st.value.state === 'offline') return [t('st.offline_text', { path: slot.value.path })]
  const out = []
  if (x && x.kind === 'info') out.push(x.text)
  else if (x && x.kind === 'ok') {
    out.push(t('st.summary', x.data.stats))
    if (x.data.stats.skipped) out.push(t('st.skipped', { n: x.data.stats.skipped }))
  } else out.push(t(st.value.state === 'unset' ? 'act.pick_first' : st.value.state === 'done' ? 'st.done_text' : 'st.idle_text'))
  return out
})
const noteInfo = computed(() => (r.value && r.value.kind === 'ok') ? noteLines(r.value.data.notes) : { lines: [], grouped: false })
const items = computed(() => (r.value && r.value.kind === 'ok') ? r.value.data.items : [])

// ---- settings: theme / language / tab / slots follow the user automatically
function setTheme(v) { theme.value = v; document.documentElement.dataset.theme = v }
function changeLang(code) {
  setLang(code)
  api('/api/settings', { lang: lang.value }).catch(() => {})
  try { window.pywebview.api.refresh_menu(lang.value) } catch (e) { /* not in the native window */ }
}
let saveTimer = null
watch([slots, tab, theme], () => {
  if (!loaded.value) return
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => api('/api/settings', { slots: slots.value, tab: tab.value, theme: theme.value }).catch(() => {}), 150)
}, { deep: true })
let pathTimer = null
watch(() => TABS.map(k => slots.value[k].path), (now, old) => {
  if (!loaded.value) return
  TABS.forEach((k, i) => { if (now[i] !== old[i]) res.value[k] = null })
  clearTimeout(pathTimer)
  pathTimer = setTimeout(refreshAll, 300)
})

function applySlots(s) {
  for (const k of TABS) slots.value[k] = { ...slots.value[k], ...((s.slots || {})[k] || {}) }
  tab.value = TABS.includes(s.tab) ? s.tab : 'pegasus'
}
async function reloadSlots() {
  applySlots(await api('/api/settings'))
  res.value = { pegasus: null, emuelec: null, folder: null }
  await refreshAll()
}
async function openAbout() { about.value = await api('/api/about'); showAbout.value = true }
function notify(key) { res.value[tab.value] = { kind: 'error', text: t(key) } }

onMounted(async () => {
  Object.assign(window, { setTheme, setLang: changeLang, openAbout, reloadSlots, notify })   // called from the native menu
  platforms.value = await api('/api/platforms')
  try {
    const s = await api('/api/settings')
    setTheme(s.theme || 'system')
    setLang(s.lang || detectLang())
    applySlots(s)
  } catch (e) { setLang(detectLang()) }
  loaded.value = true
  await refreshAll()
  window.addEventListener('focus', refreshAll)
  window.addEventListener('keydown', ev => { if (ev.key === 'Escape') showAbout.value = false })
  setInterval(heartbeat, 4000)
})
</script>

<template>
  <div class="app">
    <nav class="tabs">
      <button v-for="k in TABS" :key="k" class="tab" :class="{ on: tab === k }" :title="t('tab.' + k + '_tip')" @click="tab = k">
        <svg class="tic" viewBox="0 0 24 24" aria-hidden="true" v-html="ICONS[k]"></svg>
        <span class="tlabel">{{ t('tab.' + k) }}</span>
        <span class="dot" :class="stat[k].state"></span>
      </button>
    </nav>

    <main class="pane">
      <section class="card">
        <h2><svg class="hic" viewBox="0 0 24 24" aria-hidden="true" v-html="ICONS.source"></svg>{{ t('card.source') }}</h2>
        <div class="row">
          <input class="grow" v-model="slot.path" :placeholder="t('src.ph_' + tab)" />
          <button v-if="native()" @click="browse">{{ t('src.browse') }}</button>
        </div>
        <p class="hint">{{ t('src.intro_' + tab) }}</p>
        <p class="hint" v-if="tab !== 'folder' && st.folders !== undefined">{{ t('src.found_' + tab, { n: st.folders }) }}</p>
      </section>

      <section class="card">
        <h2><svg class="hic" viewBox="0 0 24 24" aria-hidden="true" v-html="ICONS.settings"></svg>{{ t('card.settings') }}</h2>
        <div class="row" v-if="isZh">
          <label><input type="checkbox" v-model="slot.trad" /> {{ t('opt.trad') }}</label>
        </div>
        <div class="row" v-if="tab === 'folder'">
          <label :title="t('opt.engine_tip')">{{ t('opt.engine') }}
            <select v-model="slot.engine"><option>MAME</option><option>FBNeo</option></select>
          </label>
        </div>
        <div class="row">
          <span v-if="st.state === 'offline'" class="pill off">{{ t('st.offline') }}</span>
          <button v-if="st.state === 'offline'" @click="native() ? browse() : null">{{ t('act.repick') }}</button>
          <button v-if="st.state === 'idle'" class="primary" :disabled="busy" @click="convert">{{ t('act.start') }}</button>
          <template v-if="st.state === 'done'">
            <button class="primary" :disabled="busy" @click="convert">{{ t('act.redo') }}</button>
            <button class="danger" :disabled="busy" @click="remove">{{ t('act.delete') }}</button>
          </template>
        </div>
      </section>

      <section class="card grow-card">
        <h2><svg class="hic" viewBox="0 0 24 24" aria-hidden="true" v-html="ICONS.status"></svg>{{ t('card.status') }}</h2>
        <div class="scroll">
        <div class="row"><span class="pill" :class="pill.cls">{{ pill.text }}</span></div>
        <p class="line" v-for="(l, i) in statusLines" :key="i">{{ l }}</p>

        <template v-if="noteInfo.lines.length">
          <h3>{{ t('st.notes_title', { n: noteInfo.lines.length }) }}</h3>
          <p v-if="noteInfo.grouped" class="hint">{{ t('st.warn_hint') }}</p>
          <div class="box"><div v-for="(l, i) in noteInfo.lines" :key="i" class="note">{{ l }}</div></div>
        </template>

        <template v-if="items.length">
          <h3>{{ t('st.check_title', { n: items.length + r.data.more }) }}</h3>
          <p class="hint">{{ t('st.check_hint') }}</p>
          <div class="box tall">
            <table>
              <thead><tr><th>{{ t('col.file') }}</th><th>{{ t('col.platform') }}</th><th>{{ t('col.hack') }}</th><th>{{ t('col.reason') }}</th></tr></thead>
              <tbody>
                <tr v-for="it in items" :key="it.src">
                  <td class="file" :title="it.src">{{ it.file }}</td>
                  <td>
                    <select :value="it.platform" @change="setOverride(it, { platform: $event.target.value })">
                      <option v-for="p in platforms" :key="p.key" :value="p.key">{{ p.key }}</option>
                    </select>
                  </td>
                  <td><input type="checkbox" :checked="it.hack" @change="setOverride(it, { hack: $event.target.checked })" /></td>
                  <td class="why">{{ why(it.reason) }}<span v-for="n in it.notes" :key="n" class="note"> ⚠ {{ why(n) }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="r.data.more" class="hint">{{ t('st.more', { n: r.data.more }) }}</p>
        </template>
        </div>
      </section>
    </main>
  </div>

  <div v-if="showAbout && about" class="modal" @click.self="showAbout = false">
    <div class="dialog">
      <div class="dtitle"><span>{{ t('about.title') }}</span><button class="x" :aria-label="t('about.close')" @click="showAbout = false">×</button></div>
      <div class="dbody">
        <img class="logo" src="/ponia_mark.svg" alt="Ponia" />
        <div class="info">
          <div class="name">PoniaMDM {{ about.version }}</div>
          <div class="arch">x64</div>
          <div class="small" v-if="about.release">{{ t('about.release', { date: about.release }) }}</div>
          <div class="small">© 2026 Equuleus Works</div>
          <div class="small">GPL-3.0-or-later</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
:root { --bg:#f3f3f3; --card:#fff; --fg:#1b1b1b; --mut:#5f5f5f; --line:#d9d9d9; --acc:#0067c0; --warn:#fff4ce; --sel:#e5f1fb; --ok:#2e7d32; --off:#b26a00; --err:#b3261e; }
@media (prefers-color-scheme: dark) { :root { --bg:#202020; --card:#2b2b2b; --fg:#f3f3f3; --mut:#a6a6a6; --line:#404040; --acc:#4cc2ff; --warn:#433519; --sel:#1e3a52; --ok:#7bc47f; --off:#ffb454; --err:#ff8a80; } }
:root[data-theme="light"] { --bg:#f3f3f3; --card:#fff; --fg:#1b1b1b; --mut:#5f5f5f; --line:#d9d9d9; --acc:#0067c0; --warn:#fff4ce; --sel:#e5f1fb; --ok:#2e7d32; --off:#b26a00; --err:#b3261e; }
:root[data-theme="dark"] { --bg:#202020; --card:#2b2b2b; --fg:#f3f3f3; --mut:#a6a6a6; --line:#404040; --acc:#4cc2ff; --warn:#433519; --sel:#1e3a52; --ok:#7bc47f; --off:#ffb454; --err:#ff8a80; }
* { box-sizing: border-box }
html, body, #app { height:100%; margin:0 }
body { background:var(--bg); color:var(--fg); overflow:hidden; user-select:none;
  font:13px/1.45 "Segoe UI Variable Text","Segoe UI","Microsoft JhengHei UI","Microsoft YaHei UI","Yu Gothic UI","Malgun Gothic",sans-serif }
input[type=text], input:not([type]), textarea, pre, .file, .why, .line, .note { user-select:text }

.app { display:flex; height:100vh; padding:12px; gap:12px }
.tabs { width:200px; flex:none; padding:10px 8px; border:1px solid var(--line); border-radius:12px; background:var(--card); display:flex; flex-direction:column; gap:4px }
.tab { display:flex; align-items:center; gap:10px; width:100%; height:auto; min-height:46px; padding:6px 10px; text-align:left; border:0; border-radius:8px; background:none; font-size:14px; line-height:1.25 }
.tab:hover { background:var(--sel) }
.tab.on { background:var(--sel); color:var(--acc); font-weight:600 }
.tlabel { flex:1; min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis }
.dot { width:9px; height:9px; border-radius:50%; flex:none; background:var(--line) }
.dot.done { background:var(--ok) } .dot.offline { background:var(--off) }

.pane { flex:1; min-width:0; overflow:hidden; display:flex; flex-direction:column; gap:10px }

.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:10px 14px }
.grow-card { flex:1; min-height:0; display:flex; flex-direction:column }
.scroll { flex:1; min-height:0; overflow-y:auto }
h2 { display:flex; align-items:center; gap:8px; font-size:15px; font-weight:700; margin:0 0 8px; padding-bottom:8px; border-bottom:1px solid var(--line); color:var(--fg) }
.hic { width:18px; height:18px; flex:none; fill:none; stroke:var(--acc); stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round }
.tic { width:22px; height:22px; flex:none; fill:none; stroke:currentColor; stroke-width:1.7; stroke-linecap:round; stroke-linejoin:round; color:var(--mut) }
.tab.on .tic { color:var(--acc) }
h3 { font-size:13px; font-weight:700; margin:12px 0 2px }
.row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:6px 0 }
.grow { flex:1; min-width:160px }
label { display:inline-flex; align-items:center; gap:6px }
input[type=radio], input[type=checkbox] { margin:0; flex:none; width:14px; height:14px; padding:0 }
input, select, button { font:inherit; color:var(--fg); background:var(--card); border:1px solid var(--line); border-radius:4px; height:28px; padding:2px 8px }
button { cursor:pointer; border-bottom-color:#b5b5b5 } button:disabled { opacity:.45; cursor:default }
button:hover:not(:disabled) { background:var(--sel) }
button.primary { background:var(--acc); border-color:var(--acc); color:#fff; font-weight:600 }
button.primary:hover:not(:disabled) { filter:brightness(1.1); background:var(--acc) }
button.danger { color:var(--err); border-color:var(--err) }
.hint { margin:4px 0 0; color:var(--mut); font-size:12px }
.line { margin:4px 0; color:var(--mut); font-size:12px }
.pill { display:inline-flex; align-items:center; padding:1px 10px; border-radius:12px; font-size:12px; border:1px solid var(--line); color:var(--mut) }
.pill.ok { color:var(--ok); border-color:var(--ok) } .pill.off { color:var(--off); border-color:var(--off) }
.pill.err { color:var(--err); border-color:var(--err) } .pill.busy { color:var(--acc); border-color:var(--acc) }
.box { background:var(--bg); border:1px solid var(--line); border-radius:8px; padding:6px 10px; font-size:12px }
.box.tall { padding:0; overflow:hidden }
.note { color:#c0560f; margin:2px 0; font-size:12px }
.why { color:var(--mut); font-size:12px }
table { border-collapse:collapse; width:100% }
th { position:sticky; top:0; background:var(--card); text-align:left; border-bottom:1px solid var(--line); padding:4px 8px; z-index:1; font-weight:600 }
td { padding:2px 8px; border-bottom:1px solid var(--line); vertical-align:middle }
.file { max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap }

.modal { position:fixed; inset:0; background:rgba(0,0,0,.35); display:flex; align-items:center; justify-content:center; z-index:10 }
.dialog { background:var(--card); border:1px solid var(--line); border-radius:8px; width:min(380px, 94vw); overflow:hidden }
.dtitle { display:flex; align-items:center; justify-content:space-between; padding:8px 8px 8px 14px; font-size:12px; border-bottom:1px solid var(--line) }
.x { border:0; background:none; font-size:20px; line-height:1; height:28px; width:34px; padding:0 }
.dbody { display:flex; align-items:center; justify-content:center; gap:16px; padding:18px 22px }
.logo { width:96px; height:96px; flex:none }
.info { text-align:center }
.name { font-size:20px; font-weight:700 } .arch { font-size:15px; font-weight:700; margin-bottom:10px } .small { font-size:13px }
</style>
