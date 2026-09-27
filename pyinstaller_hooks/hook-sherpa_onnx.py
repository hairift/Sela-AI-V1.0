# -*- mode: python ; coding: utf-8 -*-
"""Hook PyInstaller untuk paket ``sherpa_onnx``.

Mengapa hook ini ada
--------------------
Paket ``sherpa_onnx`` memuat pustaka aslinya dari subfolder paket
(``sherpa_onnx/lib``):

* Windows : ``onnxruntime.dll``, ``sherpa-onnx-c-api.dll``,
            ``sherpa-onnx-cxx-api.dll``
* Linux   : ``libonnxruntime.so*``, ``libsherpa-onnx-c-api.so``,
            ``libsherpa-onnx-cxx-api.so``
* macOS   : ``libonnxruntime*.dylib``, ``libsherpa-onnx-c-api.dylib``,
            ``libsherpa-onnx-cxx-api.dylib``

DLL/SO itu **tidak** muncul di tabel impor ``_sherpa_onnx.*.pyd`` (dimuat saat
berjalan), sehingga analisis PyInstaller tidak ikut mengemasnya. Build yang
cacat hanya memuat ``.pyd`` tanpa pustaka pendamping; akibatnya pembuatan
``KeywordSpotter`` (wake word) menabrak memori → **segfault**, dan karena
aplikasi dibangun ``--windowed`` pengguna tidak melihat pesan apa pun —
aplikasi tampak "tidak mau terbuka".

``pyinstaller_hooks_contrib`` tidak menyediakan hook untuk paket ini, jadi hook
ini yang melengkapinya. Platform-agnostik: ``collect_dynamic_libs`` memilih
``.dll`` / ``.so`` / ``.dylib`` sesuai sistem yang sedang membangun.
"""

from PyInstaller.utils.hooks import collect_dynamic_libs

# Mengumpulkan semua pustaka dinamis milik paket, mempertahankan struktur
# tujuannya (sherpa_onnx/lib) supaya loader menemukannya seperti pada instalasi
# pip biasa.
binaries = collect_dynamic_libs("sherpa_onnx")

# Paket ini diimpor di dalam fungsi (wake word) sehingga analisis statis bisa
# melewatkannya; pastikan modul Python-nya ikut terbundel.
hiddenimports = ["sherpa_onnx"]
