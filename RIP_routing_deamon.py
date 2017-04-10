#!/usr/bin/python
import sys
import select
import socket 
import base64
import RIP_packet

MAX_BUFF = 600
MAX_DATA = 512
INF = 16

class RIProuter:
     def __init__(self,configFile):
          self.configFile = configFile  #Try a 'state' variable?
          self.parse_config()
          self.socket_setup()
          self.routingTable = RoutingTable(self.timers[1],self.timers[2]) # to be a list of TableEntry objects
          print('routerID =',self.routerID)
          print('inport numbers =',self.inPort_numbers)
          #print('inPorts =',self.inPorts)
          print('peerInfo =',self.peerInfo)
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
                    self.getpeerInfo(tail)
               
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
               

     def getpeerInfo(self,tail):
          self.peerInfo = dict()
          for triplet in tail:
               portN,metric,peerID = triplet.split('-')
               self.peerInfo[int(peerID)] = (int(portN),int(metric))


     def getTimers(self,tail):
          self.timers = []
          for entry in tail:
               self.timers += [int(entry)]
               
               
               
     def triggeredUpdate(self):
          for peerID in peerInfo.keys(): # change peerInfo to peerInfo
               response = self.responsePacket(peerID)
               # SOMEHOW SEND PACKET
     
     def periodicUpdate(self):
          pass
     
     def responsePacket(self, peerID):
          packet = ""
          packet += rip_header(self.routerID)
          for Entry in self.routingTable:
               # Implement split horizon
               packet += RTE(Entry)
          
          return packet
               
     def proccess_rip_packet(self, packet):
          ''' Processes a RIP packet'''
          recieved_distances = [] # list of (dest, distance)
          n_RTEs = len(packet[8:])//(8*5)
          #print(n_RTEs)
          peerID = int(packet[4:8],16)
          cost = self.peerInfo[peerID][1]
          
          i = 8 # Start of first RTE
          while i < len(packet):
               
               dest = int(packet[i+8:i+16],16) # read dest from RTE
               metric = int(packet[i+32:i+40],16) # read metric from RTE
               
               new_metric = min(metric + cost, INF) # update metric
               
               currentEntry = self.routingTable.getEntry(dest)
               
               if ((currentEntry is None) and (new_metric < INF)): # Add a new entry
                    self.routingTable += TableEntry(dest, new_metric, peerID)
                    # DO NOT NEED TO TRIGGER AN UPDATE HERE
                    
               else: # Compare to existing entry
                    currentEntry.timout = 0 # Reinitialise timout
                    
                    if (currentEntry.nextHop == peerID): # Same router as existing route
                         if (new_metric != metric):
                              currentEntry.metric = new_metric
                              currentEntry.flag = 1
                              if (new_metric == INF):
                                   pass #START DELETION
                              
                              
                    elif (new_metric < metric):
                         currentEntry.metric = new_metric
                         currentEntry.nextHop = peerID
                         currentEntry.flag = 1# MUST ALSO TRIGGER AN UPDATE HERE
                         if (new_metric == INF):
                              pass #START DELETION
                                                 
               
               
               
               
               i += (8*5) # Proceed to next RTE
          
          
               
          
class RoutingTable:
     def __init__(self, timoutMax, garbageMax):
          self.table = []
          self.timoutMax = timoutMax
          self.garbageMax = garbageMax
          
     def __iter__(self):
          i = 0
          while i < len(self.table):
               yield(self.table[i])
               i += 1
          
     def addEntry(self,dest, metric, nextHop):
          self.table += [TableEntry(dest, metric, nextHop)]
          
     def getEntry(self, dest):
          ''' returns required table entry if already present'''
          for Entry in self.table:
               if Entry.dest == dest:
                    return Entry
                    
          return None
     
     def deleteEvent(self, Entry):
          ''' Begins deletion of an entry'''
          Entry.garbage = self.garbageMax # eg) 120 seconds
          Entry.metric = INF
          Entry.flag = 1
          # TRIGGER RESPONCE HERE
          
          
class TableEntry:
     def __init__(self,dest, metric, nextHop):
          self.dest = dest
          self.metric = metric
          self.nextHop = nextHop
          self.flag = 0
          self.timout = 0
          self.garbage = 0
          
          

def main():
     #configFile = open(sys.argv[1])
     configFile = open("router1.conf") # Just for developement
     router = RIProuter(configFile)
     selecttimeout = 0.5
     
     #starttime = time.time() #Gets the start time before processing
     
     #while(1):
          ### Wait for at least one of the sockets to be ready for processing
          
          #print('\nwaiting for the next event')
          #readable, writable, exceptional = select.select(router.inPorts, [], router.inPorts, selecttimeout) #block for incoming packets for half a second
          
          #for sock in readable:
               ##data, sender = sock.recvfrom(MAX_BUFF)
               #packet = sock.recv(MAX_BUFF)
               #router.proccess_rip_packet(packet)
          
          #timeInc = (time.time() - starttime) #finds the time taken on processing
          #starttime = time.time()
          #for Entry in router.routingtable:
               #Entry.timeout += timeInc
               #if Entry.flag != 0 || Entry.metric >= 16:
                    #Entry.garbage += timeInc
             
             
# Small developement test case
t = RoutingTable(18,12)
t.addEntry(2, 4, 3)
t.addEntry(1, 5, 6)
t.addEntry(5, 3, 3)
    
main()
