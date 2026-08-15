/* Главная логика приложения. */
(function () {
  const $ = (sel) => document.querySelector(sel);

  function init() {
    BSApp.init();
    document.body.classList.add("loaded");
    Catalog.load().then(() => {
      Catalog.render();
      Cart.renderBadge();
      bindEvents();
      BSApp.haptic("light");
    });
  }

  function bindEvents() {
    // Фильтры
    $("#filters").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-filter]");
      if (!btn) return;
      Catalog.activeFilter = btn.dataset.filter;
      Catalog.render();
    });

    // Добавление в корзину (делегирование)
    $("#catalog").addEventListener("click", (e) => {
      const add = e.target.closest("[data-add]");
      if (!add) return;
      Cart.add(add.dataset.add, 1);
      BSApp.haptic("medium");
      flashButton(add, "✓ Добавлено");
    });

    // Корзина
    $("#cartBtn").addEventListener("click", () => {
      Cart.renderPanel();
      openOverlay("cartOverlay");
      BSApp.haptic("light");
    });
    $("#closeCart").addEventListener("click", () => closeOverlay("cartOverlay"));

    // Кнопки +/- в корзине
    $("#cartItems").addEventListener("click", (e) => {
      const inc = e.target.closest("[data-inc]");
      const dec = e.target.closest("[data-dec]");
      if (inc) { Cart.set(inc.dataset.inc, (Cart.items[inc.dataset.inc] || 0) + 1); }
      if (dec) { Cart.set(dec.dataset.dec, (Cart.items[dec.dataset.dec] || 0) - 1); }
      if (inc || dec) { Cart.renderPanel(); Cart.renderBadge(); }
    });

    $("#emptyCartBtn").addEventListener("click", () => {
      Cart.clear();
      Cart.renderPanel();
    });

    // Оформление
    $("#checkoutBtn").addEventListener("click", () => {
      if (Cart.count() === 0) return;
      closeOverlay("cartOverlay");
      openOverlay("checkoutOverlay");
    });
    $("#closeCheckout").addEventListener("click", () => closeOverlay("checkoutOverlay"));

    $("#checkoutForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const hint = $("#checkoutHint");
      const payload = Cart.buildOrderPayload(e.target);
      if (!payload.items.length) {
        hint.textContent = "Корзина пуста";
        return;
      }
      submitOrder(payload, hint);
    });
  }

  function submitOrder(payload, hint) {
    if (BSApp.ready) {
      // Внутри Telegram: отправляем данные боту через sendData()
      BSApp.sendData(payload);
      hint.innerHTML = "✅ Заказ отправлен в бот!<br>Подтвердите его в чате Beauty Supply.";
      Cart.clear();
      Cart.renderBadge();
    } else {
      // Вне Telegram (превью/разработка): показываем payload
      hint.innerHTML = "✅ (демо) Заказ сформирован:<br><code>" + JSON.stringify(payload) + "</code>";
      Cart.clear();
      Cart.renderBadge();
    }
  }

  function openOverlay(id) { $("#" + id).hidden = false; document.body.classList.add("overlay-open"); }
  function closeOverlay(id) { $("#" + id).hidden = true; document.body.classList.remove("overlay-open"); }

  function flashButton(btn, label) {
    const old = btn.textContent;
    btn.textContent = label;
    btn.classList.add("added");
    setTimeout(() => { btn.textContent = old; btn.classList.remove("added"); }, 900);
  }

  // Локальный поиск через строку запроса (?q=)
  const q = new URLSearchParams(location.search).get("q");
  if (q) {
    document.addEventListener("DOMContentLoaded", () => { setTimeout(() => Catalog.search(q), 300); });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
