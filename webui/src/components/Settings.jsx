/* eslint-disable react/prop-types */
/**
 * Halaman Pengaturan.
 *
 * Nilai yang ditampilkan di sini benar-benar dibaca dari config mesin AI
 * (py-xiaozhi) lewat /api/config, dan setiap perubahan langsung disimpan
 * serta diterapkan tanpa memulai ulang aplikasi.
 */

import { useEffect, useState } from 'react'
import { t } from '../lib/translations'

const IconChevronLeft = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
  </svg>
)

function Kartu({ judul, children }) {
  return (
    <section className="rounded-2xl border border-gray-200/80 dark:border-slate-700/70 bg-white/80 dark:bg-slate-900/70 backdrop-blur-xl shadow-sm overflow-hidden">
      <h2 className="px-5 pt-4 pb-2 text-[11px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500">
        {judul}
      </h2>
      <div className="px-5 pb-4 divide-y divide-gray-100 dark:divide-slate-800">{children}</div>
    </section>
  )
}

function Baris({ label, keterangan, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{label}</p>
        {keterangan && <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{keterangan}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

function Sakelar({ aktif, onChange, disabled }) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange?.(!aktif)}
      disabled={disabled}
      className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${
        aktif ? 'bg-blue-600' : 'bg-gray-300 dark:bg-slate-700'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      aria-pressed={aktif}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 ${
          aktif ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

// Kata bangun yang tersedia di models/en/keywords.txt. Model KWS berbasis BPE
// sehingga kata apa pun bisa ditambahkan lewat tokennya.
const KATA_BANGUN = ['SELA', 'Hai Hai']

const PLATFORM_MUSIK = ['kw', 'kg', 'tx', 'wy', 'mg']
const KUALITAS_MUSIK = ['128k', '192k', '320k', 'flac']

export default function Settings({ onBack, theme, setTheme, terhubung = false }) {
  const [config, setConfig] = useState(null)
  const [perangkat, setPerangkat] = useState({ input: [], output: [] })
  const [galat, setGalat] = useState('')
  const [menyimpan, setMenyimpan] = useState(false)
  // Alamat server disunting lokal dulu, baru dikirim saat tombol Simpan ditekan
  // (supaya tidak menyimpan alamat setengah diketik).
  const [alamatServer, setAlamatServer] = useState('')

  const muat = async () => {
    try {
      const [rCfg, rDev] = await Promise.all([
        fetch('/api/config'),
        fetch('/api/devices'),
      ])
      const dCfg = await rCfg.json()
      const dDev = await rDev.json()
      if (dCfg.ok) {
        setConfig(dCfg.config)
        setAlamatServer(dCfg.config?.serverUrl || '')
      } else setGalat(dCfg.error || 'Gagal memuat pengaturan')
      if (dDev.ok) setPerangkat(dDev.devices)
    } catch (e) {
      setGalat('Tidak bisa menghubungi mesin AI. Pastikan aplikasi SELA sedang berjalan.')
    }
  }

  useEffect(() => {
    muat()
  }, [])

  const simpan = async (updates) => {
    setConfig((lama) => ({ ...lama, ...updates }))
    setMenyimpan(true)
    try {
      const r = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates }),
      })
      const d = await r.json()
      if (!d.ok) setGalat(d.error || 'Gagal menyimpan')
      else setGalat('')
    } catch (e) {
      setGalat('Gagal menyimpan ke mesin AI.')
    } finally {
      setMenyimpan(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="sticky top-0 z-10 flex items-center gap-3 px-5 py-4 bg-[#f8faff]/90 dark:bg-slate-950/90 backdrop-blur-xl border-b border-gray-100 dark:border-slate-800">
        <button
          onClick={onBack}
          className="w-9 h-9 flex items-center justify-center rounded-xl hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300 transition-colors"
          aria-label={t.id.back}
        >
          <IconChevronLeft />
        </button>
        <div>
          <h1 className="text-base font-bold text-gray-800 dark:text-gray-100">{t.id.settingsTitle}</h1>
          <p className="text-[11px] text-gray-400 dark:text-gray-500">{t.id.settingsSubtitle}</p>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-5 space-y-4">
        {galat && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700 px-4 py-3 text-xs text-amber-700 dark:text-amber-300">
            {galat}
          </div>
        )}

        <Kartu judul={t.id.sectionDisplay}>
          <Baris label={t.id.theme}>
            <div className="flex rounded-xl overflow-hidden border border-gray-200 dark:border-slate-700">
              {['light', 'dark'].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setTheme?.(mode)}
                  className={`px-3 py-1.5 text-xs font-semibold transition-colors ${
                    theme === mode
                      ? 'bg-blue-600 text-white'
                      : 'bg-white dark:bg-slate-900 text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {mode === 'light' ? t.id.themeLight : t.id.themeDark}
                </button>
              ))}
            </div>
          </Baris>
          <Baris label={t.id.language}>
            <span className="text-xs font-semibold text-gray-600 dark:text-gray-300">
              {t.id.languageValue}
            </span>
          </Baris>
        </Kartu>

        <Kartu judul={t.id.sectionAi}>
          <Baris label={t.id.wakeWord} keterangan={t.id.wakeWordDesc}>
            <Sakelar
              aktif={Boolean(config?.wakeWord)}
              disabled={!config}
              onChange={(v) => simpan({ wakeWord: v })}
            />
          </Baris>
          <Baris
            label={t.id.wakeWordChoice}
            keterangan={t.id.wakeWordChoiceDesc}
          >
            <select
              value={config?.wakeWordText || 'SELA'}
              disabled={!config}
              onChange={(e) => simpan({ wakeWordText: e.target.value })}
              className="max-w-[190px] text-xs px-2 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-600 dark:text-gray-300 outline-none"
            >
              {KATA_BANGUN.map((k) => (
                <option key={k} value={k}>
                  {k === 'SELA' ? 'SELA' : 'Hai Hai'}
                </option>
              ))}
            </select>
          </Baris>
          <Baris
            label={t.id.wakeWordSensitivity}
            keterangan={t.id.wakeWordSensitivityDesc}
          >
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="0.05"
                max="0.6"
                step="0.05"
                value={config?.wakeWordThreshold ?? 0.2}
                disabled={!config}
                onChange={(e) =>
                  simpan({ wakeWordThreshold: Number(e.target.value) })
                }
                className="w-28 accent-blue-600"
              />
              <span className="text-xs font-mono text-gray-500 dark:text-gray-400 w-9 text-right">
                {(config?.wakeWordThreshold ?? 0.2).toFixed(2)}
              </span>
            </div>
          </Baris>
          <Baris label={t.id.serverUrlLabel} keterangan={t.id.serverUrlDesc}>
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                value={alamatServer}
                disabled={!config}
                onChange={(e) => setAlamatServer(e.target.value)}
                placeholder="wss://..."
                className="w-[190px] text-[11px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-600 dark:text-gray-300 outline-none"
              />
              <button
                onClick={() => simpan({ serverUrl: alamatServer.trim() })}
                disabled={!config || alamatServer.trim() === (config?.serverUrl || '')}
                className="text-[11px] px-2 py-1.5 rounded-lg bg-blue-600 text-white font-semibold disabled:opacity-40"
              >
                {t.id.simpan}
              </button>
            </div>
          </Baris>
          <Baris label={t.id.connectionStatus}>
            <span
              className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
                terhubung ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${terhubung ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              {terhubung ? t.id.connected : t.id.disconnected}
            </span>
          </Baris>
        </Kartu>

        <Kartu judul={t.id.sectionMusic}>
          <Baris label={t.id.musicPlatform}>
            <select
              value={config?.musicPlatform || 'kw'}
              disabled={!config}
              onChange={(e) => simpan({ musicPlatform: e.target.value })}
              className="max-w-[190px] text-xs px-2 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-600 dark:text-gray-300 outline-none"
            >
              {PLATFORM_MUSIK.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </Baris>
          <Baris label={t.id.musicQuality}>
            <select
              value={config?.musicQuality || '320k'}
              disabled={!config}
              onChange={(e) => simpan({ musicQuality: e.target.value })}
              className="max-w-[190px] text-xs px-2 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-600 dark:text-gray-300 outline-none"
            >
              {KUALITAS_MUSIK.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </Baris>
        </Kartu>

        <Kartu judul={t.id.sectionAudio}>
          <Baris label={t.id.inputDevice}>
            <select
              value={config?.inputDevice || ''}
              disabled={!config}
              onChange={(e) => simpan({ inputDevice: e.target.value })}
              className="max-w-[190px] text-xs px-2 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-600 dark:text-gray-300 outline-none"
            >
              <option value="">{t.id.defaultDevice}</option>
              {perangkat.input.map((d) => (
                <option key={d.index} value={d.name}>
                  {d.name}
                </option>
              ))}
            </select>
          </Baris>
          <Baris label={t.id.outputDevice}>
            <select
              value={config?.outputDevice || ''}
              disabled={!config}
              onChange={(e) => simpan({ outputDevice: e.target.value })}
              className="max-w-[190px] text-xs px-2 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-600 dark:text-gray-300 outline-none"
            >
              <option value="">{t.id.defaultDevice}</option>
              {perangkat.output.map((d) => (
                <option key={d.index} value={d.name}>
                  {d.name}
                </option>
              ))}
            </select>
          </Baris>
          <Baris label="Echo Cancellation (AEC)" keterangan="Mengurangi gema pengeras suara agar mikrofon tidak terganggu.">
            <Sakelar
              aktif={Boolean(config?.aec)}
              disabled={!config}
              onChange={(v) => simpan({ aec: v })}
            />
          </Baris>
        </Kartu>

        <Kartu judul={t.id.aboutApp}>
          <Baris label={t.id.version}>
            <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
              {config?.version || '1.0.0'}
            </span>
          </Baris>
          <Baris label="Mesin AI">
            <span className="text-xs font-mono text-gray-500 dark:text-gray-400">py-xiaozhi</span>
          </Baris>
        </Kartu>

        {menyimpan && (
          <p className="text-center text-[11px] text-blue-500 font-medium">Menyimpan...</p>
        )}

        <p className="text-center text-[11px] text-gray-400 dark:text-gray-500 leading-relaxed">
          {t.id.restartNote}
        </p>
      </div>
    </div>
  )
}
