from __future__ import annotations

import string
import wx
from typing import List, Optional, Tuple

from .defaults import DEFAULT_DIODE_POSITION
from .element_position import ElementPosition, Point, PositionOption, Side
from .help_dialog import HelpDialog


TEXT_CTRL_EXTRA_SPACE = 25


class FloatValidator(wx.Validator):
    def __init__(self) -> None:
        wx.Validator.__init__(self)
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self) -> FloatValidator:
        return FloatValidator()

    def Validate(self, _):
        text_ctrl = self.GetWindow()
        if not text_ctrl.IsEnabled():
            return True

        text = text_ctrl.GetValue()
        try:
            float(text)
            return True
        except ValueError:
            # this should never happen since there is on EVT_CHAR filtering:
            wx.MessageBox(f"Invalid float value: {text}!", "Error")
            text_ctrl.SetFocus()
            return False

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

    def OnChar(self, event):
        keycode = int(event.GetKeyCode())
        if (
            keycode == wx.WXK_BACK
            or keycode == wx.WXK_LEFT
            or keycode == wx.WXK_RIGHT
            or keycode == wx.WXK_NUMPAD_LEFT
            or keycode == wx.WXK_NUMPAD_RIGHT
        ):
            event.Skip()
        else:
            text_ctrl = self.GetWindow()
            text = text_ctrl.GetValue()
            key = chr(keycode)
            if key in string.digits or key == "-" or (key == "." and "." not in text):
                event.Skip()


class LabeledTextCtrl(wx.Panel):
    def __init__(self, parent, label: str, value: str, width: int = -1) -> None:
        super().__init__(parent)

        expected_char_width = self.GetTextExtent("x").x
        if width != -1:
            annotation_format_size = wx.Size(
                expected_char_width * width + TEXT_CTRL_EXTRA_SPACE, -1
            )
        else:
            annotation_format_size = wx.Size(-1, -1)

        self.label = wx.StaticText(self, -1, label)
        self.text = wx.TextCtrl(self, value=value, size=annotation_format_size)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.label, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.text, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        self.SetSizer(sizer)

    def Enable(self):
        self.label.Enable()
        self.text.Enable()

    def Disable(self):
        self.label.Disable()
        self.text.Disable()


class CustomRadioBox(wx.Panel):
    def __init__(self, parent, choices: List[str]):
        super().__init__(parent)
        self.radio_buttons: dict[str, wx.RadioButton] = {}

        for choice in choices:
            radio_button = wx.RadioButton(self, label=choice)
            self.radio_buttons[choice] = radio_button

        # this is special hidden option to allow clearing (selecting none)
        self.none_button = wx.RadioButton(self, label="")
        self.none_button.Hide()

        sizer = wx.BoxSizer(wx.VERTICAL)
        for radio_button in self.radio_buttons.values():
            sizer.Add(radio_button, 0, wx.ALL, -2)

        self.SetSizer(sizer)

    def Select(self, choice):
        self.radio_buttons[choice].SetValue(True)

    def Clear(self):
        self.none_button.SetValue(True)

    def GetValue(self) -> Optional[str]:
        if self.none_button.GetValue():
            return None
        else:
            for choice, button in self.radio_buttons.items():
                if button.GetValue():
                    return choice
            return None


class ElementPositionWidget(wx.Panel):
    def __init__(self, parent, default: Optional[ElementPosition] = None) -> None:
        super().__init__(parent)

        self.default = default
        choices = [PositionOption.CUSTOM, PositionOption.CURRENT_RELATIVE]
        if self.default:
            choices.insert(0, PositionOption.DEFAULT)

        self.dropdown = wx.ComboBox(self, choices=choices, style=wx.CB_DROPDOWN)
        self.dropdown.Bind(wx.EVT_COMBOBOX, self.__on_position_choice_change)

        expected_char_width = self.GetTextExtent("x").x
        expected_size = wx.Size(5 * expected_char_width + TEXT_CTRL_EXTRA_SPACE, -1)
        self.x = wx.TextCtrl(
            self, value="", size=expected_size, validator=FloatValidator()
        )
        self.y = wx.TextCtrl(
            self, value="", size=expected_size, validator=FloatValidator()
        )
        self.orientation = wx.TextCtrl(
            self, value="", size=expected_size, validator=FloatValidator()
        )
        self.side = CustomRadioBox(self, choices=["Front", "Back"])

        self.__set_initial_state(choices[0])

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(self, -1, "Position:"), 0, wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.dropdown, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(
            wx.StaticText(self, -1, "X/Y offset:"), 0, wx.ALIGN_CENTER_VERTICAL, 5
        )
        sizer.Add(self.x, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.StaticText(self, -1, "/"), 0, wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.y, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(
            wx.StaticText(self, -1, "Orientation:"), 0, wx.ALIGN_CENTER_VERTICAL, 5
        )
        sizer.Add(self.orientation, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.side, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)

    def __set_initial_state(self, choice) -> None:
        self.dropdown.SetValue(choice)
        self.__set_position_by_choice(choice)

    def __on_position_choice_change(self, event) -> None:
        choice = event.GetString()
        self.__set_position_by_choice(choice)

    def __set_position_by_choice(self, choice: str) -> None:
        if choice == PositionOption.DEFAULT:
            self.__set_position_to_default()
        elif choice == PositionOption.CURRENT_RELATIVE:
            self.__set_position_to_empty_non_editable()
        elif choice == PositionOption.CUSTOM:
            self.__set_position_to_zero_editable()
        else:
            raise ValueError
        self.choice = PositionOption(choice)

    def __set_position_to_default(self) -> None:
        if self.default:
            x = str(self.default.relative_position.x)
            y = str(self.default.relative_position.y)
            self.__set_coordinates(x, y)
            self.orientation.SetValue(str(self.default.orientation))
            if self.default.side == Side.BACK:
                self.side.Select("Back")
            else:
                self.side.Select("Front")
            self.__disable_position_controls()

    def __set_position_to_zero_editable(self) -> None:
        self.__set_coordinates("0", "0")
        self.orientation.SetValue("0")
        self.side.Select("Front")
        self.__enable_position_controls()

    def __set_position_to_empty_non_editable(self):
        self.__set_coordinates("-", "-")
        self.orientation.SetValue("-")
        self.side.Clear()
        self.__disable_position_controls()

    def __set_coordinates(self, x: str, y: str):
        self.x.SetValue(x)
        self.y.SetValue(y)

    def __enable_position_controls(self):
        self.x.Enable()
        self.y.Enable()
        self.orientation.Enable()
        self.side.Enable()

    def __disable_position_controls(self):
        self.x.Disable()
        self.y.Disable()
        self.orientation.Disable()
        self.side.Disable()

    def GetValue(self) -> Tuple[PositionOption, Optional[ElementPosition]]:
        if (
            self.choice == PositionOption.DEFAULT
            or self.choice == PositionOption.CUSTOM
        ):
            x = float(self.x.GetValue())
            y = float(self.y.GetValue())
            orientation = float(self.orientation.GetValue())
            side_str = self.side.GetValue()
            return self.choice, ElementPosition(
                Point(x, y), orientation, Side(side_str == "Back")
            )
        else:
            return self.choice, None

    def Enable(self):
        self.dropdown.Enable()
        self.__set_position_by_choice(self.dropdown.GetValue())

    def Disable(self):
        self.__disable_position_controls()
        self.dropdown.Disable()


class ElementSettingsWidget(wx.Panel):
    def __init__(
        self,
        parent,
        default_annotation: str,
        default_position: Optional[ElementPosition] = None,
    ) -> None:
        super().__init__(parent)

        self.annotation_format = LabeledTextCtrl(
            self, label="Annotation format:", value=default_annotation, width=3
        )
        self.position_widget = ElementPositionWidget(self, default=default_position)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.annotation_format, 0, wx.EXPAND | wx.RIGHT, 5)
        sizer.Add(self.position_widget, 0, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(sizer)

    def GetValue(self) -> Tuple[str, PositionOption, Optional[ElementPosition]]:
        annotation = self.annotation_format.text.GetValue()
        position = self.position_widget.GetValue()
        return annotation, position[0], position[1]

    def Enable(self):
        self.annotation_format.Enable()
        self.position_widget.Enable()

    def Disable(self):
        self.annotation_format.Disable()
        self.position_widget.Disable()


class KbplacerDialog(wx.Dialog):
    def __init__(self, parent, title) -> None:
        style = wx.DEFAULT_DIALOG_STYLE
        super(KbplacerDialog, self).__init__(parent, -1, title, style=style)

        switch_section = self.get_switch_section()
        switch_diodes_section = self.get_switch_diodes_section()
        additional_elements_section = self.get_additional_elements_section()
        misc_section = self.get_misc_section()

        box = wx.BoxSizer(wx.VERTICAL)

        box.Add(switch_section, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(switch_diodes_section, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(additional_elements_section, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(misc_section, 0, wx.EXPAND | wx.ALL, 5)

        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL | wx.HELP)

        help_button = wx.FindWindowById(wx.ID_HELP, self)
        if help_button:
            help_button.Bind(wx.EVT_BUTTON, self.on_help_button)

        box.Add(buttons, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizerAndFit(box)

    def get_switch_section(self):
        key_annotation = LabeledTextCtrl(self, "Switch annotation format:", "SW{}")

        layout_label = wx.StaticText(self, -1, "KLE json file:")
        layout_file_picker = wx.FilePickerCtrl(self, -1)

        key_distance_x = wx.TextCtrl(self, value="19.05", validator=FloatValidator())
        key_distance_y = wx.TextCtrl(self, value="19.05", validator=FloatValidator())

        key_distance_label = wx.StaticText(self, -1, "X/Y 1U distance:")

        row1 = wx.BoxSizer(wx.HORIZONTAL)
        row1.Add(key_annotation, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        row1.Add(layout_label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        row1.Add(layout_file_picker, 1, wx.ALL, 5)

        row2 = wx.BoxSizer(wx.HORIZONTAL)
        row2.Add(key_distance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        row2.Add(key_distance_x, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        row2.Add(wx.StaticText(self, -1, "/"), 0, wx.ALIGN_CENTER_VERTICAL, 5)
        row2.Add(key_distance_y, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        box = wx.StaticBox(self, label="Switch settings")
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        sizer.Add(row1, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(row2, 0, wx.EXPAND | wx.ALL, 5)

        self.__key_annotation_format = key_annotation.text
        self.__layout_file_picker = layout_file_picker
        self.__key_distance_x = key_distance_x
        self.__key_distance_y = key_distance_y

        return sizer

    def get_switch_diodes_section(self):
        place_diodes_checkbox = wx.CheckBox(self, label="Enable placement")
        place_diodes_checkbox.SetValue(True)
        place_diodes_checkbox.Bind(wx.EVT_CHECKBOX, self.on_diode_place_checkbox)

        diode_settings = ElementSettingsWidget(
            self, "D{}", default_position=DEFAULT_DIODE_POSITION
        )

        box = wx.StaticBox(self, label="Switch diodes settings")
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(place_diodes_checkbox, 0, wx.EXPAND | wx.ALL, 5)
        # weird border value to make it aligned with 'additional_elements_section':
        sizer.Add(diode_settings, 0, wx.EXPAND | wx.ALL, 9)

        self.__place_diodes_checkbox = place_diodes_checkbox
        self.__diode_settings = diode_settings

        return sizer

    def on_diode_place_checkbox(self, event):
        is_checked = event.GetEventObject().IsChecked()
        if is_checked:
            self.__diode_settings.Enable()
        else:
            self.__diode_settings.Disable()

    def get_additional_elements_section(self):
        self.__additional_elements = []

        scrolled_window = wx.ScrolledWindow(self)
        scrolled_window_sizer = wx.BoxSizer(wx.VERTICAL)

        scrolled_window.SetSizer(scrolled_window_sizer)
        virtual_width, virtual_height = scrolled_window_sizer.GetMinSize()
        scrolled_window.SetVirtualSize((virtual_width, virtual_height))
        scrolled_window.SetScrollRate(0, 10)

        box = wx.StaticBox(self, label="Additional elements settings")
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        sizer.Add(scrolled_window, 1, wx.EXPAND | wx.ALL, 10)

        dialog_width, _ = self.GetSize()
        sizer.SetMinSize((dialog_width, 180))

        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)

        def add_element(annotation: str) -> None:
            element_settings = ElementSettingsWidget(scrolled_window, annotation)
            self.__additional_elements.append(element_settings)
            scrolled_window_sizer.Add(element_settings, 0, wx.ALIGN_LEFT, 0)
            self.Layout()

        def add_element_callback(_) -> None:
            add_element("")

        add_element("ST{}")

        add_icon = wx.ArtProvider.GetBitmap(wx.ART_PLUS, wx.ART_BUTTON)
        add_button = wx.BitmapButton(self, bitmap=add_icon)
        add_button.Bind(wx.EVT_BUTTON, add_element_callback)

        def remove_element(_) -> None:
            element_settings = (
                self.__additional_elements.pop() if self.__additional_elements else None
            )
            if element_settings:
                element_settings.Destroy()
                self.Layout()
            pass

        remove_icon = wx.ArtProvider.GetBitmap(wx.ART_MINUS, wx.ART_BUTTON)
        remove_button = wx.BitmapButton(self, bitmap=remove_icon)
        remove_button.Bind(wx.EVT_BUTTON, remove_element)

        buttons_sizer.Add(add_button, 0, wx.EXPAND | wx.ALL, 0)
        buttons_sizer.Add(remove_button, 0, wx.EXPAND | wx.ALL, 0)

        sizer.Add(buttons_sizer, 0, wx.EXPAND | wx.ALL, 5)

        return sizer

    def get_misc_section(self):
        tracks_checkbox = wx.CheckBox(self, label="Add tracks")
        tracks_checkbox.SetValue(True)

        template_label = wx.StaticText(self, -1, "Controller circuit template:")
        template_file_picker = wx.FilePickerCtrl(self, -1)

        box = wx.StaticBox(self, label="Other settings")
        sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

        sizer.Add(tracks_checkbox, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.StaticLine(self, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(template_label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(template_file_picker, 1, wx.EXPAND | wx.ALL, 5)

        self.__tracks_checkbox = tracks_checkbox
        self.__template_file_picker = template_file_picker

        return sizer

    def on_help_button(self, event):
        del event
        help_dialog = HelpDialog()
        help_dialog.ShowModal()
        help_dialog.Destroy()

    def get_layout_path(self) -> str:
        return self.__layout_file_picker.GetPath()

    def get_key_annotation_format(self) -> str:
        return self.__key_annotation_format.GetValue()

    def is_tracks(self) -> bool:
        return self.__tracks_checkbox.GetValue()

    def is_diode_placement(self) -> bool:
        return self.__place_diodes_checkbox.GetValue()

    def get_key_distance(self) -> Tuple[float, float]:
        x = float(self.__key_distance_x.GetValue())
        y = float(self.__key_distance_y.GetValue())
        return x, y

    def get_template_path(self) -> str:
        return self.__template_file_picker.GetPath()

    def get_diode_position_info(
        self,
    ) -> Tuple[str, PositionOption, Optional[ElementPosition]]:
        return self.__diode_settings.GetValue()

    def get_additional_elements_info(
        self,
    ) -> List[Tuple[str, PositionOption, Optional[ElementPosition]]]:
        return [
            e.GetValue() for e in self.__additional_elements if e.GetValue()[0] != ""
        ]
