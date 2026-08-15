/* Обёртка над Telegram.WebApp API.
 * Безопасно работает и вне Telegram (для локальной разработки в браузере).
 */
(function (global) {
  const hasTg = typeof window !== "undefined" && !!window.Telegram && !!window.Telegram.WebApp;

  const WebApp = hasTg ? window.Telegram.WebApp : {
    ready: function () {},
    expand: function () {},
    isExpanded: true,
    themeParams: {},
    colorScheme: "light",
    initDataUnsafe: {},
    initData: "",
    sendData: function () {},
    close: function () {},
    HapticFeedback: { impactOccurred: function () {} },
    BackButton: { show: function () {}, hide: function () {}, onClick: function () {} },
    MainButton: { setText: function () {}, show: function () {}, hide: function () {}, onClick: function () {} },
  };

  const App = {
    get webApp() { return WebApp; },
    get ready() { return hasTg; },
    get theme() {
      const t = WebApp.themeParams || {};
      return {
        bg: t.bg_color || "#fffdf9",
        text: t.text_color || "#181312",
        hint: t.hint_color || "#8a7f77",
        btn: t.button_color || "#4b1f28",
        btnText: t.button_text_color || "#ffffff",
        section: t.section_bg_color || "#f5f0e8",
        card: t.secondary_bg_color || "#fbf7f1",
        isDark: WebApp.colorScheme === "dark",
      };
    },
    init: function () {
      WebApp.ready();
      WebApp.expand();
      const theme = this.theme;
      if (theme.isDark) {
        document.documentElement.classList.add("tg-dark");
      }
      const root = document.documentElement;
      root.style.setProperty("--bg", theme.bg);
      root.style.setProperty("--text", theme.text);
      root.style.setProperty("--hint", theme.hint);
      root.style.setProperty("--accent", theme.btn);
      root.style.setProperty("--accent-text", theme.btnText);
      root.style.setProperty("--card", theme.card);
      root.style.setProperty("--section", theme.section);
    },
    haptic: function (style) { WebApp.HapticFeedback.impactOccurred(style || "light"); },
    getUser: function () {
      try { return WebApp.initDataUnsafe.user || null; } catch (e) { return null; }
    },
    getInitData: function () { return WebApp.initData || ""; },
    sendData: function (json) { WebApp.sendData(JSON.stringify(json)); },
    close: function () { WebApp.close(); },
  };

  global.BSApp = App;
})(window);
