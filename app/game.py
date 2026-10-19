"""Core game logic for 30 Seconds, independent of the web layer.

Flow of a turn:
    ready   -> the describer sees a "Start" button, die is already rolled
    running -> 30s timer; describer sees the words and ticks the guessed ones
    review  -> everyone sees the card; score = max(0, hits - die)
"""

from __future__ import annotations

import random
import secrets
import string
import time
from dataclasses import dataclass, field
from pathlib import Path

TURN_SECONDS = 30
WORDS_PER_CARD = 5
DIE_FACES = (0, 0, 1, 1, 2, 2)  # the original die: two blanks, two 1s, two 2s
DEFAULT_TARGET = 30
LANGUAGES = ("nl", "en", "fa")  # fa = Finglish: Persian in Latin letters
WORDS_DIR = Path(__file__).parent / "words"
# Theme ids, as used after "## " in the word files. The page shows their names.
THEMES = ("people", "characters", "places", "food", "animals", "sports", "everyday", "fun", "nature")
MODES = ("teams", "solo")  # solo = one phone: a game master describes, everyone guesses


class GameError(Exception):
    """Raised on an invalid action; the message is shown to the player."""


def load_themes(lang: str) -> dict[str, list[str]]:
    """Words per theme. A line "## <theme>" starts a theme; other # lines are comments."""
    if lang not in LANGUAGES:
        raise GameError(f"Unknown language: {lang}")
    themes: dict[str, list[str]] = {t: [] for t in THEMES}
    current = None
    for line in (WORDS_DIR / f"{lang}.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            current = line[3:].strip()
            if current not in themes:
                raise ValueError(f"{lang}.txt: unknown theme {current!r}")
        elif line and not line.startswith("#"):
            if current is None:
                raise ValueError(f"{lang}.txt: {line!r} comes before any '## theme' line")
            themes[current].append(line)
    return {t: list(dict.fromkeys(ws)) for t, ws in themes.items()}


def load_words(lang: str, themes: tuple[str, ...] | None = None) -> list[str]:
    """All words of a language, or only those of the given themes."""
    by_theme = load_themes(lang)
    picked = [w for t in (themes or THEMES) for w in by_theme[t]]
    return list(dict.fromkeys(picked))  # dedupe, keep order


class Deck:
    """A shuffled pile of words: none repeats until every word has been drawn."""

    def __init__(self, words: list[str], rng: random.Random):
        self.words = words
        self.rng = rng
        self.pile: list[str] = []

    def draw(self, n: int) -> list[str]:
        if len(self.pile) < n:
            fresh = [w for w in self.words if w not in self.pile]
            self.rng.shuffle(fresh)
            self.pile = fresh + self.pile
        drawn, self.pile = self.pile[-n:], self.pile[:-n]
        return drawn


# One deck per language (and theme selection), shared by all rooms: a new game
# carries on where the previous one stopped instead of reshuffling, so words
# don't come back night after night. (A restart or Serverless sleep reshuffles.)
_shared_decks: dict[tuple, Deck] = {}


def shared_deck(lang: str, themes: tuple[str, ...] | None = None) -> Deck:
    key = (lang, themes)
    if key not in _shared_decks:
        _shared_decks[key] = Deck(load_words(lang, themes), random.Random())
    return _shared_decks[key]


@dataclass
class Player:
    id: str
    name: str
    team: int | None = None
    connected: bool = False
    was_online: bool = False  # has connected at least once


@dataclass
class Turn:
    number: int
    team: int
    describer_id: str
    describer_name: str
    die: int
    words: list[str]
    hits: set[int] = field(default_factory=set)
    phase: str = "ready"  # ready | running | review
    ends_at: float | None = None
    score: int = 0


class Room:
    def __init__(
        self,
        code: str,
        lang: str = "nl",
        num_teams: int = 2,
        target: int = DEFAULT_TARGET,
        rng: random.Random | None = None,
        mode: str = "teams",
    ):
        if mode not in MODES:
            raise GameError("Unknown game mode")
        if mode == "solo":
            num_teams = 1  # one phone, no teams: just rounds and a running total
        elif not 2 <= num_teams <= 4:
            raise GameError("Choose 2 to 4 teams")
        if not 5 <= target <= 100:
            raise GameError("Target must be between 5 and 100")
        self.code = code
        self.lang = lang
        self.mode = mode
        self.num_teams = num_teams
        self.target = target
        self.rng = rng or random.Random()
        self.private_deck = rng is not None  # tests: private, reproducible deck
        self.themes: tuple[str, ...] | None = None  # None = all themes
        self.theme_counts = {t: len(ws) for t, ws in load_themes(lang).items()}
        self._build_deck()
        self.round_scores: list[int] = []  # solo mode: points per round
        self.players: dict[str, Player] = {}
        self.left_teams: dict[str, int] = {}  # lowercased name -> team, for players who left
        self.host_id: str | None = None
        self.phase = "lobby"  # lobby | playing | finished
        self.positions = [0] * num_teams
        self.winner: int | None = None
        self.turn: Turn | None = None
        self.turn_count = 0
        self.next_team = 0
        self.describer_index = [0] * num_teams
        self.last_activity = time.time()

    # ----- lobby -----

    def add_player(self, name: str) -> Player:
        name = name.strip()[:20]
        if not name:
            raise GameError("Enter a name")
        existing = next((p for p in self.players.values() if p.name.lower() == name.lower()), None)
        if existing is not None:
            if existing.connected or not existing.was_online:
                raise GameError("That name is already taken in this room")
            # Same name as an offline player (e.g. their phone died or the
            # browser forgot the game): take their seat back, team and all.
            self.touch()
            return existing
        if self.mode == "solo" and self.players:
            raise GameError("This game is played on one phone: nobody can join")
        player = Player(id=secrets.token_urlsafe(12), name=name)
        if name.lower() in self.left_teams:
            # Someone who left and comes back returns to their old team.
            player.team = self.left_teams.pop(name.lower())
        else:
            # Auto-balance: join the smallest team (works mid-game too).
            player.team = min(range(self.num_teams), key=lambda t: len(self.team_members(t)))
        self.players[player.id] = player
        if self.host_id is None:
            self.host_id = player.id
        self.touch()
        return player

    def set_team(self, player_id: str, team: int) -> None:
        self._require_phase("lobby")
        if not 0 <= team < self.num_teams:
            raise GameError("Invalid team")
        self._player(player_id).team = team

    def shuffle_teams(self, player_id: str) -> None:
        self._require_host(player_id)
        self._require_phase("lobby")
        ids = list(self.players)
        self.rng.shuffle(ids)
        for i, pid in enumerate(ids):
            self.players[pid].team = i % self.num_teams

    def remove_player(self, player_id: str) -> str | None:
        """A player leaves on purpose. Returns the new host's id if the host changed."""
        player = self._player(player_id)
        if player.team is not None:
            self.left_teams[player.name.lower()] = player.team
        del self.players[player_id]
        self.touch()
        if not self.players:
            self.host_id = None
            return None

        turn = self.turn
        if self.phase == "playing" and turn and turn.describer_id == player_id:
            if turn.phase == "ready":
                # Give the same team a new describer instead of losing the turn.
                self.next_team = turn.team
                self._new_turn()
            elif turn.phase == "running":
                self.finish_turn()  # the host confirms the score in review

        if self.host_id == player_id:
            self.host_id = None
            return self.ensure_host()
        return None

    def ensure_host(self) -> str | None:
        """Hand the host role to the longest-present connected player if the
        current host is gone or offline. Returns the new host's id if it changed."""
        host = self.players.get(self.host_id) if self.host_id else None
        if host is not None and host.connected:
            return None
        candidate = next((p for p in self.players.values() if p.connected), None)
        if candidate is None and host is None and self.players:
            candidate = next(iter(self.players.values()))  # nobody online: keep a placeholder
        if candidate is None or candidate.id == self.host_id:
            return None
        self.host_id = candidate.id
        return candidate.id

    def set_themes(self, player_id: str, themes: list[str] | None) -> None:
        """Pick which themes the cards come from. None (or all of them) = everything."""
        self._require_host(player_id)
        if self.phase == "playing":
            raise GameError("Choose themes before the game starts")
        if themes:
            if any(t not in THEMES for t in themes):
                raise GameError("Unknown theme")
            picked = tuple(t for t in THEMES if t in themes)  # canonical order
            self.themes = None if len(picked) == len(THEMES) else picked
        else:
            self.themes = None
        self._build_deck()

    def _build_deck(self) -> None:
        if self.private_deck:
            self.deck = Deck(load_words(self.lang, self.themes), self.rng)
        else:
            self.deck = shared_deck(self.lang, self.themes)
        self.all_words = self.deck.words

    def team_members(self, team: int) -> list[Player]:
        return [p for p in self.players.values() if p.team == team]

    def start_game(self, player_id: str) -> None:
        self._require_host(player_id)
        if self.phase == "playing":
            raise GameError("Game already started")
        if self.mode == "teams":
            for t in range(self.num_teams):
                if len(self.team_members(t)) < 2:
                    raise GameError(f"Team {t + 1} needs at least 2 players")
        self.phase = "playing"
        self.positions = [0] * self.num_teams
        self.round_scores = []
        self.winner = None
        self.next_team = 0
        self.describer_index = [0] * self.num_teams
        self._new_turn()

    # ----- turns -----

    def start_timer(self, player_id: str, now: float | None = None) -> Turn:
        turn = self._current_turn("ready")
        if player_id != turn.describer_id:
            raise GameError("Only the describer can start")
        turn.phase = "running"
        turn.ends_at = (now or time.time()) + TURN_SECONDS
        return turn

    def toggle_word(self, player_id: str, index: int) -> None:
        turn = self._current_turn()
        if turn.phase not in ("running", "review"):
            raise GameError("The turn hasn't started")
        # Describer ticks words live; during review anyone may correct mistakes.
        if turn.phase == "running" and player_id != turn.describer_id:
            raise GameError("Only the describer can tick words")
        if not 0 <= index < len(turn.words):
            raise GameError("Invalid word")
        turn.hits ^= {index}
        if turn.phase == "review":
            turn.score = max(0, len(turn.hits) - turn.die)

    def finish_turn(self, turn_number: int | None = None) -> bool:
        """Stop the timer and go to review. Returns False if nothing changed
        (e.g. a stale timer task for an earlier turn)."""
        turn = self.turn
        if turn is None or turn.phase != "running":
            return False
        if turn_number is not None and turn.number != turn_number:
            return False
        turn.phase = "review"
        turn.ends_at = None
        turn.score = max(0, len(turn.hits) - turn.die)
        return True

    def stop_early(self, player_id: str) -> None:
        turn = self._current_turn("running")
        if player_id != turn.describer_id:
            raise GameError("Only the describer can stop the timer")
        self.finish_turn()

    def next_turn(self, player_id: str) -> None:
        """Apply the score and move on. The describer confirms the review;
        the host can also skip a turn (e.g. describer left) with 0 points."""
        turn = self._current_turn()
        is_host = player_id == self.host_id
        if turn.phase == "review":
            # The describer may have left; then the host confirms.
            if player_id != turn.describer_id and not is_host:
                raise GameError("The describer or host confirms the score")
            score = turn.score
        elif is_host:
            score = 0  # skip
        else:
            raise GameError("Only the host can skip a turn")

        if self.mode == "solo":
            # No finish line: keep a running total until the game master ends it.
            self.positions[0] += score
            self.round_scores.append(score)
            self._new_turn()
            return
        self.positions[turn.team] = min(self.target, self.positions[turn.team] + score)
        if self.positions[turn.team] >= self.target:
            self.winner = turn.team
            self.phase = "finished"
            self.turn = None
            return
        self._new_turn()

    def end_game(self, player_id: str) -> None:
        """One-phone mode: the game master stops and sees the totals."""
        self._require_host(player_id)
        if self.mode != "solo":
            raise GameError("Not possible in a team game")
        turn = self._current_turn()
        if turn.phase == "review":
            # Count the round that was just played before stopping.
            self.positions[0] += turn.score
            self.round_scores.append(turn.score)
        self.phase = "finished"
        self.turn = None

    def _new_turn(self) -> None:
        # Find the next team that has players (someone may have left).
        for _ in range(self.num_teams):
            team = self.next_team
            self.next_team = (self.next_team + 1) % self.num_teams
            members = self.team_members(team)
            if members:
                break
        else:
            raise GameError("No players left")
        describer = members[self.describer_index[team] % len(members)]
        self.describer_index[team] += 1
        self.turn_count += 1
        self.turn = Turn(
            number=self.turn_count,
            team=team,
            describer_id=describer.id,
            describer_name=describer.name,
            die=self.rng.choice(DIE_FACES),
            words=self._draw(WORDS_PER_CARD),
        )

    def _draw(self, n: int) -> list[str]:
        return self.deck.draw(n)

    # ----- views -----

    def state_for(self, player_id: str, now: float | None = None) -> dict:
        now = now or time.time()
        me = self.players.get(player_id)
        turn_state = None
        if self.turn:
            t = self.turn
            is_describer = player_id == t.describer_id
            on_turn_team = me is not None and me.team == t.team
            # Guessers must not see the words while playing; opponents may
            # (to check for cheating), just like with the physical cards.
            show_words = t.phase == "review" or (
                t.phase == "running" and (is_describer or not on_turn_team)
            )
            turn_state = {
                "number": t.number,
                "team": t.team,
                "describer_id": t.describer_id,
                "describer_name": t.describer_name,
                "describer_left": t.describer_id not in self.players,
                "die": t.die,
                "phase": t.phase,
                "words": t.words if show_words else None,
                "hits": sorted(t.hits),
                "score": t.score,
                "remaining": max(0.0, t.ends_at - now) if t.ends_at else None,
            }
        return {
            "code": self.code,
            "lang": self.lang,
            "phase": self.phase,
            "mode": self.mode,
            "themes": list(self.themes) if self.themes else None,
            "theme_counts": self.theme_counts,
            "deck_size": len(self.all_words),
            "round_scores": self.round_scores,
            "num_teams": self.num_teams,
            "target": self.target,
            "host_id": self.host_id,
            "me": player_id,
            "players": [
                {"id": p.id, "name": p.name, "team": p.team, "connected": p.connected}
                for p in self.players.values()
            ],
            "positions": self.positions,
            "winner": self.winner,
            "turn": turn_state,
            "turn_seconds": TURN_SECONDS,
        }

    # ----- helpers -----

    def touch(self) -> None:
        self.last_activity = time.time()

    def _player(self, player_id: str) -> Player:
        try:
            return self.players[player_id]
        except KeyError:
            raise GameError("Unknown player") from None

    def _require_host(self, player_id: str) -> None:
        if player_id != self.host_id:
            raise GameError("Only the host can do that")

    def _require_phase(self, phase: str) -> None:
        if self.phase != phase:
            raise GameError("Not possible right now")

    def _current_turn(self, phase: str | None = None) -> Turn:
        if self.phase != "playing" or self.turn is None:
            raise GameError("No turn in progress")
        if phase and self.turn.phase != phase:
            raise GameError("Not possible right now")
        return self.turn


def new_room_code(existing) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # no I/O to avoid confusion
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(4))
        if code not in existing:
            return code
