#!/usr/bin/python

# REMEMBER bytes.hex() and bytes.fromhex()

def bytes_to_int(byte_string):
     return int.from_bytes(byte_string, byteorder='big')

#def int_to_bytes(myint,size):
     #''' converts integer to 'size' number of bytes'''
     #return (myint).to_bytes(size, byteorder='big').hex()
     
     
def int_to_bytes(myint, size):
     suffix = hex(myint)[2:]
     prefix = '0'*(2*size-len(suffix))
     return (prefix + suffix)

def rip_header(routerID):
     header = '0201' + int_to_bytes(routerID,2)
     return header
  
def RTE(Entry):
     zero_row =  int_to_bytes(0,4)
     s = zero_row
     s+= int_to_bytes(Entry.dest,4)
     s+= zero_row
     s+= zero_row
     s+= int_to_bytes(Entry.metric,4)
     return(s)


def rip_packet_info(packet):
     ''' Extracts relevent info from a RIP response packet'''
     
     RTEs = []
     
     peerID = int(packet[4:8],16)
     
     i = 8 # Start of first RTE
     while i < len(packet):
          
          dest = int(packet[i+8:i+16],16) # Read dest from RTE
          metric = int(packet[i+32:i+40],16) # Read metric from RTE
          RTEs += [(dest, metric)]
          
          i += (8*5) # Proceed to next RTE
          
     return(peerID,RTEs)