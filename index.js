(function() {
    var config = {
        name: "Мой ТВ Плейлист",
        version: "1.0.1",
        // Ссылка на ваш M3U файл в этом же репозитории
        content: "https://raw.githubusercontent.com/Dmitriy11223455/tv/refs/heads/main/playlist_928374hfkj.m3u"
    };

    if (typeof TVXAdminTools !== 'undefined') {
        TVXAdminTools.initApp(config);
    } else if (window.msxApp) {
        msxApp.init(config);
    }
})();
