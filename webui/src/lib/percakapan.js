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

/** Titik peta kampus (dari OpenStreetMap: Universitas Catur Insan Cendekia). */
export const KAMPUS = {
  nama: 'Universitas Catur Insan Cendekia (UCIC)',
  lat: -6.7338864,
  lon: 108.5532478,
  alamat: 'Jl. Kesambi No. 202, Kesambi, Kota Cirebon',
}

/** Kunci penyimpanan setelan kartu kamera melayang di peramban. */
export const KUNCI_KAMERA = 'sela_kamera_melayang'

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
