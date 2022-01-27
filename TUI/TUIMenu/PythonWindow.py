#!/usr/bin/env python
"""Python window

2003-12-17 ROwen
2004-05-18 ROwen    Stopped obtaining TUI model in addWindow; it was ignored.
                    Added test code.
2004-06-22 ROwen    Modified to use ScriptWdg->PythonWdg.
"""
import RO.Wdg
import TUI.Version

WindowName = "%s.Python" % (TUI.Version.ApplicationName,)

def addWindow(tlSet):
    tlSet.createToplevel (
        name = WindowName,
        defGeom = "+0+507",
        wdgFunc = RO.Wdg.PythonWdg,
        visible = False,
    )

if __name__ == "__main__":
    import tkinter
    import TUI.TUIModel

    root = tkinter.Tk()

    tm = TUI.TUIModel.getModel(True)
    addWindow(tm.tlSet)
    tm.tlSet.makeVisible('TUI.Python')

    root.lower()

    root.mainloop()
