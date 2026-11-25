<script setup>
import { ref, computed, onMounted, watch } from 'vue'

const sources = ref([])
const platforms = ref([])
const source = ref('folder')
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

const native = () => window.pywebview && window.pywebview.api
async function browse(target) {
  const p = await window.pywebview.api.pick_folder()
  if (p) { if (target === 'src') path.value = p; else exp.value.out = p }
}
const api = async (url, body) => {
  const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {})
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || r.statusText) }
  return r.json()
}

onMounted(async () => {
  sources.value = await api('/api/sources')
  platforms.value = await api('/api/platforms')
})

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
    msg.value = `找到 ${d.count} 筆，${nCheck.value} 筆需要檢查`
    fOnly.value = nCheck.value ? 'check' : 'all'
  } catch (e) { msg.value = '錯誤：' + e.message } finally { busy.value = false }
}
async function update(ids, patch) {
  await api('/api/entries/update', { ids, ...patch })
  const set = new Set(ids)
  rows.value.forEach(r => {
    if (!set.has(r.id)) return
    Object.assign(r, patch)
    if (patch.platform !== undefined) { r.conf = 'high'; r.reason = '手動'; r.notes = [] }
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
  try { report.value = await api('/api/export', exp.value); msg.value = '匯出完成' }
  catch (e) { msg.value = '錯誤：' + e.message } finally { busy.value = false }
}
const confLabel = { high: '高', medium: '中', low: '低', none: '無' }
</script>

<template>
  <header>
    <h1>PoniaMDM</h1>
    <span class="sub">Ponia Metadata Manager</span>
  </header>

  <section class="card">
    <h2>1. 來源</h2>
    <div class="row">
      <select v-model="source">
        <option v-for="s in sources" :key="s.key" :value="s.key">{{ s.label }}</option>
      </select>
      <input class="grow" v-model="path" placeholder="資料夾路徑，例如 E:\UserROM" @keyup.enter="scan" />
      <button v-if="native()" @click="browse('src')">瀏覽…</button>
      <select v-model="engine" title="無法判斷的街機 romset 要歸到哪個引擎">
        <option>MAME</option><option>FBNeo</option>
      </select>
      <button class="primary" :disabled="busy || !path" @click="scan">{{ busy ? '處理中…' : '掃描' }}</button>
    </div>
    <p v-if="msg" class="msg">{{ msg }}</p>
  </section>

  <template v-if="rows.length">
    <section class="card">
      <h2>2. 偵測結果 <small>（{{ rows.length }} 筆；{{ counts.map(([k, n]) => k + ' ' + n).join('、') }}）</small></h2>
      <div class="row">
        <input v-model="search" placeholder="搜尋標題或檔名" />
        <select v-model="fPlat">
          <option value="">所有機種</option>
          <option v-for="p in platforms" :key="p.key" :value="p.key">{{ p.key }}</option>
        </select>
        <select v-model="fOnly">
          <option value="all">全部</option>
          <option value="check">只看需要檢查（{{ nCheck }}）</option>
          <option value="edited">只看我改過的</option>
        </select>
        <button @click="showReview = !showReview" v-if="review.length">提醒（{{ review.length }}）</button>
      </div>
      <pre v-if="showReview" class="review">{{ review.join('\n') }}</pre>

      <div class="row bulk" :class="{ on: selected.size }">
        <span>已選 {{ selected.size }} 筆</span>
        <button class="link" @click="selectAllFiltered">選取篩選結果全部（{{ filtered.length }}）</button>
        <select v-model="bulkPlat">
          <option value="">改成機種…</option>
          <option v-for="p in platforms" :key="p.key" :value="p.key">{{ p.key }}（{{ p.collection }}）</option>
        </select>
        <button :disabled="!selected.size || !bulkPlat" @click="bulk({ platform: bulkPlat })">套用機種</button>
        <button :disabled="!selected.size" @click="bulk({ hack: true })">設為改版</button>
        <button :disabled="!selected.size" @click="bulk({ hack: false })">取消改版</button>
        <button :disabled="!selected.size" @click="bulk({ include: false })">排除</button>
        <button :disabled="!selected.size" @click="bulk({ include: true })">納入</button>
      </div>

      <div class="tablewrap">
        <table>
          <thead><tr>
            <th><input type="checkbox" :checked="allShown" @change="toggleAll" /></th>
            <th>標題</th><th>檔案</th><th>機種</th><th>改版</th><th>信心</th><th>依據 / 備註</th>
          </tr></thead>
          <tbody>
            <tr v-for="r in shown" :key="r.id" :class="{ off: !r.include, warn: needsCheck(r) && !r.edited, sel: selected.has(r.id) }">
              <td><input type="checkbox" :checked="selected.has(r.id)" @change="toggle(r.id)" /></td>
              <td><input class="title" :value="r.title" @change="update([r.id], { title: $event.target.value })" /></td>
              <td class="file" :title="r.src">{{ r.file }}<span v-if="r.archive" class="tag">壓縮</span></td>
              <td>
                <select :value="r.platform" @change="update([r.id], { platform: $event.target.value })">
                  <option v-for="p in platforms" :key="p.key" :value="p.key">{{ p.key }}</option>
                  <option v-if="!platforms.some(p => p.key === r.platform)" :value="r.platform">{{ r.platform }}</option>
                </select>
              </td>
              <td><input type="checkbox" :checked="r.hack" @change="update([r.id], { hack: $event.target.checked })" /></td>
              <td><span class="badge" :class="r.conf">{{ confLabel[r.conf] }}</span></td>
              <td class="why">{{ r.reason }}<span v-for="n in r.notes" :key="n" class="note"> ⚠ {{ n }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!filtered.length" class="msg">沒有符合條件的項目。</p>
      <div class="row pager">
        <button :disabled="page === 0" @click="page--">上一頁</button>
        <span>{{ page + 1 }} / {{ pages }}（{{ filtered.length }} 筆）</span>
        <button :disabled="page + 1 >= pages" @click="page++">下一頁</button>
      </div>
    </section>

    <section class="card">
      <h2>3. 匯出</h2>
      <div class="row">
        <input class="grow" v-model="exp.out" placeholder="輸出資料夾，例如 E:\Ponia.Roms" />
        <button v-if="native()" @click="browse('out')">瀏覽…</button>
        <select v-model="exp.roms">
          <option value="none">只寫 metadata 與圖片</option>
          <option value="copy">同時複製 ROM</option>
          <option value="link">同時硬連結 ROM</option>
          <option value="move">同時搬移 ROM（可復原）</option>
        </select>
        <select v-model="exp.zh">
          <option value="keep">文字維持原樣</option>
          <option value="trad">簡體轉繁體</option>
        </select>
        <button class="primary" :disabled="busy || !exp.out" @click="doExport">匯出</button>
      </div>
      <div v-if="report" class="report">
        <div v-for="(n, f) in report.folders" :key="f">{{ f }}：{{ n }} 款</div>
        <div v-for="w in report.warnings" :key="w" class="note">⚠ {{ w }}</div>
      </div>
    </section>
  </template>
</template>

<style>
:root { --bg:#f6f7f9; --card:#fff; --fg:#1d2733; --mut:#6b7785; --line:#dde2e8; --acc:#0b6ea8; --warn:#fff6e0; --sel:#e6f2fb; }
@media (prefers-color-scheme: dark) { :root { --bg:#14181d; --card:#1d242c; --fg:#e6eaee; --mut:#93a0ad; --line:#2f3a45; --acc:#4aa8e0; --warn:#3a3118; --sel:#1f3446; } }
* { box-sizing: border-box }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui,"Microsoft JhengHei",sans-serif }
header { padding:14px 20px; display:flex; align-items:baseline; gap:12px }
h1 { margin:0; font-size:20px } h2 { margin:0 0 10px; font-size:15px } h2 small { color:var(--mut); font-weight:400 }
.sub { color:var(--mut) }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; margin:0 20px 14px; padding:14px 16px }
.row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:6px 0 }
.grow { flex:1; min-width:200px }
input, select, button { font:inherit; color:var(--fg); background:var(--card); border:1px solid var(--line); border-radius:5px; padding:5px 8px }
button { cursor:pointer } button:disabled { opacity:.45; cursor:default }
button.primary { background:var(--acc); border-color:var(--acc); color:#fff }
button.link { border:0; background:none; color:var(--acc); padding:0 }
.msg { margin:6px 0 0; color:var(--mut) }
.bulk { padding:6px 8px; border:1px dashed var(--line); border-radius:6px } .bulk.on { background:var(--sel) }
.tablewrap { max-height:58vh; overflow:auto; border:1px solid var(--line); border-radius:6px }
table { border-collapse:collapse; width:100% } th { position:sticky; top:0; background:var(--card); text-align:left; border-bottom:1px solid var(--line); padding:6px 8px; z-index:1 }
td { padding:3px 8px; border-bottom:1px solid var(--line); vertical-align:middle }
tr.warn { background:var(--warn) } tr.sel { background:var(--sel) } tr.off td { opacity:.4 }
input.title { width:100%; min-width:160px; border-color:transparent; background:transparent } input.title:focus { border-color:var(--acc) }
.file { max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--mut) }
.why { color:var(--mut); font-size:12px } .note { color:#c0560f }
.tag { margin-left:6px; font-size:11px; border:1px solid var(--line); border-radius:3px; padding:0 4px }
.badge { padding:1px 8px; border-radius:10px; font-size:12px; color:#fff; background:#7a8794 }
.badge.high { background:#2e8b57 } .badge.medium { background:#c98a0b } .badge.low { background:#c0560f } .badge.none { background:#b3261e }
.review, .report { background:var(--bg); border:1px solid var(--line); border-radius:6px; padding:8px 10px; max-height:200px; overflow:auto; font-size:12px; white-space:pre-wrap }
.pager { justify-content:center }
@media (max-width:700px) { .card { margin:0 10px 12px } }
</style>
