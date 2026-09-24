/* eslint-disable react/prop-types */
/**
 * Tombol suara utama dan indikator status.
 *
 * Diposisikan tepat di tengah bawah panggung, sama seperti desain acuan.
 * Di layar potret tombol dikecilkan dan dinaikkan agar tidak menutupi panel.
 */

import { t } from '../lib/translations'

const IconMic = () => (
  <svg className="w-8 h-8 sm:w-10 sm:h-10 text-white" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 1a4 4 0 014 4v6a4 4 0 01-8 0V5a4 4 0 014-4zm-1 18v3h2v-3a8.03 8.03 0 005.65-2.35l-1.41-1.41A6 6 0 0112 19a6 6 0 01-4.24-1.76L6.35 18.65A8.03 8.03 0 0011 21z" />
  </svg>
)

const IconStop = () => (
  <svg className="w-7 h-7 sm:w-8 sm:h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
  </svg>
)

const IconSpinner = () => (
  <svg className="w-7 h-7 sm:w-8 sm:h-8 text-white animate-spin" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
  </svg>
)

export default function VoiceControls({
  stateAvatar = 'idle',
  onRekam,
  terhubung = false,
  aiTerhubung = false,
  terbuka = true,
}) {
  const label = () => {
    if (!terhubung) return t.id.appOffline
    if (!aiTerhubung) return t.id.connectingEngine
    if (stateAvatar === 'listening') return t.id.listeningHint
    if (stateAvatar === 'speaking') return t.id.speakingHint
    if (stateAvatar === 'thinking') return t.id.processingHint
    return t.id.clickToSpeak
  }

  const status = () => {
    if (!terhubung) return t.id.appOffline
    if (!aiTerhubung) return t.id.connectingEngine
    if (stateAvatar === 'listening') return t.id.listening
    if (stateAvatar === 'speaking') return t.id.speaking
    if (stateAvatar === 'thinking') return t.id.thinking
    return t.id.readyToListen
  }

  const kelasTombol =
    stateAvatar === 'listening'
      ? 'bg-red-500 shadow-red-500/50 animate-pulse ring-8 ring-red-400/30 text-white'
      : stateAvatar === 'speaking'
        ? 'bg-amber-500 shadow-amber-500/50 animate-pulse ring-8 ring-amber-400/30 text-white'
        : stateAvatar === 'thinking'
          ? 'bg-indigo-600 shadow-indigo-500/50 ring-4 ring-indigo-300/30 text-white'
          : !terhubung || !aiTerhubung
            ? 'bg-slate-400 shadow-slate-500/30 ring-4 ring-slate-300/40 text-white cursor-not-allowed'
            : 'bg-blue-600 shadow-xl shadow-blue-600/30 hover:bg-blue-700 hover:scale-105 ring-4 ring-blue-200/60 dark:ring-blue-900/40 text-white'

  return (
    <div
      className={`absolute left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-1.5 sm:gap-2 pointer-events-auto max-w-[88vw] transition-all duration-300
        ${terbuka ? 'bottom-6' : 'bottom-8 sm:bottom-6'}`}
    >
      <button
        id="tombol-suara"
        type="button"
        onClick={onRekam}
        disabled={!terhubung}
        className={`relative w-16 h-16 sm:w-20 sm:h-20 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 transform active:scale-95 ${kelasTombol}`}
        title={
          stateAvatar === 'listening'
            ? t.id.stopAndSend
            : stateAvatar === 'speaking'
              ? t.id.interrupt
              : t.id.startListening
        }
      >
        {stateAvatar === 'speaking' ? <IconStop /> : stateAvatar === 'thinking' ? <IconSpinner /> : <IconMic />}
      </button>

      <p className="text-[11px] sm:text-xs font-semibold tracking-wide text-gray-700 dark:text-gray-200 text-center px-2">
        {label()}
      </p>

      <p className="text-[10px] sm:text-xs text-gray-400 dark:text-gray-500 font-bold uppercase tracking-tighter text-center">
        {status()}
      </p>
    </div>
  )
}
