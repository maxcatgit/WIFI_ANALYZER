# Wi-Fi Analyser - Complete Feature Documentation

## Product Overview

A browser-based Wi-Fi packet capture, analysis, planning, and security auditing platform running on Raspberry Pi. Controlled from any device via web browser. No software installation required on the viewing device.

**Platform:** Raspberry Pi Zero 2 W (or any Pi / Linux SBC)
**Hardware:** Comfast tri-band Wi-Fi 6E/7 USB adapter (2.4/5/6 GHz)
**Interface:** Web UI (Flask backend, HTML/CSS/JS frontend)
**Analysis Engine:** tshark (Wireshark CLI)

---

## Pages & Features

### 1. Packet Capture (`/` - index.html)

The core capture interface. Controls Wi-Fi adapter(s) in monitor mode.

**Features:**
- Single or multi-adapter packet capture
- Channel selection across 2.4 GHz, 5 GHz, and 6 GHz bands
- Configurable dwell time per channel (200ms to 10s)
- Frame type filtering: Management, Control, Data (and subtypes)
- Sub-type filtering: Beacons, Probes, EAPOL, Auth, Assoc, Deauth, etc.
- Filename suffix for easy organisation
- Time-based file splitting for long captures
- Multi-adapter simultaneous capture into single pcap
- Live capture download without interrupting capture
- Monitor mode auto-setup
- System shutdown control

### 2. Network Scanner (`/networks` - networks.html)

Live Wi-Fi environment scanning using the Pi's wlan0 interface.

**Features:**
- One-click scan of all visible networks
- Auto-refresh mode (30-second interval)
- Sortable columns: Risk, SSID, BSSID, Channel, Band, Signal, Security, etc.
- Per-network vulnerability assessment with severity badges
- 20+ automated security checks per network:
  - Open network detection (Critical)
  - WEP encryption detection (Critical)
  - WPA-TKIP only / mixed mode (High)
  - WPA2-PSK without PMF (High)
  - WPA3 transition mode downgrade risk (Medium)
  - WPS enabled / unconfigured state (Medium)
  - No PMF support (Medium)
  - Default SSID detection (Medium)
  - Group cipher TKIP (Medium)
  - Hidden SSID (Low)
  - Legacy Wi-Fi standard (Low)
  - SSID info leak (Low)
  - WPA2-PSK brute-force risk (Info)
  - No WPA3 support (Info)
- Cross-network checks:
  - Same SSID different security (rogue AP indicator)
  - Same SSID different vendors
  - Suspiciously similar BSSIDs
- Expandable vulnerability detail per network
- Vulnerability summary bar (Critical/High/Medium/Low/Clean counts)
- PMF and WPS status indicators
- Signal strength bar visualisation
- Band summary (2.4/5/6 GHz counts)

### 3. Channel Analysis (`/channels` - channels.html)

RF environment analysis using live scan data.

**Features:**
- Channel congestion map: bar charts per channel for 2.4 GHz, 5 GHz, 6 GHz
- Color-coded: green (1-3 APs), yellow (4-6 APs), red (7+ APs)
- Recommended channels marked (1, 6, 11 for 2.4 GHz)
- Adjacent channel interference detection (non-standard 2.4 GHz channels)
- 40 MHz in 2.4 GHz detection (HT40 in congested environment)
- Heavy congestion warnings
- Channel utilisation from BSS Load element (when available)
- Optimal channel recommendation per band
  - 2.4 GHz: recommends from 1, 6, 11 only
  - 5 GHz: separate DFS and non-DFS recommendations
- Issues & warnings panel
- BSS Load utilisation table

### 4. Pcap Analyser (`/analyzer` - analyzer.html)

Deep packet analysis of uploaded .pcap/.pcapng files.

**Phase 1 - Data Collection (18 automated tshark passes):**
1. Beacon extraction (BSSID, SSID, frequency, timestamp, privacy)
2. Hidden SSID deanonymisation via probe responses
3. EAPOL 4-way handshake analysis (bad password detection)
4. Client-to-AP association mapping (ToDS data frames)
5. Wired host detection (FromDS data frames)
6. 802.1X EAP identity extraction
7. EAP method detection (PEAP, TLS, TTLS, MSCHAPv2, etc.)
8. Certificate inspection (subject, issuer, expiry, algorithm, self-signed)
9. Management attack detection (deauth, disassoc, auth floods)
10. Directed probe request analysis (client privacy)
11. Beacon anomaly detection (security parameter changes)
12. Protocol leakage (ARP, DHCP, CDP, LLDP, STP, mDNS)
13. Probe response spoofing detection
14. Data frame analysis (retry, signal, airtime - combined pass)
15. Management frame statistics (beacon/probe overhead)
16. Client capability extraction (HT/VHT/HE, bands)
17. Roaming event extraction (assoc/reassoc + 802.11r FT detection)
18. DHCP transaction timing & DNS response timing

**Phase 2 - Per-SSID Analysis:**

**Summary Tab:**
- Health Score (0-100, A-F grade) based on security, retries, signal, firmware age, SSIDs, roaming support
- AP count, BSSID count, client count, SSID count
- TX power ranges per band
- Wireshark display filter for the analysed network
- Download Report button (self-contained HTML)

**Access Points Tab:**
- AP grouping by vendor pattern (Meraki, Cisco, Ubiquiti, Aruba, Mist, Generic)
- Expandable AP rows showing per-BSSID details
- Radio info: band, channel, TX power
- Station count, SSIDs per AP

**SSID Details Tab:**
- Per-BSSID: band, channel, security, Wi-Fi generation, rates
- 802.11k/r/v roaming support indicators

**Host Details Tab:**
- Wireless clients: MAC, vendor, SSID, BSSID, frame count, EAP username, roaming status
- Randomised MAC detection
- Wired hosts detected via wireless traffic

**Retries Tab:**
- Per-client retry rate table (color-coded: >20% critical, >10% high)
- Per-AP retry rate table
- Retry vs RSSI correlation

**Signal Tab:**
- Signal distribution histogram: excellent/good/fair/weak/very weak
- Per-client RSSI statistics: average, min, max, standard deviation, sample count
- Weak client identification

**Clients Tab (Capabilities):**
- Wi-Fi generation distribution chart (Wi-Fi 4/5/6/6E/7)
- Per-client: HT/VHT/HE support, bands probed
- Dual-band vs single-band count
- Legacy device identification

**Roaming Tab:**
- Summary: roaming clients, total roams, FT roams, sticky clients, ping-pong
- Visual timeline per roaming client
- Roam duration measurement (ms) with color coding (<50ms excellent, >500ms problematic)
- 802.11r Fast Transition detection ([FT] badge)
- Sticky client table (clients on weak APs)
- Ping-pong roaming table (excessive transitions)

**Airtime Tab:**
- Data rate distribution: legacy/HT/VHT/HE bar chart
- Management frame overhead percentage
- Beacon overhead percentage
- Per-client airtime consumption table (color-coded >30% hog)
- Low data rate frame count
- Probe request storm detection

**DHCP/DNS Tab:**
- DHCP transaction timing table: client, IP, server, transaction time, status
- DHCP failure detection (timeouts, NAKs)
- DNS server performance table: avg latency, max latency, timeouts
- Color-coded response times (green <50ms, orange <200ms, red >200ms)

**Problems Tab:**
- All detected problems sorted by severity (Critical > High > Medium > Low > Info)
- 40+ automated problem detection rules across:
  - Security (deauth attacks, rogue APs, spoofing, protocol leakage)
  - Performance (retry rates, weak signals, coverage gaps, airtime hogs)
  - Configuration (legacy rates, missing roaming support, too many SSIDs)
  - Authentication (bad passwords, certificate issues, EAP weaknesses)
  - Network layer (DHCP timeouts, slow DNS, multiple DHCP servers)
  - Client behaviour (sticky clients, ping-pong, legacy devices, probe storms)

**Report Download:**
- Self-contained HTML report with:
  - Executive summary with health score
  - Network inventory table
  - Problem list by severity
  - Client inventory
  - Retry analysis table
  - Prioritised recommendations
  - Health score breakdown with penalty details

### 5. Site Survey (`/survey` - survey.html)

Floor plan-based Wi-Fi heatmap survey tool. Same methodology as Ekahau and AirMagnet.

**4-Step Wizard:**

1. **Upload Floor Plan** - drag & drop any image (PNG, JPG, SVG)
2. **Set Scale** - click two points on the plan, enter real-world distance
3. **Walk & Tap** - tap position on floor plan; automatic Wi-Fi scan at each point
4. **View Heatmap** - IDW-interpolated colour overlay on floor plan

**Heatmap Layers:**
- Signal Strength (dBm): green (strong) to red (weak)
- AP Count: number of visible APs per location
- Channel Count: RF congestion indicator

**Features:**
- BSSID filter: view heatmap for a specific AP
- Measurement points shown as white dots
- Color legend per layer
- Multiple survey projects
- Scale calibration for accurate distance representation

### 6. Capacity Planner (`/capacity` - capacity.html)

Airtime-budget-based AP count calculator. Uses industry-standard three-way formula.

**Core Formula:**
```
APs_required = max(APs_for_coverage, APs_for_capacity, APs_for_client_limit)
```

**Input Parameters:**
- AP model selection (from 55+ model library)
- Wall type / environment (5 types: open plan to heavy concrete)
- SSID count (beacon overhead calculation)
- Design margin (10%, 20%, 30%)
- Throughput assumption mode (conservative, moderate, optimistic)
- Client device mix (Wi-Fi 4/5/6/6E/7 percentage sliders)
- Multiple zones with independent settings

**Per-Zone Configuration:**
- Environment presets (9 types: open office, dense office, conference room, lecture hall, warehouse, hospital, hotel, stadium, classroom)
- User profile presets (Light 1.5 Mbps, Medium 6 Mbps, Heavy 12 Mbps, Very Heavy 25 Mbps, IoT 0.1 Mbps)
- Custom area, device count, throughput per device

**Reference Data Built In:**
- 5 Wi-Fi generations with throughput tables (conservative/moderate/optimistic)
- MAC efficiency per generation (45% Wi-Fi 4 to 78% Wi-Fi 7)
- 12 application profiles with bandwidth, latency, jitter, min RSSI requirements
- 5 composite user profiles
- 9 environment density presets

**Output:**
- Total AP count recommendation
- Per-zone breakdown: coverage APs, capacity APs, client-limit APs
- Binding constraint identification (which factor drives AP count)
- Airtime budget per zone with per-generation breakdown
- Clients per AP and area per AP metrics
- Actionable recommendations
- Usable airtime calculation (after beacon/management/margin deduction)

### 7. AP Model Library (`/ap-models` - ap_models.html)

Searchable database of enterprise access point specifications.

**55+ AP models from 12 vendors:**
- Cisco (Catalyst 9100 series: C9130, C9136, C9162, C9120, C9124, Aironet 3800/2800/1850)
- Cisco Meraki (MR57, MR56, MR46, MR36, MR86)
- Aruba HPE (AP-735, AP-635, AP-535, AP-515, AP-505, AP-387, AP-345)
- Juniper Mist (AP47, AP45, AP43, AP34, AP63)
- Ruckus CommScope (R770, R760, R750, R650, R550, T750)
- Ubiquiti (U7 Pro, U7 Pro Max, U6 Enterprise, U6 Pro, U6 Lite, UAP-AC-Pro, UAP-AC-HD)
- Extreme Networks (AP5020, AP4000, AP3000)
- Cambium Networks (XV3-8, XE5-8, XV2-2)
- Fortinet (FAP-441K, FAP-431G, FAP-231G, FAP-234G)
- TP-Link Omada (EAP773, EAP690E HD, EAP670, EAP660 HD, EAP225)
- EnGenius (ECW536, ECW336, ECW230)
- ZyXEL (WAX780, WAX640-6E, WAX630S)
- Netgear (WBE758, WAX638E, WAX630, WAX620)

**Per-Model Data:**
- Wi-Fi generation (Wi-Fi 4 through Wi-Fi 7)
- 802.11 standard
- Bands (2.4/5/6 GHz)
- Spatial streams (MIMO configuration)
- Maximum data rate (Mbps)
- Maximum client count
- TX power per band (dBm)
- Antenna type (Internal/External/BeamFlex+)
- PoE standard (802.3af/at/bt)
- Indoor/Outdoor rating
- Release year
- Notes (key differentiators)

**UI Features:**
- Full-text search across all fields
- Filter by vendor, Wi-Fi generation, indoor/outdoor
- Sortable columns
- Wi-Fi generation summary cards (click to filter)
- Expandable detail rows
- Color-coded generation and band badges

### 8. File Manager (`/files` - files.html)

Manage pcap capture files stored on the device.

**Features:**
- Disk space monitoring (total/used/free)
- Capture file listing with size, date, grouping
- Analyzer upload file listing
- Group by date or name suffix
- File deletion (pcap/pcapng only, security-restricted paths)
- Size totals per group

---

## Architecture

```
Raspberry Pi Zero 2 W
  |
  +-- Flask Web Server (app.py, port 5000)
  |     |-- Capture control (tcpdump, screen, iw)
  |     |-- Network scanning (iw dev wlan0 scan)
  |     |-- Pcap analysis (tshark - 18 automated passes)
  |     |-- Capacity planning engine (capacity_planner.py)
  |     |-- AP model library (ap_models.py)
  |     |-- Survey session management
  |     |-- File management
  |     |-- Report generation (self-contained HTML)
  |
  +-- Web UI (HTML/CSS/JS - 8 pages)
  |     |-- index.html (Capture)
  |     |-- networks.html (Network Scanner)
  |     |-- channels.html (Channel Analysis)
  |     |-- analyzer.html (Pcap Analyser - 11 tabs)
  |     |-- survey.html (Site Survey / Heatmap)
  |     |-- capacity.html (Capacity Planner)
  |     |-- ap_models.html (AP Model Library)
  |     |-- files.html (File Manager)
  |
  +-- Wi-Fi Adapter(s) in monitor mode
        |-- Comfast tri-band (2.4/5/6 GHz)
        |-- Optional additional adapters for multi-band
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Capture page |
| GET | `/adapters` | List monitor-mode adapters |
| POST | `/monitor_on` | Enable monitor mode |
| POST | `/start_capture` | Start packet capture |
| POST | `/stop_capture` | Stop packet capture |
| GET | `/download/<adapter>` | Download capture file |
| GET | `/networks` | Network scanner page |
| GET | `/scan` | Trigger live Wi-Fi scan |
| GET | `/channels` | Channel analysis page |
| GET | `/analyzer` | Pcap analyser page |
| POST | `/analyzer/upload` | Upload pcap for analysis |
| GET | `/analyzer/status/<id>` | Poll analysis progress |
| POST | `/analyzer/analyze` | Run per-SSID analysis |
| POST | `/analyzer/report` | Generate HTML report |
| GET | `/survey` | Site survey page |
| POST | `/survey/create` | Create survey project |
| POST | `/survey/upload_plan/<id>` | Upload floor plan |
| POST | `/survey/set_scale/<id>` | Set floor plan scale |
| POST | `/survey/record_point/<id>` | Record measurement point |
| GET | `/survey/heatmap/<id>` | Get heatmap data |
| GET | `/capacity` | Capacity planner page |
| GET | `/api/capacity/reference` | Get reference data |
| POST | `/api/capacity/calculate` | Run capacity calculation |
| GET | `/ap-models` | AP model library page |
| GET | `/api/ap-models` | Search/filter AP models |
| GET | `/files` | File manager page |
| GET | `/files/list` | List all capture files |
| POST | `/files/delete` | Delete capture files |
| POST | `/shutdown` | Shut down the Pi |

---

## File Structure

```
WIFI_ANALYSER/
  app.py                 # Main Flask application (3800+ lines)
  ap_models.py           # AP vendor model database (55+ models)
  capacity_planner.py    # Capacity planning engine
  index.html             # Packet capture UI
  networks.html          # Network scanner UI
  channels.html          # Channel analysis UI
  analyzer.html          # Pcap analyser UI (11 tabs)
  survey.html            # Site survey / heatmap UI
  capacity.html          # Capacity planner UI
  ap_models.html         # AP model library UI
  files.html             # File manager UI
  README.md              # Quick start guide
  docs/
    Feature_Documentation.md               # This file
    Competitive_Analysis_...Ekahau...md    # Competitive analysis vs Ekahau & AirMagnet
    Hardware_Upgrade_Path.md               # Hardware upgrade recommendations
    security_verifications.md              # Security check reference
    wifi_security_reference.md             # Wi-Fi security knowledge base
    bugs                                   # Bug tracker (all fixed)
    future features                        # Feature roadmap
  installation/                            # Installation scripts
  README_IMG/                              # README screenshots
```

---

*Last updated: 2026-04-02*
