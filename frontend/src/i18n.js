import { ref } from 'vue'
import zhTW from './locales/zh-TW.js'
import en from './locales/en.js'
import zhCN from './locales/zh-CN.js'
import es from './locales/es.js'
import pt from './locales/pt.js'
import ru from './locales/ru.js'
import ja from './locales/ja.js'
import fr from './locales/fr.js'
import de from './locales/de.js'

// Native names, in the order shown in the Language menu.
export const LANGS = [
  { code: 'en', name: 'English' },
  { code: 'zh-CN', name: '简体中文' },
  { code: 'zh-TW', name: '繁體中文' },
  { code: 'es', name: 'Español' },
  { code: 'pt', name: 'Português' },
  { code: 'ru', name: 'Русский' },
  { code: 'ja', name: '日本語' },
  { code: 'fr', name: 'Français' },
  { code: 'de', name: 'Deutsch' },
]
const BUNDLES = { 'zh-TW': zhTW, en, 'zh-CN': zhCN, es, pt, ru, ja, fr, de }

export const lang = ref('zh-TW')

// First run: follow the OS / WebView2 UI language; unsupported languages fall back to English.
export function detectLang() {
  const l = ((navigator.languages && navigator.languages[0]) || navigator.language || '').toLowerCase()
  if (l.startsWith('zh')) return /tw|hk|mo|hant/.test(l) ? 'zh-TW' : 'zh-CN'
  const base = l.split('-')[0]
  return BUNDLES[base] ? base : 'en'
}

export function setLang(code) {
  lang.value = BUNDLES[code] ? code : 'zh-TW'
  document.documentElement.lang = lang.value
}

// t('key', { n: 3 }) -> string; falls back to zh-TW, then to the key itself.
export function t(key, params) {
  const s = (BUNDLES[lang.value] || {})[key] ?? zhTW[key] ?? key
  return params ? s.replace(/\{(\w+)\}/g, (_, k) => (params[k] ?? '')) : s
}
