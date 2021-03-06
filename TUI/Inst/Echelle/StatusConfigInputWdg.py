#!/usr/bin/env python
"""Configuration input panel for the Echelle.

Special logic:
- If the cal mirror is removed, both lamps are turned off
  (but they can be turned on again).
- If one lamp is turned on, then the other lamp is turned off
  (and there is no override).
  
History:
2003-12-09 ROwen
2003-12-19 ROwen    Modified to use RO.Wdg.BoolLabel for status.
2004-05-18 ROwen    Removed constant _MaxDataWidth; it wasn't used.
2004-09-23 ROwen    Modified to allow callNow as the default for keyVars.
2005-01-04 ROwen    Modified to use autoIsCurrent for input widgets.
2005-05-12 ROwen    Modified for new Echelle ICC.
2005-06-10 ROwen    Added display of current shutter state.
2006-04-27 ROwen    Removed use of ignored clearMenu and defMenu in StatusConfigGridder.
2008-02-11 ROwen    Modified to be compatible with the new TUI.Inst.StatusConfigWdg.
2014-03-14 ROwen    Added a Presets widget
"""
import tkinter
import RO.MathUtil
import RO.Wdg
import RO.KeyVariable
import TUI.TUIModel
from . import EchelleModel

class StatusConfigInputWdg (RO.Wdg.InputContFrame):
    InstName = "Echelle"
    HelpPrefix = 'Instruments/%s/%sWin.html#' % (InstName, InstName)
    ConfigCat = RO.Wdg.StatusConfigGridder.ConfigCat
    _LampPrefix = "lamp" # full lamp name has index appended, e.g. "lamp0".
    
    def __init__(self,
        master,
        stateTracker,
    **kargs):
        """Create a new widget to show status for and configure the Dual Imaging Spectrograph

        Inputs:
        - master: parent widget
        - stateTracker: an RO.Wdg.StateTracker
        """
        RO.Wdg.InputContFrame.__init__(self, master=master, stateTracker=stateTracker, **kargs)
        self.model = EchelleModel.getModel()
        self.tuiModel = TUI.TUIModel.getModel()
        
        mirLens = [len(name) for name in self.model.mirStatesConst]
        mirMaxNameLen = max(mirLens)

        self.gridder = RO.Wdg.StatusConfigGridder(
            master = self,
            sticky = "",
        )

        self.shutterCurrWdg = RO.Wdg.StrLabel(
            master = self,
            anchor = "c",
            helpText = "Current shutter state",
            helpURL = self.HelpPrefix + "shutter",
        )
        self.model.shutter.addROWdg(self.shutterCurrWdg)
        
        self.gridder.gridWdg (
            label = "Shutter",
            dataWdg = self.shutterCurrWdg,
            units = False,
            cfgWdg = None,
        )
        
        self.mirrorCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = mirMaxNameLen,
            anchor = "c",
            helpText = "Current state of calibration mirror",
            helpURL = self.HelpPrefix + "mirror",
        )
        
        self.mirrorUserWdg = RO.Wdg.Checkbutton(
            master = self,
            offvalue = self.model.mirStatesConst[0].capitalize(),
            onvalue = self.model.mirStatesConst[1].capitalize(),
            helpText = "Insert calibration mirror for lamps?",
            helpURL = self.HelpPrefix + "Mirror",
            autoIsCurrent = True,
        )
        
        self.gridder.gridWdg (
            label = "Cal. Mirror",
            dataWdg = self.mirrorCurrWdg,
            units = False,
            cfgWdg = self.mirrorUserWdg,
        )
        
        self.lampNameWdgSet = []
        self.lampCurrWdgSet = []
        self.lampUserWdgSet = []
        for ii in range(self.model.numLamps):
            lampNameWdg = RO.Wdg.StrLabel(self)
                                
            lampCurrWdg = RO.Wdg.BoolLabel(
                master = self,
                trueValue = "On",
                falseValue = "Off",
                width = 3,
                anchor = "c",
                helpURL = self.HelpPrefix + "Lamps",
            )
            
            lampUserWdg = RO.Wdg.Checkbutton(
                master = self,
                onvalue = "On",
                offvalue = "Off",
                helpURL = self.HelpPrefix + "Lamps",
                autoIsCurrent = True,
            )
            self.gridder.gridWdg (
                label = lampNameWdg,
                dataWdg = lampCurrWdg,
                units = False,
                cfgWdg = lampUserWdg,
                cat = self._LampPrefix + str(ii),
            )

            self.lampNameWdgSet.append(lampNameWdg)
            self.lampCurrWdgSet.append(lampCurrWdg)
            self.lampUserWdgSet.append(lampUserWdg)

        self.calFilterCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 4, # initial value; update when filter names are known
            anchor = "c",
            helpText = "Current calibration lamp filter",
            helpURL = self.HelpPrefix + "Filter",
        )
        self.model.calFilter.addROWdg(self.calFilterCurrWdg)

        self.calFilterUserWdg = RO.Wdg.OptionMenu(
            master = self,
            items = [],
            helpText = "Desired calibration lamp filter",
            helpURL = self.HelpPrefix + "Filter",
            autoIsCurrent = True,
            defMenu = "Default",
        )
        self.model.calFilterNames.addCallback(self.setCalFilterNames)
        self.model.calFilter.addROWdg(self.calFilterUserWdg, setDefault=True)
        
        self.gridder.gridWdg (
            label = "Cal. Filter",
            dataWdg = self.calFilterCurrWdg,
            units = False,
            cfgWdg = self.calFilterUserWdg,
        )
        
        # add callbacks that need multiple widgets present
        self.model.mirror.addIndexedCallback(self.setMirrorState)
        self.model.lampNames.addCallback(self.setLampNames)
        self.model.lampStates.addCallback(self.setLampStates)
        for wdg in self.lampUserWdgSet:
            wdg.addCallback(self.doLamp, callNow=False)
        self.mirrorUserWdg.addCallback(self.doMirror, callNow=True)

        # set up the input container set; this is what formats the commands
        # and allows saving and recalling commands
        def lampValFmt(wdgVal):
            return str(int(wdgVal.lower() == "on"))

        self.inputCont = RO.InputCont.ContList (
            conts = [
                RO.InputCont.WdgCont (
                    name = "mirror",
                    wdgs = self.mirrorUserWdg,
                    formatFunc = RO.InputCont.BasicFmt(
                        valFmt=str.lower,
                    ),
                ),
                RO.InputCont.WdgCont (
                    name = "lamps",
                    wdgs = self.lampUserWdgSet,
                    formatFunc = RO.InputCont.BasicFmt(
                        valFmt=lampValFmt,
                        blankIfDisabled = False,
                    ),
                ),
                RO.InputCont.WdgCont (
                    name = "calfilter",
                    wdgs = self.calFilterUserWdg,
                    formatFunc = RO.InputCont.BasicFmt(),
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
            units = False,
            cfgWdg = self.configWdg,
        )
        
        self.gridder.allGridded()

    def doMirror(self, *args):
        """Called when the calibration mirror user control is toggled.
        
        If mirror out (instrument sees the sky, not the cal lamps)
        then turn off the cal lamps.
        """
        if self.mirrorUserWdg.getBool():
            # mirror set to cal lamp position; do nothing
            self.mirrorUserWdg.setSeverity(RO.Constants.sevWarning)
            return
        self.mirrorUserWdg.setSeverity(RO.Constants.sevNormal)

        for lampUserWdg in self.lampUserWdgSet:
            if lampUserWdg.getBool():
                lampUserWdg.setBool(False)
    
    def doLamp(self, lampWdg):
        """Called when a calibration lamp user control is toggled.
        
        If lamp control is on, then turn off the other lamps
        and set mirror to calibration position.
        """
        if not lampWdg.getBool():
            lampWdg.setSeverity(RO.Constants.sevNormal)
            return
            
        for lampUserWdg in self.lampUserWdgSet:
            if (lampUserWdg is not lampWdg):
                if lampUserWdg.getBool():
                    lampUserWdg.setBool(False, severity=RO.Constants.sevNormal)
            else:
                lampUserWdg.setSeverity(RO.Constants.sevWarning)
        self.mirrorUserWdg.setBool(True)
    
    def setCalFilterNames(self, filtNames, isCurrent, **kargs):
        nameList = [name for name in filtNames if name]
        self.calFilterUserWdg.setItems(nameList)

        if not nameList:
            return
        lenList = [len(name) for name in nameList]
        maxLen = max(lenList)
        self.calFilterCurrWdg["width"] = maxLen
    
    def setLampNames(self, lampNames, isCurrent, **kargs):
        """Update lamp name labels and hide nonexistent lamps"""
        if len(lampNames) < self.model.numLamps:
            # append extra "" strings so there are at least numLamps elements
            lampNames = tuple(lampNames) + ("",)*self.model.numLamps
        
        showHideDict = {}

        for ii in range(self.model.numLamps):
            # if name is blank, hide corresp. widgets
            # else set lamp names wdg
            lampName = lampNames[ii] or ""
            self.lampNameWdgSet[ii].set("%s Lamp" % lampName, isCurrent)
            self.lampUserWdgSet[ii].helpText = "Turn on %s cal lamp?" % (lampName,)
            self.lampCurrWdgSet[ii].helpText = "Current state of %s cal lamp" % (lampName,)
            showHideDict[self._LampPrefix + str(ii)] = bool(lampName)
            if not lampName:
                # turn off any user lamp that are hidden
                if self.lampUserWdgSet[ii].getBool():
                    self.lampUserWdgSet[ii].setBool(False)
        self.gridder.showHideWdg(**showHideDict)
    
    def setLampStates(self, lampStates, isCurrent, **kargs):
        for ii in range(self.model.numLamps):
            lampState = lampStates[ii]
            if lampState:
                sev = RO.Constants.sevWarning
            else:
                sev = RO.Constants.sevNormal
            
            self.lampCurrWdgSet[ii].set(lampState, isCurrent=isCurrent, severity=sev)
            self.lampUserWdgSet[ii].setDefault(lampState)
    
    def setMirrorState(self, mirrorState, isCurrent, **kargs):
        mirrorState = mirrorState or "" # change None to a string
        if mirrorState.lower() != self.model.mirStatesConst[0].lower():
            mirSev = RO.Constants.sevWarning
        else:
            mirSev = RO.Constants.sevNormal
        
        mirrorState = mirrorState.capitalize()
        self.mirrorCurrWdg.set(mirrorState, isCurrent, severity=mirSev)
        self.mirrorUserWdg.setDefault(mirrorState)


if __name__ == "__main__":
    from . import TestData
    root = TestData.tuiModel.tkRoot
    stateTracker = RO.Wdg.StateTracker(logFunc=TestData.tuiModel.logFunc)
        
    testFrame = StatusConfigInputWdg(master=root, stateTracker=stateTracker)
    testFrame.pack()
    
    TestData.start()
    
    testFrame.restoreDefault()

    def printCmds():
        print("Commands:")
        cmdList = testFrame.getStringList()
        for cmd in cmdList:
            print(cmd)
    
    bf = tkinter.Frame(root)
    cfgWdg = RO.Wdg.Checkbutton(bf, text="Config", defValue=True)
    cfgWdg.pack(side="left")
    tkinter.Button(bf, text="Cmds", command=printCmds).pack(side="left")
    tkinter.Button(bf, text="Current", command=testFrame.restoreDefault).pack(side="left")
    tkinter.Button(bf, text="Demo", command=TestData.animate).pack(side="left")
    bf.pack()

    testFrame.gridder.addShowHideControl(testFrame.ConfigCat, cfgWdg)

    root.mainloop()
