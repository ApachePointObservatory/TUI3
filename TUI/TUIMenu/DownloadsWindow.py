#!/usr/bin/env python
"""Downloads window

2005-07-08 ROwen
2010-03-10 ROwen    Added WindowName
"""
import RO.Alg
import RO.Wdg.HTTPGetWdg
import TUI.Version

_MaxLines = 100
_MaxTransfers = 5

WindowName = "%s.Downloads" % (TUI.Version.ApplicationName,)

def addWindow(tlSet, visible=False):
    tlSet.createToplevel (
        name = WindowName,
        defGeom = "+835+290",
        wdgFunc = RO.Alg.GenericCallback(
            RO.Wdg.HTTPGetWdg.HTTPGetWdg,
            maxTransfers = _MaxTransfers,
            maxLines = _MaxLines,
            helpURL = "TUIMenu/DownloadsWin.html",
        ),
        visible = visible,
    )
