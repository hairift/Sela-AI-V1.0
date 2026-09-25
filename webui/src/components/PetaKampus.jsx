/* eslint-disable react/prop-types */
/**
 * Kartu peta lokasi kampus di dalam gelembung jawaban SELA.
 *
 * Muncul otomatis ketika jawaban SELA menyebut alamat kampus atau memuat
 * tautan peta. Petanya memakai OpenStreetMap (gratis, tanpa kunci API) dengan
 * penanda di titik kampus, sehingga pengguna langsung melihat lokasinya tanpa
 * harus membuka tautan.
 */

import { useMemo } from 'react'
import { KAMPUS } from '../lib/percakapan'
import { t } from '../lib/translations'

// Setengah rentang kotak peta (derajat). ~0.004 derajat sama dengan ±450 m.
const RENTANG = 0.004

/** Ambil koordinat dari tautan peta bila ada (mlat/mlon atau #map=z/lat/lon). */
function koordinatDariTautan(teks) {
  const nilai = String(teks || '')
  const mlat = nilai.match(/mlat=(-?\d+(?:\.\d+)?)/)
  const mlon = nilai.match(/mlon=(-?\d+(?:\.\d+)?)/)
  if (mlat && mlon) {
    return { lat: Number(mlat[1]), lon: Number(mlon[1]) }
  }
  const map = nilai.match(/#map=\d+(?:\.\d+)?\/(-?\d+(?:\.\d+)?)\/(-?\d+(?:\.\d+)?)/)
  if (map) {
    return { lat: Number(map[1]), lon: Number(map[2]) }
  }
  const query = nilai.match(/[?&]query=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/)
  if (query) {
    return { lat: Number(query[1]), lon: Number(query[2]) }
  }
  return null
}

export default function PetaKampus({ text = '', judul = KAMPUS.nama }) {
  const titik = useMemo(() => koordinatDariTautan(text) || { lat: KAMPUS.lat, lon: KAMPUS.lon }, [text])

  const { semat, osm, gmaps } = useMemo(() => {
    const { lat, lon } = titik
    const bbox = [lon - RENTANG, lat - RENTANG, lon + RENTANG, lat + RENTANG]
      .map((n) => n.toFixed(6))
      .join(',')
    const posisi = `${lat.toFixed(6)},${lon.toFixed(6)}`
    return {
      semat: `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${posisi}`,
      osm: `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`,
      gmaps: `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`,
    }
  }, [titik])

  return (
    <div
      data-peta="1"
      className="mt-3 overflow-hidden rounded-xl border border-gray-200/80 bg-white shadow-sm dark:border-white/10 dark:bg-slate-900/70"
    >
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 dark:border-white/10">
        <svg className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a2 2 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <div className="min-w-0">
          <p className="text-[11px] font-semibold text-gray-800 dark:text-gray-100 truncate">{judul}</p>
          <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">{KAMPUS.alamat}</p>
        </div>
      </div>

      <iframe
        title={`Peta ${judul}`}
        src={semat}
        loading="lazy"
        className="block w-full h-40 border-0 bg-gray-100 dark:bg-slate-800"
      />

      <div className="flex items-center gap-2 px-3 py-2">
        <a
          href={gmaps}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center text-[11px] font-semibold px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 active:scale-95 transition-all"
        >
          {t.id.mapRoute}
        </a>
        <a
          href={osm}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center text-[11px] font-semibold px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-slate-800 text-blue-700 dark:text-blue-300 border border-blue-200/70 dark:border-slate-700 hover:bg-blue-100 dark:hover:bg-slate-700 active:scale-95 transition-all"
        >
          {t.id.mapOpen}
        </a>
      </div>
    </div>
  )
}
