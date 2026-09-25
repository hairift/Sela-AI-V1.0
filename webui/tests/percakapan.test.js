/**
 * Pengujian aturan percakapan antarmuka (webui/src/lib/percakapan.js).
 *
 * Yang dijaga di sini: batas panjang teks harus sama dengan jaring pengaman
 * di sisi Python, dan SEMUA balasan cepat harus muat di kolom obrolan -
 * kalau tidak, tombolnya sendiri akan ditolak server.
 *
 * Dijalankan dengan `npm test` (node --test).
 */

import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  KAMPUS,
  KUNCI_KAMERA,
  MAKS_PANJANG_TEKS,
  balasanUntuk,
  topikDari,
} from '../src/lib/percakapan.js'

const TOPIK = ['kampus', 'cuaca', 'waktu', 'umum']

test('MAKS_PANJANG_TEKS sama dengan jaring pengaman Python (24)', () => {
  assert.equal(MAKS_PANJANG_TEKS, 24)
})

test('topikDari mengenali pertanyaan kampus', () => {
  assert.equal(topikDari('Kontak dan lokasi UCIC?'), 'kampus')
  assert.equal(topikDari('berapa biaya kuliah'), 'kampus')
  assert.equal(topikDari('program studi apa saja'), 'kampus')
})

test('topikDari mengenali cuaca dan waktu', () => {
  assert.equal(topikDari('Cuaca Cirebon hari ini?'), 'cuaca')
  assert.equal(topikDari('apakah besok hujan'), 'cuaca')
  assert.equal(topikDari('sekarang jam berapa'), 'waktu')
})

test('topikDari jatuh ke umum untuk teks lain', () => {
  assert.equal(topikDari('apa itu kucing'), 'umum')
  assert.equal(topikDari(''), 'umum')
  assert.equal(topikDari(null), 'umum')
})

test('semua balasan cepat muat di batas panjang kolom obrolan', () => {
  for (const topik of TOPIK) {
    for (const { text, label } of balasanUntuk(topik, 20, [])) {
      assert.ok(
        text.length <= MAKS_PANJANG_TEKS,
        `balasan "${text}" (${text.length}) melebihi ${MAKS_PANJANG_TEKS}`,
      )
      assert.ok(label.length > 0)
    }
  }
})

test('balasanUntuk menghormati jumlah yang diminta', () => {
  assert.equal(balasanUntuk('kampus', 3, []).length, 3)
  assert.equal(balasanUntuk('kampus', 2, []).length, 2)
})

test('balasanUntuk mengutamakan pilihan yang belum terpakai', () => {
  const awal = balasanUntuk('kampus', 3, []).map((p) => p.text)
  const lanjut = balasanUntuk('kampus', 3, awal).map((p) => p.text)

  for (const teks of lanjut) {
    assert.ok(!awal.includes(teks), `"${teks}" seharusnya belum terpakai`)
  }
})

test('balasanUntuk tetap memberi pilihan saat semua sudah terpakai', () => {
  const semua = balasanUntuk('umum', 20, []).map((p) => p.text)
  const hasil = balasanUntuk('umum', 3, semua)
  assert.equal(hasil.length, 3)
})

test('topik tak dikenal memakai balasan umum', () => {
  const hasil = balasanUntuk('topik_aneh', 3, [])
  assert.equal(hasil.length, 3)
})

test('titik peta kampus berada di sekitar Cirebon', () => {
  assert.ok(KAMPUS.lat < -6.7 && KAMPUS.lat > -6.8)
  assert.ok(KAMPUS.lon > 108.5 && KAMPUS.lon < 108.6)
  assert.match(KAMPUS.alamat, /Kesambi/)
})

test('kunci setelan kamera berupa string', () => {
  assert.equal(typeof KUNCI_KAMERA, 'string')
  assert.ok(KUNCI_KAMERA.length > 0)
})
