import wx


class KbplacerDialog(wx.Dialog):
    def __init__(self, parent, title):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super(KbplacerDialog, self).__init__(parent, -1, title, style=style)
        row1 = wx.BoxSizer(wx.HORIZONTAL)

        text = wx.StaticText(self, -1, "Select kle json file:")
        row1.Add(text, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)

        layoutFilePicker = wx.FilePickerCtrl(self, -1)
        row1.Add(layoutFilePicker, 1, wx.EXPAND | wx.ALL, 5)

        row2 = wx.BoxSizer(wx.HORIZONTAL)

        keyAnnotationLabel = wx.StaticText(self, -1, "Key annotation format string:")
        row2.Add(
            keyAnnotationLabel, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5
        )

        keyAnnotationFormat = wx.TextCtrl(self, value="SW{}")
        row2.Add(keyAnnotationFormat, 1, wx.EXPAND | wx.ALL, 5)

        row3 = wx.BoxSizer(wx.HORIZONTAL)

        stabilizerAnnotationLabel = wx.StaticText(
            self, -1, "Stabilizer annotation format string:"
        )
        row3.Add(
            stabilizerAnnotationLabel,
            1,
            wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
            5,
        )

        stabilizerAnnotationFormat = wx.TextCtrl(self, value="ST{}")
        row3.Add(stabilizerAnnotationFormat, 1, wx.EXPAND | wx.ALL, 5)

        row4 = wx.BoxSizer(wx.HORIZONTAL)

        diodeAnnotationLabel = wx.StaticText(
            self, -1, "Diode annotation format string:"
        )
        row4.Add(
            diodeAnnotationLabel, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5
        )

        diodeAnnotationFormat = wx.TextCtrl(self, value="D{}")
        row4.Add(diodeAnnotationFormat, 1, wx.EXPAND | wx.ALL, 5)

        row5 = wx.BoxSizer(wx.HORIZONTAL)

        tracksCheckbox = wx.CheckBox(self, label="Add tracks")
        tracksCheckbox.SetValue(True)
        row5.Add(tracksCheckbox, 1, wx.EXPAND | wx.ALL, 5)

        row6 = wx.BoxSizer(wx.HORIZONTAL)

        useFirstPairAsTemplateCheckbox = wx.CheckBox(
            self, label="Use first switch-diode pair as reference for relative position"
        )
        useFirstPairAsTemplateCheckbox.SetValue(False)
        row6.Add(useFirstPairAsTemplateCheckbox, 1, wx.EXPAND | wx.ALL, 5)

        row7 = wx.BoxSizer(wx.HORIZONTAL)

        text = wx.StaticText(self, -1, "Select controller circuit template:")
        row7.Add(text, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)

        templateFilePicker = wx.FilePickerCtrl(self, -1)
        row7.Add(templateFilePicker, 1, wx.EXPAND | wx.ALL, 5)

        box = wx.BoxSizer(wx.VERTICAL)

        box.Add(row1, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(row2, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(row3, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(row4, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(row5, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(row6, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(row7, 0, wx.EXPAND | wx.ALL, 5)

        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        box.Add(buttons, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizerAndFit(box)
        self.layoutFilePicker = layoutFilePicker
        self.keyAnnotationFormat = keyAnnotationFormat
        self.stabilizerAnnotationFormat = stabilizerAnnotationFormat
        self.diodeAnnotationFormat = diodeAnnotationFormat
        self.useFirstPairAsTemplateCheckbox = useFirstPairAsTemplateCheckbox
        self.tracksCheckbox = tracksCheckbox
        self.templateFilePicker = templateFilePicker

    def get_layout_path(self):
        return self.layoutFilePicker.GetPath()

    def get_key_annotation_format(self):
        return self.keyAnnotationFormat.GetValue()

    def get_stabilizer_annotation_format(self):
        return self.stabilizerAnnotationFormat.GetValue()

    def get_diode_annotation_format(self):
        return self.diodeAnnotationFormat.GetValue()

    def is_tracks(self):
        return self.tracksCheckbox.GetValue()

    def is_first_pair_used_as_template(self):
        return self.useFirstPairAsTemplateCheckbox.GetValue()

    def get_template_path(self):
        return self.templateFilePicker.GetPath()
