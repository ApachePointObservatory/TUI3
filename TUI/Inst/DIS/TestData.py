#!/usr/bin/env python
"""Data for testing various DIS widgets

History:
2005-07-21 ROwen    Bug fix: was not dispatching MainDataList in order
                    (because it was specified as a normal non-ordered dict).
2014-02-05 ROwen    Updated to use TUI.Base.TestDispatcher
"""
import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher(actor="dis", delay=0.5)
tuiModel = testDispatcher.tuiModel

MainDataList = (
    'filterNames="Empty","Gunn-Thuan"',
    'filterID=1',
    'filterName="Empty"',
    'maskNames="1.5\" Slit","2.0\" Slit","0.9\" Slit","open","1.2\" Bar"',
    'maskID=1',
    'maskName="1.5\" Slit"',
    'shutter="closed"',
    'detent=1394',
    'gset1names="high","high"',
    'gset2names="low","medium"',
    'turretPos=1',
    'turretPosName="grating set 1"',
    'gset1steps=1148,1315',
    'gset1zerosteps=318,314',
    'gset1cmdLambdas=4098,7102',
    'gset1actLambdas=4097,7103',
    'gset1dispersions=0.62,1.2',
    'gset2steps=275,297',
    'gset2zerosteps=275,296',
    'gset2cmdLambdas=0,20',
    'gset2actLambdas=1,19',
    'gset2dispersions=2.4,3.1',
    'ccdState="ok"',
    'ccdBin=2,2',
    'ccdWindow=1,1,1024,514',
    'ccdUBWindow=1,1,2048,1028',
    'ccdOverscan=50,50',
    'readoutOrder="parallel"',
    'name="dtest030319."',
    'number=1',
    'places=4',
    'path="/export/images"',
    'basename="/export/images/dtest030319.0001"',
    'ccdTemps=13.8,25.7',
    'ccdHeaters=0.0,0.0',
)

# each element of animDataSet is a full set of data to be dispatched,
# hence each element is a list of keyvar, value tuples
AnimDataSet = (
    ("turretPos=1",),
    ("turretPos=4",),
    ("turretPos=3",),
    ("turretPos=5",),
    ("turretPos=2",),
)

def start():
    testDispatcher.dispatch(MainDataList)

def animate():
    testDispatcher.runDataSet(AnimDataSet)
