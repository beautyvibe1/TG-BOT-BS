/* Корзина: состояние, рендер, checkout через Telegram.WebApp.sendData(). */
(function (global) {
  const Cart = {
    items: {}, // { [productId]: quantity }

    load() {
      try { this.items = JSON.parse(localStorage.getItem("bs_cart") || "{}"); }
      catch (e) { this.items = {}; }
    },
    save() {
      localStorage.setItem("bs_cart", JSON.stringify(this.items));
      this.renderBadge();
    },
    add(id, qty) {
      this.items[id] = (this.items[id] || 0) + (qty || 1);
      this.save();
    },
    set(id, qty) {
      if (qty <= 0) delete this.items[id];
      else this.items[id] = qty;
      this.save();
    },
    clear() { this.items = {}; this.save(); },
    count() { return Object.values(this.items).reduce((a, b) => a + b, 0); },
    total() {
      let sum = 0;
      for (const [id, qty] of Object.entries(this.items)) {
        const p = global.Catalog.findById(id);
        if (p) sum += p.price * qty;
      }
      return sum;
    },
    renderBadge() {
      const el = document.getElementById("cartBadge");
      const n = this.count();
      if (!el) return;
      el.hidden = n === 0;
      el.textContent = n;
    },
    renderPanel() {
      const container = document.getElementById("cartItems");
      const totalEl = document.getElementById("cartTotal");
      if (!container) return;
      const ids = Object.keys(this.items).filter((id) => this.items[id] > 0);
      if (ids.length === 0) {
        container.innerHTML = '<p class="cart-empty">Корзина пуста 😔<br>Добавьте товары из каталога.</p>';
        totalEl.textContent = "0 ₽";
        return;
      }
      container.innerHTML = ids.map((id) => {
        const p = global.Catalog.findById(id);
        if (!p) return "";
        const qty = this.items[id];
        return `
          <div class="cart-line">
            <img src="${global.Catalog.esc(p.image)}" alt="" />
            <div class="cart-line-info">
              <strong>${global.Catalog.esc(p.ruName || p.name)}</strong>
              <span>${global.Catalog.fmt(p.price)}</span>
            </div>
            <div class="qty">
              <button data-dec="${id}">−</button>
              <span>${qty}</span>
              <button data-inc="${id}">+</button>
            </div>
          </div>`;
      }).join("");
      totalEl.textContent = global.Catalog.fmt(this.total());
    },
    buildOrderPayload(form) {
      const data = new FormData(form);
      const items = [];
      for (const [id, qty] of Object.entries(this.items)) {
        if (qty <= 0) continue;
        const p = global.Catalog.findById(id);
        if (!p) continue;
        items.push({ product_id: p.id, slug: p.slug, name: p.ruName || p.name, qty, price: p.price });
      }
      return {
        source: "webapp",
        customer_name: data.get("name") || "",
        phone: data.get("phone") || "",
        address: data.get("address") || "",
        delivery_method: data.get("delivery") || "cdek",
        comment: data.get("comment") || "",
        total: this.total(),
        items: items,
        initData: global.BSApp.getInitData(),
        user: global.BSApp.getUser(),
      };
    },
  };

  Cart.load();
  global.Cart = Cart;
})(window);
