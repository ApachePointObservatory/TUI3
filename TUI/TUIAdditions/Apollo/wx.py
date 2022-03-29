#!/usr/bin/env python
'''
Returns a weather string
'''

from socket import *    # import *, but we'll avoid name conflict

def weather():
    sock = socket(AF_INET, SOCK_DGRAM)
    messout = ""
    ip=getaddrinfo(gethostname(), None)[0][4][0]
    sock.bind((ip,6251))
    sock.sendto(messout, ('marmot.apo.nmsu.edu', 6251))
    messin, server = sock.recvfrom(512)
    #print "Received:", messin
    return messin[7:]
    sock.close()
