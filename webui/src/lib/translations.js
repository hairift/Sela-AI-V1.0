/**
 * Terjemahan antarmuka SELA AI.
 *
 * Hanya Bahasa Indonesia - sesuai kebutuhan kampus. Seluruh teks tombol,
 * judul, dan pesan diambil dari sini agar tidak ada string yang tercecer.
 */

export const t = {
  id: {
    appName: 'SELA',
    appTagline: 'Asisten Kampus UCIC',
    assistantName: 'SELA',
    you: 'Anda',
    sela: 'SELA',
    back: 'Kembali',
    close: 'Tutup',
    save: 'Simpan',
    cancel: 'Batal',
    reset: 'Atur ulang',

    // Menu samping
    newChat: 'Sesi Baru',
    recentChats: 'Riwayat Percakapan',
    noConversations: 'Belum ada percakapan',
    startNewChat: 'Mulai percakapan baru di atas',
    searchConversations: 'Cari percakapan...',
    noResults: 'Tidak ada hasil untuk',
    settings: 'Pengaturan',
    help: 'Bantuan',

    // Panel chat
    chatPanelTitle: 'SELA Asisten UCIC',
    openChat: 'Buka Chat',
    hideChat: 'Sembunyikan bilah chat',
    newSession: '+ Sesi Baru',
    emptyHint: 'Ketik pesan, pilih topik, atau gunakan audio',
    popularQuestions: 'PERTANYAAN POPULER',
    typeMessage: 'Ketik pesan untuk Sela...',
    listeningPlaceholder: 'Sedang mendengarkan... Silakan bicara!',
    sendText: 'Kirim pesan teks',
    listeningClickToSend: 'Sedang mendengarkan... Klik untuk selesai dan kirim',
    speakViaMic: 'Bicara lewat mikrofon',
    scrollDown: 'Gulir ke bawah',

    // Status
    ready: 'Siap',
    listening: 'Mendengarkan',
    thinking: 'Sedang berpikir',
    speaking: 'SELA sedang bicara',
    readyToListen: 'Siap mendengarkan',
    connected: 'Terhubung',
    disconnected: 'Terputus',
    notConnected: 'Tidak terhubung',
    micDenied: 'Izin mikrofon ditolak',
    retryMic: 'Coba lagi izin mikrofon',
    micMissing: 'Mikrofon tidak terdeteksi. Silakan ketik pesan di bilah kanan.',
    clickToSpeak: 'Klik untuk Berbicara',
    listeningHint: 'Mendengarkan... (Bicara atau Klik untuk Kirim)',
    speakingHint: 'SELA Sedang Bicara (Klik untuk Potong)',
    processingHint: 'Sedang Memproses Ucapan...',
    connectingEngine: 'Menyambungkan ke mesin AI...',
    engineOffline: 'Mesin AI belum tersambung. Coba lagi sebentar lagi.',
    appOffline:
      'Aplikasi SELA belum berjalan. Jalankan aplikasi, lalu muat ulang halaman ini.',

    // Tombol aksi
    startListening: 'Mulai bicara',
    stopAndSend: 'Selesai dan kirim',
    interrupt: 'Potong ucapan SELA',
    autoMode: 'Mode Otomatis',
    manualMode: 'Mode Manual',
    abort: 'Batalkan',

    // Pengaturan
    settingsTitle: 'Pengaturan',
    settingsSubtitle: 'Sesuaikan perilaku asisten',
    sectionGeneral: 'Umum',
    sectionAudio: 'Suara & Mikrofon',
    sectionAi: 'Mesin AI',
    sectionDisplay: 'Tampilan',
    theme: 'Tema',
    themeLight: 'Terang',
    themeDark: 'Gelap',
    language: 'Bahasa',
    languageValue: 'Bahasa Indonesia',
    wakeWord: 'Kata Bangun (Wake Word)',
    wakeWordDesc: 'Asisten aktif otomatis saat mendengar kata bangun.',
    wakeWordChoice: 'Pilihan Kata Bangun',
    wakeWordChoiceDesc: 'Ucapkan salah satu untuk memulai tanpa menyentuh layar.',
    wakeWordSensitivity: 'Sensitivitas Kata Bangun',
    wakeWordSensitivityDesc:
      'Makin kecil nilainya, makin mudah terpicu (juga makin mudah salah dengar).',
    serverUrlLabel: 'Alamat Server AI',
    serverUrlDesc:
      'Ubah bila memakai server xiaozhi sendiri, agar jawaban memakai prompt kampus Anda.',
    simpan: 'Simpan',
    batal: 'Batal',
    tersimpan: 'Tersimpan',
    restartNote:
      'Sebagian perubahan (kata bangun, perangkat audio) berlaku setelah aplikasi dijalankan ulang.',
    // Gerbang admin untuk halaman pengaturan
    adminTitle: 'Pengaturan Terkunci',
    adminDesc:
      'Halaman ini mengubah perilaku mesin AI. Masukkan kata sandi admin untuk melanjutkan.',
    adminPlaceholder: 'Kata sandi admin',
    adminUnlock: 'Buka Pengaturan',
    adminChecking: 'Memeriksa...',
    adminWrong: 'Kata sandi salah. Coba lagi.',
    adminUnreachable: 'Tidak bisa menghubungi mesin AI. Pastikan SELA berjalan.',
    adminLock: 'Kunci lagi',
    // Catatan: nilai sebenarnya ada di sisi mesin AI, bukan di berkas ini.
    adminPasswordNote: 'Kata sandi diperiksa oleh mesin AI, bukan disimpan di antarmuka.',

    // Uji mikrofon
    micTest: 'Uji Mikrofon',
    micTestDesc:
      'Rekam 3 detik dan lihat level suaranya. Bila level hampir nol, masalahnya di perangkat mikrofon, bukan di mesin AI.',
    micTestBtn: 'Mulai Uji',
    micTesting: 'Merekam...',
    micTestFail: 'Uji mikrofon gagal dijalankan.',
    micLevel: 'Level suara',
    micPeak: 'Puncak',

    // Log waktu nyata
    logTitle: 'Log Mesin AI',
    logDesc: 'Catatan terbaru dari mesin AI, berguna saat ada masalah.',
    logRefresh: 'Muat ulang',
    logEmpty: 'Belum ada catatan.',
    logLoading: 'Memuat log...',

    // Peredam gema
    aecLabel: 'Peredam Gema (AEC)',
    aecDesc: 'Mengurangi gema pengeras suara agar mikrofon tidak terganggu.',

    // Kamera
    sectionCamera: 'Kamera',
    cameraDevice: 'Perangkat Kamera',
    cameraDeviceDesc: 'Kamera yang dipakai untuk fitur penglihatan (vision).',
    cameraNone: 'Tidak ada kamera terdeteksi',
    cameraLoading: 'Mendeteksi kamera...',
    cameraBackend: 'Mesin Kamera',
    cameraBackendDesc: 'Pilih "Otomatis" bila tidak yakin.',
    cameraTest: 'Uji Kamera',
    cameraTestDesc:
      'Buka kamera dan ambil satu bingkai untuk memastikan kamera berfungsi.',
    cameraTestBtn: 'Mulai Uji',
    cameraTesting: 'Menguji...',
    cameraTestOk: 'Kamera berfungsi.',
    cameraTestFail: 'Uji kamera gagal dijalankan.',
    cameraFloat: 'Kartu Kamera Melayang',
    cameraFloatDesc:
      'Tampilkan kartu kamera kecil yang bisa digeser. Kamera ini yang dipakai saat Anda meminta SELA melihat atau memotret Anda.',
    cameraCard: 'Kamera',
    cameraDrag: 'Geser kartu',
    cameraTake: 'Ambil Foto',
    cameraStarting: 'Menyalakan kamera...',
    cameraNoSupport: 'Peramban ini tidak mendukung kamera.',
    cameraDenied: 'Izin kamera ditolak.',
    cameraFail: 'Kamera tidak bisa dibuka.',
    photoFromCamera: 'Foto dari kamera',
    photoTakenBy: 'SELA mengambil foto ini',

    // Peta lokasi kampus
    mapRoute: 'Buka Rute',
    mapOpen: 'Lihat Peta',
    mapTitle: 'Lokasi Kampus UCIC',

    // Langkah alat (MCP) dan balasan lanjutan
    toolWorking: 'SELA sedang bekerja',
    followUp: 'TANYA LANJUT',
    selaSpeaking: 'SELA sedang bicara',

    // Batas panjang teks
    textLimit: 'Batas teks',
    textLimitHint:
      'Mesin AI hanya menjawab teks pendek. Untuk pertanyaan panjang, tekan tombol mikrofon - jalur suara tidak dibatasi.',
    textTooLong: 'Teks dipotong ke batas mesin AI',
    voiceUnlimited: 'Bicara lewat mikrofon tanpa batas panjang',

    // Pintasan papan tik
    sectionShortcuts: 'Pintasan Papan Tik',
    shortcutsEnabled: 'Aktifkan Pintasan',
    shortcutsEnabledDesc: 'Kendalikan asisten lewat pintasan papan tik.',

    // Tool MCP
    sectionMcp: 'Alat (MCP)',
    mcpDesc:
      'Matikan alat yang tidak dipakai. Alat yang dimatikan tidak ditawarkan ke mesin AI.',
    mcpSearchPlaceholder: 'Cari alat...',
    mcpDisabledCount: 'alat dimatikan',
    mcpNone: 'Tidak ada alat terdeteksi.',
    mcpNotFound: 'Alat tidak ditemukan.',

    autoConversation: 'Percakapan Otomatis',
    autoConversationDesc: 'Mendengarkan dan menjawab tanpa menekan tombol.',
    voiceReply: 'Balasan Suara',
    voiceReplyDesc: 'Asisten membacakan jawaban dengan suara.',
    inputDevice: 'Perangkat Mikrofon',
    outputDevice: 'Perangkat Pengeras Suara',
    defaultDevice: 'Bawaan Sistem',
    connectionStatus: 'Status Koneksi',
    engineAddress: 'Alamat Mesin AI',
    aboutApp: 'Tentang Aplikasi',
    version: 'Versi',

    // Bantuan
    helpTitle: 'Bantuan',
    helpSubtitle: 'Panduan singkat penggunaan SELA',
    helpVoiceTitle: 'Bertanya dengan suara',
    helpVoiceBody:
      'Tekan tombol mikrofon di bawah avatar, lalu ucapkan pertanyaan Anda. Tekan sekali lagi untuk mengirim, atau tunggu SELA selesai mendengarkan.',
    helpTextTitle: 'Bertanya dengan teks',
    helpTextBody:
      'Tulis pertanyaan pada kolom di panel kanan, lalu tekan tombol kirim atau tombol Enter.',
    helpTopicsTitle: 'Topik populer',
    helpTopicsBody:
      'Gunakan tombol pertanyaan populer untuk bertanya cepat tentang pendaftaran, biaya kuliah, program studi, dan kontak kampus.',
    helpInterruptTitle: 'Menghentikan jawaban',
    helpInterruptBody:
      'Saat SELA sedang berbicara, tekan tombol mikrofon sekali untuk menghentikannya dan langsung mengajukan pertanyaan baru.',
    helpTroubleTitle: 'Jika suara tidak merespons',
    helpTroubleBody:
      'Pastikan mikrofon terpasang dan izin mikrofon diberikan. Bila masih bermasalah, jalankan aplikasi dengan perintah "python main.py --doctor" untuk memeriksa perangkat audio.',
    helpShortcuts: 'Pintasan',
    shortcutMic: 'Mulai / hentikan rekaman suara',
    shortcutEsc: 'Tutup menu atau kembali',
    shortcutSend: 'Kirim pesan teks',

    // Pertanyaan populer.
    //
    // Sengaja dibuat PENDEK (di bawah MAKS_PANJANG_TEKS). Server xiaozhi
    // menolak teks panjang pada jalur listen/detect dengan
    // "Detect is only for wake words, do not send long texts". Pertanyaan
    // pendek dikirim sebagai teks sehingga pertanyaannya sampai PERSIS APA
    // ADANYA ke mesin AI - penting agar tool pengetahuan kampus terpanggil
    // dan jawabannya tepat. Pertanyaan panjang tetap bisa diajukan, tetapi
    // lewat tombol mikrofon (jalur suara tidak punya batas panjang).
    quickReplies: [
      { label: 'Cara Daftar?', text: 'Cara daftar di UCIC?' },
      { label: 'Biaya Kuliah', text: 'Biaya kuliah UCIC?' },
      { label: 'Program Studi', text: 'Program studi UCIC?' },
      { label: 'Kontak & Lokasi', text: 'Kontak dan lokasi UCIC?' },
    ],

    // Pesan sistem
    errorNetwork: 'Maaf, koneksi ke mesin AI terputus. Coba lagi ya.',
    errorGeneric: 'Maaf, terjadi kendala. Bisa diulang?',
  },
}

export const tr = (key, fallback = '') => t.id[key] ?? fallback ?? key

export default t
