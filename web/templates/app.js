// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Kratos Innovation Labs Limited
// Svaram beta. Two modes, chosen by <body data-mode>:
//   speak   — type in /te/, /hi/, /ta/, /kn/, /ml/, /mr/, /bn/, /pa/, /as/, /gu/, /or/ or /doi/: spoken exactly as typed
//   convey  — home page: type English, tap the speaker: translated on Svaram's own server
//             into the language picked under "Svaram speaks", shown, and spoken
// Nothing you type is stored: no cookies, no analytics. The only things kept, on this device
// only, are the language you picked ("svaram.lang") and the last few you used ("svaram.recent").
// Text goes only to Svaram's own /api on this site, over HTTPS, and is not kept there.
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var MODE = document.body.getAttribute("data-mode") === "convey" ? "convey" : "speak";
  var msg = $("msg"), btn = $("speak"), statusEl = $("status"), player = $("player");
  var check = $("check"), checkText = $("check-text"), checkTitle = $("check-title");
  var teCard = $("te-card"), teText = $("te-text"), numWarn = $("num-warn");
  var MAX_RETRIES = 3;
  var PHRASE_VER = "{{phrase_version}}";
  var run = null;          // current run: {ctrl, stopped, urls, onStop}
  var unlocked = false;
  var lastSpans = [];
  var lastShown = "";      // convey mode: the translation the check panel refers to
  var pendingSegments = null;

  // Words shown in the page, per spoken language.
  var L = {{languages_js}};
  // Only live languages are listed; "All languages" is in English alphabetical order.
  var ORDER = Object.keys(L).sort(function (a, b) { return L[a].name < L[b].name ? -1 : 1; });
  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode: not remembered */ } }
  function read(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  var recent = [];
  try { recent = JSON.parse(read("svaram.recent") || "[]").filter(function (l) { return !!L[l]; }); } catch (e) { recent = []; }

  var LANG = L[document.body.getAttribute("data-lang")] ? document.body.getAttribute("data-lang") : "te";
  if (MODE === "convey") {
    // ?speak=ta (QR posters) > the choice made on this device > the phone's own language > Telugu
    var asked = (/[?&]speak=([a-z]{2})/.exec(location.search) || [])[1];
    var saved = read("svaram.lang");
    var phone = (navigator.languages || [navigator.language || ""]).map(function (x) { return String(x).slice(0, 2).toLowerCase(); })
      .filter(function (x) { return !!L[x]; })[0];
    LANG = L[asked] ? asked : L[saved] ? saved : phone || "te";
    if (L[asked]) { store("svaram.lang", asked); }
  }
  function remember(l) {
    recent = [l].concat(recent.filter(function (x) { return x !== l; })).slice(0, 3);
    store("svaram.recent", JSON.stringify(recent));
  }
  function T() { return L[LANG]; }
  function span(lang, t) { return '<span lang="' + lang + '">' + t + "</span>"; }

  // Same clean-up as the server (NFC, drop control characters except tab/newline).
  function clean(t) {
    return (t || "").normalize("NFC").replace(/[\u0000-\u0008\u000B-\u001F\u007F-\u009F]/g, "");
  }

  function setStatus(t, isErr) {
    statusEl.textContent = t || "";
    statusEl.className = "status" + (isErr === "wait" ? " wait" : isErr ? " err" : "");
  }

  // s300-030 (design 26.16, wireframe 12): over the server's limit -> one notice, a countdown on the button,
  // the typed message kept, quick phrases still working. The notice is announced once, not every second.
  var coolUntil = 0, coolTimer = null, lastWait = 15;
  function startCooldown(sec) {
    sec = Math.max(3, Math.min(120, sec || 15));
    coolUntil = Date.now() + sec * 1000;
    btn.classList.add("cool");
    btn.setAttribute("aria-disabled", "true");
    setStatus("Too many requests in a short time. Please wait " + sec + " seconds. · " + T().busy + " · " + sec, "wait");
    if (coolTimer) { clearInterval(coolTimer); }
    function tick() {
      var left = Math.ceil((coolUntil - Date.now()) / 1000);
      if (left <= 0) {
        clearInterval(coolTimer); coolTimer = null; coolUntil = 0;
        btn.classList.remove("cool"); btn.removeAttribute("aria-disabled");
        btn.setAttribute("aria-label", idleAria());
        $("speak-label").innerHTML = idleLabel();
        if (statusEl.classList.contains("wait")) { setStatus(""); }
        return;
      }
      btn.setAttribute("aria-label", idleAria() + ", available in " + left + " seconds");
      $("speak-label").innerHTML = span("en", "Speak again in " + left + " s") + " · " + span(LANG, T().busy);
    }
    tick();
    coolTimer = setInterval(tick, 1000);
  }

  function idleLabel() {
    return MODE === "convey" ? "Speak in " + T().name + " · " + span(LANG, T().speak)
                             : span("en", "Speak") + " · " + span(LANG, T().speak);
  }
  function idleAria() { return MODE === "convey" ? "Translate and speak in " + T().name : "Speak this message"; }

  function setBusy(on) {
    btn.classList.toggle("busy", on);
    btn.setAttribute("aria-label", on ? "Stop speaking" : idleAria());
    $("speak-label").innerHTML = on ? span("en", "Stop") + " · " + span(LANG, T().stop) : idleLabel();
  }

  function updateCount() { $("count").textContent = msg.value.length + " / 500"; }

  function hideCheck() {
    check.hidden = true;
    msg.classList.remove("has-issue");
    lastSpans = [];
  }

  function hideShown() {
    if (teCard) { teCard.hidden = true; teText.textContent = ""; if (numWarn) { numWarn.hidden = true; } }
    pendingSegments = null;
  }

  var teNote = teCard ? teCard.querySelector(".te-note") : null;
  var teLabel = teCard ? teCard.querySelector(".te-label") : null;
  var teLabelHtml = teLabel ? teLabel.innerHTML : "";

  // machine: true for a translation (shows the beta note), false for a reviewed quick phrase.
  function showText(t, machine) {
    if (!teCard) { return; }
    teText.textContent = t;
    teText.setAttribute("lang", LANG);
    if (teNote && teNote.textContent.trim()) { teNote.hidden = !machine; }
    if (teLabel) { teLabel.innerHTML = machine ? teLabelHtml : teLabelHtml + " · quick phrase"; applyLang(); }
    teCard.hidden = false;
  }

  function showCheck(text, spans) {
    lastSpans = spans;
    checkText.textContent = "";
    checkText.setAttribute("lang", LANG);
    var pos = 0, words = [];
    spans.forEach(function (s) {
      checkText.appendChild(document.createTextNode(text.slice(pos, s[0])));
      var m = document.createElement("mark");
      m.textContent = text.slice(s[0], s[1]);
      checkText.appendChild(m);
      words.push("“" + text.slice(s[0], s[1]) + "”");
      pos = s[1];
    });
    checkText.appendChild(document.createTextNode(text.slice(pos)));
    var shown = words.slice(0, 3).join(", ");
    if (words.length > 3) { shown += " and " + (words.length - 3) + " more"; }
    checkTitle.textContent = "The voice cannot say " + shown + ".";
    var help = $("check-help") || check.querySelector(".check-help");
    if (help) {
      help.textContent = MODE === "convey"
        ? "Change those words in your message and try again, or speak the rest without them."
        : "Type it in " + T().name + " letters, or speak the rest without it.";
    }
    check.hidden = false;
    msg.classList.add("has-issue");
  }

  function unlock() {
    // iOS only lets audio play later if something plays inside the tap itself.
    if (unlocked) { return; }
    unlocked = true;
    try {
      player.src = "/silence.mp3";
      var p = player.play();
      if (p && p.then) { p.then(function () { player.pause(); }, function () {}); }
    } catch (e) { /* ignore */ }
  }

  function wait(ms, r) {
    return new Promise(function (ok) { setTimeout(ok, ms); }).then(function () {
      if (r.stopped) { throw new Error("STOPPED"); }
    });
  }

  function errorFor(code) {
    switch (code) {
      case "RATE_LIMITED": return "Too many requests in a short time. Please wait a few seconds.";
      case "ENGINE_BUSY": case "VOICE_UNAVAILABLE": return "Svaram is busy right now. Please try again in a moment.";
      case "TRANSLATE_UNAVAILABLE": return "Translation is not available right now. Nothing was spoken. Please try again.";
      case "TEXT_TOO_LONG": return "The message is too long. Please keep it under 500 letters.";
      case "OFFLINE": return "No connection. Check your internet and try again.";
      default: return "Something went wrong. Nothing was spoken. Please try again.";
    }
  }

  function post(path, body, r) {
    return fetch(path, {
      method: "POST", cache: "no-store", credentials: "omit", signal: r.ctrl.signal,
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    }).catch(function () {
      if (r.stopped) { throw new Error("STOPPED"); }
      throw new Error("OFFLINE");
    });
  }

  function readError(res) {
    if (res.status === 429) {
      lastWait = parseInt(res.headers.get("Retry-After") || "", 10) || 15;
      return Promise.resolve({ code: "RATE_LIMITED" });
    }
    return res.json().then(function (j) { return (j && j.error) || {}; }, function () { return {}; });
  }

  // POST returning JSON, retrying a busy engine a few times.
  function postJson(path, body, r, attempt) {
    attempt = attempt || 0;
    return post(path, body, r).then(function (res) {
      if (res.ok) { return res.json(); }
      return readError(res).then(function (e) {
        var code = e.code || "HTTP_" + res.status;
        if (code === "ENGINE_BUSY" && attempt < MAX_RETRIES) {
          setStatus("Busy, trying again… · " + r.t.busy);
          return wait(e.retry_after_ms || 1500, r).then(function () { return postJson(path, body, r, attempt + 1); });
        }
        throw new Error(code);
      });
    });
  }

  // One segment -> object URL of its audio. Retries a busy voice a few times.
  function fetchAudio(seg, r, attempt) {
    attempt = attempt || 0;
    return post("/api/speak", { text: seg, lang: r.lang }, r).then(function (res) {
      if (res.ok) { return res.blob().then(function (b) { var u = URL.createObjectURL(b); r.urls.push(u); return u; }); }
      return readError(res).then(function (e) {
        var code = e.code || "HTTP_" + res.status;
        if ((code === "ENGINE_BUSY" || code === "VOICE_UNAVAILABLE") && attempt < MAX_RETRIES) {
          if (attempt === 0) { setStatus("Busy, trying again… · " + r.t.busy); }
          return wait(e.retry_after_ms || 1000, r).then(function () { return fetchAudio(seg, r, attempt + 1); });
        }
        throw new Error(code);
      });
    });
  }

  function playUrl(url, r) {
    return new Promise(function (resolve, reject) {
      function done(fn, v) {
        player.removeEventListener("ended", onEnd);
        player.removeEventListener("error", onErr);
        r.onStop = null;
        fn(v);
      }
      function onEnd() { done(resolve); }
      function onErr() { done(reject, new Error("PLAYBACK")); }
      player.addEventListener("ended", onEnd);
      player.addEventListener("error", onErr);
      r.onStop = function () { done(reject, new Error("STOPPED")); };
      player.src = url;
      var p = player.play();
      if (p && p.catch) { p.catch(function () { done(reject, new Error(r.stopped ? "STOPPED" : "PLAYBACK")); }); }
    });
  }

  // Fetch segment i+1 while segment i plays; the first one is short, so sound starts fast.
  function speakSegments(segs, r) {
    var pending = [];
    function get(i) {
      if (!pending[i]) {
        pending[i] = (i === 0 ? Promise.resolve() : get(i - 1).catch(function () {}))
          .then(function () { return fetchAudio(segs[i], r); });
        pending[i].catch(function () {});
      }
      return pending[i];
    }
    var i = 0;
    function next() {
      if (i >= segs.length) { return Promise.resolve(); }
      var me = i++;
      return get(me).then(function (url) {
        if (me + 1 < segs.length) { get(me + 1); }
        setStatus((MODE === "convey" ? "Speaking in " + r.t.name + "… · " : "Speaking… · ") + r.t.speaking);
        return playUrl(url, r);
      }).then(next);
    }
    return next();
  }

  function clearChips() {
    Array.prototype.forEach.call(document.querySelectorAll(".qp.on"), function (b) { b.classList.remove("on"); });
  }

  function finish(r, err) {
    if (run !== r) { return; }
    run = null;
    setBusy(false);
    clearChips();
    r.urls.forEach(function (u) { URL.revokeObjectURL(u); });
    if (!err || err.message === "STOPPED") { setStatus(""); return; }
    if (err.message === "RATE_LIMITED") { startCooldown(lastWait); return; }
    setStatus(err.message === "PLAYBACK" ? "This browser could not play the audio. Please try again."
                                         : errorFor(err.message), true);
  }

  function stop() {
    if (!run) { return; }
    var r = run;
    r.stopped = true;
    try { r.ctrl.abort(); } catch (e) { /* old browsers */ }
    try { player.pause(); } catch (e) { /* ignore */ }
    if (r.onStop) { r.onStop(); }
    finish(r, null);
  }

  // A run keeps the language it started with, even if the switch changes meanwhile.
  function newRun() {
    var r = { ctrl: new AbortController(), stopped: false, urls: [], onStop: null, lang: LANG, t: T() };
    run = r;
    setBusy(true);
    return r;
  }

  function speakNow(segs, lang) {
    unlock();
    var r = newRun();
    r.lang = lang; r.t = L[lang];
    if (numWarn) { numWarn.hidden = true; }
    speakSegments(segs, r).then(function () { finish(r, null); }).catch(function (e) { finish(r, e); });
  }

  // ---- speak mode: Telugu or Hindi typed, spoken as typed
  function startSpeak(skip) {
    var text = clean(msg.value);
    if (!text.trim()) {
      setStatus("Type something first · " + T().first, true);
      msg.focus();
      return;
    }
    unlock();
    hideShown();
    var r = newRun();
    setStatus("Getting ready… · " + r.t.ready);
    postJson("/api/prepare", { text: text, skip_unspeakable: !!skip, lang: r.lang }, r).then(function (p) {
      if (r.stopped) { throw new Error("STOPPED"); }
      if (!p.ok && p.unspeakable) { showCheck(text, p.unspeakable); finish(r, null); return null; }
      if (!p.ok) { finish(r, null); setStatus("There is nothing the voice can say in this message.", true); return null; }
      hideCheck();
      return speakSegments(p.segments, r).then(function () { finish(r, null); });
    }).catch(function (e) { finish(r, e); });
  }

  // ---- convey mode: English typed, translated, shown, spoken
  var pendingLang = LANG;
  function startConvey() {
    var text = clean(msg.value);
    if (!text.trim()) {
      setStatus("Type your message first.", true);
      msg.focus();
      return;
    }
    unlock();
    hideCheck(); hideShown();
    var r = newRun();
    setStatus("Translating… · " + r.t.translating);
    postJson("/api/convey", { text: text, lang: r.lang }, r).then(function (p) {
      if (r.stopped) { throw new Error("STOPPED"); }
      lastShown = p.telugu || "";            // the API keeps this key name for every language
      if (lastShown) { showText(lastShown, !!p.translated); }
      if (!p.ok && p.unspeakable) { showCheck(lastShown, p.unspeakable); finish(r, null); return null; }
      if (!p.ok) { finish(r, null); setStatus("There is nothing the voice can say in this message.", true); return null; }
      if (p.numbers_ok === false) {          // never speak changed numbers without a second look
        pendingSegments = p.segments; pendingLang = r.lang;
        numWarn.hidden = false;
        finish(r, null);
        setStatus("Check the numbers in the " + r.t.name + " before speaking.", true);
        return null;
      }
      return speakSegments(p.segments, r).then(function () { finish(r, null); });
    }).catch(function (e) { finish(r, e); });
  }

  // "Speak the rest" in convey mode: prepare the shown translation, leaving out what it cannot say.
  function conveyRest() {
    unlock();
    var r = newRun();
    postJson("/api/prepare", { text: lastShown, skip_unspeakable: true, lang: r.lang }, r).then(function (p) {
      if (!p.ok) { finish(r, null); setStatus("There is nothing the voice can say in this message.", true); return null; }
      hideCheck();
      return speakSegments(p.segments, r).then(function () { finish(r, null); });
    }).catch(function (e) { finish(r, e); });
  }

  // ---- language: labels, chips and the switch (home page only has the switch)
  function applyLang() {
    var t = T();
    document.body.setAttribute("data-lang", LANG);
    Array.prototype.forEach.call(document.querySelectorAll(".L-name"), function (e) { e.textContent = t.name; });
    Array.prototype.forEach.call(document.querySelectorAll(".L-native"), function (e) { e.textContent = t.native; e.setAttribute("lang", LANG); });
    renderRecent();
    if (MODE === "convey") {
      Array.prototype.forEach.call(document.querySelectorAll(".qp"), function (b) {
        var sub = b.querySelector(".qp-te");
        if (sub) { sub.textContent = b.getAttribute("data-" + LANG); sub.setAttribute("lang", LANG); }
      });
      var link = $("type-native");
      if (link) { link.href = t.page; link.innerHTML = t.typeHere + span(LANG, t.typeNative); }
    }
    if (!run) { setBusy(false); }
  }

  function setLang(l) {
    if (!L[l]) { return; }
    if (l !== LANG) {
      if (run) { stop(); }
      var prev = LANG;
      LANG = l;
      if (recent.indexOf(prev) < 0) { remember(prev); }
      hideCheck(); hideShown(); setStatus("");
    }
    store("svaram.lang", l);
    remember(l);
    applyLang();
  }

  // ---- language picker : button + two recent pills + a sheet of tiles
  var langBtn = $("lang-btn"), recentBox = $("lang-recent"), sheet = $("lang-sheet");
  function others() {                                // the two other languages for one-tap pills
    var r = recent.filter(function (l) { return l !== LANG; });
    ["te", "hi"].concat(ORDER).forEach(function (l) { if (l !== LANG && r.indexOf(l) < 0) { r.push(l); } });
    return r.slice(0, 2);
  }
  function renderRecent() {
    if (!recentBox) { return; }
    recentBox.textContent = "";
    others().forEach(function (l) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "lang-pill"; b.lang = l; b.textContent = L[l].native;
      b.setAttribute("aria-label", "Switch to " + L[l].name);
      b.addEventListener("click", function () { setLang(l); });
      recentBox.appendChild(b);
    });
  }
  function tile(l) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "tile"; b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", l === LANG ? "true" : "false");
    var n = document.createElement("span"); n.className = "t-native"; n.lang = l; n.textContent = L[l].native;
    var e = document.createElement("span"); e.className = "t-en"; e.textContent = L[l].name;
    b.appendChild(n); b.appendChild(e);
    b.addEventListener("click", function () { setLang(l); closeSheet(); });
    return b;
  }
  function fill(box, list) {
    box.textContent = "";
    list.forEach(function (l) { box.appendChild(tile(l)); });
  }
  var sheetHistory = false;
  function openSheet() {
    if (!sheet) { return; }
    var rec = [LANG].concat(recent.filter(function (l) { return l !== LANG; })).slice(0, 3);
    fill($("tiles-recent"), rec);
    $("tiles-recent").hidden = $("sheet-recent-label").hidden = rec.length < 2;   // nothing recent yet: just the list
    fill($("tiles-all"), ORDER);
    if (typeof sheet.showModal === "function") { sheet.showModal(); } else { sheet.setAttribute("open", ""); }
    try { history.pushState({ svaramSheet: 1 }, ""); sheetHistory = true; } catch (e) { sheetHistory = false; }
    var cur = sheet.querySelector('.tile[aria-checked="true"]');
    if (cur) { cur.focus(); }
  }
  function closeSheet(fromBack) {
    if (!sheet || !sheet.hasAttribute("open")) { return; }
    if (typeof sheet.close === "function") { sheet.close(); } else { sheet.removeAttribute("open"); }
    if (sheetHistory && !fromBack) { sheetHistory = false; try { history.back(); } catch (e) { /* ignore */ } }
    sheetHistory = false;
    if (langBtn) { langBtn.focus(); }
  }
  if (langBtn && sheet) {
    langBtn.addEventListener("click", openSheet);
    $("sheet-close").addEventListener("click", function () { closeSheet(); });
    sheet.addEventListener("cancel", function (ev) { ev.preventDefault(); closeSheet(); });     // Escape
    sheet.addEventListener("click", function (ev) { if (ev.target === sheet) { closeSheet(); } }); // tap outside
    window.addEventListener("popstate", function () { if (sheet.hasAttribute("open")) { closeSheet(true); } });  // phone back button
    sheet.addEventListener("keydown", function (ev) {                                          // arrows move between tiles
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].indexOf(ev.key) < 0) { return; }
      var tiles = Array.prototype.slice.call(sheet.querySelectorAll(".tile"));
      var i = tiles.indexOf(document.activeElement);
      if (i < 0) { return; }
      ev.preventDefault();
      var step = ev.key === "ArrowLeft" || ev.key === "ArrowUp" ? -1 : 1;
      tiles[(i + step + tiles.length) % tiles.length].focus();
    });
  }

  btn.addEventListener("click", function () {
    if (run) { stop(); return; }
    if (Date.now() < coolUntil) { return; }                // waiting out the limit
    if (MODE === "convey") { startConvey(); } else { startSpeak(false); }
  });
  $("rest").addEventListener("click", function () {
    if (run) { stop(); }
    if (MODE === "convey") { conveyRest(); } else { startSpeak(true); }
  });
  $("fix").addEventListener("click", function () {
    msg.focus();
    if (MODE === "speak" && lastSpans[0]) {
      try { msg.setSelectionRange(lastSpans[0][0], lastSpans[0][1]); } catch (e) { /* ignore */ }
    }
  });
  if ($("anyway")) {
    $("anyway").addEventListener("click", function () {
      if (pendingSegments) { var s = pendingSegments; pendingSegments = null; speakNow(s, pendingLang); }
    });
  }
  msg.addEventListener("input", function () {
    updateCount();
    if (!check.hidden) { hideCheck(); }
    if (teCard && !teCard.hidden && !run) { hideShown(); }
    if (statusEl.classList.contains("err")) { setStatus(""); }
  });

  // ---- quick phrases: reviewed wording, audio made once at install, no translation
  var qpMore = $("qp-more");
  if (qpMore) {
    qpMore.addEventListener("click", function () {
      var open = qpMore.getAttribute("aria-expanded") !== "true";
      Array.prototype.forEach.call(document.querySelectorAll(".qp[data-extra]"), function (b) { b.hidden = !open; });
      qpMore.setAttribute("aria-expanded", open ? "true" : "false");
      qpMore.textContent = open ? qpMore.getAttribute("data-less") : qpMore.getAttribute("data-more");
    });
  }
  Array.prototype.forEach.call(document.querySelectorAll(".qp"), function (b) {
    b.addEventListener("click", function () {
      var wasOn = b.classList.contains("on");
      if (run) { stop(); }
      if (wasOn) { return; }                       // tapping the playing phrase stops it
      unlock();
      hideCheck(); hideShown();
      showText(b.getAttribute("data-" + LANG), false);
      var r = newRun();
      b.classList.add("on");
      setStatus("Speaking… · " + r.t.speaking);
      playUrl("/phrases/" + r.lang + "/" + b.getAttribute("data-id") + ".mp3?v=" + PHRASE_VER, r)
        .then(function () { finish(r, null); })
        .catch(function (e) { finish(r, e); });
    });
  });

  if (MODE === "convey") { remember(LANG); }
  applyLang();
  updateCount();
})();
