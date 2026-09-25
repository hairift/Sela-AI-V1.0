/* eslint-disable react/prop-types */
/**
 * Gelembung percakapan SELA.
 *
 * Aturan tampil yang dipegang berkas ini:
 *   1. SATU gelembung per jawaban. Potongan jawaban dari mesin AI digabung di
 *      hook useSelaBridge; di sini tinggal menampilkan.
 *   2. Selagi SELA berbicara, gelembung menampilkan **visualizer audio** (dari
 *      level suara nyata), bukan teks yang setengah jadi.
 *   3. Setelah suara selesai, teks muncul dengan **efek mengetik**.
 *   4. Markdown dirender rapi: tebal, miring, kode, paragraf, dan daftar -
 *      tanpa karakter mentah seperti `**` yang ikut terlihat.
 *   5. Bila jawaban menyebut alamat kampus, kartu **peta** muncul di bawahnya.
 *   6. Di bawah jawaban ada satu baris **tanya lanjut** yang mengikuti topik.
 */

import { memo, useEffect, useRef, useState } from 'react'
import QRCode from 'qrcode'
import Visualizer from './Visualizer'
import PetaKampus from './PetaKampus'
import { tr } from '../lib/translations'
import { buangPenandaSisa } from '../lib/teks'

const URL_PATTERN = /(https?:\/\/[^\s]+)/g
const TRAILING_PUNCTUATION = /[.,!?;:)\]]$/
const SELA_ALIASES = new Set(['cela', 'sela', 'zela', 'selah', 'sella', 'selak'])
const BOLD_GLOBAL = /(\*\*[^*]+\*\*|__[^_]+__)/g
// Miring: satu bintang mengapit teks (*miring*). Dipisah dari tebal (**tebal**)
// supaya keduanya bisa dipakai bersamaan tanpa saling merusak.
const ITALIC_PATTERN = /(\*[^*\n]+\*)/
const CODE_PATTERN = /(`[^`\n]+`)/
const PROTECTED_TOKEN_PREFIX = '__SELA_PROTECTED_'
const FOLLOW_UP_PATTERN = /(?:^|\s)((?:\[[^\]\n]*\?]\s*(?:\|\s*)?){1,2})\s*$/

// Jawaban dianggap membahas lokasi kampus bila memuat salah satu penanda ini.
const PENANDA_LOKASI =
  /(kesambi|alamat kampus|lokasi kampus|peta lokasi|openstreetmap\.org|google\.com\/maps|map=1[0-9]\/)/i

function isSelaAlias(word) {
  return SELA_ALIASES.has(word.toLowerCase())
}

function normalizeSelaAliases(text = '') {
  return text.replace(/[A-Za-z]+/g, word => (
    isSelaAlias(word) ? 'Sela' : word
  ))
}

function splitTextByLinks(text = '') {
  const parts = []
  let lastIndex = 0

  for (const match of text.matchAll(URL_PATTERN)) {
    const rawUrl = match[0]
    const start = match.index
    let url = rawUrl
    let trailing = ''

    while (TRAILING_PUNCTUATION.test(url)) {
      trailing = url.slice(-1) + trailing
      url = url.slice(0, -1)
    }

    if (start > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, start) })
    }

    if (url) {
      parts.push({ type: 'link', value: url })
    }

    if (trailing) {
      parts.push({ type: 'text', value: trailing })
    }

    lastIndex = start + rawUrl.length
  }

  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) })
  }

  return parts
}

function withProtectedLinks(text = '', formatter) {
  const links = []
  const protectedText = String(text || '').replace(URL_PATTERN, (url) => {
    const token = `${PROTECTED_TOKEN_PREFIX}${links.length}__`
    links.push(url)
    return token
  })

  const formatted = formatter(protectedText)
  return formatted.replace(
    new RegExp(`${PROTECTED_TOKEN_PREFIX}(\\d+)__`, 'g'),
    (_, index) => links[Number(index)] || ''
  )
}

function normalizeMarkdownStructure(text = '') {
  return withProtectedLinks(text, (value) => {
    let normalized = value
      .replace(/\r/g, '')
      .replace(/[ \t]+/g, ' ')
      .replace(/[ \t]+\n/g, '\n')
      .replace(/\n[ \t]+/g, '\n')
      // Penanda tebal gaya lain diubah ke bentuk yang dikenali perender.
      .replace(/__([^_\n]+)__/g, '**$1**')

    // Poin daftar dari model sering memakai karakter lain. Diseragamkan agar
    // benar-benar dirender sebagai daftar, bukan kalimat berhamburan.
    normalized = normalized
      .replace(/^[\s]*[•·▪◦‣–—]\s+/gm, '- ')
      .replace(/^([\s]*)([1-9]\d?)\)\s+/gm, '$1$2. ')

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

    // Label bagian yang sering muncul dari dataset dibuat sebagai baris sendiri
    // agar "Program S1:" tidak menempel dengan paragraf sebelumnya.
    normalized = normalized.replace(
      /([.!?])\s+((?:Program|Fakultas|Syarat|Langkah|Biaya|Fasilitas|Beasiswa|Kontak|Lokasi)\b[^:\n]{0,60}:)/gi,
      '$1\n\n$2'
    )

    return normalized
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  })
}

function splitFollowUpSuggestions(text = '') {
  const value = String(text || '').trim()
  const match = value.match(FOLLOW_UP_PATTERN)
  if (!match) return { answerText: value, suggestions: [] }

  const rawSuggestions = match[1]
  const suggestions = [...rawSuggestions.matchAll(/\[([^\]\n]*\?)]/g)]
    .map((item) => item[1].trim())
    .filter(Boolean)

  if (suggestions.length === 0) return { answerText: value, suggestions: [] }

  return {
    answerText: value.slice(0, match.index).trim(),
    suggestions
  }
}

/**
 * Pecah teks menjadi blok: judul, daftar berpoin, daftar bernomor, paragraf.
 *
 * Aturan daftar: teks yang sudah bernomor ("1.", "2.") tetap bernomor karena
 * urutannya penting (langkah, tahapan). Teks berpoin ("-") dirender sebagai
 * butir, karena urutannya tidak penting (ciri, fasilitas, syarat).
 */
function splitMarkdownBlocks(text = '') {
  const lines = normalizeMarkdownStructure(text).split('\n')
  const blocks = []
  let paragraphLines = []
  let activeList = null

  const flushParagraph = () => {
    if (paragraphLines.length === 0) return
    blocks.push({
      type: 'paragraph',
      content: paragraphLines.join('\n').trim()
    })
    paragraphLines = []
  }

  const flushList = () => {
    if (!activeList) return
    blocks.push(activeList)
    activeList = null
  }

  lines.forEach((line) => {
    const trimmed = line.trim()

    if (!trimmed) {
      flushParagraph()
      flushList()
      return
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)$/)
    if (headingMatch) {
      flushParagraph()
      flushList()
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        content: headingMatch[2]
      })
      return
    }

    const unorderedMatch = trimmed.match(/^[-*]\s+(.*)$/)
    if (unorderedMatch) {
      flushParagraph()
      if (!activeList || activeList.type !== 'unordered-list') {
        flushList()
        activeList = { type: 'unordered-list', items: [] }
      }
      activeList.items.push(unorderedMatch[1])
      return
    }

    const orderedMatch = trimmed.match(/^(\d+)[.)]\s+(.*)$/)
    if (orderedMatch) {
      flushParagraph()
      if (!activeList || activeList.type !== 'ordered-list') {
        flushList()
        activeList = { type: 'ordered-list', items: [] }
      }
      activeList.items.push(orderedMatch[2])
      return
    }

    flushList()
    paragraphLines.push(line)
  })

  flushParagraph()
  flushList()

  return blocks
}

/** Render teks kaya: tautan, tebal, miring, dan kode. */
function renderInlineMarkdown(text = '', keyPrefix = 'inline') {
  const normalized = normalizeSelaAliases(text)
  const parts = splitTextByLinks(normalized)

  return parts.flatMap((part, partIndex) => {
    if (part.type === 'link') {
      return (
        <a
          key={`${keyPrefix}-link-${partIndex}`}
          href={part.value}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 dark:text-blue-400 hover:underline font-medium break-all"
        >
          {part.value}
        </a>
      )
    }

    return part.value
      .split(BOLD_GLOBAL)
      .filter(Boolean)
      .flatMap((segment, segmentIndex) => {
        const boldMatch = segment.match(/^(?:\*\*|__)([\s\S]*?)(?:\*\*|__)$/)
        if (boldMatch) {
          return (
            <strong key={`${keyPrefix}-bold-${partIndex}-${segmentIndex}`} className="font-semibold text-gray-800 dark:text-white">
              {renderKodeDanMiring(boldMatch[1], `${keyPrefix}-b-${partIndex}-${segmentIndex}`)}
            </strong>
          )
        }

        return renderKodeDanMiring(segment, `${keyPrefix}-s-${partIndex}-${segmentIndex}`)
      })
  })
}

/** Render kode sebaris dan teks miring di dalam sebuah potongan teks. */
function renderKodeDanMiring(teks, keyPrefix) {
  return String(teks)
    .split(CODE_PATTERN)
    .filter(Boolean)
    .flatMap((potonganKode, i) => {
      const kodeMatch = potonganKode.match(/^`([^`\n]+)`$/)
      if (kodeMatch) {
        return (
          <code
            key={`${keyPrefix}-code-${i}`}
            className="px-1 py-0.5 rounded bg-gray-100 dark:bg-slate-700/70 text-[0.85em] font-mono text-gray-800 dark:text-gray-100"
          >
            {kodeMatch[1]}
          </code>
        )
      }

      return potonganKode
        .split(ITALIC_PATTERN)
        .filter(Boolean)
        .map((potongan, j) => {
          const italicMatch = potongan.match(/^\*([^*\n]+)\*$/)
          if (italicMatch) {
            return (
              <em key={`${keyPrefix}-italic-${i}-${j}`} className="italic">
                {buangPenandaSisa(italicMatch[1])}
              </em>
            )
          }

          return (
            <span key={`${keyPrefix}-text-${i}-${j}`}>
              {buangPenandaSisa(potongan)}
            </span>
          )
        })
    })
}

function QrLinkCard({ url, visibleMs = null }) {
  const [qrSrc, setQrSrc] = useState('')
  const [isVisible, setIsVisible] = useState(true)

  useEffect(() => {
    let active = true

    QRCode.toDataURL(url, {
      width: 132,
      margin: 1,
      color: {
        dark: '#111827',
        light: '#ffffff'
      }
    }).then(src => {
      if (active) setQrSrc(src)
    }).catch(() => {
      if (active) setQrSrc('')
    })

    return () => {
      active = false
    }
  }, [url])

  useEffect(() => {
    setIsVisible(true)

    if (!visibleMs) return undefined

    const timeout = setTimeout(() => {
      setIsVisible(false)
    }, visibleMs)

    return () => clearTimeout(timeout)
  }, [url, visibleMs])

  if (!isVisible) return null

  return (
    <span className="my-2 flex w-fit max-w-full flex-col items-center gap-1 rounded-xl border border-gray-200/80 bg-white p-2 shadow-sm dark:border-white/10 dark:bg-slate-900/80">
      {qrSrc ? (
        <img
          src={qrSrc}
          alt="QR code untuk link"
          className="h-28 w-28 rounded-md"
          loading="lazy"
        />
      ) : (
        <span className="flex h-28 w-28 items-center justify-center rounded-md bg-gray-100 text-[10px] font-medium text-gray-400 dark:bg-slate-800 dark:text-gray-500">
          QR
        </span>
      )}
      <span className="text-[10px] font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400">
        Scan QR
      </span>
    </span>
  )
}

function ChatContent({ text, qrVisibleMs = null, tampilkanPeta = false }) {
  const { answerText, suggestions } = splitFollowUpSuggestions(text)
  const blocks = splitMarkdownBlocks(answerText)

  // Ekstrak tautan pertama yang valid untuk kartu QR tunggal (mencegah QR ganda)
  const matches = answerText.match(URL_PATTERN)
  let primaryQrUrl = null
  if (matches && matches.length > 0) {
    let raw = matches[0]
    while (TRAILING_PUNCTUATION.test(raw)) {
      raw = raw.slice(0, -1)
    }
    primaryQrUrl = raw
  }

  const perluPeta = tampilkanPeta && PENANDA_LOKASI.test(answerText)

  return (
    <ChatSuggestionLayout suggestions={suggestions}>
      <div className="space-y-3 break-words">
        {blocks.length === 0 ? (
          <span className="whitespace-pre-wrap break-words">
            {renderInlineMarkdown(answerText, 'fallback')}
          </span>
        ) : (
          blocks.map((block, blockIndex) => {
            if (block.type === 'heading') {
              const headingClass =
                block.level === 1
                  ? 'text-base font-semibold text-gray-900 dark:text-white'
                  : 'text-sm font-semibold text-gray-800 dark:text-gray-100'

              return (
                <p key={`heading-${blockIndex}`} className={headingClass}>
                  {renderInlineMarkdown(block.content, `heading-${blockIndex}`)}
                </p>
              )
            }

            if (block.type === 'ordered-list' || block.type === 'unordered-list') {
              const Daftar = block.type === 'ordered-list' ? 'ol' : 'ul'
              const gayaPenanda = block.type === 'ordered-list' ? 'list-decimal' : 'list-disc'

              return (
                <Daftar
                  key={`list-${blockIndex}`}
                  className={`${gayaPenanda} space-y-1.5 pl-5 leading-relaxed marker:text-gray-400 dark:marker:text-gray-500`}
                >
                  {block.items.map((item, itemIndex) => (
                    <li key={`list-${blockIndex}-${itemIndex}`} className="break-words pl-0.5">
                      {renderInlineMarkdown(item, `list-${blockIndex}-${itemIndex}`)}
                    </li>
                  ))}
                </Daftar>
              )
            }

            return (
              <p key={`p-${blockIndex}`} className="whitespace-pre-wrap break-words leading-relaxed">
                {renderInlineMarkdown(block.content, `p-${blockIndex}`)}
              </p>
            )
          })
        )}

        {/* Kartu peta untuk jawaban yang membahas lokasi kampus */}
        {perluPeta && <PetaKampus text={answerText} />}

        {/* Kartu QR tunggal yang rapi untuk pesan ini */}
        {primaryQrUrl && (
          <div className="pt-2 flex justify-start">
            <QrLinkCard url={primaryQrUrl} visibleMs={qrVisibleMs} />
          </div>
        )}
      </div>
    </ChatSuggestionLayout>
  )
}

function ChatSuggestionLayout({ children, suggestions = [] }) {
  return (
    <div className="space-y-2 break-words">
      {children}
      {suggestions.length > 0 && (
        <div className="border-t border-gray-100 pt-2 text-xs leading-snug text-gray-500 dark:border-white/10 dark:text-gray-400">
          <div className="space-y-1">
            {suggestions.map((suggestion, index) => (
              <p key={`suggestion-${index}`}>{suggestion}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/** Baris tanya lanjut di bawah jawaban; mengetuk salah satunya langsung kirim. */
function BarisSaran({ saran = [], onSaran }) {
  if (!saran.length) return null
  return (
    <div data-saran="1" className="mt-1.5 w-full">
      <p className="text-[9px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-1">
        {tr('followUp')}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {saran.map((s) => (
          <button
            key={s.text}
            type="button"
            onClick={() => onSaran?.(s.text)}
            className="text-[11px] font-medium px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-200 border border-gray-200/90 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-500/50 hover:text-blue-700 dark:hover:text-blue-300 hover:shadow-sm active:scale-95 transition-all"
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  )
}

/** Avatar bulat dari berkas di webui/public (user.png / sela.png). */
function Avatar({ isUser }) {
  return (
    <img
      src={isUser ? '/user.png' : '/sela.png'}
      alt={isUser ? tr('you') : tr('sela')}
      className="w-8 h-8 rounded-full object-cover shrink-0 border border-white/70 dark:border-slate-700 shadow-sm bg-white"
      // Tanpa loading="lazy": avatar selalu kecil dan berkasnya hanya dua,
      // jadi menundanya justru membuat avatar gelembung lama tidak ter-decode.
      decoding="async"
      draggable={false}
    />
  )
}

function ChatBubble({
  role,
  text,
  gambar = null,
  isLoading = false,
  mengetik = false,
  isSpeaking = false,
  qrVisibleMs = null,
  volume = 0,
  saran = [],
  onSaran,
  onTumbuh,
}) {
  const isUser = role === 'user'
  const [jumlah, setJumlah] = useState(mengetik ? 0 : String(text || '').length)
  const jumlahRef = useRef(mengetik ? 0 : String(text || '').length)
  const [selesai, setSelesai] = useState(!mengetik)
  const tahanRef = useRef(null)

  // Apakah SELA sedang mengeluarkan suara. Selain status "speaking" dari mesin
  // AI, level suara nyata (data lipsync) juga dipakai: status bisa tertinggal
  // sesaat, sedangkan suara tidak bisa dibohongi.
  const bersuara = Boolean(isSpeaking) || Number(volume) > 0.02

  // Efek mengetik: dimulai setelah SELA selesai berbicara, lalu berjalan
  // bertahap. Bila potongan teks baru menyusul, pengetikan melanjutkan dari
  // posisi terakhir sehingga teks tidak berkedip ulang dari awal.
  useEffect(() => {
    const penuh = String(text || '').length
    clearTimeout(tahanRef.current)

    if (!mengetik) {
      jumlahRef.current = penuh
      setJumlah(penuh)
      setSelesai(true)
      return undefined
    }

    // Masih ada suara: tahan teks, visualizer yang tampil. Bila masih ada
    // teks baru yang belum ditampilkan, tandai belum selesai agar baris tanya
    // lanjut tidak muncul selagi SELA berbicara.
    if (bersuara) {
      if (jumlahRef.current < penuh) setSelesai(false)
      tahanRef.current = setTimeout(() => {
        jumlahRef.current = penuh
        setJumlah(penuh)
        setSelesai(true)
      }, 45000)
      return () => clearTimeout(tahanRef.current)
    }

    if (jumlahRef.current >= penuh) {
      setJumlah(penuh)
      setSelesai(true)
      return undefined
    }

    let i = jumlahRef.current
    const langkah = Math.max(1, Math.ceil(penuh / 70))
    const id = setInterval(() => {
      i += langkah
      if (i >= penuh) {
        i = penuh
        clearInterval(id)
        setSelesai(true)
      }
      jumlahRef.current = i
      setJumlah(i)
      onTumbuh?.()
    }, 16)

    return () => clearInterval(id)
  }, [text, mengetik, bersuara, onTumbuh])

  const tampilkanVisualizer = !isUser && bersuara
  const terlihat = String(text || '').slice(0, jumlah)

  return (
    <div
      data-peran={isUser ? 'user' : 'assistant'}
      data-muat={isLoading ? '1' : '0'}
      data-selesai={selesai ? '1' : '0'}
      data-bicara={tampilkanVisualizer ? '1' : '0'}
      className={`animate-fade-in flex gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-3`}
    >
      <Avatar isUser={isUser} />

      <div className={`flex flex-col min-w-0 ${isUser ? 'items-end' : 'items-start'}`}>
        <span className={`text-[10px] font-semibold uppercase tracking-widest mb-1 ${isUser ? 'text-blue-400' : 'text-gray-400'}`}>
          {isUser ? tr('you') : tr('sela')}
        </span>

        <div
          className={`max-w-[min(340px,78vw)] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm transition-colors
            ${isUser
              ? 'bg-blue-50/90 dark:bg-blue-900/40 text-gray-700 dark:text-blue-100 rounded-tr-sm border border-blue-100/60 dark:border-blue-800/50'
              : 'bg-white/90 dark:bg-slate-800/90 text-gray-600 dark:text-gray-200 rounded-tl-sm border border-gray-100/80 dark:border-white/5'
            }`}
        >
          {gambar && (
            <img
              src={gambar}
              alt={tr('photoFromCamera')}
              className="mb-2 w-44 rounded-xl border border-black/5 dark:border-white/10 shadow-sm"
              loading="lazy"
            />
          )}

          {isLoading ? (
            // Animasi 3 titik bergerak (thinking/loading indicator)
            <span className="flex gap-1.5 items-center h-4 px-1">
              <span className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-500 animate-bounce [animation-delay:-0.3s]" />
              <span className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-500 animate-bounce [animation-delay:-0.15s]" />
              <span className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-500 animate-bounce" />
            </span>
          ) : tampilkanVisualizer ? (
            <Visualizer volume={volume} label={tr('selaSpeaking')} />
          ) : (
            <>
              <ChatContent text={terlihat} qrVisibleMs={qrVisibleMs} tampilkanPeta={!isUser} />
              {!selesai && (
                <span className="inline-block w-[2px] h-3.5 align-middle ml-0.5 bg-blue-500/70 dark:bg-blue-400/70 animate-pulse" />
              )}
            </>
          )}
        </div>

        {/* Baris tanya lanjut hanya untuk jawaban SELA yang sudah selesai
            ditampilkan. Selagi visualizer berjalan teksnya sendiri belum
            tampil, jadi baris ini pun belum perlu muncul. */}
        {!isUser && !isLoading && selesai && String(text || '').trim().length > 0 && (
          <BarisSaran saran={saran} onSaran={onSaran} />
        )}
      </div>
    </div>
  )
}

export default memo(ChatBubble)
