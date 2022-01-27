#!/usr/bin/env python
"""Specify what users from each program are allowed to do.

2003-12-18 ROwen    Preliminary version; html help is broken.
2003-12-29 ROwen    Implemented html help.
2004-02-17 ROwen    Moved to the TUI menu (now that this is possible!)
                    and changed to visible by default.
2004-07-29 ROwen    Added read-only support.
                    Updated for new RO.KeyVariable
2005-01-05 ROwen    Added Read Only button to test code.
2006-04-10 ROwen    Updated Sort button help text because actors are now sorted.
2007-07-27 ROwen    Modified to pay command-completed sounds.
2009-07-06 ROwen    Modified for updated TestData.
2009-07-09 ROwen    Modified test code to look more like tuisdss.
2011-04-08 ROwen    Modified to use updated PermsTableWdg (formerly PermsInputWdg).
2011-06-17 ROwen    Added constants WindowName.
2011-07-27 ROwen    Updated for new location of PermsModel.
2012-07-10 ROwen    Removed use of update_idletasks.
2012-11-19 ROwen    Fixed demo mode.
2012-11-30 ROwen    Removed fix for demo mode; it's inside RO now.
"""
import tkinter
import RO.KeyVariable
import RO.Wdg
import TUI.TUIModel
import TUI.Models.PermsModel
from . import PermsTableWdg

WindowName = "TUI.Permissions"

_HelpPrefix = "TUIMenu/PermissionsWin.html#"

def addWindow(tlSet):
    """Create the window for TUI.
    """
    tlSet.createToplevel(
        name = WindowName,
        defGeom = "180x237+172+722",
        visible = True,
        resizable = (False, True),
        wdgFunc = PermsWdg,
    )

_HelpPrefix = "TUIMenu/PermissionsWin.html#"

class PermsWdg(tkinter.Frame):
    def __init__(self, master):
        tkinter.Frame.__init__(self, master)

        tuiModel = TUI.TUIModel.getModel()

        self._permsModel = TUI.Models.PermsModel.getModel()

        self._statusBar = RO.Wdg.StatusBar(
            master = self,
            dispatcher = tuiModel.dispatcher,
            prefs = tuiModel.prefs,
            playCmdSounds = True,
            summaryLen = 20,
        )
        
        self.permsTableWdg = PermsTableWdg.PermsTableWdg(
            master = self,
            statusBar = self._statusBar,
            readOnlyCallback = self.doReadOnly,
        )
        self.permsTableWdg.grid(row=1, sticky="ns")
        self.grid_rowconfigure(1, weight=1)

        self._statusBar.grid(row=2, sticky="ew")
    
        self.butFrame = tkinter.Frame(self)
        
        RO.Wdg.StrLabel(self.butFrame, text="Add:").pack(side="left", anchor="e")
        newEntryWdg = RO.Wdg.StrEntry (
            master = self.butFrame,
            partialPattern = r"^[a-zA-Z]{0,2}[0-9]{0,2}$",
            finalPattern = r"^[a-zA-Z][a-zA-Z][0-9][0-9]$",
            width = 4,
            helpText = "type new program name and <return>",
            
        )
        newEntryWdg.bind("<Return>", self.doNew)
        newEntryWdg.pack(side="left", anchor="w")
        
        purgeWdg = RO.Wdg.Button(
            master = self.butFrame,
            text = "Purge",
            command = self.permsTableWdg.purge,
            helpText = "Purge unregistered programs",
            helpURL = _HelpPrefix + "Purge",
        )
        purgeWdg.pack(side="left")

        sortWdg = RO.Wdg.Button(
            master = self.butFrame,
            text = "Sort",
            command = self.permsTableWdg.sort,
            helpText = "Sort programs and actors",
            helpURL = _HelpPrefix + "Sort",
        )
        sortWdg.pack(side="left")
        
        self.butFrame.grid(row=3, sticky="w")
        self.butFrame.grid_remove() # start in read-only state
    
    def doReadOnly(self, readOnly):
        """Callback for readOnly state changing.
        """
        if readOnly:
            self.butFrame.grid_remove()
        else:
            self.butFrame.grid()
    
    def doApply(self, wdg=None):
        pass

    def doNew(self, evt):
        """Callback for Add entry widget."""
        wdg = evt.widget
        if not wdg.isOK():
            return

        progName = wdg.getString().upper()

        newCmd = RO.KeyVariable.CmdVar (
            cmdStr = "register " + progName,
            actor="perms",
            timeLim = 5,
            description="create a new program to authorize",
        )
        self._statusBar.doCmd(newCmd)
        wdg.clear()
        wdg.focus_set()


if __name__ == "__main__":
    from . import TestData
    root = TestData.tuiModel.tkRoot
    root.resizable(False, True)

    DefReadOnly = False
    
    testFrame = PermsWdg(master=root)
    testFrame.pack(side="top", expand=True, fill="y")
    testFrame.permsTableWdg._setReadOnly(DefReadOnly)
    
    def doReadOnly(but):
        readOnly = but.getBool()
        testFrame.permsTableWdg._setReadOnly(readOnly)

    butFrame = tkinter.Frame(root)
    
    tkinter.Button(butFrame, text="Demo", command=TestData.animate).pack(side="left")
    
    RO.Wdg.Checkbutton(butFrame, text="Read Only", defValue=DefReadOnly, callFunc=doReadOnly).pack(side="left")
    
    butFrame.pack(side="top", anchor="w")

    TestData.start()

    root.mainloop()
