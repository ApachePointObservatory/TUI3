#!/usr/bin/env python
"""Data for testing various TSpec widgets

History:
2014-02-07 ROwen    Updated to use TestDispatcher
"""
import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher(actor="tspec", delay=0.5)
tuiModel = testDispatcher.tuiModel

tuiModel = TUI.TUIModel.getModel(True)
dispatcher = tuiModel.dispatcher
cmdr = tuiModel.getCmdr()

MainDataList = (
    'arrayPower="On"',
    'exposureModeInfo="Fowler", 1, 16, "Sutr", 1, 4',
    'exposureMode="Fowler", 3',
    'ttMode="ClosedLoop"',
    'ttPosition=15.4, 16.4, -17.2, -17.1',
    'ttLimits=-20.0, 20.0, -20.0, 20.0',
    'tempNames="BoilOff","TempBrd","PrismBox","SpecCam","AuxTank","H1","BH4","BH3","BH2","Shield"',
    'temps=85.404,284.601,78.508,77.363,76.405,78.069,78.392,77.749,77.503,79.244',
    'tempAlarms=0,0,0,0,0,0,0,0,0,0',
    'tempThresholds=115,400,400,400,80,400,400,None,400,400', # neg for lower limit; None for no limit
    'vacuum=1.5e-8',
    'vacuumAlarm=0',
    'vacuumThreshold=1e-7',
)

slitPosList = ["%s %s" % (a, b) for a in ("0.7", "1.1", "1.5", "1.7") for b in ("Slit", "Block")]
TCameraDataList = (
    'slitPositions = %s' % (", ".join(repr(val) for val in slitPosList),),
    'slitPosition = %s' % (", ".join(repr(val) for val in slitPosList[2:3]),),
    'slitState="Done", 0.0, 0.0',
)

# each element of animDataSet is a list of data to be dispatched
# note: if you want to include slit data then use a list of dicts and call runDataDictSet, instead
AnimDataSet = (
    (
        'mirror="lamps"',
        'calFilter="a"',
    ),
    (
        'vacuum=2.43e-7',
        'vacuumAlarm=1',
    ),
    (
        'temps=159.404,284.601,78.508,77.363,76.405,78.069,78.392,77.749,77.503,500.244',
        'tempAlarms=1,0,0,0,0,0,0,0,0,1',
    ),
    (
        'temps=73.052,284.601,78.508,77.363,76.405,78.069,78.392,77.749,77.503,79.244',
        'tempAlarms=0,0,0,0,0,0,0,0,0,0',
        'vacuum=1.5e-8',
        'vacuumAlarm=0',
    ),
)

def start():
    testDispatcher.dispatch(MainDataList)
    testDispatcher.dispatch(TCameraDataList, actor="tcamera")

def animate():
    testDispatcher.runDataSet(AnimDataSet)
