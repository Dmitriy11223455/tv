(function() {
    var config = {
        name: "Мой ТВ Плейлист",
        version: "1.0.1",
        // Ссылка на ваш M3U файл в этом же репозитории
        content: "raw.githubusercontent.com"
    };

    if (typeof TVXAdminTools !== 'undefined') {
        TVXAdminTools.initApp(config);
    } else if (window.msxApp) {
        msxApp.init(config);
    }
})();
