/**
 * Hook React penghubung antarmuka dengan mesin AI SELA (py-xiaozhi).
 *
 * Menyatukan seluruh status runtime di satu tempat: percakapan, status
 * avatar, emosi, mode otomatis, dan data lipsync. Komponen lain cukup
 * membaca nilai kembalian hook ini.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createSelaBridge } from './bridge'

let urutanId = 0
const idBaru = () => `m${Date.now().toString(36)}${(urutanId++).toString(36)}`

/**
 * Gabungkan dua potongan jawaban AI menjadi satu teks yang enak dibaca.
 *
 * Mesin AI mengirim jawaban per kalimat. Penggabungan naif menghasilkan
 * "Halo.Selamat datang" atau "Halo . Selamat". Fungsi ini menambahkan spasi
 * hanya bila perlu, dan tidak menambahkan titik yang sudah ada.
 */
const gabungTeks = (lama, baru) => {
  const a = String(lama || '').trimEnd()
  const b = String(baru || '').trim()
  if (!a) return b
  if (!b) return a
  // Potongan yang sudah termuat di akhir teks tidak perlu ditambah lagi.
  if (a.endsWith(b)) return a
  // Baris baru dipertahankan sebagai pemisah paragraf.
  if (a.endsWith('\n') || b.startsWith('\n')) return `${a}${b}`
  // Setelah tanda baca tidak perlu spasi; selain itu tambahkan spasi.
  if (/[.!?,;:)\]}"'”’]$/.test(a)) return `${a} ${b}`
  if (/^[.,;:)\]}]/.test(b)) return `${a}${b}`
  return `${a} ${b}`
}

// Nama state dari Python (DeviceState) -> state avatar di antarmuka.
const PETA_STATE = {
  idle: 'idle',
  listening: 'listening',
  speaking: 'speaking',
  connecting: 'thinking',
  connecting_state: 'thinking',
}

export default function useSelaBridge() {
  const [terhubung, setTerhubung] = useState(false)
  // Terhubung ke mesin AI (protokol ke layanan SELA), terpisah dari
  // terhubung ke server lokal aplikasi. Keduanya perlu dibedakan supaya
  // pesan ke pengguna tidak menyesatkan.
  const [aiTerhubung, setAiTerhubung] = useState(false)
  const [statusTeks, setStatusTeks] = useState('Menghubungkan...')
  const [emosi, setEmosi] = useState('neutral')
  const [stateAvatar, setStateAvatar] = useState('idle')
  const [modeOtomatis, setModeOtomatis] = useState(false)
  const [teksTombol, setTeksTombol] = useState('')
  const [barisMusik, setBarisMusik] = useState('')
  // Data pemutar musik: judul, status, posisi, dan durasi.
  const [musik, setMusik] = useState({
    song: '',
    state: 'stopped',
    position: 0,
    duration: 0,
  })
  const [pesan, setPesan] = useState([])
  const [lip, setLip] = useState({ v: 0, viseme: 'sil' })
  const [catatan, setCatatan] = useState(null)
  // Benar saat pertanyaan sudah dikirim tetapi jawaban belum mulai.
  // Dipakai untuk menampilkan animasi "Thinking" selagi mesin AI mencari
  // jawaban (termasuk saat memanggil tool data kampus / pencarian web).
  const [menungguJawaban, setMenungguJawaban] = useState(false)

  const bridgeRef = useRef(null)
  const timerMenunggu = useRef(null)
  // Menandai apakah mikrofon sedang merekam (klik pertama = mulai,
  // klik kedua = berhenti dan kirim).
  const merekamRef = useRef(false)

  const tandaiMenunggu = useCallback(() => {
    setMenungguJawaban(true)
    clearTimeout(timerMenunggu.current)
    // Jaring pengaman: jangan biarkan avatar "berpikir" selamanya bila
    // jawaban tidak pernah datang (mis. jaringan terputus).
    timerMenunggu.current = setTimeout(() => setMenungguJawaban(false), 20000)
  }, [])

  const selesaiMenunggu = useCallback(() => {
    clearTimeout(timerMenunggu.current)
    setMenungguJawaban(false)
  }, [])

  // Batas waktu penggabungan potongan jawaban AI menjadi satu gelembung.
  // Mesin AI mengirim jawaban sepotong-sepotong (per kalimat); tanpa ini
  // pengguna melihat banyak gelembung kecil yang beruntun.
  const JEDA_GABUNG_MS = 8000
  const waktuPesanTerakhir = useRef(0)

  const tambahPesan = useCallback((peran, teks) => {
    const bersih = String(teks || '').trim()
    if (!bersih) return
    const sekarang = Date.now()
    setPesan((lama) => {
      const terakhir = lama[lama.length - 1]

      // Potongan jawaban AI digabung ke gelembung terakhir yang masih satu
      // giliran bicara, sehingga tampil sebagai SATU jawaban utuh.
      if (
        peran === 'assistant' &&
        terakhir &&
        terakhir.peran === 'assistant' &&
        sekarang - waktuPesanTerakhir.current < JEDA_GABUNG_MS
      ) {
        const gabung = gabungTeks(terakhir.teks, bersih)
        if (gabung === terakhir.teks) return lama
        const baru = lama.slice(0, -1)
        baru.push({ ...terakhir, teks: gabung, waktu: sekarang })
        waktuPesanTerakhir.current = sekarang
        return baru
      }

      // Hindari duplikat beruntun (jalur tts dan presenter bisa mengirim sama).
      if (terakhir && terakhir.peran === peran && terakhir.teks === bersih) {
        return lama
      }

      waktuPesanTerakhir.current = sekarang
      return [...lama, { id: idBaru(), peran, teks: bersih, waktu: sekarang }]
    })
  }, [])

  const tanganiEvent = useCallback(
    (data) => {
      switch (data.t) {
        case 'snapshot':
          if (typeof data.connected === 'boolean') setAiTerhubung(data.connected)
          if (data.status) setStatusTeks(data.status)
          if (data.emotion) setEmosi(data.emotion)
          if (data.deviceState) setStateAvatar(PETA_STATE[data.deviceState] || 'idle')
          if (typeof data.autoMode === 'boolean') setModeOtomatis(data.autoMode)
          if (data.buttonText) setTeksTombol(data.buttonText)
          if (data.musicLine) setBarisMusik(data.musicLine)
          break

        case 'state':
          setStateAvatar(PETA_STATE[data.state] || 'idle')
          if (data.state === 'speaking') selesaiMenunggu()
          break

        case 'chat':
          tambahPesan(data.role === 'user' ? 'user' : 'assistant', data.text)
          if (data.role !== 'user') selesaiMenunggu()
          break

        case 'user_text':
          tambahPesan('user', data.text)
          break

        case 'emotion':
          if (data.emotion) setEmosi(data.emotion)
          break

        case 'status':
          if (typeof data.connected === 'boolean') setAiTerhubung(data.connected)
          if (data.status) setStatusTeks(data.status)
          break

        case 'notice':
          if (data.text) {
            setCatatan(data.text)
            setTimeout(() => setCatatan(null), 6000)
          }
          break

        case 'music':
          setMusik({
            song: data.song || '',
            state: data.state || 'stopped',
            position: Number(data.position) || 0,
            duration: Number(data.duration) || 0,
          })
          if (data.song) setBarisMusik(`Musik: ${data.song}`)
          break

        case 'lyrics':
        case 'music_line':
          if (data.text) setBarisMusik(data.text)
          break

        case 'button_text':
          if (data.text) setTeksTombol(data.text)
          break

        case 'auto_mode':
          if (typeof data.autoMode === 'boolean') setModeOtomatis(data.autoMode)
          break

        case 'lip':
          setLip({ v: Number(data.v) || 0, viseme: data.viseme || 'sil' })
          break

        default:
          break
      }
    },
    [tambahPesan, selesaiMenunggu],
  )

  useEffect(() => {
    const bridge = createSelaBridge({
      onEvent: tanganiEvent,
      onConnectionChange: (ok) => {
        setTerhubung(ok)
        setStatusTeks(
          ok
            ? 'Siap'
            : 'Aplikasi SELA belum berjalan. Jalankan aplikasi, lalu muat ulang halaman ini.',
        )
        if (!ok) {
          setAiTerhubung(false)
          setStateAvatar('idle')
        }
      },
    })
    bridgeRef.current = bridge
    return () => bridge.tutup()
  }, [tanganiEvent])

  const aksi = useMemo(
    () => ({
      kirimTeks: (teks) => {
        tandaiMenunggu()
        bridgeRef.current?.sendText(teks)
      },
      rekamToggle: () => {
        // Saat menghentikan rekaman, pertanyaan ikut terkirim -> mulai menunggu.
        if (merekamRef.current) tandaiMenunggu()
        merekamRef.current = !merekamRef.current
        bridgeRef.current?.manualToggle()
      },
      mulaiOtomatis: () => bridgeRef.current?.autoStart(),
      // Pastikan sambungan + sesi dengar siap (dipanggil saat pindah halaman).
      siapSiaga: () => bridgeRef.current?.siapSiaga(),
      // Tombol pada pemutar musik di panel percakapan.
      kendaliMusik: (jenis, nilai) => bridgeRef.current?.kendaliMusik(jenis, nilai),
      toggleMode: () => bridgeRef.current?.autoToggle(),
      batalkan: () => {
        selesaiMenunggu()
        bridgeRef.current?.abort()
      },
      bukaPengaturan: () => bridgeRef.current?.openSettings(),
      keluar: () => bridgeRef.current?.quit(),
      bersihkanPercakapan: () => setPesan([]),
      hapusPesan: (id) => setPesan((lama) => lama.filter((p) => p.id !== id)),
    }),
    [tandaiMenunggu, selesaiMenunggu],
  )

  // State avatar yang ditampilkan: selagi menunggu jawaban, tampilkan
  // "thinking" agar avatar bergerak dan tidak terlihat diam.
  const stateTampil =
    menungguJawaban && stateAvatar !== 'speaking' && stateAvatar !== 'listening'
      ? 'thinking'
      : stateAvatar

  return {
    terhubung,
    aiTerhubung,
    statusTeks,
    emosi,
    stateAvatar: stateTampil,
    modeOtomatis,
    teksTombol,
    barisMusik,
    musik,
    pesan,
    lip,
    catatan,
    aksi,
  }
}
