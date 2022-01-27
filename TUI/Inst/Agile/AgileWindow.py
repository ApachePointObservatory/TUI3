#!/usr/bin/env python
"""Status/config and exposure windows for Agile.

History:
2008-10-24 ROwen
2009-01-28 ROwen    Put all Agile controls in one window.
                    Added gain, read rate and extSync controls.
2009-02-05 ROwen    Bug fix: amplifier gain option medium corrected to med.
2009-02-25 ROwen    Added display of camera connection state.
                    Modified getExpCmdStr to raise an exception if the camera is not connected.
2009-06-24 ROwen    Added filter widget.
2009-07-02 ROwen    Modified for updated TestData.
2009-07-10 ROwen    Modified for updated TestData.
2010-09-20 ROwen    Modified Abort and Stop to command agile directly instead of going through agileExpose;
                    this works around a bug in agileExpose whereby it goes catatonic when it receives
                    stop or abort.
"""
import RO.Alg
import TUI.Inst.ExposeWdg
from . import StatusConfigInputWdg
from . import AgileModel
from . import AgileFilterWdg

InstName = StatusConfigInputWdg.StatusConfigInputWdg.InstName
WindowName = "Inst.%s" % (InstName,)

def addWindow(tlSet):
    tlSet.createToplevel (
        name = WindowName,
        defGeom = "+676+280",
        resizable = False,
        wdgFunc = AgileExposeWindow,
        visible = False,
        doSaveState = True,
    )

class AgileExposeWindow(TUI.Inst.ExposeWdg.ExposeWdg):
    HelpPrefix = 'Instruments/%sWin.html#' % (InstName,)
    def __init__(self, master):
        TUI.Inst.ExposeWdg.ExposeWdg.__init__(self, master, instName=InstName)
        
        gr = self.expInputWdg.gridder
        
        self.gainWdg = RO.Wdg.OptionMenu(
            master = self.expInputWdg,
            items = ("Low", "Med", "High"),
            defValue = "Med",
            defMenu = "Default",
            helpText = "CCD amplifier gain",
            helpURL = self.HelpPrefix + "Gain",
        )
        gr.gridWdg("Gain", self.gainWdg, colSpan=2)
        
        self.readRateWdg = RO.Wdg.OptionMenu(
            master = self.expInputWdg,
            items = ("Slow", "Fast"),
            defValue = "Fast",
            defMenu = "Default",
            helpText = "CCD readout rate",
            helpURL = self.HelpPrefix + "ReadRate",
        )
        gr.gridWdg("Read Rate", self.readRateWdg, colSpan=2)
        
        self.filterWdg = AgileFilterWdg.AgileFilterWdg(
            master = self.expInputWdg,
            statusBar = self.statusBar,
            gridder = gr,
            helpPrefix = self.HelpPrefix,
        )
#        gr.gridWdg(False, self.filterWdg, colSpan=5)
        
        self.statusConfigWdg = StatusConfigInputWdg.StatusConfigInputWdg(
            master = self.expInputWdg,
        )
        gr.gridWdg(False, self.statusConfigWdg, colSpan=10, sticky="w")
        self.configWdg.pack_forget()
        self._stateTracker.trackCheckbutton("showEnviron", self.statusConfigWdg.environShowHideWdg)
        
        self.connSensitiveWdgSet = (self.startWdg, self.stopWdg, self.abortWdg)
        self.agileModel = AgileModel.getModel()

    def getExpCmdStr(self):
        """Get exposure command string"""
        connState, isCurrent = self.agileModel.cameraConnState.getInd(0)
        if connState and connState.lower() != "connected":
            raise RuntimeError("Wait for camera to be connected")
        cmdStr = self.expInputWdg.getString()
        if cmdStr is None:
            return
        cmdStr += " gain=%s readrate=%s" % (self.gainWdg.getString().lower(), self.readRateWdg.getString().lower())
        return cmdStr
    
    def doStop(self, wdg):
        """Handles the Stop and Abort buttons (and Pause and Resume if agile supported those).
        
        This method overrides the default behavior by sending the command directly to agile
        (instead of agileExpose) because sending abort or stop to agileExpose causes it to go catatonic.
        Fortunately agileExpose reacts very well to agile stopping the sequence.
        
        Inputs:
        - wdg   the button that was pressed
        """
        cmdVerb = wdg["text"].split()[0].lower()
        
        try:
            nextState = TUI.Inst.ExposeWdg._StopCmdStateDict[cmdVerb]
        except LookupError:
            raise ValueError("ExposeWdg.doStop: unknown command %r" % (cmdVerb,))

        cmdStr = "expose %s" % (cmdVerb,)
        self.doCmd(cmdStr, nextState, actor="agile")
        

if __name__ == "__main__":
    from . import TestData

    tlSet = TestData.tuiModel.tlSet

    addWindow(tlSet)
    tlSet.makeVisible(WindowName)
    
    TestData.start()
    
    TestData.tuiModel.tkRoot.mainloop()
