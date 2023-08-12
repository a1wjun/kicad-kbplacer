import json
from pathlib import Path

import pytest

try:
    from kbplacer.kle_serial import Keyboard, parse
except:
    pass


def __minify(string: str) -> str:
    for ch in ["\n", " "]:
        string = string.replace(ch, "")
    return string


# single key layouts with various labels:
@pytest.mark.parametrize(
    # fmt: off
    "layout,expected",
    [
        ([["x"]],                         [          "x"]), # top-left
        ([[{"a":5},"x"]],                 [None,     "x"]), # top-center
        ([["\n\nx"]],                (2 * [None]) + ["x"]), # top-right
        ([[{"a":6},"x"]],            (3 * [None]) + ["x"]), # center-left
        ([[{"a":7},"x"]],            (4 * [None]) + ["x"]), # center
        ([[{"a":6},"\n\nx"]],        (5 * [None]) + ["x"]), # center-right
        ([["\nx"]],                  (6 * [None]) + ["x"]), # bottom-left
        ([[{"a":5},"\nx"]],          (7 * [None]) + ["x"]), # bottom-center
        ([["\n\n\nx"]],              (8 * [None]) + ["x"]), # bottom-right
        ([[{"a":3},"\n\n\n\nx"]],    (9 * [None]) + ["x"]), # front-left
        ([[{"a":7},"\n\n\n\nx"]],   (10 * [None]) + ["x"]), # fron-center
        ([[{"a":3},"\n\n\n\n\nx"]], (11 * [None]) + ["x"]), # front-right
        ([[{"a":0},"x\nx\nx\nx\nx\nx\nx\nx\nx\nx\nx\nx"]], (12 * ["x"])) # all at once
    ],
    # fmt: on
)
def test_labels(layout, expected) -> None:
    result = parse(layout)
    assert result.keys[0].labels == expected
    # check if reverse operation works as well:
    assert [json.loads(result.to_kle())] == layout


@pytest.mark.parametrize(
    # fmt: off
    "layout,expected_labels,expected_text_size",
    [
        ([[{"fa":[6]},"x"]],         [          "x"], [               6]),
        ([[{"a":5,"fa":[6]},"x"]],   [     None,"x"], [          None,6]),
        ([[{"fa":[0,0,6]},"\n\nx"]], [None,None,"x"], [     None,None,6]),
        ([[{"f2":6},"\nx"]],    (6 * [None]) + ["x"], (6 * [None]) + [6]),
    ],
    # fmt: on
)
def test_labels_text_size(layout, expected_labels, expected_text_size) -> None:
    result = parse(layout)
    assert result.keys[0].labels == expected_labels
    assert result.keys[0].textSize == expected_text_size
    # check if reverse operation works as well:
    assert [json.loads(result.to_kle())] == layout


def test_labels_colors() -> None:
    # fmt: off
    layout = [[
        {"t": "#ff0000\n\n\n\n\n\n\n\n\n\n#0018ff"},"x\n\n\n\n\n\n\n\n\n\nx",
        {"t": "#ff0000\n\n\n\n\n\n\n\n\n#736827"},"x\n\n\n\n\n\n\n\n\nx",
        {"t": "#210e0e\n\n\n\n\n\n\n\n\n#736827"},"x\n\n\n\n\n\n\n\n\nx\nx",
        {"t": "#000000\n\n\n\n\n\n\n\n\n#a80000"},"x\n\n\n\n\n\n\n\n\nx\nx",
    ]]
    # fmt: on
    result = parse(layout)
    assert [json.loads(result.to_kle())] == layout


def test_if_produces_valid_json() -> None:
    result = parse([["x"]])
    assert (
        result.to_json() == '{"meta": '
        '{"author": "", "backcolor": "#eeeeee", "background": null, "name": "", '
        '"notes": "", "radii": "", "switchBrand": "", "switchMount": "", "switchType": ""}, '
        '"keys": [{"color": "#cccccc", "labels": ["x"], "textColor": [], "textSize": [], '
        '"default": {"textColor": "#000000", "textSize": 3}, "x": 0, "y": 0, "width": 1, '
        '"height": 1, "x2": 0, "y2": 0, "width2": 1, "height2": 1, "rotation_x": 0, '
        '"rotation_y": 0, "rotation_angle": 0, "decal": false, "ghost": false, "stepped": false, '
        '"nub": false, "profile": "", "sm": "", "sb": "", "st": ""}]}'
    )


def __get_invalid_parse_parameters():
    test_params = []
    test_params.append(pytest.param([], id="empty-list"))
    test_params.append(pytest.param({}, id="empty-dict"))
    test_params.append(pytest.param("", id="empty-string"))
    test_params.append(pytest.param('[["x"]]', id="some-string"))
    test_params.append(pytest.param(["", ""], id="list-of-unexpected-type"))
    test_params.append(pytest.param([{}, {}], id="list-with-wrong-dict-position"))
    test_params.append(pytest.param([[], {}], id="list-with-wrong-dict-position-2"))
    return test_params


@pytest.mark.parametrize("input_object", __get_invalid_parse_parameters())
def test_parse_invalid_schema(input_object) -> None:
    with pytest.raises(RuntimeError):
        parse(input_object)


def test_parse_invalid_key_rotation() -> None:
    with pytest.raises(RuntimeError):
        # Rotation can only be specified on the first key in the row
        layout = [["0", {"r": 15, "rx": 1, "ry": 2}, "1"]]
        parse(layout)


def test_keyboard_from_invalid_type() -> None:
    with pytest.raises(TypeError):
        Keyboard.from_json("{}")  # type: ignore


def test_keyboard_from_invalid_schema() -> None:
    with pytest.raises(KeyError):
        Keyboard.from_json({})  # type: ignore


def get_reference(path: str):
    with open(path, "r") as f:
        layout: str = f.read()
        reference_dict = json.loads(layout)
        return Keyboard.from_json(reference_dict)


def __get_parameters():
    test_params = []
    # some standard layouts and complex samples from keyboard-layout-editor.com
    kle_presets = [
        "ansi-104-big-ass-enter",
        "ansi-104",
        "apple-wireless",
        "atreus",
        "ergodox",
        "iso-105",
        "kinesis-advantage",
        "symbolics-spacecadet",
    ]
    for f in kle_presets:
        param = pytest.param(
            f"./data/kle-layouts/{f}.json",
            f"./data/kle-layouts/{f}-internal.json",
            id=f,
        )
        test_params.append(param)

    examples = ["2x2", "3x2-sizes", "2x3-rotations", "1x4-rotations-90-step"]
    for e in examples:
        param = pytest.param(
            f"../examples/{e}/kle.json", f"../examples/{e}/kle-internal.json", id=e
        )
        test_params.append(param)

    return test_params


@pytest.mark.parametrize("layout_file,reference_file", __get_parameters())
def test_with_references(layout_file, reference_file, request) -> None:
    test_dir = request.fspath.dirname

    reference = get_reference(Path(test_dir) / reference_file)

    with open(Path(test_dir) / layout_file, "r") as f:
        layout = json.load(f)
        result = parse(layout)
        assert result == reference

        f.seek(0)
        kle_result = json.loads("[" + __minify(result.to_kle()) + "]")
        expected = json.loads(__minify(f.read()))
        assert kle_result == expected
