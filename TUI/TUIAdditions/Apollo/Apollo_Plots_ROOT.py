import ROOT
import socket
import pickle
import numpy as np
import threading
import queue
import time
import sys
import json

#############################
# Tips:
# ROOT Colors are explained at:
#    https://root.cern.ch/doc/master/classTColor.html


HOST = 'localhost'
PORT = 32768

UPDATING_FLAG = True
SAVE_FLAG = 0
last_update_time = time.time()

subplot_names = ["lun_hitgrid", "lun_hist", "fid_hist", "lun_strip", "lun_rate_strip",
                 "laser_power", "stare_rate", "acssweep", "lun_tws_phased", "fid_tws_phased"]
subplots = {}

pickleSep = ':::::'

setup_file_name = 'Apollo_Plots.config'
preference_file_name = 'twm2.json'

if len(sys.argv) == 2:
    preference_file_name = sys.argv[1]
    if preference_file_name[-5:] != '.json':
        preference_file_name += '.json'


#variables that will later be changed from ATUI

#Original chanMap = [6,15,2,11,3,10,1,7,8,14,5,12,4,13,0,9]
CHAN_MAP = [(3, 3),(4, 1),(3, 4), (4, 2), (4, 4), (3, 2),         # (col, row) starting in lower-left of the hitgrid plot
           (2, 4), (4, 3), (1, 2), (3, 1), (2, 3), (1, 1),
           (1, 3), (2, 1), (1, 4), (2, 2)]

# actually not these ^

stripWindow = 2000
hitgridReserve = 1200   # total number of data points to keep in memory
hitgridBuffer  = 200   # number of data points to be used for plot generation (must be <= hitgridReserve)
# for both lun and fid histograms
histReserve = 200
rateReserve = 200
fpdReserve = 400
rawTDCReserve = 400
twsShotReserve = 200

#old CHAN_OFFSET = [-23, 29, 0, -5, 0, 12, 16, 0, 28, 15, 3, -44, -10, -29, 0, 9]
#CHAN_OFFSET = [7, -16, 16, -33, 27, -10, 33, 18, 7, -12, 11, -26, -5, -13, 0, -8]
CHAN_OFFSET = [2, -21, 13, -37, 25, -14, 30, 16, 1, -16, 46, -31, -9, -19, 0, 16]


omitTDCChan = []
chanBackground = np.zeros(16)
chanFlatCorr = np.ones(16)

regCenter= 0   # predSkew
binForReg = 160
lunLower = 0 - binForReg/2.0
lunUpper = 0 + binForReg/2.0


regCenterFid= -444
binForRegFid = 160
fidLower = -444 - binForRegFid / 2.0
fidUpper = -444 + binForRegFid / 2.0

offsetAz = 0.0
offsetEl = 0.0


ACS_filter_active = False
ACS_filter_on = False
active_since = 0
ACS_count = 0
ACSReserve = 100
ACSShotReserve = 100

fid_data = {"chanTimesCorTot":[], "chanTimesCorHist":[], "FPDchanTimesCorHist": [], "chanTimesTot":[], "chanTimesHist":[]}
lun_data = {"chanTimesCorTot":[], "chanTimesCorHist":[], "hitgridData":np.zeros([hitgridReserve, 16]), "totalRegNum": 0 , "shotList":[], "regList":[], "chanTimesTot":[], "chanTimesHist":[], "maxRate": (0, 0), "subtractedTot":[], "subtractedHist":[]}
dark_data = {"sumDarkChans": 0}
stare_data = {"stareShot": 0, "stareNum": 0, "stareRate":[], "averageStareRate" : 0}
laser_data = {"laserPower":[], "laserPowerNum": 0, "20AveragePower": []}
tws_test_data = {"chanTimesTot":[], "chanTimesTransient":[], "peakList":[0]}  # data for displaying the working of tws-based ACS filter
fid_tws_test_data = {"chanTimesTot":[], "chanTimesTransient":[]}    # data for displaying the working of tws-based ACS filter

dacsweep_data = {"IR_Post":[],"Green":[]}


#setting for threading
#ROOT.MethodProxy._threaded.__set__(ROOT.TCanvas.Update,True)
#ROOT.MethodProxy._threaded.__set__(ROOT.TH1F.FindBin,True)
#ROOT.MethodProxy._threaded.__set__(ROOT.TH1F.GetBinContent,True)
#ROOT.MethodProxy._threaded.__set__(ROOT.TH1F.SetBinContent,True)
#ROOT.MethodProxy._threaded.__set__(ROOT.TH1F.Fill,True)
#ROOT.MethodProxy._threaded.__set__(ROOT.gPad.Modified,True)
#ROOT.MethodProxy._threaded.__set__(ROOT.gSystem.ProcessEvents, True)
#ROOT.MethodProxy._threaded.__set__(ROOT.gApplication.Run, True)
#ROOT.MethodProxy._threaded.__set__(ROOT.TGraph.SetPoint,True)
#ROOT.MethodProxy._threaded.__set__(ROOT.TPad.cd,True)


def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def handleROOTColorNames(plotNameList, setupDict):
    """ Look through setup for "ROOT Color Strings" and convert them to integers
    see getROOTColorInfo() for definition of ROOT color string.
    """
    for plotname in plotNameList:
        plotsetup = setupDict[plotname]
        for key, val in plotsetup.items():
            cmdList = val["commands"]
            # now loop over all arguments to the command list
            #cmdList is like:  [['SetMarkerSize', [0]], ['SetTitle', ['DAC Sweep']], ['SetLineColor', ["kRed-3"]], ['SetPoint', [0, 0, 0]]]
            for cmd_args in cmdList:
                args = cmd_args[1]
                for ii in range(len(args)):
                    arg = args[ii]
                    ROOTColorInfo = getROOTColorInfo(arg)
                    if ROOTColorInfo[0]:
                        color_integer  = getattr(ROOT, ROOTColorInfo[1])
                        color_integer += ROOTColorInfo[2]
                        #print "************* UPDATING ROOT COLOR *******************"
                        #print "  from: ", args[ii]
                        args[ii] = color_integer
                        #print "    to: ", args[ii]
                        #print "****************************************************"

    return setupDict
    
def getROOTColorInfo(inStr):
    """check if a string is a valid ROOT color string
    which is a ROOT color name with an optional +/- integer
    e.g. 'kViolet - 6' or 'kMagenta+2'

    returns a 3-element list:
    [bool, string, int]
    bool specifies if inStr is a valid ROOT color string
    string specifies what the color string is (e.g. "kRed" or "kGreen")
    int specifies the integer offset from that base (e.g. if the string is kRed-3 then int is -3)
    """

    retArr = [False, None, None]

    # make sure that the input is actually a string!
    if not isinstance(inStr, str):
        return retArr

    # https://root.cern.ch/doc/master/classTColor.html
    valid_ROOT_color_names = ['kYellow', 'kOrange', 'kRed', 'kPink', 'kMagenta',
                              'kViolet', 'kBlue', 'kAzure', 'kCyan', 'kTeal', 'kGreen', 'kSpring']
    #looking for strings like:
    #"kBlue - 4" or "kSpring+5"
    # so need to split on + or -.  Instead, replace all - with + and then split on +
    newStr = inStr.replace('-','+')
    toks = newStr.split('+')

    if len(toks) > 2:   # can only have a color and an integer (2 values, max)
        return retArr

    # need to also check that anything after the + or - is an integer
    if len(toks) == 2:
        if not is_integer(toks[1]):
            return retArr

    # Finally, test the first token to see if it is a valid ROOT color name
    tstStr = toks[0].strip()  # get rid of whitespace

    isValid = tstStr in valid_ROOT_color_names
    
    retArr[0] = isValid
    if not isValid:
        return retArr

    retArr[1] = tstStr
    if len(toks)==2:
        # get the sign of the offset from the original string
        if inStr.find("+") > -1:
            offsetSign = 1
        elif inStr.find("-") > -1:
            offsetSign = -1
        else:
            print("ERROR:  didn't find a + or a - sign in:  ", inStr)
            sys.exit()
        retArr[2] = offsetSign*int(toks[1])
    else:
        retArr[2] = 0 # no color offset
    #print '   got HERE:  ', retArr
    return retArr

    
#===========plot configuration things==========

class APlot(object):
    def __init__(self, plot_name, setupDict, preferenceDict):
        setup = setupDict[plot_name]
        preference = preferenceDict[plot_name]
        self.name = plot_name
        self.status = preference['status']
        
        if self.status == 'dead':
            self.pad = None
            return

        # draw canvas
        to_correct = False
        pos = preference['pos']
        for i in range(4):
            if pos[i] < 0.01:
                pos[i] = 0.01
                to_correct = True
                
            elif pos[i] > 0.99:
                pos[i] = 0.99
                to_correct = True
        self.pad = ROOT.TPad(plot_name, plot_name, pos[0], pos[2], pos[1], pos[3], preference['color'])
        self.pad.SetTickx(1)
        self.pad.SetTicky(1)
        p = setup["pad"]
        for step in p["commands"]:
            if type(step[0]) == type(''):
                getattr(self.pad, step[0])(*step[1])
            else:
                funcs = step[0]
                args = step[1]
                cur = self.pad
                for i in range(len(funcs)):
                    cur = getattr(cur, funcs[i])(*args[i])
        #self.pad.GetFrame().SetEditable(0)
        self.pad.Draw()
        self.pad.cd()
        ROOT.SetOwnership(self.pad, False)

        if to_correct == True:
            # autocorrect the pad's position in pref file if error detected.
            self.update_preference(preference_file_name, preference_file_name)
        
        # draw graph(s)
        self.allGraphs = []
        # the main graph
        if setup["main"]["type"] == "TMultiGraph":
            self.handle_multigraph(setup)
        else:
            a = setup["main"]
            self.mainGraph = getattr(ROOT, a["type"])()
            self.allGraphs.append(self.mainGraph)
            self.mainGraph.SetName(plot_name)
            for step in a["commands"]:
                #step[0] function name, step[1] argument tuple
                if type(step[0]) == type(''):
                    getattr(self.mainGraph, step[0])(*step[1])
                else:
                    funcs = step[0]
                    args = step[1]
                    cur = self.mainGraph
                    for i in range(len(funcs)):
                        cur = getattr(cur,funcs[i])(*args[i])
            self.mainGraph.SetFillColor(3)


            # draw any graph to superpose on main
            for graph_name in list(setup.keys()):
                # keys are name of graphs in this plot
                if graph_name != "main" and graph_name != "pad":
                    a = setup[graph_name]
                    setattr(self, graph_name + 'Graph', getattr(ROOT, a["type"])())
                    graph = getattr(self, graph_name + 'Graph')
                    self.allGraphs.append(graph)
                    graph.SetNameTitle(plot_name + '_' + graph_name, plot_name + '_' + graph_name)
                    for step in a["commands"]:
                        getattr(graph, step[0])(*step[1])

        for eachGraph in self.allGraphs:
            ROOT.SetOwnership(eachGraph, False)

        # will need to be put into subclasses in the future
        if plot_name == "lun_strip":
            self.set_y_range(regCenter)

            
    def update_preference(self, from_pref, to_pref):
        if self.pad != None:
            pref = None
            with open(from_pref, 'r') as f:
                pref = json.load(f)
                xlow = self.pad.GetAbsXlowNDC()
                ylow = self.pad.GetAbsYlowNDC()
                xup = xlow + self.pad.GetAbsWNDC()
                yup = ylow + self.pad.GetAbsHNDC()
                pref[self.name]['pos'] = [xlow, xup, ylow, yup]
                pref[self.name]['color'] = self.pad.GetFillColor()

            with open(to_pref, 'w') as f:
                json.dump(pref, f, indent = 4)
                # save current position

        else:
            pref = None
            with open(from_pref, 'r') as f:
                pref = json.load(f)
                pref[self.name]['status'] = 'dead'
            with open(to_pref, 'w') as f:
                json.dump(pref, f, indent = 4)



    #functions that will be in the subclasses in the future
    def set_max_label(self, text):
        # lun_rate_strip
        self.maxLabel = ROOT.TLatex(0.12, 0.85, text)
        self.maxLabel.SetNDC()
        self.maxLabel.Draw("")


    def set_y_range(self, center):
        # lun_strip
        lower = center - 500
        upper = center + 500
        self.pad.cd()
        self.mainGraph.GetYaxis().SetRangeUser(lower, upper)

        
    def switch_to(self, s):
        if not hasattr(self, "switch"):
            self.switch = 0
        # lun_hitgrid
        # s belongs to {0, "Lunar", "Stare", "Dark", "Flat"}
        # currently nothing other than the __init__ function sets s to 0.
        if s == self.switch:
            return

        self.switch = s
        if s != 0:
            self.mainGraph.SetTitle(s)
            for i in range(4):
                for j in range(4):
                    self.mainGraph.SetBinContent(i+1, j+1, 0.0)
            ROOT.gPad.Modified()

    def handle_multigraph(self, setup):
        self.mainGraph = getattr(ROOT, setup["main"]["type"])() # main will be TMultiGraph
        self.allGraphs.append(self.mainGraph)
        self.mainGraph.SetName(self.name)

        # draw actual TGraphs first
        for graph_name in list(setup.keys()):
            # keys are name of graphs in this plot
            if graph_name != "main" and graph_name != "pad":
                a = setup[graph_name]
                setattr(self, graph_name + 'Graph', getattr(ROOT, a["type"])())
                graph = getattr(self, graph_name + 'Graph')
                self.allGraphs.append(graph)
                graph.SetName(self.name + '_' + graph_name)
                for step in a["commands"]:
                    getattr(graph, step[0])(*step[1])

        #back to TMultiGraph
        a = setup["main"]
        for step in a["commands"]:
            #step[0] function name, step[1] argument tuple
            if type(step[0]) == type(''):
                if step[0] == "Add":
                    args = step[1]
                    first_arg = getattr(self, args.pop(0) + 'Graph')
                    args.insert(0, first_arg)
                    getattr(self.mainGraph, step[0])(*args)
                else:
                    print(step[0])
                    getattr(self.mainGraph, step[0])(*step[1])
            else:
                funcs = step[0]
                args = step[1]
                cur = self.mainGraph
                for i in range(len(funcs)):
                    cur = getattr(cur,funcs[i])(*args[i])





def create_plots(setup = setup_file_name, preference = preference_file_name, skews = (regCenter, regCenterFid)):
    print("Apollo_Plots_ROOT:  create_plots")
    #global fid_data, lun_data, stare_data, dark_data, laser_data, subplots
    #global fid_data, lun_data, stare_data, dark_data, laser_data, subplots, tws_test_data, fid_tws_test_data
    global fid_data, lun_data, stare_data, dark_data, laser_data, subplots, tws_test_data, fid_tws_test_data, ACS_filter_active, ACS_filter_on, active_since

    subplots = {}
    fid_data = {"chanTimesCorTot":[], "chanTimesCorHist":[], "FPDchanTimesCorHist": [], "chanTimesTot":[], "chanTimesHist":[]}
    lun_data = {"chanTimesCorTot":[], "chanTimesCorHist":[], "hitgridData":np.zeros([hitgridReserve, 16]), "totalRegNum": 0 , "shotList":[], "regList":[], "chanTimesTot":[], "chanTimesHist":[], "maxRate": (0, 0), "subtractedTot":[], "subtractedHist":[]}
    dark_data = {"sumDarkChans": 0}
    stare_data = {"stareShot": 0, "stareNum": 0, "stareRate":[], "averageStareRate" : 0}
    laser_data = {"laserPower":[], "laserPowerNum": 0, "20AveragePower": []}
    tws_test_data = {"chanTimesTot":[], "chanTimesTransient":[], "peakList":[0]}  # data for displaying the working of tws-based ACS filter
    fid_tws_test_data = {"chanTimesTot":[], "chanTimesTransient":[]}    # data for displaying the working of tws-based ACS filter
    ACS_filter_active = False
    ACS_filter_on = False
    active_since = 0
    
    style = ROOT.TStyle()
    style.SetOptStat(0)
    style.SetPalette(52)
    style.SetPadBorderSize(0)
    style.SetPadBorderMode(0)
    style.SetFrameFillColor(10)
    style.SetHistFillStyle(0)
    style.SetTitleStyle(0)
    style.SetTitleFont(42, "aaa")
    #^ any other 2nd arg value than some combination of "x", "y" and "z" sets the title font. 
    style.SetTitleBorderSize(0)
    style.SetTitleX(0.1)
    style.SetTitleH(0.07)
    style.SetTitleW(0.8)
    style.cd()
    #print style.GetPadBorderMode()
    #print style.GetHistFillColor()



    canvas_scale = 240
    cc = ROOT.TCanvas('cc','Apollo Plots', canvas_scale * 4, canvas_scale * 3)
    cc.SetFixedAspectRatio()
    ROOT.SetOwnership(cc, False)

    
    def get_setup_preference(setup, preference):
        print("opening setup")
        s = open(setup, 'r')
        sd = json.load(s)
        print("opening preference")
        p = open(preference, 'r')
        pd = json.load(p)
        return list(sd.keys()), sd, pd                        

    plotNameList, setupDict, preferenceDict= get_setup_preference(setup, preference)
    setupDict = handleROOTColorNames(plotNameList, setupDict)

    for name in plotNameList:
        subplots[name] = APlot(name, setupDict, preferenceDict)
        cc.cd()

    predskew_update(cc, skews[0])
    fidskew_update(cc, skews[1])

    cc.Update()

    return cc



def save_preference(from_pref = preference_file_name, to_pref = preference_file_name):
    first = True
    for plot in list(subplots.values()):
        if first:
            plot.update_preference(from_pref, to_pref)
            first = False
        else:
            plot.update_preference(to_pref, to_pref)


#============socket things===========

            
def receive_data(sock, plot):
    #sock.settimeout(30.0)
    receive_data.leftover = []
    connected = True
    while connected:
        #try:
            pickled_data = sock.recv(4096)
            ROOT.gSystem.ProcessEvents()
            if sys.getsizeof(pickled_data) > 3000:
                print("LARGE PACKAGE:", sys.getsizeof(pickled_data))

            pickled_data = pickled_data.split(pickleSep)

            if len(receive_data.leftover) > 0:
                #print "stored: ", receive_data.leftover
                combined = receive_data.leftover.pop(0) + pickled_data.pop(0)
                combined = combined.split(pickleSep)
                combined.extend(pickled_data)
                pickled_data = combined
            
            if pickled_data[-1] != '':
                receive_data.leftover.append(pickled_data.pop())
                
            for each in pickled_data:
                if len(each) > 0:
                    data = pickle.loads(each)
                    #future plan: use dictionary instead...
                    if data[0] == 'lunar':
                        lunar_update(plot, data[1])

                    elif data[0] == 'fiducial':
                        fiducial_update(plot, data[1])

                    elif data[0] == 'tws_test':
                        tws_update(plot, data[1])

                    elif data[0] == 'fid_tws_test':
                        fid_tws_update(plot, data[1])
                        
                    elif data[0] == 'ACS':
                        if type(data[1]) == tuple:
                            global ACS_filter_on, ACS_filter_active, active_since
                            if (not ACS_filter_active) and data[1][1]:
                                active_since = 0 
                            ACS_filter_on, ACS_filter_active = data[1]
                        else:
                            tws_fidlun_peak_update(plot, data[1])
                            
                    elif data[0] == 'ACS_DAC_SCAN':
                        #print 'FOUND ACS_DAC_SCAN'
                        #print "data[1:] = ", data[1:]
                        #print "data[1]  = ", data[1]
                        acssweep_update(plot, data[1:])

                    elif data[0] == 'ACS_PHASE_SCAN':
                        acssweep_update_phase(plot, data[1:])

                    elif data[0] == 'predskew':
                        predskew_update(plot, data[1])

                    elif data[0] == 'fidskew':
                        fidskew_update(plot, data[1])

                    elif data[0] == 'dacsweepfit':
                        print('DAC sweep is done')
                        print('Now doing a FIT')
                        print('data = ', data)
                        print('plot = ', plot)
                        acssweep_dac_fit(plot, data[1:])
                        
                    elif data[0] == 'hitgrid_buffer':
                        global hitgridBuffer
                        print("hitgrid_buffer_update:")
                        print("    old hitgridBuffer = [", hitgridBuffer, "]")
                        hitgridBuffer = int(data[1])
                        print("    new hitgridBuffer = [", hitgridBuffer, "]")
                        
                    elif data[0] == 'guideoff':
                        # can have empty second element:
                        #   data =  ('guideoff', [])
                        global offsetAz, offsetEl
                        if len(data[1]) >= 2:
                            offsetAz = float(data[1][0])
                            offsetEl = float(data[1][1])
                        
                    elif data[0] == 'stare':
                        stare_update(plot, data[1])

                    elif data[0] == 'laser':
                        laser_update(plot, data[1])

                    elif data[0] == 'dark':
                        dark_update(plot, data[1])

                    elif data[0] == 'flat':
                        flat_update(plot, data[1])

                    elif data[0] == 'clear':
                        if data[1] == 'laser':
                            global subplots, laser_data
                            laser_data = {"laserPower":[], "laserPowerNum": 0, "20AveragePower": []}
                            subplots["laser_power"].pad.cd()
                            subplots["laser_power"].mainGraph.Set(0)
                            subplots["laser_power"].last20Graph.Set(0)
                            subplots["laser_power"].mainGraph.SetPoint(0, 0, 0)
                            plot.Update()
                        elif data[1] == 'acssweep':
                            # the 'acssweep' subplot is a TMultiGraph
                            # So to wipe the child graphs clean, we need to get a list of graphs
                            # and then clear each graph in that list
                            tlist = subplots["acssweep"].mainGraph.GetListOfGraphs()
                            ngraphs = tlist.GetSize()
                            for ig in range(ngraphs):
                                tlist[ig].Set(0)  # clear the contents of each TGraph

                            # FIXME:  can add title, xaxis, yaxis updates here (shoud have Apollo_Wdg send a second argument
                            # that specifies the kind of sweep (DAC or phase).
                            if data[2] == 'DAC':
                                print('DAC SWEEP STARTING')
                                subplots["acssweep"].mainGraph.SetTitle("DAC Sweep;DAC;ADC Counts")
                                subplots["acssweep"].mainGraph.GetXaxis().SetTitle("DAC Value")
                                subplots["acssweep"].mainGraph.GetYaxis().SetTitle("ADC Counts")
                            elif data[2] == 'PHASE':
                                print('PHASE SWEEP STARTING')
                                subplots["acssweep"].mainGraph.SetTitle("Phase Sweep")
                                subplots["acssweep"].mainGraph.GetXaxis().SetTitle("Phase Steps")
                                subplots["acssweep"].mainGraph.GetYaxis().SetTitle("ADC Counts")
                                
                            plot.Update()
                            
                    elif data[0] == 'disconnect':
                        sock.close()
                        connected = False
                        break

                    elif data[0] == 'refresh':
                        #connected = socket_refresh(sock, plot)
                        ## if returns, connected will be set to False

                        #just creates a new plot, instead of resetting connection
                        print('Apollo_Plots_ROOT: refresh')
                        skews = data[1]
                        plot = create_plots(skews = skews)
                        
                    elif data[0] == 'idle':
                        print('idling')
                        global IDLING_FLAG
                        IDLING_FLAG = 0

                        q_slow = queue.Queue()
                        q2 = queue.Queue()
                        q3 = queue.Queue()
                        
                        idleThread = threading.Thread(target = idle_listening, args =(sock, plot, q_slow, q2, q3))
                        idleThread.start()
                        
                        while IDLING_FLAG == 0:
                            misc = idle_loop(sock, plot, q_slow, q2, q3)
                            if misc == False:
                                connected = misc
                            elif misc != None:
                                plot = misc
                        
                    
                    elif data[0] == 'chanoffset':
                        global CHAN_OFFSET
                        CHAN_OFFSET = data[1]

                        
        #except:
        #    global UPDATING_FLAG
        #    UPDATING_FLAG = False
        #    break


def idle_loop(sock, plot, q_slow, q2, q3):
    global IDLING_FLAG
    # this loop happens in the main program
    while IDLING_FLAG == 0:
        ROOT.gSystem.ProcessEvents()
        
    if IDLING_FLAG == 1:
        # breaks the idling loop above (in the previous function)
        skews = q_slow.get()
        plot = create_plots(skews = skews)
        return plot

    elif IDLING_FLAG == 2:
        sock.close()
        conn = False
        return conn

    elif IDLING_FLAG == 3:
        # save plot configurations
        save_preference()
        global IDLING_FLAG
        IDLING_FLAG = 0
        misc = idle_loop(sock, plot, q_slow, q2, q3)
        return misc
        # assume this is not performed too many times in a row, i.e. not too many nested functions are created
        # this option and this only creates a nested looping function.

    elif IDLING_FLAG == 3.1:
        to_file = q_slow.get()
        save_preference(to_pref = to_file)
        global IDLING_FLAG
        IDLING_FLAG = 0
        misc = idle_loop(sock, plot, q_slow, q2, q3)
        return misc
        
        
    elif IDLING_FLAG == 4.1:
        predskew = q2.get()
        predskew_update(plot, predskew)
        IDLING_FLAG = 0
    
    elif IDLING_FLAG == 4.2:
        fidskew = q3.get()
        fidskew_update(plot, fidskew)
        IDLING_FLAG = 0

    elif IDLING_FLAG == 4.3:
        global CHAN_OFFSET
        CHAN_OFFSET = q_slow.get()



def idle_listening(sock, cc, q_slow, q2, q3):
    # This happends in a new thread when the window status is idle
    global IDLING_FLAG
    IDLING_FLAG = 0
    local_connected = True
    while local_connected:
        pickled_data = sock.recv(4096).split(pickleSep)
        for each in pickled_data:
            if len(each) > 0:
                data = pickle.loads(each)
                if data[0] == 'refresh':
                    local_connected = False
                    q_slow.put(data[1])
                    IDLING_FLAG = 1
                    break
                    
                elif data[0] == 'disconnect':
                    local_connected = False
                    IDLING_FLAG = 2
                    break

                elif data[0] == 'save':
                    if data[1] == 0: 
                        IDLING_FLAG = 3
                    else:
                        IDLING_FLAG = 3.1
                        q_slow.put(data[1])

                elif data[0] == 'predskew':
                    q2.queue.clear()
                    q2.put(data[1])
                    IDLING_FLAG = 4.1

                elif data[0] == 'fidskew':
                    q3.queue.clear()
                    q3.put(data[1])
                    IDLING_FLAG = 4.2

                elif data[0] == 'chanoffset':
                    q_slow.put(data[1])
                    IDLING_FLAG = 4.3
                    

                    
# not used anymore
def socket_refresh(sock, plot):
    sock.close()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST,PORT))
    plot.Destructor()
    
    newPlot = create_plots()
    receive_data(s, newPlot)
    # the receive_data returns when the loop breaks, which is when the new socket gets disconnected. this function will return, and the loop in which this function is run will continue, but without connection because it was closed at the beginning of this funciton.  
    return False
    

#=============plot updating things==========


def lunar_update(cc, lunarData):
    global lun_data, subplots, active_since, regCenter
    
    shotNum = lunarData[0]
    #Apollo_MPL_Wdg.py uses a counter self.shotNumLun instead of shotNum, which assumes shot number always increments by 1.

    lun_data["shotList"].append(shotNum)
    
    if shotNum < 0: return
    #chanPred = lunarData[3]  # tpred
    chanPred = lunarData[2]  # ppred
    nhit = lunarData[4]
    # ??? need to take away channels that appeared in omitTDCChan or no?
    chanDict = lunarData[6] ############NOTE: temporarily changed due to hack
    chan_tagged = lunarData[7]
    #print "chan_tagged:", chan_tagged
    
    for j in omitTDCChan:
        if j+1 in chanDict:
            chanDict.pop(j+1)
            # responding to ???
            
    active_since += 1

    #timing related.
    chanTimesCor = []
    lunRegNum = 0
    temp = {}

    # Each hitgrid_row represents a shot.
    # Make sure that old data is cleared out (zero each row) before populating with new data.
    # FIXME: should row be the number of *registered* photons, NOT shot number???
    hitgrid_row = np.mod(shotNum-1, hitgridReserve) # for hitgrid data filling. putting up here to not do repeated calc.
    if np.sum(lun_data["hitgridData"][hitgrid_row][:]) > 0:
        lun_data["hitgridData"][hitgrid_row] = np.zeros(16)

    for chan in chanDict:
        # does nothing if chanDict is empty
        
        #here are data and graphs to be updated regardless of ACS status (tagged/not tagged) 
        temp[chan] = chanDict[chan] - CHAN_OFFSET[chan - 1]

        lun_data["chanTimesHist"].append(temp[chan])
        if subplots["raw_lun_hist"].status == 'alive' and subplots["raw_lun_hist"].pad != None:
                subplots["raw_lun_hist"].pad.cd()
                subplots["raw_lun_hist"].mainGraph.Fill(temp[chan])
                if len(lun_data["chanTimesHist"]) > rawTDCReserve:
                    binToDecrement = subplots["raw_lun_hist"].mainGraph.FindBin(lun_data["chanTimesHist"][-rawTDCReserve-1])
                    contentOfBin = subplots["raw_lun_hist"].mainGraph.GetBinContent(binToDecrement)
                    subplots["raw_lun_hist"].mainGraph.SetBinContent(binToDecrement, contentOfBin - 1)
                ROOT.gPad.Modified()
        

        # stuff that depends on ACS status (tagged/not tagged)
        if chan not in chan_tagged or not ACS_filter_active:
            chanTimesDiff = (temp[chan] - chanPred)
            chanTimesCor.append(chanTimesDiff)
            lun_data["chanTimesCorHist"].append(chanTimesDiff)
        
            #update lunar histogram
            if subplots["lun_hist"].status == 'alive' and subplots["lun_hist"].pad != None:
                subplots["lun_hist"].pad.cd()

                subplots["lun_hist"].mainGraph.Fill(chanTimesDiff)
                
                if len(lun_data["chanTimesCorHist"]) > histReserve:
                    binToDecrement = subplots["lun_hist"].mainGraph.FindBin(lun_data["chanTimesCorHist"][-histReserve-1])
                    contentOfBin = subplots["lun_hist"].mainGraph.GetBinContent(binToDecrement)
                    subplots["lun_hist"].mainGraph.SetBinContent(binToDecrement, contentOfBin - 1)    

                # old ACS filtering implementation
                #if ACS_on == False or (ACS_on == True and ACS_sift(chanTimes[i])):
                #    #print ACS_on
                #    subplots["lun_hist"].mainGraph.Fill(chanTimesDiff)
                #    
                #    if ACS_on == True or shotNum < ACSShotReserve:
                #        lun_data["subtractedHist"].append(chanTimesDiff)
                #
                #    if ACS_on == False:
                #        if len(lun_data["chanTimesCorHist"]) > histReserve:
                #            binToDecrement = subplots["lun_hist"].mainGraph.FindBin(lun_data["chanTimesCorHist"][-histReserve-1])
                #            contentOfBin = subplots["lun_hist"].mainGraph.GetBinContent(binToDecrement)
                #            subplots["lun_hist"].mainGraph.SetBinContent(binToDecrement, contentOfBin - 1)    
                #    
                #    elif len(lun_data["subtractedHist"]) > histReserve:
                #        binToDecrement = subplots["lun_hist"].mainGraph.FindBin(lun_data["subtractedHist"][-histReserve-1])
                #        contentOfBin = subplots["lun_hist"].mainGraph.GetBinContent(binToDecrement)
                #        subplots["lun_hist"].mainGraph.SetBinContent(binToDecrement, contentOfBin - 1)    


                ROOT.gPad.Modified()


            #update lunar return time plot
            if subplots["lun_strip"].status == 'alive' and subplots["lun_hist"].pad != None:
                subplots["lun_strip"].pad.cd()
                subplots["lun_strip"].mainGraph.SetPoint(subplots["lun_strip"].mainGraph.GetN(), shotNum, chanTimesDiff)
                if shotNum > stripWindow:
                    subplots["lun_strip"].mainGraph.GetXaxis().SetRangeUser(shotNum - stripWindow, shotNum + 100)

                subplots["lun_strip"].set_y_range(regCenter)

            # If photon is a registered lunar...
            if chanTimesDiff > lunLower and chanTimesDiff < lunUpper:
                #print "GOT_REG_LUN: shot, chan, hitgrid_row, chanBkg, chanFlat = %d %d %d %f %f" % (shotNum, chan, hitgrid_row, chanBackground[chan-1], chanFlatCorr[chan-1])
                lun_data["totalRegNum"] += 1
                lunRegNum += 1
                lun_data["hitgridData"][hitgrid_row, chan-1] = np.true_divide(1.0 - 0.0001 * chanBackground[chan-1], chanFlatCorr[chan-1])


    if subplots["lun_hitgrid"].status == 'alive' and subplots["lun_hitgrid"].pad != None:
        subplots["lun_hitgrid"].pad.cd()
        # update hitgrid plot
        subplots["lun_hitgrid"].switch_to("Lunar")
        #a = np.sum(lun_data["hitgridData"], axis = 0)  # gives a 1D array with 16 entries (one per APD channel).  values are sum of all hits in history
        # Create chan-by-chan sum of registered hits, over last hitgridBuffer shots
        hitHistoryIds = np.mod(np.arange(hitgridBuffer)+((shotNum-1)-(hitgridBuffer-1)), hitgridReserve)
        #print "SHOT, IDs: ", shotNum, ", ", hitHistoryIds
        a = np.sum(lun_data["hitgridData"][hitHistoryIds], axis = 0)  
        #print "SHOT, SUM: ", shotNum, ", ", a
        if np.max(a) == 0:
            a[:] = [0.0 for i in a]  # why do this? were there negative values in a?
        else:
            amax = np.max(a)
            a[:] = [(1 - np.true_divide(i, amax)+ 0.00001) for i in a] # + 0.00001 because 0.0 ends up being plotted as white (or not plotted). 

        for j in range(16):
            chanAPD = CHAN_MAP[j]
            subplots["lun_hitgrid"].mainGraph.SetBinContent(chanAPD[0], chanAPD[1], a[j])

        #for debugging
        #hist = np.zeros([4,4])
        #for i in range(4):
        #    for j in range(4):
        #        hist[3 - j, i] = subplots["lun_hitgrid"].GetBinContent(i+1, j +1)
        #print hist
    
    ROOT.gPad.Modified()

    #chanTimesTot and chanTimesCorTot: [[times]]
    lun_data["chanTimesCorTot"].append(chanTimesCor)
    lun_data["chanTimesTot"].append(list(temp.values()))
    lun_data["regList"].append(lunRegNum)

    
    # update lunar rate plot
    if shotNum > rateReserve:
        if subplots["lun_rate_strip"].status == 'alive' and subplots["lun_rate_strip"].pad != None:
            subplots["lun_rate_strip"].pad.cd()
            y = 1.0 * sum(lun_data["regList"][-rateReserve-1:]) / rateReserve

            if shotNum == rateReserve + 1:
                subplots["lun_rate_strip"].mainGraph.SetPoint(0, shotNum, y)
            else:
                subplots["lun_rate_strip"].mainGraph.SetPoint(subplots["lun_rate_strip"].mainGraph.GetN(), shotNum, y)

            if shotNum > stripWindow:
            # scrolling window
                subplots["lun_rate_strip"].mainGraph.GetXaxis().SetRangeUser(shotNum-stripWindow, shotNum + 100)

                
            if y >= lun_data["maxRate"][1] and (ACS_filter_on == False or (ACS_filter_active == True and active_since >= rateReserve)):
                lun_data["maxRate"] = (shotNum, y)
                if hasattr(subplots["lun_rate_strip"], "maxLabel"):
                    subplots["lun_rate_strip"].maxLabel.SetText(0.12, 0.85, "Max: %.3f Shot: %i at (%.1f, %.1f)" % (y, shotNum, offsetAz, offsetEl))
                else:
                    subplots["lun_rate_strip"].set_max_label("Max: %.3f Shot: %i at (%.1f, %.1f)" % (y, shotNum, offsetAz, offsetEl))
                
                
            
        render(cc)
    
#def ACS_sift(rawTDC):
#    # True --> keep
#    if rawTDC < 1500 or rawTDC > 3500:
#        return True
#    elif (rawTDC % ACS_period) in mod_list:
#        global ACS_count
#        ACS_count += 1
#        #print ACS_count
#        return False
#    return True

    

def fiducial_update(cc, fiducialData):
    global fid_data, subplots
    fid_data["chanTimesCorTot"].append([])
    fid_data["chanTimesTot"].append([])
    # not sure why dummy 5000 (in MPL) is needed.
    shotNum = fiducialData[0]
    chanInten = fiducialData[2]
    photoD = fiducialData[4]
    chanDict = fiducialData[7]
    chan_tagged = fiducialData[8]

    #remove misbehaving APD channels (of which there are always none currently...)
    # omitTDCChan is in 0-base
    for j in omitTDCChan:
        if j+1 in chanDict:
            chanDict.pop(j+1)
    
    if 15 in chanDict and (15 not in chan_tagged or ACS_filter_active == False):
        FPD_time = chanDict.pop(15)
        FPD_time = FPD_time - 1000
        fid_data["FPDchanTimesCorHist"].append(FPD_time)
        if subplots["fid_hist"].status == 'alive' and subplots["fid_hist"].pad != None:
            subplots["fid_hist"].pad.cd()
            subplots["fid_hist"].FPDGraph.Fill(FPD_time)
            if len(fid_data["FPDchanTimesCorHist"]) > fpdReserve:
                binToDecrement = subplots["fid_hist"].FPDGraph.FindBin(fid_data["FPDchanTimesCorHist"][-fpdReserve-1])
                contentOfBin = subplots["fid_hist"].FPDGraph.GetBinContent(binToDecrement)
                subplots["fid_hist"].FPDGraph.SetBinContent(binToDecrement, contentOfBin - 1)



    
    temp = {}
    for chan in chanDict:
        # update fiducial subtracted histogram
        # not actually altering chanDict
        temp[chan] = chanDict[chan] - CHAN_OFFSET[chan-1]
        tcor = photoD - temp[chan]


        
        fid_data["chanTimesTot"][-1].append(temp[chan])
        fid_data["chanTimesHist"].append(temp[chan])


        
        if chan not in chan_tagged or ACS_filter_active == False:
            fid_data["chanTimesCorTot"][-1].append(tcor)
            fid_data["chanTimesCorHist"].append(tcor)

            if subplots["fid_hist"].status == 'alive' and subplots["fid_hist"].pad != None:
                subplots["fid_hist"].pad.cd()
                subplots["fid_hist"].mainGraph.Fill(tcor)
                if len(fid_data["chanTimesCorHist"]) > histReserve:
                    binToDecrement = subplots["fid_hist"].mainGraph.FindBin(fid_data["chanTimesCorHist"][-histReserve-1])
                    contentOfBin = subplots["fid_hist"].mainGraph.GetBinContent(binToDecrement)
                    subplots["fid_hist"].mainGraph.SetBinContent(binToDecrement, contentOfBin - 1)


        if subplots["raw_fid_hist"].status == 'alive' and subplots['raw_fid_hist'].pad != None:
            #if chan == 13:
            #    print "here"
            subplots["raw_fid_hist"].pad.cd()
            subplots["raw_fid_hist"].mainGraph.Fill(temp[chan])
            if len(fid_data["chanTimesHist"]) > rawTDCReserve:
                binToDecrement = subplots["raw_fid_hist"].mainGraph.FindBin(fid_data["chanTimesHist"][-rawTDCReserve-1])
                contentOfBin = subplots["raw_fid_hist"].mainGraph.GetBinContent(binToDecrement)
                subplots["raw_fid_hist"].mainGraph.SetBinContent(binToDecrement, contentOfBin - 1)

            
    ROOT.gPad.Modified()


    
    #histogramed = 0
    #for i in range(102):
    #    histogramed += subplots["fid_hist"].GetBinContent(i)
    #print len(fid_data["chanTimesCorHist"]), len(fid_data["chanTimesCorTot"])
    #check whether messages are lost *-*


    render(cc)



def tws_fidlun_peak_update(plot, peakData):
    global tws_test_data, subplots
    peakData %= 500
    peakData += 2000
    tws_test_data["peakList"].append(peakData)
    if peakData != tws_test_data["peakList"][-2]:
        if subplots["fid_tws_phased"].status == 'alive' and subplots["fid_tws_phased"].pad != None:
            subplots["fid_tws_phased"].pad.cd()

            if tws_test_data["peakList"][-2] != 0:
                binToClear = subplots["fid_tws_phased"].peakGraph.FindBin(tws_test_data["peakList"][-2])
                subplots["fid_tws_phased"].peakGraph.SetBinContent(binToClear, 0)

            binToFill = subplots["fid_tws_phased"].peakGraph.FindBin(peakData)
            subplots["fid_tws_phased"].peakGraph.SetBinContent(binToFill, 500)
                
        if subplots["lun_tws_phased"].status == 'alive' and subplots["lun_tws_phased"].pad != None:
            subplots["lun_tws_phased"].pad.cd()

            if tws_test_data["peakList"][-2] != 0:
                binToClear = subplots["lun_tws_phased"].peakGraph.FindBin(tws_test_data["peakList"][-2])
                subplots["lun_tws_phased"].peakGraph.SetBinContent(binToClear, 0)

            binToFill = subplots["lun_tws_phased"].peakGraph.FindBin(peakData)
            subplots["lun_tws_phased"].peakGraph.SetBinContent(binToFill, 500)

                
def fid_tws_update(cc, twsData):
    global subplots, fid_tws_test_data
    shotNum = twsData[0]
    times = twsData[1]
    fid_tws_test_data["chanTimesTot"].append(times)
    fid_tws_test_data["chanTimesTransient"].append(times)

    if subplots["fid_tws_phased"].status == 'alive' and subplots["fid_tws_phased"].pad != None:
            subplots["fid_tws_phased"].pad.cd()
            for time in times:
                if time != None:
                    subplots["fid_tws_phased"].mainGraph.Fill(time)

            while len(fid_tws_test_data["chanTimesTransient"]) > twsShotReserve:
                shotToRemove = fid_tws_test_data["chanTimesTransient"].pop(0)
                for time in shotToRemove:
                    if time != None:
                        binToDecrement = subplots["fid_tws_phased"].mainGraph.FindBin(time)
                        contentOfBin = subplots["fid_tws_phased"].mainGraph.GetBinContent(binToDecrement)
                        subplots["fid_tws_phased"].mainGraph.SetBinContent(binToDecrement, contentOfBin - 1)
            ROOT.gPad.Modified()


    
def tws_update(cc, twsData):
    #print "tws_update is getting called"
    global subplots, tws_test_data
    shotNum = twsData[0]
    times = twsData[1]
    tws_test_data["chanTimesTot"].append(times)
    tws_test_data["chanTimesTransient"].append(times)

    if subplots["lun_tws_phased"].status == 'alive' and subplots["lun_tws_phased"].pad != None:
            subplots["lun_tws_phased"].pad.cd()
            for time in times:
                if time != None:
                    subplots["lun_tws_phased"].mainGraph.Fill(time)

            while len(tws_test_data["chanTimesTransient"]) > twsShotReserve:
                shotToRemove = tws_test_data["chanTimesTransient"].pop(0)
                for time in shotToRemove:
                    if time != None:
                        binToDecrement = subplots["lun_tws_phased"].mainGraph.FindBin(time)
                        contentOfBin = subplots["lun_tws_phased"].mainGraph.GetBinContent(binToDecrement)
                        subplots["lun_tws_phased"].mainGraph.SetBinContent(binToDecrement, contentOfBin - 1)
            ROOT.gPad.Modified()


def stare_update(cc, stareData):
    global subplots, stare_data
    stare_data["stareShot"] += 1
    stare_data["stareNum"] += np.add.reduce(stareData) - 0.05* dark_data["sumDarkChans"]
    stare_data["stareRate"].append(np.add.reduce(stareData) - 0.05 * dark_data["sumDarkChans"])
    stare_data["averageStareRate"] = 1.0 * stare_data["stareNum"] / stare_data["stareShot"]

    #update stare rate
    if subplots["stare_rate"].status == "alive" and subplots["stare_rate"].pad != None:
        subplots["stare_rate"].pad.cd()
        subplots["stare_rate"].mainGraph.SetPoint(stare_data["stareShot"], stare_data["stareShot"], stare_data["stareRate"][-1])

        
    #update hitgrid
    if subplots["lun_hitgrid"].status == "alive" and subplots["lun_hitgrid"].pad != None:
        subplots["lun_hitgrid"].pad.cd()
        subplots["lun_hitgrid"].switch_to("Stare")
        amax = np.max(stareData)
        if amax != 0.0:
            for i in range(16):
                chanAPD = CHAN_MAP[i]
                relative_intensity = 1.00001 - 1.0 * stareData[i] / amax
                subplots["lun_hitgrid"].mainGraph.SetBinContent(chanAPD[0], chanAPD[1], relative_intensity)
        else:
            subplots["lun_hitgrid"].mainGraph.SetBinContent(0, 4, 0.01)
            for i in range(4):
                for j in range(4):
                    subplots["lun_hitgrid"].mainGraph.SetBinContent(i+1, j+1, 0.00)
                    subplots["lun_hitgrid"].mainGraph.SetFillColorAlpha(0, 0)
        ROOT.gPad.Modified()

    render(cc)


def acssweep_update_phase(cc, acssweepData):    
    global subplots
    #print "acssweepData = ", acsweepData
    newx      = acssweepData[0]
    #newIRPre  = acssweepData[1]
    newIRPost = acssweepData[2]
    #print "newx, newIRPre, newIRPost = ", newdac, ", ", newIRPre, ", ", newIRPost

    if subplots["acssweep"].status == 'alive' and subplots["acssweep"].pad != None:
        subplots["acssweep"].pad.cd()
        # update acssweep graph
        # Only need to update the IRPost graph
        subplots["acssweep"].IRPostGraph.SetPoint(subplots["acssweep"].IRPostGraph.GetN(), newx, newIRPost)
        subplots["acssweep"].mainGraph.SetMinimum( subplots["acssweep"].IRPostGraph.GetMinimum() )
        subplots["acssweep"].mainGraph.SetMaximum( subplots["acssweep"].IRPostGraph.GetMaximum() )

        subplots["acssweep"].mainGraph.GetXaxis().SetRangeUser(0, newx)
        
    render(cc)

    
def acssweep_dac_fit(plot, acs_fit_data):
    pass

def acssweep_update(cc, acssweepData):    
    global subplots
    #print "acssweepData = ", acsweepData
    newx      = acssweepData[0]
    newIRPre  = acssweepData[1]
    newIRPost = acssweepData[2]
    #newPPMon  = acssweepData[3]
    newGreen  = acssweepData[4]
    #print "newx, newIRPre, newIRPost = ", newdac, ", ", newIRPre, ", ", newIRPost

    if subplots["acssweep"].status == 'alive' and subplots["acssweep"].pad != None:
        subplots["acssweep"].pad.cd()

        # update acssweep graph
        subplots["acssweep"].IRPreGraph.SetPoint(subplots["acssweep"].IRPreGraph.GetN(), newx, newIRPre)
        subplots["acssweep"].IRPostGraph.SetPoint(subplots["acssweep"].IRPostGraph.GetN(), newx, newIRPost)
        subplots["acssweep"].greenGraph.SetPoint(subplots["acssweep"].greenGraph.GetN(), newx, newGreen)

        minPre   = subplots["acssweep"].IRPreGraph.GetMinimum()
        maxPre   = subplots["acssweep"].IRPreGraph.GetMaximum()
        minPost  = subplots["acssweep"].IRPostGraph.GetMinimum()
        maxPost  = subplots["acssweep"].IRPostGraph.GetMaximum()
        minGreen = subplots["acssweep"].greenGraph.GetMinimum()
        maxGreen = subplots["acssweep"].greenGraph.GetMaximum()
        #
        subplots["acssweep"].mainGraph.SetMinimum( min(minPre, minPost, minGreen) )
        subplots["acssweep"].mainGraph.SetMaximum( max(maxPre, maxPost, maxGreen) )

        subplots["acssweep"].mainGraph.GetXaxis().SetRangeUser(0, newx)
        
    render(cc)
    
def laser_update(cc, bolopowerData):
    global subplots, laser_data
    new = bolopowerData[0]
    laser_data["laserPower"].append(new)

    laser_data["laserPowerNum"] += 1
    x = laser_data["laserPowerNum"]

    last20average = np.add.reduce(laser_data["laserPower"][-20:]) / min(20.0, x * 1.0)
    laser_data["20AveragePower"].append(last20average)
    
    if subplots["laser_power"].status == 'alive' and subplots["laser_power"].pad != None:
        subplots["laser_power"].pad.cd()
        # update laser power graph.

        if x == 1:
            subplots["laser_power"].mainGraph.SetPoint(0, x, new)
            subplots["laser_power"].last20Graph.SetPoint(0, x, last20average)
        else:
            subplots["laser_power"].mainGraph.SetPoint(subplots["laser_power"].mainGraph.GetN(), x, new)
            subplots["laser_power"].last20Graph.SetPoint(subplots["laser_power"].last20Graph.GetN(), x, last20average)

            # Could update the Laser Power graph title to show the average power reading
            #subplots["laser_power"].mainGraph.SetTitle("Laser Power (20pt avg = %.2f)" % last20average)

    render(cc)


def flat_update(cc, flatData):
    global subplots, chanFlatCorr

    #flat_data = {"chanFlat": np.zeros(16), "usableChannel": 0, "flatSum" = 0}

    chanFlat = np.zeros(16)
    usableChannel = 0
    flatSum = 0
    
    for i in range(16):
        chanFlat[i] = flatData[i] - chanBackground[i]
        if i not in omitTDCChan:
            usableChannel += 1
            flatSum += chanFlat[i]

    ave = 1.0 * flatSum / usableChannel
    chanFlatCorr = 1.0* chanFlat / ave

    for i in range(16):
        if i in omitTDCChan or chanFlatCorr[i] <= 0.0:
            chanFlatCorr[i] = 1.0

            
    amax = float(max(chanFlatCorr))
    if amax <= 0.0:
        amax = 1.0
            
    if subplots["lun_hitgrid"].status == 'alive' and subplots["lun_hitgrid"].pad != None:
        subplots["lun_hitgrid"].pad.cd()
        subplots["lun_hitgrid"].switch_to("Flat")
        for i in range(16):
            chanAPD = CHAN_MAP[i]
            subplots["lun_hitgrid"].mainGraph.SetBinContent(chanAPD[0], chanAPD[1], 1.00001 - chanFlatCorr[i] / amax)
        ROOT.gPad.Modified()

    cc.Update()


        
def dark_update(cc, darkData):


    global dark_data, subplots, omitTDCChan, chanBackground

    dark_data["sumDarkChans"] = 0
    new_omit = []
    
    for i in range(len(darkData)):
        if darkData[i] != None:
            if darkData[i] <= 3000:
                dark_data["sumDarkChans"] += darkData[i]
                chanBackground[i] = darkData[i]
                if i in omitTDCChan:
                    omitTDCChan.remove(i)
                
            else:
                new_omit.append(i)
                chanBackground[i] = 0.0
                if i not in omitTDCChan:
                    omitTDCChan.append(i)
        else:
            chanBackground[i] = 0.0

    amax = max(chanBackground) if sum(chanBackground) > 0.0 else 1.0
            
            
    if subplots["lun_hitgrid"].status == 'alive' and subplots["lun_hitgrid"].pad != None:
        subplots["lun_hitgrid"].pad.cd()
        subplots["lun_hitgrid"].switch_to("Dark")
        for i in range(16):
            if i not in omitTDCChan:
                intensity = 1.00001 - 1.0 * chanBackground[i] / amax
            else:
                intensity = 0.0
            subplots["lun_hitgrid"].mainGraph.SetBinContent(CHAN_MAP[i][0], CHAN_MAP[i][1], intensity)

        ROOT.gPad.Modified()

    cc.Update()


    
def predskew_update(cc, center = regCenter):
    global regCenter, lunLower, lunUpper, subplots
    regCenter = center
    lunLower = center - binForReg/2.0
    lunUpper = center + binForReg/2.0
    if subplots["lun_hist"].status == 'alive' and subplots["lun_hist"].pad != None:
        subplots["lun_hist"].pad.cd()
        subplots["lun_hist"].lowerGraph.SetPoint(0, lunLower, 0)
        subplots["lun_hist"].lowerGraph.SetPoint(1, lunLower, 2000)
        subplots["lun_hist"].upperGraph.SetPoint(0, lunUpper, 0)
        subplots["lun_hist"].upperGraph.SetPoint(1, lunUpper, 2000)

    if subplots["lun_strip"].status == 'alive' and subplots["lun_strip"].pad != None:
        subplots["lun_strip"].pad.cd()
        subplots["lun_strip"].lowerGraph.SetPoint(0, 0, lunLower)
        subplots["lun_strip"].lowerGraph.SetPoint(1, 99000, lunLower)
        subplots["lun_strip"].upperGraph.SetPoint(0, 0, lunUpper)
        subplots["lun_strip"].upperGraph.SetPoint(1, 99000,lunUpper)
        subplots["lun_strip"].set_y_range(center)

    render(cc)

def fidskew_update(cc, center = regCenterFid):
    global regCenterFid, fidLower, fidUpper, subplots
    regCenterFid = center
    fidLower = center - binForRegFid/2.0
    fidUpper = center + binForRegFid/2.0
    #print "fidskew center: ", center
    if subplots["fid_hist"].status == 'alive' and subplots["fid_hist"].pad != None:
        subplots["fid_hist"].pad.cd()
        subplots["fid_hist"].lowerGraph.SetPoint(0, fidLower, 0)
        subplots["fid_hist"].lowerGraph.SetPoint(1, fidLower, 2000)
        subplots["fid_hist"].upperGraph.SetPoint(0, fidUpper, 0)
        subplots["fid_hist"].upperGraph.SetPoint(1, fidUpper, 2000)

    render(cc)


    
#def rendering(cc):
#    while UPDATING_FLAG == True:
#        cc.Update()
#        time.sleep(0.5)


def render(cc):
    # unthreaded
    global last_update_time
    if time.time() - last_update_time > 0.1:
        cc.Update()
        last_update_time = time.time()


if __name__ == "__main__":
    
    myPlot = create_plots()
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST,PORT))

    #secondThread = threading.Thread(target = receive_data, args = (s, myPlot))
    #secondThread.start()
    
    #myOneThread = threading.Thread(target = rendering, args = (myPlot,))
    #myOneThread.start()
    
    receive_data(s, myPlot)
    ROOT.gSystem.ProcessEvents()
    ROOT.gApplication.Run()
