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
    sectionMusic: 'Musik',
    musicPlatform: 'Platform Pencarian Musik',
    musicQuality: 'Kualitas Audio',
    restartNote:
      'Sebagian perubahan (kata bangun, perangkat audio) berlaku setelah aplikasi dijalankan ulang.',
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

    // Pertanyaan populer
    quickReplies: [
      { label: 'Cara Daftar?', text: 'Bagaimana cara mendaftar sebagai mahasiswa baru?' },
      { label: 'Biaya Kuliah', text: 'Berapa rincian biaya kuliah?' },
      { label: 'Program Studi', text: 'Apa saja program studi dan jurusan yang tersedia?' },
      { label: 'Kontak & Lokasi', text: 'Di mana alamat kampus dan kontak yang bisa dihubungi?' },
    ],

    // Pesan sistem
    errorNetwork: 'Maaf, koneksi ke mesin AI terputus. Coba lagi ya.',
    errorGeneric: 'Maaf, terjadi kendala. Bisa diulang?',
  },
}

export const tr = (key, fallback = '') => t.id[key] ?? fallback ?? key

export default t
