/**
 * Pemutar musik SELA di dalam panel percakapan.
 *
 * Menampilkan lagu yang sedang diputar beserta bilah kemajuan dan tombol
 * jeda/lanjut, mundur 15 detik, maju 15 detik, dan hentikan. Muncul otomatis
 * begitu mesin AI mulai memutar musik, dan hilang saat musik dihentikan.
 */

import { useEffect, useRef, useState } from 'react'
import { t } from '../lib/translations'

/** Ubah detik menjadi "m:ss". */
function waktu(detik) {
  const d = Math.max(0, Math.floor(Number(detik) || 0))
  const m = Math.floor(d / 60)
  const s = d % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function PemutarMusik({ musik, aksi }) {
  const { song, state, position, duration } = musik || {}
  // Kemajuan diperbarui lokal agar bilah bergerak halus di antara pembaruan
  // dari mesin AI (yang datang beberapa detik sekali).
  const [posisi, setPosisi] = useState(0)
  const acuan = useRef({ pos: 0, waktu: Date.now(), jalan: false })

  useEffect(() => {
    const pos = Number(position) || 0
    const jalan = state === 'playing'
    acuan.current = { pos, waktu: Date.now(), jalan }
    setPosisi(pos)
  }, [position, state, song])

  useEffect(() => {
    if (state !== 'playing') return undefined
    const timer = setInterval(() => {
      const { pos, waktu: kapan, jalan } = acuan.current
      if (!jalan) return
      setPosisi(pos + (Date.now() - kapan) / 1000)
    }, 500)
    return () => clearInterval(timer)
  }, [state])

  if (!song || state === 'stopped' || state === 'completed') return null

  const total = Number(duration) || 0
  const persen = total > 0 ? Math.min(100, (posisi / total) * 100) : 0
  const sedangMain = state === 'playing'

  const kirim = (jenis, nilai) => {
    aksi?.kendaliMusik?.(jenis, nilai)
  }

  const lompat = (e) => {
    if (total <= 0) return
    const kotak = e.currentTarget.getBoundingClientRect()
    const rasio = Math.min(1, Math.max(0, (e.clientX - kotak.left) / kotak.width))
    kirim('seek', Math.round(rasio * 100))
  }

  return (
    <div className="mx-1 mb-3 rounded-2xl border border-gray-100/80 dark:border-white/10 bg-white/95 dark:bg-slate-800/95 shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-3.5 pt-3">
        <span className="w-9 h-9 shrink-0 rounded-xl bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 flex items-center justify-center text-base">
          {sedangMain ? '♪' : '❚❚'}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold text-gray-800 dark:text-gray-100 truncate">
            {song}
          </p>
          <p className="text-[10px] text-gray-400 dark:text-gray-500">
            {sedangMain ? t.id.musicPlaying : t.id.musicPaused}
          </p>
        </div>
      </div>

      {/* Bilah kemajuan: bisa diklik untuk melompat */}
      <div className="px-3.5 pt-2.5">
        <div
          onClick={lompat}
          className="group h-1.5 w-full rounded-full bg-gray-200 dark:bg-slate-700 cursor-pointer"
        >
          <div
            className="h-full rounded-full bg-blue-500 transition-[width] duration-300"
            style={{ width: `${persen}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-500 pt-1 tabular-nums">
          <span>{waktu(posisi)}</span>
          <span>{total > 0 ? waktu(total) : '--:--'}</span>
        </div>
      </div>

      <div className="flex items-center justify-center gap-1 pb-2.5 pt-0.5">
        <button
          onClick={() => kirim('mundur')}
          title={t.id.musicBack}
          className="w-9 h-9 rounded-xl text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 text-xs font-semibold transition-colors"
        >
          −15
        </button>
        <button
          onClick={() => kirim(sedangMain ? 'pause' : 'resume')}
          title={sedangMain ? t.id.musicPause : t.id.musicResume}
          className="w-11 h-11 rounded-full bg-blue-600 text-white hover:bg-blue-700 flex items-center justify-center text-sm shadow-sm transition-colors"
        >
          {sedangMain ? '❚❚' : '▶'}
        </button>
        <button
          onClick={() => kirim('maju')}
          title={t.id.musicForward}
          className="w-9 h-9 rounded-xl text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 text-xs font-semibold transition-colors"
        >
          +15
        </button>
        <button
          onClick={() => kirim('stop')}
          title={t.id.musicStop}
          className="w-9 h-9 rounded-xl text-gray-500 dark:text-gray-400 hover:bg-red-50 dark:hover:bg-red-900/30 hover:text-red-500 text-sm transition-colors"
        >
          ■
        </button>
      </div>
    </div>
  )
}
