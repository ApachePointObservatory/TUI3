#!/usr/bin/env python
"""Configuration input panel for Agile.

To do:
- Add filter wheel support.
- Support downloading every Nth image, or at least skipping images if we get behind.

History:
2008-10-24 ROwen    preliminary adaptation from DIS
2008-11-06 ROwen    Removed unused detector controls; the rest is not yet functional
2008-11-07 ROwen    Implemented temperature display. Still need functional filter control.
2008-11-10 ROwen    Commented out nonfunctional filter code.
                    Set minimum temperature width so no info shows up properly.
                    Call temperature callbacks right away.
2009-04-17 ROwen    Added full evironmental display
2009-04-20 ROwen    Commented out a debug print statement.
2009-06-25 ROwen    Remove filter controls.
2009-06-25 ROwen    Tweaked environment display:
                    - Show OK instead of "Camera: Connected" when all is well.
                    - Show "Connection Failed/Failing" instead of "Failed/Failing" to make the display of
                      those two connection states clearer. The other connection states need no clarification.
                    - Show filter wheel moving or homing as a warning instead of a normal state.
2009-07-02 ROwen    Modified for updated TestData.
2009-07-10 ROwen    Removed an inline conditional statement to be Python 2.4 compatible.
                    Modified for updated TestData.
2012-11-13 ROwen    Stop using Checkbutton indicatoron=False because it is no longer supported on MacOS X.
2012-11-14 ROwen    Update help text for show/hide controls for checkbuttons with indicatoron.
2015-11-05 ROwen    Changed ==/!= True/False to is/is not True/False to modernize the code.
                    Removed some unused variables.
"""
import tkinter
import RO.Constants
import RO.Wdg
import TUI.Base.StateSet
from . import AgileModel

_EnvWidth = 6 # width of environment value columns

StCameraConn = "Camera"
StCCDTemp = "CCD Temp"
StCCDSetTemp = "CCD Set Temp"
StGPSSynced = "GPS Synced"
StNTPStatus = "NTP Status"
StFWConn = "Filter Wheel"
StFWMotor = "Filter Wheel Motor"
StNames = (StCameraConn, StCCDTemp, StCCDSetTemp, StGPSSynced, StNTPStatus, StFWConn, StFWMotor)

class StatusConfigInputWdg (RO.Wdg.InputContFrame):
    InstName = "Agile"
    HelpPrefix = "Instruments/%sWin.html#" % (InstName,)

    # category names
    EnvironCat = 'temp'

    def __init__(self,
        master,
    **kargs):
        """Create a new widget to show status for and configure Agile
        """
        RO.Wdg.InputContFrame.__init__(self, master, **kargs)
        self.model = AgileModel.getModel()
        
        self.environStateSet = TUI.Base.StateSet.StateSet(StNames, callFunc=self._updEnvironStateSet)
        
        self.settingCurrWin = False
    
        gr = RO.Wdg.StatusConfigGridder(
            master = self,
            sticky = "w",
            numStatusCols = 3,
        )
        self.gridder = gr

        # Temperature State information
        
        self.ccdTempStateDict = {
            None: (None, RO.Constants.sevNormal),
            "normal": ("", RO.Constants.sevNormal),
            "low": ("Low", RO.Constants.sevWarning),
            "high": ("High", RO.Constants.sevWarning),
            "verylow": ("Very Low", RO.Constants.sevError),
            "veryhigh": ("Very High", RO.Constants.sevError),
        }
        
        # Environment
        
        self.environShowHideWdg = RO.Wdg.Checkbutton(
            master = self,
            text = "Environ",
            helpText = "Show environment details?",
            helpURL = self.HelpPrefix + "Environ",
        )
        
        self.environSummaryWdg = RO.Wdg.StrLabel(
            master = self,
            helpText = "Environment summary",
            helpURL = self.HelpPrefix + "Environ",
        )

        gr.gridWdg (
            label = self.environShowHideWdg,
            dataWdg = self.environSummaryWdg,
            colSpan=3,
            numStatusCols = None,
        )

        # Camera connected
        self.cameraConnStateWdg = RO.Wdg.StrLabel(
            master = self,
            anchor = "w",
            helpText = "Camera connection state",
            helpURL = self.HelpPrefix + "env_Camera",
        )
        gr.gridWdg("Camera", self.cameraConnStateWdg, cat = self.EnvironCat)
        
        self.ccdTempWdg = RO.Wdg.StrLabel(
            master = self,
            helpText = "Current CCD Temp (C)",
            helpURL = self.HelpPrefix + "env_CCDTemp",
        )
        
        gr.gridWdg (
            label = StCCDTemp,
            dataWdg = self.ccdTempWdg,
            cat = self.EnvironCat,
        )
        
        # CCD Set Temperature
        
        self.ccdSetTempWdg = RO.Wdg.StrLabel(
            master = self,
            helpText = "Desired CCD Temp (C)",
            helpURL = self.HelpPrefix + "env_CCDSetTemp",
        )

        gr.gridWdg (
            label = StCCDSetTemp,
            dataWdg = self.ccdSetTempWdg,
            cat = self.EnvironCat,
        )
        
        # CCD Temperature Limits
        
        self.ccdTempLimitsFrame = tkinter.Frame(self)
        self.ccdTempLimitsWdgSet = []
        for col, limitName in enumerate(("Low", "High", "Very Low", "Very High")):
            ccdTempLimitWdg = RO.Wdg.FloatLabel(
                self.ccdTempLimitsFrame,
                precision = 1,
                width = _EnvWidth,
                helpText = "Error limit for %s CCD temp." % (limitName.lower(),),
                helpURL = self.HelpPrefix + "env_CCDTempLimits",
            )
            ccdTempLimitWdg.grid(row=0, column=col)
            self.ccdTempLimitsWdgSet.append(ccdTempLimitWdg)
        
        gr.gridWdg(
            label = "CCD Temp Limits",
            dataWdg = self.ccdTempLimitsFrame,
            colSpan = 10,
            numStatusCols = None,
            cat = self.EnvironCat,
        )
        
        self.gpsSyncedWdg = RO.Wdg.StrLabel(
            master = self,
            anchor = "w",
            helpText = "Is clock card synched to the GPS clock?",
            helpURL = self.HelpPrefix + "env_GPSSynced",
        )
       
        gr.gridWdg(
            label = StGPSSynced,
            dataWdg = self.gpsSyncedWdg,
            cat = self.EnvironCat,
         )
        
        self.ntpStatusFrame = tkinter.Frame(self)
        self.ntpStatusWdgSet = []
        for col, helpStr in enumerate(("Is NTP client running?", "NTP server", "Stratum of NTP server")):
            ntpStatusWdg = RO.Wdg.StrLabel(
                self.ntpStatusFrame,
                helpText = helpStr,
                helpURL = self.HelpPrefix + "env_NTPStatus",
            )
            ntpStatusWdg.grid(row=0, column=col)
            self.ntpStatusWdgSet.append(ntpStatusWdg)

        gr.gridWdg(
            label = StNTPStatus,
            dataWdg = self.ntpStatusFrame,
            colSpan = 10,
            numStatusCols = None,
            cat = self.EnvironCat,
         )
         
         # filter related status

        self.fwConnStateWdg = RO.Wdg.StrLabel(
            master = self,
            anchor = "w",
            helpText = "Filter wheel connection state",
            helpURL = self.HelpPrefix + "env_FilterWheel",
        )
        gr.gridWdg(StFWConn, self.fwConnStateWdg, cat = self.EnvironCat)
        
        self.fwHomedWdg = RO.Wdg.StrLabel(
            master = self,
            anchor = "w",
            helpText = "Filter wheel motor state",
            helpURL = self.HelpPrefix + "env_FilterWheelMotor",
        )
       
        gr.gridWdg(
            label = StFWMotor,
            dataWdg = self.fwHomedWdg,
            cat = self.EnvironCat,
         )

        gr.allGridded()
        
        self.gpsSyncedDict = {
            True: (RO.Constants.sevNormal, "Yes"),
            False: (RO.Constants.sevError, "No"),
            None: (RO.Constants.sevWarning, "?"),
        }
        
        self.ntpRunningDict = {
            True: "Running",
            False: "NotRunning",
            None: "?",
        }

        # add callbacks that deal with multiple widgets
        self.environShowHideWdg.addCallback(self._doShowHide, callNow = False)
        self.model.cameraConnState.addCallback(self._updCameraConnState, callNow = True)
        self.model.fwConnState.addCallback(self._updFWConnState, callNow = True)
        self.model.ccdTemp.addCallback(self._updCCDTemp, callNow = True)
        self.model.ccdSetTemp.addCallback(self._updCCDSetTemp, callNow = True)
        self.model.ccdTempLimits.addCallback(self._updCCDTempLimits, callNow = True)
        self.model.gpsSynced.addCallback(self._updGPSSynced, callNow = True)
        self.model.ntpStatus.addCallback(self._updNTPStatus, callNow = True)
        self.model.fwStatus.addCallback(self._updFWStatus, callNow = True)
        self._doShowHide()

    def _doShowHide(self, wdg=None):
        showTemps = self.environShowHideWdg.getBool()
        argDict = {self.EnvironCat: showTemps}
        self.gridder.showHideWdg (**argDict)
    
    def _updCameraConnState(self, connState, isCurrent, keyVar=None):
        stateStr, severity = parseConnState(connState)
        self.cameraConnStateWdg.set(stateStr, isCurrent=isCurrent, severity=severity)
        self.environStateSet.setState(StCameraConn, severity=severity, stateStr=stateStr)
    
    def _updFWConnState(self, connState, isCurrent, keyVar=None):
        stateStr, severity = parseConnState(connState)
        self.fwConnStateWdg.set(stateStr, isCurrent=isCurrent, severity=severity)
        self.environStateSet.setState(StFWConn, severity=severity, stateStr=stateStr)
    
    def _updCCDTemp(self, dataList, isCurrent, keyVar=None):
        #print "_updCCDTemp(dataList=%s, isCurrent=%s)" % (dataList, isCurrent)
        ccdTemp, tempStatus = dataList[0:2]
        if ccdTemp is None:
            stateStr = "?"
        else:
            stateStr = "%0.1f" % (ccdTemp,)
        if tempStatus is not None:
            tempStatus = tempStatus.lower()
        dispStr, severity = self.ccdTempStateDict.get(tempStatus, (tempStatus, RO.Constants.sevWarning))
        if dispStr is not None:
            stateStr = "%s %s" % (stateStr, dispStr)
        self.ccdTempWdg.set(stateStr, isCurrent=isCurrent, severity=severity)
        if not isCurrent or severity != RO.Constants.sevNormal:
            self.environStateSet.setState(StCCDTemp, severity = severity, stateStr=stateStr)
        else:
            self.environStateSet.clearState(StCCDTemp)
    
    def _updCCDSetTemp(self, dataList, isCurrent, keyVar=None):
        #print "_updCCDSetTemp(dataList=%s, isCurrent=%s)" % (dataList, isCurrent)
        ccdSetTemp, tempStatus = dataList[0:2]
        if ccdSetTemp is None:
            stateStr = "?"
        else:
            stateStr = "%0.1f" % (ccdSetTemp,)
        if tempStatus is not None:
            tempStatus = tempStatus.lower()
        dispStr, severity = self.ccdTempStateDict.get(tempStatus, (tempStatus, RO.Constants.sevWarning))
        if dispStr is not None:
            stateStr = "%s %s" % (stateStr, dispStr)
        self.ccdSetTempWdg.set(stateStr, isCurrent=isCurrent, severity=severity)
        if not isCurrent or severity != RO.Constants.sevNormal:
            self.environStateSet.setState(StCCDSetTemp, severity = severity, stateStr=stateStr)
        else:
            self.environStateSet.clearState(StCCDSetTemp)
    
    def _updCCDTempLimits(self, ccdTempLimits, isCurrent, keyVar=None):
        #print "_updCCDTempLimits(ccdTempLimits=%s, isCurrent=%s)" % (ccdTempLimits, isCurrent)
        for ind, wdg in enumerate(self.ccdTempLimitsWdgSet):
            tempLimit = ccdTempLimits[ind]
            if tempLimit is None:
                wdg.grid_remove()
            else:
                tempLimit = abs(tempLimit)
                if ind % 2 == 0: # limits 0 and 2 are negative
                    tempLimit = -tempLimit
                wdg.grid()
                wdg.set(tempLimit)
    
    def _updFWStatus(self, fwStatus, isCurrent, keyVar=None):
        #print "_updFWStatus(fwStatus=%s, isCurrent=%s)" % (fwStatus, isCurrent)
        statusWord = fwStatus[2]
        motorSev = RO.Constants.sevWarning
        if statusWord is None:
            motorStr = "?"
        else:
            if statusWord & 0x0201 != 0:
                motorStr = "Not Homed"
            elif statusWord & 0x004 != 0:
                motorStr = "Disabled"
            elif statusWord & 0x008 != 0:
                motorStr = "Controller Error"
            elif statusWord & 0x0400 != 0:
                motorStr = "Is Homing"
            elif statusWord & 0x1002 != 0:
                motorStr = "Is Moving"
            else:
                motorStr = "OK"
                motorSev = RO.Constants.sevNormal
        self.fwHomedWdg.set(motorStr, isCurrent=isCurrent, severity=motorSev)
        self.environStateSet.setState(StFWMotor, severity=motorSev, stateStr=motorStr)
        
    def _updGPSSynced(self, dataList, isCurrent, keyVar=None):
        severity, stateStr = self.gpsSyncedDict[dataList[0]]
        self.gpsSyncedWdg.set(stateStr, isCurrent=isCurrent, severity=severity)
        if severity == RO.Constants.sevNormal and isCurrent:
            self.environStateSet.clearState(StGPSSynced)
        else:
            self.environStateSet.setState(StGPSSynced, severity=severity, stateStr=stateStr)
    
    def _updNTPStatus(self, dataList, isCurrent, keyVar=None):
        isRunning, server, stratum = dataList[0:3]
        severity = RO.Constants.sevNormal
        if isRunning is False:
            severity = RO.Constants.sevError
        elif (isRunning is None) or (server == "?") or (stratum is None):
            severity = RO.Constants.sevWarning
        isRunningStr = self.ntpRunningDict[isRunning]
        if server is None:
            serverStr = "?"
        else:
            serverStr = server.split(".")[0]
        if stratum is not None:
            stratumStr = stratum
        else:
            stratumStr = "?"
        self.ntpStatusWdgSet[0].set(isRunningStr, isCurrent=isCurrent, severity=severity)
        self.ntpStatusWdgSet[1].set(serverStr, isCurrent=isCurrent, severity=severity)
        self.ntpStatusWdgSet[2].set(stratumStr, isCurrent=isCurrent, severity=severity)
        stateStr = "%s %s %s" % (isRunningStr, serverStr, stratumStr)
        if severity == RO.Constants.sevNormal and isCurrent:
            self.environStateSet.clearState(StNTPStatus)
        else:
            self.environStateSet.setState(StNTPStatus, severity=severity, stateStr=stateStr)

    def _updEnvironStateSet(self, *args):
        """Environmental state set updated"""
        state = self.environStateSet.getFirstState()
        #print "_updEnvironStateSet; first state=", state
        if not state or state.severity == RO.Constants.sevNormal:
            self.environSummaryWdg.set("OK", severity=RO.Constants.sevNormal)
        else:
             summaryStr = "%s: %s" % (state.name, state.stateStr)
             self.environSummaryWdg.set(summaryStr, severity=state.severity)

def parseConnState(connState):
    """Parse a connction state (stateStr, descrStr)
    
    Return: stateStr (suitably modified), severity
    """
    stateStr = connState[0]
    if not stateStr:
        stateStr = "?"
    isConnected = stateStr.lower() == "connected"
    if "fail" in stateStr.lower():
        stateStr = "Connection " + stateStr
    if isConnected:
        severity = RO.Constants.sevNormal
    else:
        severity = RO.Constants.sevWarning
    return stateStr, severity


if __name__ == '__main__':
    from . import TestData
    root = TestData.tuiModel.tkRoot
        
    testFrame = StatusConfigInputWdg(root)
    testFrame.pack()
    
    bf = tkinter.Frame(root)
    tkinter.Button(bf, text='Demo', command=TestData.animate).pack(side='left')
    bf.pack()

    TestData.start()
    
    root.mainloop()
