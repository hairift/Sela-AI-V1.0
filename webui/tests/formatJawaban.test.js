/**
 * Uji parser format jawaban untuk gelembung obrolan SELA.
 *
 * Kenapa berkas ini ada: aturan 14 pada Role Introduction xiaozhi.me meminta AI
 * memakai tanda "-" untuk fakta setara dan "1." untuk langkah berurutan. Agar
 * permintaan itu berguna, gelembung obrolan HARUS merender kedua bentuk itu
 * sebagai daftar yang rapi - termasuk variasi yang sering keluar dari model:
 * butir memakai "*" atau "•", nomor memakai "1)", dan butir bersarang.
 */

import test from 'node:test'
import assert from 'node:assert/strict'

import { pisahBlokJawaban, rapikanStrukturJawaban } from '../src/lib/formatJawaban.js'

const jenis = (teks) => pisahBlokJawaban(teks).map((b) => b.type)
const isi = (teks) => pisahBlokJawaban(teks).map((b) => b.items || b.content)

test('butir dengan tanda hubung menjadi daftar butir', () => {
  const teks = ['Fasilitas UCIC:', '- Perpustakaan', '- Laboratorium', '- WiFi'].join('\n')
  assert.deepEqual(jenis(teks), ['paragraph', 'unordered-list'])
  const daftar = pisahBlokJawaban(teks)[1]
  assert.deepEqual(daftar.items, ['Perpustakaan', 'Laboratorium', 'WiFi'])
})

test('butir dengan tanda bintang juga dikenali', () => {
  const teks = ['Syarat pendaftaran:', '* Ijazah SMA', '* Kartu keluarga'].join('\n')
  assert.deepEqual(jenis(teks), ['paragraph', 'unordered-list'])
})

test('butir dengan tanda titik tebal (bullet asli) dikenali', () => {
  const teks = ['Fasilitas:', '\u2022 Perpustakaan', '\u2022 Laboratorium'].join('\n')
  assert.deepEqual(jenis(teks), ['paragraph', 'unordered-list'])
})

test('nomor dengan titik menghasilkan daftar bernomor', () => {
  const teks = ['Cara mendaftar:', '1. Buka situs PMB', '2. Isi formulir', '3. Bayar'].join('\n')
  assert.deepEqual(jenis(teks), ['paragraph', 'ordered-list'])
  assert.deepEqual(pisahBlokJawaban(teks)[1].items, ['Buka situs PMB', 'Isi formulir', 'Bayar'])
})

test('nomor dengan tanda kurung juga dikenali', () => {
  const teks = ['Langkah:', '1) Daftar', '2) Verifikasi'].join('\n')
  assert.deepEqual(jenis(teks), ['paragraph', 'ordered-list'])
})

test('butir dan nomor tidak tercampur dalam satu blok', () => {
  const teks = ['Campur:', '- Satu', '1. Dua', '- Tiga'].join('\n')
  const blok = pisahBlokJawaban(teks)
  const tipeDaftar = blok.filter((b) => b.type.endsWith('list')).map((b) => b.type)
  // Harus terpisah menjadi dua blok daftar yang berbeda jenisnya.
  assert.ok(tipeDaftar.includes('unordered-list'), 'ada daftar butir')
  assert.ok(tipeDaftar.includes('ordered-list'), 'ada daftar bernomor')
  assert.notEqual(tipeDaftar[0], tipeDaftar[1] || 'x', 'jenisnya tidak sama')
})

test('jawaban pendek tetap berupa paragraf, bukan daftar', () => {
  const teks = 'Halo, saya SELA, asisten kampus UCIC.'
  assert.deepEqual(jenis(teks), ['paragraph'])
})

test('jawaban tanpa tanda daftar tidak dipaksa jadi daftar', () => {
  const teks = 'Rektor UCIC saat ini memimpin kampus dengan fokus pada akreditasi.'
  const blok = pisahBlokJawaban(teks)
  assert.equal(blok.length, 1)
  assert.equal(blok[0].type, 'paragraph')
})

test('daftar panjang tetap utuh sebagai satu blok', () => {
  const baris = ['Prodi UCIC:']
  for (let i = 1; i <= 8; i += 1) baris.push(`- Prodi ${i}`)
  const blok = pisahBlokJawaban(baris.join('\n'))
  const daftar = blok.find((b) => b.type === 'unordered-list')
  assert.equal(daftar.items.length, 8)
})

test('baris kosong memisahkan dua daftar', () => {
  const teks = ['- Satu', '- Dua', '', '- Tiga', '- Empat'].join('\n')
  const jenisBlok = jenis(teks)
  assert.equal(jenisBlok.filter((t) => t === 'unordered-list').length, 2, 'dua daftar terpisah')
})

test('rapikanStrukturJawaban menormalkan daftar yang menempel pada judul', () => {
  // Model kadang menulis "Fasilitas: - Perpustakaan - Laboratorium" dalam satu baris.
  const teks = 'Fasilitas: - Perpustakaan - Laboratorium - WiFi'
  const rapi = rapikanStrukturJawaban(teks)
  const blok = pisahBlokJawaban(rapi)
  assert.equal(blok[0].type, 'paragraph', 'judul tetap paragraf')
  assert.equal(blok[1].type, 'unordered-list', 'butir jadi daftar')
  assert.equal(blok[1].items.length, 3, 'tiga butir terpisah')
})

test('rapikanStrukturJawaban menormalkan nomor yang menempel pada judul', () => {
  const teks = 'Cara daftar: 1. Buka situs 2. Isi formulir 3. Bayar'
  const rapi = rapikanStrukturJawaban(teks)
  const blok = pisahBlokJawaban(rapi)
  assert.equal(blok[1].type, 'ordered-list', 'nomor jadi daftar bernomor')
  assert.equal(blok[1].items.length, 3, 'tiga langkah terpisah')
})

test('rapikanStrukturJawaban tidak merusak kalimat biasa', () => {
  const teks = 'Kampus UCIC berdiri sejak 2008 dan terus berkembang.'
  assert.equal(rapikanStrukturJawaban(teks), teks)
})

test('rapikanStrukturJawaban tidak memecah desimal atau versi', () => {
  // Desimal seperti 250.000 dan versi 1.0.12 tidak boleh jadi daftar palsu.
  const teks = 'Biaya pendaftaran 250.000 rupiah dan versi 1.0.12 sudah rilis.'
  const rapi = rapikanStrukturJawaban(teks)
  assert.equal(pisahBlokJawaban(rapi).filter((b) => b.type === 'ordered-list').length, 0, 'tidak ada daftar palsu')
})

test('isi butir dipertahankan apa adanya', () => {
  const teks = ['- Beasiswa prestasi hingga 100%', '- Potongan uang pangkal'].join('\n')
  const daftar = pisahBlokJawaban(teks)[0]
  assert.deepEqual(daftar.items, ['Beasiswa prestasi hingga 100%', 'Potongan uang pangkal'])
})
