#!/usr/bin/python
import sys
import select
import socket 
import base64
import RIP_packet

MAX_BUFF = 600
MAX_DATA = 512

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
                    self.getID(tail)
                    
               elif lineType == 'input-ports':
                    self.getInPort_numbers(tail)
               
               elif lineType == 'outputs':
                    self.getOutPorts(tail)
               
               elif lineType == 'timers':
                    self.getTimers(tail)
                    
                    
     def getID(self,tail):
          myID = int(tail[0]) 
          if myID in range(1,64001):
               self.routerID = int(tail[0])
          
          else:
               raise(IndexError('Router ID not valid'))     
     
     
     def getInPort_numbers(self,tail):
          self.inPort_numbers = []
          for portstring in tail:
               port = int(portstring)
               if (port not in self.inPort_numbers) and (port in range(1024,64001)):
                    self.inPort_numbers += [port]
               else:
                    print("invalid inport port {} supplied".format(port))
               

     def getOutPorts(self,tail):
          self.outPorts = dict()
          for triplet in tail:
               portN,metric,peerID = triplet.split('-')
               self.outPorts[int(peerID)] = (int(portN),int(metric))


     def getTimers(self,tail):
          self.timers = []
          for entry in tail:
               self.timers += [int(entry)]
               
          
     

def main():
     configFile = open(sys.argv[1])
     router = RIProuter(configFile)
     while(1):
          ## Wait for at least one of the sockets to be ready for processing
          print('\nwaiting for the next event')
          readable, writable, exceptional = select.select(router.inPorts, [], router.inPorts)
          
          for sock in readable:
               data, sender = sock.recvfrom(MAX_BUFF)
               
    
main()
