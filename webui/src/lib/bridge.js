/**
 * Klien WebSocket ke mesin AI SELA (py-xiaozhi).
 *
 * Seluruh kecerdasan aplikasi ada di sisi Python. Peramban hanya menjadi
 * tampilan: mengirim perintah (bicara, mode, batal, keluar) dan menerima
 * status (transkrip, jawaban, emosi, data lipsync).
 *
 * Protokol pesan (JSON, dua arah):
 *   Python -> Web : snapshot | state | chat | emotion | status | notice |
 *                   music | lyrics | music_line | button_text | auto_mode |
 *                   user_text | lip | pong
 *   Web -> Python : send_text | manual_toggle | auto_start | auto_toggle |
 *                   abort | open_settings | quit | ping
 */

const RECONNECT_BASE_MS = 800;
const RECONNECT_MAX_MS = 8000;

export function buatAlamatWebSocket() {
  const { protocol, host } = window.location;
  const skema = protocol === 'https:' ? 'wss:' : 'ws:';
  // Bila dibuka langsung dari berkas (file://), kembali ke localhost bawaan.
  if (!host) return `${skema}//127.0.0.1:8765/ws`;
  return `${skema}//${host}/ws`;
}

export function createSelaBridge({ onEvent, onConnectionChange } = {}) {
  let socket = null
  let tertutup = false
  let percobaan = 0
  let timer = null
  const antrean = []

  const kirimMentah = (objek) => {
    const teks = JSON.stringify(objek)
    if (socket && socket.readyState === WebSocket.OPEN) {
      try {
        socket.send(teks)
        return true
      } catch (_) {
        return false
      }
    }
    antrean.push(teks)
    return false
  }

  const bersihkanAntrean = () => {
    while (antrean.length > 0) {
      const teks = antrean.shift()
      try {
        socket.send(teks)
      } catch (_) {
        break
      }
    }
  }

  const sambung = () => {
    if (tertutup) return
    try {
      socket = new WebSocket(buatAlamatWebSocket())
    } catch (_) {
      jadwalkanUlang()
      return
    }

    socket.onopen = () => {
      percobaan = 0
      if (onConnectionChange) onConnectionChange(true)
      bersihkanAntrean()
    }

    socket.onmessage = (event) => {
      let data
      try {
        data = JSON.parse(event.data)
      } catch (_) {
        return
      }
      if (data && onEvent) onEvent(data)
    }

    socket.onclose = () => {
      if (onConnectionChange) onConnectionChange(false)
      jadwalkanUlang()
    }

    socket.onerror = () => {
      // onclose akan menyusul; cukup pastikan status tampil terputus.
      if (onConnectionChange) onConnectionChange(false)
    }
  }

  const jadwalkanUlang = () => {
    if (tertutup) return
    const jeda = Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * 2 ** percobaan)
    percobaan += 1
    clearTimeout(timer)
    timer = setTimeout(sambung, jeda)
  }

  sambung()

  return {
    sendText: (text) => kirimMentah({ t: 'send_text', text }),
    manualToggle: () => kirimMentah({ t: 'manual_toggle' }),
    buttonPress: () => kirimMentah({ t: 'button_press' }),
    buttonRelease: () => kirimMentah({ t: 'button_release' }),
    autoStart: () => kirimMentah({ t: 'auto_start' }),
    autoToggle: () => kirimMentah({ t: 'auto_toggle' }),
    abort: () => kirimMentah({ t: 'abort' }),
    openSettings: () => kirimMentah({ t: 'open_settings' }),
    quit: () => kirimMentah({ t: 'quit' }),
    ping: () => kirimMentah({ t: 'ping' }),
    tutup: () => {
      tertutup = true
      clearTimeout(timer)
      try {
        socket?.close()
      } catch (_) {
        // diabaikan
      }
    },
    apakahTerbuka: () => Boolean(socket && socket.readyState === WebSocket.OPEN),
  }
}
