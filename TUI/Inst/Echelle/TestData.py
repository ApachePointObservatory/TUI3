#!/usr/bin/env python
"""Data for testing various Echelle widgets

History:
2014-02-05 ROwen    Updated to use TUI.Base.TestDispatcher
"""
import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher(actor="echelle", delay=0.5)
tuiModel = testDispatcher.tuiModel

MainDataList = (
    'shutter="closed",',
    'calFilterNames="a", "b", "open", "", "", ""',
    'svFilterNames="x", "y", "z", "open", "", ""',
    'mirrorNames="sky", "calibration"',
    'mirror="sky",',
    'calFilter="open",',
    'svFilter="open",',
    'lampNames="ThAr", "Quartz", ""',
    'lampStates=0, 0, 0',
)
# each element of animDataSet is a full set of data to be dispatched,
# hence each element is a dict of keyvar, value tuples
AnimDataSet = (
    ('mirror="lamps"', 'calFilter="a"',),
    ('lampStates=1,0,0', 'shutter="open"',),
    ('lampStates=0,1,0', 'calFilter="b"',),
    ('lampNames="ThAr", "Quartz", "Other"',),
    ('lampStates=0,0,1', 'calFilter="a"',),
    ('lampNames="ThAr", "Quartz"',),
    ('mirror="sky"', 'lamps=0,0,0', 'shutter="closed"',),
)

def start():
    testDispatcher.dispatch(MainDataList)

def animate():
    testDispatcher.runDataSet(AnimDataSet)
