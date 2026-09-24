# Arsitektur: Cara Kerja Jembatan Antarmuka ↔ Mesin AI

Dokumen ini menjelaskan bagaimana antarmuka web SELA terhubung ke mesin AI
py-xiaozhi **tanpa mengubah** arsitektur inti mesin tersebut.

---

## Prinsip

1. **Satu mesin AI.** Seluruh kecerdasan (protokol, audio, MCP, kata bangun,
   aktivasi) tetap di `src/`. Antarmuka tidak menghitung apa pun selain tata
   letak dan animasi.
2. **Antarmuka = ViewPort.** py-xiaozhi sudah punya konsep `ViewPort`
   (`src/ui/shared/viewport.py`) dengan implementasi `gui`, `cli`, `tui`,
   `gpio`. Mode `web` adalah implementasi **kelima**, ditambahkan tanpa
   menyentuh yang lain.
3. **Tanpa penghapusan.** Semua tombol dan fungsi lama tetap ada. Perubahan
   hanya menambah, memperbaiki, dan menerjemahkan.

---

## Alur data

```
        Pengguna menekan tombol mikrofon
                    │
                    ▼
   [webui] ChatPanel / VoiceControls
                    │  WebSocket: {"t":"manual_toggle"}
                    ▼
   [Python] SelaWebServer  (src/ui/web/server.py)
                    │
                    ▼
   [Python] SelaBridge.handle_command()  (src/ui/web/bridge.py)
                    │  EventBus: UI_MANUAL_TOGGLE
                    ▼
   ┌────────────────────────────────────────────────────┐
   │  MESIN AI py-xiaozhi (tidak diubah)                │
   │  Session → Protocol → Audio → MCP                  │
   └────────────────────────────────────────────────────┘
                    │  EventBus: DEVICE_STATE_CHANGED, INCOMING_JSON …
                    ▼
   [Python] SelaBridge → WebSocket {"t":"state"} {"t":"chat"}
                    │
                    ▼
   [webui] useSelaBridge() → Avatar3D, ChatPanel, VoiceControls
```

---

## Bagian-bagian

### 1. `src/ui/web/server.py` — server lokal

Server **aiohttp** yang mengikat hanya ke `127.0.0.1`:

| Rute | Fungsi |
| --- | --- |
| `GET /` | Menyajikan `webui/dist/index.html` |
| `GET /<aset>` | Berkas JS/CSS/model 3D |
| `GET /ws` | **WebSocket** dua arah (status ↔ perintah) |
| `GET /api/status` | Status singkat (jumlah klien, kesiapan dist) |
| `GET /api/config` | Baca setelan mesin AI |
| `POST /api/config` | Tulis setelan mesin AI |
| `GET /api/devices` | Daftar perangkat audio |

Bila `webui/dist` belum dibangun, server menyajikan halaman petunjuk yang
menjelaskan cara membangunnya — bukan halaman kosong.

### 2. `src/ui/web/bridge.py` — jembatan EventBus

Berlangganan ke EventBus yang **sudah ada**:

| Event py-xiaozhi | Dikirim ke antarmuka sebagai |
| --- | --- |
| `DEVICE_STATE_CHANGED` | `{"t":"state","state":"listening"}` |
| `INCOMING_JSON` (`tts`) | `{"t":"chat","role":"assistant","text":…}` |
| `INCOMING_JSON` (`stt`) | `{"t":"chat","role":"user","text":…}` |
| `INCOMING_JSON` (`llm`) | `{"t":"emotion","emotion":…}` |
| `NETWORK_ERROR` | `{"t":"status","connected":false}` |
| `SYSTEM_NOTICE` | `{"t":"notice","text":…}` |
| `MUSIC_STATE_CHANGED` | `{"t":"music","state":…,"song":…}` |
| `MUSIC_LYRICS_UPDATE` | `{"t":"lyrics","text":…}` |

Dan sebaliknya, perintah dari antarmuka menjadi event UI yang **sama persis**
dengan yang dipakai antarmuka QML:

| Pesan antarmuka | Event yang dipancarkan |
| --- | --- |
| `send_text` | `UI_SEND_TEXT` (+ `UISendTextRequest`) |
| `manual_toggle` | `UI_MANUAL_TOGGLE` |
| `auto_start` | `UI_AUTO_START` |
| `auto_toggle` | `UI_AUTO_TOGGLE` |
| `abort` | `UI_ABORT_REQUEST` |
| `open_settings` | `UI_OPEN_SETTINGS` |
| `quit` | `UI_QUIT_REQUEST` |

Karena memakai event yang sama, perilaku aplikasi identik dengan antarmuka
QML — tidak ada logika yang diduplikasi.

### 3. `src/ui/web/manager.py` — `WebViewManager`

Mengimplementasikan protokol `ViewPort`. Artinya seluruh pemanggilan dari
`UiPresenter` (`set_chat_text`, `set_status`, `set_emotion`, `set_button_text`,
`set_auto_mode`, `set_music_line`) otomatis diteruskan ke peramban — presenter
tidak perlu diubah.

Kelas ini juga memasang **pendengar audio output** pada codec untuk lipsync.

### 4. `src/ui/web/launcher.py` — pembuka jendela

Tiga strategi, dipilih otomatis:

1. **pywebview** — jendela native tanpa bilah peramban (bila terpasang)
2. **Chromium/Chrome kiosk** — layar penuh tanpa bingkai (kios Raspberry Pi)
3. **Peramban bawaan sistem** — selalu tersedia

Kegagalan membuka jendela **tidak pernah** menghentikan mesin AI; URL selalu
tercatat di log.

---

## Lipsync: bagaimana mulut bergerak mengikuti suara

Ini bagian yang membuat avatar terasa hidup.

```
Opus dari server → AudioCodec.decode → FIFO → _output_callback (thread audio)
                                                     │
                                    outdata = PCM akhir yang dikirim ke speaker
                                                     │
                              SelaBridge.feed_output_audio(pcm)
                                                     │
                          RMS + centroid spektral → {volume, viseme}
                                                     │
                             WebSocket {"t":"lip","v":0.62,"viseme":"a"}
                                                     │
                              Avatar3D → morph target mulut
```

**Mengapa dari Python, bukan dari peramban?**
Karena suara diputar oleh mesin AI di Python, peramban tidak "mendengar" audio
itu dan tidak bisa menganalisisnya. Dengan mengambil sampel **tepat sebelum
dikirim ke speaker**, gerak mulut dijamin sinkron dengan suara yang benar-benar
terdengar.

**Ringan untuk Raspberry Pi.** Perhitungan hanya RMS + satu FFT kecil (≤1024
sampel) pada thread audio yang sudah ada, lalu dikirim maksimal 30 paket per
detik. Tidak ada render ulang React per frame — data lipsync disimpan di `ref`
dan dibaca langsung oleh `useFrame` Three.js.

**Pemetaan viseme → morph target**

| Viseme | Bentuk mulut | Morph utama |
| --- | --- | --- |
| `a` | terbuka lebar | `visemeAa` (+`visemeE` sedikit) |
| `e` | agak melebar | `visemeE` |
| `i` | melebar | `visemeIh` |
| `o` | bulat | `visemeO` |
| `u` | bulat kecil | `visemeU` |

Model `sela.glb` memakai nama morph `a, i, u, e, o` — daftar alias di
`Avatar3D.jsx` juga menerima `aa, ih, EyeBlinkLeft, …` sehingga model versi lain
tetap jalan.

---

## Model 3D

`webui/public/models/sela.glb` berisi:

| Jenis | Isi |
| --- | --- |
| Animasi | `Idle`, `Talking`, `Thinking`, `Greeting`, `Goodbye`, `Confused`, `Nodding`, `Shaking Head` |
| Morph target | `a`, `i`, `u`, `e`, `o`, `blink.l`, `blink.r`, `blink.all` |

`Talking_%temp` sengaja **tidak** diputar karena ia menganimasikan bobot mulut
dan akan bertabrakan dengan lipsync.

Gerakan sekali-jalan (`Greeting`, `Goodbye`, …) dipicu oleh properti `gerakan`
dari mesin AI, sama seperti pada aplikasi SELA Desktop.

---

## Tata letak responsif

| Layar | Tata letak |
| --- | --- |
| Desktop (≥768 px) | Avatar di tengah, panel percakapan mengambang di kanan (lebar 380-420 px) |
| Potret (<768 px) | Avatar penuh layar, panel percakapan menjadi lembaran bawah yang dapat dibuka/tutup |

Dijalankan dengan kelas Tailwind (`md:`) plus penyesuaian di `index.css`
(safe-area, `overscroll-behavior`, pengurangan animasi). Mode jendela diatur
lewat `--portrait` / `--kiosk` atau `SELA_PORTRAIT=1` / `SELA_KIOSK=1`.

---

## Yang **tidak** berubah

Agar jelas, hal-hal berikut sama sekali tidak disentuh:

- `src/protocols/` — WebSocket & MQTT
- `src/audio_codecs/` — kecuali **penambahan** pendengar output (aditif, tidak mengubah alur)
- `src/activation/`, `src/mcp/`, `src/plugins/` (selain string presenter)
- `src/ui/gui/`, `src/ui/cli/`, `src/ui/tui/`, `src/ui/gpio/`
- `libs/`, `models/`

Perubahan pada mesin AI terbatas pada:

1. `src/constants/system.py` — nama & versi aplikasi
2. `src/plugins/ui_presenter.py` — teks status diterjemahkan ke Bahasa Indonesia
3. `src/audio_codecs/audio_codec.py` — penambahan `add_output_listener`
4. `src/ui/shared/factory.py` — pendaftaran mode `web`
5. `main.py` — mode bawaan, `--doctor`, `--portrait`, `--kiosk`, pelaporan galat
6. `src/utils/diagnostics.py` — **berkas baru**
