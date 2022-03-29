import os

class _popen:

    """ Fairly portable (alternative) popen implementation.

        This is mostly needed in case os.popen() is not available, or
        doesn't work as advertised, e.g. in Win9X GUI programs like
        PythonWin or IDLE.

        XXX Writing to the pipe is currently not supported.

    """
    tmpfile = ''
    pipe = None
    bufsize = None
    mode = 'r'

    def __init__(self,cmd,mode='r',bufsize=None):

        if mode != 'r':
            raise ValueError('popen()-emulation only support read mode')
        import tempfile
        self.tmpfile = tmpfile = tempfile.mktemp()
        os.system(cmd + ' > %s' % tmpfile)
        self.pipe = open(tmpfile,'rb')
        self.bufsize = bufsize
        self.mode = mode

    def read(self):

        return self.pipe.read()

    def readlines(self):

        if self.bufsize is not None:
            return self.pipe.readlines()

    def close(self,

              remove=os.unlink,error=os.error):

        if self.pipe:
            rc = self.pipe.close()
        else:
            rc = 255
        if self.tmpfile:
            try:
                remove(self.tmpfile)
            except error:
                pass
        return rc

    # Alias
    __del__ = close

def popen(cmd, mode='r', bufsize=None):

    """ Portable popen() interface.
    """
    # Find a working popen implementation preferring win32pipe.popen
    # over os.popen over _popen
    popen = None
    if os.environ.get('OS','') == 'Windows_NT':
        # On NT win32pipe should work; on Win9x it hangs due to bugs
        # in the MS C lib (see MS KnowledgeBase article Q150956)
        try:
            import win32pipe
        except ImportError:
            pass
        else:
            popen = win32pipe.popen
    if popen is None:
        if hasattr(os,'popen'):
            popen = os.popen
            # Check whether it works... it doesn't in GUI programs
            # on Windows platforms
            if sys.platform == 'win32': # XXX Others too ?
                try:
                    popen('')
                except os.error:
                    popen = _popen
        else:
            popen = _popen
    if bufsize is None:
        return popen(cmd,mode)
    else:
        return popen(cmd,mode,bufsize)

if __name__ == '__main__':
    print(""" """)
