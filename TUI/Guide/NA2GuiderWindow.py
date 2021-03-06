#!/usr/bin/env python
"""GCam NA2 guider window

To do:
- Consider a cancel button for Apply -- perhaps replace Current with Cancel
  while applying changes. (That might be a nice thing for all Configure windows).
  If implemented, ditch the time limit.
- Reimplement mech components as a separate widget that is brought in.
  That would greatly reduce the chance for collision.

History:
2005-05-26 ROwen
2005-06-16 ROwen    Changed to not use a command status bar for gmech changes
                    (this part of the code is not enabled anyway).
                    Imported RO.Wdg again in the test code (found by pychecker).
2005-06-17 ROwen    Renamed window from "GCam" to "NA2 Guider".
2005-06-21 ROwen    Fixed the test code.
2005-06-22 ROwen    Improved the test code.
2005-07-14 ROwen    Removed local test mode support.
2006-05-19 ROwen    Bug fix: doCurrent was colliding with parent class.
2008-02-01 ROwen    Modified to load GMech model.
2008-02-11 ROwen    Modified to use relPiston command.
                    Renamed Current to Current Filter.
                    Added a switch for showing/hiding the current filter.
2008-02-13 ROwen    Removed limits to match updated FocusWdg.
                    Removed preliminary attempt at a countdown timer (for now).
2008-07-02 ROwen	Updated for changes to TUI.Base.FocusWdg.
					Changed format from %.1f to %.0f.
2010-01-19 ROwen    Bug fix: some help strings said Echelle instead of NA2.
2012-07-09 ROwen    Removed some unused imports.
"""
import tkinter
import TUI.Base.FocusWdg
import TUI.Guide.GMechModel
import RO.Wdg
from . import GuideWdg
from . import GMechModel

WindowName = "Guide.NA2 Guider"

_HelpURL = "Guiding/NA2GuiderWin.html"
_FiltWidth = 5 # initial width for widgets that show filter name

def addWindow(tlSet):
    return tlSet.createToplevel (
        name = WindowName,
        defGeom = "+452+280",
        resizable = True,
        wdgFunc = NA2GuiderWdg,
        visible = False,
    )


class NA2GuiderWdg(GuideWdg.GuideWdg):
    def __init__(self,
        master,
    **kargs):
        GuideWdg.GuideWdg.__init__(self,
            master = master,
            actor = "gcam",
        )
        
        self.focusWdg = GMechFocusWdg(
            master = self.devSpecificFrame,
            statusBar = self.statusBar,
        )
        self.focusWdg.grid(row=0, column=0, sticky="w")

        self.filterWdg = GMechFilterWdg(
            master = self.devSpecificFrame,
            statusBar = self.statusBar,
        )
        self.filterWdg.grid(row=1, column=0, sticky="w")

        self.devSpecificFrame.grid_columnconfigure(1, weight=1)
        self.devSpecificFrame.configure(border=5, relief="sunken")


class GMechFocusWdg(TUI.Base.FocusWdg.FocusWdg):
    def __init__(self, master, statusBar):
        TUI.Base.FocusWdg.FocusWdg.__init__(self,
            master,
            name = "NA2 guider",
            statusBar = statusBar,
            increments = (1000, 2000, 4000),
            defIncr = 2000,
            helpURL = _HelpURL,
            label = "Focus",
            formatStr = "%.0f",
            focusWidth = 7,
        )

        gmechModel = TUI.Guide.GMechModel.getModel()
#        gmechModel.desFocus.addCallback(self.endTimer) # not the right way to end the timer
#        gmechModel.pistonMoveTime.addCallback(self._pistonMoveTime)
        gmechModel.focus.addIndexedCallback(self.updFocus)
        
    def _pistonMoveTime(self, elapsedPredTime, isCurrent, keyVar=None):
        """Called when CmdDTime seen, to put up a timer.
        """
        if not isCurrent or None in elapsedPredTime:
            return
        elapsedTime, predTime = elapsedPredTime
        self.startTimer(predTime, elapsedTime)
    
    def createFocusCmd(self, newFocus, isIncr=False):
        """Create and return the focus command"""
        if isIncr:
            incrStr = "relPiston"
        else:
            incrStr = "focus"
        cmdStr = "%s %s" % (incrStr, newFocus)

        return RO.KeyVariable.CmdVar (
            actor = "gmech",
            cmdStr = cmdStr,
        )


class GMechFilterWdg(tkinter.Frame):
    def __init__(self,
        master,
        statusBar,
    ):
        tkinter.Frame.__init__(self, master)
        self.statusBar = statusBar

        self.gmechModel = GMechModel.getModel()
        self.currCmd = None

        # show current filter as well as user filter menu?
        showCurrFilter = False

        col = 0
        
        RO.Wdg.StrLabel(
            master=self,
            text="Filter",
            helpText = "NA2 guider filter",
            helpURL = _HelpURL,
        ).grid(row=0, column=col)
        col += 1
        
        self.currFilterWdg = RO.Wdg.StrLabel(
            master = self,
            width = _FiltWidth,
            helpText = "Current NA2 guider filter",
            helpURL = _HelpURL,
        )
        if showCurrFilter:
            self.currFilterWdg.grid(row=0, column=col)
            col += 1

        if showCurrFilter:
            userFilterHelp = "Desired NA2 guider filter"
        else:
            userFilterHelp = "NA2 guider filter"
        
        self.userFilterWdg = RO.Wdg.OptionMenu(
            master = self,
            items = (),
            autoIsCurrent = True,
            width = _FiltWidth,
            callFunc = self.enableButtons,
            helpText = userFilterHelp,
            helpURL = _HelpURL,
            defMenu = "Current Filter",
        )
        self.userFilterWdg.grid(row=0, column=col)
        col += 1

        self.applyBtn = RO.Wdg.Button(
            master = self,
            text = "Set Filter",
            callFunc = self.doApply,
            helpText = "Set NA2 guider filter",
            helpURL = _HelpURL,
        )
        self.applyBtn.grid(row=0, column=col)
        col += 1

        self.cancelBtn = RO.Wdg.Button(
            master = self,
            text = "X",
            callFunc = self.doCancel,
            helpText = "Cancel filter command",
            helpURL = _HelpURL,
        )
        self.cancelBtn.grid(row=0, column=col)
        col += 1

        self.currentBtn = RO.Wdg.Button(
            master = self,
            text = "Current Filter",
            callFunc = self.doCurrent,
            helpText = "Show current NA2 guider filter",
            helpURL = _HelpURL,
        )
        self.currentBtn.grid(row=0, column=col)
        col += 1
 
        self.gmechModel.filter.addIndexedCallback(self.updFilter)
        self.gmechModel.filterNames.addCallback(self.updFilterNames)
        
        self.enableButtons()
    
    def cmdDone(self, *args, **kargs):
        self.currCmd = None
        self.enableButtons()

    def doApply(self, wdg=None):
        """Command a new filter"""
        desFilterInd = self.userFilterWdg.getIndex()
        if desFilterInd is None:
            raise RuntimeError("No filter selected")
        desFilterNum = desFilterInd + self.getMinFilterNum()
        cmdStr = "filter %s" % (desFilterNum,)
        self.currCmd = RO.KeyVariable.CmdVar (
            actor = "gmech",
            cmdStr = cmdStr,
            callFunc = self.cmdDone,
            callTypes = RO.KeyVariable.DoneTypes,
        )
        self.statusBar.doCmd(self.currCmd)
        self.enableButtons()
    
    def doCancel(self, *args, **kargs):
        if self.currCmd and not self.currCmd.isDone():
            self.currCmd.abort()
            self.doCurrent()
        
    def doCurrent(self, wdg=None):
        self.userFilterWdg.restoreDefault()

    def enableButtons(self, wdg=None):
        """Enable the various buttons depending on the current state"""
        if self.currCmd and not self.currCmd.isDone():
            self.userFilterWdg.setEnable(False)
            self.currentBtn.setEnable(False)
            self.cancelBtn.setEnable(True)
            self.applyBtn.setEnable(False)
        else:
            allowChange = not self.userFilterWdg.isDefault()
            self.userFilterWdg.setEnable(True)
            self.applyBtn.setEnable(allowChange)
            self.cancelBtn.setEnable(False)
            self.currentBtn.setEnable(allowChange)
    
    def getMinFilterNum(self):
        """Return the minimum filter number; raise RuntimeError if unavailable"""
        minFilter = self.gmechModel.minFilter.getInd(0)[0]
        if minFilter is None:
            raise RuntimeError("Minimum filter number unknown")
        return minFilter

    def updFilter(self, filterNum, isCurrent, keyVar=None):
        if filterNum is None:
            return

        self.currFilterWdg.set(filterNum)
        filterInd = filterNum - self.getMinFilterNum()
        filterName = self.userFilterWdg._items[filterInd]
        self.currFilterWdg.set(filterName)
        self.userFilterWdg.setDefault(filterName)
    
    def updFilterNames(self, filtNames, isCurrent, keyVar=None):
        if None in filtNames:
            return
        
        maxNameLen = 0
        for name in filtNames:
            maxNameLen = max(maxNameLen, len(name))

        self.currFilterWdg["width"] = maxNameLen
        self.userFilterWdg["width"] = maxNameLen
        self.userFilterWdg.setItems(filtNames)


if __name__ == "__main__":
    from . import GuideTest
    
    root = RO.Wdg.PythonTk()

    GuideTest.init("gcam")

    testTL = addWindow(GuideTest.tuiModel.tlSet)
    testTL.makeVisible()
    testTL.wait_visibility() # must be visible to download images
    testFrame = testTL.getWdg()
    
    for msg in (
        'i filterNames="red", "red nd1", "red nd2", "blue", "", "", ""; minFilter=0; maxFilter=6',
        'i minFocus=-10, maxFocus=20000',
        'i filter=0; focus=10',
    ):
        GuideTest.dispatch(msg, actor="gmech")

#    GuideTest.runDownload(
#        basePath = "keep/gcam/UT050422/",
#        imPrefix = "g",
#        startNum = 101,
#        numImages = 3,
#        waitMs = 2500,
#    )

    root.mainloop()
