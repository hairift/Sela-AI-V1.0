/**
 * Aturan percakapan antarmuka SELA: batas panjang teks, lokasi kampus, dan
 * balasan cepat yang mengikuti topik jawaban.
 *
 * Semua nilai di sini hanya untuk TAMPILAN. Kecerdasan tetap di py-xiaozhi.
 */

/**
 * Panjang maksimum teks pada kotak obrolan.
 *
 * Server xiaozhi menolak teks panjang pada jalur ``listen/detect``:
 * "Detect is only for wake words, do not send long texts." Bila pengguna
 * mengetik lebih panjang, pertanyaannya tidak pernah dijawab. Karena itu
 * kotak teks dibatasi, dan pertanyaan panjang diarahkan ke tombol mikrofon
 * (jalur suara tidak melewati batas ini).
 *
 * Nilai ini HARUS sama dengan ``MAKS_PANJANG_TEKS`` di
 * ``src/ui/web/bridge.py`` (jaring pengaman di sisi Python).
 */
export const MAKS_PANJANG_TEKS = 24

/**
 * Batas jeda suara sebelum status "bicara" dianggap macet (ms).
 *
 * Mesin AI bisa tetap melaporkan ``speaking`` walau pemutaran audio tersendat
 * (mis. ``output underflow`` saat berjalan tanpa jendela). Selama visualizer
 * tampil, isi gelembung - termasuk teks jawaban dan kartu peta - TIDAK
 * dirender. Bila tak ada suara nyata selama jeda ini, visualizer dilepas agar
 * teks jawaban tetap terbaca. Nilainya jauh di atas jeda antar-kalimat TTS
 * yang wajar supaya tidak berkedip.
 */
export const BATAS_SEPI_BICARA_MS = 10000

/** Titik peta kampus (dari OpenStreetMap: Universitas Catur Insan Cendekia). */
export const KAMPUS = {
  nama: 'Universitas Catur Insan Cendekia (UCIC)',
  lat: -6.7338864,
  lon: 108.5532478,
  alamat: 'Jl. Kesambi No. 202, Kesambi, Kota Cirebon',
}

/** Kunci penyimpanan setelan kartu kamera melayang di peramban.
 *
 * Dua tingkat, seperti panel obrolan:
 *  - ``KUNCI_KAMERA``        -> saklar induk di Pengaturan (0 = kamera dimatikan
 *                               total, ikon kecil pun tidak muncul);
 *  - ``KUNCI_KAMERA_TERBUKA`` -> kartunya sedang dibentangkan atau dilipat
 *                               menjadi ikon kecil.
 */
export const KUNCI_KAMERA = 'sela_kamera_melayang'
export const KUNCI_KAMERA_TERBUKA = 'sela_kamera_terbuka'

/** Posisi kartu kamera di layar. Dipakai bersama oleh kartunya sendiri dan
 *  oleh pil kecil yang menggantikannya saat kartu dilipat, supaya pil itu
 *  muncul persis di tempat kartunya tadi berada (tidak melompat ke sudut). */
export const KUNCI_POSISI_KAMERA = 'sela_kamera_posisi'

/** Lebar kartu kamera (px). Harus sama dengan ``UKURAN`` di KartuKamera.jsx. */
export const LEBAR_KARTU_KAMERA = 168

/** Ukuran kartu kamera yang dipakai untuk menjepit posisinya (px).
 *
 * Tinggi kartu ikut berubah mengikuti isinya (bilah geser + pratinjau 4:3 +
 * tombol), jadi angkanya hanya perkiraan. Yang penting: kartu tidak pernah
 * dibiarkan keluar jendela. */
export const TINGGI_KARTU_KAMERA = 210

/** Ukuran pil kecil pengganti kartu saat dilipat (px).
 *
 * Lebarnya sengaja memakai lebar kartu (lebih lebar dari pil sebenarnya)
 * supaya pil tidak pernah tersangkut setengah di tepi kanan. */
export const LEBAR_PIL_KAMERA = 168
export const TINGGI_PIL_KAMERA = 56

/** Posisi bawaan kartu kamera: di bawah tombol menu, sedikit dari tepi kiri. */
export const POSISI_KARTU_BAWAAN = { x: 24, y: 96 }

/**
 * Jepit posisi kartu kamera agar seluruh kartunya tetap di dalam jendela.
 *
 * Dipakai di TIGA tempat yang harus sepakat: posisi awal dari penyimpanan,
 * saat kartu digeser, dan saat jendela berubah ukuran. Sebelumnya kartu hanya
 * dijepit saat digeser, sehingga jendela yang diperkecil (mis. berpindah ke
 * mode potret) bisa meninggalkan kartu di luar layar - pengguna melihat
 * kamera "hilang". Posisi asli TIDAK diubah di sini; hanya nilai tampilnya,
 * sehingga jendela yang dibesarkan lagi mengembalikan kartu ke tempat semula.
 *
 * @param {{x: number, y: number}|null|undefined} posisi posisi yang diinginkan
 * @param {number} lebar lebar elemen (px)
 * @param {number} tinggi tinggi elemen (px)
 * @returns {{x: number, y: number}} posisi yang aman ditampilkan
 */
export function jepitPosisiKartu(posisi, lebar, tinggi) {
  if (typeof window === 'undefined') return { ...POSISI_KARTU_BAWAAN }
  const x = Number.isFinite(posisi?.x) ? posisi.x : POSISI_KARTU_BAWAAN.x
  const y = Number.isFinite(posisi?.y) ? posisi.y : POSISI_KARTU_BAWAAN.y
  const maksX = Math.max(8, window.innerWidth - (lebar || 0) - 8)
  const maksY = Math.max(8, window.innerHeight - (tinggi || 0) - 8)
  return {
    x: Math.round(Math.min(maksX, Math.max(8, x))),
    y: Math.round(Math.min(maksY, Math.max(8, y))),
  }
}

/** Balasan cepat bawaan per topik. Semua di bawah MAKS_PANJANG_TEKS. */
const BALASAN = {
  kampus: [
    'Biaya kuliah UCIC?',
    'Cara daftar UCIC?',
    'Program studi UCIC?',
    'Beasiswa UCIC?',
    'Alamat kampus UCIC?',
    'Fasilitas kampus UCIC?',
    'Akreditasi UCIC?',
    'Kontak PMB UCIC?',
    'Jadwal kuliah UCIC?',
    'Dosen UCIC siapa?',
  ],
  cuaca: [
    'Cuaca Cirebon hari ini?',
    'Besok hujan tidak?',
    'Suhu sekarang berapa?',
    'Cuaca besok pagi?',
  ],
  waktu: ['Hari ini tanggal berapa?', 'Sekarang jam berapa?'],
  umum: [
    'Bisa jelaskan lagi?',
    'Contohnya seperti apa?',
    'Ringkas saja ya',
    'Terima kasih SELA',
  ],
}

/** Pola kata kunci -> topik. Diperiksa berurutan, yang pertama menang. */
const POLA_TOPIK = [
  {
    topik: 'kampus',
    pola:
      /\b(ucic|cic|uic|kampus|kuliah|prodi|program studi|jurusan|fakultas|pendaftaran|daftar|pmb|biaya|ukt|beasiswa|akreditasi|dosen|mahasiswa|semester|sks|wisuda|perpustakaan|lab|mushola|konvension|convention|alamat|lokasi|kontak|kantin|sbc|rektor)\b/i,
  },
  {
    topik: 'cuaca',
    pola: /\b(cuaca|hujan|cerah|mendung|suhu|prakiraan|angin|panas|dingin|berawan)\b/i,
  },
  {
    topik: 'waktu',
    pola: /\b(jam|pukul|tanggal|hari ini|besok|hari apa|waktu sekarang)\b/i,
  },
]

/**
 * Tebak topik dari sebuah teks (pertanyaan pengguna atau jawaban SELA).
 *
 * @param {string} teks
 * @returns {'kampus'|'cuaca'|'waktu'|'umum'}
 */
export function topikDari(teks) {
  const nilai = String(teks || '')
  if (!nilai.trim()) return 'umum'
  for (const { topik, pola } of POLA_TOPIK) {
    if (pola.test(nilai)) return topik
  }
  return 'umum'
}

/**
 * Pilih beberapa balasan cepat yang belum pernah dipakai pada sesi ini.
 *
 * @param {string} topik
 * @param {number} jumlah
 * @param {string[]} terpakai - daftar pertanyaan yang sudah ditampilkan
 * @returns {{label: string, text: string}[]}
 */
export function balasanUntuk(topik, jumlah = 3, terpakai = []) {
  const kandidat = BALASAN[topik] || BALASAN.umum
  const bekas = new Set(terpakai)
  const segar = kandidat.filter((q) => !bekas.has(q))
  const dasar = segar.length >= jumlah ? segar : kandidat

  // Acak stabil memakai Fisher-Yates agar tiap jawaban terasa berbeda.
  const acak = [...dasar]
  for (let i = acak.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[acak[i], acak[j]] = [acak[j], acak[i]]
  }

  return acak.slice(0, jumlah).map((text) => ({
    text,
    label: text.replace(/\?$/, ''),
  }))
}
