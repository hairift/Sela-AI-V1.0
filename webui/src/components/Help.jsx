/* eslint-disable react/prop-types */
/**
 * Halaman Bantuan: panduan singkat penggunaan SELA.
 */

import { t } from '../lib/translations'

const IconChevronLeft = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
  </svg>
)

function Bagian({ judul, isi }) {
  return (
    <section className="rounded-2xl border border-gray-200/80 dark:border-slate-700/70 bg-white/80 dark:bg-slate-900/70 backdrop-blur-xl shadow-sm p-5">
      <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-1.5">{judul}</h3>
      <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">{isi}</p>
    </section>
  )
}

export default function Help({ onBack }) {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="sticky top-0 z-10 flex items-center gap-3 px-5 py-4 bg-[#f8faff]/90 dark:bg-slate-950/90 backdrop-blur-xl border-b border-gray-100 dark:border-slate-800">
        <button
          onClick={onBack}
          className="w-9 h-9 flex items-center justify-center rounded-xl hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300 transition-colors"
          aria-label={t.id.back}
        >
          <IconChevronLeft />
        </button>
        <div>
          <h1 className="text-base font-bold text-gray-800 dark:text-gray-100">{t.id.helpTitle}</h1>
          <p className="text-[11px] text-gray-400 dark:text-gray-500">{t.id.helpSubtitle}</p>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-5 space-y-3">
        <Bagian judul={t.id.helpVoiceTitle} isi={t.id.helpVoiceBody} />
        <Bagian judul={t.id.helpTextTitle} isi={t.id.helpTextBody} />
        <Bagian judul={t.id.helpTopicsTitle} isi={t.id.helpTopicsBody} />
        <Bagian judul={t.id.helpInterruptTitle} isi={t.id.helpInterruptBody} />

        <section className="rounded-2xl border border-gray-200/80 dark:border-slate-700/70 bg-white/80 dark:bg-slate-900/70 backdrop-blur-xl shadow-sm p-5">
          <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-2">
            {t.id.helpShortcuts}
          </h3>
          <ul className="space-y-1.5 text-xs text-gray-500 dark:text-gray-400">
            <li className="flex justify-between gap-4">
              <span>{t.id.shortcutMic}</span>
              <span className="font-mono text-gray-400 dark:text-gray-500">Mic</span>
            </li>
            <li className="flex justify-between gap-4">
              <span>{t.id.shortcutSend}</span>
              <span className="font-mono text-gray-400 dark:text-gray-500">Enter</span>
            </li>
            <li className="flex justify-between gap-4">
              <span>{t.id.shortcutEsc}</span>
              <span className="font-mono text-gray-400 dark:text-gray-500">Esc</span>
            </li>
          </ul>
        </section>

        <Bagian judul={t.id.helpTroubleTitle} isi={t.id.helpTroubleBody} />
      </div>
    </div>
  )
}
