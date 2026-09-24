"""音乐 MCP 工具：由容器注入的 MusicPlayer 注册，不使用全局 get_instance."""

from typing import Any, Callable

from src.logging import get_logger
from src.mcp.tooling import McpTool, Property, PropertyList, PropertyType

from .music_player import MusicPlayer

logger = get_logger()


def register_music_tools(
    add_tool: Callable[[McpTool], None], player: MusicPlayer
) -> None:
    """向 McpServer 注册音乐工具（闭包持有容器注入的 player）."""

    async def search_and_play(args: dict[str, Any]) -> str:
        song_name = (args or {}).get("song_name", "")
        result = await player.search_and_play(song_name)
        return result.get("message", "搜索播放完成")

    async def pause(args: dict[str, Any]) -> str:
        # MCP 工具侧默认 manual；TTS 暂停走 EventBus 不经此工具
        result = await player.pause(source="manual")
        return result.get("message", "已暂停")

    async def resume(args: dict[str, Any]) -> str:
        result = await player.resume()
        return result.get("message", "已恢复播放")

    async def stop(args: dict[str, Any]) -> str:
        result = await player.stop()
        return result.get("message", "停止播放完成")

    async def seek(args: dict[str, Any]) -> str:
        percent = int(args.get("percent", -1))
        position = int(args.get("position", -1))
        kwargs: dict[str, Any] = {}
        if percent >= 0:
            kwargs["percent"] = percent
        elif position >= 0:
            kwargs["position"] = position
        else:
            return "请指定 percent（0-100）或 position（秒）"
        result = await player.seek(**kwargs)
        return result.get("message", "跳转完成")

    async def get_status(args: dict[str, Any]) -> str:
        result = await player.get_status()
        return result.get("message", "无法获取状态")

    async def get_lyrics(args: dict[str, Any]) -> str:
        result = await player.get_lyrics()
        if result.get("status") == "success":
            lyrics = result.get("lyrics", [])
            return "歌词内容:\n" + "\n".join(lyrics)
        return result.get("message", "获取歌词失败")

    async def get_local_playlist(args: dict[str, Any]) -> str:
        force_refresh = args.get("force_refresh", False)
        result = await player.get_local_playlist(force_refresh)
        if result.get("status") == "success":
            playlist = result.get("playlist", [])
            total_count = result.get("total_count", 0)
            if playlist:
                text = f"本地音乐歌单 (共{total_count}首):\n"
                text += "\n".join(playlist)
                return text
            return "本地缓存中没有音乐文件"
        return result.get("message", "获取本地歌单失败")

    tools: list[McpTool] = [
        McpTool(
            "music_player.search_and_play",
            (
                "WAJIB dipanggil setiap kali pengguna ingin MENDENGARKAN atau MEMUTAR "
                "musik, misalnya 'putar lagu ...', 'nyalikan musik ...', 'mau dengar lagu ...', "
                "'mainkan lagu ...', atau menyebut judul lagu/penyanyi. "
                "Panggil tool ini LEBIH DULU, jangan menjawab bahwa lagu tidak ditemukan "
                "sebelum tool ini benar-benar dipanggil. "
                "Bila ada musik yang sedang diputar, tool ini menghentikannya lalu memutar "
                "lagu baru. Pencarian mencakup lagu Indonesia maupun luar negeri. "
                "Parameter: song_name - judul lagu dan/atau nama penyanyi."
            ),
            PropertyList([Property("song_name", PropertyType.STRING)]),
            search_and_play,
        ),
        McpTool(
            "music_player.pause",
            (
                "Jeda musik yang sedang diputar tanpa kehilangan posisi; "
                "bisa dilanjutkan dengan resume. Panggil saat pengguna berkata "
                "'jeda musik', 'hentikan dulu musiknya', 'pause lagunya'. "
                "PENTING: panggil tool ini SEBELUM menjawab, jika tidak musik akan "
                "otomatis lanjut setelah SELA selesai bicara."
            ),
            PropertyList(),
            pause,
        ),
        McpTool(
            "music_player.resume",
            (
                "Lanjutkan musik yang dijeda, dari posisi terakhir. "
                "Panggil saat pengguna berkata 'lanjutkan musiknya', 'putar lagi', "
                "'nyalakan lagi musiknya'. Catatan: saat SELA bicara musik dijeda "
                "otomatis dan lanjut sendiri; tool ini hanya untuk permintaan pengguna."
            ),
            PropertyList(),
            resume,
        ),
        McpTool(
            "music_player.stop",
            (
                "Hentikan musik sepenuhnya dan kembali ke awal. "
                "Panggil saat pengguna berkata 'matikan musik', 'stop musiknya', "
                "'tidak usah diputar', 'sudahi'. Beda dengan pause: stop benar-benar "
                "berhenti, pause hanya menjeda dan bisa dilanjutkan."
            ),
            PropertyList(),
            stop,
        ),
        McpTool(
            "music_player.seek",
            (
                "Khusus MELOMPAT ke posisi tertentu dalam lagu. "
                "Bila pengguna berkata 'lompat ke 30%', 'ke tengah lagu' -> pakai "
                "percent (0-100); pemutar menghitung sendiri detiknya. "
                "Bila berkata 'ke menit 2', 'ke detik 90', 'kembali ke awal' -> pakai "
                "position (detik, mulai 0). Untuk 'maju 30 detik': panggil get_status "
                "dulu untuk posisi sekarang, lalu position = detik sekarang + 30. "
                "Tidak perlu lirik untuk melompat."
            ),
            PropertyList(
                [
                    Property("percent", PropertyType.INTEGER, default_value=-1),
                    Property("position", PropertyType.INTEGER, default_value=-1),
                ]
            ),
            seek,
        ),
        McpTool(
            "music_player.get_status",
            (
                "Lihat status pemutaran: judul lagu, sedang diputar/dijeda, "
                "durasi total (detik), posisi sekarang (detik), dan persentase. "
                "Dipakai untuk 'sekarang lagunya sampai mana', 'lagunya berapa lama'. "
                "Untuk melompat posisi gunakan seek, bukan tool ini."
            ),
            PropertyList(),
            get_status,
        ),
        McpTool(
            "music_player.get_lyrics",
            (
                "仅用于获取当前歌曲的歌词文本。"
                "当用户问「歌词是什么」「唱了什么」时调用。"
                "禁止用于：进度跳转、跳到百分之几、快进/快退、计算播放位置——"
                "那些请用 music_player.seek（百分比用 percent）。"
            ),
            PropertyList(),
            get_lyrics,
        ),
        McpTool(
            "music_player.get_local_playlist",
            (
                "获取本地音乐歌单。显示所有已下载并缓存的歌曲。"
                "返回格式：'歌名 - 歌手'，例如'菊花台 - 周杰伦'。"
                "用于用户询问'我有哪些歌'、'本地歌曲列表'、'缓存了什么音乐'等场景。"
                "注意：播放列表中的歌曲时，只需使用歌名调用 search_and_play，"
                "例如列表显示'菊花台 - 周杰伦'，调用 search_and_play(song_name='菊花台') 即可。"
            ),
            PropertyList(
                [Property("force_refresh", PropertyType.BOOLEAN, default_value=False)]
            ),
            get_local_playlist,
        ),
    ]

    for tool in tools:
        add_tool(tool)
    logger.info("已注册 %d 个音乐 MCP 工具（容器注入 MusicPlayer）", len(tools))
