#!/usr/bin/env python3
# Last updated: Jan, 2023
# Author: Phuthipong (Nikko)
import sys
import socket
import datetime
import time

CONNECTION_TIMEOUT = 60

# for testing with gaia server
SERVER_IP = "128.119.245.12" 
SERVER_PORT = 20008

def checksum(msg):
    """
     This function calculates checksum of an input string
     Note that this checksum is not Internet checksum.
    
     Input: msg - String
     Output: String with length of five
     Example Input: "1 0 That was the time fo "
     Expected Output: "02018"
    """

    # step1: covert msg (string) to bytes
    msg = msg.encode("utf-8")
    s = 0
    # step2: sum all bytes
    for i in range(0, len(msg), 1):
        s += msg[i]
    # step3: return the checksum string with fixed length of five 
    #        (zero-padding in front if needed)
    return format(s, '05d')

def checksum_verifier(msg):
    """
     This function compares packet checksum with expected checksum
    
     Input: msg - String
     Output: Boolean - True if they are the same, Otherwise False.
     Example Input: "1 0 That was the time fo 02018"
     Expected Output: True
    """

    expected_packet_length = 30
    # step 1: make sure the checksum range is 30
    if len(msg) < expected_packet_length:
        return False
    # step 2: calculate the packet checksum
    content = msg[:-5]
    calc_checksum = checksum(content)
    expected_checksum = msg[-5:]
    # step 3: compare with expected checksum
    if calc_checksum == expected_checksum:
        return True
    return False

def start_sender(connection_ID, loss_rate=0, corrupt_rate=0, max_delay=0, transmission_timeout=60):
    """
     This function runs the sender, connnect to the server, and send a file to the receiver.
     The function will print the checksum, number of packet sent/recv/corrupt recv/timeout at the end. 
     The checksum is expected to be the same as the checksum that the receiver prints at the end.

     Input: 
        connection_ID - String
        loss_rate - float (default is 0, the value should be between [0.0, 1.0])
        corrupt_rate - float (default is 0, the value should be between [0.0, 1.0])
        max_delay - int (default is 0, the value should be between [0, 5])
        tranmission_timeout - int (default is 60 seconds and cannot be 0)
     Output: None
    """

    ## STEP 0: PRINT YOUR NAME AND DATE TIME
    name = "Sungchan Park"
    print("START receiver - {} @ {}".format(name, datetime.datetime.now()))

    ## STEP 1: CONNECT TO THE SERVER
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # set connection timeout
    clientSocket.settimeout(CONNECTION_TIMEOUT)
    try:
        # connect to the server
        clientSocket.connect((SERVER_IP,SERVER_PORT))
    except socket.error as e:
        # print error and terminate if fail
        print('Connection error: {}'.format(e))
        clientSocket.close()
        sys.exit()
    # disable timeout 
    clientSocket.settimeout(None)
    # request a relay service
    message = "HELLO S {} {} {} {}".format(loss_rate, corrupt_rate, max_delay, connection_ID)
    clientSocket.sendall(message.encode("utf-8"))
    print("sending: {}".format(message))
    # wait for message
    recv_message = clientSocket.recv(1024).decode("utf-8")
    print("received: {}".format(recv_message))
    # check response and keep waiting or terminate if the respond is not OK
    while not recv_message.startswith("OK"):
        if recv_message.startswith("WAITING"):
            # wait
            print("Waiting for a receiver")
            recv_message = clientSocket.recv(1024).decode("utf-8")
            
        elif recv_message.startswith("ERROR"):
            # print error and terminate
            print("Error: {}".format(recv_message.split(' ')[1]))
            exit()
        else:
            # invalid message, print and temrinate
            print("Error: Invalid message from server during connection. The message is {}".format(recv_message))
            exit()

    print("ESTABLISHED A CHANNEL @ {}".format(datetime.datetime.now()))

    ## STEP 2: READ FILE
    # read file
    filename = 'declaration.txt'
    with open(filename, 'r') as f:
        data = f.read()

    # some helpful variables but you don't have to use all of them
    pointer = 0
    SEQ = 0
    ACK = 0
    total_packet_sent = 0
    total_packet_recv = 0
    total_corrupted_pkt_recv = 0
    total_timeout =  0
    
    # set transmission timeout (set to 3 seconds if input is less or equal to zero)
    if transmission_timeout <= 0:
        transmission_timeout = 3
    clientSocket.settimeout(transmission_timeout)

    # send the first 200 characters
    start_index = 0
    to_send_size = 200

    # STEP 3: SEND FILE

    ##################################################
    # START YOUR RDT 3.0 SENDER IMPLEMENTATION BELOW #
    ##################################################

    total_correct_ack_recv = 0      # total number of correct(non-corrupted/non-lost) ACK received
    
    seq = '0'                       # initial sequence number to be 0

    exceptChecksum = '0 0 {} '.format(data[start_index:start_index+20])         # packet without checksum included
    msgChecksum = checksum(exceptChecksum)                                      # checksum for packet calculated
    packet = '0 0 {} {}'.format(data[start_index:start_index+20], msgChecksum)  # complete packet with checksum

    clientSocket.send(packet.encode('utf-8'))               # send packet to receiver
    total_packet_sent+=1                                    

    
    while total_correct_ack_recv < 10:                      # need 10 correct ACK for first 200 char of text

        ackCorrect = False                                  
        clientSocket.settimeout(transmission_timeout)

        while not ackCorrect:                               # if sender didn't receive correct ACK (non-corrupted/non-lost/non-NAK) then repeat until it gets correct ACK

            try:

                sender_state = '0' if seq == '0' else '1'       # set sender state to either 'wait for 0' or 'wait for 1' depending on what seq is sent

                ACKpacket = clientSocket.recv(30).decode('utf-8')   # ACK packet (ACK#, checksum) sent by receiver
                
                if ACKpacket[2] != sender_state:            # packet corrupted from sender->receiver , so NAK is sent , requires retransmission
                    total_packet_recv+=1
                    ACKpacket = clientSocket.recv(30).decode('utf-8')

                elif not checksum_verifier(ACKpacket):        # ACK packet corrupted from receiver->sender
                    total_corrupted_pkt_recv += 1
                    total_packet_recv+=1
                    ACKpacket = clientSocket.recv(30).decode('utf-8')

                else:                                       # correct ACK is received
                    total_packet_recv+=1
                    ackCorrect = True                       # break loop and proceed to send next packet
                    total_correct_ack_recv += 1

            except socket.error as e:                       # timeout error
                total_timeout+=1
                clientSocket.send(packet.encode('utf-8'))   # retransmission
                total_packet_sent += 1

        
        start_index+=20                                 # increase starting index of text by 20 for every new packet

        seq = '1' if sender_state == '0' else '0'       # alternating seq# for each new packet

        if total_correct_ack_recv == 10:                # if all 200 characters are sent then send empty packet to receiver to signal end
            clientSocket.send("".encode('utf-8'))

        else:                                                                               # else continue to send new packet of next text
            exceptChecksum = '{} 0 {} '.format(seq, data[start_index:start_index+20])
            msgChecksum = checksum(exceptChecksum)
            packet = '{} 0 {} {}'.format(seq, data[start_index:start_index+20], msgChecksum)
            clientSocket.send(packet.encode('utf-8'))
            total_packet_sent+=1
    

    ########################################
    # END YOUR RDT 3.0 SENDER IMPLEMENTATION HERE #
    ########################################

    # close the socket
    clientSocket.close() 

    # print out your name, the date and time,
    print("DONE sender - {} @ {}".format(name, datetime.datetime.now()))

    # print checksum of the sent file 
    print("File checksum: {}".format(checksum(data[:to_send_size])))
    # print stats
    print("Total packet sent: {}".format(total_packet_sent))
    print("Total packet recv: {}".format(total_packet_recv))
    print("Total corrupted packet recv: {}".format(total_corrupted_pkt_recv))
    print("Total timeout: {}".format(total_timeout))
 
if __name__ == '__main__':
    # check arguments
    if len(sys.argv) != 6:
        print("Expected \"python PA2_sender.py <connection_id> <loss_rate> <corrupt_rate> <max_delay> <transmission_timeout>\"")
        exit()
    connection_ID, loss_rate, corrupt_rate, max_delay, transmission_timeout = sys.argv[1:]
    # start sender
    start_sender(connection_ID, loss_rate, corrupt_rate, max_delay, float(transmission_timeout))