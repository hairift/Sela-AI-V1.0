/**
 * Pengujian aturan kamera antarmuka SELA.
 *
 * Yang dijaga di sini adalah janji ke pengguna:
 *  - saklar induk di Pengaturan mematikan kamera SEPENUHNYA (ikon kecil pun
 *    tidak muncul, jadi tidak ada jalan masuk);
 *  - kartu kamera bisa dilipat jadi ikon kecil, seperti panel obrolan;
 *  - foto sadar masuk ke kotak teks sebagai lampiran, BUKAN langsung jadi
 *    gelembung percakapan;
 *  - bingkai hidup dikirim lebih cepat daripada masa kedaluwarsa di sisi
 *    Python, supaya pertanyaan "saya lagi ngapain?" selalu punya gambar segar.
 *
 * Dijalankan dengan `npm test` (node --test).
 */

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

import { KUNCI_KAMERA, KUNCI_KAMERA_TERBUKA } from '../src/lib/percakapan.js'
import { t } from '../src/lib/translations.js'

const AKAR = join(dirname(fileURLToPath(import.meta.url)), '..')
const baca = (p) => readFileSync(join(AKAR, p), 'utf8')

const APP = baca('src/App.jsx')
const KARTU = baca('src/components/KartuKamera.jsx')
const PANEL = baca('src/components/ChatPanel.jsx')
const PY_KAMERA = baca('../src/ui/web/kamera_peramban.py')

const HAN = /[\u4e00-\u9fff]/

test('dua kunci kamera terpisah: saklar induk dan lipatan', () => {
  assert.equal(KUNCI_KAMERA, 'sela_kamera_melayang')
  assert.equal(KUNCI_KAMERA_TERBUKA, 'sela_kamera_terbuka')
  assert.notEqual(KUNCI_KAMERA, KUNCI_KAMERA_TERBUKA)
})

test('terjemahan kamera baru ada dan berbahasa Indonesia', () => {
  for (const kunci of ['cameraShow', 'cameraHide', 'cameraLive', 'photoAttached', 'photoRemove', 'photoAskHint']) {
    assert.ok(t.id[kunci], `terjemahan ${kunci} hilang`)
    assert.ok(!HAN.test(t.id[kunci]), `terjemahan ${kunci} masih beraksara Han`)
  }
})

test('ikon kecil kamera hanya muncul saat saklar induk menyala', () => {
  // Penanda ikon kecil ada, dan berada di dalam blok yang dijaga kameraMelayang.
  const posIkon = APP.indexOf('data-kamera-ikon')
  assert.ok(posIkon > 0, 'tombol ikon kecil kamera tidak ditemukan')
  const posPenjaga = APP.indexOf('{kameraMelayang &&')
  assert.ok(posPenjaga > 0, 'penjaga kameraMelayang tidak ditemukan')
  assert.ok(
    posPenjaga < posIkon,
    'ikon kecil kamera harus berada di dalam penjaga kameraMelayang, ' +
      'supaya tidak bisa diakses saat kamera dimatikan dari Pengaturan',
  )
})

test('kartu kamera menerima bingkai hidup', () => {
  assert.ok(APP.includes('onBingkaiHidup'), 'App tidak mengirim onBingkaiHidup')
  assert.ok(KARTU.includes('onBingkaiHidup'), 'KartuKamera tidak menerima onBingkaiHidup')
  assert.ok(KARTU.includes('JEDA_HIDUP_MS'), 'jeda bingkai hidup tidak ada')
})

test('tombol silang melipat kartu, bukan mematikan saklar induk', () => {
  // onTutup harus diarahkan ke lipatKamera (yang menulis kunci lipatan),
  // bukan ke fungsi yang menulis kunci saklar induk.
  assert.ok(APP.includes('onTutup={lipatKamera}'), 'onTutup bukan lipatKamera')
  const badan = APP.slice(APP.indexOf('const lipatKamera'), APP.indexOf('const bentangkanKamera'))
  assert.ok(badan.includes('KUNCI_KAMERA_TERBUKA'), 'lipatKamera tidak menulis kunci lipatan')
  assert.ok(
    !badan.includes('KUNCI_KAMERA,'),
    'lipatKamera tidak boleh mematikan saklar induk kamera',
  )
})

test('foto sadar dilampirkan ke kotak teks, bukan langsung jadi gelembung', () => {
  const badan = APP.slice(APP.indexOf('const tanganiBingkai'), APP.indexOf('const tanganiBingkaiHidup'))
  assert.ok(badan.includes('setLampiranFoto'), 'foto tidak dilampirkan ke kotak teks')
  assert.ok(
    !badan.includes('tambahFoto'),
    'foto sadar tidak boleh langsung dikirim sebagai gelembung percakapan',
  )
  // Pratinjau lampiran harus ada di panel obrolan.
  assert.ok(PANEL.includes('data-lampiran'), 'pratinjau lampiran tidak ada di ChatPanel')
  assert.ok(PANEL.includes('lampiran'), 'ChatPanel tidak menerima prop lampiran')
})

test('permintaan foto dari mesin AI tidak mengotori kotak teks', () => {
  const badan = APP.slice(APP.indexOf('const tanganiBingkai'), APP.indexOf('const tanganiBingkaiHidup'))
  assert.ok(
    badan.includes("sumber === 'ai'"),
    'tanganiBingkai harus membedakan sumber "ai" dan "pengguna"',
  )
  // Sumber dikirim oleh bridge Python lewat event ambil_foto.
  const hook = baca('src/lib/useSelaBridge.js')
  assert.ok(hook.includes("data.source === 'pengguna'"), 'useSelaBridge tidak membaca data.source')
  // Kartu kamera meneruskan sumber itu kembali.
  assert.ok(KARTU.includes("ambilFoto(permintaan.sumber)"), 'KartuKamera tidak meneruskan sumber')
  assert.ok(KARTU.includes("ambilFoto('pengguna')"), 'tombol foto tidak menandai sumber pengguna')
})

test('mengirim lampiran mengirim gambar lalu teks', () => {
  const badan = APP.slice(APP.indexOf('const kirimPesan'), APP.indexOf('const pilihSesi'))
  assert.ok(badan.includes('aksi.kirimBingkai'), 'gambar lampiran tidak dikirim ke mesin AI')
  assert.ok(badan.includes('aksi.tambahFoto'), 'gelembung foto tidak dibuat saat dikirim')
  assert.ok(badan.includes('aksi.kirimTeks'), 'teks pertanyaan tidak dikirim')
})

test('bingkai hidup lebih cepat daripada masa kedaluwarsa di Python', () => {
  const cocok = KARTU.match(/JEDA_HIDUP_MS\s*=\s*(\d+)/)
  assert.ok(cocok, 'JEDA_HIDUP_MS tidak ditemukan')
  const jedaDetik = Number(cocok[1]) / 1000

  const cocokPy = PY_KAMERA.match(/MAKS_UMUR_BINGKAI_S\s*=\s*([\d.]+)/)
  assert.ok(cocokPy, 'MAKS_UMUR_BINGKAI_S tidak ditemukan di kamera_peramban.py')
  const umurDetik = Number(cocokPy[1])

  assert.ok(
    jedaDetik < umurDetik,
    `bingkai hidup dikirim tiap ${jedaDetik}s tetapi kedaluwarsa dalam ` +
      `${umurDetik}s - gambar akan sering basi`,
  )
  // Sisakan ruang untuk jaringan yang lambat.
  assert.ok(
    jedaDetik <= umurDetik / 2,
    `jeda ${jedaDetik}s terlalu dekat dengan batas kedaluwarsa ${umurDetik}s`,
  )
})
