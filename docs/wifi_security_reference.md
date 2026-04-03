# Wi-Fi Security Protocols & Vulnerabilities Reference

## Protocol Overview

| Protocol | Year | Encryption | Key Exchange | Status |
|----------|------|-----------|--------------|--------|
| Open | 1997 | None | None | Active (public hotspots) |
| WEP | 1999 | RC4 (40/104-bit) | Shared Key | Broken, deprecated |
| WPA | 2003 | TKIP (RC4-based) | PSK / 802.1X | Deprecated 2012 |
| WPA2 | 2004 | AES-CCMP (128-bit) | PSK / 802.1X | Active, aging |
| WPA3 | 2018 | AES-CCMP / AES-GCMP (128/256-bit) | SAE / 802.1X (192-bit) | Current standard |
| OWE | 2018 | AES-CCMP | Diffie-Hellman | Enhanced Open |

---

## 1. Open Networks (No Encryption)

### How It Works
No authentication or encryption. All frames are transmitted in plaintext.

### Vulnerabilities

**OPN-1: Complete Traffic Exposure**
- Severity: Critical
- All data (HTTP, DNS, emails, credentials) is visible to any device within range
- Tools: Any packet sniffer (Wireshark, tcpdump)
- Impact: Full data interception

**OPN-2: Evil Twin / Rogue AP**
- Severity: Critical
- Attacker creates an AP with the same SSID
- Clients auto-connect to the strongest signal
- All traffic routes through the attacker (man-in-the-middle)
- Particularly dangerous for public hotspots (airports, cafes)

**OPN-3: Session Hijacking**
- Severity: High
- Unencrypted session cookies can be intercepted and replayed
- Grants access to authenticated web sessions

**OPN-4: DNS Spoofing**
- Severity: High
- DNS queries are visible and can be intercepted
- Attacker redirects traffic to malicious servers

### Mitigation
- Use WPA3-OWE (Opportunistic Wireless Encryption) for encryption without a password
- If Open is required, enforce captive portal with HTTPS
- Users should use VPN on open networks

---

## 2. WEP (Wired Equivalent Privacy)

### How It Works
- Uses RC4 stream cipher with a 24-bit Initialisation Vector (IV)
- Same key shared by all clients
- IV is prepended to each packet in plaintext
- CRC-32 for integrity (not cryptographic)

### Vulnerabilities

**WEP-1: IV Collision / Key Recovery (FMS Attack)**
- Severity: Critical
- CVE: N/A (fundamental protocol flaw)
- The 24-bit IV space (16.7 million) cycles quickly on busy networks
- Repeated IVs allow statistical recovery of the RC4 key
- Fluhrer, Mantin, Shamir (2001) demonstrated weak IV exploitation
- Requires: ~4 million captured packets
- Tools: aircrack-ng

**WEP-2: KoreK Chopchop Attack**
- Severity: Critical
- Decrypts individual packets without knowing the key
- Exploits CRC-32 weakness to iteratively guess plaintext bytes
- Can decrypt a packet in minutes
- Tools: aireplay-ng, chopchop

**WEP-3: PTW Attack (Pyshkin, Tews, Weinmann)**
- Severity: Critical
- Dramatically reduced packets needed for key recovery to ~40,000-85,000
- Works by exploiting RC4 key scheduling algorithm correlations
- Can crack WEP key in under 2 minutes on active networks
- Tools: aircrack-ng (default method)

**WEP-4: Fragmentation Attack**
- Severity: High
- Obtains PRGA (pseudo-random generation algorithm) keystream
- Allows injection of arbitrary packets
- Only needs one captured data packet
- Tools: aireplay-ng --fragment

**WEP-5: ARP Replay Injection**
- Severity: High
- Captures an ARP packet and replays it to generate traffic
- Forces IV generation to accelerate key cracking
- Turns passive attack into active: crack time from hours to minutes
- Tools: aireplay-ng -3

**WEP-6: Shared Key Authentication Bypass**
- Severity: High
- The challenge-response in Shared Key Auth leaks one keystream
- Captured keystream allows the attacker to authenticate
- Ironically, Shared Key Auth is weaker than Open Auth under WEP

**WEP-7: Bit-Flipping Attack**
- Severity: Medium
- CRC-32 is linear: modifying ciphertext bits predictably changes plaintext
- Allows targeted modification of packet contents without knowing the key
- Can redirect traffic, change IP destinations

### Mitigation
- No mitigation exists. WEP is fundamentally broken.
- Upgrade immediately to WPA2-AES (minimum) or WPA3-SAE

---

## 3. WPA (Wi-Fi Protected Access)

### How It Works
- Temporary standard bridging WEP to full 802.11i (WPA2)
- Uses TKIP (Temporal Key Integrity Protocol) built on RC4
- Per-packet key mixing function
- 48-bit IV (vs WEP's 24-bit) to prevent IV reuse
- Michael MIC for integrity (replaces CRC-32)
- Supports PSK (Pre-Shared Key) and 802.1X (Enterprise)

### Vulnerabilities

**WPA-1: Beck-Tews Attack on TKIP**
- Severity: High
- Published: 2008
- Exploits weaknesses in the Michael MIC and TKIP key scheduling
- Can decrypt short packets (ARP) and inject up to 7 forged packets
- Requires QoS (WMM) enabled and long re-keying interval
- Time: 12-15 minutes per packet decryption

**WPA-2: Ohigashi-Morii Attack**
- Severity: High
- Published: 2009
- Practical man-in-the-middle extension of Beck-Tews
- Reduces attack time to ~1 minute
- Allows injection of forged frames

**WPA-3: TKIP Michael MIC Denial of Service**
- Severity: Medium
- Two MIC failures within 60 seconds triggers a 60-second network shutdown
- TKIP countermeasure designed to detect attacks, but can be weaponised for DoS
- Attacker intentionally triggers MIC failures

**WPA-4: PSK Offline Dictionary Attack**
- Severity: High (same as WPA2-PSK)
- The 4-way handshake can be captured
- PSK is derived from passphrase + SSID using PBKDF2 (4096 iterations)
- Weak passphrases are crackable via dictionary/brute-force
- Tools: aircrack-ng, hashcat, cowpatty

**WPA-5: WPA/WPA2 Mixed Mode Downgrade**
- Severity: Medium
- APs offering both WPA-TKIP and WPA2-AES allow downgrade
- Attacker manipulates RSNE in beacons to force TKIP
- Client may accept the weaker cipher suite

### Mitigation
- Disable WPA (TKIP) entirely
- Use WPA2-only with CCMP/AES
- Upgrade to WPA3-SAE

---

## 4. WPA2 (IEEE 802.11i)

### How It Works
- Full implementation of IEEE 802.11i
- Mandatory AES-CCMP (Counter Mode with CBC-MAC Protocol)
- 128-bit AES encryption, 128-bit block cipher
- Two modes:
  - **WPA2-Personal (PSK)**: Pre-Shared Key, 4-way handshake derives session keys
  - **WPA2-Enterprise (802.1X)**: Per-user authentication via RADIUS, EAP methods
- Optional PMF (Protected Management Frames / 802.11w)

### 4-Way Handshake (EAPOL)
1. AP → Client: ANonce (AP nonce)
2. Client → AP: SNonce + MIC (client nonce, proves PSK knowledge)
3. AP → Client: GTK + MIC (group key, encrypted)
4. Client → AP: ACK

The PTK (Pairwise Transient Key) is derived from: PMK + ANonce + SNonce + AP MAC + Client MAC

### Vulnerabilities

**WPA2-1: Offline PSK Brute-Force (Handshake Capture)**
- Severity: High
- The 4-way handshake contains enough information to verify a password guess
- Capturing messages 1 and 2 (or 2 and 3) is sufficient
- No forward secrecy: cracking the PSK decrypts all past and future traffic
- GPU-accelerated cracking: hashcat can test billions of candidates per second
- Tools: aircrack-ng, hashcat (mode 22000), hcxtools
- PMKID variant: only need message 1 (no client needed)

**WPA2-2: PMKID Attack**
- Severity: High
- Published: 2018 by Jens Steube (hashcat author)
- The PMKID is included in the first message of the 4-way handshake
- PMKID = HMAC-SHA1-128(PMK, "PMK Name" + AP MAC + Client MAC)
- Attacker needs only a single frame from the AP (no client interaction)
- Eliminates need for deauthentication or waiting for a client to connect
- Tools: hcxdumptool, hcxpcapngtool, hashcat (mode 22000)

**WPA2-3: KRACK (Key Reinstallation Attacks)**
- Severity: High
- CVE: CVE-2017-13077 through CVE-2017-13088
- Published: 2017 by Mathy Vanhoef
- Exploits handshake message retransmission to reinstall an already-in-use key
- Nonce reuse allows decryption and packet injection
- Affects: 4-way handshake, group key handshake, FT handshake, PeerKey handshake
- Linux/Android particularly vulnerable (wpa_supplicant 2.4+): key reset to all zeros
- Requires: man-in-the-middle position
- Patched in most implementations, but unpatched devices remain vulnerable

**WPA2-4: Deauthentication Attack (No PMF)**
- Severity: High
- Management frames (deauth, disassoc) are unprotected without PMF (802.11w)
- Forged deauth frames disconnect clients
- Used to:
  - Force handshake recapture for offline cracking
  - Denial of service
  - Force clients to connect to evil twin AP
- Tools: aireplay-ng -0, mdk3/mdk4

**WPA2-5: Hole196 (GTK Vulnerability)**
- Severity: Medium
- CVE: N/A (protocol design limitation)
- Published: 2010 by AirTight Networks
- Any authenticated client has the GTK (Group Temporal Key)
- Insider can use GTK to decrypt broadcast/multicast traffic from other clients
- Can craft ARP poisoning packets using GTK
- Requires: already authenticated to the network

**WPA2-6: FragAttacks (Fragmentation and Aggregation Attacks)**
- Severity: Medium to High
- CVE: CVE-2020-24586 through CVE-2020-26145
- Published: 2021 by Mathy Vanhoef
- Collection of 12 vulnerabilities in the 802.11 specification and implementations
- Three design flaws:
  - Frame aggregation flag not authenticated (inject arbitrary frames)
  - Fragment cache not cleared on reconnection
  - Mixed plaintext and encrypted fragments accepted
- Nine implementation bugs across various vendors
- Affects: virtually all Wi-Fi devices since 1997
- Can inject packets, exfiltrate data from secure networks

**WPA2-7: Kr00k**
- Severity: Medium
- CVE: CVE-2019-15126
- Published: 2020 by ESET
- Affects Broadcom and Cypress Wi-Fi chips
- After disassociation, buffered data frames are transmitted encrypted with an all-zero TK
- Allows decryption of a few kilobytes of data after each disassociation
- Affects: billions of devices (iPhones, iPads, Macs, Samsung, Amazon Echo, Raspberry Pi)

**WPA2-8: Enterprise: RADIUS Impersonation (Evil Twin)**
- Severity: High
- 802.1X requires proper certificate validation by the client
- Many clients accept any certificate or skip validation
- Attacker sets up rogue AP with fake RADIUS server
- Captures EAP credentials (MSCHAPv2 can be cracked offline)
- Particularly effective with EAP-PEAP/MSCHAPv2 without certificate pinning

**WPA2-9: Enterprise: EAP Downgrade**
- Severity: Medium
- If multiple EAP methods are configured, attacker can reject stronger methods
- Forces client to fall back to weaker EAP type
- Example: forcing EAP-PEAP over EAP-TLS

### Mitigation
- Enable PMF (802.11w) as **required** — stops deauthentication attacks
- Use strong passphrases (15+ characters, random)
- Upgrade to WPA3-SAE (immune to offline brute-force)
- Enterprise: use EAP-TLS with certificate pinning, disable MSCHAPv2
- Apply vendor patches for KRACK, FragAttacks, Kr00k
- Disable TKIP entirely (CCMP only)

---

## 5. WPA3 (IEEE 802.11-2020)

### How It Works
- **WPA3-Personal (SAE)**: Simultaneous Authentication of Equals
  - Based on Dragonfly key exchange (RFC 7664)
  - Password-authenticated key exchange (PAKE)
  - Forward secrecy: each session has unique keys
  - Resistant to offline dictionary attacks
  - PMF (802.11w) mandatory
- **WPA3-Enterprise**: 192-bit security suite
  - CNSA (Commercial National Security Algorithm) suite
  - 256-bit GCMP encryption
  - 384-bit ECDH key exchange
  - 256-bit BIP-GMAC for management frame protection
- **WPA3 Transition Mode**: AP advertises both WPA3-SAE and WPA2-PSK

### Vulnerabilities

**WPA3-1: Dragonblood Side-Channel Attacks**
- Severity: Medium
- CVE: CVE-2019-9494, CVE-2019-9495, CVE-2019-9496
- Published: 2019 by Mathy Vanhoef and Eyal Ronen
- Cache-based side-channel attack on the Dragonfly handshake
- Timing-based side-channel reveals information about the password encoding
- Can partition passwords into groups, reducing brute-force search space
- Requires: attacker on same machine or microarchitectural side channel
- Patched in updated implementations

**WPA3-2: Dragonblood Downgrade Attack**
- Severity: Medium
- CVE: CVE-2019-9497
- In WPA3 Transition Mode, attacker sets up rogue AP offering only WPA2-PSK
- Client falls back to WPA2-PSK, handshake can be captured and cracked offline
- Transition mode is inherently weaker than WPA3-only mode

**WPA3-3: SAE Group Downgrade**
- Severity: Low
- Attacker forces use of a weaker elliptic curve group
- SAE supports multiple groups; client can be tricked into using weaker ones
- Mitigated by limiting supported groups to known-strong ones

**WPA3-4: Denial of Service via SAE**
- Severity: Medium
- SAE handshake is computationally expensive (elliptic curve operations)
- Attacker sends many SAE commit frames to exhaust AP resources
- Anti-clogging token mechanism exists but adds complexity
- More CPU-intensive than WPA2 handshake for the AP

**WPA3-5: Implementation-Specific Bugs**
- Severity: Varies
- CVE: Various (implementation-dependent)
- Some early WPA3 implementations had flaws in the SAE state machine
- Improper validation of SAE commit/confirm messages
- Memory corruption in some implementations
- Patched in updated firmware/drivers

**WPA3-6: Transition Mode Rogue AP**
- Severity: Medium
- If both WPA3 and WPA2 SSIDs exist, attacker clones the WPA2 one
- Clients configured for the SSID connect via WPA2
- Full offline brute-force then applies
- Not a WPA3 flaw per se, but a deployment weakness

### Mitigation
- Use WPA3-only mode (disable transition mode) when all clients support WPA3
- Update firmware to address Dragonblood patches
- Limit SAE groups to strong curves only
- Enterprise: use 192-bit mode with EAP-TLS

---

## 6. OWE (Opportunistic Wireless Encryption)

### How It Works
- Defined in RFC 8110 and Wi-Fi Alliance Enhanced Open
- Provides encryption on open networks without requiring a password
- Uses Diffie-Hellman key exchange during association
- Encrypts all traffic with unique per-client keys
- No authentication (anyone can still connect)

### Vulnerabilities

**OWE-1: No Authentication**
- Severity: Medium
- OWE encrypts traffic but does not authenticate the AP
- Evil twin attacks still possible (attacker sets up rogue OWE AP)
- No way for client to verify it is connecting to the legitimate AP

**OWE-2: Transition Mode Downgrade**
- Severity: Medium
- OWE transition mode maintains a parallel Open SSID for backward compatibility
- Legacy clients connect without encryption
- Attacker can clone the Open SSID

### Mitigation
- OWE is still far better than Open (no encryption)
- Use OWE transition mode to provide backward compatibility while protecting capable clients
- For sensitive environments, use WPA3-SAE instead

---

## 7. WPS (Wi-Fi Protected Setup)

WPS is not a security protocol but a provisioning mechanism. It is a significant attack surface.

### How It Works
- PIN-based: 8-digit PIN printed on the AP
- Push-button: physical button press on AP and client
- NFC: near-field communication tap

### Vulnerabilities

**WPS-1: PIN Brute-Force (Reaver)**
- Severity: Critical
- CVE: CVE-2011-5053
- Published: 2011 by Stefan Viehbock
- The 8-digit PIN is validated in two halves (4 + 3 digits + 1 checksum)
- First half: 10,000 combinations, second half: 1,000 combinations
- Total keyspace: ~11,000 attempts (not 100 million)
- Average crack time: 2-10 hours
- Tools: Reaver, Bully

**WPS-2: Pixie Dust Attack**
- Severity: Critical
- Published: 2014 by Dominique Bongard
- Exploits weak random number generation in WPS implementations
- Recovers the PIN offline from a single WPS exchange
- Affected chipsets: Ralink, MediaTek, Realtek, Broadcom
- Crack time: seconds to minutes
- Tools: Reaver with -K flag, pixiewps

**WPS-3: WPS Lockout Bypass**
- Severity: Medium
- Some AP implementations have weak or no lockout after failed attempts
- Lockout can sometimes be reset by sending specific frames
- Some APs lock out by MAC: MAC spoofing bypasses the lockout

### Mitigation
- Disable WPS entirely
- If WPS is needed, disable PIN method and use push-button only
- Ensure AP firmware has proper rate limiting

---

## 8. Management Frame Vulnerabilities (Pre-802.11w)

These affect all protocols when PMF (802.11w) is not enabled.

**MGT-1: Deauthentication Flood**
- Severity: High
- Forged deauth frames disconnect clients
- Can target specific clients or broadcast to all
- Used for: DoS, handshake capture, forcing evil twin connection

**MGT-2: Disassociation Flood**
- Severity: High
- Similar to deauth but uses disassociation frames
- Forces client back to associated-but-not-authenticated state

**MGT-3: Beacon Flood**
- Severity: Medium
- Thousands of fake beacon frames with random SSIDs
- Overwhelms client network lists
- Can confuse or crash some client implementations

**MGT-4: Authentication Flood**
- Severity: Medium
- Floods AP with authentication requests
- Can exhaust AP resources and prevent legitimate connections

**MGT-5: Probe Response Flood**
- Severity: Low
- Fake probe responses to client probe requests
- Can direct clients to rogue APs

### Mitigation
- Enable PMF (802.11w) as required
- WPA3 mandates PMF
- Use wireless IDS/IPS to detect management frame attacks

---

## 9. General Wi-Fi Vulnerabilities (Protocol Independent)

**GEN-1: Evil Twin AP**
- Affects: All protocols
- Attacker creates AP with identical SSID and stronger signal
- Clients preferentially connect to stronger signal
- All traffic routed through attacker

**GEN-2: KARMA / Known Beacons Attack**
- Affects: Client devices
- Attacker responds to all probe requests from client devices
- Client auto-connects to a previously known SSID name
- Particularly effective against devices with long saved network lists

**GEN-3: Rogue AP Detection Evasion**
- Affects: Enterprise networks
- Rogue APs can be configured to mimic legitimate AP characteristics
- MAC spoofing, SSID cloning, channel matching

**GEN-4: Hidden SSID Discovery**
- Affects: Networks using SSID hiding
- Hidden SSIDs are revealed in probe requests and probe responses
- Passive monitoring reveals the SSID when any client connects
- Clients probe for hidden SSIDs everywhere, leaking the network name

**GEN-5: MAC Address Tracking**
- Affects: Client privacy
- Fixed MAC addresses allow tracking client device movement
- Mitigated by MAC address randomisation (iOS 14+, Android 10+)
- Some implementations have flaws that still allow de-randomisation

**GEN-6: Channel-Based Man-in-the-Middle**
- Affects: All protocols
- Attacker relays traffic between client and AP on different channels
- Enables selective packet dropping, injection, or modification
- Used as the basis for many advanced attacks (KRACK, etc.)

---

## 10. Comparison Matrix

### Encryption Strength

| Protocol | Cipher | Key Length | IV/Nonce | Integrity | Status |
|----------|--------|-----------|----------|-----------|--------|
| Open | None | None | None | None | Broken |
| WEP | RC4 | 40/104-bit | 24-bit IV | CRC-32 | Broken |
| WPA-TKIP | RC4 | 128-bit | 48-bit IV | Michael MIC | Deprecated |
| WPA2-CCMP | AES-CTR | 128-bit | 48-bit PN | CBC-MAC | Secure |
| WPA3-CCMP | AES-CTR | 128-bit | 48-bit PN | CBC-MAC | Secure |
| WPA3-GCMP | AES-GCM | 256-bit | 48-bit PN | GHASH | Secure |
| OWE | AES-CTR | 128-bit | 48-bit PN | CBC-MAC | Secure (no auth) |

### Vulnerability Summary

| Vulnerability | Open | WEP | WPA | WPA2 | WPA3 | OWE |
|--------------|------|-----|-----|------|------|-----|
| Traffic sniffing | Yes | Minutes | Partial | No* | No | No |
| Offline password crack | N/A | Minutes | Hours | Hours-Years** | No | N/A |
| Evil twin | Yes | Yes | Yes | Yes | Transition only | Yes |
| Deauth attack | Yes | Yes | Yes | Without PMF | No (PMF mandatory) | Without PMF |
| Key reinstallation | N/A | N/A | N/A | KRACK (patched) | No | No |
| Forward secrecy | No | No | No | No | Yes | Yes |
| Insider eavesdropping | Yes | Yes | Yes | Hole196 | Limited | No |

\* With CCMP encryption intact
\** Depends entirely on password strength

### Recommended Configuration (2024+)

| Use Case | Minimum | Recommended | Ideal |
|----------|---------|-------------|-------|
| Home | WPA2-PSK (AES) + strong passphrase | WPA3-SAE | WPA3-SAE only |
| Small business | WPA2-PSK + PMF required | WPA3 transition mode | WPA3-SAE only |
| Enterprise | WPA2-Enterprise + PMF | WPA3-Enterprise | WPA3-Enterprise 192-bit |
| Guest/Public | WPA2-PSK (shared) | OWE | OWE + captive portal |
| IoT | WPA2-PSK (separate VLAN) | WPA3-SAE | WPA3-SAE + network segmentation |

---

## 11. Detection Capabilities of This Tool

The network scanner and pcap analyser in this project can detect the following:

### From Live Scanning (Network Scanner)
- Protocol in use (Open/WEP/WPA/WPA2/WPA3)
- Cipher suites (TKIP/CCMP/GCMP)
- Authentication methods (PSK/SAE/802.1X/OWE)
- PMF status (none/capable/required)
- WPS enabled
- Hidden SSIDs
- Wi-Fi generation (802.11n/ac/ax)
- Legacy standards indicating outdated hardware

### From Packet Captures (Pcap Analyser)
- EAPOL 4-way handshake failures (bad passwords)
- BSS uptime (stale firmware detection)
- TX power misconfiguration (2.4/5 GHz imbalance)
- Excessive SSIDs (airtime waste)
- Legacy bit rates enabled
- Missing 802.11k/r/v roaming support
- 802.1X certificate expiry
- Client usernames from EAP identity
- Client roaming patterns
- Wired-side host identification
- Hidden SSID deanonymisation

---

*This document is a reference for understanding Wi-Fi security. All information is for authorised network analysis and defensive security purposes.*
