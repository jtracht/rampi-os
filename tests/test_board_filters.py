import array
import math
import runpy
from pathlib import Path

import pytest
from rampi.config import Settings
from rampi.kanban import Board, Card


def test_filters_combine_without_changing_source_or_losing_options():
    cards = [
        Card("1", "VPN", "Blocked", "Routing", "high", "Infra"),
        Card("2", "Layout", "Review", "Keyboard", "normal", "UI"),
        Card("3", "Keys", "Review", "Routing", "high", "Infra"),
    ]
    board = Board(cards=cards)
    view = board.view("routing", "Infra", "high", "Review", ["Review", "Blocked"])
    assert view["count"] == 1 and view["total"] == 3
    assert view["columns"][0]["cards"][0]["id"] == "3"
    assert view["projects"] == ["Infra", "UI"]
    assert view["priorities"] == ["high", "normal"]
    assert board.cards == cards and board.columns == ["Offen", "In Arbeit", "Review", "Erledigt"]
    assert board.view()["count"] == 3


def test_custom_order_keeps_unknown_states_and_empty_columns():
    board = Board(cards=[Card("1", "Task", "External")])
    result = board.view("does not match", columns=["Review", "New"])
    assert [column["name"] for column in result["columns"]] == ["Review", "New", "External"]
    assert result["count"] == 0 and "External" in result["statuses"]


@pytest.mark.parametrize(
    "columns",
    [["Same", "Same"], [""], [" Bad"], ["A\nB"], ["x"] * 33, ["x" * 81], "Not a list", [{}]],
)
def test_invalid_columns_cannot_replace_personal_configuration(tmp_path, columns):
    target = tmp_path / "settings.json"
    original = Settings(board_columns=["Review", "Done"])
    original.save(target)
    with pytest.raises(ValueError):
        Settings(board_columns=columns).save(target)
    assert Settings.load(target) == original


def test_tone_verification_rejects_silence_and_wrong_frequency(tmp_path):
    verify = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/test-streaming.py"))[
        "verify_audio"
    ]
    audio = tmp_path / "audio.raw"
    assert not verify(audio)
    audio.write_bytes(bytes(48000 * 4))
    assert not verify(audio)
    for frequency, accepted in [(440, False), (997, True)]:
        pcm = array.array("h")
        for i in range(48000):
            value = int(5000 * math.sin(2 * math.pi * frequency * i / 48000))
            pcm.extend([value, value])
        audio.write_bytes(pcm.tobytes())
        assert verify(audio) is accepted
