#displays apo weather in TUI
## dw=displayweath
# right now i just define dummy variables and display them
# in a tk text window.

## TO DO:
# update "these data are .... sec old"
# Primary mirror Temp
# Secondary Mirror Temp
# Air temp (dome air?)
# store the 15 minute minimum temperature and gust speed and dir
# Improve the alignment of the data...

"""
Displays APO's weather information
"""

from tkinter import *
import re
from . import wx
import time

class DisplayWeath:
    keyval = re.compile("([^\s;]*=[^\s;]*)") #ignore the ;keyval

    def putText(self, index, text):
        # deletes any text already present
        # then inserts the new text

        # make sure that the text box is editable
        self.tt.config(state=NORMAL)

        # compute index2 by adding len(text) to index
        rowCol = index.split('.')
        rowNumber = int(rowCol[0])
        colNumber = int(rowCol[1])
        index2 = str(rowNumber)+"."+str(colNumber+len(text))
        
        # delete old text
        self.tt.delete(index,index2=index2)
        # add new text
        self.tt.insert(index, text)

        # make the window read-only
        self.tt.config(state=DISABLED)


    def __init__(self, parent):
        self.myParent=parent

        ## define window geometry
        self.height = 22
        self.width  = 80

        ## create a text widget
        self.tt = Text(self.myParent, bg="white", fg="black",
                       height=self.height,width=self.width,
                       font=("Courier","12"))

        ## stuff the text widget into the Tk window.
        self.tt.pack()

        # initialize all lines in the text widget
        # create a blank string that is as wide as the widget
        blankString = " "
        for ii in range(self.width-2):
            blankString = blankString+" "
        # insert the blank string into the text widget
        for ii in range(self.height-1):
            self.tt.insert(CURRENT,blankString+"\n")

        #########################
        ### Define the labels ###
        #########################
        self.labels = {'title':['2.30','APO Weather Status'],
                       'status':['4.24','These data are    seconds old:'],
                       'airSect':["6.2",'Air:'],
                       'pressLabel':["7.5",    'Pressure            inHg'],
                       'humidLabel':["8.5",    'Humidity            %   '],
                       'tempLabel':["9.5",     'Temp                C   '],
                       'dewLabel':["10.5",     'Dewpoint            C   '],
                       'diffLabel':["11.5",    'Diff                C   '],
                       '15minMinLabel':["12.5",'15 min Min          C   '],
                       'dustSect':["14.2","Dust, particles/0.1 cu.ft:"],
                       'tower3uLabel':["15.5","Tower 0.3u"],
                       'tower1uLabel':["16.5","Tower 1.0u"],
                       'encl3uLabel':["15.40","3.5m Encl. 0.3u"],
                       'encl1uLabel':["16.40","3.5m Encl. 1.0u"],
                       'windSect':["18.2","Wind:"],
                       'gustSect':["18.37","Wind, last 15 minutes:"],
                       'speedLabel':["19.5",'Speed               mph'],
                       'dirLabel':["20.5",  'Dir                 degrees'],
                       'gustSpeedLabel':["19.40",'Gust Speed            mph'],
                       'gustDirLabel':["20.40",  'Gust Dir              degrees'],
                       'teleSect':['6.37',      "3.5m Telescope:"],
                       'structLabel':['7.40',   "Structure             C"],
                       'primaryLabel':['8.40',  "Primary (front)       C"],
                       'secondaryLabel':['9.40',"Secondary (avg)       C"],
                       'airLabel':['10.40',     "Air                   C"]
                       }
        ##########################
        ### DISPLAY THE LABELS ###
        ##########################
        for key in list(self.labels.keys()):
            idxValue = self.labels[key]
            self.putText(idxValue[0],idxValue[1])


        ### DEFINE THE DATA ###
        self.defVal = '-999'
        self.lastTime = time.time()
        # Format looks like: "2006 Feb 20  23:18:15"
        self.dateFormat = "%Y %b %d  %H:%M:%S"
        self.defDate = time.strftime(self.dateFormat,
                                     time.localtime(self.lastTime))
        self.data = {'date':['3.28',self.defDate],
                     'staleSeconds':['4.39','XX'],
                     'pressure':['7.18',self.defVal],
                     'humidity':['8.18',self.defVal],
                     'airtemp':['9.18',self.defVal],
                     'dewpoint':['10.18',self.defVal],
                     'diff':['11.18',self.defVal],
                     'fifteenMinMin':['12.18',self.defVal],
                     'dusta':['15.18',self.defVal], # tower 0.3u
                     'dustb':['16.18',self.defVal], # tower 1.0u
                     'dustc':['15.59',''], # 3.5m Encl. 0.3u
                     'dustd':['16.59',''], # 3.5m Encl. 1.0u
                     'winds':['19.18',self.defVal],
                     'windd':['20.18',self.defVal],
                     'gusts':['19.56',self.defVal],
                     'gustd':['20.56',self.defVal],                     
                     'structtemp':['7.56',self.defVal],
                     'PrimF_BFTemp':['8.56',self.defVal],
                     'sectemp':['9.56',self.defVal],
                     'air':['10.56',self.defVal]
                     }

        for key in list(self.data.keys()):
            idxValue = self.data[key]
            self.putText(idxValue[0],idxValue[1])

        # update the data!
        outstring = self.updateData()
        print(outstring)
        
    #def updateData(self,parent,key,val):
    #def updateData(self,parent):
    def updateData(self):
        weatherData = wx.weather()

        # get all key/val pairs
        for kv in self.keyval.findall(weatherData):
            # parse each keyval into (k,v)
            (k,v) = kv.split('=',1)
            #if key exists in self.data then update it
            if k in self.data:
                # update data dictionary
                self.data[k][1]=v
                # display the new weather info
                self.putText(self.data[k][0],self.data[k][1])
                print(k, ' --> ', v)
            # update the time variable
            if k=="timeStamp":
                print('found time string')
                timeString = time.strftime(self.dateFormat,
                                           time.localtime(int(v)))
                print('storing date:')
                self.data['date'][1] = timeString
                print('putting text: ', self.data['date'][1])
                self.putText(self.data['date'][0],self.data['date'][1])

        # update the "Diff" variable
        newDiff = float(self.data['airtemp'][1]) - float(self.data['dewpoint'][1])
        self.data['diff'][1] = str(newDiff)
        print('newDiff = ', self.data['diff'][1])
        self.putText(self.data['diff'][0],self.data['diff'][1])
                
        #for key in self.data.keys():
            #print 'data[',key,'] --> ', self.data[key]

        return weatherData
    
if __name__ == "__main__":

    root = Tk()
    dw   = DisplayWeath(root)
    root.mainloop()
    #time.sleep(3)
    #while (1):
        #outstring = dw.updateData()
        #print 'outstring = '
        #print outstring
        #print ''
        #time.sleep(1)
        #root.mainloop()
