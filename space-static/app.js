// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Kratos Innovation Labs Limited
//
// Svaram demo page on Hugging Face (static Space). English text goes to svaram.live's public API:
// /api/convey translates it and prepares it in segments, /api/speak turns each segment into MP3.
// The first segment plays while the next is fetched. Nothing is stored: no cookies, no storage,
// no analytics; the text exists only in this page and in the request to svaram.live.
(function () {
  "use strict";

  var API = "https://svaram.live";
  // Local testing only: http://localhost/...?api=http://127.0.0.1:8200
  if (/^(localhost|127\.0\.0\.1)$/.test(location.hostname)) {
    var q = new URLSearchParams(location.search).get("api");
    if (q) { API = q; }
  }
  var MAX_RETRIES = 3;

  var $ = function (id) { return document.getElementById(id); };
  var text = $("text"), lang = $("lang"), go = $("go"), shown = $("shown"), shownLabel = $("shown-label");
  var status = $("status"), player = $("player"), phrasesBox = $("phrases"), count = $("count");
  var LANGS = {}, run = null;

  function setStatus(msg, err) { status.textContent = msg || ""; status.className = "status" + (err ? " err" : ""); }

  function errorFor(code, waitS) {
    switch (code) {
      case "RATE_LIMITED": return "Too many requests in a short time. Please wait " + (waitS || 15) + " seconds.";
      case "ENGINE_BUSY": case "VOICE_UNAVAILABLE": return "Svaram is busy right now. Please try again in a moment.";
      case "TRANSLATE_UNAVAILABLE": return "Translation is not available right now. Please try again.";
      case "TEXT_EMPTY": return "Type something first.";
      case "TEXT_TOO_LONG": return "Please keep it under 300 characters.";
      case "OFFLINE": return "Could not reach svaram.live. Check your connection and try again.";
      case "NOTHING": return "Nothing here can be spoken in " + LANGS[lang.value].name + ". Type in English or in " + LANGS[lang.value].name + ".";
      case "PLAYBACK": return "This browser could not play the audio. Please try again.";
      default: return "Something went wrong. Nothing was spoken. Please try again.";
    }
  }

  function fail(code, extra) { var e = new Error(code); e.extra = extra || {}; return e; }

  function post(path, body, r) {
    return fetch(API + path, {
      method: "POST", mode: "cors", cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer",
      signal: r.ctrl.signal, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    }).catch(function () { throw fail(r.stopped ? "STOPPED" : "OFFLINE"); });
  }

  function readError(res) {
    return res.json().then(function (j) { return (j && j.error) || {}; }, function () { return {}; })
      .then(function (e) { if (res.status === 429 && !e.code) { e.code = "RATE_LIMITED"; } return e; });
  }

  function wait(ms, r) {
    return new Promise(function (ok) { setTimeout(ok, ms); }).then(function () { if (r.stopped) { throw fail("STOPPED"); } });
  }

  function postJson(path, body, r, attempt) {
    attempt = attempt || 0;
    return post(path, body, r).then(function (res) {
      if (res.ok) { return res.json(); }
      return readError(res).then(function (e) {
        var code = e.code || "HTTP_" + res.status;
        if ((code === "ENGINE_BUSY" || code === "TRANSLATE_UNAVAILABLE") && attempt < MAX_RETRIES) {
          setStatus("Busy, trying again…");
          return wait(e.retry_after_ms || 1500, r).then(function () { return postJson(path, body, r, attempt + 1); });
        }
        throw fail(code, e);
      });
    });
  }

  function fetchAudio(seg, r, attempt) {
    attempt = attempt || 0;
    return post("/api/speak", { text: seg, lang: r.lang, rate: 1.0 }, r).then(function (res) {
      if (res.ok) { return res.blob().then(function (b) { var u = URL.createObjectURL(b); r.urls.push(u); return u; }); }
      return readError(res).then(function (e) {
        var code = e.code || "HTTP_" + res.status;
        if ((code === "ENGINE_BUSY" || code === "VOICE_UNAVAILABLE") && attempt < MAX_RETRIES) {
          return wait(e.retry_after_ms || 1000, r).then(function () { return fetchAudio(seg, r, attempt + 1); });
        }
        throw fail(code, e);
      });
    });
  }

  function playUrl(url, r) {
    return new Promise(function (resolve, reject) {
      function done(fn, v) { player.onended = player.onerror = null; r.onStop = null; fn(v); }
      player.onended = function () { done(resolve); };
      player.onerror = function () { done(reject, fail("PLAYBACK")); };
      r.onStop = function () { done(reject, fail("STOPPED")); };
      player.src = url;
      var p = player.play();
      if (p && p.catch) { p.catch(function () { done(reject, fail(r.stopped ? "STOPPED" : "PLAYBACK")); }); }
    });
  }

  // Fetch segment i+1 while segment i plays.
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
        setStatus("Speaking in " + LANGS[r.lang].name + "…");
        return playUrl(url, r);
      }).then(next);
    }
    return next();
  }

  function finish(r, err) {
    if (run !== r) { return; }
    run = null;
    go.textContent = "Speak";
    r.urls.forEach(function (u) { URL.revokeObjectURL(u); });
    if (!err || err.message === "STOPPED") { setStatus(""); return; }
    var waitS = err.extra && err.extra.retry_after_ms ? Math.round(err.extra.retry_after_ms / 1000) : 15;
    setStatus(errorFor(err.message, waitS), true);
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

  // English (or the language itself) -> shown text + speech.
  function speak(input) {
    stop();
    input = (input || "").trim();
    if (!input) { setStatus(errorFor("TEXT_EMPTY"), true); return; }
    if (input.length > 300) { setStatus(errorFor("TEXT_TOO_LONG"), true); return; }
    var r = { lang: lang.value, ctrl: new AbortController(), urls: [], stopped: false, onStop: null };
    run = r;
    go.textContent = "Stop";
    shown.textContent = "";
    setStatus("Translating…");
    var note = "";
    postJson("/api/convey", { text: input, lang: r.lang }, r).then(function (p) {
      if (!p.ok && p.unspeakable) {
        note = "Some words can't be spoken in " + LANGS[r.lang].name + ", so they were left out. ";
        return postJson("/api/convey", { text: input, lang: r.lang, skip_unspeakable: true }, r);
      }
      return p;
    }).then(function (p) {
      shown.textContent = p.telugu || "";            // "telugu" holds the text in whichever language was asked
      if (!p.ok || !p.segments || !p.segments.length) { throw fail("NOTHING"); }
      if (p.translated && p.numbers_ok === false) { note += "Check the numbers: the translation may have changed them. "; }
      return speakSegments(p.segments, r);
    }).then(function () {
      finish(r, null);
      if (note) { setStatus(note); }
    }, function (err) { finish(r, err); });
  }

  function showLanguage() {
    var L = LANGS[lang.value];
    shownLabel.textContent = "In " + L.name;
    phrasesBox.innerHTML = "";
    L.phrases.forEach(function (p) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = p.english;
      b.title = p.text;
      b.addEventListener("click", function () { text.value = p.english; count.textContent = text.value.length; speak(p.text); });
      phrasesBox.appendChild(b);
    });
  }

  fetch("phrases.json", { cache: "no-cache" }).then(function (r) { return r.json(); }).then(function (data) {
    data.languages.forEach(function (L) {
      LANGS[L.code] = L;
      var o = document.createElement("option");
      o.value = L.code;
      o.textContent = L.native + "  " + L.name;
      lang.appendChild(o);
    });
    showLanguage();
  });

  lang.addEventListener("change", function () { stop(); shown.textContent = ""; showLanguage(); });
  text.addEventListener("input", function () { count.textContent = text.value.length; });
  text.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); speak(text.value); }
  });
  go.addEventListener("click", function () { if (run) { stop(); } else { speak(text.value); } });
})();
