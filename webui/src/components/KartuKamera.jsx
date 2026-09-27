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
 * Kartu bisa digeser, dilipat jadi pil kecil (tombol panah), dan dimatikan
 * total dari halaman Pengaturan.
 *
 * PENTING - kartu ini TIDAK dilepas dari React saat dilipat. Komponen tetap
 * terpasang dan hanya disembunyikan secara visual (``opacity-0``), karena
 * melepasnya akan menghentikan ``getUserMedia`` dan timer bingkai hidup.
 * Akibatnya SELA tidak lagi bisa menjawab "saya lagi ngapain?" padahal
 * pengguna hanya ingin menyembunyikan kartunya. Jangan ganti ``opacity-0``
 * menjadi ``hidden`` / ``display:none`` / melepas komponen: peramban
 * menghentikan produksi bingkai video begitu elemennya tidak digambar lagi.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { t } from '../lib/translations'
import {
  KUNCI_POSISI_KAMERA,
  LEBAR_KARTU_KAMERA,
  POSISI_KARTU_BAWAAN,
  TINGGI_KARTU_KAMERA,
  jepitPosisiKartu,
} from '../lib/percakapan'
import useUkuranJendela from '../lib/useUkuranJendela'

const UKURAN = LEBAR_KARTU_KAMERA
const KUNCI_POSISI = KUNCI_POSISI_KAMERA

/** Jeda antar bingkai hidup. Harus lebih pendek dari masa segar bingkai di
 *  sisi Python (``MAKS_UMUR_BINGKAI_S`` = 12 detik). */
const JEDA_HIDUP_MS = 5000

function posisiAwal() {
  if (typeof window === 'undefined') return { ...POSISI_KARTU_BAWAAN }
  try {
    const tersimpan = JSON.parse(localStorage.getItem(KUNCI_POSISI) || 'null')
    if (tersimpan && Number.isFinite(tersimpan.x) && Number.isFinite(tersimpan.y)) {
      return { x: tersimpan.x, y: tersimpan.y }
    }
  } catch (_) {
    // diabaikan
  }
  return { ...POSISI_KARTU_BAWAAN }
}

export default function KartuKamera({
  permintaan = { nonce: 0, sumber: 'ai' },
  onBingkai,
  onBingkaiHidup,
  onTutup,
  onSiap,
  tersembunyi = false,
}) {
  const [posisi, setPosisi] = useState(posisiAwal)
  const [galat, setGalat] = useState('')
  const [siap, setSiap] = useState(false)
  const [kilat, setKilat] = useState(false)

  // Posisi yang BENAR-BENAR ditampilkan. Posisi asli (dari penyimpanan atau
  // hasil geser) tetap disimpan apa adanya, lalu dijepit ke dalam jendela.
  // Dengan begitu jendela yang diperkecil tidak meninggalkan kartu di luar
  // layar, dan jendela yang dibesarkan lagi mengembalikannya ke tempat semula.
  const { lebar: lebarJendela, tinggi: tinggiJendela } = useUkuranJendela()
  const posisiTampil = useMemo(
    () => jepitPosisiKartu(posisi, UKURAN, TINGGI_KARTU_KAMERA),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [posisi, lebarJendela, tinggiJendela],
  )

  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const seretRef = useRef(null)
  const posisiRef = useRef(posisiTampil)
  // Dipakai penyeretan: harus posisi TAMPIL, bukan posisi keinginan, supaya
  // kartu tidak melompat saat mulai diseret setelah jendela diperkecil.
  posisiRef.current = posisiTampil
  const onBingkaiRef = useRef(onBingkai)
  onBingkaiRef.current = onBingkai
  const onBingkaiHidupRef = useRef(onBingkaiHidup)
  onBingkaiHidupRef.current = onBingkaiHidup
  const onSiapRef = useRef(onSiap)
  onSiapRef.current = onSiap
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

  // Beri tahu induk apakah kamera benar-benar menyala. Dipakai pil kecil yang
  // menggantikan kartu saat dilipat, supaya pengguna tetap tahu SELA melihat
  // walau kartunya disembunyikan.
  useEffect(() => {
    onSiapRef.current?.(siap)
  }, [siap])

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
    setPosisi(
      jepitPosisiKartu(
        { x: e.clientX - s.dx, y: e.clientY - s.dy },
        UKURAN,
        TINGGI_KARTU_KAMERA,
      ),
    )
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
      data-kamera-tersembunyi={tersembunyi ? '1' : '0'}
      aria-hidden={tersembunyi || undefined}
      className={`fixed z-40 select-none transition-all duration-300 ease-out ${
        tersembunyi ? 'opacity-0 pointer-events-none -translate-y-1' : 'opacity-100'
      }`}
      style={{ left: posisiTampil.x, top: posisiTampil.y, width: UKURAN }}
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
            className="w-5 h-5 rounded-lg flex items-center justify-center text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/40 transition-all"
            title={t.id.cameraHide}
            aria-label={t.id.cameraHide}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2.6} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
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
