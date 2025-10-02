# Tema 1 RL – Basic Switch Implementation

Proiect realizat pentru cursul **Rețele Locale (RL)**.  
Implementarea constă într-un switch software care suportă:  
- **Forwarding with learning**  
- **VLAN support**  
- **Spanning Tree Protocol (STP)**  

## Funcționalități implementate

Pe lângă funcțiile din schelet, am adăugat:  
- `create_BDPU`: creează un frame BDPU conform structurii din enunț  
- `parse_BDPU`: primește un BDPU și extrage datele din el  
- `read_config_file`: citește fișierul de configurare al switch-ului, returnează prioritatea și creează un dicționar cu interfețe și tipurile lor (`T` pentru trunk, `<VLAN_ID>` pentru access)  
- `is_unicast`: verifică dacă adresa MAC este unicast  
- `forward_frame`: tratează logica de forward în funcție de CAM table și VLAN  

## Structuri de date
- `config_data`: dicționar cu interfețe și tipurile lor (trunk sau access)  
- `trunk_state`: dicționar cu interfețele trunk și starea lor (BLOCKED / LISTENING) pentru STP  
- `CAM_table`: dicționar cu adrese MAC și interfețele asociate  

## Spanning Tree Protocol (STP)
- Inițial, fiecare switch pornește ca **root bridge**.  
- Pachetele BDPU sunt deosebite prin adresa MAC de destinație `00:80:C2:00:00:00`.  
- La recepția unui BDPU, se actualizează RB și porturile în funcție de prioritate și costuri.  
- Thread-ul `send_bdpu_every_sec` se ocupă cu trimiterea periodică de BDPU-uri atunci când switch-ul este root bridge.  

## Forwarding & Learning
- Dacă destinația există în CAM table:  
  - Cadru primit pe port access (fără tag): trimis pe trunk cu tag și pe access fără tag.  
  - Cadru primit pe port trunk (cu tag): trimis mai departe pe trunk cu tag și pe access fără tag.  
- Dacă destinația nu este în CAM table sau este broadcast:  
  - Se face flood pe toate porturile în **stare LISTENING**, respectând regulile VLAN.  

## Concluzie
Proiectul demonstrează implementarea unui switch software simplificat cu suport pentru **learning, VLAN și STP**, folosind concepte de rețelistică practică și algoritmi de rutare a cadrelor Ethernet.
