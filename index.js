(function() {
    var config = {
        name: "Мой ТВ Плейлист",
        version: "1.0.0",
        // Параметр "content" должен указывать на тип контента или список элементов
        content: "https://raw.githubusercontent.com/Dmitriy11223455/tv/refs/heads/main/playlist_928374hfkj.m3u"
    };

    // Проверка окружения MSX
    if (typeof TVXAdminTools !== 'undefined') {
        TVXAdminTools.initApp(config);
    } else if (window.msxApp) {
        msxApp.init(config);
    } else {
        console.log("Конфигурация готова: ", config);
    }
})();
