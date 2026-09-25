/**
 * Pengujian perapi teks jawaban (webui/src/lib/teks.js).
 *
 * Fokus pada kasus nyata yang pernah muncul di layar: blok kalimat yang
 * tercetak dua kali karena mesin AI menggabungkan dua hasil alat data yang
 * isinya mirip. Contoh di bawah diambil apa adanya dari tangkapan layar
 * pemeriksaan `scripts/cek_percakapan_baru.py`.
 *
 * Dijalankan dengan `npm test` (node --test).
 */

import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  MIN_PANJANG_BLOK_GANDA,
  buangBlokGanda,
  buangPenandaSisa,
  kunciKata,
  pecahKata,
  runtuhkanBlokGanda,
} from '../src/lib/teks.js'

// ── Kasus nyata 1: jawaban Bahasa Indonesia soal kontak & lokasi UCIC ────────
const KAMPUS_1 =
  'Ini ya info kontak dan lokasi UCIC: Kampus 1 ada di Jl. Kesambi No. 58A, Kesambi, Kota Cirebon.'
const KAMPUS_2 =
  'Kampus 2 di Jl. Kesambi No. 202, Kesambi, Kota Cirebon.'

// ── Kasus nyata 2: jawaban beraksara Han yang terpotong-potong ──────────────
const HAN_A = '好喔，UCIC 的联络方式和位置我帮你整理一下。'
const HAN_B = 'WhatsApp PMB 是 0812 1670 0519，'
const HAN_C = '网站是 pmb.cic.ac.id，报名连结是 pmb.cic.ac.id/register。'

test('kunciKata membuang tanda baca dan huruf besar', () => {
  assert.equal(kunciKata('Cirebon.'), 'cirebon')
  assert.equal(kunciKata('UCIC:'), 'ucic')
  assert.equal(kunciKata('58A,'), '58a')
  assert.equal(kunciKata('WhatsApp'), 'whatsapp')
})

test('kunciKata tetap mengenali aksara Han', () => {
  assert.equal(kunciKata('好喔，UCIC'), '好喔ucic')
  assert.equal(kunciKata('网站是'), '网站是')
  assert.notEqual(kunciKata('的联络方式和位置我帮你整理一下。'), '')
})

test('pecahKata memecah baris menjadi kata tanpa spasi kosong', () => {
  assert.deepEqual(pecahKata('  satu   dua tiga '), ['satu', 'dua', 'tiga'])
  assert.deepEqual(pecahKata(''), [])
})

test('runtuhkanBlokGanda membuang salinan yang berurutan', () => {
  const blok = ['Kampus', 'pertama', 'ada', 'di', 'Jalan', 'Kesambi']
  assert.ok(blok.join('').length >= MIN_PANJANG_BLOK_GANDA)
  assert.deepEqual(runtuhkanBlokGanda([...blok, ...blok]), blok)
})

test('runtuhkanBlokGanda membiarkan kata pendek yang memang diulang', () => {
  assert.deepEqual(runtuhkanBlokGanda(['ya', 'ya', 'ya']), ['ya', 'ya', 'ya'])
  assert.ok(MIN_PANJANG_BLOK_GANDA > 'ya ya'.length)
})

test('runtuhkanBlokGanda membiarkan jawaban yang sudah bersih', () => {
  const bersih = ['SELA', 'siap', 'membantu', 'silakan', 'tanya', 'soal', 'UCIC']
  assert.deepEqual(runtuhkanBlokGanda(bersih), bersih)
})

test('buangBlokGanda memperbaiki kalimat kampus yang tercetak dua kali', () => {
  const masukan = `${KAMPUS_1} ${KAMPUS_1} ${KAMPUS_2}`

  const hasil = buangBlokGanda(masukan)

  assert.equal(hasil, `${KAMPUS_1} ${KAMPUS_2}`)
  assert.equal(hasil.split(KAMPUS_1).length - 1, 1)
})

test('buangBlokGanda memperbaiki jawaban beraksara Han', () => {
  // Bentuk yang benar-benar terlihat: A B A B C B C.
  const masukan = `${HAN_A} ${HAN_B} ${HAN_A} ${HAN_B} ${HAN_C} ${HAN_B} ${HAN_C}`

  const hasil = buangBlokGanda(masukan)

  assert.equal(hasil, `${HAN_A} ${HAN_B} ${HAN_C}`)
  assert.equal(hasil.split(HAN_A).length - 1, 1)
  assert.equal(hasil.split(HAN_C).length - 1, 1)
})

test('buangBlokGanda tidak mengubah jawaban yang memang bersih', () => {
  const bersih = 'SELA siap membantu. Silakan tanya soal UCIC. Terima kasih!'
  assert.equal(buangBlokGanda(bersih), bersih)
})

test('buangBlokGanda menjaga susunan baris dan daftar', () => {
  const masukan = [
    'Berikut daftar kampus UCIC:',
    `- ${KAMPUS_1} ${KAMPUS_1}`,
    `- ${KAMPUS_2}`,
  ].join('\n')

  const hasil = buangBlokGanda(masukan)
  const baris = hasil.split('\n')

  assert.equal(baris.length, 3)
  assert.equal(baris[0], 'Berikut daftar kampus UCIC:')
  assert.equal(baris[1], `- ${KAMPUS_1}`)
  assert.equal(baris[2], `- ${KAMPUS_2}`)
})

test('buangBlokGanda aman untuk teks kosong atau aneh', () => {
  assert.equal(buangBlokGanda(''), '')
  assert.equal(buangBlokGanda(null), 'null')
  assert.equal(buangBlokGanda('...'), '...')
  assert.equal(buangBlokGanda('a\n\nb'), 'a\n\nb')
})

test('buangBlokGanda tidak menggantung pada jawaban sangat panjang', () => {
  // 600 kata unik: pemangkasan pencarian blok harus menjaga waktu tetap wajar.
  const kata = Array.from({ length: 600 }, (_, i) => `kata${i}`)
  const mulai = Date.now()
  const hasil = buangBlokGanda(kata.join(' '))
  const durasi = Date.now() - mulai

  assert.equal(hasil, kata.join(' '))
  assert.ok(durasi < 1000, `terlalu lambat: ${durasi} ms`)
})

test('buangPenandaSisa membuang bintang dan garis bawah liar', () => {
  assert.equal(buangPenandaSisa('**tebal**'), 'tebal')
  assert.equal(buangPenandaSisa('sisa ** bintang'), 'sisa  bintang')
  assert.equal(buangPenandaSisa('__tebal__'), 'tebal')
})
