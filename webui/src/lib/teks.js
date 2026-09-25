/**
 * Perapi teks jawaban SELA (fungsi murni, tanpa React).
 *
 * Dipisah dari komponen supaya bisa diuji langsung dengan `node --test`.
 * Semua fungsi di sini hanya mengubah TAMPILAN; isi jawaban dari mesin AI
 * tidak pernah diubah di sisi Python.
 */

/** Buang sisa penanda markdown yang tidak berpasangan (mis. `**` tunggal). */
export function buangPenandaSisa(teks = '') {
  return String(teks)
    .replace(/\*+/g, '')
    .replace(/_{2,}/g, '')
}

/**
 * Bentuk kunci sebuah kata: huruf kecil, tanpa tanda baca.
 *
 * Memakai kelas Unicode (\p{L}, \p{N}) supaya tetap bekerja untuk jawaban
 * beraksara lain (mis. Han) yang pernah keluar dari server.
 */
export function kunciKata(kata = '') {
  return String(kata)
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, '')
}

/** Pecah satu baris menjadi kata-kata (spasi kosong dibuang). */
export function pecahKata(baris = '') {
  return String(baris).split(/\s+/).filter(Boolean)
}

/**
 * Panjang teks minimum sebuah blok agar boleh dianggap salinan ganda.
 *
 * Blok yang lebih pendek dari ini dibiarkan, supaya pengulangan yang memang
 * disengaja ("ya ya", "sangat sangat") tidak ikut dibuang.
 */
export const MIN_PANJANG_BLOK_GANDA = 24

/**
 * Syarat yang jauh lebih ketat untuk membuang blok ganda di AKHIR baris.
 *
 * Blok di akhir baris bisa saja memang kalimat penutup yang menyebut ulang
 * sesuatu (mis. "Kedua kampus ada di Jl. Kesambi, Kota Cirebon."). Karena itu
 * hanya blok yang benar-benar panjang dan utuh yang dibuang.
 */
const MIN_KATA_EKOR_GANDA = 6
const MIN_PANJANG_EKOR_GANDA = 48

/**
 * Batas jumlah kata per blok yang diperiksa.
 *
 * Duplikat nyata selalu berupa kalimat atau paragraf pendek; membatasi
 * pencarian menjaga biaya tetap kecil bahkan untuk jawaban sangat panjang.
 */
const MAKS_KATA_BLOK = 60

/** Susun kunci tiap kata beserta jumlah panjang kuncinya (untuk O(1)). */
function siapkanKunci(kata) {
  const kunci = kata.map(kunciKata)
  const jumlah = new Array(kunci.length + 1).fill(0)
  for (let i = 0; i < kunci.length; i += 1) {
    jumlah[i + 1] = jumlah[i] + kunci[i].length
  }
  return { kunci, jumlah }
}

/** Panjang kunci pada rentang kata [mulai, mulai + panjang). */
function panjangKunci(jumlah, mulai, panjang) {
  return jumlah[mulai + panjang] - jumlah[mulai]
}

/** Apakah dua rentang kata sama persis (menurut kuncinya). */
function rentangSama(kunci, a, b, panjang) {
  for (let k = 0; k < panjang; k += 1) {
    const kiri = kunci[a + k]
    if (!kiri || kiri !== kunci[b + k]) return false
  }
  return true
}

/**
 * Buang blok di akhir baris yang sudah muncul sebelumnya.
 *
 * Menangkap pola yang tersisa setelah penggabungan, mis. "A B C B C" yang
 * seharusnya "A B C": ekor "B C" sudah ada di tengah kalimat.
 */
function buangEkorGanda(kata, kunci, jumlah) {
  const n = kata.length
  const pMaks = Math.min(Math.floor(n / 2), MAKS_KATA_BLOK)

  for (let p = pMaks; p >= MIN_KATA_EKOR_GANDA; p -= 1) {
    const mulai = n - p
    // Panjang kunci bertambah seiring p, jadi begitu terlalu pendek, semua p
    // yang lebih kecil juga terlalu pendek.
    if (panjangKunci(jumlah, mulai, p) < MIN_PANJANG_EKOR_GANDA) break
    for (let i = 0; i + p <= mulai; i += 1) {
      if (rentangSama(kunci, i, mulai, p)) return kata.slice(0, mulai)
    }
  }

  return kata
}

/**
 * Runtuhkan blok kata yang tercetak dua kali berturut-turut.
 *
 * Contoh: ``[A B C A B C D]`` menjadi ``[A B C D]``. Perbandingan memakai
 * kunci yang sudah dinormalkan (huruf kecil, tanpa tanda baca) sehingga tetap
 * bekerja untuk kalimat dengan tanda baca berbeda.
 *
 * Dipakai pada saat pesan DIGABUNG, bukan pada setiap gambar ulang layar,
 * supaya tidak membebani animasi mengetik.
 */
export function runtuhkanBlokGanda(kata = []) {
  const { kunci, jumlah } = siapkanKunci(kata)
  const keluar = []
  const n = kata.length
  let i = 0

  while (i < n) {
    let panjangBlok = 0
    const pMaks = Math.min(Math.floor((n - i) / 2), MAKS_KATA_BLOK)
    for (let p = pMaks; p >= 1; p -= 1) {
      if (panjangKunci(jumlah, i, p) < MIN_PANJANG_BLOK_GANDA) break
      if (rentangSama(kunci, i, i + p, p)) {
        panjangBlok = p
        break
      }
    }

    if (panjangBlok > 0) {
      for (let k = 0; k < panjangBlok; k += 1) keluar.push(kata[i + k])
      i += panjangBlok * 2
    } else {
      keluar.push(kata[i])
      i += 1
    }
  }

  const akhir = siapkanKunci(keluar)
  return buangEkorGanda(keluar, akhir.kunci, akhir.jumlah)
}

/**
 * Buang blok kata ganda pada tiap baris tanpa mengubah susunan barisnya.
 *
 * Bekerja per baris supaya daftar dan paragraf tetap utuh, dan supaya spasi
 * tunggal antar kata bisa dipulihkan dengan aman.
 */
export function buangBlokGanda(teks = '') {
  return String(teks)
    .split('\n')
    .map((baris) => runtuhkanBlokGanda(pecahKata(baris)).join(' ').trim())
    .join('\n')
}
