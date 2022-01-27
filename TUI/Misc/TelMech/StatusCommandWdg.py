#!/usr/bin/env python
"""Status and control for the enclosure controller.

To do:
- Enhance buttons to handle None as a state

History:
2005-08-02 ROwen
2005-08-15 ROwen    Modified to not show enclosure enable (it doesn't seem to do anything).
2005-10-13 ROwen    Removed unused globals.
2006-05-04 ROwen    Modified to use telmech actor instead of tcc (but not all commands supported).
2007-06-26 ROwen    Added support for Eyelid controls
                    Allow group control of lights, louvers and heaters (and hiding details)
2007-06-28 ROwen    Added support for mirror covers and tertiary rotation.
2007-07-02 ROwen    TertRot widget now can track the current state even if it goes to unknown.
                    Modified tertRot widget to display "?" if unknown.
                    Both changes are due to improvements in RO.Wdg.OptionMenu.
2007-07-05 ROwen    Fix PR 630: tert rot widgets sometimes not properly enabled after rot.
                    Device labels now use " " instead of "_".
                    Added a small margin along the right edge.
2008-01-04 ROwen    Fix PR 701: heater All On/All Off buttons are reversed.
2008-04-28 ROwen    Display tert rot "Home" position correctly (and as a warning).
2008-07-01 ROwen    StatusCmdWdg no longer requires statusBar as an argument.
                    Each widget is disabled while the command it triggered is running.
                    Added a Cancel button to cancel all executing commands.
2008-07-02 ROwen	Commented out a diagnostic print statement.
2008-07-17 ROwen    Added tertiary rotation Restore button.
2010-11-05 ROwen    Eyelids now have status summary and Open All and Close All buttons.
2012-10-26 ROwen    Modified to use separate checkbuttons to toggle state and labels to display state;
                    this works around a bug in Tk (indicatoron is ignored on MacOS X)
                    and may slightly clarify the interface because command and state are separate.
2012-11-13 ROwen    Bug fix: the individual device widges were being mishandled for show/hide.
                    This caused an incorrect display and TUI would freeze when showing devices.
                    Stop using Checkbutton indicatoron=False because it is no longer supported on MacOS X.
2014-05-19 ROwen    Made detection of a running tertiary rotation command more robust.
2015-11-02 ROwen    Switched from arr.any/all to all/any(arr) for numpy arrays
"""
import numpy
import tkinter
if __name__ == '__main__':
    import RO.Comm.Generic
    RO.Comm.Generic.setFramework("tk")
import RO.Alg
import RO.Constants
import RO.Wdg
import TUI.TUIModel
from . import TelMechModel

_HelpURL = "Misc/EnclosureWin.html"

_ColsPerDev = 3 # number of columns for each device widget

class DevStateWdg(RO.Wdg.Label):
    """Widget that displays a summary of device state.
    
    Note: this widget registers itself with the TelMech model
    so once created it self-updates.
    
    Inputs:
    - master: master widget
    - catInfo: category info from the TelMech model
    - onIsNormal: if True/False then severity is normal if all are on/off
    - patternDict: dict of state: (state string, severity)
        where state is a tuple of bools or ints (one per device)
    - **kargs: keyword arguments for RO.Wdg.Label
    """
    def __init__(self,
        master,
        catInfo,
        onIsNormal = True,
        patternDict = None,
    **kargs):
        kargs.setdefault("borderwidth", 2)
        kargs.setdefault("relief", "sunken")
        kargs.setdefault("anchor", "center")
        RO.Wdg.Label.__init__(self, master, **kargs)
        self.patternDict = patternDict or {}    
        self.onIsNormal = onIsNormal
        catInfo.addCallback(self.updateState)

    def updateState(self, catInfo):
        isCurrent = all(catInfo.devIsCurrent)
        stateStr, severity = self.getStateStrSev(catInfo.devState, catInfo)
        self.set(stateStr, isCurrent = isCurrent, severity = severity)

    def getStateStrSev(self, devState, catInfo):
        """Return state string associated with specified device state"""
        if any(numpy.isnan(devState)):
            return ("?", RO.Constants.sevWarning)

        if self.patternDict:
            statusStrSev = self.patternDict.get(tuple(devState.astype(numpy.bool)))
            if statusStrSev is not None:
                return statusStrSev
            
        if all(devState):
            if self.onIsNormal:
                severity = RO.Constants.sevNormal
            else:
                severity = RO.Constants.sevWarning
            return ("All " + catInfo.stateNames[1], severity)
        elif all(devState):
            return ("Some " + catInfo.stateNames[1], RO.Constants.sevWarning)

        # all are off
        if self.onIsNormal:
            severity = RO.Constants.sevWarning
        else:
            severity = RO.Constants.sevNormal
        return ("All " + catInfo.stateNames[0], severity)

class EyelidsStateWdg(DevStateWdg):
    def __init__(self, master, helpURL=None):
        self.model = TelMechModel.getModel()
        DevStateWdg.__init__(self,
            master = master,
            catInfo = self.model.catDict["Eyelids"],
            helpText = "State of the eyelids",
            helpURL = helpURL,
        )
        self.catInfo = self.model.catDict["Eyelids"]
        self.tertRot = self.model.tertRot
        self.model.tertRot.addCallback(self.updateState, callNow=False)

    def updateState(self, *args, **kargs):
        DevStateWdg.updateState(self, self.catInfo)

    def getStateStrSev(self, devState, catInfo):
        """Return state string associated with specified device state"""
        devState = self.catInfo.devState
        
        if any(numpy.isnan(devState)):
            return ("?", RO.Constants.sevWarning)

        if all(devState):
            return ("All " + self.catInfo.stateNames[1], RO.Constants.sevNormal)
        elif not any(devState):
            return ("All " + self.catInfo.stateNames[0], RO.Constants.sevWarning)
        
        # indicate whether the eyelid at the current port is open
        currPortName, isCurrent = self.tertRot.getInd(0)
        if currPortName is not None:
            currPortName = currPortName.upper()
        if currPortName is None:
            return ("Some " + self.catInfo.stateNames[1], RO.Constants.sevNormal)
        devInd = self.catInfo.devIndDict.get(currPortName.upper())
        if devInd is None:
            return ("Some " + self.catInfo.stateNames[1], RO.Constants.sevWarning)
        if devState[devInd]:
            return ("%s Open" % (currPortName,), RO.Constants.sevNormal)
        # matching port is NOT open
        return ("%s Closed" % (currPortName,), RO.Constants.sevWarning)
        

class StatusCommandWdg (tkinter.Frame):
    def __init__(self,
        master,
    **kargs):
        """Create a new widget to show status for and configure the enclosure controller
        """
        tkinter.Frame.__init__(self, master, **kargs)
        self.model = TelMechModel.getModel()
        self.tuiModel = TUI.TUIModel.getModel()
        
        # dict of category: sequence of detailed controls (for show/hide)
        self.detailWdgDict ={}
        
        self.pendingCmds = []

        self.col = 0
        self.row = 0
        self.statusRow = 0
        
        self.addCategory("Shutters")
        self.row += 1
        self.addCategory("Fans")

        self.startNewColumn()
        RO.Wdg.StrLabel(
            master = self,
            text = "Mir Covers",
            helpURL = _HelpURL,
        ).grid(row=self.row, column=self.col)
        self.row += 1
        coversFrame = tkinter.Frame(master = self)
        self.coversUserWdg = RO.Wdg.Checkbutton(
            master = coversFrame,
            autoIsCurrent = True,
            command = self.doCoversCmd,
            helpText = "Open the primary mirror covers?",
            helpURL = _HelpURL,
        )
        self.coversUserWdg.pack(side="left")
        self.coversCurrWdg = RO.Wdg.Label(
            master = coversFrame,
            width = 6,
            anchor = "w",
            helpText = "State of the primary mirror covers?",
            helpURL = _HelpURL,
        )
        self.coversCurrWdg.pack(side="left")
        coversFrame.grid(row=self.row, column=self.col, sticky="w")
        self.row += 3
        self.model.covers.addIndexedCallback(self.updateCovers)
        
        RO.Wdg.StrLabel(
            master = self,
            text = "Tert Rot",
            helpURL = _HelpURL,
        ).grid(row=self.row, column=self.col)
        self.row += 1
        self.tertRotWdg = RO.Wdg.OptionMenu(
            master = self,
            items = list(self.model.catDict["Eyelids"].devDict.keys()),
            noneDisplay = "?",
            ignoreCase = True,
            autoIsCurrent = True,
            defMenu = "Default",
            callFunc = self.tertRotEnable,
            helpText = "Tertiary rotation",
            helpURL = _HelpURL,
        )
        self.tertRotWdg.grid(row=self.row, column=self.col)
        self.row += 1
        self.tertRotApplyWdg = RO.Wdg.Button(
            master = self,
            text = "Apply",
            callFunc = self.doTertRotApply,
            helpText = "Apply tertiary rotation",
            helpURL = _HelpURL,
        )
        self.tertRotApplyWdg.grid(row=self.row, column=self.col)
        self.row += 1
        self.tertRotCurrWdg = RO.Wdg.Button(
            master = self,
            text = "Current",
            callFunc = self.doTertRotRestore,
            helpText = "Show current tertiary rotation",
            helpURL = _HelpURL,
        )
        self.tertRotCurrWdg.grid(row=self.row, column=self.col)
        self.row += 1
        self.model.tertRot.addIndexedCallback(self.updateTertRot)
        
        self.startNewColumn()
        self.eyelidsState = EyelidsStateWdg(
            master = self,
            helpURL = _HelpURL,
        )
        self.eyelidsOpenWdg = RO.Wdg.Button(
            master = self,
            text = "Open All",
            callFunc = self.doEyelidsOpen,
            helpText = "Open all eyelids",
            helpURL = _HelpURL,
        )
        self.eyelidsCloseWdg = RO.Wdg.Button(
            master = self,
            text = "Close All",
            callFunc = self.doEyelidsClose,
            helpText = "Close all eyelids",
            helpURL = _HelpURL,
        )
        self.addCategory(
            catName = "Eyelids",
            extraWdgs = (self.eyelidsState, self.eyelidsOpenWdg, self.eyelidsCloseWdg),
        )
        
        self.startNewColumn()
        self.lightsState = DevStateWdg(
            master = self,
            catInfo = self.model.catDict["Lights"],
            onIsNormal = False,
            patternDict = {
                (0, 0, 0, 0, 0, 0, 1, 0): ("Main Off", RO.Constants.sevNormal),
            },
            helpText = "State of the lights",
            helpURL = _HelpURL,
        )
        self.lightsMainOffWdg = RO.Wdg.Button(
            master = self,
            text = "Main Off",
            callFunc = self.doLightsMainOff,
            helpText = "Turn off all lights except int. incandescents",
            helpURL = _HelpURL,
        )
        self.addCategory("Lights", extraWdgs=(self.lightsState, self.lightsMainOffWdg))
        
        self.startNewColumn()
        self.louversState = DevStateWdg(
            master = self,
            catInfo = self.model.catDict["Louvers"],
            onIsNormal = True,
            helpText = "State of the louvers",
            helpURL = _HelpURL,
        )
        self.louversOpenWdg = RO.Wdg.Button(
            master = self,
            text = "Open All",
            callFunc = self.doLouversOpen,
            helpText = "Open all louvers",
            helpURL = _HelpURL,
        )
        self.louversCloseWdg = RO.Wdg.Button(
            master = self,
            text = "Close All",
            callFunc = self.doLouversClose,
            helpText = "Close all louvers",
            helpURL = _HelpURL,
        )
        self.addCategory(
            catName = "Louvers",
            extraWdgs = (self.louversState, self.louversOpenWdg, self.louversCloseWdg),
        )
        
        self.startNewColumn()
        self.heatersState = DevStateWdg(
            master = self,
            catInfo = self.model.catDict["Heaters"],
            onIsNormal = False,
            helpText = "State of the roof heaters",
            helpURL = _HelpURL,
        )
        self.heatersOffWdg = RO.Wdg.Button(
            master = self,
            text = "All Off",
            callFunc = self.doHeatersOff,
            helpText = "Turn off all roof heaters",
            helpURL = _HelpURL,
        )
        self.heatersOnWdg = RO.Wdg.Button(
            master = self,
            text = "All On",
            callFunc = self.doHeatersOn,
            helpText = "Turn on all roof heaters",
            helpURL = _HelpURL,
        )
        self.addCategory(
            catName = "Heaters",
            extraWdgs = (self.heatersState, self.heatersOffWdg, self.heatersOnWdg),
        )

        self.statusBar = RO.Wdg.StatusBar(
            master = self,
            dispatcher = self.tuiModel.dispatcher,
            prefs = self.tuiModel.prefs,
            playCmdSounds = True,
            summaryLen = 20,
            helpURL = _HelpURL,
        )
        self.statusBar.grid(
            column=0,
            row=self.statusRow + 1,
            columnspan = self.col - 1,
            sticky="sew",
        )
        
        self.cancelBtn = RO.Wdg.Button(
            master = self,
            text = "Cancel",
            callFunc = self.cancelCmds,
            helpText = "Cancel all executing commands",
            helpURL = _HelpURL,
        )
        self.cancelBtn.setEnable(False)
        self.cancelBtn.grid(
            column = self.col,
            row = self.statusRow + 1,
            columnspan = _ColsPerDev,
        )
        
    def addCategory(self, catName, extraWdgs=None):
        """Add a set of widgets for a category of devices"""
        catInfo = self.model.catDict[catName]

        hasDetails = bool(extraWdgs)
        self.addCategoryLabel(catName, hasDetails)
        
        if extraWdgs:
            for ctrl in extraWdgs:
                ctrl.grid(column=self.col, row=self.row, columnspan=_ColsPerDev, sticky="ew")
                self.row += 1

        self.addDevWdgs(catInfo, doHide=bool(extraWdgs))
        
    def addCategoryLabel(self, catName, hasDetails):
        """Add a label for a category of devices"""
        if hasDetails:
            labelWdg = RO.Wdg.Checkbutton(
                master = self,
                text = catName,
                callFunc = self.showHideDetails,
                helpText = "show/hide detailed info",
            )
        else:
            labelWdg = RO.Wdg.StrLabel(self, text=catName)
        labelWdg.grid(
            row = self.row,
            column = self.col,
            columnspan = _ColsPerDev,
        )
        self.row += 1
    
    def addDevWdgs(self, catInfo, doHide):
        """Add a set of widgets to control one device.
        """
#         print "addDevWdgs(catInfo=%r, doHide=%r)" % (catInfo.catName, doHide)
        stateWidth = max([len(name) for name in catInfo.stateNames])
        
        wdgList = []

        for devName, keyVar in catInfo.devDict.items():
            colInd = self.col

            devLabel = devName.replace("_", " ")
            labelWdg = RO.Wdg.StrLabel(
                master = self,
                text = devLabel,
                anchor = "e",
                helpText = None,
                helpURL = _HelpURL,
            )
            wdgList.append(labelWdg)
            labelWdg.grid(row = self.row, column = colInd, sticky="e")
            colInd += 1
            
            ctrlStateFrame = tkinter.Frame(self)

            if not catInfo.readOnly:
                ctrlWdg = RO.Wdg.Checkbutton(
                    master = ctrlStateFrame,
                    onvalue = catInfo.stateNames[1],
                    offvalue = catInfo.stateNames[0],
                    autoIsCurrent = True,
                    helpText = "Toggle %s %s" % (devLabel, catInfo.catNameSingular.lower()),
                    helpURL = _HelpURL,
                )
                ctrlWdg["command"] = RO.Alg.GenericCallback(self._doCmd, catInfo, devName, ctrlWdg)
                keyVar.addROWdg(ctrlWdg, setDefault=True)
                keyVar.addROWdg(ctrlWdg)
                ctrlWdg.pack(side="left")

            stateWdg = RO.Wdg.Label(
                master = ctrlStateFrame,
                width = stateWidth,
                anchor = "w",
                helpText = "State of %s %s" % (devLabel, catInfo.catNameSingular.lower()),
                helpURL = _HelpURL,
            )
            stateWdg.pack(side="left")

            wdgList.append(ctrlStateFrame)
            ctrlStateFrame.grid(row = self.row, column = colInd, sticky="w")
            colInd += 1
            self.row += 1
            
            def updateWdg(value, isCurrent, keyVar=keyVar, stateWdg=stateWdg, stateNames=catInfo.stateNames):
                if value is None:
                    str = "?"
                else:
                    ind = 1 if value else 0
                    str = stateNames[ind]
                stateWdg.set(str, isCurrent=isCurrent)
            keyVar.addIndexedCallback(updateWdg)
            
        if doHide:
            for wdg in wdgList:
                wdg.grid_remove()

        self.detailWdgDict[catInfo.catName] = wdgList
    
    def cancelCmds(self, wdg=None):
        """Cancel all executing commands"""
        locPendingCmds = self.pendingCmds[:]
        for cmd in locPendingCmds:
            try:
                cmd.abort()
            except Exception:
                pass
        # paranoia
        self.pendingCmds = []
        self.cancelBtn.setEnable(False)
    
    def startCmd(self, wdg, cmdStr, cmdCallback=None):
        """Start a command
        
        Enables the Cancel button, disables the appropriate widget
        and sets up a callback that will re-enable it when done
        """
        wdg.setEnable(False)
        if cmdCallback is None:
            cmdCallback = self.cmdDone
        cmdVar = RO.KeyVariable.CmdVar(
            actor = self.model.actor,
            cmdStr = cmdStr,
            callFunc = RO.Alg.GenericCallback(self.cmdDone, wdg),
            callTypes = RO.KeyVariable.DoneTypes,
        )
        self.pendingCmds.append(cmdVar)
        self.cancelBtn.setEnable(True)
        self.statusBar.doCmd(cmdVar)
    
    def cmdDone(self, wdg, msgType, msgDict, cmdVar):
        """A command finished. Re-enable the widget.
        If the command failed then restore the default value.
        Use after because a simple callback will not have the right effect
        if the command fails early during the command button callback.
        """
        wdg.setEnable(True)
        if cmdVar.didFail():
            self.after(10, wdg.restoreDefault)
        self.pendingCmds.remove(cmdVar)
        if not self.pendingCmds:
            self.cancelBtn.setEnable(False)
    
    def doCoversCmd(self):
        """Open or close the primary mirror covers"""
        boolVal = self.coversUserWdg.getBool()
        verbStr = {True: "open", False: "close"}[boolVal]
        cmdStr = "covers %s" % verbStr
        self.coversCurrWdg.setIsCurrent(False)
        self.startCmd(
            wdg = self.coversUserWdg,
            cmdStr = cmdStr,
        )
    
    def doEyelidsClose(self, wdg=None):
        """Close all eyelids"""
        self.startCmd(
            cmdStr = "eyelids all close",
            wdg = self.eyelidsCloseWdg,
        )
    
    def doEyelidsOpen(self, wdg=None):
        """Open all eyelids"""
        self.startCmd(
            cmdStr = "eyelids all open",
            wdg = self.eyelidsOpenWdg,
        )
    
    def doHeatersOff(self, wdg=None):
        """Turn off all roof heaters"""
        self.startCmd(
            cmdStr = "heaters all off",
            wdg = self.heatersOffWdg,
        )

    def doHeatersOn(self, wdg=None):
        """Turn on all roof heaters"""
        self.startCmd(
            cmdStr = "heaters all on",
            wdg = self.heatersOnWdg,
        )

    def doLightsMainOff(self, wdg=None):
        """Turn off main lights"""
        self.startCmd(
            cmdStr = "lights fhalides rhalides incand platform catwalk stairs int_fluor off",
            wdg = self.lightsMainOffWdg,
        )
    
    def doLouversClose(self, wdg=None):
        """Close all louvers"""
        self.startCmd(
            cmdStr = "louvers all close",
            wdg = self.louversCloseWdg,
        )
    
    def doLouversOpen(self, wdg=None):
        """Open all louvers"""
        self.startCmd(
            cmdStr = "louvers all open",
            wdg = self.louversOpenWdg,
        )

    def isTertRotCmdRunning(self):
        """Return True if a tertiary rotation command is running
        """
        for cmdVar in self.pendingCmds:
            if not cmdVar.isDone() and cmdVar.cmdStr.startswith("tertrot"):
                return True
        return False
    
    def doTertRotApply(self, wdg=None):
        """Apply tertiary rotation command"""
        desTertRot = self.tertRotWdg.getString().lower()
        cmdStr = "tertrot %s" % desTertRot
        self.startCmd(
            cmdStr = cmdStr,
            wdg = self.tertRotWdg,
            cmdCallback = self.tertRotCmdCallback,
        )
        self.tertRotEnable()
    
    def doTertRotRestore(self, wdg=None):
        """Restore tertRot to current value"""
        self.tertRotWdg.restoreDefault()
        self.tertRotEnable()
    
    def showHideDetails(self, wdg):
        """Show or hide detailed controls for a category"""
        catName = wdg["text"]
        doShow = wdg.getBool()
        detailWdgs = self.detailWdgDict[catName]
        if doShow:
            for wdg in detailWdgs:
                wdg.grid()
        else:
            for wdg in detailWdgs:
                wdg.grid_remove()
    
    def tertRotCmdCallback(self, msgType, msgDict, cmdVar):
        """Tertiary rotation command callback function"""
        if cmdVar.isDone():
            self.tertRotWdg.setEnable(True)
            self.tertRotEnable()
    
    def tertRotEnable(self, wdg=None):
        """Enable or disable tertiary rotation Apply and Restore buttons

        Note: the Tert Rot option menu is handled separately.
        """
        isDefault = self.tertRotWdg.isDefault()
        cmdRunning = self.isTertRotCmdRunning()
#        print "tertRotEnable; isDefault=%s, cmdRunning=%s" % (isDefault, cmdRunning)
        enableBtns = not isDefault and not cmdRunning
        self.tertRotApplyWdg.setEnable(enableBtns)
        self.tertRotCurrWdg.setEnable(enableBtns)
    
    def updateCovers(self, value, isCurrent, keyVar=None):
        """Handle covers keyword data"""
#         print "updateCovers(value=%r, isCurrent=%r)" % (value, isCurrent)
        if value is None:
            severity = RO.Constants.sevWarning
            strValue = "?"
        else:
            if value:
                severity = RO.Constants.sevNormal
                strValue = "Open"
            else:
                severity = RO.Constants.sevWarning
                strValue = "Closed"
        self.coversCurrWdg.set(strValue, severity=severity, isCurrent=isCurrent)
        self.coversUserWdg.set(value)
        self.coversUserWdg.setDefault(value, severity=severity, isCurrent=isCurrent)
    
    def updateTertRot(self, value, isCurrent, keyVar=None):
        """Handle tertRot keyword data"""
        if value is None or value.lower() == "home":
            severity = RO.Constants.sevWarning
        else:
            severity = RO.Constants.sevNormal
        self.tertRotWdg.setDefault(value, severity=severity, doCheck=False)
        self.tertRotEnable()
    
    def _doCmd(self, catInfo, devName, ctrlWdg):
        """Change the state of a device with category info"""
#        print "_doCmd(catInfo=%r, devName=%r, ctrlWdg=%r)" % (catInfo, devName, ctrlWdg)

        boolVal = ctrlWdg.getBool()
        verbStr = catInfo.getVerbStr(boolVal)
        cmdStr = "%s %s %s" % (catInfo.catName, devName, verbStr)
        cmdStr = cmdStr.lower()
        self.startCmd(cmdStr = cmdStr, wdg=ctrlWdg)
    
    def startNewColumn(self):
        """Start a new column of controls"""
        self.statusRow = max(self.statusRow, self.row)
        self.row = 0
        self.col += _ColsPerDev
        # create narrow blank column
        RO.Wdg.StrLabel(self, text=" ").grid(row=self.row, column=self.col)
        self.col += 1

        
if __name__ == '__main__':
    from . import TestData
    root = TestData.tuiModel.tkRoot
    root.resizable(width=0, height=0)
        
    testFrame = StatusCommandWdg (root)
    testFrame.pack()

    tkinter.Button(root, text="Demo", command=TestData.runDemo).pack()
    
    TestData.init()
    
    root.mainloop()
