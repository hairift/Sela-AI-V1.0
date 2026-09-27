/**
 * Hook kecil: ukuran jendela peramban, diperbarui saat jendela berubah.
 *
 * Dipakai elemen melayang (kartu kamera, pil kecil penggantinya) supaya
 * posisinya dihitung ulang saat jendela diperkecil/dibesarkan. Tanpa ini,
 * posisi hanya dihitung sekali dan elemen bisa tertinggal di luar layar -
 * misalnya saat antarmuka berpindah dari lanskap ke potret.
 *
 * Pengambarnya sengaja memakai ``requestAnimationFrame`` supaya perubahan
 * ukuran yang beruntun (saat pengguna menyeret tepi jendela) tidak membuat
 * React merender puluhan kali per detik.
 */

import { useEffect, useState } from 'react'

function ukuranSekarang() {
  if (typeof window === 'undefined') return { lebar: 0, tinggi: 0 }
  return { lebar: window.innerWidth, tinggi: window.innerHeight }
}

export default function useUkuranJendela() {
  const [ukuran, setUkuran] = useState(ukuranSekarang)

  useEffect(() => {
    if (typeof window === 'undefined') return undefined
    let tertunda = 0
    const jadwalkan = () => {
      if (tertunda) return
      tertunda = window.requestAnimationFrame(() => {
        tertunda = 0
        const baru = ukuranSekarang()
        setUkuran((lama) =>
          lama.lebar === baru.lebar && lama.tinggi === baru.tinggi ? lama : baru,
        )
      })
    }
    window.addEventListener('resize', jadwalkan)
    window.addEventListener('orientationchange', jadwalkan)
    return () => {
      window.removeEventListener('resize', jadwalkan)
      window.removeEventListener('orientationchange', jadwalkan)
      if (tertunda) window.cancelAnimationFrame(tertunda)
    }
  }, [])

  return ukuran
}
