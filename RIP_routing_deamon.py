#!/usr/bin/python
import sys
import select
import socket 

#Random edit

class RIProuter:
     def __init__(self,configFile):
          self.configFile = configFile  #Try a 'state' variable?
          self.parse_config()
          self.socket_setup()
          self.table = [] # to be a list of triplets (dest, D, next-hop)
          print('routerID =',self.routerID)
          print('inport numbers =',self.inPort_numbers)
          #print('inPorts =',self.inPorts)
          print('outports =',self.outPorts)
          print('timers =',self.timers)
          
          
     def socket_setup(self):
          #host = socket.gethostname()
          self.inPorts = []
          for portn in self.inPort_numbers:
               newSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
               newSocket.bind(('127.0.0.1', portn)) # binding may be incorrect
               self.inPorts += [newSocket]
               
               
     def close_sockets(self):
          for port in self.inPorts:
               port.close()               
                     
          
                
     def parse_config(self):
          lines = self.configFile.readlines()
          for line in lines:
               entries = line.split(',')
               #print(entries)
               lineType = entries[0]
               tail = entries[1:]
               if lineType == 'router-id':
                    self.routerID = getID(tail)
                    
               elif lineType == 'input-ports':
                    self.inPort_numbers = getInPort_numbers(tail)
               
               elif lineType == 'outputs':
                    self.outPorts = getOutPorts(tail)
               
               elif lineType == 'timers':
                    self.timers = getTimers(tail)
                    
                    
          
               
                    
      


def getID(tail):
     myID = int(tail[0])
     if myID in range(1,64001):
          return myID
     
     else:
          raise(IndexError('Router ID not valid'))     
     
     
def getInPort_numbers(tail):
     ports = []
     for portstring in tail:
          port = int(portstring)
          if (port not in ports) and (port in range(1024,64001)):
               ports += [port]
          else:
               print("invalid inport port {} supplied".format(port))
     return ports

def getOutPorts(tail):
     portinfo = []
     for triplet in tail:
          portN,metric,peerID = triplet.split('-')
          portinfo += [[int(portN),int(metric),int(peerID)]]
     return portinfo


def getTimers(tail):
     timers = []
     for entry in tail:
          timers += [int(entry)]
          
     return timers
     
               
     
     

def main():
     configFile = open(sys.argv[1])
     router = RIProuter(configFile)
     while(1):
          ## Wait for at least one of the sockets to be ready for processing
          readable, writable, exceptional = select.select(router.inPorts, [], router.inPorts)
    
    
main()
