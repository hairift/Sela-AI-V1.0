/* eslint-disable react/prop-types */
/**
 * Subtitle AI - teks jawaban SELA yang muncul di layar selagi ia berbicara.
 *
 * Kenapa komponen ini ada: selama SELA mengeluarkan suara, isi gelembung chat
 * diganti visualizer (lihat ChatBubble.jsx), sehingga teks jawaban tidak
 * terbaca di mana pun. Tanpa subtitle, pengguna yang menyimak avatar hanya
 * mendengar suara tanpa bisa mengikuti teksnya.
 *
 * Dua mode mengikuti kebutuhan yang berbeda:
 * - ``kata`` (bawaan): teks muncul kata per kata, meniru gaya live caption.
 *   Cocok untuk kios yang berdiri sendiri sebab terasa mengikuti suara.
 * - ``penuh``: seluruh teks tampil sekaligus.
 *
 * Gaya sengaja dibuat mirip subtitle pada aplikasi SELA Desktop - teks putih di
 * atas lapisan gelap semi-transparan, di bawah avatar - agar tetap terbaca di
 * latar terang maupun gelap. Subtitle berada di atas visualizer audio dan
 * ``pointer-events-none`` supaya tidak pernah menghalangi tombol.
 */

import { useEffect, useRef, useState } from 'react'

// Jeda antar-kata (ms) saat mode ``kata``.
const JEDA_KATA_MS = 150

// Berapa lama teks ditahan setelah SELA berhenti bicara (ms), memberi
// kesempatan membaca kalimat terakhir sebelum subtitle hilang.
const TAHAN_SELESAI_MS = 2600

// Toleransi jeda pendek di sela kalimat (ms). State perangkat bisa berkedip
// idle sekejap walau suara masih berlanjut; tanpa toleransi ini subtitle
// berkedip hilang-timbul.
const TOLERANSI_JEDA_MS = 1400

// Batas ukuran agar subtitle tidak menutupi avatar atau tombol.
const MAKS_LEBAR_VW = 78
const MAKS_LEBAR_PX = 720

/**
 * Buang pranala dari teks subtitle.
 *
 * Pranala panjang merusak tampilan subtitle dan sudah disajikan sebagai kartu
 * terpisah di gelembung obrolan, jadi lebih baik tidak diulang di sini.
 */
function tanpaPranala(teks) {
  return String(teks || '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export default function SubtitleAI({ teks, aktif = false, mode = 'kata' }) {
  const [terlihat, setTerlihat] = useState('')
  const [tahan, setTahan] = useState(false)
  // Teks sumber ikut disimpan agar efek jeda-tahan tidak menghapus subtitle
  // yang sudah tampil hanya karena prop `teks` sempat berubah.
  const [sumberTahan, setSumberTahan] = useState('')
  const timerRef = useRef(null)

  useEffect(() => {
    clearInterval(timerRef.current)
    clearTimeout(timerRef.current)

    const sumber = tanpaPranala(teks)

    // Belum bicara atau tidak ada teks: kosongkan setelah jeda tahan.
    if (!aktif || !sumber) {
      if (!aktif) {
        setTahan(false)
        setTerlihat('')
      } else {
        // Sudah bicara tetapi teks jawaban belum sampai: tahan tampilan agar
        // tidak berkedip. Bila belum ada apa pun untuk ditahan, biarkan kosong
        // supaya tidak ada kotak hampa di layar.
        setTahan(true)
      }
      return undefined
    }

    setSumberTahan(sumber)

    setTahan(false)

    if (mode === 'penuh') {
      setTerlihat(sumber)
      return undefined
    }

    // Mode ``kata``: tampilkan bertahap supaya terasa mengikuti suara. Bila
    // teks baru menggantikan yang lama, mulai dari awal agar tidak tercampur.
    const kata = sumber.split(' ').filter((k) => k.length > 0)
    if (kata.length === 0) {
      setTerlihat('')
      return undefined
    }

    let i = 0
    setTerlihat('')
    timerRef.current = setInterval(() => {
      i += 1
      setTerlihat(kata.slice(0, i).join(' '))
      if (i >= kata.length) {
        clearInterval(timerRef.current)
      }
    }, JEDA_KATA_MS)

    return () => clearInterval(timerRef.current)
  }, [teks, aktif, mode])

  // Setelah bicara selesai, tahan teks sesaat lalu hilangkan. Jeda pendek di
  // sela kalimat (state berkedip ke idle) tidak langsung menghapus subtitle:
  // tunggu TOLERANSI_JEDA_MS dulu. Bila suara kembali sebelum itu, efek dibatal.
  useEffect(() => {
    if (aktif) {
      setTahan(false)
      return undefined
    }
    const id = setTimeout(() => setTahan(true), TOLERANSI_JEDA_MS)
    return () => clearTimeout(id)
  }, [aktif])

  // Hilangkan benar-benar setelah bicara sungguh selesai.
  useEffect(() => {
    if (aktif) return undefined
    const id = setTimeout(() => {
      setTahan(false)
      setTerlihat('')
      setSumberTahan('')
    }, TAHAN_SELESAI_MS)
    return () => clearTimeout(id)
  }, [aktif])

  const tampil = aktif || tahan
  // Selagi bicara tetapi teks belum sampai, tahan cuplikan terakhir supaya
  // subtitle tidak berkedip hilang-timbul di sela kalimat.
  const isiTampil = terlihat || (tampil ? sumberTahan : '')
  if (!tampil || !isiTampil) return null

  return (
    <div
      data-subtitle-ai="1"
      className="flex justify-center px-4 transition-opacity duration-300"
      style={{
        opacity: tampil ? 1 : 0,
        maxWidth: `min(${MAKS_LEBAR_PX}px, ${MAKS_LEBAR_VW}vw)`,
      }}
    >
      <p
        className="text-center text-white text-[13px] leading-snug font-medium
          bg-black/65 backdrop-blur-sm rounded-lg px-3 py-1.5
          shadow-lg max-h-[3.6rem] overflow-hidden"
        style={{
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
        }}
      >
        {isiTampil}
      </p>
    </div>
  )
}
