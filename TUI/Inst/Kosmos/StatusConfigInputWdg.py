#!/usr/bin/env python
"""Configuration input panel for Kosmos.

History:
2019-12-20 CS       Created
"""
import tkinter
import RO.Constants
import RO.MathUtil
import RO.Wdg
import RO.KeyVariable
import TUI.TUIModel
from . import KosmosModel

_MaxDataWidth = 5

class StatusConfigInputWdg (RO.Wdg.InputContFrame):
    InstName = "Kosmos"
    HelpPrefix = 'Instruments/%s/%sWin.html#' % (InstName, InstName)

    # category names
    CCDCat = "ccd"
    ConfigCat = RO.Wdg.StatusConfigGridder.ConfigCat

    def __init__(self,
        master,
        stateTracker,
    **kargs):
        """Create a new widget to show status for and configure Kosmos

        Inputs:
        - master: parent widget
        - stateTracker: an RO.Wdg.StateTracker
        """
        RO.Wdg.InputContFrame.__init__(self, master=master, stateTracker=stateTracker, **kargs)
        self.model = KosmosModel.getModel()
        self.tuiModel = TUI.TUIModel.getModel()

        # set while updating user ccd binning or user window default,
        # to prevent storing new unbinned values for ccd window.
        self._freezeCCDUBWindow = False

        gr = RO.Wdg.StatusConfigGridder(
            master = self,
            sticky = "e",
        )
        self.gridder = gr

        shutterCurrWdg = RO.Wdg.StrLabel(
            master = self,
            helpText = "current state of the shutter",
            # helpURL = self.HelpPrefix + "Shutter",
            anchor = "w",
        )
        self.model.shutter.addROWdg(shutterCurrWdg)
        gr.gridWdg ("Shutter", shutterCurrWdg, sticky="ew", colSpan=3)

        self.disperserNameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.disperserNameUserWdg = RO.Wdg.OptionMenu(
            self,
            items = [],
            noneDisplay = "?",
            helpText = "requested filter",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "disperser",
            dataWdg = self.disperserNameCurrWdg,
            units = False,
            cfgWdg = self.disperserNameUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.slitNameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.slitNameUserWdg = RO.Wdg.OptionMenu(
            self,
            items = [],
            noneDisplay = "?",
            helpText = "requested filter",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "slit",
            dataWdg = self.slitNameCurrWdg,
            units = False,
            cfgWdg = self.slitNameUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )


        self.filter1NameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.filter1NameUserWdg = RO.Wdg.OptionMenu(
            self,
            items = [],
            noneDisplay = "?",
            helpText = "requested filter",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "Filter1",
            dataWdg = self.filter1NameCurrWdg,
            units = False,
            cfgWdg = self.filter1NameUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.filter2NameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.filter2NameUserWdg = RO.Wdg.OptionMenu(
            self,
            items = [],
            noneDisplay = "?",
            helpText = "requested filter",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "Filter2",
            dataWdg = self.filter2NameCurrWdg,
            units = False,
            cfgWdg = self.filter2NameUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.calstageNameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.calstageNameUserWdg = RO.Wdg.OptionMenu(
            self,
            items = [],
            noneDisplay = "?",
            helpText = "requested filter",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "calibration stage",
            dataWdg = self.calstageNameCurrWdg,
            units = False,
            cfgWdg = self.calstageNameUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )


        self.rowBinNameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.rowBinNameUserWdg = RO.Wdg.OptionMenu(
            self,
            items = ["1", "2"],
            noneDisplay = "?",
            helpText = "requested row bin factor",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "row bin",
            dataWdg = self.rowBinNameCurrWdg,
            units = False,
            cfgWdg = self.rowBinNameUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.colBinNameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "column bin factor",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.colBinNameUserWdg = RO.Wdg.OptionMenu(
            self,
            items = ["1", "2"],
            noneDisplay = "?",
            helpText = "requested column bin",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "column bin",
            dataWdg = self.colBinNameCurrWdg,
            units = False,
            cfgWdg = self.colBinNameUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        # lamps
        self.neonCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "internal cal lamp",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.neonUserWdg = RO.Wdg.OptionMenu(
            self,
            items = ["on", "off"],
            noneDisplay = "?",
            helpText = "internal cal lamp",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "neon lamp",
            dataWdg = self.neonCurrWdg,
            units = False,
            cfgWdg = self.neonUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.kryptonCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "internal cal lamp",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.kryptonUserWdg = RO.Wdg.OptionMenu(
            self,
            items = ["on", "off"],
            noneDisplay = "?",
            helpText = "internal cal lamp",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "krypton lamp",
            dataWdg = self.kryptonCurrWdg,
            units = False,
            cfgWdg = self.kryptonUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.argonCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "internal cal lamp",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.argonUserWdg = RO.Wdg.OptionMenu(
            self,
            items = ["on", "off"],
            noneDisplay = "?",
            helpText = "internal cal lamp",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "argon lamp",
            dataWdg = self.argonCurrWdg,
            units = False,
            cfgWdg = self.argonUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.quartzCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "internal cal lamp",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )
        self.quartzUserWdg = RO.Wdg.OptionMenu(
            self,
            items = ["on", "off"],
            noneDisplay = "?",
            helpText = "internal cal lamp",
            # helpURL = self.HelpPrefix + "Filter",
            defMenu = "Current",
            autoIsCurrent = True,
        )
        gr.gridWdg (
            label = "quartz lamp",
            dataWdg = self.quartzCurrWdg,
            units = False,
            cfgWdg = self.quartzUserWdg,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.gfocusNameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )

        gr.gridWdg (
            label = "kcamera focus",
            dataWdg = self.gfocusNameCurrWdg,
            units = False,
            cfgWdg = None,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.camfocNameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )

        gr.gridWdg (
            label = "spectrograph focus",
            dataWdg = self.camfocNameCurrWdg,
            units = False,
            cfgWdg = None,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )


        self.colfocNameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )

        gr.gridWdg (
            label = "collimator focus",
            dataWdg = self.colfocNameCurrWdg,
            units = False,
            cfgWdg = None,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        self.detectorTemp1NameCurrWdg = RO.Wdg.StrLabel(
            master = self,
            width = 9, # room for "Not Homed"
            helpText = "current filter or status",
            # helpURL = self.HelpPrefix + "Filter",
            anchor = "w",
        )

        gr.gridWdg (
            label = "CCD Temp",
            dataWdg = self.detectorTemp1NameCurrWdg,
            units = False,
            cfgWdg = None,
            sticky = "ew",
            cfgSticky = "w",
            colSpan = 3,
        )

        # set up format functions for the filter menu
        # this allows us to return index values instead of names
        class indFormat(object):
            def __init__(self, indFunc, offset=1):
                self.indFunc = indFunc
                self.offset = offset
            def __call__(self, inputCont):
                valueList = inputCont.getValueList()
                if not valueList:
                    return ''
                selValue = valueList[0]
                if not selValue:
                    return ''
                name = inputCont.getName()
                return "%s=%d" % (name, self.indFunc(selValue) + self.offset)

        # def myCB(*args, **kwargs):
        #     import pdb; pdb.set_trace()

        # add callbacks that access widgets
        self.model.filter1Names.addCallback(self.filter1NameUserWdg.setItems)
        self.model.filter2Names.addCallback(self.filter2NameUserWdg.setItems)
        self.model.disperserNames.addCallback(self.disperserNameUserWdg.setItems)
        self.model.slitNames.addCallback(self.slitNameUserWdg.setItems)
        self.model.calstageNames.addCallback(self.calstageNameUserWdg.setItems)
        # self.model.calstageNames.addCallback(myCB)


        self.model.filter1.addIndexedCallback(self._updFilter1Name)
        self.model.filter2.addIndexedCallback(self._updFilter2Name)
        self.model.disperser.addIndexedCallback(self._updDisperserName)
        self.model.slit.addIndexedCallback(self._updSlitName)
        self.model.gfocusPos.addIndexedCallback(self._updGfocusName)
        self.model.gfocusState.addIndexedCallback(self._updGfocusState)
        self.model.calstagePos.addIndexedCallback(self._updCalstageName)
        self.model.calstageState.addIndexedCallback(self._updCalstageState)
        self.model.camfoc.addIndexedCallback(self._updCamfocState)
        self.model.colfoc.addIndexedCallback(self._updColfocState)
        self.model.detectorTemp1.addIndexedCallback(self._updDetectorTemp1State)
        self.model.rowBin.addIndexedCallback(self._updRowBinName)
        self.model.colBin.addIndexedCallback(self._updColBinName)
        self.model.quartz.addIndexedCallback(self._updQuartzName)
        self.model.neon.addIndexedCallback(self._updNeonName)
        self.model.argon.addIndexedCallback(self._updArgonName)
        self.model.krypton.addIndexedCallback(self._updKryptonName)


        # set up the input container set; this is what formats the commands
        # and allows saving and recalling commands
        self.inputCont = RO.InputCont.ContList (
            conts = [
                RO.InputCont.WdgCont (
                    name = "filter1",
                    wdgs = self.filter1NameUserWdg,
                    formatFunc = indFormat(self.filter1NameUserWdg.index),
                ),
                RO.InputCont.WdgCont (
                    name = "filter2",
                    wdgs = self.filter2NameUserWdg,
                    formatFunc = indFormat(self.filter2NameUserWdg.index),
                ),
                RO.InputCont.WdgCont (
                    name = "disperser",
                    wdgs = self.disperserNameUserWdg,
                    formatFunc = indFormat(self.disperserNameUserWdg.index),
                ),
                RO.InputCont.WdgCont (
                    name = "slit",
                    wdgs = self.slitNameUserWdg,
                    formatFunc = indFormat(self.slitNameUserWdg.index),
                ),
                RO.InputCont.WdgCont (
                    name = "calstage",
                    wdgs = self.calstageNameUserWdg,
                    formatFunc = RO.InputCont.BasicFmt(nameSep="="),
                ),
                RO.InputCont.WdgCont (
                    name = "rowBin",
                    wdgs = self.rowBinNameUserWdg,
                    formatFunc = RO.InputCont.BasicFmt(nameSep="="),
                ),
                RO.InputCont.WdgCont (
                    name = "colBin",
                    wdgs = self.colBinNameUserWdg,
                    formatFunc = RO.InputCont.BasicFmt(nameSep="="),
                ),
                RO.InputCont.WdgCont (
                    name = "neon",
                    wdgs = self.neonUserWdg,
                    formatFunc = RO.InputCont.BasicFmt(nameSep="="),
                ),
                RO.InputCont.WdgCont (
                    name = "krypton",
                    wdgs = self.kryptonUserWdg,
                    formatFunc = RO.InputCont.BasicFmt(nameSep="="),
                ),
                RO.InputCont.WdgCont (
                    name = "argon",
                    wdgs = self.argonUserWdg,
                    formatFunc = RO.InputCont.BasicFmt(nameSep="="),
                ),
                RO.InputCont.WdgCont (
                    name = "quartz",
                    wdgs = self.quartzUserWdg,
                    formatFunc = RO.InputCont.BasicFmt(nameSep="="),
                ),
            ],
        )

        self.configWdg = RO.Wdg.InputContPresetsWdg(
            master = self,
            sysName = "%sConfig" % (self.InstName,),
            userPresetsDict = self.tuiModel.userPresetsDict,
            stdPresets = dict(),
            inputCont = self.inputCont,
            helpText = "use and manage named presets",
            # helpURL = self.HelpPrefix + "Presets",
        )
        self.gridder.gridWdg(
            "Presets",
            cfgWdg = self.configWdg,
            colSpan = 2,
        )

        self.gridder.allGridded()

        def repaint(evt):
            self.restoreDefault()
        self.bind("<Map>", repaint)


    def _updFilter1Name(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        filter1, isCurrent = self.model.filter1.getInd(0)
        try:
            filterIndex = int(filter1) - 1
            filterName = self.filter1NameUserWdg._items[filterIndex]
            self.filter1NameCurrWdg.set(filterName, severity=RO.Constants.sevNormal)
            self.filter1NameUserWdg.setDefault(filterName, doCheck=False)
        except:
            self.filter1NameCurrWdg.set(filter1, severity=RO.Constants.sevWarning) # probably something like moving

    def _updFilter2Name(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        filter2, isCurrent = self.model.filter2.getInd(0)
        try:
            filterIndex = int(filter2) - 1
            filterName = self.filter2NameUserWdg._items[filterIndex]
            self.filter2NameCurrWdg.set(filterName, severity=RO.Constants.sevNormal)
            self.filter2NameUserWdg.setDefault(filterName, doCheck=False)
        except:
            self.filter2NameCurrWdg.set(filter2, severity=RO.Constants.sevWarning) # probably something like moving

    def _updDisperserName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        disperser, isCurrent = self.model.disperser.getInd(0)
        try:
            filterIndex = int(disperser) - 1
            filterName = self.disperserNameUserWdg._items[filterIndex]
            self.disperserNameCurrWdg.set(filterName, severity=RO.Constants.sevNormal)
            self.disperserNameUserWdg.setDefault(filterName, doCheck=False)
        except:
            self.disperserNameCurrWdg.set(disperser, severity=RO.Constants.sevWarning) # probably something like moving

    def _updSlitName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        slit, isCurrent = self.model.slit.getInd(0)
        try:
            filterIndex = int(slit) - 1
            filterName = self.slitNameUserWdg._items[filterIndex]
            self.slitNameCurrWdg.set(filterName, severity=RO.Constants.sevNormal)
            self.slitNameUserWdg.setDefault(filterName, doCheck=False)
        except:
            self.slitNameCurrWdg.set(slit, severity=RO.Constants.sevWarning) # probably something like moving

    def _updCalstageState(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        calstageState, isCurrent = self.model.calstageState.getInd(0)
        if calstageState is None:
            return
        if calstageState == "Moving" or "hom" in calstageState.lower():
            self.calstageNameCurrWdg.set(calstageState, severity=RO.Constants.sevWarning)

    def _updGfocusState(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        gfocusState, isCurrent = self.model.gfocusState.getInd(0)
        if gfocusState is None:
            return
        if gfocusState == "Moving" or "hom" in gfocusState.lower():
            self.gfocusNameCurrWdg.set(gfocusState, severity=RO.Constants.sevWarning)

    def _updCalstageName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        calstage, isCurrent = self.model.calstagePos.getInd(0)
        if calstage is None:
            stagePos = "?"
        elif int(calstage) > 5000:
            stagePos = "in"
            self.calstageNameCurrWdg.set(calstage, severity=RO.Constants.sevCritical)
        else:
            stagePos = "out"
            self.calstageNameCurrWdg.set(calstage, severity=RO.Constants.sevNormal)

        self.calstageNameUserWdg.setDefault(stagePos, doCheck=False)

    def _updGfocusName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        gfocus, isCurrent = self.model.gfocusPos.getInd(0)
        self.gfocusNameCurrWdg.set(gfocus, severity=RO.Constants.sevNormal)

    def _updCamfocState(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        camfoc, isCurrent = self.model.camfoc.getInd(0)
        self.camfocNameCurrWdg.set(camfoc)

    def _updColfocState(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        colfoc, isCurrent = self.model.colfoc.getInd(0)
        self.colfocNameCurrWdg.set(colfoc)

    def _updDetectorTemp1State(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        detectorTemp1, isCurrent = self.model.detectorTemp1.getInd(0)
        self.detectorTemp1NameCurrWdg.set(detectorTemp1)

    def _updRowBinName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        rowBin, isCurrent = self.model.rowBin.getInd(0)
        if rowBin is None:
            rowBin = "?"
        else:
            rowBin = str(int(float(rowBin)))
        self.rowBinNameCurrWdg.set(rowBin, severity=RO.Constants.sevNormal)
        self.rowBinNameUserWdg.setDefault(rowBin, doCheck=False)

    def _updColBinName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        colBin, isCurrent = self.model.colBin.getInd(0)
        if colBin is None:
            colBin = "?"
        else:
            colBin = str(int(float(colBin)))
        self.colBinNameCurrWdg.set(colBin, severity=RO.Constants.sevNormal)
        self.colBinNameUserWdg.setDefault(colBin, doCheck=False)

    def _updNeonName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        neon, isCurrent = self.model.neon.getInd(0)
        if neon is None:
            neon = "?"
        else:
            neon = str(neon)

        if neon.__eq__("off"):
            self.neonCurrWdg.set(neon, severity=RO.Constants.sevNormal)
        elif neon.__eq__("on"):
            self.neonCurrWdg.set(neon, severity=RO.Constants.sevCritical)
        self.neonUserWdg.setDefault(neon, doCheck=False)

    def _updKryptonName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        krypton, isCurrent = self.model.krypton.getInd(0)
        if krypton is None:
            krypton = "?"
        else:
            krypton = str(krypton)

        if krypton.__eq__("off"):
            self.kryptonCurrWdg.set(krypton, severity=RO.Constants.sevNormal)
        elif krypton.__eq__("on"):
            self.kryptonCurrWdg.set(krypton, severity=RO.Constants.sevCritical)

        self.kryptonUserWdg.setDefault(krypton, doCheck=False)

    def _updQuartzName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        quartz, isCurrent = self.model.quartz.getInd(0)
        if quartz is None:
            quartz = "?"
        else:
            quartz = str(quartz)

        if quartz.__eq__("off"):            
            self.quartzCurrWdg.set(quartz, severity=RO.Constants.sevNormal)
        elif quartz.__eq__("on"):
            self.quartzCurrWdg.set(quartz, severity=RO.Constants.sevCritical)

        self.quartzUserWdg.setDefault(quartz, doCheck=False)


    def _updArgonName(self, *args, **kargs):
        """Show current filter name, if stopped at a known position, else state
        """
        argon, isCurrent = self.model.argon.getInd(0)
        if argon is None:
            argon = "?"
        else:
            argon = str(argon)
        
        if argon.__eq__("off"):
            self.argonCurrWdg.set(argon, severity=RO.Constants.sevNormal)
        elif argon.__eq__("on"):
            self.argonCurrWdg.set(argon, severity=RO.Constants.sevCritical)      
        self.argonCurrWdg.set(argon, severity=RO.Constants.sevNormal)
        self.argonUserWdg.setDefault(argon, doCheck=False)

    def _getUserBinFac(self):
        """Return the current user-set bin factor in x and y.
        """
        return [wdg.getNum() for wdg in self.ccdBinUserWdgSet]

    def _getUserCCDWindow(self):
        """Return the current user-set ccd window (binned) in x and y.
        """
        return [wdg.getNum() for wdg in self.ccdWindowUserWdgSet]


if __name__ == "__main__":
    from . import TestData
    root = TestData.tuiModel.tkRoot
    stateTracker = RO.Wdg.StateTracker(logFunc=TestData.tuiModel.logFunc)

    testFrame = StatusConfigInputWdg(root, stateTracker=stateTracker)
    testFrame.pack()

    TestData.start()

    testFrame.restoreDefault()

    def printCmds():
        print("strList =", testFrame.getStringList())

    bf = tkinter.Frame(root)
    cfgWdg = RO.Wdg.Checkbutton(bf, text="Config", defValue=True)
    cfgWdg.pack(side="left")
    tkinter.Button(bf, text="Cmds", command=printCmds).pack(side="left")
    tkinter.Button(bf, text="Current", command=testFrame.restoreDefault).pack(side="left")
    tkinter.Button(bf, text="Demo", command=TestData.animate).pack(side="left")
    bf.pack()

    testFrame.gridder.addShowHideControl(testFrame.ConfigCat, cfgWdg)

    root.mainloop()
