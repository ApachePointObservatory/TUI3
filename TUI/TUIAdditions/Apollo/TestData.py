#!/usr/local/bin/python
"""Apollo test data.

Reads a simulation file, converts each line to keyword/value format
and dispatches it.

History:
2005-07-21 CDH - updated for Houston data format
2005-02-17 ROwen
"""
import numpy as num
import TUI.TUIModel
from . import ApolloModel

tuiModel = TUI.TUIModel.getModel(True)
apModel = ApolloModel.getModel()
startFlag = False
nshots = 0
#nmax = 5000

#testfile = "/Users/Lou/Documents/Wellesley/Acad/lunarRanging/test.txt"
#testfile = r'/Users/jbattat/Library/Application Support/TUIAdditions/Apollo/data/test.txt'
#f = open(testfile,'w')
#to_write = []

def dispatch(replyStr, cmdID=0):
	"""Dispatch the reply string.
	The string should start from the message type character
	(thus program ID, actor and command ID are added).
	"""
	global tuiModel, apModel
	dispatcher = tuiModel.dispatcher
	cmdr = tuiModel.getCmdr()
	
	msgStr = "%s %d %s %s" % (cmdr, cmdID, apModel.actor, replyStr)
	tuiModel.dispatcher.doRead(None, msgStr)

def fileParseIter(fileName,startNum):
        
        global startFlag
        global nshots
        
        fobj = file(fileName, "rU")
        for line in fobj:
            
            if startNum != None:
                startChar = len(startNum)
                nblanks = 8 - startChar
                blankStr = ''
                for i in range(nblanks):blankStr+=' '
                startStr = "fid0"+blankStr+"%s" % startNum
                #print startStr
                if startNum and startStr in line:    #!
                    startFlag=True      #!

            if startFlag == True or startNum == None:   #!

                dataList = line.split()
                    
		if not dataList:
			continue

		msgCode = dataList[0]
		
		keyword = {
			"fid!": "OldFid",
			"lun!": "Lunar",
                        "fid0": "Fiducial",
                        "lun0": "Lunar",
                        "str0": "Stare",
                        "gdo0": "guideOff",
                        "tmp0": "Temps",
                        "flw0": "Flow",
                        "pow0": "Power",
                        "par0": "Par",
                        "drk0": "Dark",
                        "flt0": "Flat",
                        "gps0": "GPS",
                        "rem": "rem",
		}.get(msgCode)

		if keyword == "OldFid":
			# format channel dictionary
			chanData = "\"%s\"" % (", ".join(dataList[9:]))
			# format reply string
			replyList = [dataList[ind] for ind in (1, 2, 6, 7, 8)]
			replyList.append(chanData)
			replyStr = ": %s=%s" % (keyword, ", ".join(replyList))
                if keyword == "Fiducial":
			# format channel dictionary
			chanData = "\"%s\"" % (", ".join(dataList[10:]))
			# format reply string
			replyList = [dataList[ind] for ind in (1, 2, 6, 7, 8, 9, 3)]
			replyList.append(chanData)
			replyStr = ": %s=%s" % (keyword, ", ".join(replyList))
		elif keyword == "Lunar":
                        nshots+=1
			# format channel dictionary
			chanData = "\"%s\"" % (", ".join(dataList[9:]))
			# format reply string
			replyList = [dataList[ind] for ind in (1, 2, 6, 7, 8, 3)]
			replyList.append(chanData)
			replyStr = ": %s=%s" % (keyword, ", ".join(replyList))
                        #to_write.append(replyStr)
		elif keyword == "Stare":
			replyList = [dataList[1+ind] for ind in range(16)]
			replyStr = ": %s=%s" % (keyword, ", ".join(replyList))
		elif keyword == "Dark":
			replyList = [dataList[2+ind] for ind in range(16)]
			replyStr = ": %s=%s" % (keyword, ", ".join(replyList))
		elif keyword == "Flat":
			replyList = [dataList[2+ind] for ind in range(16)]
			replyStr = ": %s=%s" % (keyword, ", ".join(replyList))
		elif keyword == "guideOff":
			# format reply string
			replyList = [dataList[1+ind] for ind in range(2)]
			replyStr = ": %s=%s" % (keyword, ", ".join(replyList))
		elif keyword == "Temps":
			continue
		elif keyword == "Flow":
                        continue
                elif keyword == "Power":
                        continue
                elif keyword == "Par":
                        replyStr = ': '+' '.join(dataList[1:])
                        #print replyStr
                elif keyword == "GPS":
                        replyStr = ': '+'; '.join(dataList[1:])
                        replyStr = replyStr[:-1]
                elif keyword == "rem":
                        continue
                elif keyword == None:
                        replyStr = ': '+'; '.join(dataList[0:])
		else:
			continue

		yield replyStr

def animate(dataIter,n,nmax):

        global nshots

        #n=nshots
        
        try:
            data = next(dataIter)
        except StopIteration:
            return

        #print n, nmax, n == 10
    
        dispatch(data)
        #n+=1
        if nshots == nmax: return
        tuiModel.tkRoot.after(1, animate, dataIter, n,nmax)
        #tuiModel.tkRoot.after(5, animate, dataIter, n,nmax)
        #f.write(str(to_write))
        #f.close
        
def dispatchFile(fileName,startNum,n):
        global nshots
        nshots = 0
        nmax = int(n)
	dataIter = fileParseIter(fileName,startNum)
	animate(dataIter,0,nmax)
