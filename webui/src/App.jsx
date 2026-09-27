/**
 * Kerangka utama antarmuka SELA AI.
 *
 * Menyatukan avatar 3D, panel percakapan, menu, pengaturan, dan bantuan.
 * Tata letak menyesuaikan diri:
 *   - Layar potret (kios Raspberry Pi): avatar penuh, panel chat menjadi
 *     lembaran bawah yang bisa dibuka/tutup.
 *   - Layar desktop: avatar di tengah, panel chat mengambang di kanan.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Navbar from './components/Navbar'
import Avatar3D from './components/Avatar3D'
import ChatPanel from './components/ChatPanel'
import VoiceControls from './components/VoiceControls'
import HamburgerMenu from './components/HamburgerMenu'
import Settings from './components/Settings'
import GerbangAdmin from './components/GerbangAdmin'
import Help from './components/Help'
import KartuKamera from './components/KartuKamera'
import useSelaBridge from './lib/useSelaBridge'
import { KUNCI_KAMERA, KUNCI_KAMERA_TERBUKA } from './lib/percakapan'
import { t } from './lib/translations'

/** Ikon kamera (lensa) untuk tombol kecil pelipat kartu kamera. */
function IconLensa() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.9} viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.822 1.316z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z"
      />
    </svg>
  )
}

let urutSesi = 0
const idSesi = () => `s${Date.now().toString(36)}${(urutSesi++).toString(36)}`

const KUNCI_TEMA = 'sela-tema'

// Halaman yang boleh dibuka langsung lewat URL, mis. ?halaman=pengaturan.
// Berguna untuk kios: petugas bisa membuka halaman setelan tanpa mengklik menu,
// dan memudahkan pengujian otomatis tiap halaman.
const HALAMAN_SAH = new Set(['beranda', 'pengaturan', 'bantuan'])

// Emosi dari mesin AI -> animasi sekali-jalan pada avatar 3D.
// Nama animasi harus sama persis dengan yang ada di dalam sela.glb:
// Confused, Goodbye, Greeting, Idle, Nodding, Shaking Head, Talking, Thinking.
const PETA_EMOSI_ANIMASI = {
  // positif
  happy: 'Nodding',
  laughing: 'Nodding',
  funny: 'Nodding',
  cool: 'Nodding',
  confident: 'Nodding',
  delicious: 'Nodding',
  kissy: 'Nodding',
  loving: 'Nodding',
  relaxed: 'Nodding',
  // bingung / ragu
  confused: 'Confused',
  silly: 'Confused',
  embarrassed: 'Confused',
  // sedih
  sad: 'Confused',
  crying: 'Confused',
  // tidak setuju / terkejut
  angry: 'Shaking Head',
  shocked: 'Shaking Head',
  surprised: 'Shaking Head',
  // menyapa / berpamitan
  greeting: 'Greeting',
  goodbye: 'Goodbye',
}

function halamanAwal() {
  if (typeof window === 'undefined') return 'beranda'
  const param = new URLSearchParams(window.location.search).get('halaman')
  return param && HALAMAN_SAH.has(param) ? param : 'beranda'
}

function temaAwal() {
  try {
    const tersimpan = localStorage.getItem(KUNCI_TEMA)
    if (tersimpan) return tersimpan
  } catch (_) {
    // diabaikan
  }
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'light'
}

/**
 * Apakah kartu kamera melayang dinyalakan.
 *
 * Disimpan di peramban (bukan di config mesin AI) karena ini murni soal
 * tampilan kios. Halaman Pengaturan menulis nilai yang sama.
 */
function kameraAwal() {
  try {
    return localStorage.getItem(KUNCI_KAMERA) !== '0'
  } catch (_) {
    return true
  }
}

/**
 * Apakah kartu kamera sedang dibentangkan (bukan dilipat jadi ikon kecil).
 *
 * Ini tingkat kedua, terpisah dari saklar induk di Pengaturan: saklar induk
 * mematikan kamera sepenuhnya (ikon kecil pun hilang), sedangkan lipatan ini
 * hanya menyembunyikan kartunya.
 */
function kameraTerbukaAwal() {
  try {
    return localStorage.getItem(KUNCI_KAMERA_TERBUKA) !== '0'
  } catch (_) {
    return true
  }
}

export default function App() {
  const {
    terhubung,
    aiTerhubung,
    stateAvatar,
    emosi,
    teksTombol,
    pesan,
    lip,
    langkahAlat,
    permintaanFoto,
    aksi,
  } = useSelaBridge()

  const [menuTerbuka, setMenuTerbuka] = useState(false)
  const [halaman, setHalaman] = useState(halamanAwal)
  const [arsip, setArsip] = useState([])
  const [sesiAktif, setSesiAktif] = useState('live')
  const [panelTerbuka, setPanelTerbuka] = useState(
    typeof window !== 'undefined' ? window.innerWidth >= 768 : true,
  )
  const [tema, setTema] = useState(temaAwal)
  const [kameraMelayang, setKameraMelayang] = useState(kameraAwal)
  // Kartu kamera sedang dibentangkan atau dilipat jadi ikon kecil.
  const [kameraTerbuka, setKameraTerbuka] = useState(kameraTerbukaAwal)
  // Foto yang menunggu dikirim bersama pertanyaan pengguna.
  const [lampiranFoto, setLampiranFoto] = useState(null)
  // Animasi sekali-jalan yang dipicu oleh emosi dari mesin AI.
  const [gerakan, setGerakan] = useState(null)
  const emosiSebelumnya = useRef(null)

  // Beri tahu mesin AI apakah kamera peramban boleh dipakai. Bila kartunya
  // mati, alat "take_photo" kembali memakai kamera perangkat seperti semula.
  useEffect(() => {
    aksi.setKameraAktif?.(kameraMelayang)
  }, [kameraMelayang, aksi])

  useEffect(() => {
    if (!emosi) return
    const kunci = String(emosi).toLowerCase()
    if (kunci === emosiSebelumnya.current) return
    emosiSebelumnya.current = kunci
    const nama = PETA_EMOSI_ANIMASI[kunci]
    if (!nama) return
    // `kunci` unik tiap kali supaya animasi yang sama bisa diputar ulang.
    setGerakan({ nama, kunci: `${nama}-${Date.now()}` })
  }, [emosi])

  // Kait diagnostik: memungkinkan pengujian otomatis mengirim teks tanpa
  // menyentuh antarmuka (lihat scripts/cek_lipsync_visual.py).
  useEffect(() => {
    window.__selaKirim = (teks) => aksi.kirimTeks(teks)
    window.__selaMic = () => aksi.rekamToggle()
    return () => {
      delete window.__selaKirim
      delete window.__selaMic
    }
  }, [aksi])

  useEffect(() => {
    if (tema === 'dark') document.documentElement.classList.add('dark')
    else document.documentElement.classList.remove('dark')
    try {
      localStorage.setItem(KUNCI_TEMA, tema)
    } catch (_) {
      // diabaikan
    }
  }, [tema])

  // Jaga URL tetap sinkron dengan halaman aktif (tanpa memuat ulang).
  useEffect(() => {
    if (typeof window === 'undefined' || !window.history?.replaceState) return
    const url = new URL(window.location.href)
    if (halaman === 'beranda') url.searchParams.delete('halaman')
    else url.searchParams.set('halaman', halaman)
    window.history.replaceState(null, '', url.toString())
  }, [halaman])

  // Pesan yang ditampilkan: percakapan berjalan atau sesi arsip yang dipilih.
  const pesanTampil = useMemo(() => {
    if (sesiAktif === 'live') return pesan
    const s = arsip.find((x) => x.id === sesiAktif)
    return s ? s.pesan : pesan
  }, [sesiAktif, arsip, pesan])

  const sesiBaru = useCallback(() => {
    setArsip((lama) => {
      if (pesan.length === 0) return lama
      const pertama = pesan.find((p) => p.peran === 'user')
      const judul = (pertama?.teks || 'Percakapan').slice(0, 40)
      return [{ id: idSesi(), judul, pesan }, ...lama].slice(0, 30)
    })
    aksi.bersihkanPercakapan()
    setSesiAktif('live')
    setMenuTerbuka(false)
    setHalaman('beranda')
  }, [pesan, aksi])

  const kirimPesan = useCallback(
    (teks) => {
      if (!teks?.trim()) return
      if (sesiAktif !== 'live') {
        // Mulai percakapan baru bila sedang melihat arsip.
        setSesiAktif('live')
        aksi.bersihkanPercakapan()
      }
      // Bila ada foto terlampir, kirim gambarnya lebih dulu supaya alat
      // kamera mesin AI memakai foto itu, lalu gelembungnya baru muncul.
      if (lampiranFoto) {
        aksi.kirimBingkai?.(lampiranFoto)
        aksi.tambahFoto?.(lampiranFoto, teks.trim())
        setLampiranFoto(null)
      }
      aksi.kirimTeks(teks.trim())
    },
    [aksi, sesiAktif, lampiranFoto],
  )

  const pilihSesi = useCallback((id) => {
    setSesiAktif(id)
    setMenuTerbuka(false)
    setHalaman('beranda')
    setPanelTerbuka(true)
  }, [])

  const hapusSesi = useCallback(
    (id) => {
      setArsip((lama) => lama.filter((s) => s.id !== id))
      setSesiAktif((kini) => (kini === id ? 'live' : kini))
    },
    [],
  )

  // Setiap kali pengguna berpindah halaman, pastikan sambungan dan sesi
  // dengar siap. Sebelumnya keluar dari Pengaturan kadang meninggalkan
  // sambungan setengah siap sehingga SELA diam sampai aplikasi dijalankan
  // ulang. Sekaligus membaca ulang setelan kartu kamera, karena halaman
  // Pengaturan menulisnya ke penyimpanan peramban.
  useEffect(() => {
    setKameraMelayang(kameraAwal())
    setKameraTerbuka(kameraTerbukaAwal())
    const tunda = setTimeout(() => aksi.siapSiaga?.(), 300)
    return () => clearTimeout(tunda)
  }, [halaman, aksi])

  // Foto sadar (tombol "Ambil Foto", atau permintaan yang datang dari teks
  // pengguna): TIDAK langsung jadi gelembung. Foto dilampirkan ke kotak teks
  // supaya pengguna bisa bertanya tentang foto itu.
  //
  // Permintaan dari MESIN AI sendiri (alat take_photo) tidak dilampirkan -
  // gambar itu hanya dipakai AI untuk menjawab, tanpa mengganggu kotak teks.
  const tanganiBingkai = useCallback(
    (dataUrl, sumber = 'pengguna') => {
      aksi.kirimBingkai?.(dataUrl)
      if (sumber === 'ai') return
      setLampiranFoto(dataUrl)
      setPanelTerbuka(true)
      setHalaman('beranda')
    },
    [aksi],
  )

  // Bingkai hidup: hanya disimpan di mesin AI, tidak mengganggu percakapan.
  const tanganiBingkaiHidup = useCallback(
    (dataUrl) => {
      aksi.kirimBingkai?.(dataUrl)
    },
    [aksi],
  )

  // Tombol silang pada kartu kamera melipat kartunya jadi ikon kecil - sama
  // seperti panel obrolan. Mematikan kamera sepenuhnya tetap hanya dari
  // halaman Pengaturan.
  const lipatKamera = useCallback(() => {
    setKameraTerbuka(false)
    try {
      localStorage.setItem(KUNCI_KAMERA_TERBUKA, '0')
    } catch (_) {
      // diabaikan
    }
  }, [])

  const bentangkanKamera = useCallback(() => {
    setKameraTerbuka(true)
    try {
      localStorage.setItem(KUNCI_KAMERA_TERBUKA, '1')
    } catch (_) {
      // diabaikan
    }
  }, [])

  // Escape menutup menu / kembali ke beranda.
  useEffect(() => {
    const handler = (e) => {
      if (e.key !== 'Escape') return
      if (menuTerbuka) setMenuTerbuka(false)
      else if (halaman !== 'beranda') setHalaman('beranda')
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [menuTerbuka, halaman])

  return (
    <div className="fixed inset-0 flex flex-col overflow-hidden">
      {/* Latar gradien bergerak */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-[#f8faff] dark:bg-slate-950 transition-colors duration-500">
        <div className="absolute -top-[10%] -left-[10%] w-[50%] h-[50%] rounded-full bg-blue-200/40 dark:bg-blue-900/20 blur-[120px] animate-float-1" />
        <div className="absolute top-[20%] -right-[10%] w-[45%] h-[45%] rounded-full bg-indigo-200/30 dark:bg-indigo-900/15 blur-[120px] animate-float-2" />
        <div className="absolute -bottom-[10%] left-[20%] w-[40%] h-[40%] rounded-full bg-sky-100/50 dark:bg-blue-800/20 blur-[120px] animate-float-3" />
      </div>

      {halaman === 'beranda' ? (
        <>
          <Navbar
            onMenuClick={() => setMenuTerbuka(true)}
            theme={tema}
            setTheme={setTema}
            terhubung={terhubung}
            aiTerhubung={aiTerhubung}
          />

          <main className="flex-1 relative flex flex-col overflow-hidden min-h-0">
            {/* Avatar 3D sebagai latar penuh */}
            <div className="absolute inset-0 pointer-events-none z-0">
              <div className="pointer-events-auto w-full h-full">
                <Avatar3D state={stateAvatar} theme={tema} lip={lip} gerakan={gerakan} />
              </div>
            </div>

            {/* Panel percakapan */}
            <ChatPanel
              pesan={pesanTampil}
              onKirim={kirimPesan}
              onRekam={aksi.rekamToggle}
              onSesiBaru={sesiBaru}
              onTutup={(tutup) => setPanelTerbuka(!tutup)}
              terbuka={panelTerbuka}
              stateAvatar={stateAvatar}
              terhubung={terhubung}
              volume={lip?.v || 0}
              langkahAlat={langkahAlat}
              lampiran={lampiranFoto}
              onHapusLampiran={() => setLampiranFoto(null)}
            />

            {/* Kamera. Saklar induk di Pengaturan menentukan apakah kamera
                bisa diakses sama sekali; bila mati, ikon kecilnya pun tidak
                muncul sehingga pengguna tidak punya jalan masuk. Bila aktif,
                kartunya bisa dilipat jadi ikon kecil - sama seperti panel
                obrolan. */}
            {kameraMelayang &&
              (kameraTerbuka ? (
                <KartuKamera
                  permintaan={permintaanFoto}
                  onBingkai={tanganiBingkai}
                  onBingkaiHidup={tanganiBingkaiHidup}
                  onTutup={lipatKamera}
                />
              ) : (
                <button
                  type="button"
                  onClick={bentangkanKamera}
                  data-kamera-ikon="1"
                  className="fixed z-40 top-24 left-6 w-11 h-11 rounded-2xl flex items-center justify-center
                    bg-white/92 dark:bg-slate-900/92 backdrop-blur-xl border border-white/60 dark:border-slate-700/60
                    shadow-xl text-blue-600 dark:text-blue-400 hover:scale-105 active:scale-95 transition-all"
                  title={t.id.cameraShow}
                >
                  <IconLensa />
                </button>
              ))}

            {/* Tombol suara + status */}
            <VoiceControls
              stateAvatar={stateAvatar}
              onRekam={aksi.rekamToggle}
              terhubung={terhubung}
              aiTerhubung={aiTerhubung}
              teksTombol={teksTombol}
              terbuka={panelTerbuka}
            />
          </main>
        </>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden min-h-0">
          {halaman === 'pengaturan' && (
            <GerbangAdmin>
              <Settings
                onBack={() => setHalaman('beranda')}
                theme={tema}
                setTheme={setTema}
                terhubung={terhubung}
              />
            </GerbangAdmin>
          )}
          {halaman === 'bantuan' && <Help onBack={() => setHalaman('beranda')} />}
        </div>
      )}

      <HamburgerMenu
        isOpen={menuTerbuka}
        onClose={() => setMenuTerbuka(false)}
        sesi={arsip}
        sesiAktif={sesiAktif}
        onSesiBaru={sesiBaru}
        onPilihSesi={pilihSesi}
        onHapusSesi={hapusSesi}
        onOpenSettings={() => {
          setMenuTerbuka(false)
          setHalaman('pengaturan')
        }}
        onOpenHelp={() => {
          setMenuTerbuka(false)
          setHalaman('bantuan')
        }}
      />
    </div>
  )
}
