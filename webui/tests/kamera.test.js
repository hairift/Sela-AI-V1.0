/**
 * Pengujian aturan kamera antarmuka SELA.
 *
 * Yang dijaga di sini adalah janji ke pengguna:
 *  - saklar induk di Pengaturan mematikan kamera SEPENUHNYA (pil kecil pun
 *    tidak muncul, jadi tidak ada jalan masuk);
 *  - kartu kamera bisa dilipat jadi pil kecil, seperti panel obrolan;
 *  - melipat HANYA menyembunyikan tampilan: kartunya tetap terpasang sehingga
 *    kamera tidak mati dan SELA tetap bisa menjawab "saya lagi ngapain?";
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

import {
  KUNCI_KAMERA,
  KUNCI_KAMERA_TERBUKA,
  KUNCI_POSISI_KAMERA,
  LEBAR_KARTU_KAMERA,
  LEBAR_PIL_KAMERA,
  POSISI_KARTU_BAWAAN,
  TINGGI_KARTU_KAMERA,
  TINGGI_PIL_KAMERA,
  jepitPosisiKartu,
} from '../src/lib/percakapan.js'
import { t } from '../src/lib/translations.js'

const AKAR = join(dirname(fileURLToPath(import.meta.url)), '..')
const baca = (p) => readFileSync(join(AKAR, p), 'utf8')

const APP = baca('src/App.jsx')
const KARTU = baca('src/components/KartuKamera.jsx')
const PANEL = baca('src/components/ChatPanel.jsx')
const PY_KAMERA = baca('../src/ui/web/kamera_peramban.py')

const HAN = /[\u4e00-\u9fff]/

/** Jalankan fn dengan ukuran jendela buatan, lalu kembalikan window aslinya. */
function denganJendela(lebar, tinggi, fn) {
  const asli = globalThis.window
  globalThis.window = { innerWidth: lebar, innerHeight: tinggi }
  try {
    return fn()
  } finally {
    if (asli === undefined) delete globalThis.window
    else globalThis.window = asli
  }
}

test('dua kunci kamera terpisah: saklar induk dan lipatan', () => {
  assert.equal(KUNCI_KAMERA, 'sela_kamera_melayang')
  assert.equal(KUNCI_KAMERA_TERBUKA, 'sela_kamera_terbuka')
  assert.notEqual(KUNCI_KAMERA, KUNCI_KAMERA_TERBUKA)
})

test('terjemahan kamera baru ada dan berbahasa Indonesia', () => {
  for (const kunci of ['cameraShow', 'cameraHide', 'cameraLive', 'cameraOpen', 'photoAttached', 'photoRemove', 'photoAskHint']) {
    assert.ok(t.id[kunci], `terjemahan ${kunci} hilang`)
    assert.ok(!HAN.test(t.id[kunci]), `terjemahan ${kunci} masih beraksara Han`)
  }
})

test('pil kecil kamera hanya muncul saat saklar induk menyala', () => {
  // Penanda pil ada, dan berada di dalam blok yang dijaga kameraMelayang.
  const posIkon = APP.indexOf('data-kamera-ikon')
  assert.ok(posIkon > 0, 'tombol pil kecil kamera tidak ditemukan')
  const posPenjaga = APP.indexOf('{kameraMelayang &&')
  assert.ok(posPenjaga > 0, 'penjaga kameraMelayang tidak ditemukan')
  assert.ok(
    posPenjaga < posIkon,
    'pil kecil kamera harus berada di dalam penjaga kameraMelayang, ' +
      'supaya tidak bisa diakses saat kamera dimatikan dari Pengaturan',
  )
})

test('melipat kamera TIDAK melepas kartunya dari React', () => {
  // Ini inti permintaan pengguna: kartu boleh disembunyikan, tetapi kamera
  // harus tetap menyala supaya SELA masih bisa melihat.
  assert.ok(
    APP.includes('tersembunyi={!kameraTerbuka}'),
    'App harus meneruskan tersembunyi={!kameraTerbuka} ke KartuKamera',
  )
  assert.ok(
    !APP.includes('kameraTerbuka ? ('),
    'kartu kamera tidak boleh dirender bersyarat - melepasnya mematikan kamera',
  )
  assert.ok(KARTU.includes('tersembunyi'), 'KartuKamera tidak menerima prop tersembunyi')
  const mulaiKelas = KARTU.indexOf("opacity-0 pointer-events-none")
  assert.ok(mulaiKelas > 0, 'kelas opacity-0 tidak ditemukan pada kartu kamera')
  const kelasTersembunyi = KARTU.slice(
    KARTU.lastIndexOf('\n', mulaiKelas),
    KARTU.indexOf('\n', mulaiKelas),
  )
  assert.ok(
    kelasTersembunyi.includes('tersembunyi ?'),
    'kelas opacity-0 harus dipakai untuk keadaan tersembunyi',
  )
  assert.ok(
    !/\bhidden\b/.test(kelasTersembunyi),
    'jangan pakai kelas "hidden" untuk menyembunyikan kartu - video berhenti digambar',
  )
  // Pil kecil harus berada di posisi kartu terakhir, bukan melompat ke sudut.
  assert.equal(KUNCI_POSISI_KAMERA, 'sela_kamera_posisi')
  assert.ok(APP.includes('posisiPilKamera'), 'posisi pil kamera tidak dihitung')
  assert.equal(LEBAR_KARTU_KAMERA, 168)
})

test('kartu kamera menerima bingkai hidup', () => {
  assert.ok(APP.includes('onBingkaiHidup'), 'App tidak mengirim onBingkaiHidup')
  assert.ok(KARTU.includes('onBingkaiHidup'), 'KartuKamera tidak menerima onBingkaiHidup')
  assert.ok(KARTU.includes('JEDA_HIDUP_MS'), 'jeda bingkai hidup tidak ada')
})

test('posisi kartu kamera dijepit agar tidak pernah keluar jendela', () => {
  // Kasus nyata: kartu diseret ke kanan pada jendela 1280px, lalu antarmuka
  // berpindah ke potret 480px. Tanpa penjepitan, kartu berada di x=684 dan
  // tidak terlihat sama sekali - pengguna mengira kameranya hilang.
  const diPotret = denganJendela(480, 900, () =>
    jepitPosisiKartu({ x: 684, y: 414 }, LEBAR_KARTU_KAMERA, TINGGI_KARTU_KAMERA),
  )
  assert.ok(diPotret.x <= 480 - LEBAR_KARTU_KAMERA, `x=${diPotret.x} masih di luar jendela 480px`)
  assert.ok(diPotret.x >= 8, 'kartu tidak boleh menempel keluar tepi kiri')
  assert.ok(diPotret.y <= 900 - TINGGI_KARTU_KAMERA, `y=${diPotret.y} masih di luar jendela 900px`)

  // Posisi yang sudah di dalam jendela tidak boleh diubah.
  const tetap = denganJendela(1280, 800, () =>
    jepitPosisiKartu({ x: 600, y: 300 }, LEBAR_KARTU_KAMERA, TINGGI_KARTU_KAMERA),
  )
  assert.deepEqual(tetap, { x: 600, y: 300 })

  // Posisi rusak / belum pernah disimpan -> kembali ke posisi bawaan.
  const bawaan = denganJendela(1280, 800, () => jepitPosisiKartu(null, LEBAR_PIL_KAMERA, TINGGI_PIL_KAMERA))
  assert.deepEqual(bawaan, POSISI_KARTU_BAWAAN)

  // Nilai negatif pun dijepit, bukan dibiarkan.
  const negatif = denganJendela(1280, 800, () =>
    jepitPosisiKartu({ x: -50, y: -90 }, LEBAR_KARTU_KAMERA, TINGGI_KARTU_KAMERA),
  )
  assert.equal(negatif.x, 8)
  assert.equal(negatif.y, 8)

  // Jendela yang lebih kecil dari kartunya tidak boleh menghasilkan angka negatif.
  const sempit = denganJendela(120, 100, () =>
    jepitPosisiKartu({ x: 500, y: 500 }, LEBAR_KARTU_KAMERA, TINGGI_KARTU_KAMERA),
  )
  assert.ok(sempit.x >= 8 && sempit.y >= 8, `posisi sempit tidak valid: ${JSON.stringify(sempit)}`)
})

test('posisi melayang ikut dihitung ulang saat jendela berubah ukuran', () => {
  // Kartu kamera memakai posisi tampil hasil penjepitan, bukan posisi mentah.
  assert.ok(KARTU.includes('useUkuranJendela'), 'KartuKamera tidak memantau ukuran jendela')
  assert.ok(KARTU.includes('posisiTampil'), 'KartuKamera tidak memakai posisi tampil')
  assert.ok(
    !/style=\{\{\s*left:\s*posisi\.x/.test(KARTU),
    'kartu harus memakai posisiTampil (hasil jepitan), bukan posisi mentah',
  )
  // Pil kecil di App juga harus ikut dihitung ulang saat ukuran berubah.
  assert.ok(APP.includes('useUkuranJendela'), 'App tidak memantau ukuran jendela')
  const badanPil = APP.slice(APP.indexOf('const posisiPil = useMemo'), APP.indexOf('const sesiBaru'))
  assert.ok(
    badanPil.includes('lebarJendela') && badanPil.includes('tinggiJendela'),
    'posisi pil kamera tidak bergantung pada ukuran jendela',
  )
  // Keduanya memakai penjepit yang sama, jadi tidak mungkin berbeda pendapat.
  assert.ok(KARTU.includes('jepitPosisiKartu'), 'KartuKamera tidak memakai penjepit bersama')
  assert.ok(APP.includes('jepitPosisiKartu'), 'App tidak memakai penjepit bersama')
  // Ikon pelipat tidak boleh lagi dipaku di sudut kiri atas seperti v1.0.10.
  assert.ok(
    !/data-kamera-ikon[\s\S]{0,400}?fixed z-40 top-24 left-6/.test(APP),
    'ikon pelipat kamera dipaku di sudut kiri atas - itu penyebab tampilan "condong ke kiri"',
  )
})

test('tombol panah melipat kartu, bukan mematikan saklar induk', () => {
  // onTutup harus diarahkan ke lipatKamera (yang menulis kunci lipatan),
  // bukan ke fungsi yang menulis kunci saklar induk.
  assert.ok(APP.includes('onTutup={lipatKamera}'), 'onTutup bukan lipatKamera')
  const badan = APP.slice(APP.indexOf('const lipatKamera'), APP.indexOf('const bentangkanKamera'))
  assert.ok(badan.includes('KUNCI_KAMERA_TERBUKA'), 'lipatKamera tidak menulis kunci lipatan')
  assert.ok(
    !badan.includes('KUNCI_KAMERA,'),
    'lipatKamera tidak boleh mematikan saklar induk kamera',
  )
  // Ikonnya panah (chevron), bukan tanda silang.
  const bilah = KARTU.slice(KARTU.indexOf('data-kamera-lipat'), KARTU.indexOf('data-kamera-lipat') + 900)
  assert.ok(
    bilah.includes('M15 19l-7-7 7-7'),
    'tombol lipat harus memakai ikon panah (chevron), bukan tanda silang',
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
