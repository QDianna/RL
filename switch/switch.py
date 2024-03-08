#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name


def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]
        
    bdpu_check = (dest_mac == b'\x01\x80\xc2\x00\x00\x00')

    return dest_mac, src_mac, ether_type, vlan_id, bdpu_check


def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)


def create_BPDU(root_bridge_id, root_path_cost, bridge_id, src_mac, port_id):
    # BPDU Config data
    flags = b'\x00'  # 1 byte
    root_bridge_id = struct.pack("!B", int(root_bridge_id))  # 1 byte
    root_path_cost = struct.pack("!I", root_path_cost)  # 4 bytes
    bridge_id = struct.pack("!B", int(bridge_id))  # 1 byte
    port_id = struct.pack("!H", port_id)  # 2 bytes
    message_age = 1
    message_age = struct.pack("!H", message_age)  # 2 bytes
    max_age = 20
    max_age = struct.pack("!H", max_age)  # 2 bytes
    hello_time = 2
    hello_time = struct.pack("!H", hello_time)  # 2 byes
    forward_delay = 15
    forward_delay = struct.pack("!H", forward_delay)  # 2 bytes
    
    # BPDU Config
    bpdu_config = flags + root_bridge_id + root_path_cost + bridge_id + port_id + message_age + max_age + hello_time + forward_delay

    # LLC header
    llc_header = b'\x42\x42\x03'  # 3 bytes

    # LLC_LENGTH
    llc_length = struct.pack("!H", len(bpdu_config) + len(llc_header))  # 2 bytes

    # BPDU_HEADER
    bpdu_header = b'\x00\x00\x00\x00'  # 4 bytes

    dest_mac = b'\x01\x80\xc2\x00\x00\x00'  # 6 bytes

    # BPDU frame
    bpdu_frame = dest_mac + src_mac + llc_length + llc_header + bpdu_header + bpdu_config
    return bpdu_frame 


def parse_bpdu(data):
    dest_mac = data[0:6]  # 6 bytes
    src_mac = data[6:12]  # 6 bytes
    llc_length = data[12:14]  # 2 bytes
    llc_header = data[14:17]  # 3 bytes
    bpdu_header = data[17:21] # 4 bytes

    bpdu_config = data[21:]
    # BPDU Config data:
    flags = bpdu_config[0:1]  # 1 byte
    root_bridge_id = struct.unpack('!B', bpdu_config[1:2])[0]  # 1 byte
    root_path_cost = struct.unpack('!I', bpdu_config[2:6])[0]  # 4 bytes
    bridge_id = struct.unpack('!B', bpdu_config[6:7])[0]  # 1 byte
    port_id = struct.unpack('!H', bpdu_config[7:9])[0]  # 2 bytes
    message_age = struct.unpack('!H', bpdu_config[9:11])[0]  # 2 bytes
    max_age = struct.unpack('!H', bpdu_config[11:13])[0]  # 2 bytes
    hello_time = struct.unpack('!H', bpdu_config[13:15])[0]  # 2 bytes
    forward_delay = struct.unpack('!H', bpdu_config[15:17])[0]  # 2 bytes

    # return only what I need for frame processing
    return dest_mac, src_mac, root_bridge_id, root_path_cost, bridge_id, port_id

    
def send_bpdu_every_sec(path_cost, my_mac, trunk_state):
    while True:
        # TODO Send BPDU every second if necessary
        if Bid == RBid:
            for i in trunk_state:
                # send BPDU on trunk interfaces
                bpdu_frame = create_BPDU(RBid, path_cost, Bid, my_mac, i)
                send_to_link(i, bpdu_frame, len(bpdu_frame))
        time.sleep(1)


def is_unicast(mac_addr):
    return not (mac_addr == 0xFFFFFFFFFFFF)


def forward_frame(data, interface):
    send_to_link(interface, data, len(data))


def read_config_file(file_id):
    filename = f"./configs/switch{file_id}.cfg"

    # dictionary for interfaces information 
    # config_data[interface_name] = interface_type ('T' sau "VLAN")
    config_data = {}

    try:
        with open(filename, 'r') as file:
            for line in file:
                words = line.split()

                # extract info form line: interface_name interface_type
                if len(words) >= 2:
                    interface_name = words[0]
                    interface_type = words[1]

                    config_data[interface_name] = interface_type
                else:
                    prio = words[0]

    except FileNotFoundError:
        print(f"File {filename} not found.")

    return config_data, prio


def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    # dictionary for interfaces information 
    # config_data[interface_name] = interface_type ('T' sau "VLAN")
    config_data, prio = read_config_file(switch_id)

    # print("# Starting switch with id {}".format(switch_id), flush=True)
    # print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))
    
    # Printing interface names
    # for i in interfaces:
        # print(get_interface_name(i))

    # dictionary for CAM table
    # CAM_table[MAC_address] = interface
    CAM_table = {}

    # STP data

    # dictionary for the states of the trunk ports on switch
    # trunk_state[interface] = state ("BLOCKED" sau "LISTENING")
    trunk_state = {}

    # all ports start blocked
    for i in interfaces:
        if config_data[get_interface_name(i)] == 'T':
            trunk_state[i] = "BLOCKED"
    
    global Bid
    Bid = prio

    global RBid
    RBid = prio

    path_cost = 0
    root_port = -1

    # if switch is RB set all ports to listen
    if Bid == RBid:
        for i in trunk_state:
            trunk_state[i] = "LISTENING"    

    # create and start a new thread that deals with sending BPDU
    my_mac = get_switch_mac()
    
    t = threading.Thread(target = send_bpdu_every_sec, args = (path_cost, my_mac, trunk_state))
    t.start()

    
    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id, bdpu_check = parse_ethernet_header(data)        

        # printing the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        # print(f'Destination MAC: {dest_mac}')
        # print(f'Source MAC: {src_mac}')
        # print(f'EtherType: {ethertype}')

        # print("Received frame of size {} on interface {}".format(length, interface), flush=True)
        
        # TODO: Implement STP support
        # bdpu_check = is_bpdu(dest_mac)
        if bdpu_check:
            dest_mac, src_mac, root_bridge_id, root_path_cost, bridge_id, port_id = parse_bpdu(data)

            if int(root_bridge_id) < int(RBid):
                # I received info of a better RB than what I had
                oldRBid = RBid
                RBid = root_bridge_id
                path_cost = int(root_path_cost) + 10
                root_port = port_id

                if int(Bid) == int(oldRBid):
                    # I was RB => block all my ports except root_port
                    for i in trunk_state:
                        if i != int(port_id):
                            trunk_state[i] = "BLOCKED"
                
                if trunk_state[port_id] == "BLOCKED":
                    trunk_state[root_port] == "LISTENING"

                # update and fwd BPDU frame with modifications: port_id = own interface, bridge_id = Bid
                for i in trunk_state:
                    if i != int(port_id):
                        bpdu_frame = create_BPDU(root_bridge_id, path_cost, Bid, my_mac, i)
                        send_to_link(i, bpdu_frame, len(bpdu_frame))

            elif int(root_bridge_id) == int(RBid):
                # I received info of the same RB => see if I can find a better path to it
                if port_id == root_port and root_path_cost + 10 < path_cost:
                    path_cost = int(root_path_cost) + 10
                
                elif port_id != root_port:
                    if int(root_path_cost) > int(path_cost):
                        trunk_state[port_id] = "LISTENING"
                            
            elif int(bridge_id) == int(Bid):
                trunk_state[port_id] = "BLOCKED"
            
            else:
                # discard BPDU 
                continue

            if int(Bid) == int(root_bridge_id):
                for i in trunk_state:
                    trunk_state[i] = "LISTENING"

        # TODO: Implement forwarding with learning
        # TODO: Implement VLAN support
        else:
            if src_mac not in CAM_table:
                CAM_table[src_mac] = interface

            if is_unicast(dest_mac):                    
                if dest_mac in CAM_table:
                    # dest is in CAM table
                    i_dest = CAM_table[dest_mac]
                    if vlan_id == -1:
                        # frame came from access (without tag) => see where it has to go
                        # on trunk => add tag
                        if config_data[get_interface_name(i_dest)] == 'T':
                            tagged_frame = data[0:12] + create_vlan_tag(int(config_data[get_interface_name(interface)])) + data[12:]
                            forward_frame(tagged_frame, i_dest)
                        # on access => dont add tag
                        else:
                            if (int(config_data[get_interface_name(interface)]) ==  int(config_data[get_interface_name(i_dest)])):
                                forward_frame(data, i_dest)
                    else:
                        # frame came from trunk (with tag) => see where it has to go
                        # on trunk => keep tag
                        if config_data[get_interface_name(i_dest)] == 'T':
                            forward_frame(data, i_dest)
                        # on access => remove tag
                        else:
                            untagged_frame = data[0:12] + data[16:]
                            forward_frame(untagged_frame, i_dest)

                else:
                    # dest is not CAM table => flooding on trunk ports and access ports with the same vlan_id
                    if vlan_id == -1:
                    # came from acc (without tag) => send on trunk with tag and on access without
                        for i in interfaces:
                            if i in trunk_state:
                                if i != interface and config_data[get_interface_name(i)] == 'T' and trunk_state[i] == "LISTENING":
                                    tagged_frame = data[0:12] + create_vlan_tag(int(config_data[get_interface_name(interface)])) + data[12:]
                                    forward_frame(tagged_frame, i)
                            else:
                                if i != interface and int(config_data[get_interface_name(i)]) == int(config_data[get_interface_name(interface)]):
                                    forward_frame(data, i)
                    else:
                    # a venit pe trunk => trimit pe trunk la fel si pe acc scot tag
                        for i in interfaces:
                            if i in trunk_state:
                                if i != interface and config_data[get_interface_name(i)] == 'T' and trunk_state[i] == "LISTENING":
                                    forward_frame(data, i)
                            else:
                                if i != interface and int(config_data[get_interface_name(i)]) == vlan_id:
                                    untagged_frame = data[0:12] + data[16:]
                                    forward_frame(untagged_frame, i)
            else:
                # broadcast (same as dest not in CAM table)
                if vlan_id == -1:
                        for i in interfaces:
                            if i in trunk_state:
                                if i != interface and config_data[get_interface_name(i)] == "T" and trunk_state[i] == "LISTENING":
                                    tagged_frame = data[0:12] + create_vlan_tag(int(config_data[get_interface_name(interface)])) + data[12:]
                                    forward_frame(tagged_frame, i)
                            else:
                                if i != interface and int(config_data[get_interface_name(i)]) == int(config_data[get_interface_name(interface)]):
                                    forward_frame(data, i)
                else:
                    for i in interfaces:
                        if i in trunk_state:
                            if i != interface and config_data[get_interface_name(i)] == 'T' and trunk_state[i] == "LISTENING":
                                forward_frame(data, i)
                        else:
                            if i != interface and int(config_data[get_interface_name(i)]) == vlan_id:
                                untagged_frame = data[0:12] + data[16:]
                                forward_frame(untagged_frame, i)


if __name__ == "__main__":
    main()