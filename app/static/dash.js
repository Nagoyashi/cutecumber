/* cutecumber editor JS — the ONLY JavaScript in the product.
   Hard budget: 200 lines (PROJECT_STRUCTURE.md). Count before adding anything.
   Everything is progressive enhancement: with JS disabled, all CRUD still
   works — only drag-reordering and live-typing preview are lost.
   Public pages NEVER load this file or any script. */
"use strict";
(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) =>
    Array.from(root.querySelectorAll(selector));

  /* ---- confirm-before-destructive-action (opt in via data-confirm) ---- */
  document.addEventListener("submit", (event) => {
    const button = event.submitter;
    if (button && button.dataset.confirm && !window.confirm(button.dataset.confirm)) {
      event.preventDefault();
    }
  });

  /* ---- link reordering: pointer drag + arrow keys on the handle.
          Pointer Events cover mouse AND touch (HTML5 drag-and-drop does
          not work on touchscreens, and our people edit from phones).
          Changes batch in the DOM; the save button only appears when the
          order actually differs from what's saved. ---- */
  const list = $("#linklist");
  const orderForm = $("#order-form");
  if (list && orderForm) {
    const currentOrder = () =>
      $$("li[data-id]", list).map((li) => li.dataset.id).join(",");
    const savedOrder = currentOrder();
    const refreshDirty = () => {
      orderForm.hidden = currentOrder() === savedOrder;
    };

    orderForm.addEventListener("submit", () => {
      $("input[name=order]", orderForm).value = currentOrder();
    });

    let dragging = null;

    list.addEventListener("pointerdown", (event) => {
      const handle = event.target.closest(".drag");
      if (!handle) return;
      dragging = handle.closest("li");
      dragging.classList.add("dragging");
      // Capture on the LIST, never the handle: WebKit silently drops the
      // capture (and the pointerup with it) if the captured element moves
      // in the DOM mid-drag — which reordering does constantly. The list
      // itself never moves. Scroll suppression is touch-action in the CSS.
      list.setPointerCapture(event.pointerId);
      event.preventDefault(); // stop text selection on desktop
    });

    list.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      const next = $$("li[data-id]", list).find(
        (li) =>
          li !== dragging &&
          event.clientY < li.getBoundingClientRect().top + li.offsetHeight / 2
      );
      // Skip no-op mutations — fewer reflows, smoother drag on phones.
      if (next && next !== dragging.nextElementSibling) {
        list.insertBefore(dragging, next);
      } else if (!next && dragging !== list.lastElementChild) {
        list.appendChild(dragging);
      }
      refreshDirty(); // reveal the save button the moment order changes
    });

    const endDrag = () => {
      if (!dragging) return;
      dragging.classList.remove("dragging");
      dragging = null;
      refreshDirty();
    };
    list.addEventListener("pointerup", endDrag);
    list.addEventListener("pointercancel", endDrag);
    list.addEventListener("lostpointercapture", endDrag); // WebKit belt & braces

    list.addEventListener("keydown", (event) => {
      const handle = event.target.closest(".drag");
      if (!handle) return;
      const li = handle.closest("li");
      if (event.key === "ArrowUp" && li.previousElementSibling) {
        list.insertBefore(li, li.previousElementSibling);
      } else if (event.key === "ArrowDown" && li.nextElementSibling) {
        list.insertBefore(li.nextElementSibling, li);
      } else {
        return;
      }
      event.preventDefault();
      handle.focus(); // moving the row must not drop keyboard focus
      refreshDirty();
    });
  }

  /* ---- live preview: the dash embeds an iframe of the REAL public page
          (same origin) and we update its text nodes as the person types.
          The real renderer and real CSS do all the work; no script ever
          runs inside the public page itself. Avatar/theme/links update on
          save, when the page reloads the iframe fresh. ---- */
  const frame = $("#preview-frame");
  if (frame) {
    const wire = () => {
      const doc = frame.contentDocument;
      const h1 = doc && doc.querySelector("h1");
      if (!h1) return;

      // .pronouns / .bio only exist on the page when non-empty; create them
      // on demand in the iframe so typing into an empty field previews too.
      const ensure = (selector, className) => {
        let el = doc.querySelector(selector);
        if (!el) {
          el = doc.createElement("p");
          el.className = className;
          const anchor =
            className === "bio" ? doc.querySelector(".pronouns") || h1 : h1;
          anchor.insertAdjacentElement("afterend", el);
        }
        return el;
      };

      const bind = (inputId, getTarget, fallback = "") => {
        const input = document.getElementById(inputId);
        if (!input) return;
        input.addEventListener("input", () => {
          const value = input.value.trim() || fallback;
          const target = getTarget();
          target.textContent = value;
          target.hidden = !value;
        });
      };

      bind("display_name", () => h1, "@" + frame.dataset.username);
      bind("pronouns", () => ensure(".pronouns", "pronouns"));
      bind("bio", () => ensure(".bio", "bio"));
    };
    frame.addEventListener("load", wire);
  }
})();
