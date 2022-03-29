#!/usr/local/bin/python

"""Apollo Window.

History:
"""
import RO.Alg
from . import pathStuff
pathStuff.apolloWindowPaths()
from . import Apollo_Wdg #HippoWdg_bunched for packaged data

def addWindow(tlSet):

	tlSet.createToplevel (
		name = "Inst.Apollo",
		defGeom = "1200x900+650+280",
		resizable = True,
		wdgFunc = Apollo_Wdg.NoteBook,#HippoWdg_bunched.NoteBook for packaged data
		visible = True
	)
