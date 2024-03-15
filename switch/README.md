# TEMA 1 RL - Basic Switch Implementation

In aceasta tema am realizat implementarea unui switch cu toate cele 3 functionalitati
prezentate in enunt: forwarding with learning, VLAN support si STP support.
Pe langa functiile existente in schelet, am creat urmatoarele functii:
- create_BDPU: functie folosita pentru a crea un frame de tip BDPU, urmand structura
din enunt
- parse_BDPU: primeste un cadru BDPU si extrage datele din el
- read_config_file: citeste fisierul de config al switch-ului, returneaza prioritatea
si creeaza si returneaza un dictionar in care cheia este numele interfetei si
valoarea este tipul acesteia ('T' pt trunk si <VLAN_ID> pentru access)
- is_unicast
- foward_frame

In functia main am inceput prin a initializa dictionarele pe care le-am utilizat:
- config_data - interfete & tipul lor (trunk sau access)
- trunk_state - interfete trunk & starea lor ("BLOCKED" sau "LISTENING"), pentru STP
- CAM_table - adrese MAC & interfetele asociate
Am pornit un thread care are ca thread function "send_bdpu_every_sec", care se ocupa
cu trimiterea de pachete BDPU in cazul in care switch-ul este root bridge in LAN

In continuare, intr-un loop infinit, se primesc cadre ("recv_from_any_link"), se
determina tipul lor si se iau actiuni corespunzatoare:

1. pachete BDPU - rulez STP conform cu pseudocodul din enunt
- deosebite prin adresa mac destinatie = 00:80:C2:00:00:00
Pornesc cu fiecare switch configurat ca RB; la primirea unui pachet determin daca
am "aflat" un RB mai prioritar:
- daca da - actualizez datele switch-ului; daca switch-ul era RB ii blochez porturile,
mai putin "root_port", apoi transmit mai departe pachetul adaugand costul de a trece
prin switch-ul curent;
- daca nu - daca am primit pe root_port un RB la fel de prioritar ca RB curent,
compar costul de a trece prin switch-ul de la care am primit cu costul pe care
il aveam initial si actualizez daca e cazul;
          - daca portul pe care am primit nu e root_port, verific daca switch-ul
care a trimis are un cost mai mare decat costul pe care l-ar avea prin switch-ul
curent si daca da, pun portul sw curent in listening

2. alte pachete - fac forwarding & learning avand in vedere VLAN urile din topologie
daca am destinatia in tabela CAM:
- daca am primit de pe port access (fara tag) trimit pe trunk cu tag si pe acces fara tag
- daca am primit de pe port trunk (cu tag) trimit pe trunk la fel si pe access scot tag-ul
daca destinatia nu e in tabela CAM / destinatia e adr de broadcast:
- pentru toate interfetele disponibile (listening) am aceleasi 2 cazuri de mai sus
