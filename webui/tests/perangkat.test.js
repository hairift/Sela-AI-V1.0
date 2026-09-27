/**
 * Pengujian bagian "Perangkat & Aktivasi" dan daftar kata bangun.
 *
 * Janji ke pengguna:
 *  - status aktivasi perangkat TERLIHAT di antarmuka, bukan hanya di log;
 *  - ada jalan ke konsol xiaozhi.me supaya agent bisa diatur;
 *  - bila server memang mengirim kode aktivasi, kodenya ditampilkan;
 *  - daftar kata bangun yang tampil adalah yang BENAR-BENAR dikenali mesin
 *    pengenal suara, bukan pemilih yang tidak berpengaruh.
 *
 * Dijalankan dengan `npm test` (node --test).
 */

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

import { t } from '../src/lib/translations.js'

const AKAR = join(dirname(fileURLToPath(import.meta.url)), '..')
const baca = (p) => readFileSync(join(AKAR, p), 'utf8')

const PENGATURAN = baca('src/components/Settings.jsx')
const SERVER = baca('../src/ui/web/server.py')
const KATA_KUNCI = baca('../models/en/keywords.txt')

const HAN = /[\u4e00-\u9fff]/

test('terjemahan perangkat ada dan berbahasa Indonesia', () => {
  const kunci = [
    'sectionPerangkat',
    'perangkatDesc',
    'perangkatSerial',
    'perangkatId',
    'perangkatStatus',
    'perangkatAktif',
    'perangkatBelum',
    'perangkatPeriksa',
    'perangkatMemeriksa',
    'perangkatKonsol',
    'perangkatKonsolDesc',
    'perangkatKode',
    'perangkatKodeHint',
    'perangkatSudahTerdaftar',
    'perangkatGagal',
    'wakeWordChoice',
    'wakeWordChoiceDesc',
  ]
  for (const k of kunci) {
    assert.ok(t.id[k], `terjemahan ${k} hilang`)
    assert.ok(!HAN.test(t.id[k]), `terjemahan ${k} masih beraksara Han`)
  }
})

test('pengaturan menampilkan kartu Perangkat & Aktivasi', () => {
  assert.ok(
    PENGATURAN.includes('t.id.sectionPerangkat'),
    'kartu Perangkat & Aktivasi tidak ada di pengaturan',
  )
  assert.ok(PENGATURAN.includes('data-periksa-aktivasi'), 'tombol periksa ulang tidak ada')
  assert.ok(PENGATURAN.includes('data-konsol-xiaozhi'), 'tombol konsol xiaozhi tidak ada')
  assert.ok(PENGATURAN.includes('data-perangkat-status'), 'penanda status aktivasi tidak ada')
  // Kode aktivasi hanya muncul bila server memang mengirimkannya.
  assert.ok(PENGATURAN.includes('data-kode-aktivasi'), 'kotak kode aktivasi tidak ada')
  assert.ok(
    PENGATURAN.includes('hasilPeriksa?.code'),
    'kotak kode aktivasi harus bergantung pada kode dari server',
  )
  // Nomor seri bisa disalin (pengguna perlu menempelkannya di dasbor).
  assert.ok(PENGATURAN.includes('data-salin-serial'), 'tombol salin nomor seri tidak ada')
})

test('pengaturan memuat data perangkat dari mesin AI', () => {
  assert.ok(PENGATURAN.includes("fetch('/api/perangkat')"), 'data perangkat tidak dimuat')
  assert.ok(
    PENGATURAN.includes("fetch('/api/perangkat/periksa'"),
    'pemeriksaan aktivasi tidak dijalankan',
  )
  assert.ok(
    PENGATURAN.includes("fetch('/api/buka-tautan'"),
    'tautan konsol tidak dibuka lewat mesin AI',
  )
  assert.ok(PENGATURAN.includes('muatPerangkat()'), 'muatPerangkat tidak dipanggil saat halaman dibuka')
})

test('kata bangun yang tampil berasal dari berkas kata kunci', () => {
  // Antarmuka menampilkan daftar dari mesin AI, bukan daftar tetap di JS.
  assert.ok(PENGATURAN.includes('config?.wakeWords'), 'daftar kata bangun tidak dari mesin AI')
  assert.ok(PENGATURAN.includes('data-kata-bangun'), 'penanda kata bangun tidak ada')
  // Pemilih lama (yang menulis kunci tidak terpakai) harus hilang.
  assert.ok(
    !PENGATURAN.includes('wakeWordText'),
    'pemilih kata bangun lama masih ada - kunci itu tidak dibaca pengenal suara',
  )
  assert.ok(
    !/id="kata-bangun"/.test(PENGATURAN),
    'kontrol kata bangun lama masih tersisa',
  )
})

test('berkas kata kunci memuat tiga kata bangun yang sah', () => {
  const baris = KATA_KUNCI.split('\n')
    .map((b) => b.trim())
    .filter((b) => b && !b.startsWith('#'))
  assert.equal(baris.length, 3, `harus ada 3 kata bangun, ada ${baris.length}`)
  const label = baris.map((b) => b.slice(b.lastIndexOf('@') + 1))
  assert.deepEqual(label.sort(), ['HaiHai', 'HelloSela', 'Sela'])
  for (const b of baris) {
    const pos = b.lastIndexOf('@')
    assert.ok(pos > 0, `baris tanpa label: ${b}`)
    const nama = b.slice(pos + 1)
    assert.ok(!nama.includes(' '), `label tidak boleh berspasi: "${nama}"`)
    assert.ok(b.slice(0, pos).trim().length > 0, `baris tanpa token: ${b}`)
  }
})

test('mesin AI menyediakan endpoint perangkat dan tautan yang aman', () => {
  assert.ok(SERVER.includes('"/api/perangkat"'), 'endpoint /api/perangkat tidak terdaftar')
  assert.ok(
    SERVER.includes('"/api/perangkat/periksa"'),
    'endpoint pemeriksaan aktivasi tidak terdaftar',
  )
  assert.ok(SERVER.includes('"/api/buka-tautan"'), 'endpoint buka tautan tidak terdaftar')
  // Hanya host yang dipakai aplikasi yang boleh dibuka di peramban pengguna.
  assert.ok(SERVER.includes('_HOST_TAUTAN'), 'batas host tautan tidak ada')
  assert.ok(SERVER.includes('xiaozhi.me'), 'host xiaozhi.me tidak diizinkan')
  assert.ok(SERVER.includes('_daftar_kata_bangun'), 'pembaca daftar kata bangun tidak ada')
  // Endpoint periksa harus mengembalikan kode bila ada.
  assert.ok(SERVER.includes('"code"'), 'endpoint periksa tidak mengembalikan kode aktivasi')
})
