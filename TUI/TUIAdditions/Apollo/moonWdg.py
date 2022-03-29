#!/usr/local/bin/python
"""Display retroreflector locations and slew telescope.

History """
import tkinter
#import Numeric
import numpy as num
from . import moontarg
from . import mooncoords
import os
import re
import time
import math
import RO.Wdg
import TUI.TUIModel

# kluge for now
from . import pathStuff

coords = mooncoords.Finders()
retros = mooncoords.Retros()
pair = re.compile("\(\s*(\S+)\s*,\s*(\S+)\s*\)")
trio = re.compile("\(\s*(\S+\d+)\s*,\s*(\S+\d+)\s*,\s*(\S+\d+)\s*\)")
time_now = time.time()
time_utc = time_now
feature = "CENTER"
track_cmd = ""
new_track_cmd = ""
offset_cmd = ""
pi = num.pi
dtr = pi/180.0

class moonWdg(tkinter.Frame):
      def __init__(self,master,logWdg=None,tuiModel=None):

        tkinter.Frame.__init__(self, master, logWdg=None)

        self.logWdg=logWdg
        self.tuiModel = tuiModel

        self.tuiModel = TUI.TUIModel.getModel()
        self.dispatcher = self.tuiModel.dispatcher

        phaseframe = tkinter.Frame(self)
        phaseframe.pack(side='left')

        mcframe = tkinter.Frame(phaseframe)
        mcframe.pack()

        mctrlframe = tkinter.Frame(phaseframe)
        mctrlframe.pack()
          
        ctrlframe = tkinter.Frame(self)
        ctrlframe.pack()

        targframe = tkinter.Frame(self)
        targframe.pack()

        self.targ_select = ""
        self.targname = tkinter.StringVar()
        self.targname.set("Apollo 11")

        infoframe = tkinter.Frame(self)
        infoframe.pack()
        
        self.pointer_string = ""
        self.pointer_info = tkinter.Label(infoframe,text=self.pointer_string)
        self.pointer_info.pack()

        self.target_string = "Target Selection: "
        self.targ_info = tkinter.Label(infoframe,text=self.target_string)
        self.targ_info.pack()

        self.track_string = "Now Tracking: "
        self.track_info = tkinter.Label(infoframe,text=self.track_string)
        self.track_info.pack()

        libx=0.0
        liby=0.0
        libs_string = "Libration: (%6.2f,%6.2f)" % (libx,liby)
        self.libs_info = tkinter.Label(infoframe,text=libs_string)
        self.libs_info.pack()

        lib_string = "Total Libration: %6.2f" % math.sqrt(libx*libx + liby*liby)
        self.lib_info = tkinter.Label(infoframe,text=lib_string)
        self.lib_info.pack()

        D = 0.0
        D_string = "Lunar Phase, D = %6.2f" % D
        self.D_info = tkinter.Label(infoframe,text=D_string)
        self.D_info.pack()

        moonaz=0.0
        moonel=0.0
        azel_string = "Az, El: (%7.2f, %6.2f)" % (moonaz,moonel)
        self.azel_info = tkinter.Label(infoframe,text=azel_string)
        self.azel_info.pack()

        moondec=0.0
        dec_string = "Declination: %6.2f" % moondec
        self.dec_info = tkinter.Label(infoframe,text=dec_string)
        self.dec_info.pack()

        sunel=-30.0
        sunel_string = "Sun Elevation: %6.2f" % sunel
        self.sunel_info = tkinter.Label(infoframe,text=sunel_string)
        self.sunel_info.pack()

        vaz = 0.0
        vel = 0.0
        self.voff_string = "Velocity Offset: (%5.2f,%5.2f)" % (vaz,vel)
        self.voff_info = tkinter.Label(infoframe,text=self.voff_string)
        self.voff_info.pack()

        orient_frame = tkinter.Frame(self)
        orient_frame.pack()
        
        canvx = 100
        canvy = 70

        self.midx = canvx/2.0
        self.midy = canvy/2.0

        apd_size = 10
        self.orient_canv = tkinter.Canvas(orient_frame,width=canvx,height=canvy,bd=1)
        self.orient_canv.pack()
        orient_rect = self.orient_canv.create_rectangle(5,5,canvx-5,canvy-5)
        apd_ll = self.orient_canv.create_line(self.midx,self.midy-apd_size,self.midx-apd_size,self.midy)
        apd_ul = self.orient_canv.create_line(self.midx-apd_size,self.midy,self.midx,self.midy+apd_size)
        apd_ur = self.orient_canv.create_line(self.midx,self.midy+apd_size,self.midx+apd_size,self.midy)
        apd_lr = self.orient_canv.create_line(self.midx+apd_size,self.midy,self.midx,self.midy-apd_size)

        self.voff_mark = self.orient_canv.create_oval(self.midx-4,self.midy-4,self.midx+4,self.midy+4)

        goframe = tkinter.Frame(self)
        goframe.pack(side='bottom')

        ####
        
        moonparams = self.update_moon(feature,time_now)

        D = moonparams[0]
        libx = moonparams[1]
        liby = moonparams[2]
        moonel = moonparams[3]
        moondec = moonparams[4]
        sunel = moonparams[5]
        vaz = moonparams[6]
        vel = moonparams[7]

        self.mc = moontarg.Moonbox(mcframe,D,libx,liby,moonel,sunel)
        self.update_moon_disp(feature,time_utc)		# so up to date @ start

        ####
        self.mc.canv.bind("<Motion>",self.cursor_move)
        self.mc.canv.bind("<Button-1>",self.cursor_click)

        decrmonth = tkinter.Button(mctrlframe,text='mo--',command=self.decr_month)
        decrmonth.grid(row=0,column=0)

        incrmonth = tkinter.Button(mctrlframe,text='mo++',command=self.incr_month)
        incrmonth.grid(row=1,column=0)

        decrday = tkinter.Button(mctrlframe,text='day--',command=self.decr_day)
        decrday.grid(row=0,column=1)

        incrday = tkinter.Button(mctrlframe,text='day++',command=self.incr_day)
        incrday.grid(row=1,column=1)

        decrhour = tkinter.Button(mctrlframe,text='hour--',command=self.decr_hour)
        decrhour.grid(row=0,column=2)

        incrhour = tkinter.Button(mctrlframe,text='hour++',command=self.incr_hour)
        incrhour.grid(row=1,column=2)

        decrmin = tkinter.Button(mctrlframe,text='min--',command=self.decr_min)
        decrmin.grid(row=0,column=3)

        incrmin = tkinter.Button(mctrlframe,text='min++',command=self.incr_min)
        incrmin.grid(row=1,column=3)

        now = tkinter.Button(mctrlframe,text='Now',command=self.now)
        now.grid(row=0,column=4)

        qb = tkinter.Button(ctrlframe,text='Quit',anchor='se',command=self.destroy)
        #qb.pack(side='right')

        self.hide_But = tkinter.Button(targframe,text="Show Craters",command=self.toggle_hide)
        self.hide_But.pack()

        self.new_go_But = tkinter.Button(goframe,
                                text="Slew Telescope",
                                state='disabled',
                                command=self.new_slew)
        self.new_go_But.pack()

        #self.go_But = Tkinter.Button(goframe,
        #                        text="Old Slew Telescope",
        #                        state='disabled',
        #                        command=self.now_slew)
        #self.go_But.pack()

      def update_moon(self,feature,time_utc):
            global track_cmd
            global new_track_cmd
            global offset_cmd
            global rx_cmd
            time_tuple = time.gmtime(time_utc)
            year = time_tuple[0]
            month = time_tuple[1]
            day = time_tuple[2]
            hour = time_tuple[3]
            minute = time_tuple[4]
            second = float(time_tuple[5])
            doy = time_tuple[6]
            time_string = "%d %d %d %d %d %f" % (month,day,year,hour,minute,second)
            #cmd_string = "C:\\apollo\\ephem\\moon_pos.py " + feature + " " + time_string
            moon_pos_exec = pathStuff.moonPos()
            #print 'update_moon: moon_pos_exec = ', moon_pos_exec
            #cmd_string = "python /Users/jbattat/Library/Application\ Support/TUIAdditions/Apollo/ephem/moon_pos.py " + feature + " " + time_string
            cmd_string = "%s %s %s" % (moon_pos_exec, feature, time_string)
            #print 'update_moon: cmd_string = ', cmd_string
            #D,libx,liby,moonel,moondec,sunel,vaz,vel,solar_tuple,lunar_tuple =\
            (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

            moonout = os.popen(cmd_string)
            lines = moonout.readlines()
            #f = open('/Users/Lou/Documents/Apollo/teststuffz/hello.txt', 'a')
            #f.write(str(lines))
            #f.write(os.getcwd())
            #f.flush()
            #f.close()
            for line in lines:
                if line.find('Total libration') > -1:
                    libs = pair.search(line)
                    libx = float(libs.group(1))
                    liby = float(libs.group(2))
                    libs_string = "Libration: (%6.2f,%6.2f)" % (libx,liby)
                    self.libs_info.configure(text=libs_string)
                    lib_string = "Total Libration: %6.2f" % math.sqrt(libx*libx+liby*liby)
                    self.lib_info.configure(text=lib_string)
                if line.find('phase angle') > -1:
                    Slist = line.split(':')
                    D = float(Slist[1])
                    D_string = "Lunar Phase, D = %6.2f" % D
                    self.D_info.configure(text=D_string)
                if (line.find('Solar') > -1):
                    solar = trio.search(line)
                    sunlong = float(solar.group(1))
                    sunlat = float(solar.group(2))
                    sunrange = float(solar.group(3))
                    solar_tuple = (sunlong,sunlat,sunrange)
                if (line.find('Moon apparent') > -1):
                    lunar = trio.search(line)
                    moonlong = float(lunar.group(1))
                    moonlat = float(lunar.group(2))
                    moonrange = float(lunar.group(3))
                    lunar_tuple = (moonlong,moonlat,moonrange)
                if (line.find('Azimuth') > -1):
                    azel = pair.search(line)
                    moonaz = float(azel.group(1))
                    moonel = float(azel.group(2))
                    azel_string = "Az, El: (%7.2f, %6.2f)" % (moonaz,moonel)
                    self.azel_info.configure(text=azel_string)
                if (line.find('Sun') > -1):
                    sunazel = pair.search(line)
                    sunel = float(sunazel.group(2))
                    sunel_string = "Sun Elevation: %6.2f" % sunel
                    self.sunel_info.configure(text=sunel_string)
                if (line.find('Feature at') > -1):
                    moonradec=pair.search(line)
                    moondec = float(moonradec.group(2))
                    dec_string = "Declination: %6.2f" % moondec
                    self.dec_info.configure(text=dec_string)
                if (line.find('v_offset_az') > -1):
                    Slist = line.split('=')
                    vaz = float(Slist[1].split()[0])
                    vel = float(Slist[2].split()[0])
                    voff_string = "Velocity Offset: (%5.2f,%5.2f)" % (vaz,vel)
                    self.voff_info.configure(text=voff_string)
                    rxx = math.cos(dtr*158.7)*vel - math.sin(dtr*158.7)*vaz
                    rxy = math.sin(dtr*158.7)*vel + math.cos(dtr*158.7)*vaz
                    ccdx = math.cos(dtr*21.3)*rxx + math.sin(dtr*21.3)*rxy
                    ccdy = -math.sin(dtr*21.3)*rxx + math.cos(dtr*21.3)*rxy
                    oval_x = self.midx+ccdx*10.0
                    oval_y = self.midy+ccdy*10.0
                    self.orient_canv.coords(self.voff_mark,oval_x-4,oval_y-4,oval_x+4,oval_y+4)
                    self.rx_cmd = "houston vtarget %5.2f %5.2f" % (rxx,rxy)

                if (-1 < line.find('tcc track') < 3):
                    track_cmd = line.strip()+'/NoAbsRefCorrect'
                if (line.find('tcc offset') > -1):
                    offset_cmd = line.strip()
                if (line.find('new tcc track') > -1):
                    tcc_pos = line.find('tcc')	# strip out 'new'
                    new_track_cmd = line[tcc_pos:].strip()+'/NoAbsRefCorrect'
                #line = moonout.readline()
            return (D,libx,liby,moonel,moondec,sunel,vaz,vel,solar_tuple,lunar_tuple)

      def update_moon_disp(self,feature,time_utc):
            moonparams = self.update_moon(feature,time_utc)
            time_string = time.asctime(time.gmtime(time_utc))
            self.mc.D = moonparams[0]
            self.mc.libx = moonparams[1]
            self.mc.liby = moonparams[2]
            self.mc.moonel = moonparams[3]
            self.mc.sunel = moonparams[5]
            self.mc.solar = moonparams[8]
            self.mc.lunar = moonparams[9]
            self.mc.time = time_utc
            self.mc.update()
            self.mc.canv.itemconfig(self.mc.time_stamp,text=time_string)

      def incr_min(self):
            global time_utc
            time_utc += 300.0
            self.update_moon_disp('CENTER',time_utc)

      def decr_min(self):
            global time_utc
            time_utc -= 300.0
            self.update_moon_disp('CENTER',time_utc)

      def incr_hour(self):
            global time_utc
            time_utc += 3600.0
            self.update_moon_disp('CENTER',time_utc)

      def decr_hour(self):
            global time_utc
            time_utc -= 3600.0
            self.update_moon_disp('CENTER',time_utc)

      def incr_day(self):
            global time_utc
            time_utc += 86400.0
            self.update_moon_disp('CENTER',time_utc)

      def decr_day(self):
            global time_utc
            time_utc -= 86400.0
            self.update_moon_disp('CENTER',time_utc)

      def incr_month(self):
            global time_utc
            time_utc += 86400.0*30.0
            self.update_moon_disp('CENTER',time_utc)

      def decr_month(self):
            global time_utc
            time_utc -= 86400.0*30.0
            self.update_moon_disp('CENTER',time_utc)

      def cursor_move(self,event):
            targnames = retros.names
            for i in range(len(targnames)):
              cnv_x = self.mc.targ_coords[i][0]
              cnv_y = self.mc.targ_coords[i][1]
              if (abs(event.x-cnv_x) < 5 and abs(event.y-cnv_y) < 5):
                self.mc.canv.itemconfig(self.mc.targs[targnames[i]],fill='green')
                self.pointer_info.configure(text=targnames[i])
              else:
                self.mc.canv.itemconfig(self.mc.targs[targnames[i]],fill='red')
            targnames = self.mc.finders.names
            for i in range(len(targnames)):
              cnv_x = self.mc.crater_coords[i][0]
              cnv_y = self.mc.crater_coords[i][1]
              if (abs(event.x-cnv_x) < 5 and abs(event.y-cnv_y) < 5):
                self.mc.canv.itemconfig(self.mc.craters[targnames[i]],fill='red')
                self.pointer_info.configure(text=targnames[i])
              else:
                if (self.mc.hide):
                  self.mc.canv.itemconfig(self.mc.craters[targnames[i]],fill='black')
                else:
                  self.mc.canv.itemconfig(self.mc.craters[targnames[i]],fill='green')

      def cursor_click(self,event):
            global targ_select
            targnames = self.mc.retros.names
            for i in range(len(targnames)):
              cnv_x = self.mc.targ_coords[i][0]
              cnv_y = self.mc.targ_coords[i][1]
              if (abs(event.x-cnv_x) < 5 and abs(event.y-cnv_y) < 5):
                self.targ_info.configure(text="Target Selection: " + targnames[i])
                self.targ_select = targnames[i]
                long = coords.long[targnames[i]]
                lat = coords.lat[targnames[i]]
                self.mc.explrlong = int
                self.mc.explrlat = lat
                self.mc.update()
                self.mc.canv.itemconfig(self.mc.explrpoint,fill='orange')
            targnames = self.mc.finders.names
            for i in range(len(targnames)):
              cnv_x = self.mc.crater_coords[i][0]
              cnv_y = self.mc.crater_coords[i][1]
              if (abs(event.x-cnv_x) < 5 and abs(event.y-cnv_y) < 5):
                self.targ_info.configure(text="Target Selection: " + targnames[i])
                self.targ_select = targnames[i]
                long = coords.long[targnames[i]]
                lat = coords.lat[targnames[i]]
                self.mc.explrlong = int
                self.mc.explrlat = lat
                self.mc.update()
                self.mc.canv.itemconfig(self.mc.explrpoint,fill='orange')

      def now(self):
            global time_utc
            time_now = time.time()
            time_utc = time_now
            self.update_moon_disp('CENTER',time_utc)
   
      #def now_slew(self):
      #      global targ_select
      #      global time_utc
      #      global track_cmd
      #      global offset_cmd
      #      global rx_cmd
      #      time_now = time.time()
      #      time_utc = time_now
      #      name = self.targ_select
      #      long = coords.long[name]
      #      lat = coords.lat[name]
      #      self.mc.tcclong = long
      #      self.mc.tcclat = lat
      #      self.mc.explrlong = 0.0
      #      self.mc.explrlat = 0.0
      #      feature = coords.lookup[name]
      #      self.update_moon_disp(feature,time_utc)
      #      self.mc.canv.itemconfig(self.mc.explrpoint,fill='black')
      #      self.targ_string = "Target Selection: "
      #      self.targ_info.configure(text=self.targ_string)
      #      self.mc.canv.itemconfig(self.mc.tccpoint,fill='red')
      #
      #      self.doCmd('apollo','houston tr clear')
      #
      #      track_cmd+='/Name="%s"' % name
      #
      #      for cmd in (track_cmd, offset_cmd):
      #          act, cmdStr = cmd.split(None, 1)
      #          self.doCmd(act,cmdStr)
      #
      #      if (retros.codes.has_key(name)):
      #          self.doCmd('apollo','houston refl %d' % retros.codes[name])
      #          
      #      self.doCmd('apollo',self.rx_cmd)
      #
      #      self.doCmd('apollo','houston set slewtarget="%s"' % name)
      #
      #      track_string = "Now Tracking: %s" % name
      #      self.track_info.configure(text=track_string)
   
      def new_slew(self):
            global targ_select
            global time_utc
            global new_track_cmd
            global offset_cmd
            global rx_cmd
            time_now = time.time()
            time_utc = time_now
            name = self.targ_select
            long = coords.long[name]
            lat = coords.lat[name]
            self.mc.tcclong = int
            self.mc.tcclat = lat
            self.mc.explrlong = 0.0
            self.mc.explrlat = 0.0
            feature = coords.lookup[name]
            self.update_moon_disp(feature,time_utc)
            self.mc.canv.itemconfig(self.mc.explrpoint,fill='black')
            self.targ_string = "Target Selection: "
            self.targ_info.configure(text=self.targ_string)
            self.mc.canv.itemconfig(self.mc.tccpoint,fill='red')

            self.doCmd('apollo','houston tr clear')

            new_track_cmd+='/Name="%s"' % name

            act, cmdStr = new_track_cmd.split(None, 1)
            self.doCmd(act,cmdStr)

            if (name in retros.codes):
                self.doCmd('apollo','houston refl %d' % retros.codes[name])
                
            self.doCmd('apollo',self.rx_cmd)

            self.doCmd('apollo','houston set slewtarget="%s"' % name)
 
            track_string = "Now Tracking: %s" % name
            self.track_info.configure(text=track_string)

      def doCmd(self,act,cmd,write=True):

                if write:
                    func=self.callBack
                else:
                    func=None

                cmdVar=RO.KeyVariable.CmdVar (
			actor = act,
			cmdStr = cmd,
			dispatcher = self.dispatcher,
                        callFunc = func,
                        callTypes = RO.KeyVariable.AllTypes
		)

                timeStr = time.strftime("%H:%M:%S", time.gmtime())
                me = self.tuiModel.getCmdr()
                
                if write and self.logWdg != None:
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
                elif msgType == '>':
                    endStr = ' Queued '
                    
                timeStr = time.strftime("%H:%M:%S", time.gmtime())

                if self.logWdg != None:
                    
                    self.logWdg.addOutput(timeStr+endStr+msgDict.get('msgStr')+'\n',category=cat)

      def toggle_hide(self):
            self.mc.hide += 1
            self.mc.hide %= 2
            if self.mc.hide:
              self.hide_But.configure(text="Show Craters")
              self.mc.update()
            else:
              self.hide_But.configure(text="Hide Craters")
              self.mc.update()

if __name__ == "__main__":
    root = RO.Wdg.PythonTk()
    testFrame = moonWdg(root)
    testFrame.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
    root.mainloop()
