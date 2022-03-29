import tkinter
import time
import math
from . import mooncoords

class Moonbox(tkinter.Canvas):
  def __init__(self,master,D,libx,liby,moonel,sunel):
    tkinter.Canvas.__init__(self)
    self.nx = 320
    self.ny = self.nx
    self.D = D
    self.libx = libx
    self.liby = liby
    self.moonel = moonel
    self.sunel = sunel
    self.solar = (0.0,0.0,1.49e8)
    self.lunar = (0.0,0.0,385000.0)
    self.time = time.time()
    self.tcclong = 0.0
    self.tcclat = 0.0
    self.explrlong = 0.0
    self.explrlat = 0.0
    self.hide = 1
    self.nom_frac = 0.85
    self.scale = 1.0
    # scale of full nx,ny box in degrees
    self.rtd = 180.0/math.pi
    self.dtr = math.pi/180.0
    self.scale_deg = self.rtd*2.0*1736.0/(385000.0*self.nom_frac)
    self.rearth = 6378.0
    self.rsun = 109*self.rearth

    self.targs = {}
    self.retros = mooncoords.Retros()
    self.targ_coords = []
    for i in range(len(self.retros.names)): self.targ_coords.append([0,0])

    self.craters = {}
    self.finders = mooncoords.Finders()
    self.crater_coords = []
    for i in range(len(self.finders.names)): self.crater_coords.append([0,0])

    self.bgval = 20
    if (self.sunel > -18.0 and self.sunel < 0.0):
      self.bgval += (18.0+self.sunel)*10.0
    if (self.sunel > 0.0): self.bgval = 240
    self.bgcol = '#%02x%02x%02x' % (self.bgval*0.6, self.bgval*0.8, self.bgval)
    if (self.moonel > 0): self.mooncol = '#eeeea0'
    else: self.mooncol = '#999960'
    self.esval = 40 + int(abs(180-self.D)/2.0)
    self.escol = '#0000%02x' % self.esval

    self.canv = tkinter.Canvas(master,width=self.nx,height=self.ny, \
                               bg='#000000',highlightthickness=0,bd=0)
    self.canv.pack()

    self.bgbox = self.canv.create_rectangle(0,0,self.nx,self.ny,fill=self.bgcol,outline='')

    scl = 2.0/(1.0-self.nom_frac*self.scale)		# = 14 nominally
    xy = self.nx/scl,self.ny/scl,self.nx-self.nx/scl,self.ny-self.ny/scl
    xc = (xy[0] + xy[2])/2
    yc = (xy[1] + xy[2])/2
    self.rad = (xy[2] - xy[0])/2
    self.backdrop = self.canv.create_oval(xy,fill=self.escol,outline='')
    self.half = self.canv.create_arc(xy,start=90,extent=180, \
                                     fill=self.mooncol,outline='')
    self.oval = self.canv.create_oval(xy,fill=self.mooncol,outline='')

    self.libmark = self.canv.create_oval(10,10,12,12,fill='#ff0000',outline='')
    self.eq = self.canv.create_arc(xy,start=0,extent=180, \
                   fill='',outline='#44ff44',style=tkinter.ARC)
    self.md = self.canv.create_arc(xy,start=90,extent=180, \
                   fill='',outline='#44ff44',style=tkinter.ARC)

    self.lro = self.canv.create_arc(xy,start=89,extent=190, \
                   fill='',outline='#800080',style=tkinter.ARC)
    self.lroblob = self.canv.create_oval(5,5,7,7,fill='#800080',outline='')

    self.umbra = self.canv.create_oval(xy,fill=None,outline='#8b2500')
    self.penumbra = self.canv.create_oval(xy,fill=None,outline='#ff8c00')

    for target in self.retros.names:
      self.targs[target] = self.canv.create_text(xc,yc,text='+',fill='red') 

    for target in self.finders.names:
      self.craters[target]=self.canv.create_text(10,10,text='o',fill='black')

    self.tccpoint = self.canv.create_text(xc,yc,text='o',fill='black')
    self.explrpoint = self.canv.create_text(xc,yc,text='o',fill='black')

    ycoord = self.ny/30.0
    self.time_stamp = self.canv.create_text(xc,ycoord,text="",fill='red')

    self.update()

  def update(self):
    self.bgval = 20
    if (self.sunel > -18.0 and self.sunel < 0.0):
      self.bgval += (18.0+self.sunel)*10.0
    if (self.sunel > 0.0): self.bgval = 240
    self.bgcol = '#%02x%02x%02x' % (self.bgval*0.6, self.bgval*0.8, self.bgval)
    if (self.moonel > 0): self.mooncol = '#eeeea0'
    else: self.mooncol = '#999960'
    self.esval = 40 + int(abs(180.0-self.D)/2.0)
    self.escol = '#0000%02x' % self.esval
    self.lib = math.sqrt(self.libx**2 + self.liby**2)

    scale = 385000.0/self.lunar[2]
    scl = 2.0/(1-self.nom_frac*scale)		# = 14 for nominal size
    xy = self.nx/scl,self.ny/scl,self.nx-self.nx/scl,self.ny-self.ny/scl
    xc = (xy[0] + xy[2])/2
    yc = (xy[1] + xy[3])/2
    self.rad = (xy[2] - xy[0])/2.0
    xoff = int(0.5*(xy[2] - xy[0])*math.cos(self.D*self.dtr))
    xyp = xc-abs(xoff), xy[1], xc+abs(xoff), xy[3]
    if xoff > 0 and self.D < 180.0:
      self.canv.itemconfig(self.bgbox,fill=self.bgcol)
      self.canv.itemconfig(self.half,fill=self.mooncol)
      self.canv.itemconfig(self.backdrop,fill=self.escol)
      self.canv.itemconfig(self.half,start=270)
      self.canv.coords(self.backdrop,xy[0],xy[1],xy[2],xy[3])
      self.canv.coords(self.half,xy[0],xy[1],xy[2],xy[3])
      self.canv.coords(self.oval,xyp[0],xyp[1],xyp[2],xyp[3])
      self.canv.itemconfig(self.oval,fill=self.escol)
    elif xoff <= 0 and self.D < 180.0:
      self.canv.itemconfig(self.bgbox,fill=self.bgcol)
      self.canv.itemconfig(self.half,fill=self.mooncol)
      self.canv.itemconfig(self.backdrop,fill=self.escol)
      self.canv.itemconfig(self.half,start=270)
      self.canv.coords(self.backdrop,xy[0],xy[1],xy[2],xy[3])
      self.canv.coords(self.half,xy[0],xy[1],xy[2],xy[3])
      self.canv.coords(self.oval,xyp[0],xyp[1],xyp[2],xyp[3])
      self.canv.itemconfig(self.oval,fill=self.mooncol)
    elif xoff <= 0 and self.D >= 180.0:
      self.canv.itemconfig(self.bgbox,fill=self.bgcol)
      self.canv.itemconfig(self.half,fill=self.mooncol)
      self.canv.itemconfig(self.backdrop,fill=self.escol)
      self.canv.itemconfig(self.half,start=90)
      self.canv.coords(self.backdrop,xy[0],xy[1],xy[2],xy[3])
      self.canv.coords(self.half,xy[0],xy[1],xy[2],xy[3])
      self.canv.coords(self.oval,xyp[0],xyp[1],xyp[2],xyp[3])
      self.canv.itemconfig(self.oval,fill=self.mooncol)
    elif xoff > 0 and self.D >= 180.0:
      self.canv.itemconfig(self.bgbox,fill=self.bgcol)
      self.canv.itemconfig(self.half,fill=self.mooncol)
      self.canv.itemconfig(self.backdrop,fill=self.escol)
      self.canv.itemconfig(self.half,start=90)
      self.canv.coords(self.backdrop,xy[0],xy[1],xy[2],xy[3])
      self.canv.coords(self.half,xy[0],xy[1],xy[2],xy[3])
      self.canv.coords(self.oval,xyp[0],xyp[1],xyp[2],xyp[3])
      self.canv.itemconfig(self.oval,fill=self.escol)

    shadow_lon_deg = (self.lunar[0] - self.solar[0] + 180.0) % 360.0
    shadow_lat_deg = self.lunar[1] - self.solar[1]
    if (shadow_lon_deg > 180.0):
      shadow_lon_deg -= 360.0
    shadow_lon_pix = self.nx*(0.5 + shadow_lon_deg/self.scale_deg)
    shadow_lat_pix = self.ny*(0.5 + shadow_lat_deg/self.scale_deg)
    umbra_theta = self.rearth/self.lunar[2] - self.rsun/self.solar[2]
    umbra_rad = umbra_theta*self.rtd*self.nx/self.scale_deg
    penumbra_theta = self.rearth/self.lunar[2] + self.rsun/self.solar[2]
    penumbra_rad = penumbra_theta*self.rtd*self.nx/self.scale_deg
    umbx = [shadow_lon_pix-umbra_rad,shadow_lat_pix-umbra_rad, \
            shadow_lon_pix+umbra_rad,shadow_lat_pix+umbra_rad]
    pbx = [shadow_lon_pix-penumbra_rad,shadow_lat_pix-penumbra_rad, \
            shadow_lon_pix+penumbra_rad,shadow_lat_pix+penumbra_rad]

    self.canv.coords(self.umbra,umbx[0],umbx[1],umbx[2],umbx[3])
    self.canv.coords(self.penumbra,pbx[0],pbx[1],pbx[2],pbx[3])

    librad = round((self.nx/160.0)*self.lib/2)
    diam = 2.0*librad
    self.libsize = diam
    x = xc + int(self.rad*self.libx/self.lib)
    y = yc - int(self.rad*self.liby/self.lib)
    self.liblocx = x
    self.liblocy = y
    libxy = x-librad, y-librad, x-librad+diam, y-librad+diam
    xoff = -int(self.rad*math.sin(self.libx*self.dtr))
    yoff = -int(self.rad*math.sin(self.liby*self.dtr))
    merid = xc-abs(xoff), xy[1], xc+abs(xoff), xy[3]
    equat = xy[0], yc-abs(yoff), xy[2], yc+abs(yoff)
    if xoff < 0: xst = 90
    else: xst = 270
    if yoff < 0: yst = 180
    else: yst = 0
    self.canv.coords(self.libmark,libxy[0],libxy[1],libxy[2],libxy[3])
    self.canv.coords(self.eq,equat[0],equat[1],equat[2],equat[3])
    self.canv.coords(self.md,merid[0],merid[1],merid[2],merid[3])
    self.canv.itemconfig(self.eq,start=yst)
    self.canv.itemconfig(self.md,start=xst)

    # LRO arc
    lro_ang = 180.0 - self.lunar[0] + 10.5
    if lro_ang > 180.0: lro_ang -= 360.0
    if lro_ang < -180.0: lro_ang += 360.0
    if lro_ang > 360.0:
      lro_ang -= 360.0
    lro_rad = self.rad*1788.0/1738.0
    lro_proj = lro_rad*math.fabs(math.sin(lro_ang*math.pi/180.0))
    lro_xy=(xc-lro_proj,yc-lro_rad,xc+lro_proj,yc+lro_rad)
    st2 = (self.rad*self.rad - lro_rad*lro_rad)/(lro_proj*lro_proj - lro_rad*lro_rad)
    if st2 < 1.0:
      thet = math.asin(math.sqrt(st2))*180.0/math.pi
    else:
      thet = 89.9
    if (lro_ang % 180.0) > 90.0:
      lro_st =  90.0 - thet
      extent = 180.0 + 2.0*thet
    else:
      lro_st = 270 - thet
      extent = 180.0 + 2.0*thet
    self.canv.coords(self.lro,lro_xy[0],lro_xy[1],lro_xy[2],lro_xy[3])
    self.canv.itemconfig(self.lro,start=lro_st)
    self.canv.itemconfig(self.lro,extent=extent)

    # LRO blob
    orbit_time = self.time % 7200.0             # kluge for now
    orbit_phase = orbit_time/7200.0*360.0       # kluge for now
    lro_visible = False
    lro_lrflip = 1.0
    if orbit_phase < 180.0:
      lro_asccending = True
      if math.fabs(lro_ang) > 90.0:
        lro_backside = True
        lro_lrflip = -1.0
        if (90.0 - math.fabs(orbit_phase-90.0) < thet):
          lro_visible = True
      else:
        lro_backside = False
        lro_lrflip = 1.0
        lro_visible = True
    else:
      lro_ascending = False
      if math.fabs(lro_ang) < 90.0:
        lro_backside = True
        lro_lrflip = 1.0
        if (90 - math.fabs(orbit_phase-270.0) < thet):
          lro_visible = True
      else:
        lro_backside = False
        lro_lrflip = -1.0
        lro_visible = True
    lro_x = xc + lro_lrflip*lro_proj*math.sin(orbit_phase*math.pi/180.0)
    lro_y = yc - lro_rad*math.cos(orbit_phase*math.pi/180.0)
    self.canv.coords(self.lroblob,lro_x-4,lro_y-4,lro_x+4,lro_y+4)
    if lro_visible:
      self.canv.itemconfig(self.lroblob,fill='#c000c0',outline='')
    else:
      self.canv.itemconfig(self.lroblob,fill='',outline='#c000c0')

    i = 0
    slibx = math.sin(self.libx*self.dtr)
    clibx = math.cos(self.libx*self.dtr)
    sliby = math.sin(self.liby*self.dtr)
    cliby = math.cos(self.liby*self.dtr)
    for target in self.retros.names:
      self.canv.itemconfig(self.targs[target],fill='red')
      slong = math.sin(self.retros.long[target]*self.dtr)
      clong = math.cos(self.retros.long[target]*self.dtr)
      slat = math.sin(self.retros.lat[target]*self.dtr)
      clat = math.cos(self.retros.lat[target]*self.dtr)
      ang_part = slibx*sliby*slat + clibx*slong*clat - slibx*cliby*clong*clat
      x = xc + self.rad*ang_part
      ang_part = cliby*slat - sliby*clong*clat
      y = yc - self.rad*ang_part
      self.canv.coords(self.targs[target],x,y)
      self.targ_coords[i] = [int(x),int(y)]
      i += 1

    if (self.hide == 0):
      i = 0
      for target in self.finders.names:
        self.canv.itemconfig(self.craters[target],fill='green')
        slong = math.sin(self.finders.long[target]*self.dtr)
        clong = math.cos(self.finders.long[target]*self.dtr)
        slat = math.sin(self.finders.lat[target]*self.dtr)
        clat = math.cos(self.finders.lat[target]*self.dtr)
        ang_part = slibx*sliby*slat + clibx*slong*clat - slibx*cliby*clong*clat
        x = xc + self.rad*ang_part
        ang_part = cliby*slat - sliby*clong*clat
        y = yc - self.rad*ang_part
        self.canv.coords(self.craters[target],x,y)
        self.crater_coords[i] = [int(x),int(y)]
        i += 1
    else:
      i = 0
      for target in self.finders.names:
        self.canv.itemconfig(self.craters[target],fill='black')
        self.canv.coords(self.craters[target],10,10)
        self.crater_coords[i] = [10,10]
        i += 1
      

    slong = math.sin(self.tcclong*self.dtr)
    clong = math.cos(self.tcclong*self.dtr)
    slat = math.sin(self.tcclat*self.dtr)
    clat = math.cos(self.tcclat*self.dtr)
    ang_part = slibx*sliby*slat + clibx*slong*clat - slibx*cliby*clong*clat
    x = xc + self.rad*ang_part
    ang_part = cliby*slat - sliby*clong*clat
    y = yc - self.rad*ang_part
    if (self.tcclong == 0.0 and self.tcclat == 0.0):
      x = self.nx - 4
      y = self.ny - 4
    self.canv.coords(self.tccpoint,x,y)

    slong = math.sin(self.explrlong*self.dtr)
    clong = math.cos(self.explrlong*self.dtr)
    slat = math.sin(self.explrlat*self.dtr)
    clat = math.cos(self.explrlat*self.dtr)
    ang_part = slibx*sliby*slat + clibx*slong*clat - slibx*cliby*clong*clat
    x = xc + self.rad*ang_part
    ang_part = cliby*slat - sliby*clong*clat
    y = yc - self.rad*ang_part
    if (self.explrlong == 0.0 and self.explrlat == 0.0):
      x = self.nx - 4
      y = self.ny - 4
    self.canv.coords(self.explrpoint,x,y)

  def incrD(self):
    self.D += 10
    if self.D > 360.0: self.D -= 360.0
    self.update()

  def decrD(self):
    self.D -= 10
    if self.D < 0.0: self.D += 360.0
    self.update()

  def incrlib(self):
    arg = math.atan2(self.liby,self.libx)
    arg += 15.0*self.dtr
    self.libx = self.lib*math.cos(arg)
    self.liby = self.lib*math.sin(arg)
    self.update()

if __name__ == '__main__':

  root = tkinter.Tk()

  D = 300.0
  mcframe = tkinter.Frame(root)
  mcframe.pack()
  mc = Moonbox(mcframe,D)

  ctrlframe = tkinter.Frame(root)
  ctrlframe.pack()

  decrbut = tkinter.Button(ctrlframe,text='-',command=mc.decrD)
  decrbut.pack(side='left')

  incrbut = tkinter.Button(ctrlframe,text='+',command=mc.incrD)
  incrbut.pack(side='left')

  libbut = tkinter.Button(ctrlframe,text='+lib',command=mc.incrlib)
  libbut.pack(side='left')

  qb = tkinter.Button(ctrlframe,text='Quit',anchor='se',command=root.quit)
  qb.pack()

  root.mainloop()
