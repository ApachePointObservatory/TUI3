# A virtual STV panel that allows the user to
# select buttons by clicking the mouse over
# the image of the STV.

# uses calls to stvadam to actually talk to the STV camera

# Created by James Battat
# February 1, 2006
# modified by CD Hoyle, June 2006

from tkinter import *
#import os
import RO.Wdg
import RO.Alg
import TUI.TUIModel
from . import pathStuff
import time
path = pathStuff.imagePath()

class StvFrontEnd:
    def __init__(self, parent,logWdg=None,tuiModel=None):

        self.myParent = parent
        self.logWdg = logWdg
        self.tuiModel = tuiModel
        self.state = 0
        
        ## added for tui version
        self.FuncCall = RO.Alg.GenericCallback
        self.tuiModel = TUI.TUIModel.getModel()
        self.dispatcher = self.tuiModel.dispatcher
        ## end added for tui version

        ########### DEFINE CONSTANTS FOR THE GUI ############
        self.imageFile=path+"stv.gif"
        self.xSize=640
        self.ySize=515
        
        ## define the locations of various regions of the STV 
        ## all are in pixels, with (0,0) the top left corner

        # the top left corner of text in the LCD screen
        self.textX0 = 400 ; self.textY0 = 178
        # corners of the rectangular background for the stv screen
        self.textBoxX0 = 394 ; self.textBoxY0 = 178
        self.textBoxX1 = 600 ; self.textBoxY1 = 217
        
        # corners of the "Focus" button
        self.focusX0 = 68  ; self.focusY0 = 282
        self.focusX1 = 110 ; self.focusY1 = 325

        # corners of the "Image" button
        self.imageX0 = 166 ; self.imageY0 = 280
        self.imageX1 = 208 ; self.imageY1 = 323

        # corners of the "Monitor" button
        self.monX0 = 264 ; self.monY0 = 280
        self.monX1 = 305 ; self.monY1 = 322

        # corners of the "Parameter" button
        self.paramX0 = 404 ; self.paramY0 = 279
        self.paramX1 = 446 ; self.paramY1 = 321

        # corners of the "Value" button
        self.valueX0 = 550 ; self.valueY0 = 280
        self.valueX1 = 591 ; self.valueY1 = 321

        # corners of the "Calibrate" button
        self.calibX0 = 35  ; self.calibY0 = 382
        self.calibX1 = 74  ; self.calibY1 = 422

        # corners of the "Track" button
        self.trackX0 = 35  ; self.trackY0 = 440
        self.trackX1 = 74  ; self.trackY1 = 482

        # corners of the "Display/Crosshairs" button
        self.dispX0 = 212  ; self.dispY0 = 379
        self.dispX1 = 254  ; self.dispY1 = 422

        # corners of the "File Ops" button
        self.fileX0 = 212  ; self.fileY0 = 438
        self.fileX1 = 254  ; self.fileY1 = 482

        # corners of the "Setup" button
        self.setupX0 = 405  ; self.setupY0 = 438
        self.setupX1 = 445  ; self.setupY1 = 479

        # corners of the "Interrupt" button
        self.interX0 = 550  ; self.interY0 = 438
        self.interX1 = 591  ; self.interY1 = 479
        
        # corners of up arrow
        self.upX0 = 462       ; self.upY0 = 358             # point of arrow
        self.upX1 = 454       ; self.upY1 = 366             # down/left
        self.upX2 = 459       ; self.upY2 = self.upY1
        self.upX3 = self.upX2 ; self.upY3 = 376
        self.upX4 = 465       ; self.upY4 = self.upY3
        self.upX5 = self.upX4 ; self.upY5 = 366
        self.upX6 = 470       ; self.upY6 = self.upY5
        self.upX7 = self.upX0 ; self.upY7 = self.upY0

        # corners of down arrow
        self.downX0 = 462         ; self.downY0 = 393         # point of arrow
        self.downX1 = self.upX6   ; self.downY1 = 385         # up/right
        self.downX2 = self.upX5   ; self.downY2 = self.downY1 
        self.downX3 = self.upX5   ; self.downY3 = 377
        self.downX4 = self.upX3   ; self.downY4 = self.downY3
        self.downX5 = self.upX3   ; self.downY5 = self.downY1
        self.downX6 = self.upX1   ; self.downY6 = self.downY1

        # corners of left arrow
        self.leftX0 = 493         ; self.leftY0 = 376         # point of arrow
        self.leftX1 = 502         ; self.leftY1 = 385         # down/right
        self.leftX2 = self.leftX1 ; self.leftY2 = 380         
        self.leftX3 = 514         ; self.leftY3 = self.leftY2
        self.leftX4 = self.leftX3 ; self.leftY4 = 373
        self.leftX5 = self.leftX1 ; self.leftY5 = self.leftY4
        self.leftX6 = self.leftX1 ; self.leftY6 = 368

        # corners of right arrow
        self.rightX0 = 536          ; self.rightY0 = self.leftY0 # pt. of arrow
        self.rightX1 = 527          ; self.rightY1 = self.leftY6 # up/left
        self.rightX2 = self.rightX1 ; self.rightY2 = self.leftY4
        self.rightX3 = 515          ; self.rightY3 = self.leftY4
        self.rightX4 = self.rightX3 ; self.rightY4 = self.leftY2
        self.rightX5 = self.rightX1 ; self.rightY5 = self.leftY2
        self.rightX6 = self.rightX1 ; self.rightY6 = self.leftY1

        
        self.stvTextColor="red"
        self.stvTextFont ="Courier 10 bold"
        #####################################################
        
        # create the canvas, size in pixels
        self.cc = Canvas(self.myParent,width=self.xSize, height=self.ySize, bg='black')

        # pack the canvas into a frame/form
        self.cc.pack(expand=YES, fill=BOTH)

        # load the .gif image file
        # put in your own gif file here, may need to add full path
        self.gif1 = PhotoImage(file=self.imageFile)

        # put gif image on canvas
        # pic's upper left corner (NW) on the canvas is at x=0 y=0
        self.cc.create_image(0, 0, image=self.gif1,
                             anchor=NW, tags="STVFRONT")

        self.cc.bind("<Button-1>", self.canvasEvent)
        self.cc.bind("<Control-Button-1>", self.canvasEvent2)

        self.stvTextBox=self.cc.create_rectangle(self.textBoxX0,self.textBoxY0,
                                                 self.textBoxX1,self.textBoxY1,
                                                 fill="white",tags="STVTEXT")
        self.stvText=self.cc.create_text(self.textX0,self.textY0,
                                         #text="THIS IS STV TEXT ROW1\n"+
                                         text="123456789012345678901234\n"+
                                         "STV TEXT ROW 2         x",
                                         anchor=NW, fill=self.stvTextColor,
                                         tags="STVTEXT",
                                         font=self.stvTextFont)
        self.focus=self.cc.create_rectangle(self.focusX0,self.focusY0,
                                            self.focusX1,self.focusY1,
                                            fill="black",
                                            tags="FOCUS")
        self.image=self.cc.create_rectangle(self.imageX0,self.imageY0,
                                            self.imageX1,self.imageY1,
                                            fill="black",
                                            tags="IMAGE")        
        self.monitor=self.cc.create_rectangle(self.monX0,self.monY0,
                                              self.monX1,self.monY1,
                                              fill="black",
                                              tags="MONITOR")        
        self.param=self.cc.create_rectangle(self.paramX0,self.paramY0,
                                            self.paramX1,self.paramY1,
                                            fill="black",
                                            tags="PARAMETER")
        self.value=self.cc.create_rectangle(self.valueX0,self.valueY0,
                                            self.valueX1,self.valueY1,
                                            fill="black",
                                            tags="VALUE")
        self.calib=self.cc.create_rectangle(self.calibX0,self.calibY0,
                                            self.calibX1,self.calibY1,
                                            fill="black",
                                            tags="CALIBRATE")
        self.track=self.cc.create_rectangle(self.trackX0,self.trackY0,
                                            self.trackX1,self.trackY1,
                                            fill="black",
                                            tags="TRACK")
        self.disp=self.cc.create_rectangle(self.dispX0,self.dispY0,
                                            self.dispX1,self.dispY1,
                                            fill="black",
                                            tags="DISPLAY")
        self.file=self.cc.create_rectangle(self.fileX0,self.fileY0,
                                            self.fileX1,self.fileY1,
                                            fill="black",
                                            tags="FILE")
        self.setup=self.cc.create_rectangle(self.setupX0,self.setupY0,
                                            self.setupX1,self.setupY1,
                                            fill="black",
                                            tags="SETUP")
        self.inter=self.cc.create_rectangle(self.interX0,self.interY0,
                                            self.interX1,self.interY1,
                                            fill="black",
                                            tags="INTERRUPT")

        self.up = self.cc.create_polygon(self.upX0,self.upY0,
                                         self.upX1,self.upY1,
                                         self.upX2,self.upY2,
                                         self.upX3,self.upY3,
                                         self.upX4,self.upY4,
                                         self.upX5,self.upY5,
                                         self.upX6,self.upY6,
                                         self.upX0,self.upY0,
                                         fill="white",
                                         outline="black",
                                         tags="UP")
        self.down = self.cc.create_polygon(self.downX0,self.downY0,
                                         self.downX1,self.downY1,
                                         self.downX2,self.downY2,
                                         self.downX3,self.downY3,
                                         self.downX4,self.downY4,
                                         self.downX5,self.downY5,
                                         self.downX6,self.downY6,
                                         self.downX0,self.downY0,
                                         fill="white",
                                         outline="black",
                                         tags="DOWN")
        self.left = self.cc.create_polygon(self.leftX0,self.leftY0,
                                           self.leftX1,self.leftY1,
                                           self.leftX2,self.leftY2,
                                           self.leftX3,self.leftY3,
                                           self.leftX4,self.leftY4,
                                           self.leftX5,self.leftY5,
                                           self.leftX6,self.leftY6,
                                           self.leftX0,self.leftY0,
                                           fill="white",
                                           outline="black",
                                           tags="LEFT")
        self.right = self.cc.create_polygon(self.rightX0,self.rightY0,
                                            self.rightX1,self.rightY1,
                                            self.rightX2,self.rightY2,
                                            self.rightX3,self.rightY3,
                                            self.rightX4,self.rightY4,
                                            self.rightX5,self.rightY5,
                                            self.rightX6,self.rightY6,
                                            self.rightX0,self.rightY0,
                                            fill="white",
                                            outline="black",
                                            tags="RIGHT")

# increment entries

        self.udWdg = RO.Wdg.IntEntry(self.myParent,
			defValue = 20,
			minValue = 1,
			maxValue = 10000,
                        helpText ='use Control-Click to move this many steps Up-Down',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=2
                )
        for i in range(0,9):self.udWdg.bind('<KeyPress-%d>' %i,self.FuncCall(self.setBackground,var=self.udWdg))
        
        self.udWdg.bind('<Return>',self.FuncCall(self.setCurrent,var=self.udWdg))
        self.udWdg.place(in_=self.cc,relx=0.645,rely=0.705)
        

        self.lrWdg = RO.Wdg.IntEntry(self.myParent,
			defValue = 20,
			minValue = 0,
			maxValue = 10000,
                        helpText ='use Control-Click to move this many steps Left-Right',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=2
                )
        for i in range(0,9):self.lrWdg.bind('<KeyPress-%d>' %i,self.FuncCall(self.setBackground,var=self.lrWdg))
        self.lrWdg.bind('<Return>',self.FuncCall(self.setCurrent,var=self.lrWdg))
        self.lrWdg.place(in_=self.cc,relx=0.87,rely=0.705)

        self.fmodeWdg = RO.Wdg.StrEntry(self.myParent,
                        helpText ='leave blank or enter focus mode #',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=3
                )
        self.fmodeWdg.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.fmodeWdg))
        self.fmodeWdg.bind('<Return>',self.FuncCall(self.setCurrent,var=self.fmodeWdg))
        self.fmodeWdg.place(in_=self.cc,relx=0.12,rely=0.585)

        self.button1 = Button(self.myParent,text="clear text",background='red',foreground='white')
        self.button1.bind("<Button-1>", self.clearTextEvent)
        self.button1.place(in_=self.cc,relx=0.75,rely=0.45)

## create a frame to store buttons for composite functions
        self.compositeFrame = Frame(self.myParent)
        self.compositeFrame.pack()

        gr = RO.Wdg.Gridder(self.compositeFrame)

        self.snapEntry = RO.Wdg.IntEntry(self.compositeFrame,
			defValue = 1,
			minValue = 1,
			maxValue = 1000,
                        helpText ='Length of exposure in seconds',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=3
                )

        self.snapButt = Button(self.compositeFrame,text="Snap",state='disabled')
        self.snapButt.bind("<Button-1>", self.snap)
        
        self.snapEntry.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.snapEntry))
        self.snapEntry.bind('<Return>',self.FuncCall(self.setCurrent,var=self.snapEntry))

        gr.gridWdg("Exposure length (s)", self.snapEntry,self.snapButt)

        self.saveEntry = RO.Wdg.IntEntry(self.compositeFrame,
			defValue = None,
			minValue = 0,
			maxValue = 1000,
                        helpText ='save to this register, leave blank to go to register selection page',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=3
                )

        self.saveButt = Button(self.compositeFrame,text="Save",state='disabled')
        self.saveButt.bind("<Button-1>", self.save)
        
        self.saveEntry.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.saveEntry))
        self.saveEntry.bind('<Return>',self.FuncCall(self.setCurrent,var=self.saveEntry))

        gr.gridWdg("Save to register ", self.saveEntry,self.saveButt)

        self.cursorXEntry = RO.Wdg.IntEntry(self.compositeFrame,
			defValue = 0,
			minValue = -5000,
			maxValue = 5000,
                        helpText ='cursor X position',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=5
                )

        self.cursorYEntry = RO.Wdg.IntEntry(self.compositeFrame,
			defValue = 0,
			minValue = -5000,
			maxValue = 5000,
                        helpText ='cursor Y position',
                        autoIsCurrent = False,
                        isCurrent = True,
                        width=5
                )

        self.cursorButt = RO.Wdg.Button(self.compositeFrame,
                                        text="Move",
                                        helpText ='move cursor to shown position',
                                        state='disabled')
        self.cursorButt.bind("<Button-1>", self.move)
        
        self.cursorXEntry.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.cursorXEntry))
        self.cursorXEntry.bind('<Return>',self.FuncCall(self.setCurrent,var=self.cursorXEntry))

        self.cursorYEntry.bind('<KeyPress>',self.FuncCall(self.setBackground,var=self.cursorYEntry))
        self.cursorYEntry.bind('<Return>',self.FuncCall(self.setCurrent,var=self.cursorYEntry))

        gr.gridWdg('')

        gr.gridWdg("Move to cursor position [x, y]", self.cursorXEntry,self.cursorYEntry)
        gr.gridWdg(self.cursorButt,row=-1,col=3)

    # this comes from a button push and has an associated event
    def clearTextEvent(self, event):
        self.clearText()
        
    # this does not come from an Event
    def clearText(self):
        self.cc.itemconfigure(self.stvText, text="")
        
    def canvasEvent(self, event):
        #print "Clicked in canvas at ", event.x, event.y
        closestItem = self.cc.find_closest(event.x, event.y)
        #print 'Nearest item is ', closestItem
        itemTags = self.cc.gettags(closestItem)
        exeString = itemTags[0]
        self.sendCommand(exeString)
        
        if itemTags[0]=="FOCUS":
            if self.fmodeWdg.get():
                val= ' ' + self.fmodeWdg.get()
            else: val = ''
            self.doCmd(' focus'+ val)
        elif itemTags[0]=="IMAGE":
            self.doCmd(' image')
        elif itemTags[0]=="MONITOR":
            self.doCmd('')
        elif itemTags[0]=="PARAMETER":
            self.doCmd(' parm')
        elif itemTags[0]=="VALUE":
            self.doCmd(' value')
        elif itemTags[0]=="CALIBRATE":
            self.doCmd('')
        elif itemTags[0]=="TRACK":
            self.doCmd('')
        elif itemTags[0]=="DISPLAY":
            self.doCmd(' hairs')
        elif itemTags[0]=="FILE":
            self.doCmd(' file')
        elif itemTags[0]=="SETUP":
            self.doCmd(' setup')
        elif itemTags[0]=="INTERRUPT":
            self.doCmd(' int')
        elif itemTags[0]=="UP":
            val='1'
            self.doCmd(' up ' + val)
        elif itemTags[0]=="DOWN":
            val='1'
            self.doCmd(' down ' + val)
        elif itemTags[0]=="LEFT":
            val='1'
            self.doCmd(' left ' + val)
        elif itemTags[0]=="RIGHT":
            val='1'
            self.doCmd(' right ' + val)
        elif itemTags[0]=="STVFRONT":
            self.doCmd('')
        elif itemTags[0]=="STVTEXT":
            self.doCmd('')
        else:
            self.doCmd('')

    def canvasEvent2(self, event):
        closestItem = self.cc.find_closest(event.x, event.y)
        itemTags = self.cc.gettags(closestItem)
        exeString = itemTags[0]
        self.sendCommand(exeString)
        
        if itemTags[0]=="UP":
            val=self.udWdg.get()
            self.doCmd(' up ' + val)
        elif itemTags[0]=="DOWN":
            val=self.udWdg.get()
            self.doCmd(' down ' + val)
        elif itemTags[0]=="LEFT":
            val=self.lrWdg.get()
            self.doCmd(' left ' + val)
        elif itemTags[0]=="RIGHT":
            val=self.lrWdg.get()
            self.doCmd(' right ' + val)
            
    def sendCommand(self, exeString):
        
        if self.state:
            stvOutput = exeString
            self.updateDisplay(stvOutput)
        else:
            stvOutput = "No Houston Control\n"+exeString
            self.updateDisplay(stvOutput)

    def updateDisplay(self, stvTextString):
        # clear the STV Display
        self.clearText()

        # send the string to the stvText box
        self.cc.itemconfigure(self.stvText, text=stvTextString,
                              fill=self.stvTextColor,
                              font=self.stvTextFont)

    def doCmd(self,cmd):

        act = 'apollo'
        cmd = 'houston stv' + cmd
        
        if self.state:
            cmdVar= RO.KeyVariable.CmdVar (
                    actor = act,
                    cmdStr = cmd,
                    dispatcher = self.dispatcher,
                    callFunc = self.callBack,
                    callTypes = RO.KeyVariable.AllTypes
                    )

            if self.logWdg != None:
                timeStr = time.strftime("%H:%M:%S", time.gmtime())
                me = ' ' + self.tuiModel.getCmdr()
                self.logWdg.addOutput('%s %s to %s %s %s \n' % (timeStr,me,act.upper(),str(cmdVar.cmdID),cmd))

        #cmdVar= RO.KeyVariable.CmdVar (
        #            actor = act,
        #            cmdStr = 'houston power',
        #            dispatcher = self.dispatcher,
        #            callFunc = self.callBack,
        #            callTypes = RO.KeyVariable.AllTypes
        #            )

    def callBack(self,msgType,msgDict,cmdVar):

                endStr = ''
                
                if msgType in RO.KeyVariable.FailTypes:
                    cat="Error"
                elif msgType == 'w' or msgType == '>':
                    cat="Warning"
                else:
                    cat = "Information"

                if msgType == ':':
                    endStr = ' Finished '

                if msgType == '>':
                    endStr = ' Queued '
                    
                timeStr = time.strftime("%H:%M:%S", time.gmtime())
                    
                self.logWdg.addOutput(timeStr+endStr+msgDict.get('msgStr')+'\n',category=cat)

    def setBackground(self, evt, var):
            var.setIsCurrent(False)

    def setCurrent(self, evt, var):
            var.setIsCurrent(True)

    def snap(self, evt):
            val = self.snapEntry.get()
            self.doCmd(' snap ' + val)

    def save(self, evt):
            val = self.saveEntry.get()
            if val: val = ' '+ val
            self.doCmd(' save' + val)

    def move(self, evt):
            x = self.cursorXEntry.get()
            y = self.cursorYEntry.get()
            self.doCmd(' cursor ' + x + ' ' +y)
            
if __name__=="__main__":
    root  = Tk()
    stvfrontend=StvFrontEnd(root)
    
    # run it ...
    root.mainloop()
