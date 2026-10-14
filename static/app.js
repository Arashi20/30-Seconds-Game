"use strict";

// ---------- UI text (interface language, separate from the word deck language) ----------
const STRINGS = {
  en: {
    yourName: "Your name", joinRoom: "Join a game", roomCode: "Room code", join: "Join",
    newGame: "Start a new game", wordLanguage: "Word language", teams: "Teams",
    target: "Points to win", create: "Create room", howToPlay: "How to play",
    rulesText:
      "Split into teams. Each turn one player is the describer: they see 5 words and have 30 seconds to make their team guess as many as possible — without saying the word itself.\n\n" +
      "The describer taps every word their team guesses. Before the turn a die is rolled (0, 1 or 2) — that many points are subtracted from the turn's score.\n\n" +
      "Teams take turns and the describer rotates. The first team to reach the finish wins!",
    shareLink: "Share invite link", pickTeam: "Tap a team to join it", shuffle: "Shuffle teams",
    startGame: "Start game", waitHost: "Waiting for the host to start…", team: "Team",
    you: "you", host: "host", describer: "Describer", yourTurn: "You're describing!",
    teamTurn: (t, n) => `${t} — ${n} is describing`, guessing: "Guess! Your teammate is describing.",
    watching: "Watch the words — no cheating!", die: "Die", minus: (d) => `−${d} point${d === 1 ? "" : "s"} this turn`,
    startTimer: "Start 30 seconds", waitDescriber: (n) => `Waiting for ${n} to start…`,
    allDone: "All guessed — stop timer", timeUp: "Time's up!",
    turnScore: (h, d, s) => `${h} guessed − ${d} = ${s} point${s === 1 ? "" : "s"}`,
    fixHint: "Tap a word to correct it", confirm: "Confirm & next turn", skip: "Skip turn (host)",
    waitConfirm: (n) => `Waiting for ${n} to confirm…`, wins: (t) => `${t} wins!`,
    playAgain: "Play again", leave: "Leave game", copied: "Link copied!",
    leaveConfirm: "Leave this game?", needName: "Enter your name first", needCode: "Enter a room code",
    reconnecting: "Reconnecting…", roomGone: "That game no longer exists",
  },
  nl: {
    yourName: "Je naam", joinRoom: "Meedoen met een spel", roomCode: "Spelcode", join: "Meedoen",
    newGame: "Nieuw spel starten", wordLanguage: "Taal van de woorden", teams: "Teams",
    target: "Punten om te winnen", create: "Spel aanmaken", howToPlay: "Spelregels",
    rulesText:
      "Verdeel je in teams. Elke beurt is één speler de omschrijver: die ziet 5 woorden en heeft 30 seconden om zijn team er zoveel mogelijk te laten raden — zonder het woord zelf te zeggen.\n\n" +
      "De omschrijver tikt elk geraden woord aan. Vóór de beurt wordt er gegooid met een dobbelsteen (0, 1 of 2) — dat aantal punten gaat van de score van de beurt af.\n\n" +
      "Teams zijn om de beurt en de omschrijver wisselt steeds. Het eerste team bij de finish wint!",
    shareLink: "Deel uitnodigingslink", pickTeam: "Tik op een team om erbij te gaan", shuffle: "Teams husselen",
    startGame: "Start spel", waitHost: "Wachten tot de host het spel start…", team: "Team",
    you: "jij", host: "host", describer: "Omschrijver", yourTurn: "Jij mag omschrijven!",
    teamTurn: (t, n) => `${t} — ${n} omschrijft`, guessing: "Raden maar! Je teamgenoot omschrijft.",
    watching: "Kijk mee — niet valsspelen!", die: "Dobbelsteen", minus: (d) => `−${d} punt${d === 1 ? "" : "en"} deze beurt`,
    startTimer: "Start 30 seconden", waitDescriber: (n) => `Wachten tot ${n} start…`,
    allDone: "Alles geraden — stop de tijd", timeUp: "Tijd is om!",
    turnScore: (h, d, s) => `${h} geraden − ${d} = ${s} punt${s === 1 ? "" : "en"}`,
    fixHint: "Tik op een woord om te corrigeren", confirm: "Bevestig & volgende beurt", skip: "Beurt overslaan (host)",
    waitConfirm: (n) => `Wachten tot ${n} bevestigt…`, wins: (t) => `${t} wint!`,
    playAgain: "Nog een keer", leave: "Spel verlaten", copied: "Link gekopieerd!",
    leaveConfirm: "Dit spel verlaten?", needName: "Vul eerst je naam in", needCode: "Vul een spelcode in",
    reconnecting: "Opnieuw verbinden…", roomGone: "Dit spel bestaat niet meer",
  },
};

const store = {
  get(key) { try { return JSON.parse(localStorage.getItem(key)); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode */ } },
  del(key) { try { localStorage.removeItem(key); } catch { /* private mode */ } },
};

let uiLang = store.get("uiLang") || ((navigator.language || "").toLowerCase().startsWith("nl") ? "nl" : "en");
const t = (key, ...args) => {
  const s = STRINGS[uiLang][key];
  return typeof s === "function" ? s(...args) : s;
};

// ---------- state ----------
let session = store.get("session"); // {code, playerId}
let state = null;
let ws = null;
let reconnectTimer = null;
let timerInterval = null;
let localEnd = null; // performance.now() timestamp when the turn ends
let lastTurnPhase = null;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function toast(msg, ms = 2500) {
  const el = $("toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.hidden = true; }, ms);
}

function show(screen) {
  for (const el of document.querySelectorAll(".screen")) el.hidden = el.id !== `screen-${screen}`;
  $("leave-btn").hidden = screen === "home";
}

function applyStaticText() {
  document.documentElement.lang = uiLang;
  for (const el of document.querySelectorAll("[data-t]")) el.textContent = t(el.dataset.t);
  $("ui-lang").textContent = uiLang === "nl" ? "EN" : "NL";
}

// ---------- networking ----------
async function api(path, body) {
  const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function connect() {
  if (!session) return;
  clearTimeout(reconnectTimer);
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const sock = new WebSocket(`${proto}://${location.host}/ws/${session.code}/${session.playerId}`);
  ws = sock;
  sock.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "state") { state = msg.state; render(); }
    else if (msg.type === "error") toast(msg.message);
    else if (msg.type === "gone") { toast(t("roomGone")); leave(false); }
  };
  sock.onclose = () => {
    if (ws !== sock || !session) return;
    toast(t("reconnecting"), 1500);
    reconnectTimer = setTimeout(connect, 1500);
  };
}

function send(action, extra = {}) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action, ...extra }));
  else toast(t("reconnecting"));
}

function enterRoom(code, playerId) {
  session = { code, playerId };
  store.set("session", session);
  history.replaceState(null, "", `/?room=${code}`);
  connect();
}

function leave(ask = true) {
  if (ask && !confirm(t("leaveConfirm"))) return;
  session = null;
  state = null;
  store.del("session");
  const sock = ws;
  ws = null;
  if (sock) sock.close();
  history.replaceState(null, "", "/");
  show("home");
}

// ---------- rendering ----------
const teamName = (i) => `${t("team")} ${i + 1}`;
const playerName = (id) => (state.players.find((p) => p.id === id) || { name: "?" }).name;
const me = () => state.players.find((p) => p.id === state.me);
const isHost = () => state.host_id === state.me;

function render() {
  if (!state) return;
  if (state.phase === "lobby") { show("lobby"); renderLobby(); }
  else if (state.phase === "playing") { show("game"); renderBoard($("board")); renderTurn(); }
  else { show("finished"); renderFinished(); }
}

function renderLobby() {
  $("lobby-code").textContent = state.code;
  const myTeam = me()?.team;
  let html = "";
  for (let i = 0; i < state.num_teams; i++) {
    const members = state.players.filter((p) => p.team === i);
    html += `<button class="team t${i} ${myTeam === i ? "mine" : ""}" data-team="${i}">
      <h3>${teamName(i)} (${members.length})</h3>
      <ul>${members.map((p) => `<li class="${p.connected ? "" : "offline"}">${esc(p.name)}${p.id === state.me ? ` (${t("you")})` : ""}${p.id === state.host_id ? " ★" : ""}</li>`).join("")}</ul>
    </button>`;
  }
  $("lobby-teams").innerHTML = html;
  $("host-controls").hidden = !isHost();
  $("wait-host").hidden = isHost();
}

function renderBoard(el) {
  const active = state.turn?.team;
  let html = "";
  for (let i = 0; i < state.num_teams; i++) {
    const pos = state.positions[i];
    html += `<div class="track t${i} ${active === i ? "active" : ""}">
      <span class="label">${teamName(i)}</span>
      <span class="bar"><span class="fill" style="width:${(100 * pos) / state.target}%"></span></span>
      <span class="pos">${pos}/${state.target}</span>
    </div>`;
  }
  el.innerHTML = html;
}

function renderTurn() {
  const turn = state.turn;
  const el = $("turn");
  const amDescriber = turn.describer_id === state.me;
  const describer = esc(playerName(turn.describer_id));

  // Vibrate / sync timer on phase changes.
  const phaseKey = `${turn.number}:${turn.phase}`;
  if (phaseKey !== lastTurnPhase) {
    if (turn.phase === "review" && lastTurnPhase?.endsWith(":running") && navigator.vibrate) navigator.vibrate([200, 100, 200]);
    lastTurnPhase = phaseKey;
  }
  if (turn.phase === "running" && turn.remaining != null) {
    localEnd = performance.now() + turn.remaining * 1000;
    startTimerLoop();
  } else {
    stopTimerLoop();
  }

  let html = `<div class="turn-title t${turn.team}">${amDescriber ? `<strong>${t("yourTurn")}</strong>` : t("teamTurn", teamName(turn.team), describer)}</div>`;
  html += `<div><span class="die" title="${t("die")}">${turn.die}</span></div><div class="hint">${t("minus", turn.die)}</div>`;

  if (turn.phase === "ready") {
    if (amDescriber) html += `<div class="actions" style="margin-top:14px"><button class="primary" data-action="start_timer">${t("startTimer")}</button></div>`;
    else html += `<p class="hint" style="margin-top:14px">${t("waitDescriber", describer)}</p>`;
  } else if (turn.phase === "running") {
    html += `<div id="timer" class="timer"></div>`;
    if (turn.words) {
      if (!amDescriber) html += `<p class="hint">${t("watching")}</p>`;
      html += wordsHtml(turn, amDescriber);
    } else {
      html += `<p class="score">${t("guessing")}</p>`;
    }
    if (amDescriber) html += `<div class="actions"><button class="secondary" data-action="stop_early">${t("allDone")}</button></div>`;
  } else {
    html += `<div class="timer">${t("timeUp")}</div>`;
    html += `<p class="hint">${t("fixHint")}</p>`;
    html += wordsHtml(turn, true);
    html += `<div class="score">${t("turnScore", turn.hits.length, turn.die, turn.score)}</div>`;
    html += `<div class="actions">`;
    if (amDescriber || isHost()) html += `<button class="primary" data-action="next_turn">${t("confirm")}</button>`;
    else html += `<p class="hint">${t("waitConfirm", describer)}</p>`;
    html += `</div>`;
  }
  if (turn.phase === "ready" && isHost() && !amDescriber) {
    html += `<div class="actions" style="margin-top:10px"><button class="link" data-action="next_turn">${t("skip")}</button></div>`;
  }
  el.innerHTML = html;
  updateTimer();
}

function wordsHtml(turn, clickable) {
  return `<div class="words">${turn.words.map((w, i) =>
    `<button class="word ${turn.hits.includes(i) ? "hit" : ""} ${clickable ? "" : "static"}" ${clickable ? `data-word="${i}"` : "disabled"}>${esc(w)}</button>`
  ).join("")}</div>`;
}

function renderFinished() {
  stopTimerLoop();
  $("winner-text").textContent = t("wins", teamName(state.winner));
  $("winner-text").className = `t${state.winner}`;
  $("winner-text").style.color = "var(--team-color)";
  renderBoard($("final-board"));
  $("again-btn").hidden = !isHost();
  $("wait-host-again").hidden = isHost();
}

function updateTimer() {
  const el = $("timer");
  if (!el || localEnd == null) return;
  const secs = Math.max(0, Math.ceil((localEnd - performance.now()) / 1000));
  el.textContent = secs;
  el.classList.toggle("low", secs <= 5);
}
function startTimerLoop() { if (!timerInterval) timerInterval = setInterval(updateTimer, 200); }
function stopTimerLoop() { clearInterval(timerInterval); timerInterval = null; localEnd = null; }

// ---------- events ----------
function getName() {
  const name = $("name").value.trim();
  if (!name) { toast(t("needName")); $("name").focus(); return null; }
  store.set("name", name);
  return name;
}

$("create-btn").onclick = async () => {
  const name = getName();
  if (!name) return;
  try {
    const res = await api("/api/rooms", {
      name, lang: $("lang").value, teams: Number($("teams").value), target: Number($("target").value),
    });
    enterRoom(res.code, res.player_id);
  } catch (e) { toast(e.message); }
};

$("join-btn").onclick = async () => {
  const name = getName();
  if (!name) return;
  const code = $("join-code").value.trim().toUpperCase();
  if (!code) { toast(t("needCode")); return; }
  try {
    const res = await api(`/api/rooms/${code}/join`, { name });
    enterRoom(res.code, res.player_id);
  } catch (e) { toast(e.message); }
};

$("share-btn").onclick = async () => {
  const url = `${location.origin}/?room=${state.code}`;
  if (navigator.share) { try { await navigator.share({ title: "30 Seconds", url }); return; } catch { /* cancelled */ } }
  try { await navigator.clipboard.writeText(url); toast(t("copied")); } catch { prompt("", url); }
};

$("lobby-teams").onclick = (e) => {
  const btn = e.target.closest("[data-team]");
  if (btn) send("set_team", { team: Number(btn.dataset.team) });
};
$("shuffle-btn").onclick = () => send("shuffle_teams");
$("start-btn").onclick = () => send("start_game");
$("again-btn").onclick = () => send("start_game");
$("leave-btn").onclick = () => leave(true);

$("turn").onclick = (e) => {
  const word = e.target.closest("[data-word]");
  if (word) { send("toggle_word", { index: Number(word.dataset.word) }); return; }
  const act = e.target.closest("[data-action]");
  if (act) send(act.dataset.action);
};

$("ui-lang").onclick = () => {
  uiLang = uiLang === "nl" ? "en" : "nl";
  store.set("uiLang", uiLang);
  applyStaticText();
  render();
};

// Reconnect right away when the phone wakes up / tab becomes visible again.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && session && (!ws || ws.readyState > WebSocket.OPEN)) connect();
});

// ---------- boot ----------
applyStaticText();
$("name").value = store.get("name") || "";
$("lang").value = uiLang;
const roomParam = new URLSearchParams(location.search).get("room");
if (roomParam) $("join-code").value = roomParam.toUpperCase();

if (session && (!roomParam || roomParam.toUpperCase() === session.code)) {
  show("home");
  connect();
} else {
  session = null;
  store.del("session");
  show("home");
}
