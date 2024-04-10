import copy
import ctypes
import json
import logging
import os
import subprocess
import sys
import time

import pytest
from PIL import ImageGrab
from pyvirtualdisplay.smartdisplay import DisplayTimeoutError, SmartDisplay

from kbplacer.kbplacer_dialog import load_window_state_from_log

if sys.platform == "win32":
    from ctypes.wintypes import DWORD, HWND, RECT

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_STATE = {
    "switch_section": {
        "layout_path": "",
        "key_distance": [19.05, 19.05],
        "element_info": {
            "annotation_format": "SW{}",
            "position": {
                "x": 0.0,
                "y": 0.0,
                "orientation": 0.0,
                "side": "Front",
            },
            "position_option": "Default",
            "template_path": "",
        },
    },
    "switch_diodes_section": {
        "enable": True,
        "route_switches_with_diodes": True,
        "element_info": {
            "annotation_format": "D{}",
            "position": {
                "x": 5.08,
                "y": 3.03,
                "orientation": 90.0,
                "side": "Back",
            },
            "position_option": "Default",
            "template_path": "",
        },
    },
    "additional_elements": {
        "elements_info": [
            {
                "annotation_format": "ST{}",
                "position": {
                    "x": 0.0,
                    "y": 0.0,
                    "orientation": 0.0,
                    "side": "Front",
                },
                "position_option": "Custom",
                "template_path": "",
            }
        ],
    },
    "misc_section": {
        "route_rows_and_columns": True,
        "template_path": "",
        "generate_outline": False,
        "outline_delta": 0.0,
    },
}

CUSTOM_WINDOW_STATE_EXAMPLE1 = {
    "switch_section": {
        "layout_path": "/home/user/kle.json",
        "key_distance": [18, 18],
        "element_info": {
            "annotation_format": "KEY{}",
            "position": {
                "x": 0.0,
                "y": 0.0,
                "orientation": 90.0,
                "side": "Back",
            },
            "position_option": "Default",
            "template_path": "",
        },
    },
    "switch_diodes_section": {
        "enable": False,
        "route_switches_with_diodes": False,
        "element_info": {
            "annotation_format": "D{}",
            "position": {
                "x": -5.0,
                "y": 5.5,
                "orientation": 180.0,
                "side": "Front",
            },
            "position_option": "Custom",
            "template_path": "",
        },
    },
    "additional_elements": {
        "elements_info": [
            {
                "annotation_format": "ST{}",
                "position": {
                    "x": 0.0,
                    "y": -5.0,
                    "orientation": 0.0,
                    "side": "Front",
                },
                "position_option": "Custom",
                "template_path": "",
            },
            {
                "annotation_format": "LED{}",
                "position": None,
                "position_option": "Relative",
                "template_path": "/home/user/led_template.kicad_pcb",
            },
        ],
    },
    "misc_section": {
        "route_rows_and_columns": False,
        "template_path": "/home/user/template.kicad_pcb",
        "generate_outline": True,
        "outline_delta": 1.5,
    },
}


class LinuxVirtualScreenManager:
    def __enter__(self):
        self.display = SmartDisplay(backend="xvfb", size=(960, 640))
        self.display.start()
        return self

    def __exit__(self, *exc):
        self.display.stop()
        return False

    def screenshot(self, window_name, path):
        try:
            img = self.display.waitgrab(timeout=5)
            img.save(path)
            return True
        except DisplayTimeoutError as err:
            logger.error(err)
            return False


class HostScreenManager:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def screenshot(self, window_name, path):
        try:
            time.sleep(1)
            window_handle = find_window(window_name)
            window_rect = get_window_position(window_handle)
            img = ImageGrab.grab()
            if window_rect:
                img = img.crop(window_rect)
            img.save(path)
            return True
        except Exception as err:
            logger.error(err)
            return False


def find_window(name):
    if sys.platform != "win32":
        return None
    user32 = ctypes.windll.user32
    return user32.FindWindowW(None, name)


def get_window_position(window_handle):
    if sys.platform != "win32":
        return None
    dwmapi = ctypes.windll.dwmapi
    # based on https://stackoverflow.com/a/67137723
    rect = RECT()
    DMWA_EXTENDED_FRAME_BOUNDS = 9
    dwmapi.DwmGetWindowAttribute(
        HWND(window_handle),
        DWORD(DMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    return (rect.left, rect.top, rect.right, rect.bottom)


def run_process(args, package_path):
    env = os.environ.copy()
    return subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True,
        cwd=package_path,
        env=env,
    )


def is_xvfb_avaiable() -> bool:
    try:
        p = subprocess.Popen(
            ["Xvfb", "-help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        _, _ = p.communicate()
        exit_code = p.returncode
        return exit_code == 0
    except FileNotFoundError:
        logger.warning("Xvfb was not found")
    return False


@pytest.fixture
def screen_manager():
    if sys.platform == "linux":
        if is_xvfb_avaiable():
            return LinuxVirtualScreenManager()
        else:
            return HostScreenManager()
    elif sys.platform == "win32":
        return HostScreenManager()
    else:
        pytest.skip(f"Platform '{sys.platform}' is not supported")


def run_gui_test(tmpdir, screen_manager, window_name, gui_callback) -> None:
    is_ok = True
    # for some reason, it occasionally may fail with
    # 'wxEntryStart failed, unable to initialize wxWidgets!' error, most likely
    # this is not related with plugin's code - try to get screenshot 3 times
    # to limit false positives
    max_attempts = 3
    for i in range(0, max_attempts):
        with screen_manager as mgr:
            p = gui_callback()

            is_ok = mgr.screenshot(window_name, f"{tmpdir}/report/screenshot.png")
            try:
                outs, _ = p.communicate("q\n", timeout=1)
            except subprocess.TimeoutExpired:
                p.kill()
                outs, _ = p.communicate()

            assert outs == "Press any key to exit: "
            # here we used to check if stderr is empty but on some occasions
            # (linux only) it would contain `AssertionError: assert 'double free'`
            # or similar even though dialog opened correctly.
            # This probably is related to test harness (running GUI in Xvfb
            # virtual buffer) and not to tested code defect.
            # Decided to skip stderr check.
            # If gui fails to open then screenshot function of pyvirtualdisplay
            # would return 'screenshot is empty' which can be verified by swapping
            # order of gui_callback and screenshot calls.

            if is_ok:
                break
            else:
                logger.info(f"Failed to get screenshot, attempt {i+1}/{max_attempts}")

    assert is_ok


def test_gui(tmpdir, package_path, package_name, screen_manager) -> None:
    def _callback():
        return run_process(
            [
                "python3",
                "-m",
                f"{package_name}.kbplacer_dialog",
                "-o",
                tmpdir,
            ],
            package_path,
        )

    run_gui_test(tmpdir, screen_manager, "kbplacer", _callback)
    with open(f"{tmpdir}/window_state.json", "r") as f:
        state = json.load(f)
        # state not explicitly restored should result in default state:
        assert state == DEFAULT_WINDOW_STATE


def test_help_dialog(tmpdir, package_path, package_name, screen_manager) -> None:
    def _callback():
        return run_process(
            ["python3", "-m", f"{package_name}.help_dialog"], package_path
        )

    run_gui_test(tmpdir, screen_manager, "kbplacer help", _callback)


def test_gui_default_state(tmpdir, package_path, package_name, screen_manager) -> None:
    def _callback():
        return run_process(
            ["python3", "-m", f"{package_name}.kbplacer_dialog", "-o", tmpdir],
            package_path,
        )

    run_gui_test(tmpdir, screen_manager, "kbplacer", _callback)
    with open(f"{tmpdir}/window_state.json", "r") as f:
        state = json.load(f)
        assert state == DEFAULT_WINDOW_STATE


def merge_dicts(dict1, dict2):
    for key, val in dict2.items():
        if key not in dict1:
            dict1[key] = val
            continue

        if isinstance(val, dict):
            merge_dicts(dict1[key], val)
        else:
            dict1[key] = val
    return dict1


def get_state_data(state: dict, name: str):
    input_state = json.dumps(state, indent=None)
    expected = copy.deepcopy(DEFAULT_WINDOW_STATE)
    expected = merge_dicts(expected, state)
    return pytest.param(input_state, expected, id=name)


@pytest.mark.parametrize(
    "state,expected",
    [
        # fmt: off
        ("{}",DEFAULT_WINDOW_STATE),  # state has no values defined, should fallback to default
        get_state_data({"switch_section": {
            "element_info": {
                    "annotation_format": "KEY{}",
                    "position_option": "Default",
                    "position": {
                        "x": 0,
                        "y": 0,
                        "orientation": 90,
                        "side": "Back"
                    },
                    "template_path": ""
                }
            }
        }, "non-default-key-annotation-and-position"),
        get_state_data({"switch_section": {"key_distance": [18, 18.01]}}, "non-default-x-distance"),
        get_state_data({"additional_elements": {"elements_info": []}}, "no-additional-elements"),
        get_state_data(CUSTOM_WINDOW_STATE_EXAMPLE1, "custom-state-1"),
        # fmt: on
    ],
)
def test_gui_state_restore(
    state, expected, tmpdir, package_path, package_name, screen_manager
) -> None:
    def _callback():
        return run_process(
            [
                "python3",
                "-m",
                f"{package_name}.kbplacer_dialog",
                "-i",
                state,
                "-o",
                tmpdir,
            ],
            package_path,
        )

    run_gui_test(tmpdir, screen_manager, "kbplacer", _callback)
    with open(f"{tmpdir}/window_state.json", "r") as f:
        state = json.load(f)
        assert state == expected


def test_load_window_state_from_log(tmpdir) -> None:
    logfile = f"{tmpdir}/kbplacer.log"
    with open(logfile, "w") as f:
        state_str = json.dumps(DEFAULT_WINDOW_STATE, indent=None)
        f.write(f"GUI state: {state_str}")
    state, error = load_window_state_from_log(logfile)
    assert error is False
    assert state == DEFAULT_WINDOW_STATE


def test_load_window_state_from_corrupted_log(tmpdir) -> None:
    logfile = f"{tmpdir}/kbplacer.log"
    with open(logfile, "w") as f:
        f.write("GUI state: Some nonsense")
    state, error = load_window_state_from_log(logfile)
    assert error is True
    assert state is None


def test_load_window_state_from_missing_log(tmpdir) -> None:
    logfile = f"{tmpdir}/kbplacer.log"
    state, error = load_window_state_from_log(logfile)
    assert error is False
    assert state is None
