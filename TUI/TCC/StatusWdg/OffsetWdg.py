#!/usr/bin/env python
"""Displays arc/sky and boresight offsets.

History:
2003-04-04 ROwen
2003-04-14 ROwen    Modified to show Obj and Obj XY offset at the same time
2003-06-09 Rowen    Removed dispatcher arg.
2003-06-11 ROwen    Modified to use new tccModel objSys.
2003-06-12 ROwen    Added helpText entries.
2003-06-25 ROwen    Modified test case to handle message data as a dict
2004-02-04 ROwen    Modified _HelpURL to match minor help reorg.
2004-05-18 ROwen    Bug fix: OffsetWdg._updObjXYOff used "except a, b:" instead of "except (a, b):"
                    to catch two classes of exception, so the second would not be caught.
                    Removed unused constant _ArcLabelWidth.
2009-09-09 ROwen    Modified to use TestData.
2010-11-04 ROwen    Changed Obj Off to Object Arc Off. Tweaked help URLs.
2011-02-16 ROwen    Tightened the layout a bit.
                    Made the display expand to the right of the displayed data.
"""
import tkinter
import RO.CoordSys
import RO.StringUtil
import RO.Wdg
import TUI.TCC.TCCModel

_HelpURL = "Telescope/StatusWin.html#Offsets"
_DataWidth = 10

class OffsetWdg (tkinter.Frame):
    def __init__ (self, master=None, **kargs):
        """creates a new offset display frame

        Inputs:
        - master        master Tk widget -- typically a frame or window
        """
        tkinter.Frame.__init__(self, master, **kargs)
        self.tccModel = TUI.TCC.TCCModel.getModel()
        gr = RO.Wdg.Gridder(self, sticky="w")

        gr.gridWdg("Object")
        gr.gridWdg("Arc Off")
        gr.startNewCol()

        # object offset (tcc arc offset)
        self.objLabelSet = []
        self.objOffWdgSet = [   # arc offset position
            RO.Wdg.DMSLabel(
                master = self,
                precision = 1,
                width = _DataWidth,
                helpText = "Object arc offset",
                helpURL = _HelpURL,
            )
            for ii in range(2)
        ]
        for ii in range(2):
            wdgSet = gr.gridWdg (
                label = "",
                dataWdg = self.objOffWdgSet[ii],
                units = RO.StringUtil.DMSStr,
            )
            wdgSet.labelWdg.configure(width=4, anchor="e")
            self.objLabelSet.append(wdgSet.labelWdg)

        # sky offset
        gr.startNewCol()
        self.objXYOffWdgSet = [
            RO.Wdg.DMSLabel(
                master = self,
                precision = 1,
                width = _DataWidth,
                helpText = "Object offset shown in instrument x,y",
                helpURL = _HelpURL,
            )
            for ii in range(2)
        ]
        for ii in range(2):
            wdgSet = gr.gridWdg (
                label = ("(X", "(Y")[ii],
                dataWdg = self.objXYOffWdgSet[ii],
                units = RO.StringUtil.DMSStr + ")",
            )

        gr.startNewCol()
        gr.gridWdg(" Bore")
        gr.startNewCol()

        # boresight
        gr.startNewCol()
        self.boreWdgSet = [
            RO.Wdg.DMSLabel(
                master = self,
                precision = 1,
                width = _DataWidth,
                helpText = "Position of boresight on instrument",
                helpURL = _HelpURL,
            )
            for ii in range(2)
        ]
        for ii in range(2):
            gr.gridWdg (
                label = ("X", "Y")[ii],
                dataWdg = self.boreWdgSet[ii],
                units = RO.StringUtil.DMSStr,
            )
        
        # allow the last+1 column to grow to fill the available space
        self.columnconfigure(gr.getMaxNextCol(), weight=1)

        # track coordsys and objInstAng changes for arc/sky offset
        self.tccModel.objSys.addIndexedCallback(self._updObjSys)
        self.tccModel.objInstAng.addIndexedCallback(self._updObjXYOff)
        
        # track objArcOff and boresight position
        self.tccModel.objArcOff.addCallback(self._updObjOff)
        self.tccModel.boresight.addROWdgSet(self.boreWdgSet)
        
    def _updObjSys (self, csysObj, isCurrent=True, **kargs):
        """Object coordinate system updated; update arc offset labels
        """
        # print "StatusWdg/OffsetWdg._updObjSys%r" % ((csysObj, isCurrent),)
        posLabels = csysObj.posLabels()
        
        for ii in range(2):
            self.objLabelSet[ii]["text"] = posLabels[ii]

    def _updObjOff(self, objOffPVT, isCurrent, **kargs):
        for ii in range(2):
            objOff = objOffPVT[ii].getPos()
            self.objOffWdgSet[ii].set(objOff, isCurrent)
        self._updObjXYOff()

    def _updObjXYOff(self, *args, **kargs):
        objInstAngPVT, isCurrent = self.tccModel.objInstAng.getInd(0)
        objInstAng = objInstAngPVT.getPos()
        objOff = [None, None]
        for ii in range(2):
            objOff[ii], arcCurr = self.objOffWdgSet[ii].get()
            isCurrent = isCurrent and arcCurr
        try:
            objXYOff = RO.MathUtil.rot2D(objOff, objInstAng)
        except (TypeError, ValueError):
            objXYOff = (None, None)
        for ii in range(2):
            self.objXYOffWdgSet[ii].set(objXYOff[ii], isCurrent)
        

if __name__ == "__main__":
    from . import TestData

    tuiModel = TestData.tuiModel

    testFrame = OffsetWdg(tuiModel.tkRoot)
    testFrame.pack()

    TestData.init()

    tuiModel.tkRoot.mainloop()
