#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink

def topology():
    # Spoji ryu kontroler
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
    
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    # Switches
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    
    # Hosts
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')
    
    # Links
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s2)
    net.addLink(h4, s2)
    net.addLink(s1, s2)
    
    net.start()
    
    print("Mininet SDN mreža kreirana!")
    
    CLI(net)
    
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()