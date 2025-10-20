#!/usr/bin/env python3

"""
SDN kontroler koji implementira whitelist-based routing sa dinamičkim učenjem topologije.
Blokira ARP i IP promet između neautoriziranih IP parova.

=== RYU CHEAT SHEET ===
Često korišteni objekti:
  - datapath: Predstavlja switch (OpenFlow uređaj)
  - datapath.id (dpid): Jedinstveni ID switcha
  - ofproto: OpenFlow protokol konstante (OFPP_CONTROLLER, OFPCML_NO_BUFFER, ...)
  - parser: Factory za stvaranje OpenFlow poruka (OFPMatch, OFPActionOutput, ...)
  
Ključne poruke:
  - OFPFlowMod: Instalira/briše flow pravila u switchu (trajno)
  - OFPPacketOut: Šalje JEDAN paket natrag u switch sa instrukcijama
  - OFPPacketIn: Switch šalje paket kontroleru (nema match u flow tablici)
  
Event handleri:
  - @set_ev_cls(event, dispatcher): Dekorator koji registrira handler za OpenFlow događaje
  - CONFIG_DISPATCHER: Faza inicijalizacije switcha
  - MAIN_DISPATCHER: Normalan rad switcha
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4

class SmartARPController(app_manager.RyuApp):
    # Koristi OpenFlow v1.3
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    def __init__(self, *args, **kwargs):
        # Inicijaliziraj ryu kontroler
        super(SmartARPController, self).__init__(*args, **kwargs)
        
        # Mrežna topologija u obliku: IP -> (MAC, switch_id, port)
        # Koristi se za usmjeravanje ARP paketa i provjeru whiteliste između IP adresa
        # Kontroler uči topologiju dinamički iz paketa koje primi
        self.host_info = {}
        
        # Mac adrese spojene na portovima switcheva
        # Koristi se za stvaranje pravila u routing tablicama switcheva
        self.mac_to_port = {}
        
        # Whitelista: dozvoljena komunikacija paketa
        self.ALLOWED_PAIRS = {
            ('10.0.0.1', '10.0.0.2'),
            ('10.0.0.2', '10.0.0.1'),
        }
        
        self.logger.info("Dinamički kontroler inicijaliziran.")

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0):
        """
        Šalje FlowMod poruku switchu da instalira novo pravilo.
        
        Priority: Veći broj = viši prioritet (provjerava se prvi)
        Match: Uvjeti koje paket mora zadovoljiti (npr. src_ip, dst_mac)
        Actions: Što napraviti s paketom (npr. proslijedi na port 2)
        idle_timeout: Koliko sekundi pravilo ostaje ako nema matcheva
                      0 = pravilo nikad ne istječe samo
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # OFPIT_APPLY_ACTIONS znači "izvrši akcije odmah"
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, 
                                match=match, instructions=inst, 
                                idle_timeout=idle_timeout)
        datapath.send_msg(mod)
    
    # Metoda koja se poziva kada se switch spojit na kontroler
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Poziva se automatski kada se switch spoji na kontroler.
        CONFIG_DISPATCHER znači da se ovo događa u fazi inicijalizacije.
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        self.logger.info(f"Switch {datapath.id} spojen")
        
        # Postavi default pravilo: Ako paket name match u routing tablici pošalji ga u kontroler
        match = parser.OFPMatch() # Prazan match znači sve pakete

        # OFPP_CONTROLLER znači pošalji u kontroler
        # OFPCML_NO_BUFFER znači ne stavljaj ih u buffer u switchu
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, 
                                         ofproto.OFPCML_NO_BUFFER)]

        self.add_flow(datapath, 0, match, actions)
        
        # Inicijaliziraj prazno mapiranje za ovaj switch
        # Popunjavat će se kako kontroler uči o hostovima
        self.mac_to_port.setdefault(datapath.id, {})
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Poziva se kada switch pošalje paket kontroleru (nema matching flow pravila).
        MAIN_DISPATCHER znači da je switch već konfiguriran i radi normalno.
        """
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        
        # 0x0806 = ARP, 0x0800 = IPv4
        if eth.ethertype == 0x0806:
            self._handle_arp(datapath, in_port, pkt, eth)
        else:
            self._handle_ip(datapath, in_port, pkt, eth)

    def _route_packet(self, packet_type, datapath, in_port, pkt, dst_port):
        """
        Prosljeđuje paket natrag u switch sa instrukcijom na koji port ga poslati.
        PacketOut poruka ne instalira trajno pravilo - samo prosljeđuje OVAJ paket.
        """
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        self.logger.info(f"  -> {packet_type} poslan na port {dst_port}")
        actions = [parser.OFPActionOutput(dst_port)]

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=pkt.data
        )
        datapath.send_msg(out)

    def _handle_arp(self, datapath, in_port, pkt, eth):
        """
        Rukuje ARP paketima bez broadcast-a.
        Ako znamo gdje je destination, direktno šaljemo tamo.
        Ako ne znamo, odbacujemo paket (u normalnoj mreži bi bio broadcast).
        """
        arp_pkt = pkt.get_protocol(arp.arp)
        if not arp_pkt:
            return

        dpid = datapath.id 
        parser = datapath.ofproto_parser 
        src_ip = arp_pkt.src_ip 
        dst_ip = arp_pkt.dst_ip 
        src_mac = arp_pkt.src_mac

        # Spremamo informacije kako je host koji šalje paket spojen u topologiju
        self.host_info[src_ip] = (src_mac, dpid, in_port)
        self.mac_to_port.setdefault(dpid, {})[src_mac] = in_port

        self.logger.info(f"ARP: {src_ip} ({src_mac}) zahtjev prema {dst_ip}")

        # Provjera whiteliste
        if (src_ip, dst_ip) not in self.ALLOWED_PAIRS:
            self.logger.warning(f"  ZABRANJENO: ARP paket između {src_ip} i {dst_ip}")
            return

        arp_type = "ARP zahtjev" if arp_pkt.opcode == arp.ARP_REQUEST else "ARP odgovor"

        # Ako znamo gdje je destination, pošalji tamo
        if dst_ip in self.host_info:
            dst_mac, dst_switch, dst_port = self.host_info[dst_ip]
            self._route_packet(arp_type, datapath, in_port, pkt, dst_port)
        else:
            # U normalnoj mreži bi bio broadcast, mi odbacujemo
            self.logger.warning(f"  -> Nepoznat odredišni IP: {dst_ip}, paket se odbacuje")

    def _handle_ip(self, datapath, in_port, pkt, eth):
        """
        Rukuje IP paketima sa whitelist provjerom.
        Za dozvoljene IP parove instalira flow pravilo u switch
        tako da sljedeći paketi ne trebaju prolaziti kroz kontroler.
        """    
        dpid = datapath.id
        parser = datapath.ofproto_parser
        src_mac = eth.src
        dst_mac = eth.dst
        
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return
        
        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst
        
        # Spremamo informacije kako je host koji šalje paket spojen u topologiju
        self.host_info[src_ip] = (src_mac, datapath.id, in_port)
        self.mac_to_port.setdefault(datapath.id, {})[src_mac] = in_port

        self.logger.info(f"IP: {src_ip} zahtjev prema {dst_ip}")
        
        if (src_ip, dst_ip) not in self.ALLOWED_PAIRS:
            self.logger.warning(f"  ZABRANJENO: IP paket između {src_ip} i {dst_ip}")
            return

        if dst_ip in self.host_info:
            dst_mac, dst_switch, dst_port = self.host_info[dst_ip]
            self._route_packet("IP paket", datapath, in_port, pkt, dst_port)
            self.logger.info(f"  DOZVOLJENO: IP paket između {src_ip} i {dst_ip}")

            # Instaliraj flow pravilo u switch za buduće pakete
            # Priority 10 > 0 (viši od table-miss pravila)
            # idle_timeout=30 znači pravilo se briše nakon 30s neaktivnosti
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
            
            # Odredi izlazni port
            if dst_mac in self.mac_to_port[dpid]:
                # Destination je na istom switchu
                out_port = self.mac_to_port[dpid][dst_mac]
            # Odredište spojeno na drugi switch, proslijedi paket
            else:
                # HARDCODED: Destination je na drugom switchu
                # Port 3 je inter-switch link (radi SAMO za 2 switcha!)
                # U realnoj implementaciji bi trebala routing tablica ili shortest path algoritam
                out_port = 3

            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 10, match, actions, idle_timeout=30)