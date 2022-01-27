"""Widget for Agile filter wheel controller (including the filter slide)

To do:
- Center names for the filter slide
- Consider how to handle filter slide names of varying length;
  perhaps set a minimum length but grow to accommodate larger filters?

History:
2009-06-24 ROwen
"""
import tkinter
import RO.Wdg
import RO.StringUtil
import RO.KeyVariable
from . import AgileModel

class AgileFilterWdg(object):
    """Agile filter controls and status.
    
    Note: this widget adds its widgets to an existing gridder
    (so that the controls are nicely aligned with existing controls).
    """
    def __init__(self,
        master,
        statusBar,
        gridder,
        helpPrefix = None,
    ):
        self.statusBar = statusBar

        self.agileModel = AgileModel.getModel()
        self.currCmd = None
        gr = gridder
        
        wheelFrame = tkinter.Frame(master)
        
        self.userFilterWdg = RO.Wdg.OptionMenu(
            master = wheelFrame,
            items = (),
            noneDisplay = "?",
            autoIsCurrent = True,
            width = 8,
            callFunc = self.enableButtons,
            defMenu = "Current",
            helpText =  "Agile filter",
            helpURL = helpPrefix + "FilterWheel",
        )
        self.userFilterWdg.pack(side="left")
        
        self.applyBtn = RO.Wdg.Button(
            master = wheelFrame,
            text = "Set Filter",
            callFunc = self.doApply,
            helpText = "Set Agile filter",
            helpURL = helpPrefix + "FilterWheel",
        )
        self.applyBtn.pack(side="left")

        self.cancelBtn = RO.Wdg.Button(
            master = wheelFrame,
            text = "X",
            callFunc = self.doCancel,
            helpText = "Cancel filter command",
            helpURL = helpPrefix + "FilterWheel",
        )
        self.cancelBtn.pack(side="left")

        self.currentBtn = RO.Wdg.Button(
            master = wheelFrame,
            text = "Current Filter",
            callFunc = self.doCurrent,
            helpText = "Show current Agile filter",
            helpURL = helpPrefix + "FilterWheel",
        )
        self.currentBtn.setEnable(False)
        self.currentBtn.pack(side="left")

        gr.gridWdg("Filter Wheel", wheelFrame)
        
        
        slideFrame = tkinter.Frame(master)

        self.slideInfoWdg = RO.Wdg.StrLabel(
            master = slideFrame,
            helpText = "Filter slide information",
            helpURL = helpPrefix + "FilterSlide",
        )
        self.slideInfoWdg.pack(side="left")
        gr.gridWdg("Filter Slide", slideFrame)
        
        self.agileModel.currFilter.addCallback(self.updCurrFilter)
        self.agileModel.fwNames.addCallback(self.updFwNames)
    
    def cmdDone(self, *args, **kargs):
        self.currCmd = None
        self.enableButtons()

    def doApply(self, wdg=None):
        """Apply changes to configuration"""
        desFilter = self.userFilterWdg.getString()
        if desFilter == "?":
            raise RuntimeError("Unknown filter")
        try:
            desSlot = int(desFilter.split(":", 1)[0])
        except Exception:
            raise RuntimeError("Invalid filter entry %r" % (desFilter,))
        cmdStr = 'fwMove %d' % (desSlot,)

        self.currCmd = RO.KeyVariable.CmdVar (
            actor = self.agileModel.actor,
            cmdStr = cmdStr,
            callFunc = self.cmdDone,
            callTypes = RO.KeyVariable.DoneTypes,
        )
        self.statusBar.doCmd(self.currCmd)
        self.enableButtons()
    
    def doCancel(self, *args, **kargs):
        if self.currCmd and not self.currCmd.isDone():
            self.currCmd.abort()
            self.doCurrent()
    
    def doCurrent(self, wdg=None):
        self.userFilterWdg.restoreDefault()

    def enableButtons(self, wdg=None):
        """Enable the various buttons depending on the current state"""
        if self.currCmd and not self.currCmd.isDone():
            self.userFilterWdg.setEnable(False)
            self.currentBtn.setEnable(False)
            self.cancelBtn.setEnable(True)
            self.applyBtn.setEnable(False)
        else:
            allowChange = not self.userFilterWdg.isDefault()
            self.userFilterWdg.setEnable(True)
            self.applyBtn.setEnable(allowChange)
            self.cancelBtn.setEnable(False)
            self.currentBtn.setEnable(allowChange)

    def updCurrFilter(self, currFiltInfo, isCurrent, keyVar=None):
        #print "updCurrFilter(currFiltInfo = %s, isCurrent = %s)" % (currFiltInfo, isCurrent)
        slotNum, slotName, slidePos, slideName, focusOffset = currFiltInfo[0:5]
        if slotNum is None:
            wheelEntry = None
            slotIsCurr = False
        else:
            wheelEntry = formatFilterEntry(slotNum, slotName)
            slotIsCurr = isCurrent
        self.userFilterWdg.setDefault(wheelEntry, isCurrent = slotIsCurr)

        slideInfoStr, slideIsCurr = {
            True: ("In: %s" % (slideName,), isCurrent),
            False: ("Out", isCurrent),
        }.get(slidePos, ("?", False))
        self.slideInfoWdg.set(slideInfoStr, isCurrent=slideIsCurr)

    def updFwNames(self, filtNameList, isCurrent, keyVar=None):
        #print "updFwNames(filtNameList = %s, isCurrent = %s)" % (filtNameList, isCurrent)
        if not isCurrent:
            return
        
        maxEntryLen = 0
        entryList = []
        slotNum = 1
        for slotName in filtNameList:
            entryList.append(formatFilterEntry(slotNum, slotName))
            slotNum += 1

        self.userFilterWdg["width"] = maxEntryLen
        self.userFilterWdg.setItems(entryList)

def formatFilterEntry(slotNum, filterName):
    """Format an entry for the filter wheel menu
    
    Inputs:
    - slotNum: slot number; must be an integer
    - filterName: name of filter in this slot
    """
    if slotNum is None:
        raise ValueError("Invalid slotNum=%s; must be an integer" % (slotNum,))
    if filterName in ("?", None):
        return "%d: ?" % (slotNum,)
    return "%d: %s" % (slotNum, filterName)
