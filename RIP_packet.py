# REMEMBER bytes.hex() and bytes.fromhex()

#testing git123

def bytes_to_int(byte_string):
     return int.from_bytes(byte_string, byteorder='big')

def int_to_bytes(myint,size):
     return (myint).to_bytes(size, byteorder='big')

def hexstring_to_bin(hexstring):
     return bin(int(hexstring, base=16))

def bin_to_hexstring(binum):
     return hex(int(binum,base = 2))


def rip_header(routerID):
     header = '0201' + int_to_bytes(routerID,2).hex()
     return header
  
def RTE(Entry):
     zero_row =  int_to_bytes(0,4).hex()
     s = zero_row
     s+= int_to_bytes(Entry.dest,4).hex()
     s+= zero_row
     s+= zero_row
     s+= int_to_bytes(Entry.metric,4).hex()
     return(s)
     
     


#def proccess_rip_packet(packet):
     #''' Processes a RIP ver 2 packet'''
     #recieved_distances = [] # list of (dest, distance)
     #n_RTEs = len(packet[8:])//(8*5)
     ##print(n_RTEs)
     #routerID = int(packet[4:8],16)
     #i = 8
     #while i < len(packet):
          
          #dest = int(packet[i+8:i+16],16)
          #metric = int(packet[i+32:i+40],16)
          #recieved_distances += [(dest,metric)]
          
          #i += (8*5)
     
     #return recieved_distances, routerID