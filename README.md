## TODO:
### ARP paketi
- Trenutno osim IP paketima zabranjen prolaz i ARP paketima jer nisam bio siguran je li OK da se ARP paketi smiju svojevoljno broadcastati (ne zvuči mi baš kao zero trust).
### Učenje topologije
- Kako bi kontroler naučio topologiju i propustio ARP pakete svaki host mora poslati barem jedan paket (dinamičko učenje topologije). Treba istražiti druge opcije poput učenja topologije na druge načine ili početak rada sa informacijama o topologiji bez učenja.
### Routing
- Trenutno hardcodean port za komunikaciju između 2 switcha u primjeru, treba uvesti pametniji način routinga koji podržava više switcheva (Dijkstra?).
