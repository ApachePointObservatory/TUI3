import RO.KeyVariable
import TUI.TCC.TCCModel

class ScriptClass(object):
    def __init__(self, sr):
        self.tccModel = TUI.TCC.TCCModel.getModel()

    def run(self, sr):
        # Make sure a stop button has been engaged        
        stopCode = sr.getKeyVar(self.tccModel.ctrlStatusSet[0], ind=3)        
        if not ((0x800 & stopCode) >> 11):           
           raise sr.ScriptError("e-stop button must be engaged before continuing!")
        if ((0x800 & stopCode) >> 11):           
           sr.showMsg("e-stop button(s) engaged!", severity=RO.Constants.sevNormal)
           yield sr.waitMS(5000)
