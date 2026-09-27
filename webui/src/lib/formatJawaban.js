/**
 * Perapian format jawaban AI untuk gelembung obrolan SELA.
 *
 * Kenapa berkas ini ada: aturan 14 pada Role Introduction xiaozhi.me meminta AI
 * memilih sendiri format jawaban - "-" untuk fakta setara, "1." untuk langkah
 * berurutan, paragraf untuk jawaban pendek. Model sering tidak menaatinya
 * dengan rapi: butir memakai "*" atau "•", nomor memakai "1)", dan daftar
 * ditulis menempel pada judul ("Fasilitas: - A - B - C").
 *
 * Fungsi di sini menormalkan bentuk-bentuk itu menjadi markdown sederhana yang
 * pasti dirender sebagai daftar, tanpa menebak-tebak. Logika ini semula ada di
 * dalam ChatBubble.jsx; dipindah ke sini agar bisa diuji langsung tanpa
 * merender React.
 */

// Pola tautan, dipakai untuk melindungi pranala dari perapian.
const POLA_TAUTAN = /(https?:\/\/[^\s]+)/g
const AWALAN_TOKEN = '\u0000SELA_URL_'

/**
 * Jalankan `pemformat` dengan seluruh tautan disembunyikan lebih dulu.
 *
 * Tanpa ini, perapian daftar bisa merusak pranala yang kebetulan memuat tanda
 * hubung atau angka bertitik.
 */
function denganTautanDilindungi(teks, pemformat) {
  const tautan = []
  const dilindungi = String(teks || '').replace(POLA_TAUTAN, (url) => {
    const token = `${AWALAN_TOKEN}${tautan.length}__`
    tautan.push(url)
    return token
  })

  const hasil = pemformat(dilindungi)
  return hasil.replace(
    new RegExp(`${AWALAN_TOKEN}(\\d+)__`, 'g'),
    (_, index) => tautan[Number(index)] || '',
  )
}

/**
 * Rapikan struktur teks agar daftar benar-benar menjadi baris tersendiri.
 *
 * Inilah fungsi yang dipanggil sebelum pemecahan blok. Urutannya penting:
 * penanda butir diseragamkan dulu, baru daftar yang menempel pada judul
 * dipecah menjadi baris.
 *
 * @param {string} text - teks jawaban mentah dari mesin AI
 * @returns {string} teks yang setiap butir/angkanya berdiri di baris sendiri
 */
export function rapikanStrukturJawaban(text = '') {
  return denganTautanDilindungi(text, (nilai) => {
    let normalized = nilai
      .replace(/\r/g, '')
      .replace(/[ \t]+/g, ' ')
      .replace(/[ \t]+\n/g, '\n')
      .replace(/\n[ \t]+/g, '\n')
      // Penanda tebal gaya lain diubah ke bentuk yang dikenali perender.
      .replace(/__([^_\n]+)__/g, '**$1**')

    // Poin daftar dari model sering memakai karakter lain. Diseragamkan agar
    // benar-benar dirender sebagai daftar, bukan kalimat berhamburan.
    normalized = normalized
      .replace(/^[ ]*[\u2022\u00b7\u25aa\u25e6\u2023\u2013\u2014]\s+/gm, '- ')
      .replace(/^([ ]*)([1-9]\d?)\)\s+/gm, '$1$2. ')

    // Jika AI menulis "A: 1. ... 2. ..." atau "A: - ... - ...",
    // ubah menjadi list markdown yang bisa dirender rapi.
    normalized = normalized
      .replace(/:\s+(?=(?:[-*]\s+|(?:[1-9]|[1-9]\d)[.)]\s+))/g, ':\n')
      .replace(/(^|\n)((?:[1-9]|[1-9]\d)[.)])(?=\S)/g, '$1$2 ')
      .replace(/([^\n])[\s,;]+((?:[1-9]|[1-9]\d)[.)]\s+)/g, '$1\n$2')
      // Tanda hubung hanya dianggap awal bullet bila didahului akhir kalimat
      // atau baris baru. Sebelumnya spasi di sekitar tanda pisah biasa
      // ("biaya - sekitar empat juta") ikut diubah menjadi bullet sehingga
      // potongan kalimat tampil sebagai poin daftar.
      .replace(/([.!?])\s+([-*]\s+(?=[A-Z0-9]))/g, '$1\n$2')

    // Daftar sebaris: "Fasilitas: - Perpustakaan - Laboratorium - WiFi".
    // Aturan di atas hanya memecah butir PERTAMA, sehingga sisanya menempel
    // menjadi satu butir panjang. Di sini setiap tanda hubung yang mengawali
    // kata baru dijadikan baris sendiri - tetapi hanya bila tanda itu berada
    // di dalam baris yang SUDAH memuat pola "label:" atau sudah diawali butir,
    // supaya tanda pisah biasa ("biaya - sekitar empat juta") tidak ikut
    // terpecah menjadi daftar.
    normalized = normalized
      .split('\n')
      .map((baris) => {
        const kandidatDaftar = /:\s*[-*]\s+\S/.test(baris) || /^\s*[-*]\s+\S/.test(baris)
        if (!kandidatDaftar) return baris
        // Hanya pecah pada tanda hubung yang berdiri sendiri antar-spasi dan
        // diikuti huruf/angka (bukan tanda pisah dalam rentang angka).
        return baris.replace(/\s+[-*]\s+(?=[A-Za-z0-9])/g, '\n- ')
      })
      .join('\n')

    // Label bagian yang sering muncul dari dataset dibuat sebagai baris sendiri
    // agar "Program S1:" tidak menempel dengan paragraf sebelumnya.
    normalized = normalized.replace(
      /([.!?])\s+((?:Program|Fakultas|Syarat|Langkah|Biaya|Fasilitas|Beasiswa|Kontak|Lokasi)\b[^:\n]{0,60}:)/gi,
      '$1\n\n$2',
    )

    return normalized.replace(/\n{3,}/g, '\n\n').trim()
  })
}

/**
 * Pisahkan teks menjadi blok: judul, daftar butir, daftar bernomor, paragraf.
 *
 * Aturan daftar: teks yang sudah bernomor ("1.", "2.") tetap bernomor karena
 * urutannya penting (langkah, tahapan). Teks berbutir ("-") dirender sebagai
 * butir, karena urutannya tidak penting (ciri, fasilitas, syarat).
 *
 * @param {string} text - teks jawaban (idealnya sudah lewat rapikanStrukturJawaban)
 * @returns {Array<{type:string, content?:string, level?:number, items?:string[]}>}
 */
export function pisahBlokJawaban(text = '') {
  const lines = rapikanStrukturJawaban(text).split('\n')
  const blocks = []
  let paragraf = []
  let daftarAktif = null

  const tuangParagraf = () => {
    if (paragraf.length === 0) return
    blocks.push({ type: 'paragraph', content: paragraf.join('\n').trim() })
    paragraf = []
  }

  const tuangDaftar = () => {
    if (!daftarAktif) return
    blocks.push(daftarAktif)
    daftarAktif = null
  }

  for (const barisAsli of lines) {
    const baris = barisAsli.trim()

    if (!baris) {
      tuangParagraf()
      tuangDaftar()
      continue
    }

    const judul = baris.match(/^(#{1,3})\s+(.*)$/)
    if (judul) {
      tuangParagraf()
      tuangDaftar()
      blocks.push({ type: 'heading', level: judul[1].length, content: judul[2] })
      continue
    }

    const butir = baris.match(/^[-*]\s+(.*)$/)
    if (butir) {
      tuangParagraf()
      if (!daftarAktif || daftarAktif.type !== 'unordered-list') {
        tuangDaftar()
        daftarAktif = { type: 'unordered-list', items: [] }
      }
      daftarAktif.items.push(butir[1])
      continue
    }

    const nomor = baris.match(/^(\d+)[.)]\s+(.*)$/)
    if (nomor) {
      tuangParagraf()
      if (!daftarAktif || daftarAktif.type !== 'ordered-list') {
        tuangDaftar()
        daftarAktif = { type: 'ordered-list', items: [] }
      }
      daftarAktif.items.push(nomor[2])
      continue
    }

    tuangDaftar()
    paragraf.push(barisAsli)
  }

  tuangParagraf()
  tuangDaftar()

  return blocks
}
