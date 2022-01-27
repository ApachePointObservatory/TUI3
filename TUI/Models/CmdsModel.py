#!/usr/bin/env python
"""An object that models the hub's cmds actor.

2011-07-27 ROwen
"""
import RO.CnvUtil
import RO.CoordSys
import RO.KeyVariable
import TUI.TUIModel

_theModel = None

def getModel():
    global _theModel
    if _theModel ==  None:
        _theModel = _Model()
    return _theModel

class _Model (object):
    def __init__(self,
    **kargs):
        self.actor = "cmds"
        self.dispatcher = TUI.TUIModel.getModel().dispatcher

        keyVarFact = RO.KeyVariable.KeyVarFactory(
            actor = self.actor,
            converters = str,
            dispatcher = self.dispatcher,
            allowRefresh = False,
        )
        
        self.cmdDone = keyVarFact(
            keyword = "CmdDone",
            nval = 1,
            converters = RO.CnvUtil.asInt,
            description = "internal command sequence number of completed command",
        )

        self.cmdQueued = keyVarFact(
            keyword = "CmdQueued",
            converters = (
                RO.CnvUtil.asInt,
                RO.CnvUtil.asFloat,
                str,
                RO.CnvUtil.asInt,
                str,
                str,
            ),
            description = """Generated right before a new command is sent to an actor. Fields are:
            * internal command sequence number
            * MJD TAI timestamp
            * commander name
            * command ID supplied by commander
            * actor
            * command text
            """,
            isLocal = True, # synthesized on 3.5m; directly available on 2.5m and has an extra field
        )
        
        self.newCmd = keyVarFact(
            keyword = "NewCmd",
            nval = 1,
            converters = RO.CnvUtil.asInt,
            description = """Generated right before a new command is sent to an actor.
            The one field is the internal sequence number""",
            allowRefresh = False,
        )
        self.newCmd.addCallback(self._newCmdCallback)

    def _newCmdCallback(self, data, isCurrent, keyVar):
        """NewCmd callback.
        
        Synthesizes CmdQueued from:
        - NewCmd=internalId
        - CmdTime=float: TAI MJD (seconds)
        - Cmdr=str: commander
        - CmdrMID=int: the command ID number assigned by the commander
        - CmdActor=str: actor
        - cmdText=str

        Example:
        .hub 0 cmds i NewCmd=21619; CmdTime=1311803002.81; Cmdr="TU02.ROwen"; CmdrMID=1001;
            CmdrCID="TU02.ROwen"; CmdActor="keys"; CmdText="..."
        """
        if data[0] is None:
            return
        if not keyVar:
            return
        msgDict = keyVar.getMsgDict()
        if not msgDict:
            return
        dataDict = msgDict["data"]
        try:
            cmdQueuedData = [dataDict[key][0] for key in ("NewCmd", "CmdTime", "Cmdr", "CmdrMID", "CmdActor", "CmdText")]
        except Exception:
            sys.stderr.write("Could not parse cmds NewCmd line; dataDict=%s" % (dataDict,))
            return
        self.cmdQueued.set(cmdQueuedData, isCurrent=isCurrent)
        
        



if __name__ ==  "__main__":
    # confirm compilation
    model = getModel()
