import TUI.Base.TestDispatcher

testDispatcher = TUI.Base.TestDispatcher.TestDispatcher("perms", delay=1.5)
tuiModel = testDispatcher.tuiModel

MainDataList = (
    "actors=dis, echelle, tcc, tlamps, tspec, gcam",
    "programs=UW01, CL01, TU01, UW02, UW03",
    "authList=UW02, tcc, echelle",
    "authList=UW03, tcc, echelle",
    "lockedActors=tspec",
    "authList=CL01, tcc, dis, tspec, tlamps",
    "authList=TU01, echelle, perms, tcc, tspec",
)

AnimDataSet = (
    (
        "authList=CL01, tcc, dis, echelle, tspec, tlamps",
        "authList=UW01, tcc, tspec, tlamps",
    ),
    (
        "programs=TU01, UW01",
    ),
    (
        "programs=TU01, UW01, XY01",
        "authList=XY01, tcc, echelle",
    ),
    (
        "actors=tcc, tspec, dis, echelle, tlamps, apollo, gcam",
    ),
    (
        "authList=CL01, apollo, echelle, perms, tcc, tspec",
    ),
)

def start():
    testDispatcher.dispatch(MainDataList)
    
def animate(dataIter=None):
    dataList = (MainDataList,) + AnimDataSet
    testDispatcher.runDataSet(dataList)
