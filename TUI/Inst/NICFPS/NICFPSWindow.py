#!/usr/bin/env python
"""Status/config and exposure windows for NIC-FPS.

History:
2004-10-19 ROwen
2008-02-11 ROwen    Modified to use new TUI.Inst.StatusConfigWdg.
2008-02-12 ROwen    Misfeature fix: was using instName=Expose for the expose window.
2011-08-11 ROwen    Modified to save state.
2014-02-03 ROwen    Updated to use modernized TestData.
"""
import RO.Alg
import TUI.Inst.ExposeWdg
import TUI.Inst.StatusConfigWdg
from . import StatusConfigInputWdg

InstName = StatusConfigInputWdg.StatusConfigInputWdg.InstName

def addWindow(tlSet):
    tlSet.createToplevel (
        name = "None.%s Expose" % (InstName,),
        defGeom = "+452+280",
        resizable = False,
        wdgFunc = RO.Alg.GenericCallback (
            TUI.Inst.ExposeWdg.ExposeWdg,
            instName = InstName,
        ),
        visible = False,
    )
    
    tlSet.createToplevel (
        name = "Inst.%s" % (InstName,),
        defGeom = "+676+280",
        resizable = False,
        wdgFunc = StatusConfigWdg,
        visible = False,
        doSaveState = True,
    )

class StatusConfigWdg(TUI.Inst.StatusConfigWdg.StatusConfigWdg):
    def __init__(self, master):
        TUI.Inst.StatusConfigWdg.StatusConfigWdg.__init__(self,
            master = master,
            statusConfigInputClass = StatusConfigInputWdg.StatusConfigInputWdg,
        )


if __name__ == "__main__":
    import RO.Wdg
    from . import TestData

    root = TestData.tuiModel.tkRoot
    root.resizable(width=0, height=0)

    tlSet = TestData.tuiModel.tlSet
    addWindow(tlSet)
    tlSet.makeVisible("Inst.%s" % (InstName,))
    
    TestData.start()
    
    root.mainloop()
