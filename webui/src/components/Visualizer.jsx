/* eslint-disable react/prop-types */
/**
 * Visualizer audio di dalam gelembung jawaban SELA.
 *
 * Tinggi batang diambil dari level suara yang BENAR-BENAR keluar dari pengeras
 * suara: mesin AI (Python) menghitung RMS PCM keluaran lalu mengirimnya lewat
 * WebSocket pada paket "lip". Jadi animasi ini bukan hiasan acak - ia mengikuti
 * suara SELA saat itu, sama seperti gerak mulut avatar 3D.
 */

const BOBOT = [0.42, 0.7, 0.9, 1, 0.9, 0.7, 0.42]
const TINGGI_MIN = 3
const TINGGI_MAKS = 17

export default function Visualizer({ volume = 0, label = '' }) {
  const v = Math.max(0, Math.min(1, Number(volume) || 0))

  return (
    <span
      data-visualizer="1"
      className="flex items-center gap-2 h-6 select-none"
      role="status"
      aria-label={label}
    >
      <span className="flex items-end gap-[3px] h-5" aria-hidden="true">
        {BOBOT.map((bobot, i) => (
          <span
            key={i}
            className="w-[3px] rounded-full bg-blue-500/85 dark:bg-blue-400/85 transition-[height] duration-75 ease-out"
            style={{ height: `${TINGGI_MIN + v * (TINGGI_MAKS - TINGGI_MIN) * bobot}px` }}
          />
        ))}
      </span>
      {label && (
        <span className="text-[10px] font-medium text-gray-400 dark:text-gray-500">
          {label}
        </span>
      )}
    </span>
  )
}
