#!/usr/bin/env python
"""Widget to allow users to specify a target position and initiate a slew.

To Do:
- Consider packing widgets to fit N/S. The widgets have to be
modified to take advantage of this, and perhaps this should be
a flag so users aren't forced to do it this way.

History:
2002-06-25 ROwen    First version with history.
2002-08-02 ROwen    Checkbuttons no longer take focus. Added neatenDisplay method.
2002-08-08 ROwen    Added valueDictOK and added a flag for this to the callback.
2002-08-23 ROwen    Bug fix: date wasn't being returned for ICRS
                    because the main date widget was hidden.
2003-03-26 ROwen    Added dispatcher arg (wanted by ObjPosWdg).
2003-03-31 ROwen    Modified to use 2003-03-31 ObjPosWdg.
2003-05-29 ROwen    Added help text to the show/hide buttons for the option panels.
2003-06-09 ROwen    Removed dispatcher arg.
2003-07-24 ROwen    Fixed valueDictOK (broken by 2003-07-10 change to ObjPosWdg).
2003-10-24 ROwen    Added userModel input.
2004-05-18 ROwen    Stopped importing string and sys since they weren't used.
                    Bug fix: the test code was broken.
2004-09-24 ROwen    Removed restart panel; it wasn't doing anything useful.
2007-08-09 ROwen    Implemented coordsys-based enable/disable of option panels.
                    Added setStar method.
2007-09-27 ROwen    Removed userModel argument for AxisWrapWdg and CalibWdg
                    (since it was being ignored).
2007-09-28 ROwen    Fixed PR 666: was sending userModel to sub-widgets even if userModel not supplied.
2011-02-16 ROwen    Disabled the Calibrate panel at Russet's request.
2011-02-17 ROwen    Bug fix: Calibrate was still referenced in DisableDict, producing error messages.
2012-11-14 ROwen    Update help text for show/hide controls for checkbuttons with indicatoron.
"""
import tkinter
from . import ObjPosWdg
import RO.Wdg
from . import MagPMWdg
from . import DriftScanWdg
from . import KeepOffsetWdg
from . import CalibWdg
from . import AxisWrapWdg
import RO.InputCont
import TUI.TCC.UserModel

class InputWdg(RO.Wdg.InputContFrame):
    """A widget for specifying information about a slew.

    Inputs:
    - master        master Tk widget -- typically a frame or window
    - userModel     a TUI.TCC.UserModel; specify only if global model
                    not wanted (e.g. for checking catalog values)
    """
    DisableDict = {
        "Mag, PM": set((RO.CoordSys.Mount, RO.CoordSys.Physical, RO.CoordSys.Observed, RO.CoordSys.Topocentric)),
#        "Calibrate": set((RO.CoordSys.Mount, RO.CoordSys.Physical)),
        "Axis Wrap": set((RO.CoordSys.Mount,)),
    }
    def __init__ (self,
        master = None,
        userModel = None,
    ):
        RO.Wdg.InputContFrame.__init__(self, master = master)
        
        self.userModel = userModel or TUI.TCC.UserModel.getModel()
        
        # create object position frame
        self.objPosWdg = ObjPosWdg.ObjPosWdg(
            master = self,
            userModel = userModel,
        )
        self.objPosWdg.pack(side=tkinter.LEFT, anchor=tkinter.NW)
        
        # create a frame to hold hideable option panels
        optionFrame = tkinter.Frame(master = self)
                
        # create hideable panel for magnitude and proper motion
        magPMWdg = MagPMWdg.MagPMWdg(
            master = optionFrame,
            userModel = userModel,
            relief = tkinter.RIDGE,
        )
        
        # create a hideable panel for drift scanning
        driftScanWdg = DriftScanWdg.DriftScanWdg(
            master = optionFrame,
            userModel = userModel,
            relief = tkinter.RIDGE,
        )
                
        # create hideable panel for keeping offsets
        keepOffsetWdg = KeepOffsetWdg.KeepOffsetWdg(
            master = optionFrame,
            relief = tkinter.RIDGE,
        )
        
        # create hideable panel for calibration options
        calibWdg = CalibWdg.CalibWdg(
            master = optionFrame,
            relief = tkinter.RIDGE,
        )
        
        # create hideable option panel for wrap
        axisWrapWdg = AxisWrapWdg.AxisWrapWdg(
            master = optionFrame,
            relief = tkinter.RIDGE,
        )
        
        # list of option widgets, with descriptive text
        self.optionDescrWdgList = (
            ("Mag, PM", magPMWdg, "Show magnitude and proper motion controls?"),
            ("Drift Scan", driftScanWdg, "Show drift scan controls?"),
            ("Keep Offsets",  keepOffsetWdg, "Show controls to retain current offsets?"),
# Calibrate panel disabled at Russet's request; she says it is hard to use correctly
# partly because the exposure time is usually wrong for such bright stars
#            ("Calibrate", calibWdg, "Show pointing calibration controls?"),
            ("Axis Wrap", axisWrapWdg, "Show wrap preference controls?"),
        )
    
        # create a set of controls to show the optional panels
        self.optButtonWdg = RO.Wdg.OptionPanelControl(self,
            wdgList = self.optionDescrWdgList,
            labelText="Options:",
            takefocus=0,
        )
        self.optButtonWdg.pack(side=tkinter.LEFT, anchor=tkinter.NW)
        optionFrame.pack(side=tkinter.LEFT, anchor=tkinter.NW)
        
        # create input container set
        wdgList = [self.objPosWdg] + [x[1] for x in self.optionDescrWdgList]
        contList = [wdg.inputCont for wdg in wdgList]
        self.inputCont = RO.InputCont.ContList (
            conts = contList,
            formatFunc = RO.InputCont.BasicContListFmt(valSep=""),
        )
        self.userModel.coordSysName.addCallback(self._coordSysChanged)
    
    def _coordSysChanged (self, coordSys):
        """Updates the display when the coordinate system is changed.
        """
        for panelName, disableCSys in InputWdg.DisableDict.items():
            self.optButtonWdg.setEnable(panelName, coordSys not in disableCSys)
        
    def neatenDisplay(self):
        """Makes sure all input fields are neatened up
        and restore the default focus (the next tab will be into the name field).
        In fact the only ones that matter are the DMS fields (all in SetObjPos)"""
        self.objPosWdg.neatenDisplay()
    
    def setStar(self, newStar):
        """Set a new star"""
        self.userModel.potentialTarget.set(newStar)
        for wdgName, wdg, wdgDescr in self.optionDescrWdgList:
            makeVisible = not wdg.inputCont.allDefault()
            self.optButtonWdg.setBool(wdgName, makeVisible)


if __name__ == "__main__":
    root = RO.Wdg.PythonTk()
    root.resizable(width=0, height=0)
    
    def doPrint(*args):
        try:
            print("value dict = %s" % (testFrame.getValueDict(),))
            print("command = %r" % (testFrame.getString(),))
        except ValueError as e:
            print("Error:", e)

    def restoreDefault():
        print(testFrame.restoreDefault())

    testFrame = InputWdg(master = root)
    testFrame.pack()
    
    buttonFrame = tkinter.Frame(master = root)
    buttonFrame.pack(anchor="nw")

    printButton = tkinter.Button (buttonFrame, command=doPrint, text="Print")
    printButton.pack(side="left")

    defButton = tkinter.Button (buttonFrame, command=restoreDefault, text="Default")
    defButton.pack(side="left")

    root.mainloop()
