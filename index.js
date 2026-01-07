// index.js файл для Media Station X на ТВ

(function() {
    var config = {
        name: "Мой ТВ Плейлист",
        version: "2026.01.07",
        
        // Обратите внимание на полный HTTPS адрес!
        content:
    };

    if (typeof msxApp !== 'undefined') {
        msxApp.init(config);
    } else {
        console.error("Плеер не обнаружен.");
    }
})();
