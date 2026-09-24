/* eslint-disable react/prop-types */
/**
 * Menu samping: riwayat sesi, pengaturan, bantuan.
 * Lebarnya menyesuaikan layar potret agar tidak menutupi seluruh panggung.
 */

import { useEffect, useRef, useState } from 'react'
import { t } from '../lib/translations'

const IconClock = () => (
  <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="10" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2" />
  </svg>
)

const IconSearch = () => (
  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
    <circle cx="11" cy="11" r="8" />
    <path strokeLinecap="round" d="M21 21l-4.35-4.35" />
  </svg>
)

const IconPlus = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" d="M12 5v14M5 12h14" />
  </svg>
)

const IconX = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
)

const IconSettings = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.559.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.894.149c-.424.07-.764.383-.929.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.398.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.272-.806.108-1.204-.165-.397-.506-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.108-1.204l-.526-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
)

const IconHelp = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="10" />
    <path strokeLinecap="round" d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01" />
  </svg>
)

const IconMessage = () => (
  <svg className="w-10 h-10 text-gray-200 dark:text-slate-700" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
)

export default function HamburgerMenu({
  isOpen,
  onClose,
  sesi = [],
  sesiAktif = null,
  onSesiBaru,
  onPilihSesi,
  onHapusSesi,
  onOpenSettings,
  onOpenHelp,
}) {
  const [cari, setCari] = useState('')
  const [hover, setHover] = useState(null)
  const cariRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  useEffect(() => {
    if (isOpen) setTimeout(() => cariRef.current?.focus(), 300)
  }, [isOpen])

  const tersaring = sesi.filter((s) => s.judul.toLowerCase().includes(cari.toLowerCase()))

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-gray-900/20 dark:bg-black/50 backdrop-blur-[2px] transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      />

      <aside
        id="menu-samping"
        className={`fixed top-0 left-0 h-full w-[82vw] max-w-[300px] z-50 flex flex-col
          bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border-r border-gray-100 dark:border-white/10 shadow-2xl
          transition-transform duration-300 ease-out ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="flex items-center justify-between px-5 pt-6 pb-4">
          <div>
            <span className="text-xl font-bold tracking-[0.3em] text-gray-800 dark:text-gray-100 select-none block">SELA</span>
            <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium">{t.id.appTagline}</span>
          </div>
          <button
            onClick={onClose}
            aria-label="Tutup menu"
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <IconX />
          </button>
        </div>

        <div className="px-4 mb-4">
          <button
            id="tombol-sesi-baru"
            onClick={onSesiBaru}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 text-white text-sm font-semibold shadow-md shadow-blue-300/40 hover:from-blue-600 hover:to-blue-700 active:scale-95 transition-all duration-200"
          >
            <IconPlus />
            {t.id.newChat}
          </button>
        </div>

        <div className="px-4 mb-3">
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
              <IconSearch />
            </span>
            <input
              ref={cariRef}
              type="text"
              placeholder={t.id.searchConversations}
              value={cari}
              onChange={(e) => setCari(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 dark:bg-slate-800/50 border border-gray-200/80 dark:border-gray-700 rounded-xl outline-none placeholder-gray-400 text-gray-600 dark:text-gray-300 focus:ring-2 focus:ring-blue-200 focus:border-blue-300 transition-all"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-2">
          {sesi.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-10 text-center">
              <IconMessage />
              <p className="mt-3 text-sm text-gray-400 font-medium">{t.id.noConversations}</p>
              <p className="text-xs text-gray-300 dark:text-slate-600 mt-1">{t.id.startNewChat}</p>
            </div>
          ) : (
            <>
              <p className="px-2 mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500">
                {t.id.recentChats}
              </p>
              <nav className="flex flex-col gap-0.5">
                {tersaring.map((s) => (
                  <div
                    key={s.id}
                    className="relative group"
                    onMouseEnter={() => setHover(s.id)}
                    onMouseLeave={() => setHover(null)}
                  >
                    <button
                      onClick={() => onPilihSesi?.(s.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-all duration-150 pr-10 ${
                        sesiAktif === s.id
                          ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium'
                          : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800/50 hover:text-gray-800 dark:hover:text-gray-100'
                      }`}
                    >
                      <span className={sesiAktif === s.id ? 'text-blue-500' : 'text-gray-400 dark:text-gray-500'}>
                        <IconClock />
                      </span>
                      <span className="truncate">{s.judul}</span>
                    </button>

                    {hover === s.id && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onHapusSesi?.(s.id)
                        }}
                        aria-label="Hapus sesi"
                        className="absolute right-2 top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center rounded-lg text-gray-300 hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      >
                        <IconX />
                      </button>
                    )}
                  </div>
                ))}

                {tersaring.length === 0 && cari && (
                  <div className="px-4 py-6 text-center">
                    <p className="text-sm text-gray-400">
                      {t.id.noResults} &ldquo;{cari}&rdquo;
                    </p>
                  </div>
                )}
              </nav>
            </>
          )}
        </div>

        <div className="border-t border-gray-100 dark:border-white/10 px-3 pt-3 pb-4">
          <button
            onClick={onOpenSettings}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-xl text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800 hover:text-gray-700 dark:hover:text-gray-200 transition-all"
          >
            <IconSettings />
            {t.id.settings}
          </button>
          <button
            onClick={onOpenHelp}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-xl text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800 hover:text-gray-700 dark:hover:text-gray-200 transition-all"
          >
            <IconHelp />
            {t.id.help}
          </button>
        </div>
      </aside>
    </>
  )
}
