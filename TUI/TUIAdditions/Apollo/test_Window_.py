


import RO.Alg
import tkinter as Tk


def addWindow(tlSet):

    tlSet.createToplevel(
        name = "Whatever",
        defGeom = "+10+10",
        resizable = True,
        wdgFunc = fibWdg,
        visible = True)



class fibWdg(Tk.Frame):
    def __init__(self, parent):
        Tk.Frame.__init__(self, parent)
        self.label1 = Tk.Label(self, text = "Result here:")
        self.label1.pack(pady = 10, padx = 10)
        self.label2 = Tk.Label(self, text = "")
        self.label2.pack()
        
        self.e = Tk.Entry(self)
        self.e.pack(pady =10, padx =10)
        self.e.focus_set()
        self.button1 = Tk.Button(self, text = "get Fibonacci number", command = lambda: self.getFib())
        self.button1.pack(pady = 10)

        
    def fib(self, n):
        n = int(n)
        try:
            if n == 0 or n == 1:
                return n
            return self.fib(n-1) + self.fib(n-2)
        except:
            pass

    def getFib(self):
        n = int(self.e.get())
        f = self.fib(n)
        text = "Fib %i: %i" % (n, f)
        self.label2.configure(text = text)
        
        
