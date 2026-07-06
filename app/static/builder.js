/* cutecumber page builder (STAGING). Vanilla, no framework, under the dash CSP.
 * In-document canvas: sections render right on the page, are selectable, carry a
 * hover tool cluster, and drag-to-reorder. The public page stays server-rendered
 * and JS-free — this only runs inside the authenticated editor. Ported from the
 * design prototype; page-theme colors come from theme.py (--pg-* vars). */
(function () {
  "use strict";

  var AVATARS = ["sprout", "froggy", "bun", "boo", "berry", "shroom",
    "matcha", "moonbeam", "blossom", "whiskers", "riceball", "twinkle"];
  var MOTIFS = ["sparkle", "sparklePink", "blossom", "heart", "bow", "leaf"];

  // type -> {label, motif, emoji, premium, variants:[[key,label]...]}
  var TYPES = {
    hero: { label: "hello!", motif: "slice", emoji: "👋", premium: false, hint: "avatar, name & bio",
      variants: [["centered", "centered"], ["split", "side by side"], ["banner", "banner"]] },
    links: { label: "links", motif: "heart", emoji: "🔗", premium: false, hint: "the important buttons",
      variants: [["buttons", "buttons"], ["cards", "cards"], ["tiles", "tiles"]] },
    gallery: { label: "gallery", motif: "blossom", emoji: "🖼️", premium: false, hint: "show your work",
      variants: [["three", "grid"], ["polaroid", "polaroids"]] },
    about: { label: "about", motif: "cloud", emoji: "📖", premium: false, hint: "a little story",
      variants: [["simple", "simple"], ["note", "sticky note"], ["split", "text + photo"]] },
    socials: { label: "socials", motif: "strawberry", emoji: "✨", premium: false, hint: "where else to find you",
      variants: [["bubbles", "bubbles"], ["pill", "one pill"]] },
    divider: { label: "divider", motif: "sparkle", emoji: "🎀", premium: false, hint: "a cute breather",
      variants: [["line", "line"], ["row", "motif row"]] },
    embed: { label: "embed", motif: "frog", emoji: "🎬", premium: true, hint: "youtube / spotify",
      variants: [["full", "full width"], ["card", "mini card"]] },
    signup: { label: "mail list", motif: "sprout", emoji: "✉️", premium: true, hint: "link to your newsletter",
      variants: [["band", "banner"], ["card", "card"]] },
    form: { label: "form", motif: "leaf", emoji: "📝", premium: true, hint: "link to your form",
      variants: [["card", "card"]] },
    code: { label: "custom html", motif: "babyCuke", emoji: "⌨️", premium: true, hint: "runs sandboxed",
      variants: [["inert", "preview"]] }
  };
  var ORDER = ["hero", "links", "gallery", "about", "socials", "divider", "embed", "signup", "form", "code"];

  var PRESETS = [
    { key: "strawberry_milk", name: "strawberry milk", bg: "#fff5f7", accent: "#e58fb1", premium: false },
    { key: "matcha_latte", name: "matcha latte", bg: "#f4f9ef", accent: "#6f9a5d", premium: false },
    { key: "seafoam", name: "seafoam", bg: "#eefaf6", accent: "#1f7d76", premium: false },
    { key: "cherry_cola", name: "cherry cola", bg: "#fdf1ef", accent: "#b23350", premium: false },
    { key: "lavender_haze", name: "lavender haze", bg: "#f7f3fd", accent: "#7a59c8", premium: true },
    { key: "midnight_snack", name: "midnight snack", bg: "#232338", accent: "#f3a7c3", premium: true }
  ];

  var TEMPLATES = [
    { key: "artist", name: "the artist", blurb: "gallery first — for illustrators & sticker makers", preset: "strawberry_milk", sections: [
      { type: "hero", variant: "centered", props: { avatar: "blossom", name: "mochi", pronoun: "she/her", bio: "sticker artist & frog enjoyer 🌷 tiny happy things, drawn daily." } },
      { type: "gallery", variant: "polaroid", props: { photos: [{ caption: "new drops" }, { caption: "work in progress" }, { caption: "my desk" }] } },
      { type: "links", variant: "buttons", props: { links: [{ emoji: "🌷", title: "my sticker shop", url: "https://example.com/shop" }, { emoji: "✉️", title: "commission info", url: "https://example.com/commissions" }, { emoji: "📖", title: "my tiny zine", url: "https://example.com/zine" }] } },
      { type: "about", variant: "note", props: { heading: "about me", body: "i draw tiny happy things and put them on everything. based in a very small apartment with a very large cat." } },
      { type: "socials", variant: "bubbles", props: { icons: "🦋 📸 🎬 🎵" } }
    ] },
    { key: "streamer", name: "the streamer", blurb: "bold banner & big buttons — for live folks", preset: "seafoam", sections: [
      { type: "hero", variant: "banner", props: { avatar: "froggy", name: "pondcast", pronoun: "they/them", bio: "cozy games, loud laughs. live tue · thu · sun 🐸" } },
      { type: "links", variant: "tiles", props: { links: [{ emoji: "🎥", title: "watch live", url: "https://example.com/live" }, { emoji: "📼", title: "past streams", url: "https://example.com/vods" }, { emoji: "💬", title: "the lilypad", url: "https://example.com/chat" }] } },
      { type: "divider", variant: "line", props: { motif: "sparkle" } },
      { type: "about", variant: "simple", props: { heading: "stream schedule", body: "tuesday — cozy farming games · thursday — spooky night (lights off) · sunday — community art jam with chat." } },
      { type: "socials", variant: "pill", props: { icons: "🦋 📸 🎬 🎵" } }
    ] },
    { key: "shop", name: "the little shop", blurb: "products up front — for makers who sell", preset: "matcha_latte", sections: [
      { type: "hero", variant: "split", props: { avatar: "matcha", name: "bean & bloom", bio: "hand-poured candles that smell like tiny gardens. small batches, big feelings." } },
      { type: "gallery", variant: "three", props: { photos: [{ caption: "new drops" }, { caption: "bestsellers" }, { caption: "back in stock" }] } },
      { type: "links", variant: "cards", props: { links: [{ emoji: "🛒", title: "shop everything", url: "https://example.com/shop" }, { emoji: "🧺", title: "etsy store", url: "https://example.com/etsy" }, { emoji: "📦", title: "shipping faq", url: "https://example.com/shipping" }, { emoji: "📸", title: "instagram", url: "https://example.com/ig" }] } },
      { type: "divider", variant: "row", props: { motif: "leaf" } },
      { type: "about", variant: "simple", props: { heading: "restock news", body: "new scents bloom on the first friday of every month. mail-garden members get first sniff." } }
    ] },
    { key: "blank", name: "blank patch", blurb: "a fresh little patch 🌱", preset: null, sections: [] }
  ];

  var root = document.getElementById("builder");
  var state = {
    sections: [], selected: null, plan: root.dataset.plan, preset: root.dataset.preset,
    csrf: root.dataset.csrf, username: root.dataset.username, counter: 0,
    addIndex: null, dragId: null, dropIndex: null
  };
  var saveTimer = null, ghost = null;

  // ---- helpers -----------------------------------------------------------
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function host(u) { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return u || ""; } }
  function motifSvg(name, size) {
    var m = MOTIFS.indexOf(name) >= 0 ? name : "sparkle";
    return '<svg viewBox="-16 -16 32 32" width="' + size + '" height="' + size + '" aria-hidden="true"><use href="#m-' + m + '"/></svg>';
  }
  function h(tag, attrs, kids) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") el.className = attrs[k];
      else if (k === "html") el.innerHTML = attrs[k];
      else if (k === "text") el.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] === true) el.setAttribute(k, "");
      else if (attrs[k] != null && attrs[k] !== false) el.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c != null) el.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return el;
  }
  function find(id) { for (var i = 0; i < state.sections.length; i++) if (state.sections[i]._id === id) return i; return -1; }
  function selected() { var i = find(state.selected); return i < 0 ? null : state.sections[i]; }

  function defaults(type) {
    switch (type) {
      case "hero": return { avatar: "sprout", name: state.username || "me", pronoun: "she/her", bio: "sticker artist & frog enjoyer 🌷" };
      case "links": return { links: [{ emoji: "🌷", title: "my sticker shop", url: "https://example.com/shop" }] };
      case "gallery": return { photos: [{ caption: "" }, { caption: "" }, { caption: "" }] };
      case "about": return { heading: "about me", body: "i draw tiny happy things and put them on everything." };
      case "socials": return { icons: "🦋 📸 🎬 🎵" };
      case "divider": return { motif: "sparkle" };
      case "embed": return { kind: "youtube", url: "https://youtu.be/" };
      case "signup": return { heading: "join my mail garden", button: "sign up", url: "https://example.com/newsletter" };
      case "form": return { heading: "say hi", button: "get in touch", url: "https://example.com/contact" };
      case "code": return { code: "<marquee>welcome to my page!!</marquee>" };
    }
    return {};
  }

  // ---- section renderer (canvas + phone preview) -------------------------
  function sectionInner(s) {
    var p = s.props, v = s.variant, ph;
    switch (s.type) {
      case "hero":
        return '<div class="hero-in"><div class="hero-avatar"><img src="/static/avatars/' + esc(p.avatar) + '.svg" alt=""></div>'
          + '<div class="hero-words"><p class="hero-name fred">' + esc(p.name) + "</p>"
          + (p.pronoun ? '<p class="hero-pronoun">' + esc(p.pronoun) + "</p>" : "")
          + (p.bio ? '<p class="hero-bio">' + esc(p.bio) + "</p>" : "") + "</div></div>";
      case "links":
        return '<div class="links-wrap lk-' + v + '">' + (p.links || []).map(function (l) {
          if (v === "buttons") return '<span class="lk-btn"><em>' + esc(l.emoji) + "</em><span>" + esc(l.title) + "</span></span>";
          if (v === "cards") return '<span class="lk-card"><em>' + esc(l.emoji) + '</em><span class="lk-t fred">' + esc(l.title) + '</span><span class="lk-u">' + esc(host(l.url)) + "</span></span>";
          return '<span class="lk-tile"><em>' + esc(l.emoji) + '</em><span class="lk-t fred">' + esc(l.title) + "</span></span>";
        }).join("") + "</div>";
      case "gallery":
        // Polaroid tilt is done with :nth-child in CSS (no inline style — the
        // dash CSP has no 'unsafe-inline').
        return '<div class="gal gal-' + v + '">' + (p.photos || []).map(function (g, i) {
          var inner = g.image
            ? '<div class="ph"><img src="/a/' + esc(g.image) + '" alt=""></div>'
            : '<div class="ph"><span class="ph-chip">photo ' + (i + 1) + "</span></div>";
          return '<figure class="gal-item">' + inner + (g.caption ? "<figcaption>" + esc(g.caption) + "</figcaption>" : "") + "</figure>";
        }).join("") + "</div>";
      case "about":
        return '<div class="about-in"><div class="about-words">'
          + (p.heading ? '<p class="sec-h fred">' + esc(p.heading) + "</p>" : "")
          + (p.body ? '<p class="about-body">' + esc(p.body) + "</p>" : "") + "</div>"
          + (v === "split" ? '<div class="about-photo"><div class="ph"><span class="ph-chip">a photo of you</span></div></div>' : "") + "</div>";
      case "socials":
        return '<div class="soc soc-' + v + '">' + String(p.icons || "").trim().split(/\s+/).filter(Boolean)
          .map(function (ic) { return '<span class="soc-i">' + esc(ic) + "</span>"; }).join("") + "</div>";
      case "divider":
        return v === "row"
          ? '<div class="div-row">' + motifSvg(p.motif, 20) + motifSvg(p.motif, 26) + motifSvg(p.motif, 20) + "</div>"
          : '<div class="div-line"><i></i>' + motifSvg(p.motif, 22) + "<i></i></div>";
      case "embed": {
        var yt = p.kind !== "spotify", gl = yt ? "▶" : "♪", cap = (yt ? "youtube" : "spotify") + " · " + host(p.url);
        return v === "card"
          ? '<div class="emb-card"><span class="emb-play sm">' + gl + '</span><span class="emb-cap">' + esc(cap) + "</span></div>"
          : '<div class="emb-full"><div class="emb-frame ' + (yt ? "yt" : "sp") + '"><span class="emb-play">' + gl + '</span></div><p class="emb-cap">' + esc(cap) + "</p></div>";
      }
      case "signup":
        return '<div class="su su-' + v + '"><p class="sec-h fred">' + esc(p.heading) + '</p><span class="minibtn fred">' + esc(p.button) + "</span></div>";
      case "form":
        return '<div class="form-card form-linkout"><p class="sec-h fred">' + esc(p.heading) + '</p><span class="minibtn fred">' + esc(p.button) + "</span></div>";
      case "code":
        return '<div class="code-card"><span class="code-chip">custom html · sandboxed</span><pre>' + esc(p.code) + "</pre></div>";
    }
    return "";
  }
  function sectionEl(s) {
    return h("div", { class: "sec sec-" + s.type + " v-" + s.variant, html: sectionInner(s) });
  }

  // ---- canvas ------------------------------------------------------------
  function tool(label, cls, title, onclick) {
    return h("button", { class: "tool " + (cls || ""), type: "button", title: title, "aria-label": title, text: label,
      onclick: function (e) { e.stopPropagation(); if (onclick) onclick(e); } });
  }
  function gap(index) {
    return h("div", { class: "sec-gap" }, [
      h("button", { class: "gap-add", type: "button", "aria-label": "add a section here", text: "+",
        onclick: function (e) { e.stopPropagation(); openDrawer(index); } })
    ]);
  }
  function dropLine() { return h("div", { class: "drop-line" }, [motifNode(), h("span", { text: "🌱" })]); }
  function motifNode() { var s = document.createElement("span"); s.innerHTML = motifSvg("sparkle", 18); return s; }

  function renderInto(container, editable) {
    container.textContent = "";
    if (!state.sections.length) {
      if (editable) {
        container.appendChild(h("div", { class: "site-empty" }, [
          h("p", { class: "fred", text: "a fresh little patch 🌱" }),
          h("p", { text: "add your first section below." }),
          h("div", { class: "add-row" }, [h("button", { class: "add-big", type: "button", text: "+ add a section", onclick: function () { openDrawer(0); } })])
        ]));
      }
      return;
    }
    state.sections.forEach(function (s, i) {
      if (editable && state.dragId && state.dropIndex === i) container.appendChild(dropLine());
      if (editable) container.appendChild(gap(i));
      var meta = TYPES[s.type];
      var wrap = h("div", { class: "sec-wrap" + (s._id === state.selected ? " on" : "") + (s._id === state.dragId ? " lifting" : "") }, [
        editable ? h("span", { class: "sec-tag", text: s.type }) : null,
        editable ? h("div", { class: "blk-tools" }, [
          grabTool(s._id),
          meta.variants.length > 1 ? tool("🎨", "", "next style", function () { cycleVariant(s); }) : null,
          tool("⧉", "", "duplicate", function () { duplicate(find(s._id)); }),
          tool("✕", "del", "remove", function () { remove(find(s._id)); })
        ]) : null,
        sectionEl(s)
      ]);
      if (editable) wrap.addEventListener("click", function () { select(s._id); });
      container.appendChild(wrap);
    });
    if (editable && state.dragId && state.dropIndex === state.sections.length) container.appendChild(dropLine());
    if (editable) {
      container.appendChild(gap(state.sections.length));
      container.appendChild(h("div", { class: "add-row" }, [
        h("button", { class: "add-big", type: "button", text: "+ add a section", onclick: function () { openDrawer(state.sections.length); } })
      ]));
    } else {
      container.appendChild(h("p", { class: "pub-credit", text: "made with 🥒 cutecumber" }));
    }
  }
  function renderCanvas() {
    renderInto(document.getElementById("b-site"), true);
    if (!document.getElementById("b-phonewrap").hidden) renderInto(document.getElementById("b-phonesite"), false);
  }

  // ---- mutations ---------------------------------------------------------
  function select(id) { state.selected = id; renderCanvas(); renderInspector(); }
  function cycleVariant(s) {
    var vs = TYPES[s.type].variants; var keys = vs.map(function (x) { return x[0]; });
    s.variant = keys[(keys.indexOf(s.variant) + 1) % keys.length];
    renderCanvas(); renderInspector(); scheduleSave();
  }
  function duplicate(idx) {
    var copy = JSON.parse(JSON.stringify(state.sections[idx])); copy._id = "s-" + (++state.counter);
    state.sections.splice(idx + 1, 0, copy); select(copy._id); scheduleSave();
  }
  function remove(idx) {
    var was = state.sections[idx]._id; state.sections.splice(idx, 1);
    if (state.selected === was) state.selected = null;
    renderCanvas(); renderInspector(); scheduleSave();
  }
  function addSection(type, index) {
    var s = { _id: "s-" + (++state.counter), type: type, variant: TYPES[type].variants[0][0], props: defaults(type) };
    if (index == null || index > state.sections.length) index = state.sections.length;
    state.sections.splice(index, 0, s);
    select(s._id); scheduleSave(); burstAtSelected();
  }

  // ---- drag to reorder ---------------------------------------------------
  function grabTool(id) {
    var b = h("button", { class: "tool grab", type: "button", title: "drag to reorder", "aria-label": "drag to reorder", text: "⠿" });
    b.addEventListener("click", function (e) { e.stopPropagation(); });
    b.addEventListener("pointerdown", function (e) { e.stopPropagation(); e.preventDefault(); startDrag(id, e); });
    // keyboard reorder fallback
    b.addEventListener("keydown", function (e) {
      var i = find(id);
      if (e.key === "ArrowUp" && i > 0) { e.preventDefault(); moveTo(i, i - 1); }
      else if (e.key === "ArrowDown" && i < state.sections.length - 1) { e.preventDefault(); moveTo(i, i + 1); }
    });
    return b;
  }
  function moveTo(from, to) {
    var s = state.sections.splice(from, 1)[0]; state.sections.splice(to, 0, s);
    renderCanvas(); scheduleSave();
  }
  function startDrag(id, e) {
    state.dragId = id; state.dropIndex = find(id);
    document.body.classList.add("is-dragging");
    ghost = h("div", { class: "drag-ghost" }, [h("div", { class: "ghost-sticker" }, [h("span", { text: "⠿ moving…" })])]);
    document.body.appendChild(ghost);
    moveGhost(e);
    document.addEventListener("pointermove", onDragMove);
    document.addEventListener("pointerup", endDrag, { once: true });
  }
  function moveGhost(e) { if (ghost) { ghost.style.left = e.clientX + "px"; ghost.style.top = e.clientY + "px"; } }
  function onDragMove(e) {
    moveGhost(e);
    var wraps = document.querySelectorAll("#b-site .sec-wrap");
    var idx = state.sections.length;
    for (var i = 0; i < wraps.length; i++) {
      var r = wraps[i].getBoundingClientRect();
      if (e.clientY < r.top + r.height / 2) { idx = i; break; }
    }
    if (idx !== state.dropIndex) { state.dropIndex = idx; renderCanvas(); }
  }
  function endDrag() {
    document.removeEventListener("pointermove", onDragMove);
    var from = find(state.dragId), to = state.dropIndex;
    if (ghost) { ghost.remove(); ghost = null; }
    document.body.classList.remove("is-dragging");
    if (from >= 0 && to != null) {
      if (to > from) to--;
      if (to !== from) { var s = state.sections.splice(from, 1)[0]; state.sections.splice(to, 0, s); scheduleSave(); }
    }
    state.dragId = null; state.dropIndex = null;
    renderCanvas();
  }

  // ---- persistence -------------------------------------------------------
  function serialize() { return state.sections.map(function (s) { return { id: s._id, type: s.type, variant: s.variant, props: s.props }; }); }
  function setStatus(m) { document.getElementById("b-save").textContent = m || ""; }
  function scheduleSave() { setStatus("saving…"); if (saveTimer) clearTimeout(saveTimer); saveTimer = setTimeout(save, 800); }
  function body() { var b = new FormData(); b.append("_csrf", state.csrf); b.append("sections", JSON.stringify({ version: 1, sections: serialize() })); return b; }
  function save() {
    return fetch("/dash/builder/save", { method: "POST", body: body() }).then(function (r) { return r.json(); })
      .then(function (d) { setStatus(d.ok ? "saved 🌱" : (d.error || "couldn't save 😔")); })
      .catch(function () { setStatus("offline — will retry"); });
  }
  function publish() {
    fetch("/dash/builder/publish", { method: "POST", body: body() }).then(function (r) { return r.json(); })
      .then(function (d) { setStatus(d.ok ? "published ✓" : (d.error || "couldn't publish 😔")); if (d.ok) root.dataset.published = "1"; });
  }

  // ---- inspector ---------------------------------------------------------
  function field(label, control) { return h("label", { class: "ins-field" }, [h("span", { text: label }), control]); }
  function textIn(val, oninput, ph, cls) { return h("input", { class: cls || "", type: "text", value: val || "", placeholder: ph || "", oninput: function (e) { oninput(e.target.value); } }); }
  function textArea(val, oninput, cls) { return h("textarea", { class: cls || "", rows: "3", oninput: function (e) { oninput(e.target.value); } }, [val || ""]); }
  function selectIn(opts, val, onchange) { return h("select", { onchange: function (e) { onchange(e.target.value); } }, opts.map(function (o) { return h("option", { value: o[0], selected: o[0] === val, text: o[1] }); })); }
  function commit() { renderCanvas(); scheduleSave(); }

  function renderInspector() {
    var box = document.getElementById("b-inspector"); box.textContent = "";
    var s = selected();
    if (!s) return renderPageInspector(box);
    var meta = TYPES[s.type];
    box.appendChild(h("div", { class: "ins-title fred" }, [motifNodeSized(meta.motif, 22), h("span", { text: meta.label })]));
    var bodyEl = h("div", { class: "ins-body" });
    // variant chips
    if (meta.variants.length > 1) {
      bodyEl.appendChild(h("div", { class: "chiprow" }, meta.variants.map(function (vp) {
        return h("button", { class: "chip" + (vp[0] === s.variant ? " on" : ""), type: "button", text: vp[1],
          onclick: function () { s.variant = vp[0]; renderCanvas(); renderInspector(); scheduleSave(); } });
      })));
    }
    fieldsFor(bodyEl, s);
    bodyEl.appendChild(h("div", { class: "ins-actions" }, [
      h("button", { class: "pill ghost", type: "button", text: "⧉ duplicate", onclick: function () { duplicate(find(s._id)); } }),
      h("button", { class: "pill danger", type: "button", text: "remove", onclick: function () { remove(find(s._id)); } })
    ]));
    box.appendChild(bodyEl);
  }
  function motifNodeSized(name, size) { var s = document.createElement("span"); s.innerHTML = '<svg viewBox="-16 -16 32 32" width="' + size + '" height="' + size + '" aria-hidden="true"><use href="#m-' + name + '"/></svg>'; return s; }

  function fieldsFor(box, s) {
    var p = s.props;
    if (s.type === "hero") {
      box.appendChild(field("avatar", avatarGrid(p.avatar, function (a) { p.avatar = a; commit(); })));
      box.appendChild(field("name", textIn(p.name, function (v) { p.name = v; commit(); })));
      box.appendChild(field("pronouns", textIn(p.pronoun, function (v) { p.pronoun = v; commit(); }, "optional")));
      box.appendChild(field("bio", textArea(p.bio, function (v) { p.bio = v; commit(); })));
    } else if (s.type === "links") {
      linkRows(box, s);
    } else if (s.type === "gallery") {
      photoRows(box, s);
    } else if (s.type === "about") {
      box.appendChild(field("heading", textIn(p.heading, function (v) { p.heading = v; commit(); })));
      box.appendChild(field("story", textArea(p.body, function (v) { p.body = v; commit(); })));
    } else if (s.type === "socials") {
      box.appendChild(field("icons (space-separated emoji)", textIn(p.icons, function (v) { p.icons = v; commit(); })));
    } else if (s.type === "divider") {
      box.appendChild(field("motif", motifPicker(p.motif, function (m) { p.motif = m; commit(); })));
    } else if (s.type === "embed") {
      box.appendChild(field("service", selectIn([["youtube", "youtube"], ["spotify", "spotify"]], p.kind, function (v) { p.kind = v; commit(); })));
      box.appendChild(field("link", textIn(p.url, function (v) { p.url = v; commit(); }, "https://youtu.be/…")));
    } else if (s.type === "signup" || s.type === "form") {
      box.appendChild(field("heading", textIn(p.heading, function (v) { p.heading = v; commit(); })));
      box.appendChild(field("button label", textIn(p.button, function (v) { p.button = v; commit(); })));
      box.appendChild(field(s.type === "signup" ? "link (your newsletter)" : "link (your form)", textIn(p.url, function (v) { p.url = v; commit(); }, "https://…")));
    } else if (s.type === "code") {
      box.appendChild(field("custom html + css — runs sandboxed (no scripts, no network)", textArea(p.code, function (v) { p.code = v; commit(); }, "ins-code")));
    }
  }
  function avatarGrid(cur, onpick) {
    return h("div", { class: "ins-avgrid" }, AVATARS.map(function (a) {
      return h("button", { class: "ins-av" + (a === cur ? " on" : ""), type: "button", onclick: function () { onpick(a); },
        html: '<img src="/static/avatars/' + a + '.svg" alt="' + a + '">' });
    }));
  }
  function motifPicker(cur, onpick) {
    return h("div", { class: "ins-motifs" }, MOTIFS.map(function (m) {
      return h("button", { class: "ins-motif" + (m === cur ? " on" : ""), type: "button", onclick: function () { onpick(m); }, html: motifSvg(m, 22) });
    }));
  }
  function linkRows(box, s) {
    if (!Array.isArray(s.props.links)) s.props.links = [];
    var list = h("div", { class: "rowlist" });
    s.props.links.forEach(function (l, i) {
      list.appendChild(h("div", { class: "rowitem" }, [
        h("input", { class: "ins-emoji", type: "text", value: l.emoji || "", placeholder: "🌷", oninput: function (e) { l.emoji = e.target.value; commit(); } }),
        h("div", { class: "rowmain" }, [
          textIn(l.title, function (v) { l.title = v; commit(); }, "title"),
          textIn(l.url, function (v) { l.url = v; commit(); }, "https://…")
        ]),
        tool("✕", "del", "remove link", function () { s.props.links.splice(i, 1); renderInspector(); commit(); })
      ]));
    });
    box.appendChild(field("links", list));
    box.appendChild(h("button", { class: "linkrow-add", type: "button", text: "+ add a link",
      onclick: function () { s.props.links.push({ emoji: "", title: "my link", url: "https://example.com" }); renderInspector(); commit(); } }));
  }
  function photoRows(box, s) {
    if (!Array.isArray(s.props.photos)) s.props.photos = [];
    var list = h("div", { class: "rowlist" });
    s.props.photos.forEach(function (pho, i) {
      var thumb = pho.image ? h("img", { class: "photo-thumb", src: "/a/" + pho.image, alt: "" }) : h("span", { class: "photo-thumb empty", "aria-hidden": "true", text: "📷" });
      var fileIn = h("input", { class: "photo-file", type: "file", accept: "image/*", onchange: function (e) { if (e.target.files[0]) uploadPhoto(e.target.files[0], pho); } });
      list.appendChild(h("div", { class: "photo-row" }, [
        thumb,
        h("label", { class: "photo-up" }, [pho.image ? "replace" : "upload", fileIn]),
        textIn(pho.caption, function (v) { pho.caption = v; commit(); }, "caption"),
        tool("✕", "del", "remove photo", function () { s.props.photos.splice(i, 1); renderInspector(); commit(); })
      ]));
    });
    box.appendChild(field("photos", list));
    box.appendChild(h("button", { class: "photo-add", type: "button", text: "+ add a photo",
      onclick: function () { s.props.photos.push({ caption: "" }); renderInspector(); commit(); } }));
  }
  function uploadPhoto(file, pho) {
    var b = new FormData(); b.append("_csrf", state.csrf); b.append("photo", file);
    setStatus("uploading…");
    fetch("/dash/builder/upload", { method: "POST", body: b }).then(function (r) { return r.json(); })
      .then(function (d) { if (!d.ok) { setStatus(d.error || "upload failed 😔"); return; } pho.image = d.filename; renderInspector(); commit(); })
      .catch(function () { setStatus("upload failed 😔"); });
  }

  function renderPageInspector(box) {
    box.appendChild(h("div", { class: "ins-title fred" }, [h("span", { text: "✿ page theme" })]));
    var bodyEl = h("div", { class: "ins-body" });
    bodyEl.appendChild(h("div", { class: "theme-grid" }, PRESETS.map(function (pr) {
      var locked = pr.premium && state.plan !== "sprout";
      // Swatch colors set via CSSOM (element.style.*), which CSP does NOT govern
      // — unlike inline style="" attributes, which the dash CSP blocks.
      var chip = h("span", { class: "theme-chip" });
      chip.style.background = pr.bg;
      var dot = h("span", { class: "theme-dot" });
      dot.style.background = pr.accent;
      chip.appendChild(dot);
      if (pr.premium) chip.appendChild(h("span", { class: "theme-lock", text: locked ? "🔒" : "🌱" }));
      return h("button", { class: "theme-pick" + (pr.key === state.preset ? " on" : "") + (locked ? " locked" : ""), type: "button",
        onclick: function () { locked ? openUpsell() : pickTheme(pr.key); } }, [
        chip, h("span", { class: "theme-name", text: pr.name })
      ]);
    })));
    bodyEl.appendChild(h("button", { class: "add-big ins-tplbtn", type: "button", text: "✨ start from a template…", onclick: openPicker }));
    bodyEl.appendChild(h("p", { class: "ins-note", text: "click any section on the page to edit it here." }));
    box.appendChild(bodyEl);
  }
  function pickTheme(key) {
    state.preset = key; renderInspector();
    var b = new FormData(); b.append("_csrf", state.csrf); b.append("preset", key);
    fetch("/dash/builder/preset", { method: "POST", body: b }).then(function (r) { return r.json(); })
      .then(function (d) { if (d.ok) { save().then(function () { location.reload(); }); } else { setStatus(d.error || "theme locked"); } });
  }

  // ---- drawer / picker / upsell / plan / phone ---------------------------
  function openDrawer(index) { state.addIndex = index; buildDrawer(); show("b-drawer"); }
  function buildDrawer() {
    var grid = document.getElementById("b-drawer-grid"); grid.textContent = "";
    ORDER.forEach(function (t) {
      var meta = TYPES[t], locked = meta.premium && state.plan !== "sprout";
      grid.appendChild(h("button", { class: "drawer-item" + (locked ? " locked" : ""), type: "button",
        onclick: function () { if (locked) { openUpsell(); return; } addSection(t, state.addIndex); hide("b-drawer"); } }, [
        meta.premium ? h("span", { class: "lock", text: locked ? "🔒" : "🌱" }) : null,
        h("span", { class: "drawer-emoji", html: '<svg viewBox="-16 -16 32 32" width="28" height="28" aria-hidden="true"><use href="#m-' + meta.motif + '"/></svg>' }),
        h("span", { class: "drawer-name", text: meta.label }),
        h("span", { class: "drawer-hint", text: meta.hint })
      ]));
    });
  }
  function buildPicker() {
    var grid = document.getElementById("b-picker-grid"); grid.textContent = "";
    TEMPLATES.forEach(function (t) {
      grid.appendChild(h("button", { class: "tpl-card" + (t.key === "blank" ? " blank" : ""), type: "button", onclick: function () { applyTemplate(t); } }, [
        h("span", { class: "tpl-name", text: t.name }), h("span", { class: "tpl-blurb", text: t.blurb })
      ]));
    });
  }
  function applyTemplate(t) {
    if (state.sections.length && !window.confirm("replace your current page with “" + t.name + "”?")) return;
    state.sections = (t.sections || []).map(function (s) { var c = JSON.parse(JSON.stringify(s)); c._id = "s-" + (++state.counter); return c; });
    state.selected = null; hide("b-picker"); renderCanvas(); renderInspector();
    if (t.preset) { pickTheme(t.preset); } else { scheduleSave(); }
  }
  function renderPlan() {
    var b = document.getElementById("b-plan");
    if (state.plan === "sprout") { b.textContent = "🌱 sprout member"; b.classList.add("member"); }
    else { b.textContent = "get sprout 🌱"; b.classList.remove("member"); }
  }
  function upgrade() {
    var b = new FormData(); b.append("_csrf", state.csrf); b.append("plan", "sprout");
    fetch("/dash/builder/plan", { method: "POST", body: b }).then(function (r) { return r.json(); })
      .then(function (d) { if (!d.ok) return; state.plan = d.plan; renderPlan(); hide("b-upsell"); renderInspector(); setStatus("sprout unlocked 🌱"); });
  }
  function togglePhone() {
    var pw = document.getElementById("b-phonewrap"), on = pw.hidden;
    pw.hidden = !on; document.getElementById("b-desktop").hidden = on;
    document.getElementById("b-phone").setAttribute("aria-pressed", on ? "true" : "false");
    document.getElementById("b-phone").classList.toggle("on", on);
    if (on) renderInto(document.getElementById("b-phonesite"), false);
  }

  function show(id) { document.getElementById(id).hidden = false; }
  function hide(id) { document.getElementById(id).hidden = true; }
  function openPicker() { buildPicker(); show("b-picker"); }
  function openUpsell() { show("b-upsell"); }

  // ---- sparkle burst -----------------------------------------------------
  function burstAtSelected() {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var el = document.querySelector("#b-site .sec-wrap.on"); if (!el) return;
    var r = el.getBoundingClientRect(); var box = h("div", { class: "burst" });
    for (var i = 0; i < 6; i++) { var sp = h("span", { text: "✦" }); sp.style.setProperty("--a", (i * 60) + "deg"); box.appendChild(sp); }
    box.style.left = (r.left + r.width / 2) + "px"; box.style.top = (r.top + r.height / 2) + "px";
    document.body.appendChild(box); setTimeout(function () { box.remove(); }, 700);
  }

  // ---- boot --------------------------------------------------------------
  function boot() {
    try { JSON.parse(root.dataset.pg || "{}"); } catch (e) {}
    var pg = {}; try { pg = JSON.parse(root.dataset.pg || "{}"); } catch (e) {}
    var sites = [document.getElementById("b-site"), document.getElementById("b-phonesite")];
    sites.forEach(function (site) { Object.keys(pg).forEach(function (k) { site.style.setProperty(k, pg[k]); }); });

    var draft; try { draft = JSON.parse(root.dataset.draft); } catch (e) { draft = { sections: [] }; }
    (draft.sections || []).forEach(function (s) { s._id = "s-" + (++state.counter); if (!s.props) s.props = {}; state.sections.push(s); });

    document.getElementById("b-publish").addEventListener("click", publish);
    document.getElementById("b-phone").addEventListener("click", togglePhone);
    document.getElementById("b-plan").addEventListener("click", openUpsell);
    document.getElementById("b-drawer-x").addEventListener("click", function () { hide("b-drawer"); });
    document.getElementById("b-picker-x").addEventListener("click", function () { hide("b-picker"); });
    document.getElementById("b-upsell-no").addEventListener("click", function () { hide("b-upsell"); });
    document.getElementById("b-upsell-yes").addEventListener("click", upgrade);
    ["b-drawer", "b-picker", "b-upsell"].forEach(function (id) {
      document.getElementById(id).addEventListener("click", function (e) { if (e.target.id === id) hide(id); });
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") { hide("b-drawer"); hide("b-picker"); hide("b-upsell"); } });

    renderPlan(); renderCanvas(); renderInspector();
    setStatus(root.dataset.published === "1" ? "" : "draft");
    if (!state.sections.length) openPicker();
  }
  boot();
})();
