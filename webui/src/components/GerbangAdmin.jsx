/**
 * Gerbang kata sandi untuk halaman pengaturan.
 *
 * Pengaturan memuat hal yang bisa merusak jalannya aplikasi (perangkat audio,
 * kata bangun, alamat server AI), jadi hanya admin yang boleh mengubahnya.
 *
 * Kata sandi TIDAK ditanam di kode antarmuka. Nilainya diperiksa oleh mesin AI
 * lewat `/api/admin/verifikasi`, sehingga berkas JavaScript yang bisa dibaca
 * siapa pun tidak memuat kata sandinya. Ini bukan pengamanan tingkat tinggi —
 * tujuannya mencegah pengguna biasa masuk tanpa sengaja.
 */

import { useCallback, useEffect, useState } from 'react'
import { t } from '../lib/translations'

const KUNCI_SIMPAN = 'sela-admin-terbuka'

export default function GerbangAdmin({ children }) {
  const [terbuka, setTerbuka] = useState(false)
  const [sandi, setSandi] = useState('')
  const [galat, setGalat] = useState('')
  const [memeriksa, setMemeriksa] = useState(false)
  const [memuat, setMemuat] = useState(true)

  // Buka sekali per sesi peramban supaya tidak mengetik berulang.
  useEffect(() => {
    try {
      setTerbuka(sessionStorage.getItem(KUNCI_SIMPAN) === '1')
    } catch (_) {
      // Mode privasi ketat: biarkan terkunci.
    }
    setMemuat(false)
  }, [])

  const kirim = useCallback(
    async (e) => {
      e?.preventDefault?.()
      if (!sandi.trim()) return
      setMemeriksa(true)
      setGalat('')
      try {
        const r = await fetch('/api/admin/verifikasi', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sandi }),
        })
        const d = await r.json()
        if (d.ok) {
          setTerbuka(true)
          setSandi('')
          try {
            sessionStorage.setItem(KUNCI_SIMPAN, '1')
          } catch (_) {
            // Diabaikan.
          }
        } else {
          setGalat(d.error || t.id.adminWrong)
        }
      } catch (_) {
        setGalat(t.id.adminUnreachable)
      } finally {
        setMemeriksa(false)
      }
    },
    [sandi],
  )

  if (memuat) return null
  if (terbuka) return children

  return (
    <div className="max-w-sm mx-auto px-4 py-10">
      <form
        onSubmit={kirim}
        className="rounded-2xl border border-gray-200/80 dark:border-slate-700/70 bg-white/80 dark:bg-slate-900/70 backdrop-blur-xl shadow-sm p-6 space-y-4"
      >
        <div className="text-center space-y-1">
          <div className="w-12 h-12 mx-auto rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center text-blue-600 dark:text-blue-300 text-xl">
            🔒
          </div>
          <h2 className="text-sm font-bold text-gray-700 dark:text-gray-200 pt-1">
            {t.id.adminTitle}
          </h2>
          <p className="text-[11px] text-gray-400 dark:text-gray-500 leading-relaxed">
            {t.id.adminDesc}
          </p>
        </div>

        <input
          type="password"
          value={sandi}
          onChange={(e) => setSandi(e.target.value)}
          placeholder={t.id.adminPlaceholder}
          autoFocus
          className="w-full text-xs px-3 py-2 rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-gray-700 dark:text-gray-200 outline-none focus:border-blue-500"
        />

        {galat && (
          <p className="text-[11px] text-red-500 text-center">{galat}</p>
        )}

        <button
          type="submit"
          disabled={memeriksa || !sandi.trim()}
          className="w-full text-xs font-semibold py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40"
        >
          {memeriksa ? t.id.adminChecking : t.id.adminUnlock}
        </button>
      </form>
    </div>
  )
}
