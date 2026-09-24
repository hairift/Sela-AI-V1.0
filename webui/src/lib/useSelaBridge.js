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

  const tambahPesan = useCallback((peran, teks) => {
    const bersih = String(teks || '').trim()
    if (!bersih) return
    setPesan((lama) => {
      // Hindari duplikat beruntun (jalur tts dan presenter bisa mengirim sama).
      const terakhir = lama[lama.length - 1]
      if (terakhir && terakhir.peran === peran && terakhir.teks === bersih) {
        return lama
      }
      return [...lama, { id: idBaru(), peran, teks: bersih, waktu: Date.now() }]
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
    pesan,
    lip,
    catatan,
    aksi,
  }
}
