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

# STATES: 0 -> Waiting for input with periodic updates
#         1 -> Needs to send a triggered update


class RIProuter:
     def __init__(self,configFile):
          self.periodic = 0
          self.updateFlag = 0
          self.configFile = configFile  
          self.parse_config()
          self.socket_setup()
          self.routingTable = RoutingTable(self.timers[1],self.timers[2]) # timeout and garbage considered
          
          
          print('routerID =',self.routerID)
          print('inport numbers =',self.inPort_numbers)
         
          print('peerInfo =',self.peerInfo)
          print('timers =',self.timers)
          print('table=\n',self.routingTable)
          
          
     def socket_setup(self):
          self.inPorts = []
          for portn in self.inPort_numbers:
               newSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
               newSocket.bind((HOST_ID, portn))
               self.inPorts += [newSocket]
               
               
     def close_sockets(self):
          ''' Close all sockets'''
          for port in self.inPorts:
               port.close()               
                     
                
     def parse_config(self):
          ''' Parse the supplied config file'''
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
               print("update sent to {}".format(peerID))
               OutSock = self.inPorts[i]
               
               peerPort = self.peerInfo[peerID][0]
               response = self.responsePacket(peerID)
               
               OutSock.sendto(response.encode('UTF-8'),(HOST_ID,peerPort))
               
               i += 1
               
     
     def responsePacket(self, peerID):
          ''' Construct a response packet suitable for a periodic or triggered update'''
          packet = ""
          packet += rip_header(self.routerID)
          for Entry in self.routingTable:
               # Implement split horizon with poisson reverse
               if (Entry.nextHop == peerID) or (Entry.garbageFlag == 1):
                    print("split horizon entry sent to {}".format(peerID))
                    packet += RTE(TableEntry(Entry.dest, INF, Entry.nextHop)) # set metric to INF
               else:
                    packet += RTE(Entry)
          
          return packet
               
     def proccess_rip_packet(self, packet):
          ''' Processes a RIP packet'''
          recieved_distances = [] # list of (dest, distance)
          n_RTEs = len(packet[8:])//(8*5)
          """Check packet feilds are correct here"""
          peerID = int(packet[4:8],16)
          if peerID < 1 or peerID > 64000:
               print("[Error] peerID {} out of range".format(peerID))
               #need to do something here 
          print("Proccessing packet from {}".format(peerID))
          cost = self.peerInfo[peerID][1]
          
          # Consider direct link to peer Router
          incomingEntry = self.routingTable.getEntry(peerID)
          if incomingEntry is None:
               print("added directlink entry to router {}".format(peerID))
               self.routingTable.addEntry(peerID, cost, peerID)
          else:
               incomingEntry.timeout = 0 # Reinitialise timeout for this link
               incomingEntry.garbageFlag = 0
               incomingEntry.garbage = 0               
               
          
          i = 8 # Start of first RTE
          while i < len(packet):
               
               dest = int(packet[i+8:i+16],16) # Read dest from RTE
               metric = int(packet[i+32:i+40],16) # Read metric from RTE
               
               new_metric = min(metric + cost, INF) # update metric
               currentEntry = self.routingTable.getEntry(dest)
              
               if new_metric >= INF:
                    print("Metric grater than {} and so is unreachable".format(INF))
                    #do something here
               
               if (currentEntry is None):
                    print("current entry is NONE!")
                    if (new_metric < INF): # Add a new entry
                         NewEntry = TableEntry(dest, new_metric, peerID)
                         print('new Entry {}'.format(NewEntry))
                         self.routingTable.addEntry(dest, new_metric, peerID)
                    
               else: # Compare to existing entry
                    
                    print("Existing entry for {}".format(dest))
                    if (currentEntry.nextHop == peerID): # Same router as existing route
                         
                         currentEntry.timeout = 0 # Reinitialise timeout
                         currentEntry.garbageFlag = 0
                         currentEntry.garbage = 0
                         
                         if (new_metric != currentEntry.metric):
                              self.existingRouteUpdate(currentEntry, new_metric, peerID)                                 
                                   
                              
                              
                    elif (new_metric < currentEntry.metric):
                         print("update route to {}".format(dest))
                         self.existingRouteUpdate(currentEntry, new_metric, peerID)     
                                                           
                              
                                                 
               
               
               i += (8*5) # Proceed to next RTE
               
               
     def existingRouteUpdate(self, currentEntry, new_metric, peerID):
          currentEntry.metric = new_metric
          print("route to {} updated to metric = {}".format(currentEntry.dest,new_metric))
          currentEntry.nextHop = peerID
                    
          if (new_metric >= INF):
               print("Triggered update flag set")
               self.updateFlag = 1 #Set some update flag                               
               currentEntry.garbageFlag = 1                                     
          
          
               
          
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
               print("|{:>5} |{:>7} |{:>8} |{:>5} |{:>8.3f} |{:>8.3f} |".format(
                    Entry.dest, Entry.metric, Entry.nextHop, Entry.garbageFlag,
                    Entry.timeout, Entry.garbage))
               
          return blank
          
     def addEntry(self,dest, metric, nextHop):
          self.table += [TableEntry(dest, metric, nextHop)]
          
     def removeEntry(self, Entry):
          print("Entry {} removed".format(Entry))
          self.table.remove(Entry)
          
     def getEntry(self, dest):
          ''' returns required table entry if already present'''
          i = 0
          while i < len(self.table):
               Entry = self.table[i]
               if Entry.dest == dest:
                    return Entry
               
               i += 1
                    
          return None
     
          
          
class TableEntry:
     def __init__(self,dest, metric, nextHop):
          self.dest = dest
          self.metric = metric
          self.nextHop = nextHop
          self.garbageFlag = 0
          self.timeout = 0
          self.garbage = 0
          
     def __repr__(self):
          return str((self.dest, self.metric,
                      self.nextHop, self.garbageFlag, self.timeout, self.garbage))
          
          

def main():
     configFile = open(sys.argv[1])
     #configFile = open("router1.conf") # Just for developement
     router = RIProuter(configFile)
     selecttimeout = 0.5
     
     starttime = time.time() #Gets the start time before processing
     
     while(1):
          ## Wait for at least one of the sockets to be ready for processing
          print("table reads\n",router.routingTable)
          
          #print('\nwaiting for the next event')
          readable, writable, exceptional = select.select(router.inPorts, [], router.inPorts, selecttimeout) #block for incoming packets for half a second
          
          # Send triggered updates at this stage
          if (router.updateFlag == 1):
               router.SendUpdates()
               router.updateFlag = 0
          
          for sock in readable:
               
               packet = sock.recv(MAX_BUFF).decode('UTF-8')
               router.proccess_rip_packet(packet)
          
          timeInc = (time.time() - starttime) #finds the time taken on processing
          #print("proc time = {}".format(timeInc))
          starttime = time.time()
          router.periodic += timeInc
          
          if (router.periodic >= router.timers[0]): # Periodic update
               router.SendUpdates()
               router.periodic = 0 # Reset periodic timer
               print("Periodic update")
               
          for Entry in router.routingTable:     
               
               if (Entry.garbageFlag == 1):
                    Entry.garbage += timeInc
                    if (Entry.garbage >= router.timers[2]): # Garbage collection
                         print('Removed {}'.format(Entry))
                         router.routingTable.removeEntry(Entry)                    
                    
               else:
                    Entry.timeout += timeInc
                    if (Entry.timeout >= router.timers[1]): # timeout/delete event
                         print('Timeout')
                         Entry.metric = INF
                         router.updateFlag = 1 # require triggered update
                         Entry.garbageFlag = 1 # Set garbage flag                    
               
                         
          
             
             
             
# Small developement test case
t = RoutingTable(18,12)
t.addEntry(2, 4, 3)
t.addEntry(1, 5, 6)
t.addEntry(5, 3, 3)

for Entry in t:
     pass
    
main()
