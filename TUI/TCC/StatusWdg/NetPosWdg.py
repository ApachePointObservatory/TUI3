#!/usr/bin/env python
"""Displays coordinate system, object net position,
and rotation type and angle.

History:
2003-03-26 ROwen    Modified to use the tcc model.
2003-03-31 ROwen    Switched from RO.Wdg.LabelledWdg to RO.Wdg.Gridder
2003-05-28 ROwen    Modified to use RO.CoordSys.
2003-06-09 Rowen    Removed dispatcher arg.
2003-06-11 ROwen    Modified to use new tccModel objSys.
2003-06-12 ROwen    Added helpText entries.
2003-06-18 ROwen    Bug fix: pos1 not shown in hours when wanted (introduced 2003-06-11).
2003-06-19 ROwen    Improved helpText for coordinate system, rotator angle and rotator position.
2003-06-25 ROwen    Modified test case to handle message data as a dict
2003-12-03 ROwen    Made object name longer (to match slew input widget).
2004-02-04 ROwen    Modified _HelpURL to match minor help reorg.
2009-09-09 ROwen    Modified to use TestData.
2010-11-04 ROwen    Tweaked help URLs.
2014-08-15 ROwen    Fixed coordinate system display:
                    - Topocentric and Observed now show date as TAI, MJD, if provided (very unlikely)
                    - The field is now long enough to avoid truncation
                    Also removed special handling for objSys unknown, since it's not needed and never happens
"""
import tkinter
import RO.CoordSys
import RO.StringUtil
import RO.Wdg
import TUI.TCC.TCCModel

_HelpURL = "Telescope/StatusWin.html#NetPos"

_CoordSysHelpDict = {
    RO.CoordSys.ICRS: "ICRS mean RA/Dec: the current standard (\N{ALMOST EQUAL TO}FK5 J2000)",
    RO.CoordSys.FK5: "FK5 mean RA/Dec: the IAU 1976 standard",
    RO.CoordSys.FK4: "FK4 mean RA/Dec: an old standard",
    RO.CoordSys.Galactic: "Galactic long/lat: the IAU 1958 standard",
    RO.CoordSys.Geocentric: "Current apparent geocentric RA/Dec",
    RO.CoordSys.Topocentric: "Current apparent topocentric az/alt; no refraction corr.",
    RO.CoordSys.Observed: "Observed az/alt: topocentric plus refraction correction",
    RO.CoordSys.Physical: "Physical az/alt; pos. of a perfect telescope",
    RO.CoordSys.Mount: "Mount az/alt: pos. sent to the axis controllers; no wrap",
}

_RotTypeHelpDict = {
    "object":   "Rotating with the object",
    "horizon": "Rotating with the horizon",
    "mount": "Rotating with respect to the rotator mount",
    "none": "Rotator left where it is",
}

_RotPosHelpDict = {
    "object": "Angle of object with respect to the instrument",
    "horizon": "Angle of az/alt with respect to the instrument",
    "mount": "Angle sent to the rotator controller",
}

class NetPosWdg (tkinter.Frame):
    def __init__ (self, master=None, **kargs):
        """creates a new telescope position position frame

        Inputs:
        - master        master Tk widget -- typically a frame or window
        """
        tkinter.Frame.__init__(self, master, **kargs)
        self.tccModel = TUI.TCC.TCCModel.getModel()
        gr = RO.Wdg.Gridder(self, sticky="w")

        # object name
        self.objNameWdg = RO.Wdg.StrLabel(self,
            width=25,
            anchor="w",
            helpText = "Object name",
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "Name",
            dataWdg = self.objNameWdg,
            colSpan = 3,
        )
        self.tccModel.objName.addROWdg(self.objNameWdg)
        
        # object net position
        self.netPos1Wdg = gr.gridWdg (
            label = "",
            dataWdg = RO.Wdg.DMSLabel(self,
                precision=2,
                width=13,
                helpText = "Net object position, including object offset",
                helpURL = _HelpURL,
            ),
            units = "",
        )

        self.netPos2Wdg = gr.gridWdg (
            label = "",
            dataWdg = RO.Wdg.DMSLabel(self,
                precision=2,
                width=13,
                helpText = "Net object position, including object offset",
                helpURL = _HelpURL,
            ),
            units = RO.StringUtil.DMSStr,
        )
        self.tccModel.netObjPos.addROWdgSet(
            (self.netPos1Wdg.dataWdg, self.netPos2Wdg.dataWdg))

        # coordinate system
        self.csysWdg = RO.Wdg.StrLabel(self,
            width=20,
            anchor="w",
            helpText = "Object coordinate system",
            helpURL = _HelpURL,
        )
        gr.gridWdg (
            label = "CSys",
            dataWdg = self.csysWdg,
            colSpan = 2
        )
        self.tccModel.objSys.addCallback(self._objSysChanged)

        # rotation angle and type
        rotFrame = tkinter.Frame(self)
        self.rotPosWdg = RO.Wdg.FloatLabel(rotFrame,
            precision=2,
            width=8,
            helpText = "Rotator angle (see full help for more info)",
            helpURL = _HelpURL,
        )
        self.rotPosWdg.pack(side="left")
        rotUnitsLabel = tkinter.Label(rotFrame, text=RO.StringUtil.DegStr)
        rotUnitsLabel.pack(side="left")
        self.rotTypeWdg = RO.Wdg.StrLabel(rotFrame,
            width=8,
            anchor="w",
            helpURL = _HelpURL,
        )
        self.rotTypeWdg.pack(side="left")
        
        gr.gridWdg (
            label = "Rot",
            dataWdg = rotFrame,
            colSpan = 2,
        )
        self.tccModel.rotType.addROWdg(self.rotTypeWdg)
        self.tccModel.rotType.addIndexedCallback(self._rotTypeChanged)
        self.tccModel.rotPos.addROWdg(self.rotPosWdg)

        # allow the last column to grow to fill the available space
        self.columnconfigure(3, weight=1)

    def _objSysChanged (self, csysObjAndDate, isCurrent=True, **kargs):
        """sets the coordinate system

        Inputs:
        - csysObjAndDate: a duple consisting of:
          - coordinate system constant
          - date (a number)
        """
        # print "TUI.TCC.StatusWdg.NetPosWdg._objSysChanged%r" % ((csysObjAndDate, isCurrent),)
        csysObj, csysDate = csysObjAndDate
        dateValid = csysDate is not None
                
        if csysObj.dateIsYears():
            if not dateValid:
                csysStr = "%s ?date?" % (csysObj,)
            elif csysDate != 0.0 or csysObj.hasEquinox():
                if round(csysDate) == csysDate:
                    csysStr = "%s  %s%.0f" % (csysObj, csysObj.datePrefix(), csysDate)
                else:
                    csysStr = "%s  %s%.2f" % (csysObj, csysObj.datePrefix(), csysDate)
            else:
                csysStr = str(csysObj)
        elif csysObj.dateIsSidTime(): # a lie, actually TAI (MJD, sec)
            # almost always the default date (<0 => now) is used,
            # but a date might conceivably be specified, in which case it is TAI (MJD, sec)
            if not dateValid:
                csysStr = "%s ?date?" % (csysObj,)
            elif csysObjAndDate[1] == 0.0:
                csysStr = str(csysObj)
            else:
                csysStr = "%s %0.1f"% (csysObj, csysDate)
        else:
            # no date
            csysStr = str(csysObj)
            
        self.csysWdg.set(csysStr, isCurrent = isCurrent)
        
        posLabels = csysObj.posLabels()
        self.netPos1Wdg.labelWdg["text"] = posLabels[0]
        self.netPos2Wdg.labelWdg["text"] = posLabels[1]
        self.setPos1InHrs(csysObj.eqInHours())
        
        self.csysWdg.helpText = _CoordSysHelpDict.get(csysObj.name(), "Coordinate system")
    
    def _rotTypeChanged(self, rotType, isCurrent=True, **kargs):
        if rotType:
            rotType = rotType.lower()
        self.rotTypeWdg.helpText = _RotTypeHelpDict.get(rotType, "Type of rotation")
        self.rotPosWdg.helpText = _RotPosHelpDict.get(rotType, "Angle of rotation")

    def setNoCoordSys(self):
        """Call if coordinate system invalid or unknown"""
        self.csysWdg.set(None, isCurrent = False)
        self.netPos1Wdg.labelWdg["text"] = "RA"
        self.netPos2Wdg.labelWdg["text"] = "Dec"
        self.setPos1InHrs(True)
    
    def setPos1InHrs(self, pos1InHrs):
        if pos1InHrs:
            self.netPos1Wdg.dataWdg.setCvtDegToHrs(True)
            self.netPos1Wdg.unitsWdg["text"] = "hms"
        else:
            self.netPos1Wdg.dataWdg.setCvtDegToHrs(None)
            self.netPos1Wdg.unitsWdg["text"] = RO.StringUtil.DMSStr
    
if __name__ == "__main__":
    from . import TestData

    tuiModel = TestData.tuiModel

    testFrame = NetPosWdg(tuiModel.tkRoot)
    testFrame.pack()

    dataList = (
        "ObjName='test object with a long name'",
        "ObjSys=geo, 2014.352",
        "ObjNetPos=120.123450, 0.000000, 4494436859.66000, -2.345670, 0.000000, 4494436859.66000",
        "RotType=Obj",
        "RotPos=3.456789, 0.000000, 4494436895.07921",
    )

    TestData.testDispatcher.dispatch(dataList)

    tuiModel.tkRoot.mainloop()
