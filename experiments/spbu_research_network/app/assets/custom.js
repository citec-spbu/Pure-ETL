// ============================================================
// NAVBAR: подсветка активной страницы
// Работает и при полной загрузке, и при SPA-переходах Dash.
// ============================================================

(function () {
    "use strict";

    // ---------------------------------------------------------
    // Проверка: активна ли ссылка для текущего пути
    // ---------------------------------------------------------
    function isActive(href, pathname) {
        if (!href) return false;

        // Точное совпадение: /researchers === /researchers
        if (href === pathname) return true;

        // Вложенные пути: /author/123 начинается с /author
        if (href !== "/" && pathname.indexOf(href) === 0) return true;

        return false;
    }

    // ---------------------------------------------------------
    // Обновление подсветки
    // ---------------------------------------------------------
    function updateActiveLink() {
        var pathname = window.location.pathname;
        var links = document.querySelectorAll(".nav-link-custom");

        for (var i = 0; i < links.length; i++) {
            var link = links[i];
            var href = link.getAttribute("href");

            if (isActive(href, pathname)) {
                if (!link.classList.contains("active")) {
                    link.classList.add("active");
                }
            } else {
                if (link.classList.contains("active")) {
                    link.classList.remove("active");
                }
            }
        }
    }

    // ---------------------------------------------------------
    // Проверяем URL каждые 200 мс
    // (Dash не даёт события о смене URL, проще всего — polling)
    // ---------------------------------------------------------
    var lastPath = null;

    function checkPath() {
        var currentPath = window.location.pathname;
        if (currentPath !== lastPath) {
            lastPath = currentPath;
            updateActiveLink();
        }
    }

    // ---------------------------------------------------------
    // MutationObserver — срабатывает на любое изменение DOM.
    // Dash меняет DOM при каждом SPA-переходе.
    // ---------------------------------------------------------
    function startObserver() {
        var observer = new MutationObserver(function () {
            checkPath();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    }

    // ---------------------------------------------------------
    // Запуск
    // ---------------------------------------------------------
    function init() {
        checkPath();       // сразу
        startObserver();   // + следим за DOM

        // Плюс страховка: polling каждые 200 мс
        setInterval(checkPath, 200);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();