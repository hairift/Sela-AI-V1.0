/* eslint-disable react/prop-types */
/**
 * Panel percakapan SELA.
 *
 * Di layar desktop panel ini mengambang di sisi kanan (seperti pada desain
 * acuan). Di layar potret panel ini menjadi lembaran bawah yang menutupi
 * sebagian avatar, sehingga tetap nyaman dipakai di layar sentuh kios.
 */

import { useEffect, useRef, useState } from 'react'
import ChatBubble from './ChatBubble'
import { t } from '../lib/translations'

const IconSparkle = () => (
  <svg className="w-10 h-10 text-blue-200" fill="none" stroke="currentColor" strokeWidth={1.2} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>
)

const IconSend = () => (
  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2.2} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M22 2L11 13M22 2L15 22l-4-9-9-4 19-7z" />
  </svg>
)

const IconMic = () => (
  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 18v3h2v-3a8.03 8.03 0 005.65-2.35l-1.41-1.41A6 6 0 0112 19a6 6 0 01-4.24-1.76L6.35 18.65A8.03 8.03 0 0011 21z" />
  </svg>
)

const IconChevronRight = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
  </svg>
)

const IconChevronDown = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
  </svg>
)

const IconChat = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
)

export default function ChatPanel({
  pesan = [],
  onKirim,
  onRekam,
  onSesiBaru,
  onTutup,
  terbuka = true,
  stateAvatar = 'idle',
  barisMusik = '',
  terhubung = false,
  musik = null,
  aksi = null,
}) {
  const [nilai, setNilai] = useState('')
  const [fokus, setFokus] = useState(false)
  const [diBawah, setDiBawah] = useState(true)
  const ujungRef = useRef(null)
  const gulirRef = useRef(null)
  const chipRef = useRef(null)

  const cepat = t.id.quickReplies

  useEffect(() => {
    if (diBawah) ujungRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [pesan, diBawah])

  const tanganiGulir = (e) => {
    const el = e.currentTarget
    setDiBawah(el.scrollHeight - el.scrollTop - el.clientHeight < 60)
  }

  const kirim = (e) => {
    if (e?.preventDefault) e.preventDefault()
    const teks = nilai.trim()
    if (!teks) return
    setNilai('')
    setDiBawah(true)
    onKirim?.(teks)
  }

  const kirimCepat = (teks) => {
    setDiBawah(true)
    onKirim?.(teks)
  }

  const geserChip = (arah) => chipRef.current?.scrollBy({ left: arah * 160, behavior: 'smooth' })

  const sedangMendengar = stateAvatar === 'listening'

  return (
    <>
      {/* Tombol buka panel saat tersembunyi */}
      {!terbuka && (
        <button
          type="button"
          onClick={() => onTutup?.(false)}
          className="absolute top-4 right-4 z-30 flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-white/85 dark:bg-slate-900/85 backdrop-blur-xl border border-white/60 dark:border-slate-700/60 shadow-xl hover:shadow-2xl hover:scale-105 active:scale-95 text-xs font-semibold text-gray-800 dark:text-gray-100 transition-all"
          title="Buka bilah chat"
        >
          <span className="p-1.5 rounded-lg bg-blue-500/15 text-blue-600 dark:text-blue-400">
            <IconChat />
          </span>
          <span>{t.id.openChat}</span>
          {pesan.length > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-blue-600 text-white">
              {pesan.length}
            </span>
          )}
        </button>
      )}

      {/* Panel utama */}
      <div
        className={`absolute z-30 flex flex-col justify-between overflow-hidden transition-all duration-300 ease-out
          bg-white/85 dark:bg-slate-900/90 backdrop-blur-2xl border border-white/60 dark:border-slate-700/60 shadow-2xl
          left-3 right-3 bottom-3 top-3 rounded-3xl p-4
          md:left-auto md:right-4 md:top-3 md:bottom-3 md:w-[380px] lg:w-[420px] md:max-w-[420px] md:rounded-3xl
          ${terbuka ? 'translate-y-0 opacity-100 pointer-events-auto' : 'translate-y-[115%] md:translate-y-0 md:translate-x-[115%] opacity-0 pointer-events-none'}`}
      >
        {/* Kepala panel */}
        <div className="flex items-center justify-between pb-2.5 border-b border-gray-200/60 dark:border-slate-700/60 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${terhubung ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
            <span className="text-[11px] sm:text-xs font-bold tracking-wider text-gray-800 dark:text-gray-200 uppercase truncate">
              {t.id.chatPanelTitle}
            </span>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {pesan.length > 0 && (
              <button
                type="button"
                onClick={onSesiBaru}
                className="text-[11px] px-2.5 py-1 rounded-full text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 hover:bg-blue-100 dark:hover:bg-blue-900/60 font-semibold transition-all"
                title="Mulai sesi percakapan baru"
              >
                {t.id.newSession}
              </button>
            )}
            <button
              type="button"
              onClick={() => onTutup?.(true)}
              className="p-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-all"
              title={t.id.hideChat}
            >
              <IconChevronRight />
            </button>
          </div>
        </div>

        {/* Isi */}
        <div className="flex-1 overflow-hidden relative flex flex-col justify-end my-2 min-h-0">
          {pesan.length === 0 ? (
            <div className="flex flex-col items-center justify-center my-auto text-center gap-3 sm:gap-4 py-3 px-2 animate-fade-in">
              <div className="p-3 sm:p-3.5 rounded-2xl bg-blue-50 dark:bg-slate-800/90 text-blue-500 shadow-inner">
                <IconSparkle />
              </div>
              <div>
                <h3 className="text-2xl sm:text-3xl font-light text-gray-800 dark:text-gray-100 tracking-tight italic font-serif">
                  SELA
                </h3>
                <p className="text-[11px] sm:text-xs text-gray-500 dark:text-gray-400 mt-1 font-medium">
                  {t.id.emptyHint}
                </p>
              </div>

              <div className="w-full mt-1">
                <p className="text-[10px] text-gray-400 dark:text-gray-500 mb-2 font-bold uppercase tracking-widest">
                  {t.id.popularQuestions}
                </p>
                <div className="flex flex-col gap-2 w-full">
                  {cepat.map((qr, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => kirimCepat(qr.text)}
                      className="w-full py-2.5 px-3.5 rounded-xl bg-white hover:bg-slate-50 dark:bg-slate-800/90 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-100 hover:text-blue-700 dark:hover:text-blue-300 border border-slate-200/90 dark:border-slate-700/80 hover:border-blue-300 dark:hover:border-blue-500/40 text-xs font-medium shadow-sm hover:shadow active:scale-[0.98] transition-all text-left flex items-center justify-between gap-2 group"
                    >
                      <span className="truncate">{qr.label}</span>
                      <svg className="w-3.5 h-3.5 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 shrink-0 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div
              ref={gulirRef}
              onScroll={tanganiGulir}
              className="flex-1 overflow-y-auto pr-1 flex flex-col gap-1 hide-scrollbar"
            >
              {pesan.map((m) => (
                <ChatBubble
                  key={m.id}
                  role={m.peran}
                  text={m.teks}
                  isNew={false}
                  isSpeaking={stateAvatar === 'speaking' && m.peran === 'assistant' && m.id === pesan[pesan.length - 1]?.id}
                />
              ))}
              {stateAvatar === 'thinking' && (
                <ChatBubble role="assistant" text="" isLoading />
              )}
              <div ref={ujungRef} />
            </div>
          )}

          <PemutarMusik musik={musik} aksi={aksi} />
          {barisMusik && (
            <p className="mt-1 text-[10px] text-gray-400 dark:text-gray-500 truncate shrink-0">{barisMusik}</p>
          )}

          {!diBawah && pesan.length > 0 && (
            <button
              type="button"
              onClick={() => ujungRef.current?.scrollIntoView({ behavior: 'smooth' })}
              className="absolute bottom-2 left-1/2 -translate-x-1/2 z-30 w-8 h-8 rounded-full bg-white/95 dark:bg-slate-800/95 border border-gray-200 dark:border-slate-700 shadow-lg flex items-center justify-center text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-slate-700 active:scale-95 transition-all animate-fade-in"
              title={t.id.scrollDown}
            >
              <IconChevronDown />
            </button>
          )}
        </div>

        {/* Chip topik saat percakapan sudah berjalan */}
        {pesan.length > 0 && (
          <div className="relative flex items-center gap-1 w-full py-1 mb-1 shrink-0">
            <button
              type="button"
              onClick={() => geserChip(-1)}
              className="w-5 h-5 rounded-full bg-white/95 dark:bg-slate-800/95 border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 shadow-sm flex items-center justify-center shrink-0 hover:scale-105 active:scale-95 transition-all z-10"
              aria-label="Sebelumnya"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
            </button>

            <div ref={chipRef} className="flex-1 flex items-center gap-1.5 overflow-x-auto scroll-smooth hide-scrollbar py-0.5">
              {cepat.map((qr, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => kirimCepat(qr.text)}
                  className="whitespace-nowrap text-[11px] font-medium px-3 py-1 rounded-lg bg-blue-50 dark:bg-slate-800 text-blue-600 dark:text-blue-300 border border-blue-200/60 dark:border-slate-700 hover:bg-blue-100 dark:hover:bg-slate-700 transition-all flex-shrink-0 active:scale-95"
                >
                  {qr.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => geserChip(1)}
              className="w-5 h-5 rounded-full bg-white/95 dark:bg-slate-800/95 border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 shadow-sm flex items-center justify-center shrink-0 hover:scale-105 active:scale-95 transition-all z-10"
              aria-label="Berikutnya"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        )}

        {/* Kolom input */}
        <form onSubmit={kirim} className="relative w-full pt-1 shrink-0">
          <input
            id="kolom-pesan"
            type="text"
            value={nilai}
            onChange={(e) => setNilai(e.target.value)}
            onFocus={() => setFokus(true)}
            onBlur={() => setFokus(false)}
            placeholder={sedangMendengar ? t.id.listeningPlaceholder : t.id.typeMessage}
            className={`w-full bg-white/95 dark:bg-slate-800/95 backdrop-blur-md border rounded-2xl pl-3.5 pr-11 py-2.5
              text-gray-800 dark:text-gray-100 text-xs placeholder-gray-400 outline-none shadow-sm transition-all duration-200
              ${sedangMendengar
                ? 'border-red-400 ring-4 ring-red-400/30 animate-pulse'
                : fokus
                  ? 'border-blue-500 ring-2 ring-blue-200 dark:ring-blue-900'
                  : 'border-gray-200 dark:border-slate-700'}`}
          />
          <button
            id="tombol-kirim"
            type={nilai.trim() ? 'submit' : 'button'}
            onClick={nilai.trim() ? undefined : onRekam}
            className={`absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 rounded-xl flex items-center justify-center shadow-md transition-all active:scale-95 ${
              nilai.trim()
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : sedangMendengar
                  ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse ring-2 ring-red-400'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
            title={nilai.trim() ? t.id.sendText : sedangMendengar ? t.id.listeningClickToSend : t.id.speakViaMic}
          >
            {nilai.trim() ? (
              <IconSend />
            ) : sedangMendengar ? (
              <svg className="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="1" />
              </svg>
            ) : (
              <IconMic />
            )}
          </button>
        </form>
      </div>
    </>
  )
}
