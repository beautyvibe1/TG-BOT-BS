/* Каталог: загрузка данных и рендер. */
(function (global) {
  const fmt = (n) => new Intl.NumberFormat("ru-RU").format(n) + " ₽";
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

  const Catalog = {
    data: { categories: [], products: [] },
    filters: [],
    activeFilter: "all",

    async load() {
      try {
        const res = await fetch("data/catalog.json", { cache: "no-store" });
        if (!res.ok) throw new Error("HTTP " + res.status);
        this.data = await res.json();
      } catch (e) {
        console.error("Не удалось загрузить каталог", e);
        const el = document.getElementById("catalog");
        if (el) el.innerHTML = "<p>Не удалось загрузить каталог. Проверьте соединение.</p>";
      }
      return this.data;
    },

    getProducts() {
      const f = this.activeFilter;
      if (f === "all") return this.data.products;
      return this.data.products.filter((p) => p.category === f);
    },

    findById(id) {
      return this.data.products.find((p) => p.id === Number(id));
    },

    productCard(p) {
      return `
      <article class="product-card" data-id="${p.id}">
        <div class="product-media">
          <img loading="lazy" src="${esc(p.image)}" alt="${esc(p.name)}" />
          ${p.badge ? `<span class="badge">${esc(p.badge)}</span>` : ""}
        </div>
        <div class="product-body">
          <span class="product-brand">${esc(p.brand)}</span>
          <h3>${esc(p.ruName || p.name)}</h3>
          <p class="product-summary">${esc(p.summary || "")}</p>
          <div class="product-price">${fmt(p.price)}</div>
          <button class="add-btn" data-add="${p.id}">➕ В корзину</button>
        </div>
      </article>`;
    },

    renderFilters(container) {
      const cats = [{ id: "all", name: "Все", emoji: "✨", count: this.data.products.length }]
        .concat(this.data.categories);
      container.innerHTML = cats.map((c) => `
        <button class="filter ${this.activeFilter === c.id ? "active" : ""}" data-filter="${c.id}">
          ${c.emoji} ${c.name} <small>${c.count}</small>
        </button>`).join("");
    },

    renderCatalog(container, emptyEl) {
      const products = this.getProducts();
      emptyEl.hidden = products.length > 0;
      container.innerHTML = products.map((p) => this.productCard(p)).join("");
    },

    render() {
      const filters = document.getElementById("filters");
      const catalog = document.getElementById("catalog");
      const empty = document.getElementById("empty");
      if (filters) this.renderFilters(filters);
      this.renderCatalog(catalog, empty);
    },

    search(query) {
      const q = (query || "").toLowerCase().trim();
      const container = document.getElementById("catalog");
      const empty = document.getElementById("empty");
      if (!q) { this.activeFilter = "all"; this.render(); return; }
      const found = this.data.products.filter((p) =>
        (p.name + " " + (p.ruName || "") + " " + p.brand).toLowerCase().includes(q)
      );
      empty.hidden = found.length > 0;
      container.innerHTML = found.map((p) => this.productCard(p)).join("");
    },
  };

  Catalog.fmt = fmt;
  Catalog.esc = esc;
  global.Catalog = Catalog;
})(window);
