#!/usr/bin/env python
"""Configuration input panel for TripleSpec.

History:
2008-03-14 ROwen
2008-04-11 ROwen    Added needed keywords to commands.
                    Eliminated a spurious warning for temperature data.
2008-07-24 ROwen    Fixed CR 854: removed Array Power display and control.
2008-11-17 ROwen    Fixed PR 905: temperature alarms not properly reported.
2008-11-18 ROwen    Fixed an error in yesterday's fix.
2012-11-13 ROwen    Stop using Checkbutton indicatoron=False because it is no longer supported on MacOS X.
2012-11-16 ROwen    Disable the ability to change slits; a temporary hack while TSpec's slit changer is broken.
2014-03-14 ROwen    Added a Presets widget
"""
import math
import tkinter
import RO.Constants
import RO.MathUtil
import RO.Wdg
import RO.KeyVariable
import TUI.TUIModel
from . import TSpecModel

_EnvWidth = 6 # width of environment value columns

class StatusConfigInputWdg (RO.Wdg.InputContFrame):
    InstName = "TSpec"
    HelpPrefix = 'Instruments/%s/%sWin.html#' % (InstName, InstName)
    ConfigCat = RO.Wdg.StatusConfigGridder.ConfigCat
    TipTiltCat = "tipTilt"
    EnvironCat = "environ"
    
    def __init__(self,
        master,
        stateTracker,        
    **kargs):
        """Create a new widget to show status for and configure the Dual Imaging Spectrograph

        Inputs:
        - master: parent widget
        - stateTracker: an RO.Wdg.StateTracker
        """
        RO.Wdg.InputContFrame.__init__(self, master, stateTracker=stateTracker, **kargs)
        self.model = TSpecModel.getModel()
        self.tuiModel = TUI.TUIModel.getModel()

        # save last known exposure mode number for each exposure mode
        self.currExpModeNumDict = {}

        self.gridder = RO.Wdg.StatusConfigGridder(
            master = self,
            sticky = "w",
        )
        
        #
        # Exposure Mode
        #
        currExpModeFrame = tkinter.Frame(self)
        self.currExpModeNameWdg = RO.Wdg.StrLabel(
            master = currExpModeFrame,
            anchor = "w",
            helpText = "Current exposure mode",
            helpURL = self.HelpPrefix + "ExposureMode",
        )
        self.currExpModeNameWdg.pack(side="left")
        self.currExpModeNumWdg = RO.Wdg.IntLabel(
            master = currExpModeFrame,
            helpText = "Current number of samples",
            helpURL = self.HelpPrefix + "ExposureMode",
        )
        self.currExpModeNumWdg.pack(side="left")

        userExpModeFrame = tkinter.Frame(self)
        self.userExpModeNameWdg = RO.Wdg.OptionMenu(
            master = userExpModeFrame,
            autoIsCurrent = True,
            items = [],
            callFunc = self._updUserModeName,
            helpText = "Desired exposure mode",
            helpURL = self.HelpPrefix + "ExposureMode",
            defMenu = "Current",
        )
        self.userExpModeNameWdg.pack(side="left")
        self.userExpModeNumWdg = RO.Wdg.IntEntry(
            master = userExpModeFrame,
            helpText = "Current number of samples",
            helpURL = self.HelpPrefix + "ExposureMode",
            autoIsCurrent = True,
            defMenu = "Current",
            minMenu = "Minimum",
            maxMenu = "Maximum",
        )
        self.userExpModeNumWdg.pack(side="left")
        self.gridder.gridWdg("Exposure Mode", currExpModeFrame, None, userExpModeFrame, colSpan=2)
        self.model.exposureModeInfo.addCallback(self._updExposureModeInfo)
        self.model.exposureMode.addCallback(self._updExposureMode)
        
        #
        # Slit
        #
        self.currSlitWdg = RO.Wdg.StrLabel(
            master = self,
            anchor = "w",
            helpText = "Current slit",
            helpURL = self.HelpPrefix + "Slit",
        )
        self.userSlitWdg = RO.Wdg.OptionMenu(
            master = self,
            autoIsCurrent = True,
            items = (),
            helpText = "Desired slit",
            helpURL = self.HelpPrefix + "Slit",
        )
# disable user's ability to change slits until TSpec is fixed
        self.gridder.gridWdg("Slit", self.currSlitWdg, colSpan=2)
#        self.gridder.gridWdg("Slit", self.currSlitWdg, None, self.userSlitWdg, colSpan=2)
        self.model.slitPosition.addIndexedCallback(self._updSlitPosition)
        self.model.slitPositions.addCallback(self._updSlitPositions)
        
        #
        # Tip-tilt
        #
        self.tipTiltShowHideWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Tip-Tilt Mode",
            helpText = "Show tip-tilt controls?",
            helpURL = self.HelpPrefix + "TipTilt",
        )
        self._stateTracker.trackCheckbutton("showTipTilt", self.tipTiltShowHideWdg)

        ttModeNames = ("ClosedLoop", None, "OpenLoop", "Offline")
        maxTTModeNameLen = max([len(m) for m in ttModeNames if m])
        self.currTipTiltModeWdg = RO.Wdg.StrLabel(
            master = self,
            width = maxTTModeNameLen,
            anchor = "w",
            helpText = "Current tip-tilt mode",
            helpURL = self.HelpPrefix + "TipTilt",
        )
        self.userTipTiltModeWdg = RO.Wdg.OptionMenu(
            master = self,
            autoIsCurrent = True,
            items = ttModeNames,
            ignoreCase = True,
            width = maxTTModeNameLen,
            callFunc = self._updUserTTMode,
            helpText = "Desired tip-tilt mode",
            helpURL = self.HelpPrefix + "TipTilt",
        )
        wdgSet = self.gridder.gridWdg(
            self.tipTiltShowHideWdg,
            self.currTipTiltModeWdg,
            None,
            self.userTipTiltModeWdg,
            colSpan=2,
        )
        self.gridder.addShowHideWdg(self.TipTiltCat, wdgSet.cfgWdg)
    
        self.currTipTiltPosWdgSet = (
            RO.Wdg.FloatLabel(
                master = self,
                precision = 3,
                helpText = "Current x tip-tilt",
                helpURL = self.HelpPrefix + "TipTilt",
            ),
            RO.Wdg.FloatLabel(
                master = self,
                precision = 3,
                helpText = "Current y tip-tilt",
                helpURL = self.HelpPrefix + "TipTilt",
            ),
        )
        self.userTipTiltPosWdgSet = (
            RO.Wdg.FloatEntry(
                master = self,
                helpText = "Desired x tip-tilt",
                helpURL = self.HelpPrefix + "TipTilt",
            ),
            RO.Wdg.FloatEntry(
                master = self,
                helpText = "Desired y tip-tilt",
                helpURL = self.HelpPrefix + "TipTilt",
            ),
        )
        self.gridder.gridWdg(
            "Tip-Tilt Position",
            self.currTipTiltPosWdgSet,
            None,
            self.userTipTiltPosWdgSet,
            cat = self.TipTiltCat,
        )
        self.model.ttMode.addIndexedCallback(self._updTTMode)
        self.model.ttLimits.addCallback(self._updTTLimits)
        self.model.ttPosition.addCallback(self._updTTPosition)

        class KeyCmdFmt(RO.InputCont.BasicFmt):
            def __init__(self, keyword, valSep=",", doQuote=False):
                self.keyword = keyword
                self.valSep = str(valSep)
                self.doQuote = bool(doQuote)
            def __call__(self, inputCont):
                valList = inputCont.getValueList()
                if not valList:
                    return ""
                if self.doQuote:
                    valFmt = "\"%s\""
                else:
                    valFmt = "%s"
                valStrList = [valFmt % (val,) for val in valList]
                valStr = self.valSep.join(valStrList)
                name = inputCont.getName()
                return "%s %s=%s" % (name, self.keyword, valStr)

        self.inputCont = RO.InputCont.ContList (
            conts = [
                RO.InputCont.WdgCont (
                    name = 'mode',
                    wdgs = (self.userExpModeNameWdg, self.userExpModeNumWdg),
                    formatFunc = RO.InputCont.BasicFmt(valSep="=")
                ),
                RO.InputCont.WdgCont (
                    name = 'ttMode',
                    wdgs = self.userTipTiltModeWdg,
                    formatFunc = KeyCmdFmt("mode"),
                ),
                RO.InputCont.WdgCont (
                    name = 'gotoSlit',
                    wdgs = self.userSlitWdg,
                    formatFunc = KeyCmdFmt("position", doQuote=True),
                ),
                RO.InputCont.WdgCont (
                    name = 'ttPosition',
                    wdgs = self.userTipTiltPosWdgSet,
                    formatFunc = KeyCmdFmt("newposition"),
                ),
            ],
        )

        self.configWdg = RO.Wdg.InputContPresetsWdg(
            master = self,
            sysName = "%sConfig" % (self.InstName,),
            userPresetsDict = self.tuiModel.userPresetsDict,
            inputCont = self.inputCont,
            helpText = "use and manage named presets",
            helpURL = self.HelpPrefix + "Presets",
        )
        self.gridder.gridWdg(
            "Presets",
            cfgWdg = self.configWdg,
            colSpan = 2,
        )

        #
        # Environmental widgets
        #

        self.environShowHideWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Environment",
            helpText = "Show pressure and temps?",
            helpURL = self.HelpPrefix + "Environment",
        )
        self._stateTracker.trackCheckbutton("showEnviron", self.environShowHideWdg)
        
        self.environStatusWdg = RO.Wdg.StrLabel(
            master = self,
            anchor = "w",
            helpText = "Are pressure and temps OK?",
            helpURL = self.HelpPrefix + "Environment",
        )

        self.gridder.gridWdg (
            label = self.environShowHideWdg,
            dataWdg = self.environStatusWdg,
            colSpan = 2,
        )
         
        # hidable frame showing current pressure and temperatures

        self.envFrameWdg = tkinter.Frame(master=self, borderwidth=1, relief="solid")
        
        # create header
        headStrSet = (
            "Sensor",
            "Curr",
            "Min",
            "Max",
        )
        
        for ii in range(len(headStrSet)):
            headLabel = RO.Wdg.Label(
                master = self.envFrameWdg,
                text = headStrSet[ii],
                anchor = "e",
                helpURL = self.HelpPrefix + "Environment",
            )
            headLabel.grid(row=0, column=ii, sticky="e")


        # create vacuum widgets
        
        vacuumHelpStrs = (
            "vacuum",
            "current vacuum",
            None,
            "maximum safe vacuum",
        )

        rowInd = 1
        colInd = 0
        wdg = RO.Wdg.StrLabel(
            master = self.envFrameWdg,
            text = "Vacuum",
            anchor = "e",
            helpText = vacuumHelpStrs[0],
            helpURL = self.HelpPrefix + "Environment",
        )
        wdg.grid(row = rowInd, column = colInd, sticky="e")
        newWdgSet = [wdg]
        for colInd in range(1, 4):
            wdg = RO.Wdg.Label(
                master = self.envFrameWdg,
                formatFunc = fmtExp,
                width = _EnvWidth,
                anchor = "e",
                helpText = vacuumHelpStrs[colInd],
                helpURL = self.HelpPrefix + "Environment",
            )
            wdg.grid(row = rowInd, column = colInd, sticky="ew")
            newWdgSet.append(wdg)
        colInd += 1
        wdg = RO.Wdg.StrLabel(
            master = self.envFrameWdg,
            text = "torr",
            anchor = "w",
        )
        wdg.grid(row = rowInd, column = colInd, sticky="w")
        newWdgSet.append(wdg)
        self.vacuumWdgSet = newWdgSet

        # temperatures

        self.tempHelpStrSet = (
            "temperature sensor",
            "current temperature",
            "minimum safe temperature",
            "maximum safe temperature",
        )
        
        # create blank widgets to display temperatures
        # this set is indexed by row (sensor)
        # and then by column (name, current temp, min temp, max temp)
        self.tempWdgSet = []
        nextCol = self.gridder.getNextCol()
        
        self.gridder.gridWdg (
            label = False,
            dataWdg = self.envFrameWdg,
            cfgWdg = False,
            colSpan = nextCol + 1,
            sticky = "w",
            numStatusCols = None,
            cat = self.EnvironCat,
        )
        
        self.columnconfigure(nextCol, weight=1)
       
        self.gridder.allGridded()

        self.model.tempNames.addCallback(self._updEnviron, callNow = False)
        self.model.temps.addCallback(self._updEnviron, callNow = False)
        self.model.tempAlarms.addCallback(self._updEnviron, callNow = False)
        self.model.tempThresholds.addCallback(self._updEnviron, callNow = False)
        self.model.vacuum.addCallback(self._updEnviron, callNow = False)
        self.model.vacuumAlarm.addCallback(self._updEnviron, callNow = False)
        self.model.vacuumThreshold.addCallback(self._updEnviron, callNow = False)
        
        self.tipTiltShowHideWdg.addCallback(self._doShowHide, callNow = False)
        self.environShowHideWdg.addCallback(self._doShowHide, callNow = False)

    def _addTempWdgRow(self):
        """Add a row of temperature widgets"""
        rowInd = len(self.tempWdgSet) + 2
        colInd = 0
        wdg = RO.Wdg.StrLabel(
            master = self.envFrameWdg,
            anchor = "e",
            helpText = self.tempHelpStrSet[colInd],
            helpURL = self.HelpPrefix + "Environment",
        )
        wdg.grid(row = rowInd, column = colInd, sticky="e")
        newWdgSet = [wdg]
        for colInd in range(1, 4):
            wdg = RO.Wdg.FloatLabel(
                master = self.envFrameWdg,
                precision = 1,
                anchor = "e",
                helpText = self.tempHelpStrSet[colInd],
                helpURL = self.HelpPrefix + "Environment",
            )
            wdg.grid(row = rowInd, column = colInd, sticky="ew")
            newWdgSet.append(wdg)
        colInd += 1
        wdg = RO.Wdg.StrLabel(
            master = self.envFrameWdg,
            text = "K",
            anchor = "w",
        )
        wdg.grid(row = rowInd, column = colInd, sticky="w")
        newWdgSet.append(wdg)
        self.tempWdgSet.append(newWdgSet)

    def _doShowHide(self, wdg=None):
        showTipTilt = self.tipTiltShowHideWdg.getBool()
        showTemps = self.environShowHideWdg.getBool()
        argDict = {
            self.TipTiltCat: showTipTilt,
            self.EnvironCat: showTemps,
        }
        self.gridder.showHideWdg (**argDict)

    def _updEnviron(self, *args, **kargs):
        """Update environmental data"""
        isCurrent = True

        # handle vacuum
        vacuum, vacuumCurr = self.model.vacuum.getInd(0)
        vacuumAlarm, vacuumAlarmCurr = self.model.vacuumAlarm.getInd(0)
        vacuumThresh, vacuumThreshCurr = self.model.vacuumThreshold.getInd(0)
        isCurrent = isCurrent and vacuumCurr and vacuumAlarmCurr and vacuumThreshCurr

        if vacuumAlarm is not None and vacuumAlarm:
            vacuumSev = RO.Constants.sevError
            vacuumOK = False
        else:
            vacuumSev = RO.Constants.sevNormal
            vacuumOK = True
        self.vacuumWdgSet[0].setSeverity(vacuumSev)
        self.vacuumWdgSet[1].set(vacuum, isCurrent = vacuumCurr, severity = vacuumSev)
        self.vacuumWdgSet[3].set(vacuumThresh, isCurrent = vacuumThreshCurr, severity = vacuumSev)
        
        # handle temperatures

        tempNames, namesCurr = self.model.tempNames.get()
        temps, tempsCurr = self.model.temps.get()
        tempAlarms, tempAlarmsCurr = self.model.tempAlarms.get()
        tempThresholds, tempThreshCurr = self.model.tempThresholds.get()
        if () in (tempNames, temps, tempAlarms, tempThresholds):
            return
        tempMin = [None]*len(tempThresholds)
        tempMax = [None]*len(tempThresholds)
        for ii, t in enumerate(tempThresholds):
            if t is None:
                continue
            if t > 0:
                tempMax[ii] = t
            else:
                tempMin[ii] = t
        isCurrent = isCurrent and namesCurr and tempsCurr and tempAlarmsCurr and tempThreshCurr

        if not (len(temps) == len(tempNames) == len(tempAlarms) == len(tempThresholds)):
            # temp data not self-consistent
            self.tuiModel.logMsg(
                "TSpec temperature data not self-consistent; cannot test temperature limits",
                severity = RO.Constants.sevWarning,
            )
            for wdgSet in self.tempWdgSet:
                for wdg in wdgSet:
                    wdg.setNotCurrent()
            return
            
        tempSet = list(zip(tempNames, temps, tempMin, tempMax))
        isCurrSet = namesCurr, tempsCurr, tempThreshCurr, tempThreshCurr

        # add new widgets if necessary
        for ii in range(len(self.tempWdgSet), len(tempSet)):
            self._addTempWdgRow()
        
        # set widgets
        allTempsOK = True
        for ii in range(len(tempSet)):
            wdgSet = self.tempWdgSet[ii]
            infoSet = tempSet[ii]
            tName, tCurr, tMin, tMax = infoSet
            
            sevSet = [RO.Constants.sevNormal] * 4 # assume temp OK
            if tCurr is not None:
                if tempAlarms[ii]:
                    allTempsOK = False
                    sevSet = [RO.Constants.sevError] * 4

            for wdg, info, isCurr, severity in zip(wdgSet, infoSet, isCurrSet, sevSet):
                wdg.set(info, isCurrent = isCurr, severity = severity)

        if vacuumOK and allTempsOK:
            self.environStatusWdg.set(
                "OK",
                isCurrent = isCurrent,
                severity = RO.Constants.sevNormal,
            )
        else:
            self.environStatusWdg.set(
                "Bad", 
                isCurrent = isCurrent,
                severity = RO.Constants.sevError,
            )
    
        # delete extra widgets, if any
        for ii in range(len(tempSet), len(self.tempWdgSet)):
            wdgSet = self.tempWdgSet.pop(ii)
            for wdg in wdgSet:
                wdg.grid_forget()
                del(wdg)

    def _updExposureMode(self, currExpModeNameNum, isCurrent=True, keyVar=None):
        """New exposure mode information.

        Update current info and store current value tied to current mode.
        If user mode matches then also update its default.
        """
        currExpModeName, currExpModeNum = currExpModeNameNum
        self.currExpModeNameWdg.set(currExpModeName, isCurrent=isCurrent)
        self.currExpModeNumWdg.set(currExpModeNum, isCurrent=isCurrent)
        if currExpModeName:
            self.currExpModeNumDict[currExpModeName] = currExpModeNum
        self.userExpModeNameWdg.setDefault(currExpModeName, isCurrent=isCurrent, doCheck=False)
        userExpModeName = self.userExpModeNameWdg.getString()
        if userExpModeName == currExpModeName:
            self.userExpModeNumWdg.setDefault(currExpModeNum, isCurrent=isCurrent)
        
    def _updExposureModeInfo(self, expModeInfo, isCurrent=True, keyVar=None):
        modeNames = list(self.model.exposureModeInfoDict.keys())
        modeNames.sort()
        self.userExpModeNameWdg.setItems(modeNames)
        
        maxNameLen = 0
        minRange = 0
        maxRange = 0
        for name, minMax in self.model.exposureModeInfoDict.items():
            maxNameLen = max(maxNameLen, len(name))
            minRange = min(minRange, minMax[0])
            maxRange = max(maxRange, minMax[1])
            self.currExpModeNumDict.setdefault(name, minMax[0])
        if maxRange > 0:
            maxNumWidth = int(math.log10(abs(maxRange)) + 1.0)
            if minRange < 0:
                maxNumWidth = max(maxNumWidth, int(math.log10(abs(maxRange)) + 1.0))
            self.userExpModeNameWdg["width"] = maxNameLen
            self.userExpModeNumWdg["width"] = maxNumWidth
    
    def _updSlitPositions(self, slitPositions, isCurrent=True, keyVar=None):
        nameLengths = [len(n) for n in slitPositions if n]
        if not nameLengths:
           return
        self.userSlitWdg.setItems(slitPositions)
        self.userSlitWdg["width"] = max(nameLengths)
    
    def _updSlitPosition(self, slitPosition, isCurrent=True, keyVar=None):
        self.currSlitWdg.set(slitPosition, isCurrent=isCurrent)
        self.userSlitWdg.setDefault(slitPosition, isCurrent=isCurrent, doCheck=False)
    
    def _updTTMode(self, ttMode, isCurrent=True, keyVar=None):
        ttLower = ttMode and ttMode.lower()
        isOn = ttLower != "off"
        if ttLower in ("off", "closedloop"):
            severity = RO.Constants.sevNormal
        else:
            severity = RO.Constants.sevWarning
        self.currTipTiltModeWdg.set(ttMode, isCurrent=isCurrent, severity=severity)
        self.userTipTiltModeWdg.setEnable(isOn)
        for wdg in self.userTipTiltPosWdgSet:
            wdg.setEnable(isOn)
        self.userTipTiltModeWdg.setDefault(ttMode, isCurrent=isCurrent, doCheck=False)
        if not isOn:
            self.userTipTiltModeWdg.restoreDefault()

    def _updTTLimits(self, ttLimits, isCurrent=True, keyVar=None):
        if None in ttLimits:
            return
        for wdgInd in range(2):
            limInd = wdgInd * 2
            self.userTipTiltPosWdgSet[wdgInd].setRange(ttLimits[limInd], ttLimits[limInd+1], adjustWidth=True)

    def _updTTPosition(self, ttPosition, isCurrent=True, keyVar=None):
        for ii in range(2):
            self.currTipTiltPosWdgSet[ii].set(ttPosition[ii], isCurrent=isCurrent)
            self.userTipTiltPosWdgSet[ii].setDefault(ttPosition[ii], isCurrent=isCurrent)
    
    def _updUserModeName(self, wdg=None):
        modeName = self.userExpModeNameWdg.getString()
        if not modeName:
            return
        
        # update default value and range in a way that will avoid errors
        newDef = self.currExpModeNumDict.get(modeName)
        self.userExpModeNumWdg.setRange(None, None) # so new value not out of range
        self.userExpModeNumWdg.setDefault(newDef)
        minMax = self.model.exposureModeInfoDict.get(modeName, None)
        if minMax:
            self.userExpModeNumWdg.setRange(minMax[0], minMax[1])

    def _updUserTTMode(self, wdg=None):
        ttMode = self.userTipTiltModeWdg.getString()
        if ttMode and ttMode.lower() != "closedloop":
            severity = RO.Constants.sevWarning
        else:
            severity = RO.Constants.sevNormal
        self.userTipTiltModeWdg.setSeverity(severity)
    
def fmtExp(num):
    """Formats a floating-point number as x.xe-x"""
    retStr = "%.1e" % (num,)
    if retStr[-2] == '0':
        retStr = retStr[0:-2] + retStr[-1]
    return retStr


if __name__ == "__main__":
    from . import TestData
    root = TestData.tuiModel.tkRoot
    stateTracker = RO.Wdg.StateTracker(logFunc=TestData.tuiModel.logFunc)

    testFrame = StatusConfigInputWdg (root, stateTracker=stateTracker)
    testFrame.pack()
    
    TestData.start()

    testFrame.restoreDefault()

    def printCmds():
        print("Commands:")
        cmdList = testFrame.getStringList()
        for cmd in cmdList:
            print(cmd)
    
    RO.Wdg.StatusBar(root).pack(side="top", expand=True, fill="x")
    bf = tkinter.Frame(root)
    cfgWdg = RO.Wdg.Checkbutton(bf, text="Config", defValue=True)
    cfgWdg.pack(side="left")
    tkinter.Button(bf, text="Cmds", command=printCmds).pack(side="left")
    tkinter.Button(bf, text="Current", command=testFrame.restoreDefault).pack(side="left")
    tkinter.Button(bf, text="Demo", command=TestData.animate).pack(side="left")
    bf.pack()

    testFrame.gridder.addShowHideControl(testFrame.ConfigCat, cfgWdg)

    root.mainloop()
