/* eslint-disable react/prop-types */
/**
 * Kartu kamera melayang yang bisa digeser.
 *
 * Membuka kamera perangkat lewat getUserMedia (berjalan di localhost, jadi
 * dianggap konteks aman oleh peramban). Foto yang diambil:
 *   1. dikirim ke mesin AI lewat WebSocket, sehingga alat "take_photo" milik
 *      py-xiaozhi memakai gambar dari kamera ini - SELA benar-benar melihat;
 *   2. ditampilkan di gelembung percakapan sebagai pesan pengguna.
 *
 * Kartu bisa digeser ke mana saja, bisa ditutup, dan bisa dimatikan total dari
 * halaman Pengaturan.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { t } from '../lib/translations'

const UKURAN = 168
const KUNCI_POSISI = 'sela_kamera_posisi'

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

export default function KartuKamera({ nonce = 0, onBingkai, onTutup }) {
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
  // Nonce terakhir yang sudah diproses, supaya satu permintaan = satu foto.
  const nonceRef = useRef(nonce)

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

  const ambilFoto = useCallback(async () => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const kanvas = document.createElement('canvas')
    kanvas.width = video.videoWidth
    kanvas.height = video.videoHeight
    const ctx = kanvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, kanvas.width, kanvas.height)
    const data = kanvas.toDataURL('image/jpeg', 0.82)

    setKilat(true)
    setTimeout(() => setKilat(false), 260)
    onBingkaiRef.current?.(data)
  }, [])

  // Permintaan foto dari mesin AI atau dari teks pengguna.
  useEffect(() => {
    if (nonce === nonceRef.current) return
    nonceRef.current = nonce
    ambilFoto()
  }, [nonce, ambilFoto])

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
          </span>
          <button
            type="button"
            onClick={onTutup}
            className="w-4 h-4 rounded-full flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 transition-all"
            title={t.id.close}
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
            onClick={ambilFoto}
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
