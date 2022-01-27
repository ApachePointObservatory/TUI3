#!/usr/bin/env python
"""Displays calibration and guide offsets

History:
2011-02-16 ROwen
2011-02-18 ROwen    Removed the rotator axis since we never set rotator calib or guide offsets on the 3.5m.
"""
import tkinter
import RO.CoordSys
import RO.StringUtil
import RO.Wdg
import TUI.TCC.TCCModel

_HelpURL = "Telescope/StatusWin.html#Offsets"
_DataWidth = 10

class AxisOffsetWdg (tkinter.Frame):
    def __init__ (self, master=None, **kargs):
        """creates a new offset display frame

        Inputs:
        - master        master Tk widget -- typically a frame or window
        """
        tkinter.Frame.__init__(self, master, **kargs)
        self.tccModel = TUI.TCC.TCCModel.getModel()
        self.isArc = False
        gr = RO.Wdg.Gridder(self, sticky="w")

        gr.gridWdg("Calib Off")
        gr.startNewCol()
        
        # just display az and alt offsets because there's no way to measure
        # rotator correction so it's never set
        MountLabels = ("Az", "Alt")

        # calib offset
        self.calibOffWdgSet = [
            RO.Wdg.DMSLabel(
                master = self,
                precision = 1,
                width = _DataWidth,
                helpText = "Calibration offset",
                helpURL = _HelpURL,
            )
            for ii in range(len(MountLabels))
        ]
        for ii, label in enumerate(MountLabels):
            wdgSet = gr.gridWdg (
                label = label,
                dataWdg = self.calibOffWdgSet[ii],
                units = RO.StringUtil.DMSStr,
            )
            wdgSet.labelWdg.configure(width=4, anchor="e")

        gr.startNewCol()
        gr.gridWdg(" Guide Off")
        gr.startNewCol()

        # guide offset
        self.guideOffWdgSet = [
            RO.Wdg.DMSLabel(
                master = self,
                precision = 1,
                width = _DataWidth,
                helpText = "Guide offset",
                helpURL = _HelpURL,
            )
            for ii in range(len(MountLabels))
        ]
        for ii, label in enumerate(MountLabels):
            wdgSet = gr.gridWdg (
                label = label,
                dataWdg = self.guideOffWdgSet[ii],
                units = RO.StringUtil.DMSStr,
            )
            wdgSet.labelWdg.configure(width=4, anchor="e")
        
        # allow the last+1 column to grow to fill the available space
        self.columnconfigure(gr.getMaxNextCol(), weight=1)

        self.tccModel.calibOff.addROWdgSet(self.calibOffWdgSet)
        self.tccModel.guideOff.addROWdgSet(self.guideOffWdgSet)
        
if __name__ == "__main__":
    from . import TestData

    tuiModel = TestData.tuiModel

    testFrame = OffsetWdg(tuiModel.tkRoot)
    testFrame.pack()

    dataList = (
        "ObjSys=ICRS, 0",
        "ObjInstAng=30.0, 0.0, 4494436859.66000",
        "ObjArcOff=-0.012, 0.0, 4494436859.66000, -0.0234, 0.000000, 4494436859.66000",
        "Boresight=0.0054, 0.0, 4494436859.66000, -0.0078, 0.000000, 4494436859.66000",
        "CalibOff=-0.001, 0.0, 4494436859.66000, 0.003, 0.000000, 4494436859.66000, -0.017, 0.000000, 4494436859.66000",
        "GuideOff=-0.003, 0.0, 4494436859.66000, -0.002, 0.000000, 4494436859.66000, 0.023, 0.000000, 4494436859.66000",
    )

    TestData.testDispatcher.dispatch(dataList)

    tuiModel.tkRoot.mainloop()
