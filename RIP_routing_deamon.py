#!/usr/bin/python
import sys
import select
import socket 
import base64
from RIP_packet import *
import time

MAX_BUFF = 600
MAX_DATA = 512
INF = 16
HOST_ID = '127.0.0.1'


class RIProuter:
     def __init__(self,configFile):
          self.periodic = 0
          self.configFile = configFile  #Try a 'state' variable?
          self.parse_config()
          self.socket_setup()
          self.routingTable = RoutingTable(self.timers[1],self.timers[2]) # to be a list of TableEntry objects
          
          
          print('routerID =',self.routerID)
          print('inport numbers =',self.inPort_numbers)
         
          print('peerInfo =',self.peerInfo)
          print('timers =',self.timers)
          print('table=\n',self.routingTable)
          
          
     def socket_setup(self):
          #host = socket.gethostname()
          self.inPorts = []
          for portn in self.inPort_numbers:
               newSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
               newSocket.bind(('127.0.0.1', portn)) # binding may be incorrect
               self.inPorts += [newSocket]
               
               
     def close_sockets(self):
          ''' Close all sockets'''
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
                    self.setID(tail)
                    
               elif lineType == 'input-ports':
                    self.setInPort_numbers(tail)
               
               elif lineType == 'outputs':
                    self.setpeerInfo(tail)
               
               elif lineType == 'timers':
                    self.setTimers(tail)
                    
                    
     def setID(self,tail):
          myID = int(tail[0]) 
          if myID in range(1,64001):
               self.routerID = int(tail[0])
          
          else:
               raise(IndexError('Router ID not valid'))     
     
     
     def setInPort_numbers(self,tail):
          self.inPort_numbers = []
          for portstring in tail:
               port = int(portstring)
               if (port not in self.inPort_numbers) and (port in range(1024,64001)):
                    self.inPort_numbers += [port]
               else:
                    print("invalid inport port {} supplied".format(port))
               

     def setpeerInfo(self,tail):
          self.peerInfo = dict()
          for triplet in tail:
               portN,metric,peerID = triplet.split('-')
               self.peerInfo[int(peerID)] = (int(portN),int(metric))


     def setTimers(self,tail):
          self.timers = []
          for entry in tail:
               self.timers += [int(entry)]
               
               
               
     def SendUpdates(self):
          i = 0
          for peerID in self.peerInfo.keys():
               OutSock = self.inPorts[i]
               
               peerPort = self.peerInfo[peerID][0]
               response = self.responsePacket(peerID)
               # SOMEHOW SEND PACKET
               #OutSock.connect((HOST_ID,peerPort))
               OutSock.sendto(response.encode('UTF-8'),(HOST_ID,peerPort))
               
               i += 1
               
     
     def responsePacket(self, peerID):
          ''' Construct a response packet suitable for a periodic or triggered update'''
          packet = ""
          packet += rip_header(self.routerID)
          for Entry in self.routingTable:
               # Implement split horizon
               if (Entry.dest == peerID):
                    Entry = TableEntry(Entry.dest, INF, Entry.nextHop) # set metric to INF
                    
               packet += RTE(Entry)
          
          return packet
               
     def proccess_rip_packet(self, packet):
          ''' Processes a RIP packet'''
          recieved_distances = [] # list of (dest, distance)
          n_RTEs = len(packet[8:])//(8*5)
          
          peerID = int(packet[4:8],16)
          cost = self.peerInfo[peerID][1]
          
          # Consider direct link to peer Router
          incomingEntry = self.routingTable.getEntry(peerID)
          if incomingEntry is None:
               print("added directlink entry to router {}".format(peerID))
               self.routingTable.addEntry(peerID, cost, peerID)
               
          
          i = 8 # Start of first RTE
          while i < len(packet):
               
               dest = int(packet[i+8:i+16],16) # Read dest from RTE
               metric = int(packet[i+32:i+40],16) # Read metric from RTE
               
               new_metric = min(metric + cost, INF) # update metric
               
               currentEntry = self.routingTable.getEntry(dest)
               
               if (currentEntry is None):
                    if (new_metric < INF): # Add a new entry
                         NewEntry = TableEntry(dest, new_metric, peerID)
                         print('new Entry {}'.format(NewEntry))
                         self.routingTable.addEntry(dest, new_metric, peerID)
                         
                    
               else: # Compare to existing entry
                    #currentEntry.setstate0()
                    currentEntry.timeout = 0 # Reinitialise timeout
                    currentEntry.flag = 0
                    currentEntry.garbage = 0
                    
                    if (currentEntry.nextHop == peerID): # Same router as existing route
                         if (new_metric != metric):
                              currentEntry.metric = new_metric
                              
                              if (new_metric == INF):
                                   currentEntry.flag = 1
                                   #START DELETION
                              
                              
                    elif (new_metric < metric):
                         print("update route to {}".format(dest))
                         currentEntry.metric = new_metric
                         currentEntry.nextHop = peerID
                         #MUST ALSO TRIGGER AN UPDATE HERE
                         if (new_metric == INF):
                              currentEntry.flag = 1
                              #START DELETION
                                                 
               
               
               i += (8*5) # Proceed to next RTE
          
          
               
          
class RoutingTable:
     def __init__(self, timeoutMax, garbageMax):
          self.table = []
          self.timeoutMax = timeoutMax
          self.garbageMax = garbageMax
          
     def __iter__(self):
          i = 0
          while i < len(self.table):
               yield(self.table[i])
               i += 1
               
     def __repr__(self):
          blank = "-" * 54
          print(blank + "\n| dest | metric | nextHop | flag | timeout | garbage |")
          for Entry in self.table:
               print("|{:>5} |{:>7} |{:>8} |{:>5} |{:>8} |{:>8} |".format(
                    Entry.dest, Entry.metric, Entry.nextHop, Entry.flag,
                    Entry.timeout, Entry.garbage))
               
          return blank
          
     def addEntry(self,dest, metric, nextHop):
          self.table += [TableEntry(dest, metric, nextHop)]
          
     def removeEntry(self, Entry):
          print("Entry {} removed".format(Entry))
          self.table.remove(Entry)
          
     def getEntry(self, dest):
          ''' returns required table entry if already present'''
          for Entry in self.table:
               if Entry.dest == dest:
                    return Entry
                    
          return None
     
          
          
class TableEntry:
     def __init__(self,dest, metric, nextHop):
          self.dest = dest
          self.metric = metric
          self.nextHop = nextHop
          self.flag = 0
          self.timeout = 0
          self.garbage = 0
          
     def __repr__(self):
          return str((self.dest, self.metric,
                      self.nextHop, self.flag, self.timeout, self.garbage))
          
          

def main():
     configFile = open(sys.argv[1])
     #configFile = open("router1.conf") # Just for developement
     router = RIProuter(configFile)
     selecttimeout = 0.5
     
     starttime = time.time() #Gets the start time before processing
     
     while(1):
          ## Wait for at least one of the sockets to be ready for processing
          
          print('\nwaiting for the next event')
          readable, writable, exceptional = select.select(router.inPorts, [], router.inPorts, selecttimeout) #block for incoming packets for half a second
          
          for sock in readable:
               
               packet = sock.recv(MAX_BUFF).decode('UTF-8')
               print('processing packet')
               router.proccess_rip_packet(packet)
          
          timeInc = (time.time() - starttime) #finds the time taken on processing
          starttime = time.time()
          router.periodic += timeInc
          
          if (router.periodic >= router.timers[0]): # Periodic update
               router.SendUpdates()
               router.periodic = 0 # Reset periodic timer
               print("Periodic update")
               
          for Entry in router.routingTable:     
               
               if (Entry.timeout >= router.timers[1]):
                    print('Timeout')
                    Entry.flag = 1 # Set garbage flag
                    
               if (Entry.flag == 0):
                    Entry.timeout += timeInc
               else:
                    Entry.garbage += timeInc
                    if (Entry.garbage > router.timers[2]): # Garbage collection
                         print('Removed {}'.format(Entry))
                         router.routingTable.removeEntry(Entry)
             
             
             
# Small developement test case
t = RoutingTable(18,12)
t.addEntry(2, 4, 3)
t.addEntry(1, 5, 6)
t.addEntry(5, 3, 3)
    
main()
