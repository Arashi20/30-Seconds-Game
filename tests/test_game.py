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
