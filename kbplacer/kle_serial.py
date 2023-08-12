from __future__ import annotations

import argparse
import copy
import json
import pprint
from dataclasses import asdict, dataclass, field, fields
from typing import Any, List, Optional, Tuple, Type

DEFAULT_KEY_COLOR = "#cccccc"
DEFAULT_TEXT_COLOR = "#000000"
DEFAULT_TEXT_SIZE = 3

# Map from serialized label position to normalized position,
# depending on the alignment flags.
# fmt: off
LABEL_MAP: List[List[int]] = [
    # 0  1  2  3  4  5  6  7  8  9 10 11   # align flags
    [ 0, 6, 2, 8, 9,11, 3, 5, 1, 4, 7,10], # 0 = no centering
    [ 1, 7,-1,-1, 9,11, 4,-1,-1,-1,-1,10], # 1 = center x
    [ 3,-1, 5,-1, 9,11,-1,-1, 4,-1,-1,10], # 2 = center y
    [ 4,-1,-1,-1, 9,11,-1,-1,-1,-1,-1,10], # 3 = center x & y
    [ 0, 6, 2, 8,10,-1, 3, 5, 1, 4, 7,-1], # 4 = center front (default)
    [ 1, 7,-1,-1,10,-1, 4,-1,-1,-1,-1,-1], # 5 = center front & x
    [ 3,-1, 5,-1,10,-1,-1,-1, 4,-1,-1,-1], # 6 = center front & y
    [ 4,-1,-1,-1,10,-1,-1,-1,-1,-1,-1,-1], # 7 = center front & x & y
]

REVERSE_LABEL_MAP: List[List[int]] = [
    # 0  1  2  3  4  5  6  7  8  9 10 11   # align flags
    [ 0, 8, 2, 6, 9, 7, 1,10, 3, 4,11, 5], # 0 = no centering
    [-1, 0,-1,-1, 6,-1,-1, 1,-1, 4,11, 5], # 1 = center x
    [-1,-1,-1, 0, 8, 2,-1,-1,-1, 4,11, 5], # 2 = center y
    [-1,-1,-1,-1, 0,-1,-1,-1,-1, 4,11, 5], # 3 = center x & y
    [ 0, 8, 2, 6, 9, 7, 1,10, 3,-1, 4,-1], # 4 = center front (default)
    [-1, 0,-1,-1, 6,-1,-1, 1,-1,-1, 4,-1], # 5 = center front & x
    [-1,-1,-1, 0, 8, 2,-1,-1,-1,-1, 4,-1], # 6 = center front & y
    [-1,-1,-1,-1, 0,-1,-1,-1,-1,-1, 4,-1], # 7 = center front & x & y
]
# fmt: on


@dataclass
class KeyDefault:
    textColor: str = DEFAULT_TEXT_COLOR
    textSize: int = DEFAULT_TEXT_SIZE


@dataclass
class Key:
    color: str = DEFAULT_KEY_COLOR
    labels: List[str] = field(default_factory=list)
    textColor: List[Optional[str]] = field(default_factory=list)
    textSize: List[Optional[int]] = field(default_factory=list)
    default: KeyDefault = field(default_factory=KeyDefault)
    x: float = 0
    y: float = 0
    width: float = 1
    height: float = 1
    x2: float = 0
    y2: float = 0
    width2: float = 1
    height2: float = 1
    rotation_x: float = 0
    rotation_y: float = 0
    rotation_angle: float = 0
    decal: bool = False
    ghost: bool = False
    stepped: bool = False
    nub: bool = False
    profile: str = ""
    sm: str = ""  # switch mount
    sb: str = ""  # switch brand
    st: str = ""  # switch type

    def __post_init__(self: Key) -> None:
        if isinstance(self.default, dict):
            self.default = KeyDefault(**self.default)


@dataclass
class Background:
    name: str = ""
    style: str = ""


@dataclass
class KeyboardMetadata:
    author: str = ""
    backcolor: str = "#eeeeee"
    background: Optional[Background] = None
    name: str = ""
    notes: str = ""
    radii: str = ""
    switchBrand: str = ""
    switchMount: str = ""
    switchType: str = ""

    def __post_init__(self: KeyboardMetadata) -> None:
        if isinstance(self.background, dict):
            self.background = Background(**self.background)


@dataclass
class Keyboard:
    meta: KeyboardMetadata = field(default_factory=KeyboardMetadata)
    keys: List[Key] = field(default_factory=list)

    @classmethod
    def from_json(cls: Type[Keyboard], data: dict) -> Keyboard:
        if isinstance(data["meta"], dict):
            data["meta"] = KeyboardMetadata(**data["meta"])
        if isinstance(data["keys"], list):
            keys: List[Key] = [Key(**key) for key in data["keys"]]
            data["keys"] = keys
        return cls(**data)

    def to_json(self: Keyboard, indent: Optional[int] = None) -> str:
        return json.dumps(asdict(self), indent=indent)

    def __text_size_changed(self: Keyboard, current: list[Any], new: list[Any]) -> bool:
        current = copy.copy(current)
        new = copy.copy(new)
        for obj in [current, new]:
            if len_difference := 12 - len(obj):
                obj.extend(len_difference * [0])
        return current != new

    def to_kle(self: Keyboard) -> str:
        row = []
        rows = []

        current: Key = copy.deepcopy(Key())
        # some properties are not part of Key type, store them separately:
        current_alignment = 4
        current_f2 = -1
        # rotation origin:
        cluster: dict[str, float] = {"r": 0, "rx": 0, "ry": 0}

        new_row = True
        current.y -= 1  # will be incremented on first row

        for key in self.keys:
            props: dict[str, Any] = {}

            def add_prop(name: str, value: Any, default: Any) -> Any:
                if value != default:
                    props[name] = value
                return value

            if key.labels:
                alignment, labels = find_best_label_alignment(key.labels)
            else:
                alignment, labels = 7, []

            # detect new row
            new_cluster = (
                key.rotation_angle != cluster["r"]
                or key.rotation_x != cluster["rx"]
                or key.rotation_y != cluster["ry"]
            )
            new_row = key.y != current.y
            if row and (new_cluster or new_row):
                # push the old row
                rows.append(row)
                row = []
                new_row = True

            if new_row:
                current.y += 1
                # 'y' is reset if either 'rx' or 'ry' are changed
                if key.rotation_y != cluster["ry"] or key.rotation_x != cluster["rx"]:
                    current.y = key.rotation_y
                # always reset x to rx (which defaults to zero)
                current.x = key.rotation_x

                cluster["r"] = key.rotation_angle
                cluster["rx"] = key.rotation_x
                cluster["ry"] = key.rotation_y

                new_row = False

            current.rotation_angle = add_prop(
                "r", key.rotation_angle, current.rotation_angle
            )
            current.rotation_x = add_prop("rx", key.rotation_x, current.rotation_x)
            current.rotation_y = add_prop("ry", key.rotation_y, current.rotation_y)

            current.x += add_prop("x", key.x - current.x, 0) + key.width
            current.y += add_prop("y", key.y - current.y, 0)

            current.color = add_prop("c", key.color, current.color)
            if text_color := reorder_items_kle(key.textColor, alignment):
                if not text_color[0]:
                    text_color[0] = key.default.textColor
                text_color = ["" if not item else item for item in text_color]
                text_color = "\n".join(text_color).rstrip("\n")
                current.textColor = add_prop("t", text_color, current.textColor)
            else:
                current.default.textColor = add_prop(
                    "t", key.default.textColor, current.default.textColor
                )

            current.ghost = add_prop("g", key.ghost, current.ghost)
            current.profile = add_prop("p", key.profile, current.profile)
            current.sm = add_prop("sm", key.sm, current.sm)
            current.sb = add_prop("sb", key.sb, current.sb)
            current.st = add_prop("st", key.st, current.st)

            current_alignment = add_prop("a", alignment, current_alignment)
            current.default.textSize = add_prop(
                "f", key.default.textSize, current.default.textSize
            )
            if "f" in props:
                current.textSize = []

            text_size = reorder_items_kle(key.textSize, alignment)
            text_size = [0 if not isinstance(i, int) else i for i in text_size]
            if self.__text_size_changed(current.textSize, text_size):
                if not text_size:
                    current.default.textSize = add_prop(
                        "f", key.default.textSize, current.default.textSize
                    )
                    current.textSize = []
                else:
                    # todo: handle f2 optimization
                    if optimize := not text_size[0]:
                        optimize = all(x == text_size[1] for x in text_size[2:])
                    if optimize:
                        f2 = text_size[1]
                        current_f2 = add_prop("f2", f2, current_f2)
                        # don't know why this gives type checking error, works fine:
                        current.textSize = [0] + (11 * [f2])  # type: ignore
                    else:
                        current.textSize = add_prop("fa", text_size, [])

            add_prop("w", key.width, 1)
            add_prop("h", key.height, 1)
            add_prop("w2", key.width2, key.width)
            add_prop("h2", key.height2, key.height)
            add_prop("x2", key.x2, 0)
            add_prop("y2", key.y2, 0)
            add_prop("l", key.stepped, False)
            add_prop("n", key.nub, False)
            add_prop("d", key.decal, False)

            if props:
                row.append(props)

            current.labels = labels
            labels = ["" if not item else item for item in labels]
            row.append("\n".join(labels).rstrip("\n"))

        if row:
            rows.append(row)

        result = ""

        default_meta = asdict(KeyboardMetadata())
        meta = copy.deepcopy(asdict(self.meta))
        if meta != default_meta:
            # include only non-default meta fields
            for k in list(meta.keys()):
                if default_meta.get(k, None) == meta[k]:
                    del meta[k]
            result += json.dumps(meta, indent=None) + ",\n"

        for row in rows:
            result += json.dumps(row, indent=None) + ",\n"
        result = result.strip(",\n")
        return result


def reorder_items(items: List[Any], align: int) -> List[Any]:
    ret: List[Any] = 12 * [None]
    for i, item in enumerate(items):
        if item:
            index = LABEL_MAP[align][i]
            ret[index] = item
    while ret and ret[-1] is None:
        ret.pop()
    return ret


def reorder_items_kle(items, align) -> List[Any]:
    ret: List[Any] = 12 * [None]
    for i, label in enumerate(items):
        if label:
            index = REVERSE_LABEL_MAP[align][i]
            if index == -1:
                ret = []
                break
            ret[index] = label
    while ret and ret[-1] is None:
        ret.pop()
    return ret


def find_best_label_alignment(labels) -> Tuple[int, List[Any]]:
    results = {}
    for align in reversed(range(0, 8)):
        if ret := reorder_items_kle(labels, align):
            results[align] = ret

    if results.items():
        best = min(results.items(), key=lambda x: len(x[1]))
        return best[0], best[1]
    else:
        return 0, []


def cleanup_key(key: Key):
    for attribute_name in ["textSize", "textColor"]:
        attribute = getattr(key, attribute_name)
        attribute = attribute[0 : len(key.labels)]
        for i, (label, val) in enumerate(zip(key.labels, attribute)):
            if not label:
                attribute[i] = None
            if val == getattr(key.default, attribute_name):
                attribute[i] = None
        while attribute and attribute[-1] is None:
            attribute.pop()
        setattr(key, attribute_name, attribute)


def parse(layout) -> Keyboard:
    if not isinstance(layout, list):
        msg = "Expected an list of objects"
        raise RuntimeError(msg)

    metadata: KeyboardMetadata = KeyboardMetadata()
    rows: List[Any] = layout
    current: Key = Key()

    if not rows:
        msg = "Expected at least one row of keys"
        raise RuntimeError(msg)

    keys = []
    cluster = {"x": 0, "y": 0}
    align = 4

    for r, row in enumerate(rows):
        if isinstance(row, list):
            for k, item in enumerate(row):
                if isinstance(item, str):
                    new_key = copy.deepcopy(current)
                    # Calculate some generated values
                    new_key.width2 = (
                        current.width if new_key.width2 == 0 else current.width2
                    )
                    new_key.height2 = (
                        current.height if new_key.height2 == 0 else current.height2
                    )
                    new_key.labels = reorder_items(item.split("\n"), align)
                    new_key.textSize = reorder_items(new_key.textSize, align)

                    cleanup_key(new_key)

                    keys.append(new_key)

                    current.x += current.width
                    current.width = 1
                    current.height = 1
                    current.x2 = 0
                    current.y2 = 0
                    current.width2 = 0
                    current.height2 = 0
                    current.nub = False
                    current.stepped = False
                    current.decal = False
                elif isinstance(item, dict):
                    if k != 0 and ("r" in item or "rx" in item or "ry" in item):
                        msg = (
                            "Rotation can only be specified on the first key in the row"
                        )
                        raise RuntimeError(msg)
                    if "r" in item:
                        current.rotation_angle = item["r"]
                    if "rx" in item:
                        cluster["x"] = item["rx"]
                        current.x = cluster["x"]
                        current.y = cluster["y"]
                        current.rotation_x = item["rx"]
                    if "ry" in item:
                        cluster["y"] = item["ry"]
                        current.x = cluster["x"]
                        current.y = cluster["y"]
                        current.rotation_y = item["ry"]
                    if "a" in item:
                        align = item["a"]
                    if "f" in item:
                        current.default.textSize = item["f"]
                        current.textSize = []
                    if "f2" in item:
                        if len(current.textSize) == 0:
                            current.textSize = [None]
                        for _ in range(1, 12):
                            current.textSize.append(item["f2"])
                    if "fa" in item:
                        current.textSize = item["fa"]
                    if "p" in item:
                        current.profile = item["p"]
                    if "c" in item:
                        current.color = item["c"]
                    if "t" in item:
                        split = item["t"].split("\n")
                        if split[0]:
                            current.default.textColor = split[0]
                        current.textColor = reorder_items(split, align)
                    if "x" in item:
                        current.x += item["x"]
                    if "y" in item:
                        current.y += item["y"]
                    if "w" in item:
                        current.width = item["w"]
                        current.width2 = item["w"]
                    if "h" in item:
                        current.height = item["h"]
                        current.height2 = item["h"]
                    if "x2" in item:
                        current.x2 = item["x2"]
                    if "y2" in item:
                        current.y2 = item["y2"]
                    if "w2" in item:
                        current.width2 = item["w2"]
                    if "h2" in item:
                        current.height2 = item["h2"]
                    if "n" in item:
                        current.nub = item["n"]
                    if "l" in item:
                        current.stepped = item["l"]
                    if "d" in item:
                        current.decal = item["d"]
                    if "g" in item:
                        current.ghost = item["g"]
                    if "sm" in item:
                        current.sm = item["sm"]
                    if "sb" in item:
                        current.sb = item["sb"]
                    if "st" in item:
                        current.st = item["st"]
                else:
                    msg = "Unexpected item type"
                    raise RuntimeError(msg)

            # end of the row:
            current.y += 1
            current.x = current.rotation_x
        elif isinstance(row, dict) and r == 0:
            field_set = {f.name for f in fields(KeyboardMetadata) if f.init}
            row_filtered = {k: v for k, v in row.items() if k in field_set}
            metadata = KeyboardMetadata(**row_filtered)
        else:
            msg = "Unexpected"
            raise RuntimeError(msg)

    return Keyboard(meta=metadata, keys=keys)


def get_keyboard(layout: dict) -> Keyboard:
    try:
        return parse(layout)
    except Exception:
        pass
    try:
        return Keyboard.from_json(layout)
    except Exception:
        pass
    msg = "Unable to get keyboard layout"
    raise RuntimeError(msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KLE format converter")
    parser.add_argument("-in", required=True, help="Layout file")
    parser.add_argument(
        "-inform",
        required=False,
        default="RAW",
        choices=["RAW", "INTERNAL"],
        help="Specifies the input format",
    )
    parser.add_argument("-out", required=False, help="Result json file")
    parser.add_argument(
        "-text", required=False, action="store_true", help="Print result"
    )

    args = parser.parse_args()
    input_path = getattr(args, "in")
    input_format = args.inform
    result_path = getattr(args, "out")
    print_result = args.text

    with open(input_path, "r") as f:
        text_input = f.read()
        layout = json.loads(text_input)

        if "RAW" == input_format:
            result = parse(layout)
            result = json.loads(result.to_json())
            if print_result:
                pprint.pprint(result)
        else:
            keyboard = Keyboard.from_json(layout)
            result = keyboard.to_kle()
            if print_result:
                print(result)

        if result_path:
            # 'to_kle' returns 'raw data' string which can be copy pasted
            # to keyboard-layout-editor, to make json out of it we need
            # to wrap it in list. Then it can be uploaded as JSON.
            if "INTERNAL" == input_format:
                result = "[" + result + "]"
                result = json.loads(result)
            with open(result_path, "w") as f:
                json.dump(result, f, indent=4)
