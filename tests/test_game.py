import random

import pytest

from app.game import DIE_FACES, LANGUAGES, TURN_SECONDS, WORDS_PER_CARD, GameError, Room, load_words


def make_room(players=4, teams=2, target=30, seed=1):
    room = Room("TEST", lang="en", num_teams=teams, target=target, rng=random.Random(seed))
    ids = [room.add_player(f"P{i}").id for i in range(players)]
    return room, ids


def play_turn(room, hits):
    turn = room.turn
    room.start_timer(turn.describer_id)
    for i in range(hits):
        room.toggle_word(turn.describer_id, i)
    room.finish_turn()
    return turn


@pytest.mark.parametrize("lang", LANGUAGES)
def test_word_lists_are_big_and_unique(lang):
    words = load_words(lang)
    assert len(words) >= 200
    assert len(words) == len(set(words))


def test_first_player_is_host_and_teams_auto_balance():
    room, ids = make_room(players=4)
    assert room.host_id == ids[0]
    assert [len(room.team_members(t)) for t in range(2)] == [2, 2]


def test_duplicate_and_empty_names_rejected():
    room, _ = make_room(players=1)
    with pytest.raises(GameError):
        room.add_player("p0")
    with pytest.raises(GameError):
        room.add_player("   ")


def test_only_host_can_start_and_teams_need_two_players():
    room, ids = make_room(players=3)
    with pytest.raises(GameError):
        room.start_game(ids[1])
    with pytest.raises(GameError, match="at least 2"):
        room.start_game(ids[0])
    room.add_player("P3")
    room.start_game(ids[0])
    assert room.phase == "playing"
    assert room.turn.phase == "ready"
    assert len(room.turn.words) == WORDS_PER_CARD
    assert room.turn.die in DIE_FACES


def test_score_is_hits_minus_die_and_never_negative():
    room, ids = make_room()
    room.start_game(ids[0])
    turn = play_turn(room, hits=4)
    assert turn.score == max(0, 4 - turn.die)
    room.next_turn(turn.describer_id)
    assert room.positions[turn.team] == turn.score

    turn2 = room.turn
    turn2.die = 2
    play_turn(room, hits=1)
    assert turn2.score == 0


def test_only_describer_starts_and_ticks():
    room, ids = make_room()
    room.start_game(ids[0])
    turn = room.turn
    other = next(i for i in ids if i != turn.describer_id)
    with pytest.raises(GameError):
        room.start_timer(other)
    room.start_timer(turn.describer_id)
    with pytest.raises(GameError):
        room.toggle_word(other, 0)


def test_review_corrections_update_score():
    room, ids = make_room()
    room.start_game(ids[0])
    turn = room.turn
    turn.die = 0
    play_turn(room, hits=2)
    other = next(i for i in ids if i != turn.describer_id)
    room.toggle_word(other, 4)  # anyone can fix a missed tick during review
    assert turn.score == 3


def test_teams_alternate_and_describers_rotate():
    room, ids = make_room(players=4)
    room.start_game(ids[0])
    seen = []
    for _ in range(4):
        turn = room.turn
        seen.append((turn.team, turn.describer_id))
        play_turn(room, hits=0)
        room.next_turn(turn.describer_id)
    assert [team for team, _ in seen] == [0, 1, 0, 1]
    assert seen[0][1] != seen[2][1]  # team 0 had two different describers
    assert seen[1][1] != seen[3][1]


def test_guessers_cannot_see_words_but_opponents_can():
    room, ids = make_room()
    room.start_game(ids[0])
    turn = room.turn
    teammate = next(p.id for p in room.team_members(turn.team) if p.id != turn.describer_id)
    opponent = room.team_members(1 - turn.team)[0].id

    # Nobody sees the words before the timer starts.
    assert all(room.state_for(p)["turn"]["words"] is None for p in ids)

    room.start_timer(turn.describer_id, now=1000)
    assert room.state_for(turn.describer_id, now=1000)["turn"]["words"] == turn.words
    assert room.state_for(teammate, now=1000)["turn"]["words"] is None
    assert room.state_for(opponent, now=1000)["turn"]["words"] == turn.words
    assert room.state_for(opponent, now=1010)["turn"]["remaining"] == TURN_SECONDS - 10

    room.finish_turn()
    assert room.state_for(teammate)["turn"]["words"] == turn.words


def test_stale_timer_does_not_end_a_later_turn():
    room, ids = make_room()
    room.start_game(ids[0])
    first = room.turn
    room.start_timer(first.describer_id)
    room.stop_early(first.describer_id)
    room.next_turn(first.describer_id)
    room.start_timer(room.turn.describer_id)
    assert room.finish_turn(first.number) is False
    assert room.turn.phase == "running"


def test_host_can_skip_and_others_cannot():
    room, ids = make_room()
    room.start_game(ids[0])
    turn = room.turn
    non_host = next(i for i in ids if i != room.host_id)
    with pytest.raises(GameError):
        room.next_turn(non_host)
    room.next_turn(room.host_id)
    assert room.turn.number == turn.number + 1
    assert room.positions == [0, 0]


def test_reaching_target_wins_and_game_can_restart():
    room, ids = make_room(target=5)
    room.start_game(ids[0])
    turn = room.turn
    turn.die = 0
    play_turn(room, hits=5)
    room.next_turn(turn.describer_id)
    assert room.phase == "finished"
    assert room.winner == turn.team
    room.start_game(ids[0])
    assert room.phase == "playing"
    assert room.positions == [0, 0]


def test_no_repeated_words_until_deck_exhausted():
    room, ids = make_room()
    room.start_game(ids[0])
    seen = []
    for _ in range(len(room.all_words) // WORDS_PER_CARD):
        turn = room.turn
        seen += turn.words
        room.next_turn(room.host_id)  # skip
    assert len(seen) == len(set(seen))


def connect_all(room):
    for p in room.players.values():
        p.connected = True


def test_host_leaving_hands_over_to_next_connected_player():
    room, ids = make_room()
    connect_all(room)
    room.players[ids[1]].connected = False
    new_host = room.remove_player(ids[0])
    assert new_host == ids[2]  # ids[1] is offline, so skipped
    assert room.host_id == ids[2]


def test_ensure_host_only_replaces_an_offline_host():
    room, ids = make_room()
    connect_all(room)
    assert room.ensure_host() is None
    room.players[ids[0]].connected = False
    assert room.ensure_host() == ids[1]
    room.players[ids[0]].connected = True
    assert room.ensure_host() is None  # old host is back, but isn't host anymore
    assert room.host_id == ids[1]


def test_ensure_host_with_nobody_online_keeps_host():
    room, ids = make_room()
    assert room.ensure_host() is None
    assert room.host_id == ids[0]


def test_describer_leaving_before_start_gives_team_a_new_describer():
    room, ids = make_room(players=6)
    room.start_game(ids[0])
    turn = room.turn
    room.remove_player(turn.describer_id)
    assert room.turn.team == turn.team
    assert room.turn.describer_id != turn.describer_id
    assert room.turn.describer_id in room.players


def test_describer_leaving_mid_turn_ends_turn_and_host_confirms():
    room, ids = make_room(players=6)
    connect_all(room)
    room.start_game(ids[0])
    turn = room.turn
    if turn.describer_id == room.host_id:  # make sure host and describer differ
        room.next_turn(room.host_id)
        turn = room.turn
    turn.die = 0
    room.start_timer(turn.describer_id)
    room.toggle_word(turn.describer_id, 0)
    room.remove_player(turn.describer_id)
    assert turn.phase == "review"
    room.next_turn(room.host_id)
    assert room.positions[turn.team] == 1


def test_last_player_leaving_empties_room():
    room, ids = make_room(players=1)
    assert room.remove_player(ids[0]) is None
    assert room.players == {}
    assert room.host_id is None


def test_offline_player_can_take_their_seat_back_by_name():
    room, ids = make_room()
    room.start_game(ids[0])
    bob = room.players[ids[1]]
    bob.was_online = True  # was playing, then the phone died
    room.positions = [5, 3]
    again = room.add_player("p1")  # same name, different case
    assert again.id == bob.id and again.team == bob.team
    assert len(room.players) == 4
    assert room.positions == [5, 3]


def test_name_of_online_or_never_connected_player_stays_taken():
    room, ids = make_room()
    with pytest.raises(GameError):
        room.add_player("P1")  # never connected yet (e.g. joining right now)
    room.players[ids[1]].connected = room.players[ids[1]].was_online = True
    with pytest.raises(GameError):
        room.add_player("P1")  # online


def test_player_who_left_returns_to_their_old_team():
    room, ids = make_room(players=4)
    room.start_game(ids[0])
    host_team = room.players[ids[0]].team
    room.remove_player(ids[0])
    # Auto-balance alone would also pick this team; make it ambiguous first.
    room.left_teams["p0"] = 1 - host_team
    back = room.add_player("P0")
    assert back.team == 1 - host_team


def test_leaving_never_moves_other_players_or_points():
    for phase in ("lobby", "ready", "running", "review"):
        for leaver in range(4):
            room, ids = make_room(players=4, seed=leaver)
            connect_all(room)
            teams_before = {pid: p.team for pid, p in room.players.items()}
            if phase != "lobby":
                room.start_game(ids[0])
                room.positions = [7, 4]
                if phase != "ready":
                    room.start_timer(room.turn.describer_id)
                if phase == "review":
                    room.finish_turn()
            room.remove_player(ids[leaver])
            teams_after = {pid: p.team for pid, p in room.players.items()}
            assert teams_after == {pid: t for pid, t in teams_before.items() if pid != ids[leaver]}
            assert room.positions == ([0, 0] if phase == "lobby" else [7, 4])
            assert room.host_id in room.players


def test_new_rooms_continue_the_shared_deck():
    from app.game import WORDS_PER_CARD, load_words, shared_deck

    deck = shared_deck("nl")
    deck.pile = []  # start from a fresh shuffle
    seen = []
    rounds = len(load_words("nl")) // WORDS_PER_CARD // 2
    for i in range(rounds):
        room = Room(f"R{i}", lang="nl")  # a brand-new game every time
        assert room.deck is deck
        ids = [room.add_player(f"P{j}").id for j in range(4)]
        room.start_game(ids[0])
        seen += room.turn.words
    assert len(seen) == len(set(seen))  # no word came back across all those games


MIN_WORDS = {"nl": 1000, "en": 1000, "fa": 700}


def test_word_lists_have_no_near_duplicates():
    import re
    import unicodedata

    def key(word):
        w = unicodedata.normalize("NFKD", word.casefold())
        return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if not unicodedata.combining(c)))

    for lang in LANGUAGES:
        words = load_words(lang)
        assert len(words) >= MIN_WORDS[lang]
        keys = [key(w) for w in words]
        assert len(keys) == len(set(keys)), [w for w, k in zip(words, keys) if keys.count(k) > 1]


# ----- one-phone mode -----

def make_solo(seed=1):
    room = Room("SOLO", lang="en", mode="solo", rng=random.Random(seed))
    host = room.add_player("Arash").id
    return room, host


def test_solo_starts_with_just_the_game_master_and_nobody_can_join():
    room, host = make_solo()
    with pytest.raises(GameError, match="one phone"):
        room.add_player("Sam")
    room.start_game(host)
    assert room.turn.describer_id == host
    assert room.num_teams == 1


def test_solo_keeps_a_running_total_until_the_game_master_ends_it():
    room, host = make_solo()
    room.start_game(host)
    total = 0
    for hits in (5, 3, 0, 4):
        turn = room.turn
        turn.die = 1
        room.start_timer(host)
        for i in range(hits):
            room.toggle_word(host, i)
        room.finish_turn()
        room.next_turn(host)
        total += max(0, hits - 1)
    assert room.phase == "playing"  # no finish line, even past the target
    assert room.round_scores == [4, 2, 0, 3]
    assert room.positions == [total]

    turn = room.turn  # the last round is counted when ending from review
    turn.die = 0
    room.start_timer(host)
    room.toggle_word(host, 0)
    room.finish_turn()
    room.end_game(host)
    assert room.phase == "finished"
    assert room.round_scores[-1] == 1 and room.positions == [total + 1]
    room.start_game(host)  # play again
    assert room.positions == [0] and room.round_scores == []


def test_end_game_is_only_for_one_phone_mode():
    room, ids = make_room()
    room.start_game(ids[0])
    with pytest.raises(GameError):
        room.end_game(ids[0])


# ----- themes -----

def test_every_word_has_a_known_theme_and_themes_are_not_tiny():
    from app.game import THEMES, load_themes

    for lang in LANGUAGES:
        by_theme = load_themes(lang)
        assert set(by_theme) == set(THEMES)
        assert all(len(words) >= 30 for words in by_theme.values())
        assert sum(len(w) for w in by_theme.values()) == len(load_words(lang))


def test_host_can_filter_themes_before_the_game():
    from app.game import load_themes

    room, ids = make_room()
    animals = set(load_themes("en")["animals"])
    food = set(load_themes("en")["food"])
    with pytest.raises(GameError):
        room.set_themes(ids[1], ["animals"])  # not the host
    room.set_themes(ids[0], ["animals", "food"])
    assert room.themes == ("food", "animals")  # stored in THEMES order
    assert set(room.all_words) == animals | food
    room.start_game(ids[0])
    for _ in range(20):
        assert set(room.turn.words) <= animals | food
        room.next_turn(ids[0])  # host skips
    with pytest.raises(GameError, match="before the game"):
        room.set_themes(ids[0], None)


def test_all_or_no_themes_means_the_full_deck():
    from app.game import THEMES

    room, ids = make_room()
    room.set_themes(ids[0], list(THEMES))
    assert room.themes is None
    room.set_themes(ids[0], ["food"])
    room.set_themes(ids[0], [])
    assert room.themes is None and len(room.all_words) == len(load_words("en"))
    with pytest.raises(GameError):
        room.set_themes(ids[0], ["bogus"])
