"""
#RIP_routing_daemon.py
#Authors: George Drummond - gmd44
#         Ryan Cox - rlc96
#Last Edit: 5/4/2017
#
#Routing demon instance participates in the version 2 RIP routing protocol.
#Demon emulates a router in a given network from the supplied config file.
#
"""

#!/usr/bin/python
import sys
import select
import socket 
import random
from RIP_packet import *
from writelog import *
import time

MAX_BUFF = 600
MAX_DATA = 512
INF = 16
HOST_ID = '127.0.0.1'

# Router STATES: 0 -> Waiting for input with periodic updates
#                1 -> Needs to send a triggered update

def valid_portn(portn):
     return int(portn) in range(1024,64001)

def valid_ID(routerID):
     return int(routerID) in range(1,64001)

def valid_metric(metric):
     return int(metric) in range(0,INF+1)



class RIProuter:
     '''RIP router class'''
     def __init__(self,configFile):
          self.periodic = 0
          self.updateFlag = 0
          self.configFile = configFile  
          self.parse_config()
          self.socket_setup()
          self.routingTable = RoutingTable(self.timers[1],self.timers[2]) # timeout and garbage considered
          self.log = init_log(self.routerID)
          
          print('routerID =',self.routerID)
          print('inport numbers =',self.inPort_numbers)
         
          print('peerInfo =',self.peerInfo)
          print('timers =',self.timers)
          print('table=\n',self.routingTable)
          
          
     def socket_setup(self):
          '''Sets up a socket with each of the given port numbers'''
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
                    self.set_ID(tail)
                    
               elif lineType == 'input-ports':
                    self.set_InPort_numbers(tail)
               
               elif lineType == 'outputs':
                    self.set_peerInfo(tail)
               
               elif lineType == 'timers':
                    self.set_timers(tail)
                    
                    
     def set_ID(self,tail):
          ''' Checks and stores routerID'''
          myID = int(tail[0]) 
          if valid_ID(myID):
               self.routerID = int(tail[0])
          
          else:
               raise(IndexError('Router ID not valid'))     
     
     
     def set_InPort_numbers(self,tail):
          ''' Checks and stores all supplied inport numbers'''
          self.inPort_numbers = []
          for portstring in tail:
               port = int(portstring)
               if (port not in self.inPort_numbers) and valid_portn(port):
                    self.inPort_numbers += [port]
               else:
                    print("invalid inport port {} supplied".format(port))
               

     def set_peerInfo(self,tail):
          ''' Stores info relevent to immediate neighbours '''
          self.peerInfo = dict()
          for triplet in tail:
               portN,metric,peerID = triplet.split('-')
               if valid_portn(portN) and valid_metric(metric) and valid_ID(peerID):
                    self.peerInfo[int(peerID)] = (int(portN),int(metric))
               else:
                    print("invalid peer info for peer {}".format(peerID))               


     def set_timers(self,tail):
          ''' Stores supplied timer info (i.e. periodic, timeout, garbage)'''
          self.timers = []
          for entry in tail:
               self.timers += [int(entry)]
               
               
               
     def send_updates(self):
          ''' Sends an update message to each neighbour'''
          i = 0
          for peerID in self.peerInfo.keys():
               #print("update sent to {}".format(peerID))
               write_to_log(self.log,
                            "Sent update to {}".format(peerID))
               OutSock = self.inPorts[i] # use a different socket to send each
               
               peerPort = self.peerInfo[peerID][0]
               response = self.response_packet(peerID)
               
               OutSock.sendto(response.encode('UTF-8'),(HOST_ID,peerPort))
               
               i += 1
               
     
     def response_packet(self, peerID):
          ''' Construct a response packet destined to a neighboring router.
              Suitable for a periodic or triggered update'''
          
          packet = ""
          packet += rip_header(self.routerID)
          for Entry in self.routingTable:
               # Implement split horizon with poisson reverse
               if (Entry.nextHop == peerID) or (Entry.garbageFlag == 1):
                    #print("split horizon entry sent to {}".format(peerID))
                    packet += RTE(TableEntry(Entry.dest, INF, Entry.nextHop)) # set metric to INF
               else:
                    packet += RTE(Entry)
          
          return packet
               
     def process_rip_packet(self, packet):
          ''' Processes a RIP response packet'''
          
          (peerID,RTEs) = rip_packet_info(packet)
          
          
          if not valid_ID(peerID):
               print("[Error] peerID {} out of range".format(peerID))
               write_to_log(self.log, "[Error] peerID {} out of range".format(peerID))
                
               
          #print("processing packet from {}".format(peerID))
          cost = self.peerInfo[peerID][1]
          
          # Consider direct link to peer Router
          incomingEntry = self.routingTable.get_entry(peerID)
          if incomingEntry is None:
               #print("added directlink entry to router {}".format(peerID))
               self.routingTable.add_entry(peerID, cost, peerID)
          else:
               incomingEntry.metric = cost
               incomingEntry.nextHop = peerID
               incomingEntry.timeout = 0 # Reinitialise timeout for this link
               incomingEntry.garbageFlag = 0
               incomingEntry.garbage = 0               
               
          
          
          for RTE in RTEs:
               self.processRTE(RTE, peerID, cost)
               
               
     def processRTE(self, RTE, peerID, cost):
          '''processes an RTE of a RIP responce packet from a peer router'''
          (dest, metric) = RTE
               
          new_metric = min(metric + cost, INF) # update metric

          """check metric here?"""
          currentEntry = self.routingTable.get_entry(dest)


              
          if new_metric >= INF :
               #print("Path ({},{}) from {} not processed as unreachable".format(dest, metric,peerID))
               write_to_log(self.log, 
                    "Path ({},{}) from {} not processed as unreachable".format(dest, metric,peerID))
                    
               
          elif (currentEntry is None):
               #print("current route not in table")
               if (new_metric < INF): # Add a new entry
                    NewEntry = TableEntry(dest, new_metric, peerID)
                    #print('new Entry {}'.format(NewEntry))
                    write_to_log(self.log,
                         "New route added from {} to {} with Metric {}"
                         .format(self.routerID, NewEntry, new_metric))
                         

                    self.routingTable.add_entry(dest, new_metric, peerID)
                    
          else: # Compare to existing entry
                    
               #print("Existing entry for {}".format(dest))
               if (currentEntry.nextHop == peerID): # Same router as existing route
                         
                    currentEntry.timeout = 0 # Reinitialise timeout
                    currentEntry.garbageFlag = 0
                    currentEntry.garbage = 0
                         
                    if (new_metric != currentEntry.metric):
                         self.existing_route_update(currentEntry, new_metric, peerID)                                 
                                   
                              
                              
               elif (new_metric < currentEntry.metric):
                    #print("update route to {}".format(dest))
                    write_to_log(self.log,
                              "Route from {} to {} updated with new Metric {}"
                              .format(self.routerID, dest, new_metric))
                    self.existing_route_update(currentEntry, new_metric, peerID)     
                                                           
                              
                                                 
               
               
               
               
               
     def existing_route_update(self, currentEntry, new_metric, peerID):
          ''' updates an existing routing table entry with a new metric'''
          currentEntry.metric = new_metric
          #print("route to {} updated to metric = {}".format(currentEntry.dest,new_metric))
          currentEntry.nextHop = peerID
                    
          if (new_metric >= INF):
               #print("Triggered update flag set")
               self.updateFlag = 1 #Set update flag                               
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
          
     def add_entry(self,dest, metric, nextHop):
          self.table += [TableEntry(dest, metric, nextHop)]
          
     def remove_entry(self, Entry):
          print("Entry {} removed".format(Entry))
          self.table.remove(Entry)
          
     def get_entry(self, dest):
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
     periodicWaitTime = router.timers[0]
     
     starttime = time.time() #Gets the start time before processing
     
     while(1):
          try:
               # Wait for at least one of the sockets to be ready for processing
               print("Router {}\n".format(router.routerID),router.routingTable)
               readable, writable, exceptional = select.select(router.inPorts, [], router.inPorts, selecttimeout) #block for incoming packets for half a second
               
               # Send triggered updates at this stage
               if (router.updateFlag == 1):
                    router.send_updates()
                    router.updateFlag = 0
               
               for sock in readable:
                    
                    packet = sock.recv(MAX_BUFF).decode('UTF-8')
                    router.process_rip_packet(packet)
               
               timeInc = (time.time() - starttime) #finds the time taken on processing
               #print("proc time = {}".format(timeInc))
               starttime = time.time()
               router.periodic += timeInc
               
               if (router.periodic >= periodicWaitTime): # Periodic update
                    router.send_updates()
                    #Recalculate new random wait time in [0.8*periodic, 1.2*periodic]
                    periodicWaitTime = random.uniform(0.8*router.timers[0],1.2*router.timers[0])
                    
                    router.periodic = 0 # Reset periodic timer
                    #print("Periodic update")
                    
               for Entry in router.routingTable:     
                    
                    if (Entry.garbageFlag == 1):
                         Entry.garbage += timeInc
                         if (Entry.garbage >= router.timers[2]): # Garbage collection
                              #print('Removed {}'.format(Entry))
                              write_to_log(router.log,
                                           "[Warning] Route from {} to {} has been removed"
                                           .format(router.routerID, Entry.dest))
                              router.routingTable.remove_entry(Entry)                    
                         
                    else:
                         Entry.timeout += timeInc
                         if (Entry.timeout >= router.timers[1]): # timeout/delete event
                              #print('Timeout')
                              write_to_log(router.log, 
                                           "[Warning] Route from {} to {} has timed out"
                                           .format(router.routerID, Entry.dest))
                              Entry.metric = INF
                              router.updateFlag = 1 # require triggered update
                              Entry.garbageFlag = 1 # Set garbage flag     
                              
          except KeyboardInterrupt: # 'Taking down' router
               print("Exiting program")
               close_log(router.log)
               router.close_sockets()
               break
             
    
main()
