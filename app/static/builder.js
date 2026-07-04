/* cutecumber page builder (STAGING). Vanilla, no framework, under the dash CSP
 * (script-src 'self'). Edits a DRAFT held in a JS state object; every change
 * debounce-autosaves to /dash/builder/save and reloads the live-preview iframe
 * (the real public template). Publish copies the draft to the live column.
 *
 * The public page stays 100% server-rendered and JS-free — this script only
 * ever runs inside the authenticated editor. */
(function () {
  "use strict";

  var AVATARS = ["berry", "blossom", "boo", "bun", "froggy", "matcha",
    "moonbeam", "riceball", "shroom", "sprout", "twinkle", "whiskers", "cutecumber"];
  var MOTIFS = ["sparkle", "sparklePink", "blossom", "heart", "bow", "leaf"];

  // Free, addable section types + their variants. Premium types are gated
  // server-side and have no editor yet.
  var TYPES = [
    { type: "hero", label: "hero", emoji: "👋", variants: ["centered", "split", "banner"] },
    { type: "links", label: "links", emoji: "🔗", variants: ["buttons", "cards", "tiles"] },
    { type: "gallery", label: "gallery", emoji: "🖼️", variants: ["three", "polaroid"] },
    { type: "about", label: "about", emoji: "📖", variants: ["simple", "note", "split"] },
    { type: "socials", label: "socials", emoji: "✨", variants: ["bubbles", "pill"] },
    { type: "divider", label: "divider", emoji: "🎀", variants: ["line", "row"] }
  ];
  // Premium (sprout-only) types. Server-gated; the editor lock is cosmetic.
  var PREMIUM = [
    { type: "embed", label: "embed", emoji: "🎬", variants: ["full", "card"] },
    { type: "signup", label: "mail list", emoji: "✉️", variants: ["band", "card"] },
    { type: "form", label: "form", emoji: "📝", variants: ["card"] },
    { type: "code", label: "custom html", emoji: "⌨️", variants: ["inert"] }
  ];
  var ALL = TYPES.concat(PREMIUM);
  function typeMeta(t) { for (var i = 0; i < ALL.length; i++) if (ALL[i].type === t) return ALL[i]; return null; }
  function isPremium(t) { for (var i = 0; i < PREMIUM.length; i++) if (PREMIUM[i].type === t) return true; return false; }

  // Starter templates (handoff §3). Each is a whole page + a theme preset.
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
    sections: [],
    selected: null,
    csrf: root.dataset.csrf,
    username: root.dataset.username,
    plan: root.dataset.plan,
    counter: 0
  };
  var saveTimer = null;

  function defaults(type) {
    switch (type) {
      case "hero": return { avatar: "sprout", name: state.username || "me" };
      case "links": return { links: [{ emoji: "", title: "my link", url: "https://example.com" }] };
      case "gallery": return { photos: [{ caption: "" }] };
      case "about": return { heading: "about", body: "a little story about me." };
      case "socials": return { icons: "🦋 📸" };
      case "divider": return { motif: "sparkle" };
      case "embed": return { kind: "youtube", url: "https://youtu.be/" };
      case "signup": return { heading: "join my mail garden", button: "sign up", url: "https://example.com/newsletter" };
      case "form": return { heading: "say hi", button: "get in touch", url: "https://example.com/contact" };
      case "code": return { code: "<!-- your html here -->" };
    }
    return {};
  }

  // ---- helpers -----------------------------------------------------------
  function h(tag, attrs, kids) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") el.className = attrs[k];
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

  // ---- serialization + persistence --------------------------------------
  function serialize() {
    return state.sections.map(function (s) {
      return { id: s._id, type: s.type, variant: s.variant, props: s.props };
    });
  }
  function setStatus(msg) { document.getElementById("b-save").textContent = msg || ""; }
  function scheduleSave() {
    setStatus("saving…");
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 800);
  }
  function post(url, onOk) {
    var body = new FormData();
    body.append("_csrf", state.csrf);
    body.append("sections", JSON.stringify({ version: 1, sections: serialize() }));
    return fetch(url, { method: "POST", body: body, headers: { "X-Requested-With": "fetch" } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) { setStatus(d.error || "couldn't save 😔"); return; }
        onOk(d);
      })
      .catch(function () { setStatus("offline — will retry on next change"); });
  }
  function save() {
    post("/dash/builder/save", function () { setStatus("saved 🌱"); reloadPreview(); });
  }
  function publish() {
    post("/dash/builder/publish", function (d) {
      setStatus("published ✓");
      root.dataset.published = "1";
      reloadPreview();
    });
  }
  function reloadPreview() {
    var f = document.getElementById("b-preview");
    try { f.contentWindow.location.reload(); } catch (e) { f.src = f.src; }
  }

  // ---- section list ------------------------------------------------------
  function renderList() {
    var ol = document.getElementById("b-sections");
    ol.textContent = "";
    if (!state.sections.length) {
      ol.appendChild(h("li", { class: "b-empty", text: "a fresh little patch 🌱 — add your first section below." }));
    }
    state.sections.forEach(function (s, idx) {
      var meta = typeMeta(s.type);
      var row = h("li", { class: "b-row" + (s._id === state.selected ? " sel" : "") }, [
        h("button", {
          class: "b-row-main", type: "button", onclick: function () { select(s._id); }
        }, [
          h("span", { class: "b-row-emoji", "aria-hidden": "true", text: meta ? meta.emoji : "▫" }),
          h("span", { class: "b-row-label", text: s.type }),
          h("span", { class: "b-row-variant", text: s.variant })
        ]),
        h("div", { class: "b-row-tools" }, [
          tool("↑", "move up", function () { move(idx, -1); }, idx === 0),
          tool("↓", "move down", function () { move(idx, 1); }, idx === state.sections.length - 1),
          meta && meta.variants.length > 1 ? tool("🎨", "next style", function () { cycleVariant(s); }) : null,
          tool("⧉", "duplicate", function () { duplicate(idx); }),
          tool("✕", "remove", function () { remove(idx); })
        ])
      ]);
      ol.appendChild(row);
    });
  }
  function tool(label, title, onclick, disabled) {
    return h("button", { class: "b-tool", type: "button", title: title, "aria-label": title, onclick: onclick, disabled: !!disabled, text: label });
  }

  function select(id) { state.selected = id; renderList(); renderInspector(); }
  function move(idx, dir) {
    var j = idx + dir; if (j < 0 || j >= state.sections.length) return;
    var t = state.sections[idx]; state.sections[idx] = state.sections[j]; state.sections[j] = t;
    renderList(); scheduleSave();
  }
  function duplicate(idx) {
    var copy = JSON.parse(JSON.stringify(state.sections[idx]));
    copy._id = "s-" + (++state.counter);
    state.sections.splice(idx + 1, 0, copy);
    select(copy._id); scheduleSave();
  }
  function remove(idx) {
    var was = state.sections[idx]._id;
    state.sections.splice(idx, 1);
    if (state.selected === was) state.selected = null;
    renderList(); renderInspector(); scheduleSave();
  }
  function cycleVariant(s) {
    var meta = typeMeta(s.type); var i = meta.variants.indexOf(s.variant);
    s.variant = meta.variants[(i + 1) % meta.variants.length];
    renderList(); renderInspector(); scheduleSave();
  }
  function addSection(type) {
    var meta = typeMeta(type);
    var s = { _id: "s-" + (++state.counter), type: type, variant: meta.variants[0], props: defaults(type) };
    state.sections.push(s);
    select(s._id); scheduleSave(); burstAtSelected();
  }

  // A little ✦ burst where a section just appeared (handoff §4.2). CSSOM styles
  // (not inline-style attributes) so the strict dash CSP is untouched; skipped
  // entirely for reduced-motion.
  function sparkleBurst(cx, cy) {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var box = h("div", { class: "b-burst" });
    for (var i = 0; i < 6; i++) {
      var ang = (Math.PI * 2 * i) / 6;
      var sp = h("span", { class: "b-spark", text: "✦" });
      sp.style.setProperty("--dx", (Math.cos(ang) * 42).toFixed(1) + "px");
      sp.style.setProperty("--dy", (Math.sin(ang) * 42).toFixed(1) + "px");
      box.appendChild(sp);
    }
    box.style.left = cx + "px"; box.style.top = cy + "px";
    document.body.appendChild(box);
    setTimeout(function () { box.remove(); }, 700);
  }
  function burstAtSelected() {
    var el = document.querySelector(".b-row.sel");
    if (!el) return;
    var r = el.getBoundingClientRect();
    sparkleBurst(r.left + r.width / 2, r.top + r.height / 2);
  }

  // ---- inspector ---------------------------------------------------------
  function renderInspector() {
    var box = document.getElementById("b-inspector");
    box.textContent = "";
    var s = selected();
    if (!s) {
      box.appendChild(h("p", { class: "b-hint", text: "pick a section above to edit it — or add one." }));
      return;
    }
    var meta = typeMeta(s.type);
    box.appendChild(h("h2", { class: "b-h", text: s.type }));
    // style chips
    box.appendChild(h("div", { class: "b-chips" }, meta.variants.map(function (v) {
      return h("button", {
        class: "b-vchip" + (v === s.variant ? " on" : ""), type: "button",
        text: v, onclick: function () { s.variant = v; renderList(); renderInspector(); scheduleSave(); }
      });
    })));
    if (s.type === "hero") heroFields(box, s);
    else if (s.type === "links") linksFields(box, s);
    else if (s.type === "gallery") galleryFields(box, s);
    else if (s.type === "about") aboutFields(box, s);
    else if (s.type === "socials") socialsFields(box, s);
    else if (s.type === "divider") dividerFields(box, s);
    else if (s.type === "embed") embedFields(box, s);
    else if (s.type === "signup") signupFields(box, s);
    else if (s.type === "form") formFields(box, s);
    else if (s.type === "code") codeFields(box, s);
  }
  function embedFields(box, s) {
    box.appendChild(field("service", selectInput(["youtube", "spotify"], s.props.kind, function (v) { s.props.kind = v; commit(); })));
    box.appendChild(field("link", textInput(s.props.url, function (v) { s.props.url = v; commit(); }, "https://youtu.be/…")));
  }
  function signupFields(box, s) {
    box.appendChild(field("heading", textInput(s.props.heading, function (v) { s.props.heading = v; commit(); })));
    box.appendChild(field("button label", textInput(s.props.button, function (v) { s.props.button = v; commit(); })));
    box.appendChild(field("link (your newsletter sign-up)", textInput(s.props.url, function (v) { s.props.url = v; commit(); }, "https://…")));
  }
  function formFields(box, s) {
    box.appendChild(field("heading", textInput(s.props.heading, function (v) { s.props.heading = v; commit(); })));
    box.appendChild(field("button label", textInput(s.props.button, function (v) { s.props.button = v; commit(); })));
    box.appendChild(field("link (your form)", textInput(s.props.url, function (v) { s.props.url = v; commit(); }, "https://…")));
  }
  function codeFields(box, s) {
    box.appendChild(field("custom html (shown as a safe preview)", textArea(s.props.code, function (v) { s.props.code = v; commit(); })));
  }

  function field(label, control) {
    return h("label", { class: "b-field" }, [h("span", { class: "b-flabel", text: label }), control]);
  }
  function textInput(val, oninput, ph) {
    return h("input", { class: "b-in", type: "text", value: val || "", placeholder: ph || "", oninput: function (e) { oninput(e.target.value); } });
  }
  function textArea(val, oninput) {
    return h("textarea", { class: "b-in b-ta", rows: "3", oninput: function (e) { oninput(e.target.value); } }, [val || ""]);
  }
  function selectInput(opts, val, onchange) {
    return h("select", { class: "b-in", onchange: function (e) { onchange(e.target.value); } },
      opts.map(function (o) { return h("option", { value: o, selected: o === val, text: o }); }));
  }
  function commit() { renderList(); scheduleSave(); }

  function heroFields(box, s) {
    box.appendChild(field("avatar", selectInput(AVATARS, s.props.avatar, function (v) { s.props.avatar = v; commit(); })));
    box.appendChild(field("name", textInput(s.props.name, function (v) { s.props.name = v; commit(); })));
    box.appendChild(field("pronouns", textInput(s.props.pronoun, function (v) { s.props.pronoun = v; commit(); }, "optional")));
    box.appendChild(field("bio", textArea(s.props.bio, function (v) { s.props.bio = v; commit(); })));
  }
  function aboutFields(box, s) {
    box.appendChild(field("heading", textInput(s.props.heading, function (v) { s.props.heading = v; commit(); })));
    box.appendChild(field("story", textArea(s.props.body, function (v) { s.props.body = v; commit(); })));
  }
  function socialsFields(box, s) {
    box.appendChild(field("icons (space-separated emoji)", textInput(s.props.icons, function (v) { s.props.icons = v; commit(); })));
  }
  function dividerFields(box, s) {
    box.appendChild(field("motif", selectInput(MOTIFS, s.props.motif, function (v) { s.props.motif = v; commit(); })));
  }
  function linksFields(box, s) {
    if (!Array.isArray(s.props.links)) s.props.links = [];
    var list = h("div", { class: "b-links" });
    s.props.links.forEach(function (lnk, i) {
      list.appendChild(h("div", { class: "b-linkrow" }, [
        h("input", { class: "b-in b-emoji", type: "text", value: lnk.emoji || "", placeholder: "🌷", oninput: function (e) { lnk.emoji = e.target.value; commit(); } }),
        textInput(lnk.title, function (v) { lnk.title = v; commit(); }, "title"),
        textInput(lnk.url, function (v) { lnk.url = v; commit(); }, "https://…"),
        h("button", { class: "b-tool", type: "button", "aria-label": "remove link", text: "✕", onclick: function () { s.props.links.splice(i, 1); renderInspector(); commit(); } })
      ]));
    });
    box.appendChild(field("links", list));
    box.appendChild(h("button", {
      class: "b-add-min", type: "button", text: "+ add a link",
      onclick: function () { s.props.links.push({ emoji: "", title: "my link", url: "https://example.com" }); renderInspector(); commit(); }
    }));
  }

  function galleryFields(box, s) {
    if (!Array.isArray(s.props.photos)) s.props.photos = [];
    var list = h("div", { class: "b-photos" });
    s.props.photos.forEach(function (ph, i) {
      var thumb = ph.image
        ? h("img", { class: "b-thumb", src: "/a/" + ph.image, alt: "" })
        : h("span", { class: "b-thumb b-thumb-empty", "aria-hidden": "true", text: "📷" });
      var fileInput = h("input", {
        class: "b-file", type: "file", accept: "image/*",
        onchange: function (e) { if (e.target.files[0]) uploadPhoto(e.target.files[0], ph); }
      });
      list.appendChild(h("div", { class: "b-photorow" }, [
        thumb,
        h("label", { class: "b-upload" }, [ph.image ? "replace" : "upload", fileInput]),
        textInput(ph.caption, function (v) { ph.caption = v; commit(); }, "caption"),
        h("button", {
          class: "b-tool", type: "button", "aria-label": "remove photo", text: "✕",
          onclick: function () { s.props.photos.splice(i, 1); renderInspector(); commit(); }
        })
      ]));
    });
    box.appendChild(field("photos", list));
    box.appendChild(h("button", {
      class: "b-add-min", type: "button", text: "+ add a photo",
      onclick: function () { s.props.photos.push({ caption: "" }); renderInspector(); commit(); }
    }));
  }
  function uploadPhoto(file, ph) {
    var body = new FormData();
    body.append("_csrf", state.csrf);
    body.append("photo", file);
    setStatus("uploading…");
    fetch("/dash/builder/upload", { method: "POST", body: body })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) { setStatus(d.error || "upload failed 😔"); return; }
        ph.image = d.filename; renderInspector(); commit();
      })
      .catch(function () { setStatus("upload failed 😔"); });
  }

  // ---- drawer ------------------------------------------------------------
  function buildDrawer() {
    var grid = document.getElementById("b-drawer-grid");
    grid.textContent = "";
    ALL.forEach(function (t) {
      var locked = isPremium(t.type) && state.plan !== "sprout";
      grid.appendChild(h("button", {
        class: "b-card" + (locked ? " locked" : ""), type: "button",
        onclick: function () {
          if (locked) { openUpsell(); return; }
          addSection(t.type); closeDrawer();
        }
      }, [
        h("span", { class: "b-card-emoji", "aria-hidden": "true", text: t.emoji }),
        h("span", { class: "b-card-name", text: t.label }),
        isPremium(t.type) ? h("span", { class: "b-lock", "aria-hidden": "true", text: locked ? "🔒" : "🌱" }) : null
      ]));
    });
  }
  function openDrawer() { buildDrawer(); document.getElementById("b-drawer").hidden = false; }
  function closeDrawer() { document.getElementById("b-drawer").hidden = true; }

  // ---- template picker ---------------------------------------------------
  function buildPicker() {
    var grid = document.getElementById("b-picker-grid");
    grid.textContent = "";
    TEMPLATES.forEach(function (t) {
      grid.appendChild(h("button", {
        class: "b-tpl" + (t.key === "blank" ? " blank" : ""), type: "button",
        onclick: function () { applyTemplate(t); }
      }, [
        h("span", { class: "b-tpl-name", text: t.name }),
        h("span", { class: "b-tpl-blurb", text: t.blurb })
      ]));
    });
  }
  function openPicker() { buildPicker(); document.getElementById("b-picker").hidden = false; }
  function closePicker() { document.getElementById("b-picker").hidden = true; }
  function applyTemplate(t) {
    if (state.sections.length && !window.confirm("replace your current page with “" + t.name + "”?")) return;
    state.sections = (t.sections || []).map(function (s) {
      var c = JSON.parse(JSON.stringify(s)); c._id = "s-" + (++state.counter); return c;
    });
    state.selected = null;
    renderList(); renderInspector();
    if (t.preset) setPreset(t.preset);
    closePicker();
    scheduleSave();
  }
  function setPreset(preset) {
    var body = new FormData(); body.append("_csrf", state.csrf); body.append("preset", preset);
    fetch("/dash/builder/preset", { method: "POST", body: body })
      .then(function (r) { return r.json(); })
      .then(function (d) { if (d.ok) reloadPreview(); });
  }

  // ---- premium plan / upsell --------------------------------------------
  function renderPlan() {
    var b = document.getElementById("b-plan");
    if (state.plan === "sprout") { b.textContent = "🌱 sprout member"; b.classList.add("member"); }
    else { b.textContent = "get sprout 🌱"; b.classList.remove("member"); }
  }
  function openUpsell() { document.getElementById("b-upsell").hidden = false; }
  function closeUpsell() { document.getElementById("b-upsell").hidden = true; }
  function upgrade() {
    var body = new FormData(); body.append("_csrf", state.csrf); body.append("plan", "sprout");
    fetch("/dash/builder/plan", { method: "POST", body: body })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) return;
        state.plan = d.plan; renderPlan(); closeUpsell();
        setStatus("sprout unlocked 🌱");
      });
  }

  // ---- phone toggle ------------------------------------------------------
  function togglePhone() {
    var b = document.getElementById("b-phone");
    var on = document.getElementById("b-frame").classList.toggle("phone");
    b.setAttribute("aria-pressed", on ? "true" : "false");
    b.classList.toggle("on", on);
  }

  // ---- boot --------------------------------------------------------------
  function boot() {
    var draft;
    try { draft = JSON.parse(root.dataset.draft); } catch (e) { draft = { sections: [] }; }
    (draft.sections || []).forEach(function (s) {
      s._id = "s-" + (++state.counter);
      if (!s.props) s.props = {};
      state.sections.push(s);
    });
    document.getElementById("b-add").addEventListener("click", openDrawer);
    document.getElementById("b-drawer-x").addEventListener("click", closeDrawer);
    document.getElementById("b-drawer").addEventListener("click", function (e) { if (e.target.id === "b-drawer") closeDrawer(); });
    document.getElementById("b-publish").addEventListener("click", publish);
    document.getElementById("b-phone").addEventListener("click", togglePhone);
    document.getElementById("b-templates").addEventListener("click", openPicker);
    document.getElementById("b-picker-x").addEventListener("click", closePicker);
    document.getElementById("b-picker").addEventListener("click", function (e) { if (e.target.id === "b-picker") closePicker(); });
    document.getElementById("b-plan").addEventListener("click", openUpsell);
    document.getElementById("b-upsell-no").addEventListener("click", closeUpsell);
    document.getElementById("b-upsell-yes").addEventListener("click", upgrade);
    document.getElementById("b-upsell").addEventListener("click", function (e) { if (e.target.id === "b-upsell") closeUpsell(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") { closeDrawer(); closePicker(); closeUpsell(); } });
    renderPlan();
    renderList();
    renderInspector();
    setStatus(root.dataset.published === "1" ? "" : "draft");
    if (!state.sections.length) openPicker();  // first-run: offer a starting point
  }
  boot();
})();
