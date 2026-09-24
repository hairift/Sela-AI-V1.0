/* eslint-disable react/prop-types */
/**
 * Bilah atas: tombol menu, nama aplikasi, dan tombol tema.
 * Menyesuaikan ukuran untuk layar potret (kios) maupun desktop.
 */

const IconSun = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="5" />
    <path strokeLinecap="round" d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M17.66 6.34l1.42-1.42" />
  </svg>
)

const IconMoon = () => (
  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
    <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
  </svg>
)

function BadgeKoneksi({ terhubung, aiTerhubung }) {
  // Tiga keadaan, supaya pengguna tahu bedanya "aplikasi belum jalan" dengan
  // "aplikasi jalan tapi sambungan ke mesin AI belum siap".
  const keadaan = !terhubung ? 'mati' : aiTerhubung ? 'siap' : 'menyambung'
  const gaya = {
    siap: {
      judul: 'Mesin AI tersambung',
      kotak:
        'bg-emerald-100 dark:bg-emerald-900/40 border-emerald-300 dark:border-emerald-600',
      titik: 'bg-emerald-500 animate-pulse',
      teks: 'text-emerald-700 dark:text-emerald-300',
      label: 'Siap',
    },
    menyambung: {
      judul: 'Menyambungkan ke mesin AI...',
      kotak:
        'bg-amber-100 dark:bg-amber-900/40 border-amber-300 dark:border-amber-600',
      titik: 'bg-amber-500 animate-pulse',
      teks: 'text-amber-700 dark:text-amber-300',
      label: 'Menyambung',
    },
    mati: {
      judul: 'Aplikasi SELA belum berjalan',
      kotak:
        'bg-rose-100 dark:bg-rose-900/40 border-rose-300 dark:border-rose-600',
      titik: 'bg-rose-500',
      teks: 'text-rose-700 dark:text-rose-300',
      label: 'Aplikasi mati',
    },
  }[keadaan]

  return (
    <div
      id="status-koneksi-badge"
      title={gaya.judul}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border transition-colors ${gaya.kotak}`}
    >
      <span className={`w-2 h-2 rounded-full ${gaya.titik}`} />
      <span
        className={`text-[9px] font-bold uppercase tracking-wide hidden sm:inline ${gaya.teks}`}
      >
        {gaya.label}
      </span>
    </div>
  )
}

export default function Navbar({
  onMenuClick,
  theme,
  setTheme,
  terhubung = false,
  aiTerhubung = false,
}) {
  const toggleTheme = () => setTheme?.(theme === 'light' ? 'dark' : 'light')

  return (
    <header className="flex items-center justify-between gap-2 px-4 sm:px-6 pt-4 sm:pt-5 pb-2 shrink-0">
      <button
        id="hamburger-btn"
        onClick={onMenuClick}
        className="w-10 h-10 flex flex-col justify-center gap-[5px] group rounded-lg hover:bg-white/50 dark:hover:bg-slate-800/50 transition-colors"
        aria-label="Buka menu"
      >
        <span className="block h-[2px] w-6 bg-gray-500 dark:bg-gray-400 rounded-full group-hover:bg-blue-500 transition-colors" />
        <span className="block h-[2px] w-6 bg-gray-500 dark:bg-gray-400 rounded-full group-hover:bg-blue-500 transition-colors" />
        <span className="block h-[2px] w-4 bg-gray-500 dark:bg-gray-400 rounded-full group-hover:bg-blue-500 transition-colors" />
      </button>

      <h1 className="text-lg sm:text-xl font-bold tracking-[0.3em] text-gray-800 dark:text-gray-100 select-none">
        SELA
      </h1>

      <div className="flex items-center gap-2">
        <BadgeKoneksi terhubung={terhubung} aiTerhubung={aiTerhubung} />

        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg border border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-300 bg-white dark:bg-slate-900 shadow-sm hover:bg-gray-50 dark:hover:bg-slate-800 transition-all"
          aria-label="Ganti tema"
          title={theme === 'light' ? 'Aktifkan tema gelap' : 'Aktifkan tema terang'}
        >
          {theme === 'light' ? <IconMoon /> : <IconSun />}
        </button>

        <span className="px-2 py-1.5 text-xs font-bold rounded-lg border border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-300 bg-white dark:bg-slate-900 shadow-sm select-none">
          ID
        </span>
      </div>
    </header>
  )
}
