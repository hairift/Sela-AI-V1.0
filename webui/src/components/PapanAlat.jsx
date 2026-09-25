/* eslint-disable react/prop-types */
/**
 * Papan langkah alat (MCP) di dalam alur percakapan.
 *
 * Saat mesin AI memanggil sebuah alat - misalnya membuka data kampus UCIC,
 * mengambil data cuaca, atau menelusuri internet - antarmuka menampilkan
 * langkah itu sebagai kartu kecil yang bergerak. Pengguna jadi melihat SELA
 * benar-benar mengerjakan sesuatu, bukan diam menunggu.
 *
 * Ini murni tampilan: pemanggilan alatnya tetap dikerjakan py-xiaozhi lewat
 * pesan MCP yang sama seperti sebelumnya.
 */

const IconAlat = () => (
  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M11.42 15.17L17.25 21A2.65 2.65 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z"
    />
  </svg>
)

const IconCentang = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
)

export default function PapanAlat({ langkah = [], label = 'Sedang bekerja' }) {
  if (!langkah.length) return null
  const terakhir = langkah.length - 1

  return (
    <div data-alat="1" className="animate-fade-in mb-2 flex justify-start">
      <div className="max-w-[min(360px,85vw)] rounded-2xl border border-blue-100/80 dark:border-blue-900/50 bg-blue-50/80 dark:bg-blue-950/40 px-3 py-2.5 shadow-sm">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-blue-600 dark:text-blue-400">
          <span className="w-3.5 h-3.5 rounded-full border-2 border-blue-500/40 border-t-blue-600 dark:border-blue-400/30 dark:border-t-blue-400 animate-spin" />
          <span>{label}</span>
        </div>
        <ul className="mt-2 space-y-1.5">
          {langkah.map((l, i) => {
            const berjalan = i === terakhir
            return (
              <li key={l.id || i} className="flex items-center gap-2 text-[11px] leading-tight">
                <span
                  className={`shrink-0 w-4 h-4 rounded-full flex items-center justify-center ${
                    berjalan
                      ? 'bg-blue-500/15 text-blue-600 dark:text-blue-400'
                      : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                  }`}
                >
                  {berjalan ? <IconAlat /> : <IconCentang />}
                </span>
                <span
                  className={
                    berjalan
                      ? 'text-gray-700 dark:text-gray-200 font-medium'
                      : 'text-gray-500 dark:text-gray-400 line-through decoration-gray-300 dark:decoration-slate-600'
                  }
                >
                  {l.label}
                </span>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
