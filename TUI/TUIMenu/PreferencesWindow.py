#!/usr/bin/env python
"""Preferences window

2003-12-17 ROwen
2010-03-10 ROwen    Added WindowName
"""
import RO.Alg
import RO.Prefs.PrefWdg
import TUI.TUIModel
import TUI.Version

WindowName = "%s.Preferences" % (TUI.Version.ApplicationName,)
_HelpURL = "TUIMenu/PreferencesWin.html"


def addWindow(tlSet):
    tuiModel = TUI.TUIModel.getModel()

    # preferences window
    tlSet.createToplevel (
        name = WindowName,
        defGeom = "+62+116",
        resizable = False,
        visible = False,
        wdgFunc = RO.Alg.GenericCallback(
            RO.Prefs.PrefWdg.PrefWdg,
            prefSet = tuiModel.prefs,
            helpURL = _HelpURL,
        ),
    )
