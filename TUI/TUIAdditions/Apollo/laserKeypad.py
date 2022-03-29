# A virtual Laser Remote Box Keypad Emulator
# that allows the user to
# select buttons by clicking the mouse over
# the image of the keypad.

# Created by James Battat
# February 8, 2006
# modified by CD Hoyle May 13, 2006

from tkinter import *
import os
import RO.Wdg
import RO.Alg
import TUI.TUIModel
from . import pathStuff
import time
path = pathStuff.imagePath()

class MyApp:
    def __init__(self, parent,logWdg=None,tuiModel=None):

        self.myParent = parent
        self.logWdg=logWdg
        self.tuiModel = tuiModel
        self.state = 0

        self.FuncCall = RO.Alg.GenericCallback

        self.tuiModel = TUI.TUIModel.getModel()
        self.dispatcher = self.tuiModel.dispatcher

        ########### DEFINE CONSTANTS FOR THE GUI ############
        self.imageFile=path+"keypad.gif"
        self.xSize=348
        self.ySize=419

        # Define LED parameters
        self.LED_ON  = ['red','green','green','green']
        self.LED_OFF   = 'black'
        self.LED_DEFAULT = self.LED_OFF
        # Define the diameter of the LED circles
        self.LEDDiameter = 20  # pixels

        # define color of rectangle outlines
        self.outlineColor = "black"
        
        ## define the locations of various regions of the STV 
        ## all are in pixels, with (0,0) the top left corner

        # the top left corner of text in the LCD screen
        self.textX0 = 83 ; self.textY0 = 56
        # corners of the rectangular background for the LCD screen
        self.textBoxX0 = 80 ; self.textBoxY0 = 52
        self.textBoxX1 = 290 ; self.textBoxY1 = 105
        # corners of gray box to hide underlying buttons...
        self.buttonHideBoxX0 = 22 ; self.buttonHideBoxY0 = 160
        self.buttonHideBoxX1 = 335; self.buttonHideBoxY1 = 378
        self.bkgColor='#6D6F6C'
        self.DARK_GRAY = "#667172"
        self.DARK_GREEN = "#195952"

        # Top Left of  "Charging" LED
        self.chargeLEDX = 18; self.chargeLEDY = 125

        # Top Left of  "End Of Charge (EOC)" LED
        self.eocLEDX = 96; self.eocLEDY = 125

        # Top Left of  "Shutter Open" LED
        self.shutterLEDX = 176; self.shutterLEDY = 125

        # Top Left of  "Q-Switch" LED
        self.qswitchLEDX = 254; self.qswitchLEDY = 125

        # width and height of button
        self.dx = 50 ; self.dy = 50
        # row and column locations (center pixel)
        self.row1 = 190
        self.row2 = self.row1+self.dy
        self.row3 = self.row1+self.dy*2
        self.row4 = self.row1+self.dy*3        
        self.row6 = self.row1+self.dy*5

        self.col1 = 50
        self.col2 = self.col1+self.dx
        self.col3 = self.col1+self.dx*2
        self.col4 = self.col1+self.dx*3        
        self.col6 = self.col1+self.dx*5

        ### Row 1 ###
        # Center of the "Program Up" button
        self.pgmUpX0 = self.col1 ; self.pgmUpY0 = self.row1

        # Center of the "Shutter" button
        self.shutterX0 = self.col3 ; self.shutterY0=self.row1

        # Center of the "Q-Switch On/Off" button
        self.qswitchX0 = self.col4 ; self.qswitchY0=self.row1

        # Center of the "Parameter Up" button
        self.paramUpX0 = self.col2 ; self.paramUpY0 = self.row1

        ### ROW 2 ###
        # Center of the "Program Down" button
        self.pgmDnX0 = self.col1 ; self.pgmDnY0 = self.row2

        # Center of the "Parameter Down" button
        self.paramDnX0 = self.col2 ; self.paramDnY0 = self.row2

        # Center of the "Remote/Local" button
        self.remoteX0 = self.col3 ; self.remoteY0 = self.row2

        # Center of the "Auto/Manual" button
        self.autoX0 = self.col4 ; self.autoY0 = self.row2

        ### ROW 3 ###
        # Center of the "Store" button
        self.storeX0 = self.col1 ; self.storeY0 = self.row3

        # Center of the "Parameter Select" button
        self.paramSelX0 = self.col2 ; self.paramSelY0 = self.row3

        # Center of the "Charge" button
        self.chargeX0 = self.col3 ; self.chargeY0 = self.row3

        # Center of the "Start" button
        self.startX0 = self.col4 ; self.startY0 = self.row3

        ### ROW 4 ###
        # Center of the "Activate" button
        self.activX0 = self.col1 ; self.activY0 = self.row4

        # Center of the "Reset" button
        self.resetX0 = self.col2 ; self.resetY0 = self.row4

        # Center of the "Fire" button
        self.fireX0 = self.col3 ; self.fireY0 = self.row4

        # Center of the "Stop" button
        self.stopX0 = self.col4 ; self.stopY0 = self.row4

        # rotation buttons
        self.oneCWX0  = self.col6 ; self.oneCWY0  = self.row1
        self.oneCCWX0 = self.col6 ; self.oneCCWY0 = self.row2
        self.twoCWX0  = self.col6 ; self.twoCWY0  = self.row3
        self.twoCCWX0 = self.col6 ; self.twoCCWY0 = self.row4
        
        self.keypadTextColor="red"
        self.keypadTextFont ="Courier 12 bold"
        #####################################################
        
        # create the canvas, size in pixels
        self.cc = Canvas(self.myParent,width=self.xSize, height=self.ySize, bg='black')

        # pack the canvas into a frame/form
        #self.cc.pack(expand=YES, fill=BOTH)
        self.cc.pack()

        # load the .gif image file
        # put in your own gif file here, may need to add full path
        self.gif1 = PhotoImage(file=self.imageFile)

        # put gif image on canvas
        # pic's upper left corner (NW) on the canvas is at x=0 y=0
        self.cc.create_image(0, 0, image=self.gif1,
                             anchor=NW, tags="KEYPADCLICK")

        self.cc.bind("<Button-1>", self.canvasEvent)

        self.keypadTextBox=self.cc.create_rectangle(self.textBoxX0,self.textBoxY0,
                                                 self.textBoxX1,self.textBoxY1,
                                                 fill="white",tags="KEYPADTEXT")
        self.keypadText=self.cc.create_text(self.textX0,self.textY0,
                                         #text="THIS IS STV TEXT ROW1\n"+
                                         text="12345678901234567890\n12345678901234567890",
                                         anchor=NW, fill=self.keypadTextColor,
                                         tags="KEYPADTEXT",
                                         font=self.keypadTextFont)

        self.buttonHideBox = self.cc.create_rectangle(self.buttonHideBoxX0,
                                                      self.buttonHideBoxY0,
                                                      self.buttonHideBoxX1,
                                                      self.buttonHideBoxY1,
                                                      fill=self.bkgColor,
                                                      outline=self.bkgColor)

        self.chargeLED=self.cc.create_oval(self.chargeLEDX,self.chargeLEDY,
                                           self.chargeLEDX+self.LEDDiameter,
                                           self.chargeLEDY+self.LEDDiameter,
                                           fill=self.LED_DEFAULT,
                                           outline=self.LED_DEFAULT,
                                           tags="LED_CHARGING")
        self.eocLED=self.cc.create_oval(self.eocLEDX,self.eocLEDY,
                                           self.eocLEDX+self.LEDDiameter,
                                           self.eocLEDY+self.LEDDiameter,
                                           fill=self.LED_DEFAULT,
                                           outline=self.LED_DEFAULT,
                                           tags="LED_EOC")
        self.shutterLED=self.cc.create_oval(self.shutterLEDX,self.shutterLEDY,
                                           self.shutterLEDX+self.LEDDiameter,
                                           self.shutterLEDY+self.LEDDiameter,
                                           fill=self.LED_DEFAULT,
                                           outline=self.LED_DEFAULT,
                                           tags="LED_SHUTTER")
        self.qswitchLED=self.cc.create_oval(self.qswitchLEDX,self.qswitchLEDY,
                                           self.qswitchLEDX+self.LEDDiameter,
                                           self.qswitchLEDY+self.LEDDiameter,
                                           fill=self.LED_DEFAULT,
                                           outline=self.LED_DEFAULT,
                                           tags="LED_QSWITCH")

        ## create a blank box and fill it with buttons
        self.mainPanelX0 = 24  ; self.mainPanelY0 = 165
        self.mainPanelX1 = 228 ; self.mainPanelY1 = 365
        self.mainPanel=self.cc.create_rectangle(self.mainPanelX0,
                                                self.mainPanelY0,
                                                self.mainPanelX1,
                                                self.mainPanelY1,
                                                fill=self.DARK_GRAY,
                                                outline=self.DARK_GREEN,
                                                width=4,
                                                tags="MAIN_PANEL")
        
        ### ROW 1 ###
        self.programUpGIF = PhotoImage(file=path+"program_up.gif")
        self.pgmUp=self.cc.create_image(self.pgmUpX0,self.pgmUpY0,
                                        image=self.programUpGIF,
                                        tags="PROGRAM_UP")
        self.parameterUpGIF = PhotoImage(file=path+"parameter_up.gif")
        self.parameterUp=self.cc.create_image(self.paramUpX0,self.paramUpY0,
                                              image=self.parameterUpGIF,
                                              tags="PARAMETER_UP")
        self.shutterGIF = PhotoImage(file=path+"shutter.gif")
        self.shutter=self.cc.create_image(self.shutterX0,self.shutterY0,
                                          image=self.shutterGIF,
                                          tags="SHUTTER")
        self.qswitchGIF = PhotoImage(file=path+"qswitch.gif")
        self.qswitch=self.cc.create_image(self.qswitchX0,self.qswitchY0,
                                          image=self.qswitchGIF,
                                          tags="QSWITCH")
        ### ROW 2 ###
        self.programDnGIF = PhotoImage(file=path+"program_down.gif")
        self.pgmDn=self.cc.create_image(self.pgmDnX0,self.pgmDnY0,
                                        image=self.programDnGIF,
                                        tags="PROGRAM_DOWN")
        self.parameterDnGIF = PhotoImage(file=path+"parameter_down.gif")
        self.parameterDn=self.cc.create_image(self.paramDnX0,self.paramDnY0,
                                              image=self.parameterDnGIF,
                                              tags="PARAMETER_DOWN")
        self.remoteGIF = PhotoImage(file=path+"remote_local.gif")        
        self.remote=self.cc.create_image(self.remoteX0,self.remoteY0,
                                         image=self.remoteGIF,
                                         tags="REMOTE_LOCAL")
        self.autoGIF = PhotoImage(file=path+"auto_manual.gif")        
        self.auto=self.cc.create_image(self.autoX0,self.autoY0,
                                       image=self.autoGIF,
                                       tags="AUTO_MANUAL")
        ### ROW 3 ###
        self.storeGIF = PhotoImage(file=path+"store.gif")
        self.store=self.cc.create_image(self.storeX0,self.storeY0,
                                        image=self.storeGIF,
                                        tags="STORE")
        self.paramSelGIF = PhotoImage(file=path+"parameter_select.gif")
        self.paramSel=self.cc.create_image(self.paramSelX0,self.paramSelY0,
                                        image=self.paramSelGIF,
                                        tags="PARAMETER_SELECT")
        self.chargeGIF = PhotoImage(file=path+"charge.gif")
        self.charge=self.cc.create_image(self.chargeX0,self.chargeY0,
                                        image=self.chargeGIF,
                                        tags="CHARGE")
        self.startGIF = PhotoImage(file=path+"start.gif")
        self.start=self.cc.create_image(self.startX0,self.startY0,
                                        image=self.startGIF,
                                        tags="START")
        ### ROW 4 ###
        self.activGIF = PhotoImage(file=path+"activate.gif")
        self.activ=self.cc.create_image(self.activX0,self.activY0,
                                        image=self.activGIF,
                                        tags="ACTIVATE")
        self.resetGIF = PhotoImage(file=path+"reset.gif")
        self.reset=self.cc.create_image(self.resetX0,self.resetY0,
                                        image=self.resetGIF,
                                        tags="RESET")
        self.fireGIF = PhotoImage(file=path+"fire.gif")
        self.fire=self.cc.create_image(self.fireX0,self.fireY0,
                                        image=self.fireGIF,
                                        tags="FIRE")
        self.stopGIF = PhotoImage(file=path+"stop.gif")
        self.stop=self.cc.create_image(self.stopX0,self.stopY0,
                                        image=self.stopGIF,
                                        tags="STOP")

        ## create an empty box with a border
        self.mainPanelX0 = 24  ; self.mainPanelY0 = 165
        self.mainPanelX1 = 228 ; self.mainPanelY1 = 365
        self.mainPanel=self.cc.create_rectangle(self.mainPanelX0,
                                                self.mainPanelY0,
                                                self.mainPanelX1,
                                                self.mainPanelY1,
                                                #fill=self.DARK_GRAY,
                                                fill='',
                                                outline=self.DARK_GREEN,
                                                width=4,
                                                tags="MAIN_PANEL")


        ## rotation buttons
        self.oneCWGIF = PhotoImage(file=path+"1_cw.gif")
        self.stop=self.cc.create_image(self.oneCWX0,self.oneCWY0,
                                       image=self.oneCWGIF,
                                       tags="1_CW")
        self.oneCCWGIF = PhotoImage(file=path+"1_ccw.gif")
        self.stop=self.cc.create_image(self.oneCCWX0,self.oneCCWY0,
                                       image=self.oneCCWGIF,
                                       tags="1_CCW")
        self.twoCWGIF = PhotoImage(file=path+"2_cw.gif")
        self.stop=self.cc.create_image(self.twoCWX0,self.twoCWY0,
                                       image=self.twoCWGIF,
                                       tags="2_CW")
        self.twoCCWGIF = PhotoImage(file=path+"2_ccw.gif")
        self.stop=self.cc.create_image(self.twoCCWX0,self.twoCCWY0,
                                       image=self.twoCCWGIF,
                                       tags="2_CCW")

        ## create a border for the rotation buttons
        self.rotPanelX0 = 270 ; self.rotPanelY0 = 165
        self.rotPanelX1 = 330 ; self.rotPanelY1 = 368
        self.rotPanel=self.cc.create_rectangle(self.rotPanelX0,
                                               self.rotPanelY0,
                                               self.rotPanelX1,
                                               self.rotPanelY1,
                                               #fill=self.DARK_GRAY,
                                               outline=self.DARK_GREEN,
                                               width=4,
                                               tags="ROTATION_PANEL")


        ## create a frame to store buttons for composite functions
        self.compositeFrame = Frame(self.myParent)
        self.compositeFrame.pack()

        self.b2 = Button(self.compositeFrame, command= self.FuncCall(self.doCmd,'keyoff'))
        self.b2.configure(text="KeyOff",state='disabled')
        self.b2.pack(side=LEFT)
        self.b3 = Button(self.compositeFrame, command=self.FuncCall(self.doCmd,'keyon'))
        self.b3.configure(text="KeyOn",state='disabled')
        self.b3.pack(side=LEFT)
        self.b4 = Button(self.compositeFrame, command=self.FuncCall(self.doCmd,'keycycle'))
        self.b4.configure(text="KeyCycle",state='disabled')
        self.b4.pack(side=LEFT)

    # this comes from a button push
    def clearTextEvent(self):
        #print "Clear text requested"
        self.clearText()

    # this does not come from an Event
    def clearText(self):
        #print "clearing text"
        self.cc.itemconfigure(self.keypadText, text="")
        
    def canvasEvent(self, event):
        #print "Clicked in canvas at ", event.x, event.y
        closestItem = self.cc.find_closest(event.x, event.y)
        #print 'Nearest item is ', closestItem
        itemTags = self.cc.gettags(closestItem)
        #print "   its tags are ", itemTags
        #print "   first tag is ", itemTags[0]
        exeString = "BLANKBLANKBLANK"
        ### ROW 1 ###
        if itemTags[0]=="PROGRAM_UP":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.doCmd('code 11')
        elif itemTags[0]=="PARAMETER_UP":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 12')
        elif itemTags[0]=="SHUTTER" or itemTags[0]=="LED_SHUTTER":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 13')
        elif itemTags[0]=="QSWITCH":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 14')
        ### ROW 2 ###
        elif itemTags[0]=="PROGRAM_DOWN":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 21')
        elif itemTags[0]=="PARAMETER_DOWN":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 22')
        elif itemTags[0]=="REMOTE_LOCAL":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 23')
        elif itemTags[0]=="AUTO_MANUAL":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 24')
        ### ROW 3 ###
        elif itemTags[0]=="STORE":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 31')
        elif itemTags[0]=="PARAMETER_SELECT":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 32')
        elif itemTags[0]=="CHARGE":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 33')
        elif itemTags[0]=="START":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('start')
            
        ### ROW 4 ###
        elif itemTags[0]=="ACTIVATE":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 41')
        elif itemTags[0]=="RESET":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 42')
        elif itemTags[0]=="FIRE":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 43')
        elif itemTags[0]=="STOP":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('stop')
        ## ROTATION BUTTONS ##
        elif itemTags[0]=="1_CW":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('cw')
        elif itemTags[0]=="1_CCW":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('ccw')
        elif itemTags[0]=="2_CW":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 35')
        elif itemTags[0]=="2_CCW":
            exeString = itemTags[0]
            self.sendCommand(exeString)
            self.sendCommand(exeString)
            self.doCmd('code 45')
        elif itemTags[0]=="KEYPAD CLICK":            
            #print "KEYPADFRONT: Ignoring"
            exeString = "KEYPADCLICK: Ignoring"
            self.sendCommand(exeString)
        elif itemTags[0]=="KEYPADTEXT":
            #print "KEYPADTEXT: Ignoring"
            exeString = "KEYPADLICK: Ignoring"
            self.sendCommand(exeString)
        else:
            #print "ERROR: UNRECOGNIZED CLICK LOCATION"
            exeString = "ERROR: UNRECOGNIZED \n CLICK LOCATION"
            self.sendCommand(exeString)

    def sendCommand(self, exeString):
        if self.state:
            stvOutput = exeString
            self.updateDisplay(stvOutput)
        elif self.state==0:
            stvOutput = "No Houston Control\n"+exeString
            self.updateDisplay(stvOutput)

    def updateDisplay(self, keypadTextString):
        # clear the STV Display
        self.clearText()

        # send the string to the keypadText box
        self.cc.itemconfigure(self.keypadText, text=keypadTextString,
                              fill=self.keypadTextColor,
                              font=self.keypadTextFont)

    def doCmd(self,cmd):

        act = 'apollo'
        cmd = 'houston laser ' + cmd
        
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
                me = ' '+self.tuiModel.getCmdr()
                self.logWdg.addOutput('%s %s to %s %s %s \n' % (timeStr,me,act.upper(),str(cmdVar.cmdID),cmd))

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
                    
                self.logWdg.addOutput(endStr+msgDict.get('msgStr')+'\n',category=cat)
        
if __name__=="__main__":
    root  = Tk()
    myapp=MyApp(root)
    
    # run it ...
    root.mainloop()
