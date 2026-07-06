/* Click-to-load embeds — the ONLY JavaScript that ever loads on a public page,
 * and only on pages that contain a youtube/spotify embed (documented RULES.md
 * exception; see security.py _EMBED_CSP). It makes NO network request itself:
 * it swaps the server-rendered facade for the real iframe on the visitor's
 * click, so no third-party request fires until they ask for it. With JS off,
 * the facade is a plain link-out and this file never runs. */
(function () {
  "use strict";
  var facades = document.querySelectorAll("a.emb[data-embed]");
  for (var i = 0; i < facades.length; i++) {
    (function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        var f = document.createElement("iframe");
        f.className = "emb-frame";
        f.src = a.getAttribute("data-embed");
        f.title = "embedded media";
        f.setAttribute("loading", "lazy");
        f.setAttribute("referrerpolicy", "no-referrer");
        f.setAttribute("allow", "autoplay; encrypted-media; picture-in-picture; clipboard-write");
        f.setAttribute("allowfullscreen", "");
        a.replaceWith(f);
      });
    })(facades[i]);
  }
})();
