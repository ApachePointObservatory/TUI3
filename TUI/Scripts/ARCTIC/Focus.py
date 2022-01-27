#!/usr/bin/env python
"""Take a series of ARCTIC exposures at different focus positions to estimate best focus.

History:
2016-06-16 CS       Created
"""
import TUI.Base.BaseFocusScript
ImagerFocusScript = TUI.Base.BaseFocusScript.ImagerFocusScript

Debug = False # run in debug-only mode (which doesn't DO anything, it just pretends)?
HelpURL = "Scripts/BuiltInScripts/InstFocus.html"

class ScriptClass(ImagerFocusScript):
    def __init__(self, sr):
        """The setup script; run once when the script runner
        window is created.
        """
        ImagerFocusScript.__init__(self,
            sr = sr,
            instName = "ARCTIC",
            imageViewerTLName = "None.ARCTIC Expose",
            defBinFactor = 2,
            maxFindAmpl = 20000,
            doWindow = True,
            doZeroOverscan = True,
            helpURL = HelpURL,
            debug = Debug,
        )
