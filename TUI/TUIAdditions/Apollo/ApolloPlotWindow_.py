#import ttk
import tkinter as Tk
import numpy as np
import random

darkColor = "#183A54"
lightColor = "#00A3E0"

#import RO.Alg

def addWindow(tlSet):

    tlSet.createToplevel(
        name = "Apollo.Plot",
        defGeom = "+10+10",
        resizable = True,
        wdgFunc = Plots,
        visible = True)


class MainWin(Tk.Tk):
    # main window used only for testing/as a substitute for the Apollo Window

    def __init__(self, *args, **kwargs):
        Tk.Tk.__init__(self, *args, **kwargs)
        Tk.Tk.wm_title(self, "Fake Apollo Window")
        self.geometry("300x300")

        container = Tk.Frame(self)
        # creating a Frame in this window?
        container.pack(side = "top", fill = "both", expand = True)
        container.grid_rowconfigure(0, weight = 1)
        container.grid_columnconfigure(0, weight = 1)
        # ^ still don't know how this is used
        Tk.Button(container, text = "Quit", command=quit).pack()
        # try it for now, it may not work/quit properly

        Tk.Button(container, text = "Blit Test", command = lambda: self.toplevels[Plots].BLIT()).pack()

        
        self.toplevels = {}
        self.toplevels[Plots] = Plots(self)




class Plots(Tk.Toplevel):
    def __init__(self, master = None, *args, **kwargs):
        Tk.Toplevel.__init__(self, master, *args, **kwargs)

        import imp
        global matplotlib
        matplotlib =  imp.load_source('matplotlib', '/usr/local/lib/python2.7/site-packages/matplotlib/')
        matplotlib.use("TkAgg")
        global plt, FigureCanvasTkAgg, NavigationToolbar2TkAgg
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
        
        self.title("Apollo Plots")
        self.geometry("1000x800")
        self.dataThing = {}
        self.plotInit()
        self.plotInit2()
        #print self.subplots
        self.getBackgrounds()
        self.subplots = {}
        self.subplot_lines = {}
        self.plotInit2()

    def plotInit(self):
        self.matplotlibStyling()

        self.fig = plt.figure(figsize = (6, 6), dpi = 100)
        # ^ don't really know what this first argument really mean
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        #print type(self.canvas)
        #print self.canvas
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side = Tk.TOP, fill = Tk.BOTH, expand = True)

        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side = Tk.TOP, fill = Tk.BOTH, expand = True)

        self.subplots = {}
        self.subplot_lines = {}
        self.subplot_names = ["lun_hitgrid", "lun_hist", "fid_hist", "lun_strip", "lun_rate_strip", "laser_power", "stare_rate"]


    def plotInit2(self):
        
        #setup specific plots
        #self.subplots["lun_hitgrid"] = self.fig.add_subplot(331)
        self.subplots["lun_hitgrid"] = plt.subplot2grid((11, 11), (0, 0), rowspan = 3, colspan = 3)
        #print self.subplots["lun_hitgrid"].remove.__doc__
        #print dir(self.subplots["lun_hitgrid"])
        self.subplots["lun_hitgrid"].set_title("LLunar/Stare")
        self.subplots["lun_hitgrid"].set_aspect('equal')
        self.subplots["lun_hitgrid"].set_xlim(0, 4)
        self.subplots["lun_hitgrid"].set_ylim(0, 4)
        self.subplots["lun_hitgrid"].set_xticks([])
        self.subplots["lun_hitgrid"].set_yticks([])

        self.subplot_lines["lun_hitgrid"] = []
        print(self.subplots["lun_hitgrid"].__class__)
        
        for i in range(16):
            x = np.remainder(i + 4, 4) + 0.5
            y = 3.5-np.floor((i + 0.5) /4)
            self.subplot_lines["lun_hitgrid"].append(self.subplots["lun_hitgrid"].plot(x, y, 'ks', ms = 28)[0])

        for i in range(16):
            c = np.true_divide(i , 16)
            self.subplot_lines["lun_hitgrid"][i].set_color(str(c))


        # lun_hist plot
        #self.subplots["lun_hist"] = self.fig.add_subplot(332)
        self.subplots["lun_hist"] = plt.subplot2grid((11, 11), (0, 4), rowspan = 3, colspan = 3)
        self.subplots["lun_hist"].set_title("Lunar")
        self.subplots["lun_hist"].set_ylabel("# of Returns")
        self.subplots["lun_hist"].set_xlabel("Return Time")
        self.subplots["lun_hist"].set_ylim(0, 100)
        self.subplots["lun_hist"].set_xlim(-2200, 2200)



        self.subplot_lines["lun_hist"] = {}
        # need to be adjusted based on what exactly upper/lower/all mean
        self.subplot_lines["lun_hist"]["all"] = self.subplots["lun_hist"].plot([-1000,0,500,1000], [20,50, 33, 7], 'b-', lw = 5)[0]
        self.subplot_lines["lun_hist"]["upper"] = self.subplots["lun_hist"].plot([], [], 'k--', lw = 5)[0]
        self.subplot_lines["lun_hist"]["lower"] = self.subplots["lun_hist"].plot([], [], 'k--', lw = 5)[0]




        
        # fid_hist plot
        #self.subplots["fid_hist"] = self.fig.add_subplot(333)
        self.subplots["fid_hist"] = plt.subplot2grid((11, 11), (0, 8), rowspan = 3, colspan = 3)
        self.subplots["fid_hist"].set_title("Fiducial")
        self.subplots["fid_hist"].set_xlabel("Return Time")
        self.subplots["fid_hist"].set_xlim(-2200, 2200)
        self.subplots["fid_hist"].set_ylim(0, 100)

        self.subplot_lines["fid_hist"] = {}
        self.subplot_lines["fid_hist"]["all"] = self.subplots["fid_hist"].plot([], [], 'k--', lw = 5)[0]
        self.subplot_lines["fid_hist"]["lower"] = self.subplots["fid_hist"].plot([], [], 'k--', lw = 5)[0]
        self.subplot_lines["fid_hist"]["upper"] = self.subplots["fid_hist"].plot([], [], 'k--', lw = 5)[0]



        
        # lun_strip plot
        #self.subplots["lun_strip"] = self.fig.add_subplot(335)
        self.subplots["lun_strip"] = plt.subplot2grid((11, 11),(4, 4), rowspan = 3, colspan = 3)
        self.subplots["lun_strip"].set_xlabel("Shot Number")
        self.subplots["lun_strip"].set_ylabel("Return Time")
        inplaceofnruns = 10 # original uses self.nruns
        self.subplots["lun_strip"].set_xlim(0, float(inplaceofnruns))
        self.subplots["lun_strip"].set_ylim(-500, 500)
        
        self.subplot_lines["lun_strip"] = {}
        self.subplot_lines["lun_strip"]["all"] = self.subplots["lun_strip"].plot([], [], 'bo', ms = 1, mec = 'b')[0]
        self.subplot_lines["lun_strip"]["lower"] = self.subplots["lun_strip"].plot([], [], 'k--', ms = 1)[0]
        self.subplot_lines["lun_strip"]["upper"] = self.subplots["lun_strip"].plot([], [], 'k--', ms = 1)[0]



        #lun_rate_strip plot...
        #self.subplots["lun_rate_strip"] = self.fig.add_subplot(336)
        self.subplots["lun_rate_strip"] = plt.subplot2grid((11, 11),(4, 8), rowspan = 3, colspan = 3)
        self.subplots["lun_rate_strip"].set_xlabel("Shot Number")
        self.subplots["lun_rate_strip"].set_ylabel("Registered Rate")
        self.subplots["lun_rate_strip"].set_xlim(0, float(inplaceofnruns))
        self.subplots["lun_rate_strip"].set_ylim(0, 1.0)
        
        self.subplot_lines["lun_rate_strip"] = {}
        self.subplot_lines["lun_rate_strip"]["all"] = self.subplots["lun_rate_strip"].plot([], [], "w-", ms = 5)[0]




        #laser power stripchart
        #self.subplots["laser_power"] = self.fig.add_subplot(338)
        self.subplots["laser_power"] = plt.subplot2grid((11, 11), (8, 4), rowspan = 3, colspan = 3)
        self.subplots["laser_power"].set_ylabel("Laser Power")
        self.subplots["laser_power"].set_xlabel("Power Measurement")
        self.subplots["laser_power"].set_xlim(0, 150)
        self.subplots["laser_power"].set_ylim(0, 2.5)
        
        self.subplot_lines["laser_power"] = {}
        self.subplot_lines["laser_power"]["all"] = self.subplots["laser_power"].plot([], [], 'w-', lw = 5)[0]
        self.subplot_lines["laser_power"]["last20"] = self.subplots["laser_power"].plot([], [], 'w-', lw = 5)[0]




        #self.subplots["stare_rate"] = self.fig.add_subplot(339)
        self.subplots["stare_rate"] = plt.subplot2grid((11, 11), (8, 8), rowspan = 3, colspan = 3)
        self.subplots["stare_rate"].set_xlabel("Stares Taken")
        self.subplots["stare_rate"].set_ylabel("Stare Rate")
        self.subplots["stare_rate"].set_xlim(0, 200)
        self.subplots["stare_rate"].set_ylim(-20, 500)

        self.subplot_lines["stare_rate"] = self.subplots["stare_rate"].plot([],[], 'w-', lw = 5)[0]

        self.canvas.draw()        

        #self.stopUpdateFlag = False



        

    def getBackgrounds(self):
        self.bboxes = {}
        self.subplot_backgrounds = {}
        
        for name in self.subplot_names:
            self.bboxes[name] = self.subplots[name].bbox.expanded(1.5, 1.4)
            self.subplots[name].remove()
        self.canvas.draw()

        for name in self.subplot_names:
            self.subplot_backgrounds[name] = self.canvas.copy_from_bbox(self.bboxes[name])

    
    def plotsUpdate(self):
        if self.stopUpdateFlag:
            return
        pass



    
    def BLIT(self):
        # function used in testing blit
        a = random.randrange(2)
        if a == 0:
            self.subplot_lines["lun_hist"]["all"].set_data([1000, 500, 0, -1000], [20,50, 33, 7])
            self.subplots["lun_hist"].set_ylim(0, 55)
            self.subplots["lun_hist"].set_xlim(-1500, 1500)
            #self.subplots["lun_hist"].draw_artist(self.subplots["lun_hist"].yaxis)
        else:
            self.subplot_lines["lun_hist"]["all"].set_data([-1000, 0, 500, 1000], [20,50, 33, 7])
            self.subplots["lun_hist"].set_ylim(0, 100)
            self.subplots["lun_hist"].set_xlim(-2000, 2000)
            

        self.canvas.restore_region(self.subplot_backgrounds["lun_hist"])
        self.subplots["lun_hist"].draw(self.subplots["lun_hist"].get_renderer_cache())
        #self.canvas.blit(self.subplots["lun_hist"].bbox.expanded(1.5, 1.4))
        self.canvas.blit(self.bboxes["lun_hist"])










        
    def BLIT2(self):
        a = random.randrange(2)
        if a == 0:
            self.subplot_lines["lun_hist"]["all"].set_data([1000, 500, 0, -1000], [20,50, 33, 7])
            self.subplots["lun_hist"].set_ylim(0, 55)
        else:
            self.subplot_lines["lun_hist"]["all"].set_data([-1000, 0, 500, 1000], [20,50, 33, 7])
            self.subplots["lun_hist"].set_ylim(0, 100)

            
        self.subplots["lun_hist"].draw(self.subplots["lun_hist"].get_renderer_cache())
        #self.subplots["lun_hist"].draw_artist()
        self.canvas.blit(self.subplots["lun_hist"].bbox.expanded(1.3,1.4))



    def matplotlibStyling(self):
        matplotlib.rc('xtick', labelsize = 9)
        matplotlib.rc('ytick', labelsize = 9)
        matplotlib.rc('axes', labelsize = 10, titlesize = 11)
        matplotlib.rc("figure", facecolor="turquoise")

if __name__ == "__main__":
    app = MainWin()
    app.mainloop()
