/**
 * Perender teks jawaban SELA.
 *
 * Mesin AI membalas dengan penanda Markdown sederhana (``**tebal**``,
 * ``*miring*``, daftar ``-``, daftar bernomor, dan tautan). Sebelumnya penanda
 * itu tampil apa adanya sehingga gelembung chat penuh tanda bintang dan tidak
 * enak dibaca.
 *
 * Komponen ini mengubahnya menjadi teks berformat tanpa memakai pustaka
 * Markdown pihak ketiga: jawaban SELA hanya perlu bentuk sederhana, dan
 * menghindari ``dangerouslySetInnerHTML`` berarti tidak ada risiko penyisipan
 * HTML dari isi jawaban.
 */

import { Fragment } from 'react'

/** Ubah satu baris menjadi potongan React dengan tebal/miring/tautan. */
function barisKaya(teks, kunciAwal) {
  const potongan = []
  // Urutan penting: tautan, tebal, lalu miring.
  const pola = /(\[[^\]]+\]\([^)\s]+\))|(\*\*[^*]+\*\*)|(__[^_]+__)|(\*[^*\n]+\*)|(_[^_\n]+_)/g

  let posisi = 0
  let nomor = 0
  let cocok
  while ((cocok = pola.exec(teks)) !== null) {
    if (cocok.index > posisi) {
      potongan.push(teks.slice(posisi, cocok.index))
    }
    const isi = cocok[0]
    const kunci = `${kunciAwal}-${nomor++}`

    if (isi.startsWith('[')) {
      const pisah = isi.indexOf('](')
      const label = isi.slice(1, pisah)
      const url = isi.slice(pisah + 2, -1)
      potongan.push(
        <a
          key={kunci}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 dark:text-blue-400 underline decoration-blue-300 dark:decoration-blue-700 underline-offset-2 hover:decoration-2 break-all"
        >
          {label}
        </a>,
      )
    } else if (isi.startsWith('**') || isi.startsWith('__')) {
      potongan.push(
        <strong key={kunci} className="font-semibold text-gray-900 dark:text-white">
          {isi.slice(2, -2)}
        </strong>,
      )
    } else {
      potongan.push(
        <em key={kunci} className="italic">
          {isi.slice(1, -1)}
        </em>,
      )
    }
    posisi = cocok.index + isi.length
  }
  if (posisi < teks.length) potongan.push(teks.slice(posisi))
  return potongan
}

/**
 * Bersihkan sisa penanda yang tidak sempat diurai, mis. bintang tunggal yang
 * menggantung, sehingga tidak ada tanda aneh yang tampil ke pengguna.
 */
function bersihkanPenanda(teks) {
  return String(teks || '')
    .replace(/\*\*\s*\*\*/g, '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/`{1,3}([^`]*)`{1,3}/g, '$1')
    .replace(/^\s*>\s?/gm, '')
    .replace(/\n{3,}/g, '\n\n')
}

export default function TeksKaya({ teks, className = '' }) {
  const isi = bersihkanPenanda(teks)
  const baris = isi.split('\n')

  const keluaran = []
  let daftar = null // { jenis: 'ul' | 'ol', butir: [] }

  const tutupDaftar = () => {
    if (!daftar) return
    const Tag = daftar.jenis === 'ol' ? 'ol' : 'ul'
    keluaran.push(
      <Tag
        key={`d-${keluaran.length}`}
        className={
          daftar.jenis === 'ol'
            ? 'list-decimal list-outside ml-4 space-y-1 my-1.5'
            : 'list-disc list-outside ml-4 space-y-1 my-1.5'
        }
      >
        {daftar.butir.map((b, i) => (
          <li key={i} className="pl-0.5 leading-relaxed">
            {barisKaya(b, `li-${keluaran.length}-${i}`)}
          </li>
        ))}
      </Tag>,
    )
    daftar = null
  }

  baris.forEach((mentah, i) => {
    const baris_ = mentah.trim()

    // Butir daftar: "- ", "* ", "• "
    const ul = baris_.match(/^[-*•]\s+(.*)$/)
    // Butir bernomor: "1. ", "2) "
    const ol = baris_.match(/^(\d{1,2})[.)]\s+(.*)$/)

    if (ul) {
      if (daftar && daftar.jenis !== 'ul') tutupDaftar()
      if (!daftar) daftar = { jenis: 'ul', butir: [] }
      daftar.butir.push(ul[1])
      return
    }
    if (ol) {
      if (daftar && daftar.jenis !== 'ol') tutupDaftar()
      if (!daftar) daftar = { jenis: 'ol', butir: [] }
      daftar.butir.push(ol[2])
      return
    }

    tutupDaftar()

    if (!baris_) {
      // Baris kosong -> jarak antar paragraf.
      keluaran.push(<div key={`s-${i}`} className="h-1.5" />)
      return
    }

    // Judul tebal yang berdiri sendiri dijadikan baris tegas.
    if (/^\*\*[^*]+\*\*:?$/.test(baris_)) {
      keluaran.push(
        <p key={`h-${i}`} className="font-semibold text-gray-900 dark:text-white mt-1">
          {barisKaya(baris_.replace(/:$/, ''), `h-${i}`)}
        </p>,
      )
      return
    }

    keluaran.push(
      <p key={`p-${i}`} className="leading-relaxed">
        {barisKaya(baris_, `p-${i}`)}
      </p>,
    )
  })

  tutupDaftar()

  return <div className={`space-y-0.5 ${className}`}>{keluaran.map((e, i) => (
    <Fragment key={i}>{e}</Fragment>
  ))}</div>
}
