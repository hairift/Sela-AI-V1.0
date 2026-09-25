/**
 * Hook React penghubung antarmuka dengan mesin AI SELA (py-xiaozhi).
 *
 * Menyatukan seluruh status runtime di satu tempat: percakapan, status
 * avatar, emosi, mode otomatis, dan data lipsync. Komponen lain cukup
 * membaca nilai kembalian hook ini.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createSelaBridge } from './bridge'
import { buangBlokGanda } from './teks'

let urutanId = 0
const idBaru = () => `m${Date.now().toString(36)}${(urutanId++).toString(36)}`

/**
 * Gabungkan dua potongan jawaban AI menjadi satu teks yang enak dibaca.
 *
 * Mesin AI mengirim jawaban per kalimat, dan kadang mengirim ulang kalimat yang
 * sudah terkirim (jalur TTS dan jalur presenter). Penggabungan naif
 * menghasilkan "Halo.Selamat datang", "Halo . Selamat", atau bahkan kalimat
 * yang tercetak dua kali. Fungsi ini:
 *   - membuang potongan yang sudah ada di ujung teks lama;
 *   - memakai teks baru utuh bila ia memuat seluruh teks lama;
 *   - menambal tumpang tindih awalan/akhiran sebelum menyambung.
 */
const gabungTeks = (lama, baru) => {
  const a = String(lama || '').trimEnd()
  const b = String(baru || '').trim()
  if (!a) return b
  if (!b) return a
  // Potongan yang sudah termuat di akhir teks tidak perlu ditambah lagi.
  if (a.endsWith(b)) return a
  // Potongan baru memuat seluruh teks lama -> pakai yang baru saja.
  if (b.includes(a)) return b
  // Tumpang tindih: akhiran teks lama sama dengan awalan teks baru.
  const maks = Math.min(a.length, b.length, 240)
  for (let n = maks; n >= 8; n -= 1) {
    if (a.slice(-n) === b.slice(0, n)) return a + b.slice(n)
  }
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
  thinking: 'thinking',
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
  const [pesan, setPesan] = useState([])
  const [lip, setLip] = useState({ v: 0, viseme: 'sil' })
  const [catatan, setCatatan] = useState(null)
  // Langkah alat (MCP) yang sedang dikerjakan mesin AI. Ditampilkan sebagai
  // animasi singkat supaya pengguna melihat SELA benar-benar membuka data.
  const [langkahAlat, setLangkahAlat] = useState([])
  // Penanda permintaan foto. Setiap kali bertambah, kartu kamera mengambil
  // satu gambar lalu mengirimkannya ke mesin AI.
  const [permintaanFoto, setPermintaanFoto] = useState(0)
  // Benar saat pertanyaan sudah dikirim tetapi jawaban belum mulai.
  // Dipakai untuk menampilkan animasi "Thinking" selagi mesin AI mencari
  // jawaban (termasuk saat memanggil tool data kampus / pencarian web).
  const [menungguJawaban, setMenungguJawaban] = useState(false)

  const bridgeRef = useRef(null)
  const timerMenunggu = useRef(null)
  // Menahan papan langkah alat sebentar setelah jawaban mulai mengalir, supaya
  // pengguna benar-benar sempat melihat apa yang dikerjakan SELA.
  const timerAlat = useRef(null)
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

  // Satu giliran bicara = satu gelembung.
  //
  // Mesin AI mengirim jawaban sepotong-sepotong, dan jeda antar potongan bisa
  // puluhan detik karena kalimatnya dibacakan dengan suara lebih dulu. Karena
  // itu penggabungan TIDAK memakai batas waktu, melainkan "belum ada pesan
  // pengguna baru sejak gelembung terakhir". Begitu pengguna bicara lagi,
  // giliran selesai dan jawaban berikutnya menjadi gelembung baru.
  const waktuPesanTerakhir = useRef(0)

  const tambahPesan = useCallback((peran, teks, opsi = {}) => {
    const bersih = String(teks || '').trim()
    if (!bersih) return
    const sekarang = Date.now()
    setPesan((lama) => {
      const terakhir = lama[lama.length - 1]

      // Potongan jawaban AI digabung ke gelembung terakhir yang masih satu
      // giliran bicara, sehingga tampil sebagai SATU jawaban utuh. Blok yang
      // tercetak dua kali (karena mesin AI menggabungkan dua hasil alat data
      // yang isinya mirip) dibuang di sini, sekali saja - bukan pada setiap
      // gambar ulang layar, supaya animasi mengetik tetap ringan.
      if (peran === 'assistant' && terakhir && terakhir.peran === 'assistant') {
        const gabung = buangBlokGanda(gabungTeks(terakhir.teks, bersih))
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
      return [
        ...lama,
        {
          id: idBaru(),
          peran,
          teks: peran === 'assistant' ? buangBlokGanda(bersih) : bersih,
          waktu: sekarang,
          ...opsi,
        },
      ]
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
          break

        case 'state':
          setStateAvatar(PETA_STATE[data.state] || 'idle')
          if (data.state === 'speaking') selesaiMenunggu()
          break

        case 'chat':
          tambahPesan(data.role === 'user' ? 'user' : 'assistant', data.text)
          if (data.role !== 'user') {
            selesaiMenunggu()
            // Jawaban sudah mulai mengalir: papan langkah alat disembunyikan,
            // tetapi ditahan ~1,5 detik dulu agar tidak berkedip hilang.
            clearTimeout(timerAlat.current)
            timerAlat.current = setTimeout(() => setLangkahAlat([]), 1500)
          }
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

        case 'tool':
          // Mesin AI memanggil sebuah alat. Tampilkan sebagai langkah kerja.
          if (data.label) {
            setLangkahAlat((lama) => {
              const baru = [
                ...lama,
                { id: `t${Date.now().toString(36)}${lama.length}`, label: data.label },
              ]
              // Cukup 4 langkah terakhir agar kartu tidak memanjang.
              return baru.slice(-4)
            })
          }
          break

        case 'ambil_foto':
          // Mesin AI (atau permintaan pengguna) butuh gambar dari kamera.
          setPermintaanFoto((n) => n + 1)
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
      // Kirim satu bingkai JPEG dari kamera peramban ke mesin AI.
      kirimBingkai: (data) => bridgeRef.current?.kirimBingkai(data),
      // Nyalakan/matikan pemakaian kamera peramban di sisi mesin AI.
      setKameraAktif: (aktif) => bridgeRef.current?.kameraAktif(aktif),
      // Tampilkan foto hasil kamera sebagai pesan pengguna di percakapan.
      tambahFoto: (dataUrl, teks) =>
        tambahPesan('user', teks || 'Foto dari kamera', { gambar: dataUrl }),
      toggleMode: () => bridgeRef.current?.autoToggle(),
      batalkan: () => {
        selesaiMenunggu()
        bridgeRef.current?.abort()
      },
      bukaPengaturan: () => bridgeRef.current?.openSettings(),
      keluar: () => bridgeRef.current?.quit(),
      bersihkanPercakapan: () => {
        clearTimeout(timerAlat.current)
        setPesan([])
        setLangkahAlat([])
      },
      hapusPesan: (id) => setPesan((lama) => lama.filter((p) => p.id !== id)),
    }),
    [tandaiMenunggu, selesaiMenunggu, tambahPesan],
  )

  // State avatar yang ditampilkan: selagi menunggu jawaban, tampilkan
  // "thinking" agar avatar bergerak dan tidak terlihat diam.
  //
  // Catatan: state "listening" TIDAK dikecualikan. Saat pengguna selesai
  // bicara, mesin AI mengembalikan state ke "listening" selagi memproses
  // jawaban - bila listening dikecualikan, animasi Thinking tidak akan
  // pernah tampil pada momen paling penting itu.
  const stateTampil =
    menungguJawaban && stateAvatar !== 'speaking' ? 'thinking' : stateAvatar

  return {
    terhubung,
    aiTerhubung,
    statusTeks,
    emosi,
    stateAvatar: stateTampil,
    modeOtomatis,
    teksTombol,
    pesan,
    lip,
    catatan,
    langkahAlat,
    permintaanFoto,
    aksi,
  }
}
