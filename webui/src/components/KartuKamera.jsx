/* eslint-disable react/prop-types */
/**
 * Kartu kamera melayang yang bisa digeser.
 *
 * Membuka kamera perangkat lewat getUserMedia (berjalan di localhost, jadi
 * dianggap konteks aman oleh peramban).
 *
 * Ada dua jalur gambar:
 *   1. **Foto sadar** (tombol "Ambil Foto") - masuk ke kotak teks sebagai
 *      lampiran, supaya pengguna bisa bertanya tentang foto itu. Tidak
 *      langsung muncul sebagai gelembung percakapan.
 *   2. **Bingkai hidup** - dikirim berkala ke mesin AI tanpa mengganggu
 *      pengguna, sehingga saat pengguna bertanya "saya lagi ngapain?" alat
 *      kamera py-xiaozhi sudah punya gambar yang masih segar. SELA seolah
 *      melihat terus.
 *
 * Kartu bisa digeser, dilipat jadi ikon kecil (tombol silang), dan
 * dimatikan total dari halaman Pengaturan.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { t } from '../lib/translations'

const UKURAN = 168
const KUNCI_POSISI = 'sela_kamera_posisi'

/** Jeda antar bingkai hidup. Harus lebih pendek dari masa segar bingkai di
 *  sisi Python (``MAKS_UMUR_BINGKAI_S`` = 12 detik). */
const JEDA_HIDUP_MS = 5000

function posisiAwal() {
  if (typeof window === 'undefined') return { x: 24, y: 96 }
  try {
    const tersimpan = JSON.parse(localStorage.getItem(KUNCI_POSISI) || 'null')
    if (tersimpan && Number.isFinite(tersimpan.x) && Number.isFinite(tersimpan.y)) {
      return tersimpan
    }
  } catch (_) {
    // diabaikan
  }
  return { x: 24, y: 96 }
}

export default function KartuKamera({
  permintaan = { nonce: 0, sumber: 'ai' },
  onBingkai,
  onBingkaiHidup,
  onTutup,
}) {
  const [posisi, setPosisi] = useState(posisiAwal)
  const [galat, setGalat] = useState('')
  const [siap, setSiap] = useState(false)
  const [kilat, setKilat] = useState(false)

  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const seretRef = useRef(null)
  const posisiRef = useRef(posisi)
  posisiRef.current = posisi
  const onBingkaiRef = useRef(onBingkai)
  onBingkaiRef.current = onBingkai
  const onBingkaiHidupRef = useRef(onBingkaiHidup)
  onBingkaiHidupRef.current = onBingkaiHidup
  // Nonce terakhir yang sudah diproses, supaya satu permintaan = satu foto.
  const nonceRef = useRef(permintaan.nonce)

  // --- Kamera ---
  useEffect(() => {
    let dibatalkan = false

    const buka = async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setGalat(t.id.cameraNoSupport)
        return
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
          audio: false,
        })
        if (dibatalkan) {
          stream.getTracks().forEach((tr) => tr.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play().catch(() => {})
        }
        setSiap(true)
        setGalat('')
      } catch (e) {
        setGalat(e?.name === 'NotAllowedError' ? t.id.cameraDenied : t.id.cameraFail)
      }
    }

    buka()
    return () => {
      dibatalkan = true
      streamRef.current?.getTracks?.().forEach((tr) => tr.stop())
      streamRef.current = null
    }
  }, [])

  const potret = useCallback(() => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return null
    const kanvas = document.createElement('canvas')
    kanvas.width = video.videoWidth
    kanvas.height = video.videoHeight
    const ctx = kanvas.getContext('2d')
    if (!ctx) return null
    ctx.drawImage(video, 0, 0, kanvas.width, kanvas.height)
    return kanvas.toDataURL('image/jpeg', 0.82)
  }, [])

  const ambilFoto = useCallback(() => {
    const data = potret()
    if (!data) return
    setKilat(true)
    setTimeout(() => setKilat(false), 260)
    onBingkaiRef.current?.(data)
  }, [potret])

  // Bingkai hidup: dikirim berkala ke mesin AI tanpa mengganggu pengguna,
  // supaya pertanyaan seperti "saya lagi ngapain?" bisa dijawab dari kamera
  // walau pengguna tidak menekan tombol foto.
  useEffect(() => {
    if (!siap) return
    const kirim = () => {
      const data = potret()
      if (data) onBingkaiHidupRef.current?.(data)
    }
    kirim() // satu bingkai begitu kamera siap
    const timer = setInterval(kirim, JEDA_HIDUP_MS)
    return () => clearInterval(timer)
  }, [siap, potret])

  // Permintaan foto dari mesin AI atau dari teks pengguna.
  useEffect(() => {
    if (permintaan.nonce === nonceRef.current) return
    nonceRef.current = permintaan.nonce
    ambilFoto(permintaan.sumber)
  }, [permintaan, ambilFoto])

  // --- Geser kartu ---
  const mulaiSeret = (e) => {
    const p = posisiRef.current
    seretRef.current = { dx: e.clientX - p.x, dy: e.clientY - p.y }
    e.currentTarget.setPointerCapture?.(e.pointerId)
  }

  const seretKartu = (e) => {
    const s = seretRef.current
    if (!s) return
    const maksX = Math.max(0, window.innerWidth - UKURAN - 8)
    const maksY = Math.max(0, window.innerHeight - UKURAN - 8)
    setPosisi({
      x: Math.min(maksX, Math.max(8, e.clientX - s.dx)),
      y: Math.min(maksY, Math.max(8, e.clientY - s.dy)),
    })
  }

  const lepasSeret = () => {
    if (!seretRef.current) return
    seretRef.current = null
    try {
      localStorage.setItem(KUNCI_POSISI, JSON.stringify(posisiRef.current))
    } catch (_) {
      // diabaikan
    }
  }

  return (
    <div
      data-kamera="1"
      className="fixed z-40 select-none"
      style={{ left: posisi.x, top: posisi.y, width: UKURAN }}
    >
      <div className="rounded-2xl overflow-hidden bg-white/92 dark:bg-slate-900/92 backdrop-blur-xl border border-white/60 dark:border-slate-700/60 shadow-2xl">
        {/* Bilah geser */}
        <div
          onPointerDown={mulaiSeret}
          onPointerMove={seretKartu}
          onPointerUp={lepasSeret}
          onPointerCancel={lepasSeret}
          className="flex items-center justify-between gap-1 px-2 py-1.5 cursor-grab active:cursor-grabbing bg-gray-50/80 dark:bg-slate-800/80"
          title={t.id.cameraDrag}
        >
          <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-gray-400">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="9" cy="6" r="1.6" /><circle cx="15" cy="6" r="1.6" />
              <circle cx="9" cy="12" r="1.6" /><circle cx="15" cy="12" r="1.6" />
              <circle cx="9" cy="18" r="1.6" /><circle cx="15" cy="18" r="1.6" />
            </svg>
            {t.id.cameraCard}
            {siap && (
              <span
                className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"
                title={t.id.cameraLive}
              />
            )}
          </span>
          <button
            type="button"
            data-kamera-lipat="1"
            onClick={onTutup}
            className="w-4 h-4 rounded-full flex items-center justify-center text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/40 transition-all"
            title={t.id.cameraHide}
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={2.6} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Pratinjau */}
        <div className="relative bg-slate-900 aspect-[4/3]">
          <video
            ref={videoRef}
            playsInline
            muted
            className="w-full h-full object-cover -scale-x-100"
          />
          {!siap && (
            <div className="absolute inset-0 flex items-center justify-center px-3 text-center">
              <p className="text-[10px] leading-snug text-gray-300">
                {galat || t.id.cameraStarting}
              </p>
            </div>
          )}
          {kilat && <div className="absolute inset-0 bg-white animate-fade-in" />}
        </div>

        {/* Tombol */}
        <div className="p-2">
          <button
            type="button"
            data-kamera-ambil="1"
            onClick={() => ambilFoto('pengguna')}
            disabled={!siap}
            className="w-full text-[11px] font-semibold px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            {t.id.cameraTake}
          </button>
        </div>
      </div>
    </div>
  )
}
