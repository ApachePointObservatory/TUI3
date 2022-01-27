import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher(actor="agile", delay=0.5)
tuiModel = testDispatcher.tuiModel

MainDataList = (
    "cameraConnState=Connected, ''",
    "fwConnState=Connected, ''",
    'fwNames="Open", "MK_J", "MK_H", "?", "MK_L", "MK_M"',
    'fwOffsets=0.0, 21.0, -35.1, NaN, 1.5, 6.5',
    'fwStatus=2, 2, 0x0000, 0.0',
    'currFilter=2, "MK_J", Out, "", 21.0',
    "window=1, 1, 1024, 1024",
    "overscan=27, 0",
    "bin=2",
    "ccdTempLimits=1.5, 1.5, 10, 10",
    "ccdTemp=-40, normal",
    "ccdSetTemp=-40, normal",
    "gpsSynced=T",
    "ntpStatus=T, 'galileo.apo.nms', 1",
)

AnimDataSet = (
    ("fwConnState=Disconnected, ''",),
    ('fwStatus=-1, -1, ?, NaN',),
    ('currFilter=?, "", ?, "", 21.0',),
    ("gpsSynced=F",),
    ("ntpStatus=F, '?', ?",),
    ("gpsSynced=T",),
    ("ntpStatus=T, '?', ?",),
    ("ntpStatus=T, 'galileo.apo.nmsu', ?",),
    ("ntpStatus=T, 'galileo.apo.nmsu', 1",),
    ("ccdTemp=-5, veryHigh",),
    ("ccdTemp=-35, high",),
    ("ccdTemp=-45, low",),
    ("ccdTemp=-65, veryLow",),
    ("ccdTemp=-40, normal",),
    ("fwConnState=Connected, ''",),
    ('fwStatus=2, 2, 0x0201, 0.0',),
    ('fwStatus=2, 2, 0x1002, 0.0',),
    ('fwStatus=1, 2, 0x0000, 2.0',),
    ('currFilter=1, "Open", In, "ND 5", 0.0',),
    ("window=4, 5, 1001, 1002",),
)

FWAnimDataSet = (
    ('fwStatus=2, 2, 0x0201, 0.0',),
    ('fwStatus=2, 2, 0x0601, 1.0',),
    ('fwStatus=2, 2, 0x0000, 0.0',),
    ('fwStatus=2, 2, 0x0004, 0.0',),
    ('fwStatus=2, 2, 0x000C, 0.0',),
    ('fwStatus=2, 2, 0x0008, 0.0',),
    ('fwStatus=2, 2, 0x0000, 0.0',),
    ('fwStatus=2, 2, 0x1000, 1.0',),
    ('fwStatus=2, 2, 0x0000, 0.0',),
)

def start():
    testDispatcher.dispatch(MainDataList)

def animate():
    testDispatcher.runDataSet(AnimDataSet)
