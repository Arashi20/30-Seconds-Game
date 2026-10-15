"use strict";

// ---------- UI text (interface language, separate from the word deck language) ----------
const STRINGS = {
  en: {
    tagline: "Describe. Guess. Beat the clock.",
    yourName: "Your name", joinRoom: "Join a game", roomCode: "Room code", join: "Join",
    newGame: "Start a new game", wordLanguage: "Word language", teams: "Teams",
    target: "Points to win", create: "Create room", howToPlay: "How to play",
    rulesText:
      "Split into teams. Each turn one player is the describer: they see 5 words and have 30 seconds to make their team guess as many as possible — without saying the word itself.\n\n" +
      "The describer taps every word their team guesses. Before the turn a die is rolled (0, 1 or 2) — that many points are subtracted from the turn's score.\n\n" +
      "Teams take turns and the describer rotates. The first team to reach the finish wins!",
    shareLink: "Share invite link", pickTeam: "Tap a team to join it", shuffle: "Shuffle teams",
    startGame: "Start game", waitHost: "Waiting for the host to start…", team: "Team",
    you: "you", yourTurn: "You're describing!",
    describes: (n) => `${n} is describing`, guessing: "Guess! 🗣️",
    watching: "Watch the words — no cheating!", minus: (d) => `−${d} point${d === 1 ? "" : "s"} this turn`,
    startTimer: "Start 30 seconds", waitDescriber: (n) => `Waiting for ${n} to start…`,
    allDone: "All guessed — stop timer", timeUp: "Time's up!",
    turnScore: (h, d) => `${h} guessed − ${d} (die)`,
    fixHint: "Tap a word to correct it", confirm: "Confirm & next turn", skip: "Skip turn (host)",
    waitConfirm: (n) => `Waiting for ${n} to confirm…`, wins: (t) => `${t} wins!`,
    playAgain: "Play again", leave: "Leave game", copied: "Link copied!",
    password: "Password (only to create a game)", wrongPassword: "Wrong password",
    leaveTitle: "Leave the game?",
    leaveBody: "Your team keeps its points. Join again with the same name to get back on your team.",
    leaveHost: "You're the host: another player will take over.",
    leaveDescriber: "You're describing: your turn ends now.",
    leaveYes: "Leave", leaveNo: "Stay",
    describerLeft: (n, t) => `${n} left — the host confirms ${t}'s points.`,
    confirmFor: (t) => `Confirm ${t}'s points`,
    needName: "Enter your name first", needCode: "Enter a room code",
    reconnecting: "Reconnecting…", roomGone: "That game no longer exists",
    idleClosed: (m) => `💤 Game closed after ${m} minutes without activity`, host: (n) => `★ Host: ${n}`,
    ev_joined: (n) => `👋 ${n} joined`, ev_left: (n) => `🚪 ${n} left the game`,
    ev_disconnected: (n) => `📵 ${n} lost connection`, ev_reconnected: (n) => `✅ ${n} is back`,
    ev_new_host: (n) => `★ ${n} is now the host`, ev_you_host: "★ You're now the host",
  },
  nl: {
    tagline: "Omschrijf. Raad. Versla de klok.",
    yourName: "Je naam", joinRoom: "Meedoen met een spel", roomCode: "Spelcode", join: "Meedoen",
    newGame: "Nieuw spel starten", wordLanguage: "Taal van de woorden", teams: "Teams",
    target: "Punten om te winnen", create: "Spel aanmaken", howToPlay: "Spelregels",
    rulesText:
      "Verdeel je in teams. Elke beurt is één speler de omschrijver: die ziet 5 woorden en heeft 30 seconden om zijn team er zoveel mogelijk te laten raden — zonder het woord zelf te zeggen.\n\n" +
      "De omschrijver tikt elk geraden woord aan. Vóór de beurt wordt er gegooid met een dobbelsteen (0, 1 of 2) — dat aantal punten gaat van de score van de beurt af.\n\n" +
      "Teams zijn om de beurt en de omschrijver wisselt steeds. Het eerste team bij de finish wint!",
    shareLink: "Deel uitnodigingslink", pickTeam: "Tik op een team om erbij te gaan", shuffle: "Teams husselen",
    startGame: "Start spel", waitHost: "Wachten tot de host het spel start…", team: "Team",
    you: "jij", yourTurn: "Jij mag omschrijven!",
    describes: (n) => `${n} omschrijft`, guessing: "Raden maar! 🗣️",
    watching: "Kijk mee — niet valsspelen!", minus: (d) => `−${d} punt${d === 1 ? "" : "en"} deze beurt`,
    startTimer: "Start 30 seconden", waitDescriber: (n) => `Wachten tot ${n} start…`,
    allDone: "Alles geraden — stop de tijd", timeUp: "Tijd is om!",
    turnScore: (h, d) => `${h} geraden − ${d} (dobbelsteen)`,
    fixHint: "Tik op een woord om te corrigeren", confirm: "Bevestig & volgende beurt", skip: "Beurt overslaan (host)",
    waitConfirm: (n) => `Wachten tot ${n} bevestigt…`, wins: (t) => `${t} wint!`,
    playAgain: "Nog een keer", leave: "Spel verlaten", copied: "Link gekopieerd!",
    password: "Wachtwoord (alleen om een spel aan te maken)", wrongPassword: "Verkeerd wachtwoord",
    leaveTitle: "Spel verlaten?",
    leaveBody: "Je team houdt zijn punten. Doe opnieuw mee met dezelfde naam om terug in je team te komen.",
    leaveHost: "Jij bent de host: een andere speler neemt het over.",
    leaveDescriber: "Jij omschrijft nu: je beurt stopt meteen.",
    leaveYes: "Verlaten", leaveNo: "Blijven",
    describerLeft: (n, t) => `${n} is weg — de host bevestigt de punten van ${t}.`,
    confirmFor: (t) => `Bevestig punten van ${t}`,
    needName: "Vul eerst je naam in", needCode: "Vul een spelcode in",
    reconnecting: "Opnieuw verbinden…", roomGone: "Dit spel bestaat niet meer",
    idleClosed: (m) => `💤 Spel gesloten na ${m} minuten zonder activiteit`, host: (n) => `★ Host: ${n}`,
    ev_joined: (n) => `👋 ${n} doet mee`, ev_left: (n) => `🚪 ${n} heeft het spel verlaten`,
    ev_disconnected: (n) => `📵 ${n} heeft geen verbinding`, ev_reconnected: (n) => `✅ ${n} is terug`,
    ev_new_host: (n) => `★ ${n} is nu de host`, ev_you_host: "★ Jij bent nu de host",
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
let localEnd = null;      // performance.now() timestamp when the turn ends
let lastPhaseKey = null;  // "turnNumber:phase", to detect transitions
let rolledTurn = null;    // turn number whose die roll was animated
let prevHits = [];
let hitsTurn = null;      // turn number prevHits belongs to
let lastTickSecond = null;
let soundOn = store.get("sound") !== false;
let celebrated = false;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function toast(msg, ms = 3000) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  $("toasts").appendChild(el);
  setTimeout(() => {
    el.classList.add("out");
    setTimeout(() => el.remove(), 300);
  }, ms);
}

function show(screen) {
  for (const el of document.querySelectorAll(".screen")) el.hidden = el.id !== `screen-${screen}`;
  $("leave-btn").hidden = screen === "home";
  $("host-line").hidden = screen === "home" || !state;
}

function applyStaticText() {
  document.documentElement.lang = uiLang;
  for (const el of document.querySelectorAll("[data-t]")) el.textContent = t(el.dataset.t);
  $("ui-lang").textContent = uiLang === "nl" ? "EN" : "NL";
  $("sound-btn").textContent = soundOn ? "🔊" : "🔇";
}

// ---------- sound (generated, no audio files) ----------
let audioCtx = null;
function unlockAudio() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
  } catch { audioCtx = null; }
}
function beep(freq, duration = 0.1, type = "sine", volume = 0.2) {
  if (!soundOn || !audioCtx) return;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(volume, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
  osc.connect(gain).connect(audioCtx.destination);
  osc.start();
  osc.stop(audioCtx.currentTime + duration);
}
const sounds = {
  tick: () => beep(880, 0.08, "square", 0.08),
  hit: () => { beep(660, 0.08); setTimeout(() => beep(990, 0.12), 70); },
  buzzer: () => { beep(160, 0.6, "sawtooth", 0.25); beep(120, 0.6, "sawtooth", 0.2); },
  start: () => [523, 659, 784].forEach((f, i) => setTimeout(() => beep(f, 0.12), i * 90)),
  win: () => [523, 659, 784, 1047].forEach((f, i) => setTimeout(() => beep(f, 0.18, "triangle", 0.25), i * 130)),
};

// ---------- networking ----------
async function api(path, body) {
  const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.detail || res.statusText), { status: res.status });
  return data;
}

function connect() {
  if (!session) return;
  clearTimeout(reconnectTimer);
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const sock = new WebSocket(`${proto}://${location.host}/ws/${session.code}/${session.playerId}`);
  ws = sock;
  sock.onopen = () => { lastHeard = Date.now(); };
  sock.onmessage = (ev) => {
    lastHeard = Date.now();
    const msg = JSON.parse(ev.data);
    if (msg.type === "pong") return;
    if (msg.type === "state") { state = msg.state; render(); }
    else if (msg.type === "event") showEvent(msg);
    else if (msg.type === "error") toast(msg.message);
    else if (msg.type === "gone") { toast(t("roomGone")); leave(); }
    else if (msg.type === "closed") { toast(t("idleClosed", msg.minutes), 6000); leave(); }
  };
  sock.onclose = () => {
    if (ws !== sock || !session) return;
    toast(t("reconnecting"), 1500);
    reconnectTimer = setTimeout(connect, 1500);
  };
}

// Heartbeat: a ping every 25 s keeps the connection (and a Serverless app)
// awake during quiet moments. If the server stays silent for a minute the
// connection is dead without the browser noticing (common on phones), so
// throw it away and reconnect.
const PING_EVERY_MS = 25000;
const DEAD_AFTER_MS = 60000;
let lastHeard = 0;

function reconnectNow() {
  const dead = ws;
  ws = null; // its onclose will now ignore it
  if (dead) dead.close();
  connect();
}

setInterval(() => {
  if (!session || !ws || ws.readyState !== WebSocket.OPEN) return;
  if (Date.now() - lastHeard > DEAD_AFTER_MS) reconnectNow();
  else ws.send(JSON.stringify({ action: "ping" }));
}, PING_EVERY_MS);

function showEvent({ event, name }) {
  if (event === "new_host" && state && name === me()?.name) toast(t("ev_you_host"));
  else if (STRINGS[uiLang][`ev_${event}`]) toast(t(`ev_${event}`, name));
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

// A styled yes/no dialog instead of the browser's confirm(). Resolves true/false.
function askDialog({ title, lines, yes, no }) {
  return new Promise((resolve) => {
    const backdrop = $("dialog");
    $("dialog-title").textContent = title;
    $("dialog-body").innerHTML = lines.map((l) => `<p>${esc(l)}</p>`).join("");
    $("dialog-yes").textContent = yes;
    $("dialog-no").textContent = no;
    backdrop.hidden = false;
    $("dialog-no").focus();
    const close = (answer) => {
      backdrop.hidden = true;
      backdrop.onclick = $("dialog-yes").onclick = $("dialog-no").onclick = document.onkeydown = null;
      resolve(answer);
    };
    $("dialog-yes").onclick = () => close(true);
    $("dialog-no").onclick = () => close(false);
    backdrop.onclick = (e) => { if (e.target === backdrop) close(false); };
    document.onkeydown = (e) => { if (e.key === "Escape") close(false); };
  });
}

async function confirmLeave() {
  const lines = [t("leaveBody")];
  if (state && isHost() && state.players.length > 1) lines.push(t("leaveHost"));
  if (state?.turn?.phase === "running" && state.turn.describer_id === state.me) lines.push(t("leaveDescriber"));
  if (await askDialog({ title: t("leaveTitle"), lines, yes: t("leaveYes"), no: t("leaveNo") })) leave();
}

function leave() {
  const sock = ws;
  ws = null;
  if (sock && sock.readyState === WebSocket.OPEN) sock.send(JSON.stringify({ action: "leave" }));
  else if (sock) sock.close();
  session = null;
  state = null;
  store.del("session");
  stopTimerLoop();
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
  $("host-line").textContent = t("host", playerName(state.host_id));
  if (state.phase === "lobby") { show("lobby"); renderLobby(); celebrated = false; }
  else if (state.phase === "playing") { show("game"); renderBoard($("board")); renderTurn(); celebrated = false; }
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
      <span class="label">${teamName(i)}${me()?.team === i ? ` <span class="you-tag">${t("you")}</span>` : ""}</span>
      <span class="bar"><span class="fill" style="width:${(100 * pos) / state.target}%"></span></span>
      <span class="pos">${pos}/${state.target}</span>
    </div>`;
  }
  el.innerHTML = html;
}

// Pip positions on a 3x3 grid for the die faces 0, 1 and 2.
const PIPS = { 0: [], 1: [5], 2: [3, 7] };
function dieHtml(value, rolling) {
  const cells = Array.from({ length: 9 }, (_, i) => (PIPS[value].includes(i + 1) ? `<span class="pip"></span>` : "<span></span>"));
  return `<div class="die ${rolling ? "rolling" : ""}" role="img" aria-label="${value}">${cells.join("")}</div>`;
}

const RING = 2 * Math.PI * 72;

function renderTurn() {
  const turn = state.turn;
  const el = $("turn");
  const amDescriber = turn.describer_id === state.me;
  const describer = esc(turn.describer_name);

  // Phase transitions: sounds + timer sync.
  const phaseKey = `${turn.number}:${turn.phase}`;
  if (phaseKey !== lastPhaseKey) {
    if (turn.phase === "running" && amDescriber) sounds.start();
    if (turn.phase === "review" && lastPhaseKey === `${turn.number}:running`) {
      if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
      if (amDescriber) sounds.buzzer();
    }
    lastPhaseKey = phaseKey;
    lastTickSecond = null;
  }
  if (turn.phase === "running" && turn.remaining != null) {
    localEnd = performance.now() + turn.remaining * 1000;
    startTimerLoop();
  } else {
    stopTimerLoop();
  }

  const rolling = rolledTurn !== turn.number;
  rolledTurn = turn.number;
  if (hitsTurn !== turn.number) { prevHits = turn.hits; hitsTurn = turn.number; }
  const newHits = turn.hits.filter((h) => !prevHits.includes(h));
  if (newHits.length && amDescriber) sounds.hit();
  prevHits = turn.hits;

  let html = `<div class="turn-title">${amDescriber
    ? `<strong>${t("yourTurn")}</strong>`
    : `<span class="team-pill t${turn.team}">${teamName(turn.team)}</span> ${t("describes", describer)}`}</div>`;

  if (turn.phase !== "running") {
    html += `<div class="die-wrap">${dieHtml(turn.die, rolling)}</div><div class="hint">${t("minus", turn.die)}</div>`;
  }

  if (turn.phase === "ready") {
    if (amDescriber) html += `<div class="stack" style="margin-top:16px"><button class="btn primary big" data-action="start_timer">${t("startTimer")}</button></div>`;
    else html += `<p class="hint" style="margin-top:16px">${t("waitDescriber", describer)}</p>`;
    if (isHost() && !amDescriber) html += `<button class="link" data-action="next_turn" style="margin-top:6px">${t("skip")}</button>`;
  } else if (turn.phase === "running") {
    html += `<div id="timer-ring" class="timer-ring">
      <svg viewBox="0 0 170 170"><circle class="ring-bg" cx="85" cy="85" r="72"/><circle id="ring" class="ring-fg" cx="85" cy="85" r="72" stroke-dasharray="${RING}" stroke-dashoffset="0"/></svg>
      <div id="timer" class="timer-num"></div>
    </div>`;
    if (turn.words) {
      if (!amDescriber) html += `<p class="hint">${t("watching")}</p>`;
      html += wordsHtml(turn, amDescriber, newHits);
    } else {
      html += `<p class="guessing">${t("guessing")}</p>`;
    }
    if (amDescriber) html += `<button class="btn secondary" data-action="stop_early">${t("allDone")}</button>`;
  } else {
    html += `<div class="times-up">${t("timeUp")}</div>`;
    html += wordsHtml(turn, true, newHits);
    html += `<div class="score-pop ${turn.score ? "" : "zero"}">+${turn.score}</div>`;
    html += `<div class="score-calc">${t("turnScore", turn.hits.length, turn.die)}</div>`;
    html += `<p class="hint" style="margin-bottom:12px">${t("fixHint")}</p>`;
    if (turn.describer_left) html += `<p class="note">${t("describerLeft", describer, teamName(turn.team))}</p>`;
    if (amDescriber) html += `<button class="btn primary big" data-action="next_turn">${t("confirm")}</button>`;
    else if (isHost()) html += `<button class="btn primary big" data-action="next_turn">${turn.describer_left ? t("confirmFor", teamName(turn.team)) : t("confirm")}</button>`;
    else html += `<p class="hint">${t("waitConfirm", turn.describer_left ? esc(playerName(state.host_id)) : describer)}</p>`;
  }
  el.innerHTML = html;
  updateTimer();
}

function wordsHtml(turn, clickable, newHits) {
  return `<div class="words">${turn.words.map((w, i) => {
    const cls = ["word", turn.hits.includes(i) ? "hit" : "", newHits.includes(i) ? "just-hit" : "", clickable ? "" : "static"].join(" ");
    return `<button class="${cls}" ${clickable ? `data-word="${i}"` : "disabled"}>${esc(w)}</button>`;
  }).join("")}</div>`;
}

function renderFinished() {
  stopTimerLoop();
  const winner = $("winner-text");
  winner.textContent = t("wins", teamName(state.winner));
  winner.className = `winner t${state.winner}`;
  renderBoard($("final-board"));
  $("again-btn").hidden = !isHost();
  $("wait-host-again").hidden = isHost();
  if (!celebrated) {
    celebrated = true;
    sounds.win();
    confetti();
  }
}

function updateTimer() {
  const num = $("timer");
  if (!num || localEnd == null) return;
  const total = state?.turn_seconds || 30;
  const left = Math.max(0, (localEnd - performance.now()) / 1000);
  const secs = Math.ceil(left);
  num.textContent = secs;
  $("ring").setAttribute("stroke-dashoffset", RING * (1 - left / total));
  $("timer-ring").classList.toggle("low", secs <= 5);

  if (state.turn?.describer_id === state.me && secs !== lastTickSecond) {
    if (secs <= 5 && secs > 0) sounds.tick();
    lastTickSecond = secs;
  }
}
function startTimerLoop() { if (!timerInterval) timerInterval = setInterval(updateTimer, 100); }
function stopTimerLoop() { clearInterval(timerInterval); timerInterval = null; localEnd = null; }

// ---------- confetti ----------
function confetti() {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const canvas = $("confetti");
  const ctx = canvas.getContext("2d");
  canvas.width = innerWidth * devicePixelRatio;
  canvas.height = innerHeight * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
  const colors = ["#ffc83d", "#ff5d73", "#3e9bff", "#22c38e", "#ff9f1c", "#ffffff"];
  const parts = Array.from({ length: 160 }, () => ({
    x: Math.random() * innerWidth, y: -20 - Math.random() * innerHeight * 0.5,
    vx: (Math.random() - 0.5) * 3, vy: 2 + Math.random() * 3,
    r: Math.random() * Math.PI, vr: (Math.random() - 0.5) * 0.3,
    w: 6 + Math.random() * 6, h: 8 + Math.random() * 8,
    c: colors[Math.floor(Math.random() * colors.length)],
  }));
  const end = performance.now() + 4000;
  (function frame(now) {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    for (const p of parts) {
      p.x += p.vx; p.y += p.vy; p.vy += 0.04; p.r += p.vr;
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r);
      ctx.fillStyle = p.c; ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    }
    if (now < end) requestAnimationFrame(frame);
    else ctx.clearRect(0, 0, innerWidth, innerHeight);
  })(performance.now());
}

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
  unlockAudio();
  try {
    const password = $("password").value;
    const res = await api("/api/rooms", {
      name, lang: $("lang").value, teams: Number($("teams").value), target: Number($("target").value), password,
    });
    if (password) store.set("password", password);
    enterRoom(res.code, res.player_id);
  } catch (e) {
    if (e.status === 403) {
      $("password-row").hidden = false;
      $("password").value = "";
      store.del("password");
      $("password").focus();
      toast(t("wrongPassword"));
    } else toast(e.message);
  }
};

$("join-btn").onclick = async () => {
  const name = getName();
  if (!name) return;
  unlockAudio();
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
$("leave-btn").onclick = confirmLeave;

$("turn").onclick = (e) => {
  unlockAudio(); // browsers only allow sound after a tap
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

$("sound-btn").onclick = () => {
  soundOn = !soundOn;
  store.set("sound", soundOn);
  applyStaticText();
  if (soundOn) { unlockAudio(); sounds.hit(); }
};

document.addEventListener("pointerdown", unlockAudio, { once: true });

// Reconnect right away when the phone wakes up / tab becomes visible again.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || !session) return;
  if (!ws || ws.readyState > WebSocket.OPEN) connect();
  else if (ws.readyState === WebSocket.OPEN && Date.now() - lastHeard > DEAD_AFTER_MS) reconnectNow();
});

// ---------- boot ----------
applyStaticText();
$("name").value = store.get("name") || "";
$("password").value = store.get("password") || "";
// Only show the password field when the server has one set (e.g. on Railway).
fetch("/api/config").then((r) => r.json()).then((cfg) => {
  $("password-row").hidden = !cfg.needs_password || Boolean(store.get("password"));
}).catch(() => {});
$("lang").value = uiLang;
const roomParam = new URLSearchParams(location.search).get("room");
if (roomParam) $("join-code").value = roomParam.toUpperCase();

show("home");
if (session && (!roomParam || roomParam.toUpperCase() === session.code)) {
  connect();
} else {
  session = null;
  store.del("session");
}
