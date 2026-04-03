# Wi-Fi Security Verifications

All security checks that can be performed passively by analysing beacons, probe responses, association frames, EAPOL exchanges, and data frames — without sending any traffic or interacting with the network.

---

## 1. ENCRYPTION AND PROTOCOL CHECKS

### 1.1 Open Network Detection [IMPLEMENTED - Network Scanner]
- Source: Beacon RSN/WPA IE absence + capability field Privacy bit
- Check: Network has no RSN IE, no WPA IE, and Privacy bit is 0
- Severity: Critical
- Finding: "Network transmits all traffic in plaintext. Any device in range can intercept data."

### 1.2 WEP Detection [IMPLEMENTED - Network Scanner]
- Source: Beacon capability field (Privacy = 1) with no RSN/WPA IE
- Check: Privacy bit set but no RSN or WPA Information Element present
- Severity: Critical
- Finding: "WEP encryption is cryptographically broken. Can be cracked in minutes."

### 1.3 WPA-TKIP Only Detection [IMPLEMENTED - Network Scanner]
- Source: WPA IE present, no RSN IE
- Check: Only WPA vendor-specific IE, pairwise cipher is TKIP
- Severity: High
- Finding: "WPA with TKIP only. Deprecated protocol with known attacks (Beck-Tews, Ohigashi-Morii)."

### 1.4 TKIP Still Accepted (Mixed Cipher) [IMPLEMENTED - Network Scanner]
- Source: RSN IE pairwise cipher suite list
- Check: RSN IE lists both CCMP and TKIP as pairwise ciphers
- Severity: High
- Finding: "TKIP accepted alongside AES. Clients can be downgraded to the weaker cipher."

### 1.5 WPA/WPA2 Mixed Mode [IMPLEMENTED - Network Scanner]
- Source: Both WPA IE and RSN IE present in same beacon
- Check: Beacon contains both vendor-specific WPA IE and RSN IE
- Severity: High
- Finding: "WPA/WPA2 mixed mode allows protocol downgrade from WPA2 to WPA-TKIP."

### 1.6 WPA3 Transition Mode Downgrade Risk [IMPLEMENTED - Network Scanner]
- Source: RSN IE AKM suite list
- Check: RSN IE contains both AKM type 2 (PSK) and type 8 (SAE)
- Severity: Medium
- Finding: "WPA3 transition mode. Rogue AP offering WPA2-only can force clients to downgrade."

### 1.7 No WPA3 Support [IMPLEMENTED - Network Scanner]
- Source: RSN IE AKM suite list
- Check: RSN IE has no AKM type 8 (SAE) and no AKM type 18 (OWE)
- Severity: Info
- Finding: "No WPA3 advertised. WPA3-SAE provides forward secrecy and offline brute-force resistance."

### 1.8 Group Cipher Weakness [IMPLEMENTED - Network Scanner]
- Source: RSN IE group cipher suite
- Check: Group cipher is TKIP (type 2) instead of CCMP (type 4)
- Severity: Medium
- Finding: "Group cipher is TKIP. Broadcast/multicast traffic uses weaker encryption."

### 1.9 WPA2-PSK Without SAE Available [IMPLEMENTED - Network Scanner]
- Source: RSN IE AKM suites
- Check: AKM type 2 (PSK) present, AKM type 8 (SAE) absent
- Severity: Info
- Finding: "WPA2-PSK is susceptible to offline brute-force if handshake is captured. WPA3-SAE eliminates this risk."


## 2. PROTECTED MANAGEMENT FRAMES (PMF / 802.11w)

### 2.1 No PMF Support [IMPLEMENTED - Network Scanner]
- Source: RSN IE RSN Capabilities field
- Check: MFPC bit (bit 7) is 0
- Severity: Medium
- Finding: "AP does not support PMF. Management frames can be spoofed (deauth, disassoc attacks)."

### 2.2 PMF Capable But Not Required [IMPLEMENTED - Network Scanner]
- Source: RSN IE RSN Capabilities field
- Check: MFPC bit is 1, MFPR bit (bit 8) is 0
- Severity: Medium
- Finding: "PMF is optional. Clients without PMF support connect unprotected."

### 2.3 PMF Required (Good) [IMPLEMENTED - Network Scanner]
- Source: RSN IE RSN Capabilities field
- Check: Both MFPC and MFPR bits are 1
- Severity: Pass
- Finding: "PMF is required. All management frames are protected."

### 2.4 WPA2-PSK Without PMF Required [IMPLEMENTED - Network Scanner]
- Source: RSN IE AKM + RSN Capabilities
- Check: AKM is PSK (type 2), MFPR is 0
- Severity: High
- Finding: "WPA2-PSK without mandatory PMF. Vulnerable to deauthentication attacks and handshake capture."


## 3. WPS (Wi-Fi Protected Setup)

### 3.1 WPS Enabled [IMPLEMENTED - Network Scanner]
- Source: WPS vendor-specific IE in beacons
- Check: WPS IE present in beacon
- Severity: Medium
- Finding: "WPS is enabled. PIN mode is vulnerable to brute-force (Reaver) and Pixie Dust attacks."

### 3.2 WPS Version Detection [IMPLEMENTED - Network Scanner]
- Source: WPS IE Version field from iw scan output
- Check: Parse WPS version
- Severity: Info
- Finding: "WPS version {X}. Version 1.0 has no lockout protection."

### 3.3 WPS Configuration State [IMPLEMENTED - Network Scanner]
- Source: WPS IE Wi-Fi Protected Setup State field from iw scan output
- Check: State = 1 (not configured) vs 2 (configured)
- Severity: Low
- Finding: "WPS is in unconfigured state, making it a target for external registrar attacks."


## 4. HIDDEN SSID ANALYSIS

### 4.1 Hidden SSID Detected [IMPLEMENTED - Network Scanner + Pcap Analyser]
- Source: Beacon with empty SSID field or null bytes
- Check: wlan.ssid is empty or all null bytes in beacon frame
- Severity: Low
- Finding: "Hidden SSID provides no security. SSID is exposed in probe requests and responses."

### 4.2 Hidden SSID Deanonymisation [IMPLEMENTED - Pcap Analyser]
- Source: Probe responses matching BSSID of hidden beacon
- Check: Probe response from same BSSID contains the actual SSID
- Severity: Info
- Finding: "Hidden SSID revealed: {SSID}. Discovered from probe response."

### 4.3 Client Probing for Hidden Networks [IMPLEMENTED - Pcap Analyser]
- Source: Directed probe requests from clients
- Check: Client sends probe requests with specific SSID (not broadcast)
- Severity: Low
- Finding: "Client {MAC} is actively probing for hidden network '{SSID}'. This reveals the network name at every location the client visits."


## 5. ROGUE AP AND EVIL TWIN DETECTION

### 5.1 Duplicate SSID with Different Security [IMPLEMENTED - Network Scanner]
- Source: Beacons from multiple BSSIDs with same SSID
- Check: Same SSID seen with different RSN IE contents (different security levels)
- Severity: High
- Finding: "SSID '{name}' seen with different security settings. This may indicate a rogue AP or misconfiguration."

### 5.2 Duplicate SSID with Different Vendor [IMPLEMENTED - Network Scanner]
- Source: Beacons from multiple BSSIDs with same SSID
- Check: Same SSID but OUI (vendor) of BSSIDs does not match
- Severity: Medium
- Finding: "SSID '{name}' seen from different vendors. May indicate rogue AP."

### 5.3 Multiple Vendors for Same SSID [IMPLEMENTED - Pcap Analyser]
- Source: BSSID OUI comparison within selected SSID
- Check: BSSIDs for analysed SSID come from different hardware vendors
- Severity: Medium
- Finding: "BSSIDs for this SSID come from different vendors. May indicate rogue AP if not expected."

### 5.4 Suspiciously Similar BSSIDs [IMPLEMENTED - Network Scanner]
- Source: BSSID list
- Check: Two BSSIDs for same SSID differ by only 1 nibble (possible MAC spoofing)
- Severity: Medium
- Finding: "BSSIDs {A} and {B} are suspiciously similar. One may be a cloned AP."


## 6. 802.1X AND CERTIFICATE CHECKS

### 6.1 Enterprise Authentication Method Detection [IMPLEMENTED - Pcap Analyser]
- Source: EAP packets in capture
- Check: Parse eap.type to identify EAP method (PEAP, TLS, TTLS, FAST, etc.)
- Severity: Info
- Finding: "Network uses {EAP method} for authentication."

### 6.2 EAP-PEAP/MSCHAPv2 Weakness [IMPLEMENTED - Pcap Analyser]
- Source: EAP exchange
- Check: PEAP (type 25) or MSCHAPv2 detected
- Severity: Medium
- Finding: "EAP-PEAP/MSCHAPv2 detected. If clients do not validate the server certificate, credentials can be captured by a rogue RADIUS server."

### 6.3 Expired Server Certificate [IMPLEMENTED - Pcap Analyser]
- Source: TLS handshake in EAP-TLS/PEAP exchange
- Check: x509ce.validity.notAfter is before current date
- Severity: Critical
- Finding: "802.1X server certificate expired {days} days ago. Clients may refuse to connect."

### 6.4 Certificate Expiring Soon [IMPLEMENTED - Pcap Analyser]
- Source: TLS handshake
- Check: x509ce.validity.notAfter is within 30 days of current date
- Severity: High
- Finding: "802.1X certificate expires in {days} days. Renew before clients start failing."

### 6.5 Weak Certificate Signature Algorithm [IMPLEMENTED - Pcap Analyser]
- Source: TLS handshake certificate
- Check: Certificate uses SHA-1 or MD5 signature
- Severity: Medium
- Finding: "802.1X certificate uses weak signature algorithm. Use SHA-256 or stronger."

### 6.6 Self-Signed Certificate [IMPLEMENTED - Pcap Analyser]
- Source: TLS handshake certificate
- Check: Issuer matches Subject in certificate
- Severity: Low
- Finding: "802.1X certificate is self-signed. Clients may show certificate warnings."

### 6.7 Username Exposure in EAP Identity [IMPLEMENTED - Pcap Analyser]
- Source: EAP Identity Response packets
- Check: eap.identity contains actual usernames (not anonymous outer identity)
- Severity: Medium
- Finding: "Usernames visible in EAP Identity. The outer identity should use 'anonymous@domain' to prevent username enumeration."

### 6.8 EAPOL Handshake Failure (Wrong Password) [IMPLEMENTED - Pcap Analyser]
- Source: EAPOL 4-way handshake packets
- Check: Repeated message 1 and 2 without message 3 and 4
- Severity: High
- Finding: "Client {MAC} failed authentication {N} times. Possible wrong password or credential issue."


## 7. CLIENT SECURITY CHECKS

### 7.1 Client Probing for Insecure Networks [IMPLEMENTED - Pcap Analyser]
- Source: Directed probe requests
- Check: Client probes for known insecure network names (common open hotspot SSIDs)
- Severity: Low
- Finding: "Client probing for open network names. Device may auto-connect to rogue AP with matching name."

### 7.2 Randomised MAC Not Used [IMPLEMENTED - Pcap Analyser]
- Source: Data frames
- Check: Client MAC does not have locally administered bit set
- Severity: Info
- Finding: "Client not using MAC randomisation. Device is trackable across locations."

### 7.3 Client Broadcasting Saved Network List [IMPLEMENTED - Pcap Analyser]
- Source: Directed probe requests
- Check: Client sends directed probes for more than 5 different SSIDs
- Severity: Low
- Finding: "Client probing for {N} different networks. This reveals previously connected networks."

### 7.4 Client Connected to Open Network While Encrypted Available [IMPLEMENTED - Pcap Analyser]
- Source: Data frames + beacon security info
- Check: Client associated with an Open network BSSID while same SSID exists with encryption
- Severity: Medium
- Finding: "Client connected to open version of SSID while encrypted version is available."


## 8. INFRASTRUCTURE SECURITY CHECKS

### 8.1 Too Many SSIDs Per AP [IMPLEMENTED - Pcap Analyser]
- Source: Beacon BSSID grouping
- Check: More than 4 unique SSIDs on same physical AP
- Severity: High (operational + security)
- Finding: "AP has {N} SSIDs. Each SSID's beacons increase airtime exposure and attack surface."

### 8.2 Firmware Age Estimation [IMPLEMENTED - Pcap Analyser]
- Source: Beacon timestamp field (microseconds since BSS start)
- Check: Convert timestamp to uptime, flag if > 180 days
- Severity: Medium
- Finding: "BSS uptime is {days} days. AP firmware likely not updated."

### 8.3 Legacy Wi-Fi Standard (Old Hardware) [IMPLEMENTED - Network Scanner]
- Source: Beacon HT/VHT/HE capabilities
- Check: AP has no HT capabilities (802.11a/b/g only)
- Severity: Low
- Finding: "AP running legacy standard. Old hardware likely lacks security patches."

### 8.4 Legacy Bit Rates Enabled [IMPLEMENTED - Pcap Analyser]
- Source: Beacon Supported Rates IE
- Check: Rates 1, 2, 5.5, 11 Mbps present in supported or basic rates
- Severity: Medium
- Finding: "Legacy bit rates enabled. Slows entire BSS and indicates default configuration."

### 8.5 SSID Contains Identifying Information [IMPLEMENTED - Network Scanner]
- Source: Beacon SSID field
- Check: SSID contains IP addresses, room/floor/building numbers, device model names
- Severity: Low
- Finding: "SSID reveals organisational information that aids targeted attacks."

### 8.6 Default SSID Detection [IMPLEMENTED - Network Scanner]
- Source: Beacon SSID field
- Check: SSID matches known vendor defaults (NETGEAR, linksys, TP-LINK_XXXX, etc.)
- Severity: Medium
- Finding: "Default SSID detected. Indicates factory configuration — default passwords may also be in use."

### 8.7 Broadcast of AP Name [IMPLEMENTED - Pcap Analyser]
- Source: Vendor-specific IEs in beacons
- Check: AP broadcasts its hostname/name in vendor IEs
- Severity: Info
- Finding: "AP name is broadcast. Reveals internal naming conventions and infrastructure details."


## 9. DATA LEAKAGE DETECTION (from pcap)

### 9.1 mDNS / Multicast Traffic [IMPLEMENTED - Pcap Analyser]
- Source: Data frames with broadcast/multicast destination
- Check: mDNS traffic detected on wireless
- Severity: Low
- Finding: "mDNS traffic detected. Reveals device names, services, and types on the network."

### 9.2 STP BPDUs on Wireless [IMPLEMENTED - Pcap Analyser]
- Source: STP BPDUs captured on wireless
- Check: Spanning Tree Protocol frames detected
- Severity: Medium
- Finding: "STP BPDUs detected on wireless. Wired infrastructure topology is leaking."

### 9.3 CDP Information Leakage [IMPLEMENTED - Pcap Analyser]
- Source: CDP frames captured on wireless
- Check: Cisco Discovery Protocol frames visible
- Severity: Medium
- Finding: "CDP frames detected. Reveals switch model, port, VLAN, IP address, and firmware version."

### 9.4 LLDP Information Leakage [IMPLEMENTED - Pcap Analyser]
- Source: LLDP frames captured on wireless
- Check: Link Layer Discovery Protocol frames visible
- Severity: Medium
- Finding: "LLDP frames detected. Reveals switch model, port, and hostname."


## 10. ADVANCED PASSIVE DETECTION

### 10.1 Rogue DHCP Server Detection [IMPLEMENTED - Pcap Analyser]
- Source: DHCP Offer/ACK packets from multiple sources
- Check: DHCP responses from more than one server IP
- Severity: High
- Finding: "Multiple DHCP servers detected. A rogue DHCP server can redirect traffic through an attacker."

### 10.2 ARP Spoofing Indicators [IMPLEMENTED - Pcap Analyser]
- Source: ARP packets in capture
- Check: Multiple MACs claiming same IP address
- Severity: Critical
- Finding: "ARP conflict: IP claimed by multiple MAC addresses. Possible ARP spoofing attack."

### 10.3 Deauthentication Storm Detection [IMPLEMENTED - Pcap Analyser]
- Source: Management frames in capture
- Check: High volume of deauthentication frames to same target in short time window
- Severity: Critical
- Finding: "Deauthentication storm detected. Active attack in progress."

### 10.4 Disassociation Storm Detection [IMPLEMENTED - Pcap Analyser]
- Source: Management frames in capture
- Check: High volume of disassociation frames
- Severity: High
- Finding: "Disassociation storm detected. Possible denial-of-service attack."

### 10.5 Authentication Flood Detection [IMPLEMENTED - Pcap Analyser]
- Source: Management frames in capture
- Check: Excessive authentication frames from many different MACs to one AP
- Severity: Medium
- Finding: "Authentication flood detected targeting AP."

### 10.6 Beacon Anomaly Detection [IMPLEMENTED - Pcap Analyser]
- Source: Beacons from same BSSID over time
- Check: Beacon security parameters change during capture
- Severity: High
- Finding: "BSSID changed security parameters during capture. Possible AP compromise or spoofing."

### 10.7 Probe Response Spoofing Detection [IMPLEMENTED - Pcap Analyser]
- Source: Probe responses
- Check: Probe response from BSSID that does not match any known beacon BSSID
- Severity: Medium
- Finding: "Probe responses from unknown BSSIDs. Possible evil twin or KARMA attack."


---

## IMPLEMENTATION STATUS SUMMARY

### Total: 42 of 42 checks implemented (100%)

Network Scanner: 19 checks
- 1.1 Open network, 1.2 WEP, 1.3 WPA-TKIP, 1.4 TKIP mixed, 1.5 WPA/WPA2 mixed
- 1.6 WPA3 transition, 1.7 No WPA3, 1.8 Group cipher TKIP, 1.9 WPA2-PSK without SAE
- 2.1 No PMF, 2.2 PMF capable, 2.3 PMF required, 2.4 WPA2-PSK no PMF
- 3.1 WPS enabled, 3.2 WPS version, 3.3 WPS config state
- 4.1 Hidden SSID
- 5.1 SSID security mismatch, 5.2 SSID vendor mismatch, 5.4 Similar BSSIDs
- 8.3 Legacy standard, 8.5 SSID info leak, 8.6 Default SSID

Pcap Analyser: 27 checks
- 4.2 Hidden SSID deanonymisation, 4.3 Client probing hidden
- 5.3 Multi-vendor SSID
- 6.1 EAP method, 6.2 PEAP/MSCHAPv2, 6.3 Expired cert, 6.4 Expiring cert
- 6.5 Weak cert signature, 6.6 Self-signed cert, 6.7 Username exposure, 6.8 EAPOL failure
- 7.1 Insecure network probing, 7.2 No MAC randomisation, 7.3 Saved network broadcast
- 7.4 Open while encrypted available
- 8.1 Too many SSIDs, 8.2 Firmware age, 8.4 Legacy rates, 8.7 AP name broadcast
- 9.1 mDNS, 9.2 STP, 9.3 CDP, 9.4 LLDP
- 10.1 Rogue DHCP, 10.2 ARP spoofing, 10.3 Deauth storm, 10.4 Disassoc storm
- 10.5 Auth flood, 10.6 Beacon anomaly, 10.7 Probe response spoofing
