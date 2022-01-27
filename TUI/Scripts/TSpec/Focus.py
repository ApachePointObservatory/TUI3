"""Take a series of exposures at different focus positions to estimate best focus.

History:
2008-03-25 ROwen    First version
2008-04-03 ROwen    Changed doWindow to True because the TripleSpec slitviewer can now window
2011-10-25 ROwen    Set final bin factor = 2 (a hack).
"""
import TUI.Base.BaseFocusScript
SlitviewerFocusScript = TUI.Base.BaseFocusScript.SlitviewerFocusScript

Debug = False # run in debug-only mode (which doesn't DO anything, it just pretends)?
HelpURL = "Scripts/BuiltInScripts/InstFocus.html"

class ScriptClass(SlitviewerFocusScript):
    def __init__(self, sr):
        """The setup script; run once when the script runner
        window is created.
        """
        SlitviewerFocusScript.__init__(self,
            sr = sr,
            gcamActor = "tcam",
            instName = "TSpec",
            imageViewerTLName = "Guide.TSpec Slitviewer",
            defBoreXY = [None, -5.0],
            doWindow = True,
            finalBinFactor = 2,
            helpURL = HelpURL,
            debug = Debug,
        )
