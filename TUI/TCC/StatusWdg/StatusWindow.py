#!/usr/bin/env python
"""Create the main TCC status window
(which is also the main TUI window, since it has the menus)

History:
2003-06-09 ROwen    added addWindow and renamed from StatusWdg to StatusWindow.
2003-06-25 ROwen    Modified test case to handle message data as a dict
2003-12-17 ROwen    Modified to use renamed TUI.MainMenu.
2004-02-04 ROwen    Modified _HelpURL to match minor help reorg.
2004-02-17 ROwen    Changed buildAutoMenus to buildMenus.
2004-05-18 ROwen    Removed unused local variable in addWindow.
2004-08-11 ROwen    Modified for updated RO.Wdg.Toplevel.
2006-03-16 ROwen    Modified to use TestData module for testing.
2009-04-17 ROwen    Added this window to the TUI menu.
2009-09-09 ROwen    Moved this window to the TCC menu.
                    Modified for changes in the TestData module.
                    Added constant WindowName.
2011-02-16 ROwen    Added AxisOffsetWdg and moved MiscWdg above the offsets.
"""
import tkinter
from . import AxisStatus
from . import NetPosWdg
from . import OffsetWdg
from . import AxisOffsetWdg
from . import MiscWdg
import RO.Wdg
from . import SlewStatus

WindowName = "TCC.Status"

def addWindow(tlSet):
    """Set up the main status window
    """
    tlSet.createToplevel(
        name = WindowName,
        defGeom = "+0+22",
        resizable = False,
        closeMode = RO.Wdg.tl_CloseDisabled,
        wdgFunc = StatusWdg,
    )

_HelpPrefix = "Telescope/StatusWin.html#"

class StatusWdg (tkinter.Frame):
    def __init__ (self,
        master = None,
    **kargs):
        """creates a new telescope status frame

        Inputs:
        - master        master Tk widget -- typically a frame or window
        """
        tkinter.Frame.__init__(self, master=master, **kargs)

        row = 1
        self.netPosWdg = NetPosWdg.NetPosWdg(
            master=self,
            borderwidth=1,
        )
        self.netPosWdg.grid(row=row, column=0, sticky="w")
        self.slewStatusWdg = SlewStatus.SlewStatusWdg(
            master = self,
        )
        self.slewStatusWdg.grid(row=row, column=1, sticky="ns")
        row += 1
        
        self.miscWdg = MiscWdg.MiscWdg(
            master=self,
            borderwidth=1,
            relief="ridge",
        )
        self.miscWdg.grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1

        self.offsetWdg = OffsetWdg.OffsetWdg(
            master=self,
            borderwidth=1,
            relief="ridge",
        )
        self.offsetWdg.grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1
        
        self.axisOffsetWdg = AxisOffsetWdg.AxisOffsetWdg(
            master=self,
            borderwidth=1,
            relief="ridge",
        )
        self.axisOffsetWdg.grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1
        
        self.axisStatusWdg = AxisStatus.AxisStatusWdg(
            master=self,
            borderwidth=1,
            relief="ridge",
        )
        self.axisStatusWdg.grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1

        # set up status bar; this is only for showing help,
        # not command status, so we can omit dispatcher and prefs
        self.statusBar = RO.Wdg.StatusBar(
            master = self,
            helpURL = _HelpPrefix + "StatusBar",
        )
        self.statusBar.grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1
    

if __name__ == "__main__":
    from . import TestData
    root = TestData.tuiModel.tkRoot

    testFrame = StatusWdg(TestData.tuiModel.tkRoot)
    testFrame.pack()

    TestData.init()
    TestData.runTest()

    root.mainloop()
