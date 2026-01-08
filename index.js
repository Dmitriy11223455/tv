// index.js файл для Media Station X на ТВ

(function() {
    var config = {
        name: "Мой ТВ Плейлист",
        version: "2026.01.07",
        
        https://raw.githubusercontent.com/Dmitriy11223455/tv/refs/heads/main/playlist_928374hfkj.m3u
        content:
    };

    if (typeof msxApp !== 'undefined') {
        msxApp.init(config);
    } else {
        console.error("Плеер не обнаружен.");
    }
})();
