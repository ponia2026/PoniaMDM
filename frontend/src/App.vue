<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { t, lang, setLang, LANGS } from './i18n.js'

const sources = ref([])
const platforms = ref([])
const source = ref('pegasus')
const peg = ref({ root: '', backup: '', keep_pegasus: false })
const pegOut = ref(null)
const about = ref(null)
const showAbout = ref(false)
const path = ref('')
const engine = ref('MAME')
const rows = ref([])
const review = ref([])
const selected = ref(new Set())
const busy = ref(false)
const msg = ref('')
const search = ref('')
const fPlat = ref('')
const fOnly = ref('all')        // all | check | edited
const page = ref(0)
const PAGE = 200
const bulkPlat = ref('')
const exp = ref({ out: '', roms: 'none', zh: 'keep' })
const report = ref(null)
const showReview = ref(false)
const theme = ref('system')
const loaded = ref(false)

const api = async (url, body) => {
  const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {})
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || r.statusText) }
  return r.json()
}
// backend errors arrive as "err.key|argument"
const errText = e => {
  const [k, ...rest] = String(e.message).split('|')
  return t('status.error', { msg: k.startsWith('err.') ? t(k, { arg: rest.join('|') }) : e.message })
}

const native = () => window.pywebview && window.pywebview.api
async function browse(target) {
  const p = await window.pywebview.api.pick_folder()
  if (!p) return
  if (target === 'src') path.value = p
  else if (target === 'peg') peg.value.root = p
  else if (target === 'bak') peg.value.backup = p
  else exp.value.out = p
}

async function openAbout() { if (!about.value) about.value = await api('/api/about'); showAbout.value = true }
async function pegRun(kind) {
  busy.value = true; msg.value = ''; pegOut.value = null
  try {
    const d = await api('/api/pegasus/' + kind, peg.value)
    pegOut.value = d
    msg.value = kind === 'convert' ? t('status.converted') : t('status.restored', { n: d.restored })
  } catch (e) { msg.value = errText(e) } finally { busy.value = false }
}

// ---- settings: theme/language/window follow you automatically; the form is only stored by "Save as defaults"
function setTheme(v) { theme.value = v; document.documentElement.dataset.theme = v }
function changeLang(code) { setLang(code); api('/api/settings', { lang: lang.value }).catch(() => {}) }
watch(theme, () => { if (loaded.value) api('/api/settings', { theme: theme.value }).catch(() => {}) })

const formState = () => ({ source: source.value, peg: peg.value, folder_path: path.value, engine: engine.value, export: exp.value })
function applyForm(d) {
  d = d || {}
  source.value = d.source || 'pegasus'
  peg.value = { root: '', backup: '', keep_pegasus: false, ...(d.peg || {}) }
  path.value = d.folder_path || ''
  engine.value = d.engine || 'MAME'
  exp.value = { out: '', roms: 'none', zh: 'keep', ...(d.export || {}) }
}
async function saveDefaults() {
  try { await api('/api/settings', { defaults: formState() }); msg.value = t('status.defaults_saved') }
  catch (e) { msg.value = errText(e) }
}
async function loadDefaults() {
  try { applyForm((await api('/api/settings')).defaults); msg.value = t('status.defaults_loaded') }
  catch (e) { msg.value = errText(e) }
}

onMounted(async () => {
  Object.assign(window, { setTheme, setLang: changeLang, openAbout, saveDefaults, loadDefaults })   // called from the native menu
  sources.value = await api('/api/sources')
  platforms.value = await api('/api/platforms')
  try {
    const s = await api('/api/settings')
    setTheme(s.theme || 'system')
    setLang(s.lang || 'zh-TW')
    applyForm(s.defaults)
  } catch (e) { /* first run */ }
  loaded.value = true
})
const statusText = computed(() => msg.value || (busy.value ? t('status.busy') : t('status.ready')))

const needsCheck = r => r.conf !== 'high' || r.notes.length || r.platform === 'Unsorted'

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return rows.value.filter(r =>
    (!q || r.title.toLowerCase().includes(q) || r.file.toLowerCase().includes(q)) &&
    (!fPlat.value || r.platform === fPlat.value) &&
    (fOnly.value === 'all' || (fOnly.value === 'check' ? needsCheck(r) && !r.edited : r.edited)))
})
const pages = computed(() => Math.max(1, Math.ceil(filtered.value.length / PAGE)))
const shown = computed(() => filtered.value.slice(page.value * PAGE, (page.value + 1) * PAGE))
watch([search, fPlat, fOnly], () => { page.value = 0 })

const counts = computed(() => {
  const c = {}
  rows.value.forEach(r => {
    if (!r.include) return
    const k = r.platform + (r.hack ? ' hack' : '')
    c[k] = (c[k] || 0) + 1
  })
  return Object.entries(c).sort()
})
const nCheck = computed(() => rows.value.filter(r => needsCheck(r) && !r.edited).length)

async function load() {
  const d = await api('/api/entries')
  rows.value = d.rows; review.value = d.review; selected.value = new Set()
}
async function scan() {
  busy.value = true; msg.value = ''; report.value = null
  try {
    const d = await api('/api/scan', { source: source.value, path: path.value, arcade_engine: engine.value })
    await load()
    msg.value = t('status.found', { n: d.count, check: nCheck.value })
    fOnly.value = nCheck.value ? 'check' : 'all'
  } catch (e) { msg.value = errText(e) } finally { busy.value = false }
}
async function update(ids, patch) {
  await api('/api/entries/update', { ids, ...patch })
  const set = new Set(ids)
  rows.value.forEach(r => {
    if (!set.has(r.id)) return
    Object.assign(r, patch)
    if (patch.platform !== undefined) { r.conf = 'high'; r.reason = t('res.manual'); r.notes = [] }
    if (patch.platform !== undefined || patch.hack !== undefined || patch.title !== undefined) r.edited = true
  })
}
const toggle = id => { const s = new Set(selected.value); s.has(id) ? s.delete(id) : s.add(id); selected.value = s }
const allShown = computed(() => shown.value.length > 0 && shown.value.every(r => selected.value.has(r.id)))
const toggleAll = () => {
  const s = new Set(selected.value)
  shown.value.forEach(r => allShown.value ? s.delete(r.id) : s.add(r.id)); selected.value = s
}
const selectAllFiltered = () => { selected.value = new Set(filtered.value.map(r => r.id)) }
const bulk = async patch => { await update([...selected.value], patch); selected.value = new Set() }
async function doExport() {
  busy.value = true; msg.value = ''
  try { report.value = await api('/api/export', exp.value); msg.value = t('status.exported') }
  catch (e) { msg.value = errText(e) } finally { busy.value = false }
}
</script>

<template>
  <div class="shell"><main>
  <section class="card">
    <h2>{{ t('sec.source') }}</h2>
    <div class="row">
      <select v-model="source">
        <option v-for="s in sources" :key="s.key" :value="s.key">{{ t('src.' + s.key) }}</option>
      </select>
      <template v-if="source !== 'pegasus'">
        <input class="grow" v-model="path" :placeholder="t('scan.path_ph')" @keyup.enter="scan" />
        <button v-if="native()" @click="browse('src')">{{ t('btn.browse') }}</button>
        <select v-model="engine" :title="t('scan.engine_tip')">
          <option>MAME</option><option>FBNeo</option>
        </select>
        <button class="primary" :disabled="busy || !path" @click="scan">{{ t('scan.run') }}</button>
      </template>
    </div>

    <template v-if="source === 'pegasus'">
      <p class="msg">{{ t('peg.intro') }}</p>
      <div class="row">
        <input class="grow" v-model="peg.root" :placeholder="t('peg.root_ph')" />
        <button v-if="native()" @click="browse('peg')">{{ t('btn.browse') }}</button>
      </div>
      <div class="row">
        <input class="grow" v-model="peg.backup" :placeholder="t('peg.backup_ph')" />
        <button v-if="native()" @click="browse('bak')">{{ t('btn.browse') }}</button>
      </div>
      <div class="row">
        <label><input type="checkbox" v-model="peg.keep_pegasus" /> {{ t('peg.keep') }}</label>
        <button class="primary" :disabled="busy || !peg.root || !peg.backup" @click="pegRun('convert')">{{ t('peg.convert') }}</button>
        <button :disabled="busy || !peg.root || !peg.backup" @click="pegRun('restore')">{{ t('peg.restore') }}</button>
      </div>
      <div v-if="pegOut && pegOut.stats" class="report">
        {{ t('peg.summary', pegOut.stats) }}
        <div v-for="(l, i) in pegOut.log.slice(0, 200)" :key="i" class="note">{{ l }}</div>
      </div>
    </template>
  </section>

  <template v-if="rows.length && source !== 'pegasus'">
    <section class="card">
      <h2>{{ t('sec.result') }} <small>{{ t('res.title_count', { n: rows.length, counts: counts.map(([k, n]) => k + ' ' + n).join(', ') }) }}</small></h2>
      <div class="row">
        <input v-model="search" :placeholder="t('res.search_ph')" />
        <select v-model="fPlat">
          <option value="">{{ t('res.all_platforms') }}</option>
          <option v-for="p in platforms" :key="p.key" :value="p.key">{{ p.key }}</option>
        </select>
        <select v-model="fOnly">
          <option value="all">{{ t('res.f_all') }}</option>
          <option value="check">{{ t('res.f_check', { n: nCheck }) }}</option>
          <option value="edited">{{ t('res.f_edited') }}</option>
        </select>
        <button @click="showReview = !showReview" v-if="review.length">{{ t('res.notes', { n: review.length }) }}</button>
      </div>
      <pre v-if="showReview" class="review">{{ review.join('\n') }}</pre>

      <div class="row bulk" :class="{ on: selected.size }">
        <span>{{ t('res.selected', { n: selected.size }) }}</span>
        <button class="link" @click="selectAllFiltered">{{ t('res.select_all', { n: filtered.length }) }}</button>
        <select v-model="bulkPlat">
          <option value="">{{ t('res.set_platform_ph') }}</option>
          <option v-for="p in platforms" :key="p.key" :value="p.key">{{ p.key }} ({{ p.collection }})</option>
        </select>
        <button :disabled="!selected.size || !bulkPlat" @click="bulk({ platform: bulkPlat })">{{ t('res.apply_platform') }}</button>
        <button :disabled="!selected.size" @click="bulk({ hack: true })">{{ t('res.set_hack') }}</button>
        <button :disabled="!selected.size" @click="bulk({ hack: false })">{{ t('res.unset_hack') }}</button>
        <button :disabled="!selected.size" @click="bulk({ include: false })">{{ t('res.exclude') }}</button>
        <button :disabled="!selected.size" @click="bulk({ include: true })">{{ t('res.include') }}</button>
      </div>

      <div class="tablewrap">
        <table>
          <thead><tr>
            <th><input type="checkbox" :checked="allShown" @change="toggleAll" /></th>
            <th>{{ t('col.title') }}</th><th>{{ t('col.file') }}</th><th>{{ t('col.platform') }}</th>
            <th>{{ t('col.hack') }}</th><th>{{ t('col.conf') }}</th><th>{{ t('col.reason') }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="r in shown" :key="r.id" :class="{ off: !r.include, warn: needsCheck(r) && !r.edited, sel: selected.has(r.id) }">
              <td><input type="checkbox" :checked="selected.has(r.id)" @change="toggle(r.id)" /></td>
              <td><input class="title" :value="r.title" @change="update([r.id], { title: $event.target.value })" /></td>
              <td class="file" :title="r.src">{{ r.file }}<span v-if="r.archive" class="tag">{{ t('res.archive') }}</span></td>
              <td>
                <select :value="r.platform" @change="update([r.id], { platform: $event.target.value })">
                  <option v-for="p in platforms" :key="p.key" :value="p.key">{{ p.key }}</option>
                  <option v-if="!platforms.some(p => p.key === r.platform)" :value="r.platform">{{ r.platform }}</option>
                </select>
              </td>
              <td><input type="checkbox" :checked="r.hack" @change="update([r.id], { hack: $event.target.checked })" /></td>
              <td><span class="badge" :class="r.conf">{{ t('conf.' + r.conf) }}</span></td>
              <td class="why">{{ r.reason }}<span v-for="n in r.notes" :key="n" class="note"> ⚠ {{ n }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!filtered.length" class="msg">{{ t('res.empty') }}</p>
      <div class="row pager">
        <button :disabled="page === 0" @click="page--">{{ t('res.prev') }}</button>
        <span>{{ t('res.page', { page: page + 1, pages, n: filtered.length }) }}</span>
        <button :disabled="page + 1 >= pages" @click="page++">{{ t('res.next') }}</button>
      </div>
    </section>

    <section class="card">
      <h2>{{ t('sec.export') }}</h2>
      <div class="row">
        <input class="grow" v-model="exp.out" :placeholder="t('exp.out_ph')" />
        <button v-if="native()" @click="browse('out')">{{ t('btn.browse') }}</button>
        <select v-model="exp.roms">
          <option value="none">{{ t('exp.roms_none') }}</option>
          <option value="copy">{{ t('exp.roms_copy') }}</option>
          <option value="link">{{ t('exp.roms_link') }}</option>
          <option value="move">{{ t('exp.roms_move') }}</option>
        </select>
        <select v-model="exp.zh">
          <option value="keep">{{ t('exp.zh_keep') }}</option>
          <option value="trad">{{ t('exp.zh_trad') }}</option>
        </select>
        <button class="primary" :disabled="busy || !exp.out" @click="doExport">{{ t('exp.run') }}</button>
      </div>
      <div v-if="report" class="report">
        <div v-for="(n, f) in report.folders" :key="f">{{ t('exp.folder_line', { folder: f, n }) }}</div>
        <div v-for="w in report.warnings" :key="w" class="note">⚠ {{ w }}</div>
      </div>
    </section>
  </template>
  </main>
  <footer class="statusbar">
    <span class="st-msg" :title="statusText">{{ statusText }}</span>
    <span v-if="rows.length && source !== 'pegasus'">{{ t('res.count', { n: rows.length }) }}</span>
  </footer></div>

  <div v-if="showAbout" class="modal" @click.self="showAbout = false">
    <div class="dialog">
      <div class="dhead"><img class="logo" src="/ponia_mark.svg" alt="" /><b>PoniaMDM {{ about.version }}</b>
        <button @click="showAbout = false">{{ t('about.close') }}</button></div>
      <p>{{ t('about.text') }}</p>
      <pre>{{ about.notice }}</pre>
      <details><summary>{{ t('about.license') }}</summary><pre>{{ about.license }}</pre></details>
    </div>
  </div>
</template>

<style>
:root { --bg:#f3f3f3; --card:#fff; --fg:#1b1b1b; --mut:#5f5f5f; --line:#d9d9d9; --acc:#0067c0; --warn:#fff4ce; --sel:#e5f1fb; }
@media (prefers-color-scheme: dark) { :root { --bg:#202020; --card:#2b2b2b; --fg:#f3f3f3; --mut:#a6a6a6; --line:#404040; --acc:#4cc2ff; --warn:#433519; --sel:#1e3a52; } }
:root[data-theme="light"] { --bg:#f3f3f3; --card:#fff; --fg:#1b1b1b; --mut:#5f5f5f; --line:#d9d9d9; --acc:#0067c0; --warn:#fff4ce; --sel:#e5f1fb; }
:root[data-theme="dark"] { --bg:#202020; --card:#2b2b2b; --fg:#f3f3f3; --mut:#a6a6a6; --line:#404040; --acc:#4cc2ff; --warn:#433519; --sel:#1e3a52; }
* { box-sizing: border-box }
html, body, #app { height:100%; margin:0 }
body { background:var(--bg); color:var(--fg); overflow:hidden; user-select:none;
  font:13px/1.45 "Segoe UI Variable Text","Segoe UI","Microsoft JhengHei UI","Microsoft YaHei UI","Yu Gothic UI","Malgun Gothic",sans-serif }
input[type=text], input:not([type]), textarea, pre, .file, .why { user-select:text }
.shell { display:flex; flex-direction:column; height:100vh }
main { flex:1; overflow:auto; padding:10px 12px 4px }
.card { background:var(--card); border:1px solid var(--line); border-radius:6px; margin:0 0 10px; padding:10px 12px }
h2 { font-size:13px; font-weight:600; margin:0 0 6px } h2 small { color:var(--mut); font-weight:400 }
.row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:6px 0 }
.grow { flex:1; min-width:200px }
input, select, button { font:inherit; color:var(--fg); background:var(--card); border:1px solid var(--line); border-radius:4px; height:28px; padding:2px 8px }
input[type=checkbox] { width:14px; height:14px; padding:0 }
button { cursor:pointer; border-bottom-color:#b5b5b5 } button:disabled { opacity:.45; cursor:default }
button:hover:not(:disabled) { background:var(--sel) }
button.primary { background:var(--acc); border-color:var(--acc); color:#fff; font-weight:600 }
button.primary:hover:not(:disabled) { filter:brightness(1.1); background:var(--acc) }
button.link { height:auto; border:0; background:none; color:var(--acc); padding:0 }
button.link:hover { text-decoration:underline; background:none }
.msg { margin:6px 0 0; color:var(--mut) }
.bulk { padding:6px 8px; border:1px dashed var(--line); border-radius:6px } .bulk.on { background:var(--sel) }
.tablewrap { max-height:calc(100vh - 330px); min-height:160px; overflow:auto; border:1px solid var(--line); border-radius:6px }
table { border-collapse:collapse; width:100% }
th { position:sticky; top:0; background:var(--card); text-align:left; border-bottom:1px solid var(--line); padding:5px 8px; z-index:1 }
td { padding:2px 8px; border-bottom:1px solid var(--line); vertical-align:middle }
tr.warn { background:var(--warn) } tr.sel { background:var(--sel) } tr.off td { opacity:.4 }
input.title { width:100%; min-width:160px; height:24px; border-color:transparent; background:transparent } input.title:focus { border-color:var(--acc) }
.file { max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--mut) }
.why { color:var(--mut); font-size:12px } .note { color:#c0560f }
.tag { margin-left:6px; font-size:11px; border:1px solid var(--line); border-radius:3px; padding:0 4px }
.badge { padding:1px 8px; border-radius:10px; font-size:12px; color:#fff; background:#7a8794 }
.badge.high { background:#2e8b57 } .badge.medium { background:#c98a0b } .badge.low { background:#c0560f } .badge.none { background:#b3261e }
.review, .report { background:var(--bg); border:1px solid var(--line); border-radius:6px; padding:8px 10px; max-height:200px; overflow:auto; font-size:12px; white-space:pre-wrap }
.pager { justify-content:center }
.statusbar { display:flex; gap:18px; align-items:center; height:24px; padding:0 12px; border-top:1px solid var(--line); background:var(--card); color:var(--mut); font-size:12px; flex:none }
.st-msg { flex:1; text-align:left; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--fg) }
.modal { position:fixed; inset:0; background:rgba(0,0,0,.35); display:flex; align-items:center; justify-content:center; z-index:10 }
.dialog { background:var(--card); border:1px solid var(--line); border-radius:8px; width:min(720px, 94vw); max-height:86vh; overflow:auto; padding:14px 18px }
.dhead { display:flex; align-items:center; gap:10px } .dhead b { flex:1 }
.dialog pre { white-space:pre-wrap; font-size:12px; background:var(--bg); padding:8px 10px; border-radius:6px }
.dialog .logo { width:28px; height:28px }
</style>
