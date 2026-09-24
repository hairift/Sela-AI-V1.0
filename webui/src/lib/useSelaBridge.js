/**
 * Hook React penghubung antarmuka dengan mesin AI SELA (py-xiaozhi).
 *
 * Menyatukan seluruh status runtime di satu tempat: percakapan, status
 * avatar, emosi, mode otomatis, dan data lipsync. Komponen lain cukup
 * membaca nilai kembalian hook ini.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createSelaBridge } from './bridge'

let urutanId = 0
const idBaru = () => `m${Date.now().toString(36)}${(urutanId++).toString(36)}`

// Nama state dari Python (DeviceState) -> state avatar di antarmuka.
const PETA_STATE = {
  idle: 'idle',
  listening: 'listening',
  speaking: 'speaking',
  connecting: 'thinking',
  connecting_state: 'thinking',
}

export default function useSelaBridge() {
  const [terhubung, setTerhubung] = useState(false)
  const [statusTeks, setStatusTeks] = useState('Menghubungkan ke mesin AI...')
  const [emosi, setEmosi] = useState('neutral')
  const [stateAvatar, setStateAvatar] = useState('idle')
  const [modeOtomatis, setModeOtomatis] = useState(false)
  const [teksTombol, setTeksTombol] = useState('')
  const [barisMusik, setBarisMusik] = useState('')
  const [pesan, setPesan] = useState([])
  const [lip, setLip] = useState({ v: 0, viseme: 'sil' })
  const [catatan, setCatatan] = useState(null)

  const bridgeRef = useRef(null)

  const tambahPesan = useCallback((peran, teks) => {
    const bersih = String(teks || '').trim()
    if (!bersih) return
    setPesan((lama) => {
      // Hindari duplikat beruntun (jalur tts dan presenter bisa mengirim sama).
      const terakhir = lama[lama.length - 1]
      if (terakhir && terakhir.peran === peran && terakhir.teks === bersih) {
        return lama
      }
      return [...lama, { id: idBaru(), peran, teks: bersih, waktu: Date.now() }]
    })
  }, [])

  const tanganiEvent = useCallback(
    (data) => {
      switch (data.t) {
        case 'snapshot':
          if (data.status) setStatusTeks(data.status)
          if (data.emotion) setEmosi(data.emotion)
          if (data.deviceState) setStateAvatar(PETA_STATE[data.deviceState] || 'idle')
          if (typeof data.autoMode === 'boolean') setModeOtomatis(data.autoMode)
          if (data.buttonText) setTeksTombol(data.buttonText)
          if (data.musicLine) setBarisMusik(data.musicLine)
          break

        case 'state':
          setStateAvatar(PETA_STATE[data.state] || 'idle')
          break

        case 'chat':
          tambahPesan(data.role === 'user' ? 'user' : 'assistant', data.text)
          break

        case 'user_text':
          tambahPesan('user', data.text)
          break

        case 'emotion':
          if (data.emotion) setEmosi(data.emotion)
          break

        case 'status':
          if (data.status) setStatusTeks(data.status)
          break

        case 'notice':
          if (data.text) {
            setCatatan(data.text)
            setTimeout(() => setCatatan(null), 6000)
          }
          break

        case 'music':
          if (data.song) setBarisMusik(`Musik: ${data.song}`)
          break

        case 'lyrics':
        case 'music_line':
          if (data.text) setBarisMusik(data.text)
          break

        case 'button_text':
          if (data.text) setTeksTombol(data.text)
          break

        case 'auto_mode':
          if (typeof data.autoMode === 'boolean') setModeOtomatis(data.autoMode)
          break

        case 'lip':
          setLip({ v: Number(data.v) || 0, viseme: data.viseme || 'sil' })
          break

        default:
          break
      }
    },
    [tambahPesan],
  )

  useEffect(() => {
    const bridge = createSelaBridge({
      onEvent: tanganiEvent,
      onConnectionChange: (ok) => {
        setTerhubung(ok)
        setStatusTeks(
          ok ? 'Siap mendengarkan' : 'Mesin AI belum tersambung. Pastikan aplikasi SELA sedang berjalan.',
        )
        if (!ok) setStateAvatar('idle')
      },
    })
    bridgeRef.current = bridge
    return () => bridge.tutup()
  }, [tanganiEvent])

  const aksi = useMemo(
    () => ({
      kirimTeks: (teks) => bridgeRef.current?.sendText(teks),
      rekamToggle: () => bridgeRef.current?.manualToggle(),
      mulaiOtomatis: () => bridgeRef.current?.autoStart(),
      toggleMode: () => bridgeRef.current?.autoToggle(),
      batalkan: () => bridgeRef.current?.abort(),
      bukaPengaturan: () => bridgeRef.current?.openSettings(),
      keluar: () => bridgeRef.current?.quit(),
      bersihkanPercakapan: () => setPesan([]),
      hapusPesan: (id) => setPesan((lama) => lama.filter((p) => p.id !== id)),
    }),
    [],
  )

  return {
    terhubung,
    statusTeks,
    emosi,
    stateAvatar,
    modeOtomatis,
    teksTombol,
    barisMusik,
    pesan,
    lip,
    catatan,
    aksi,
  }
}
