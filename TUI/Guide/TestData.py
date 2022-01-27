#!/usr/bin/env python
"""Data for testing GuideWdg

History:
2014-09-16 ROwen
"""
import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher(actor="tcam", delay=5)
tuiModel = testDispatcher.tuiModel

import TUI.Models.HubModel
hubModel = TUI.Models.HubModel.getModel()

import TUI.TUIMenu.DownloadsWindow
TUI.TUIMenu.DownloadsWindow.addWindow(tlSet=tuiModel.tlSet)

HubDataList = (
    'httpRoot="hub35m.apo.nmsu.edu", "/images/"',
)

MainDataList = (
    'expState=integrating, "2014-09-17T12:13:14.5", 0.5, 2',
    'fsActRadMult=1.5',
    'fsActThresh=3.1',
    'fsDefRadmult=2.0',
    'fsDefThresh=3.0',
    'guideState=on',
    'guideMode=manual',
    'measOffset=0.01, -0.01',
    'actOffset=0.005, -0.005',
    'starQuality=0.9',
)

_ImageSubdir = "keep/guiding/tcam/UT131023/"
# each element of animDataSet is a full set of data to be dispatched,
# hence each element is a list of keyvar=value strings
AnimDataSet = (
    (
        'files=g, 1, %r, "proc-t1214.fits", ""' % (_ImageSubdir,),
        'expState=integrating, "2014-09-17T12:13:16.5", 2, 2',
        'fsActRadMult=1.5',
        'fsActThresh=3.1',
    ),
    (
        'files=g, 1, %r, "proc-tbad.fits", ""' % (_ImageSubdir,),
        'expState=integrating, "2014-09-17T12:13:18.5", 2, 2',
        'fsActRadMult=1.5',
        'fsActThresh=3.1',
    ),
    (
        'files=g, 1, %r, "proc-t1215.fits", ""' % (_ImageSubdir,),
        'expState=integrating, "2014-09-17T12:13:20.5", 2, 2',
        'fsActRadMult=1.5',
        'fsActThresh=3.1',
    ),
)

def start(actor="dcam"):
    testDispatcher.actor = actor
    testDispatcher.dispatch(HubDataList, actor="hub")
    testDispatcher.dispatch(MainDataList)

def animate():
    testDispatcher.runDataSet(AnimDataSet)
