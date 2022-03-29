#!/usr/bin/env python
"""Data for testing various ARCTIC widgets

History:
2015-10-20 ROwen    Added filterState and switched to currFilter, cmdFilter.
2015-10-29 ROwen    Added exposure state keywords and removed some keywords that are not output.
                    Added an animated state that tests a filter move that ends with cmdFilter != filterName.
"""
import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher(actor="arctic", delay=1)
tuiModel = testDispatcher.tuiModel

MainDataList = (
    'ampNames=LL, Quad',
    'ampName=Quad',
    'filterNames="SDSS u\'", "SDSS g\'", "SDSS r\'", "SDSS i\'", "SDSS z\'"',
    'currFilter=1, "SDSS u\'"',
    'cmdFilter=1, "SDSS u\'"',
    "filterState=Done, 0, 0",
    'shutter="closed"',
    'ccdState="ok"',
    'ccdBin=2,2',
    'ccdWindow=1,1,1024,514',
    'ccdUBWindow=1,1,2048,1028',
    'ccdOverscan=50,0',
    'ccdSize=4096,4096',
    'ccdTemp=?',
    'exposureState=done, 0.0000',
    'readoutRateNames=Slow, Medium, Fast',
    'readoutRateName=Slow',
    'tempSetpoint=None',
)

# Each element of animDataSet is list of keywords
AnimDataSet = (
    ('cmdFilter=3, "SDSS r\'"', "filterState=Moving, 3, 3", "ampName=UR", 'currFilter=NaN, ?'),
    ('currFilter=3, "SDSS g\'"', "filterState=Done, 0, 0"),
    ('currFilter=3, "SDSS r\'"', "filterState=Done, 0, 0"),
)

def start():
    testDispatcher.dispatch(MainDataList)

def animate():
    testDispatcher.runDataSet(AnimDataSet)
