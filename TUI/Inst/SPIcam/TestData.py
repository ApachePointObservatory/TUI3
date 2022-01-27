#!/usr/bin/env python
"""Data for testing various DIS widgets

History:
2005-07-21 ROwen    Bug fix: was not dispatching MainDataList in order
                    (because it was specified as a normal non-ordered dict).
2008-04-24 ROwen    Bug fix: had too few filter names.
2014-02-03 ROwen    Updated to use TUI.Base.TestDispatcher
"""
import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher(actor="spicam", delay=0.5)
tuiModel = testDispatcher.tuiModel

MainDataList = (
    'filterNames="SDSS u\'", "SDSS g\'", "SDSS r\'", "SDSS i\'", "SDSS z\'", "Hodge 6629"',
    'filterID=1',
    'filterName="Hodge 6629"',
    'shutter="closed"',
    'ccdState="ok"',
    'ccdBin=2,2',
    'ccdWindow=1,1,1024,514',
    'ccdUBWindow=1,1,2048,1028',
    'ccdOverscan=50,50',
    'name="dtest030319."',
    'number=1',
    'places=4',
    'path="/export/images"',
    'basename="/export/images/dtest030319.0001"',
    'ccdTemps=-113.8,-106.7',
    'ccdHeaters=0.0,0.0',
)

# Each element of animDataSet is list of keywords
AnimDataSet = (
)

def start():
    testDispatcher.dispatch(MainDataList)

def animate():
    testDispatcher.runDataSet(AnimDataSet)
