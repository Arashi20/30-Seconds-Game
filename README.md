# 30 Seconds 🎲⏱️

A free, home-made version of the party game **30 Seconds** that you play in the browser.
Everyone joins on their **own phone**: no app to install, no account, nothing to pay for.

- 🇳🇱 Dutch and 🇬🇧 English word decks (≈350 words each; add your own easily)
- 📱 Every player uses their own phone, and the game stays in sync live
- 🏠 Play on your home Wi-Fi from your laptop, **or** host it online on Railway

> The game rules are free for anyone to use. The words and the code in this repo are our own, not copied from the official app.

---

## Contents

1. [How the game works](#how-the-game-works)
2. [Features](#features)
3. [Quick start: play at home on your Wi-Fi](#quick-start-play-at-home-on-your-wi-fi)
4. [Try it without installing anything: GitHub Codespaces](#try-it-without-installing-anything-github-codespaces)
5. [Host it online on Railway](#host-it-online-on-railway)
6. [Testing](#testing)
7. [Adding or changing words](#adding-or-changing-words)
8. [Project structure](#project-structure)
9. [Troubleshooting](#troubleshooting)

---

## How the game works

1. **Make teams.** 2 to 4 teams, each with at least 2 players.
2. **Take turns.** Teams alternate turns. Within each team the **describer** rotates, so everybody gets a go.
3. **Roll the die.** At the start of each turn a die is rolled automatically. It shows **0, 1 or 2**, the same as the original game's die (two blanks, two 1s, two 2s). That many points are **subtracted** from the turn's score.
4. **Describe for 30 seconds.** The describer taps **Start**. Their phone shows **5 words**. They try to get their teammates to guess as many as possible **without saying the word itself** (no rhymes, no "sounds like", no spelling it out).
5. **Tap what's guessed.** The describer taps each word their team guesses, and it turns green ✓.
6. **Score.** When time runs out (or the describer taps *All guessed*), the turn score is **guessed words − die**, never below 0. The team moves that many steps forward.
7. **Win.** The first team to reach the finish wins. The finish is **30 points** by default, and you can change it when creating a game.

### Who sees what

| Player | Before start | During the 30 seconds | After the timer |
|---|---|---|---|
| **Describer** | Start button | ✅ the 5 words (tappable) | ✅ the words + score |
| **Their teammates** (guessers) | "Waiting…" | ❌ *no words*, just the timer | ✅ the words + score |
| **Other teams** | "Waiting…" | ✅ the words (to catch cheating!) | ✅ the words + score |

---

## Features

**Rooms and joining**
- Create a game and get a **4-letter room code** (e.g. `GGQA`).
- Friends join by typing the code, or by opening the **invite link** (the *Share invite link* button uses your phone's share sheet, or copies the link).
- Names must be unique within a room.

**Lobby**
- New players are automatically added to the smallest team.
- Tap a team to switch to it.
- The **host** (whoever created the room, marked ★) can **shuffle teams** randomly and **start the game**.
- The game won't start unless every team has at least 2 players.

**Game settings** (chosen when creating the room)
- **Word language:** Nederlands or English
- **Number of teams:** 2, 3 or 4
- **Points to win:** 5 to 100 (default 30)

**During play**
- A live **scoreboard** shows each team's progress, with ▶ marking the team whose turn it is.
- At the start of each turn the **die rolls** on screen (dots, like a real die; a blank face means 0).
- A **30-second countdown ring** empties as time runs out and turns red and pulses in the last 5 seconds. Phones **vibrate** when time is up (on phones that support it).
- **"All guessed — stop timer"** button so you don't have to wait out the clock.
- **Corrections:** after the timer, anyone can tap a word to fix a missed or wrong tick before the score is confirmed.
- The describer (or the host) taps **Confirm & next turn** to apply the score.
- The host can **skip a turn**, for example if the describer is away or their phone died.
- Words don't repeat until the whole deck has been used.

**Players coming and going**
- If a phone locks, the page reloads or the connection drops, it **reconnects automatically** to the same game.
- Pop-up messages tell everyone when a player **joins**, **leaves**, **loses connection** or **comes back**. A short connection hiccup (under 5 seconds) isn't announced, so a phone locking its screen for a moment doesn't spam everyone.
- Offline players are shown greyed out with 💤 in the lobby.
- **Leave game** really removes you from the match. If you were the describer:
  - before your turn started, your team gets a new describer;
  - during your turn, the timer stops and the host confirms the score.
- **If the host leaves**, the host role moves straight to the player who has been in the game longest and is still connected. **If the host loses connection**, the same happens after 15 seconds. Everyone gets a pop-up, and the footer always shows **★ Host: name**. A host who comes back doesn't take the role back.

**Look and sound**
- Its own brand: a stopwatch logo with "30" and a bold **SECONDS** wordmark, on a deep purple background with yellow and coral accents.
- Chunky game-style buttons that press down when tapped, and a rounded, playful font.
- Animations: rolling die, pop-in ticks, a big **+score** after each turn, and **confetti** for the winner. They're switched off automatically if the phone is set to reduce motion.
- **Sounds**, generated in the browser so there are no audio files:
  - a start jingle;
  - a blip when a word is ticked;
  - ticks in the last 5 seconds;
  - a buzzer at the end, played on the describer's phone only, so a room full of phones isn't beeping out of sync;
  - a fanfare for the winner, on everyone's phone.
- The 🔊/🔇 button at the top mutes sound on your phone.

**Other**
- **Interface language:** Dutch or English. It's picked automatically from the phone's language, and the **NL/EN** button at the top switches it. This is separate from the word language.
- **Play again** after a game finishes, with the same teams.

---

## Quick start: play at home on your Wi-Fi

You need **Python 3.10 or newer** ([download](https://www.python.org/downloads/)). Your laptop and all the phones must be on the **same Wi-Fi**.

### 1. Install (only the first time)

Open the project folder in VS Code, then open a terminal (**Terminal → New Terminal**) and run:

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If PowerShell says scripts are disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

### 2. Start the game server

Activate the environment first if it isn't already (`source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\Activate.ps1` on Windows). Then run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

You should see `Uvicorn running on http://0.0.0.0:8000`. Keep this terminal open while you play. Press **Ctrl+C** to stop.

### 3. Find your laptop's local IP address

- **macOS:** `ipconfig getifaddr en0`
- **Windows:** `ipconfig` → look for **IPv4 Address** under your Wi-Fi adapter
- **Linux:** `hostname -I`

It will look like `192.168.1.23`.

### 4. Play!

- On the laptop itself: open **http://localhost:8000**
- On every phone: open **http://192.168.1.23:8000** (use *your* IP from step 3)

One person creates the game, and the rest join with the room code or invite link.

> **Windows:** the first time, Windows Firewall may ask whether Python can accept connections. Click **Allow** (for private networks), or phones won't be able to connect.

---

## Try it without installing anything: GitHub Codespaces

Codespaces gives you VS Code in your browser, running on GitHub's computers. It's handy when you're not on your own laptop. Personal GitHub accounts get free hours every month.

1. On github.com, open this repo → green **Code** button → **Codespaces** tab → **Create codespace on main**.
2. In the terminal at the bottom, run:
   ```bash
   pip install -r requirements.txt
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   (Use `python -m uvicorn`, not plain `uvicorn`. In Codespaces the plain command often says *command not found*.)
3. Click **Open in Browser** in the pop-up, or go to the **Ports** tab and click the 🌐 globe next to port 8000.
4. **Let others join:** in the **Ports** tab, right-click port 8000 → **Port Visibility** → **Public**. Without this, everyone needs to log in to GitHub as you. The first visit may show a GitHub warning page; just click **Continue**.
5. **When you're done:** press Ctrl+C, then click **Codespaces** in the bottom-left corner → **Stop Current Codespace**. Closing the tab alone keeps it running for another 30 minutes.

---

## Host it online on Railway

This gives you a permanent public link like `https://30-seconds-production.up.railway.app`, so friends can play from anywhere, even on mobile data, and your laptop doesn't need to be on.

1. Go to [railway.com](https://railway.com) and sign in with GitHub.
2. Click **New Project → Deploy from GitHub repo** and pick this repository (`30-Seconds-Game`).
3. Railway detects Python automatically, installs `requirements.txt`, and starts the server with the command in the `Procfile`. Nothing to configure.
4. When the deploy is done, open the service → **Settings → Networking → Generate Domain**.
5. Open that URL on your phone and share it with friends. 🎉

Every time you push to the branch Railway is watching, it redeploys automatically. You can choose the branch under **Settings → Source**.

**Good to know**
- Games are kept **in memory**. A redeploy or restart ends any game in progress, which is fine for a party game. Old, idle rooms are cleaned up automatically after 6 hours.
- Run a **single instance** (Railway's default). Multiple replicas wouldn't share game state.
- Health check URL: `/healthz`

---

## Testing

### Automated tests

These check the game rules and a full game over real WebSocket connections. They take about 2 seconds.

```bash
pip install -r requirements-dev.txt   # once
python -m pytest -v
```

What's covered:
- word lists load, are large enough and have no duplicates
- joining, unique names, auto-balanced teams, the host role
- the game won't start until every team has 2 or more players
- score = guessed − die, never negative, and corrections during review
- teams alternate and describers rotate
- **guessers can't see the words, while opponents can**
- the timer ends the turn on its own, and a late timer can't end the next turn
- host skip, winning, playing again
- leaving: a describer leaving before or during their turn, the last player leaving
- **host handover** when the host leaves or loses connection, pop-up messages for joining, leaving, disconnecting and coming back, and that a quick reconnect is *not* announced (these run against a real server)
- no repeated words until the deck runs out
- the HTTP API and WebSocket flow end-to-end, including error handling

### Try every feature by hand on one computer

You don't need 4 phones to test. Each **private/incognito window** (or a different browser) counts as a separate player.

1. Start the server (see [Quick start](#2-start-the-game-server)).
2. **Window 1:** open http://localhost:8000, enter name `Anna` → **Create room**. Note the room code.
3. **Windows 2, 3, 4:** open **new incognito windows** (Chrome: *Ctrl/Cmd+Shift+N*). Join as `Bob`, `Cleo`, `Dirk` with the code.
   - Tip: shrink the windows to phone size, or use Chrome DevTools' phone view (*F12 → Ctrl/Cmd+Shift+M*).
4. **Lobby:** switch teams by tapping them, try **Shuffle teams** (as Anna) and check that **Start game** only works with 2+ players per team.
5. **Turn:** in the describer's window, tap **Start 30 seconds**. Check that:
   - the describer sees 5 words and can tap them green
   - the describer's **teammate** sees *no words*
   - the **other team** sees the words and the green ticks live
6. Let the timer run out, or tap **All guessed**. Fix a tick in any window, check the score maths, then **Confirm & next turn**. The scoreboard should move.
7. **Reconnect:** refresh a player's window mid-game. They should come straight back into the game.
8. **Skip:** as Anna (host), tap **Skip turn** while someone else is up.
9. **Leaving / host handover:** as Anna, tap **Leave game**. The others should get pop-ups ("Anna left the game", "You're now the host"), and the footer should show the new host. To test a lost connection instead, simply close a window. The pop-up appears after about 5 seconds, and if it was the host, the host role moves on after about 15 seconds.
10. **Win:** create a new room with *Points to win* = **5** to reach the end quickly, then try **Play again**.
11. **Languages:** create a room with English words, and tap **NL/EN** at the top to switch the interface.

---

## Adding or changing words

The words are plain text files, **one word per line**:

- `app/words/nl.txt`: Dutch
- `app/words/en.txt`: English

Lines starting with `#` are comments and are ignored. Duplicates are removed automatically. Add your friends' names, inside jokes, favourite series… then restart the server (or push, if you're on Railway). Run `python -m pytest` afterwards as a quick sanity check.

Want a third language? Add `app/words/de.txt` and add `"de"` to `LANGUAGES` in `app/game.py` and to the language dropdown in `static/index.html`.

---

## Project structure

```
app/
  game.py        # all game rules (teams, turns, die, scoring, who sees what)
  main.py        # web server: create/join API + live WebSocket updates
  words/
    nl.txt       # Dutch words
    en.txt       # English words
static/
  index.html     # the single page the phones load
  app.js         # screens, timer, talking to the server
  style.css      # mobile-first styling, brand colours and animations
  logo.svg       # the stopwatch logo (also the browser tab icon)
tests/
  test_game.py   # game-rule tests
  test_api.py    # end-to-end server tests
Procfile         # start command for Railway
requirements.txt # what the server needs
```

How it fits together: the **server is the referee**. It holds the one true game state (scores, the current card, the timer) and pushes it to every phone over a WebSocket whenever something changes. Each phone only gets what that player is allowed to see, so guessers can't peek at the words with dev tools. Phones just send actions such as "start timer" or "tick word 2".

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Phones can't open the page | Check they're on the **same Wi-Fi** as the laptop, you used the laptop's IP (not `localhost`), you started with `--host 0.0.0.0`, and the firewall allows Python. Some guest/office Wi-Fi networks block devices from talking to each other. Use Railway or a phone hotspot instead. |
| `uvicorn: command not found` | Activate the virtual environment first (step 2), or run `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`. |
| "Address already in use" | Another server is already running. Stop it with Ctrl+C, or use `--port 8001`. |
| A player is stuck on "Reconnecting…" | Refresh the page; they'll rejoin the same game automatically. |
| Someone's phone died mid-turn | The host taps **Skip turn**. |
| "That game no longer exists" | The server was restarted (games are kept in memory). Create a new room. |
