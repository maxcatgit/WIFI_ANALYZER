# Competitive Analysis: Wi-Fi Analyser (Raspberry Pi Zero 2) vs Ekahau vs AirMagnet

## Document Purpose

This document provides a deep-dive comparison between three Wi-Fi analysis platforms: our Raspberry Pi-based Wi-Fi Analyser, Ekahau AI Pro (Juniper), and AirMagnet (NetAlly). It evaluates features, hardware, pricing, target markets, and identifies where our product fills gaps that the enterprise incumbents do not address.

---

## 1. Product Overview

### 1.1 Wi-Fi Analyser (Raspberry Pi Zero 2 W)

A lightweight, portable, browser-based Wi-Fi packet capture and analysis tool built on a Raspberry Pi Zero 2 W. Accessed via any web browser on any device (phone, tablet, laptop). Designed for Wi-Fi professionals who need fast, actionable diagnostics from real captured traffic.

**Platform:** Raspberry Pi Zero 2 W with Comfast tri-band USB Wi-Fi adapter (2.4 + 5 + 6 GHz, Wi-Fi 6E/7, MediaTek chipset) in monitor mode
**Interface:** Web-based (HTML/CSS/JS frontend, Python/Flask backend)
**Analysis engine:** tshark (Wireshark CLI) for deep packet inspection
**Bands covered:** 2.4 GHz, 5 GHz, and 6 GHz (tri-band via Comfast adapter)
**Cost basis:** Under $60 in hardware (Pi ~$15, adapter ~$25-40, SD card ~$8)

### 1.2 Ekahau AI Pro (Juniper Networks)

The market leader in Wi-Fi network planning and site survey. Acquired by Juniper Networks in 2023. Focuses on predictive design, heatmap surveys, and AP placement optimisation. Does NOT perform packet-level troubleshooting or security analysis.

**Platform:** Windows 10/11, macOS 11+
**Hardware:** Ekahau Sidekick 2 (dedicated dual-radio USB survey dongle with spectrum analyser)
**Price range:** $5,000 - $6,000+ first year (software subscription + Sidekick hardware)

### 1.3 AirMagnet (NetAlly)

A mature suite of Wi-Fi analysis tools covering survey, real-time troubleshooting, protocol analysis, and security auditing. Acquired through multiple transitions (AirMagnet Inc. to Fluke Networks to NetAlly).

**Platform:** Windows only (no macOS)
**Hardware:** Requires compatible USB Wi-Fi adapters (chipset-specific); Spectrum XT dongle for RF analysis
**Price range:** $12,000 - $18,000+ for the full suite (Survey PRO + WiFi Analyzer PRO + Spectrum XT)

---

## 2. Feature Comparison Matrix

| Feature Category | Wi-Fi Analyser (Pi) | Ekahau AI Pro | AirMagnet Suite |
|---|:---:|:---:|:---:|
| **CAPTURE & DATA COLLECTION** | | | |
| Live packet capture (monitor mode) | Yes | No | Limited |
| Frame type filtering (mgt/ctl/data) | Yes | No | Yes |
| Sub-type filtering (beacon, EAPOL, probe) | Yes | No | Yes |
| Channel hopping with dwell time control | Yes | No | No |
| Multi-adapter simultaneous capture | Yes | No | No |
| Split captures (time-based file rotation) | Yes | No | No |
| Pcap file export (Wireshark compatible) | Yes | No | Yes |
| | | | |
| **NETWORK SCANNING & DISCOVERY** | | | |
| Live network scanning | Yes | Yes | Yes |
| SSID detection (including hidden) | Yes | Yes | Yes |
| Hidden SSID deanonymisation | Yes | No | Limited |
| Security protocol identification | Yes | Yes | Yes |
| Vulnerability assessment per network | Yes | No | Yes |
| Per-network risk scoring | Yes | No | Partial |
| WPS detection and risk flagging | Yes | Yes | Yes |
| PMF (802.11w) status detection | Yes | Yes | Yes |
| Vendor identification (OUI lookup) | Yes | Yes | Yes |
| | | | |
| **PCAP DEEP ANALYSIS** | | | |
| AP grouping by vendor pattern | Yes | N/A | No |
| BSSID-to-AP correlation | Yes | Partial | Partial |
| EAPOL 4-way handshake analysis | Yes | No | Yes |
| Bad password / failed auth detection | Yes | No | Yes |
| EAP method detection (PEAP, TLS, etc.) | Yes | No | Yes |
| 802.1X username extraction | Yes | No | Yes |
| Certificate inspection (expiry, algo, issuer) | Yes | No | Limited |
| Client-to-AP association mapping | Yes | Partial | Yes |
| Wired host detection via wireless | Yes | No | No |
| | | | |
| **RETRY & RETRANSMISSION ANALYSIS** | | | |
| Per-client retry rate | Yes | No | Yes |
| Per-AP retry rate | Yes | No | Yes |
| Retry-to-RSSI correlation | Yes | No | Partial |
| Automatic problem flagging (>10%, >20%) | Yes | No | Yes |
| | | | |
| **SIGNAL STRENGTH ANALYSIS** | | | |
| Per-client RSSI statistics | Yes | Heatmap-based | Yes |
| Signal distribution histogram | Yes | Heatmap | No |
| Weak client detection | Yes | Visual only | Yes |
| Coverage gap identification | Yes | Yes (heatmap) | Yes (heatmap) |
| Signal vs retry correlation | Yes | No | No |
| | | | |
| **CLIENT CAPABILITY ANALYSIS** | | | |
| Wi-Fi generation per client (4/5/6) | Yes | No | Limited |
| Band support detection (2.4/5/6 GHz) | Yes | No | Limited |
| Legacy client identification | Yes | No | No |
| Capability mismatch detection | Yes | No | No |
| Client population breakdown | Yes | No | No |
| | | | |
| **ROAMING ANALYSIS** | | | |
| Roaming timeline per client | Yes | No | Limited |
| Roam duration measurement | Yes | No | No |
| Sticky client detection | Yes | No | No |
| Ping-pong (excessive roaming) detection | Yes | No | No |
| 802.11r Fast Transition detection | Yes | No | Limited |
| | | | |
| **AIRTIME ANALYSIS** | | | |
| Per-client airtime estimation | Yes | No | Limited |
| Data rate distribution | Yes | No | Partial |
| Management frame overhead calculation | Yes | No | No |
| Beacon overhead percentage | Yes | No | No |
| Probe request storm detection | Yes | No | No |
| Low data rate flagging (<24 Mbps) | Yes | No | Partial |
| | | | |
| **CHANNEL ANALYSIS** | | | |
| Channel congestion map | Yes | Yes | Yes |
| Adjacent channel interference detection | Yes | Yes | Yes |
| 40 MHz in 2.4 GHz detection | Yes | Yes | Yes |
| Channel utilisation (BSS Load) | Yes | Yes | Yes |
| Optimal channel recommendation | Yes | Yes (AI-driven) | Yes |
| | | | |
| **DHCP & DNS ANALYSIS** | | | |
| DHCP transaction timing | Yes | No | No |
| DHCP failure detection | Yes | No | No |
| DNS response time measurement | Yes | No | No |
| DNS timeout detection | Yes | No | No |
| DNS server performance comparison | Yes | No | No |
| | | | |
| **SECURITY ANALYSIS** | | | |
| Deauthentication attack detection | Yes | No | Yes |
| Disassociation storm detection | Yes | No | Yes |
| Authentication flood detection | Yes | No | Yes |
| Beacon anomaly / AP spoofing detection | Yes | No | Yes |
| Rogue AP indicators | Yes | No | Yes |
| ARP spoofing detection | Yes | No | No |
| Multiple DHCP server detection | Yes | No | No |
| Probe response spoofing detection | Yes | No | Limited |
| Client probe privacy analysis | Yes | No | No |
| Protocol leakage (CDP/LLDP/STP/mDNS) | Yes | No | No |
| Non-randomised MAC detection | Yes | No | No |
| Username exposure in EAP | Yes | No | Limited |
| | | | |
| **SITE SURVEY & PLANNING** | | | |
| Predictive AP placement | No | Yes (AI) | Yes |
| Floor plan heatmap generation | Yes (click-to-walk) | Yes | Yes |
| Wall/material attenuation modeling | No | Yes | Yes |
| 3D multi-floor modeling | No | Yes | Yes |
| Capacity planning | Yes (airtime budget) | Yes | Partial |
| AP vendor model library | Yes (55+ models, 12 vendors) | Yes (largest) | Yes |
| | | | |
| **SPECTRUM ANALYSIS** | | | |
| Non-Wi-Fi interference detection | No | Yes (Sidekick) | Yes (Spectrum XT) |
| Interference source classification | No | Yes | Yes |
| Spectrum waterfall display | No | Yes | Yes |
| | | | |
| **REPORTING** | | | |
| Health score (A-F grade) | Yes | No | No |
| Self-contained HTML report | Yes | PDF | PDF |
| Executive summary | Yes | Yes | Yes |
| Problem list with severity | Yes | Partial | Yes |
| Recommendations list | Yes | Yes | Yes |
| Exportable / printable | Yes | Yes | Yes |
| | | | |
| **PLATFORM & ACCESSIBILITY** | | | |
| Web-based (any browser) | Yes | No | No |
| Mobile accessible | Yes | App only | No |
| macOS support | Yes (browser) | Yes | No |
| Linux support | Yes (native + browser) | No | No |
| iOS / Android access | Yes (browser) | iOS app | No |
| Headless / remote operation | Yes | No | No |
| Works over SSH / VPN | Yes | No | No |
| Multiple simultaneous users | Yes | No | No |
| | | | |
| **FILE MANAGEMENT** | | | |
| On-device pcap storage | Yes | N/A | Local |
| File browser with grouping | Yes | N/A | No |
| Disk space monitoring | Yes | N/A | No |
| Remote file download | Yes | N/A | No |

---

## 3. Hardware Comparison

| Attribute | Wi-Fi Analyser (Pi) | Ekahau Sidekick 2 | AirMagnet Adapters |
|---|---|---|---|
| **Form factor** | Credit-card sized Pi + USB adapter | USB-C dongle | USB adapter + laptop |
| **Weight** | ~50g total | ~120g | Adapter ~30g + laptop |
| **Power source** | USB power bank or mains | Bus-powered (USB-C) | Laptop battery |
| **Portability** | Pocket-sized, fully standalone | Requires laptop | Requires Windows laptop |
| **Monitor mode** | Yes (native, all 3 bands) | No (passive survey only) | Limited |
| **Packet capture** | Yes (full raw frames) | No | Yes |
| **Band coverage** | Tri-band: 2.4 + 5 + 6 GHz | Dual-radio: 2.4 + 5 GHz (Sidekick 2 adds 6 GHz) | Per adapter (typically dual-band) |
| **Simultaneous bands** | Per adapter (multi-adapter supported) | Dual-radio (2.4 + 5 GHz) | Per adapter |
| **Wi-Fi generation support** | Wi-Fi 6E / Wi-Fi 7 capable | Wi-Fi 6E | Wi-Fi 6 (catching up) |
| **Spectrum analysis** | No | Built-in | Separate Spectrum XT dongle |
| **Standalone operation** | Yes (headless, battery-powered) | No (needs laptop + software) | No (needs laptop + software) |
| **Cost** | ~$60 total | ~$3,000-$4,000 | ~$50-$200 per adapter |
| **Replacement cost** | ~$60 | ~$3,000+ | ~$50-$200 |
| **Display required** | No (any phone/tablet/laptop via browser) | Yes (laptop) | Yes (Windows laptop) |

---

## 4. Pricing Comparison

| Cost Element | Wi-Fi Analyser (Pi) | Ekahau | AirMagnet |
|---|---|---|---|
| **Hardware (one-time)** | ~$60 | $3,000 - $4,000 | $3,000 - $5,000 (Spectrum XT) |
| **Software license** | Free (open source) | $2,500 - $3,500/year | $10,000 - $15,000 (perpetual) |
| **Annual maintenance** | $0 | Included in subscription | $1,500 - $3,000/year |
| **Year 1 total** | ~$60 | $5,000 - $7,500 | $13,000 - $20,000 |
| **Year 2 total** | $0 | $2,500 - $3,500 | $1,500 - $3,000 |
| **3-year TCO** | ~$60 | $10,000 - $14,500 | $16,000 - $26,000 |
| **Price per additional unit** | ~$60 | $2,500 - $3,500/year | $10,000 - $15,000 |

The cost difference is approximately **100x to 500x** in favour of the Pi-based analyser.

---

## 5. What Each Product Does Best

### Wi-Fi Analyser (Pi) Excels At:

1. **Real packet-level troubleshooting** -- analyses actual captured frames, not just RF measurements. Every finding is backed by protocol evidence.

2. **Security auditing** -- 25+ automated security checks including deauth attacks, rogue AP indicators, certificate problems, protocol leakage, EAPOL analysis, and ARP spoofing. Neither Ekahau nor AirMagnet Survey offer this depth from a single device.

3. **Client behaviour analysis** -- retry rates, signal quality, Wi-Fi generation, roaming patterns, airtime consumption, and sticky client detection. Provides per-client diagnostics that survey tools cannot offer.

4. **Network layer diagnostics** -- DHCP transaction timing and DNS response time analysis. When users blame "the Wi-Fi" for slow DHCP or DNS, this tool proves (or disproves) it.

5. **Portability and stealth** -- a pocket-sized device that operates headless, controlled from a phone. Can be placed in ceiling tiles, carried during walkthroughs, or left running for extended captures. No laptop required.

6. **Accessibility** -- works from any browser on any OS. Multiple technicians can view results simultaneously. No software installation required on the viewing device.

7. **Cost of deployment at scale** -- deploy 10 capture points across a building for less than the cost of one Ekahau Sidekick. Ideal for distributed monitoring during migration projects or incident investigations.

### Ekahau AI Pro Excels At:

1. **Predictive network design** -- AI-driven AP auto-placement with the industry's largest AP model library. The gold standard for greenfield deployments.

2. **Heatmap surveys** -- walk-through surveys with beautiful signal/SNR/throughput heatmaps overlaid on floor plans. Visually communicates coverage to stakeholders.

3. **Capacity planning** -- model user density, device types, and application requirements to determine AP count and placement.

4. **3D multi-floor modeling** -- inter-floor interference and coverage analysis.

5. **Integrated spectrum analysis** -- the Sidekick 2 combines Wi-Fi measurement and spectrum analysis in one device, detecting non-Wi-Fi interference sources (microwaves, Bluetooth, etc.).

### AirMagnet Excels At:

1. **Real-time troubleshooting** -- WiFi Analyzer PRO provides 150+ automated diagnostic checks with live monitoring dashboards. The most comprehensive real-time Wi-Fi diagnostics tool available.

2. **Compliance reporting** -- built-in PCI DSS and HIPAA Wi-Fi compliance validation reports.

3. **Spectrum analysis with device classification** -- Spectrum XT identifies and classifies specific interference sources by type.

4. **Voice/video quality assessment** -- Survey PRO includes MOS score prediction for voice-over-Wi-Fi readiness.

---

## 6. What Each Product Cannot Do

### Wi-Fi Analyser (Pi) Cannot:

- Perform predictive AP placement with AI-driven optimisation
- Detect non-Wi-Fi interference (no spectrum analyser hardware)
- Model wall attenuation or building materials
- Replace a full site survey tool for greenfield deployments

### Ekahau Cannot:

- Capture or decode 802.11 frames (no packet analysis at all)
- Detect security attacks (deauth, rogue AP, spoofing)
- Analyse EAPOL handshakes or EAP authentication
- Measure retry rates, airtime, or per-client performance from real traffic
- Inspect certificates, DHCP timing, or DNS performance
- Operate without a laptop
- Analyse uploaded pcap files

### AirMagnet Cannot:

- Run on macOS or Linux (Windows only)
- Operate from a mobile phone or tablet
- Run headless or be remotely deployed
- Detect ARP spoofing, DHCP anomalies, or DNS issues
- Analyse client Wi-Fi generation or capability mismatches
- Detect protocol leakage (CDP, LLDP, STP, mDNS over wireless)
- Provide a health score or graded assessment
- Scale affordably (each deployment requires expensive licenses)

---

## 7. Target Market Differentiation

| Market Segment | Wi-Fi Analyser (Pi) | Ekahau | AirMagnet |
|---|---|---|---|
| **Independent consultants** | Strong (low cost, portable, professional reports) | Strong (industry standard for surveys) | Moderate (expensive for solo practice) |
| **MSPs / MSSPs** | Strong (deploy at multiple sites cheaply) | Moderate (subscription per seat) | Weak (very expensive per technician) |
| **Enterprise IT (operations)** | Strong (troubleshooting, security) | Weak (no troubleshooting) | Strong (built for NOC/SOC) |
| **Enterprise IT (planning)** | Weak (no heatmaps) | Strong (best in class) | Moderate |
| **Education / training** | Strong (affordable, hands-on learning) | Weak (too expensive for labs) | Weak (too expensive, Windows only) |
| **Small business** | Strong (self-service diagnostics) | Overkill / too expensive | Overkill / too expensive |
| **Security auditing** | Strong (deep security checks) | Not applicable | Strong |
| **Incident response** | Strong (rapid deployment, stealth) | Not applicable | Moderate |

---

## 8. Unique Differentiators of the Pi-Based Analyser

These are capabilities that **neither** Ekahau **nor** AirMagnet offer:

1. **Health Score with Letter Grade (A-F)** -- a single, immediately understandable metric that non-technical stakeholders can act on. No other tool produces this.

2. **Browser-based, zero-install operation** -- controlled from any phone, tablet, or laptop. No software to install, no OS requirements, no licensing on the viewing device.

3. **Headless, pocket-sized deployment** -- can be hidden in a ceiling tile or taped to a wall for extended covert captures. Powered by a USB battery pack. No other professional tool offers this form factor.

4. **DHCP and DNS timing analysis** -- proves or disproves whether "slow Wi-Fi" complaints are actually network layer issues. Neither competitor analyses DHCP transaction times or DNS latency.

5. **Client capability census** -- automatically categorises every client by Wi-Fi generation and band support, identifying legacy devices dragging down the network. Shows exact population breakdown (% Wi-Fi 6 vs 5 vs 4 vs legacy).

6. **Protocol leakage detection** -- flags CDP, LLDP, STP, and mDNS frames on the wireless network, revealing infrastructure information that should not be visible over the air.

7. **Per-client airtime analysis** -- estimates airtime consumption per client, identifying "airtime hogs" that consume disproportionate resources. Includes probe storm detection.

8. **Roaming quality metrics** -- measures actual roam duration in milliseconds, detects sticky clients and ping-pong roaming, counts 802.11r fast transitions. This level of roaming analysis from real traffic is unique.

9. **Cost of scale** -- deploy 20 units across a campus for under $1,000. The same deployment with Ekahau or AirMagnet would cost $100,000+.

10. **Combined capture + analysis** -- one device captures the traffic AND analyses it. Ekahau cannot capture at all. AirMagnet requires a full laptop.

---

## 9. Positioning Statement

**For enterprise tools:** "Use Ekahau to design your network. Use our analyser to prove it works."

**For consultants:** "Carry a $40 device that produces the same quality diagnostic report as a $15,000 toolkit."

**For MSPs:** "Deploy one at every customer site. The entire fleet costs less than one AirMagnet license."

**For security teams:** "25+ automated security checks from a device that fits in your pocket."

---

## 10. Conclusion

The Wi-Fi Analyser on Raspberry Pi Zero 2 is not a replacement for Ekahau or AirMagnet -- it operates in a different category. Ekahau is a design and survey tool. AirMagnet is a real-time monitoring and compliance tool. The Pi-based analyser is a **packet-level diagnostic and security auditing tool** that is:

- **100x cheaper** than either competitor
- **More portable** than any professional Wi-Fi tool on the market
- **More accessible** (browser-based, any device, any OS)
- **Deeper in packet analysis** than Ekahau (which has none)
- **Broader in diagnostics** than AirMagnet (DHCP/DNS, client capabilities, airtime, roaming quality)
- **Unique in security coverage** (protocol leakage, ARP spoofing, certificate analysis, client privacy)

The three products are complementary. An ideal wireless professional toolkit would include Ekahau for design, the Pi analyser for diagnostics and security, and AirMagnet only if compliance reporting is a regulatory requirement.

The strongest commercial opportunity is positioning the Pi analyser as the **affordable diagnostic companion** that fills the gaps left by the expensive enterprise tools -- particularly for the growing market of independent consultants, MSPs, and organisations that need troubleshooting without a $15,000 investment.

---

*Document generated: 2026-04-02*
*Product: Wi-Fi Analyser on Raspberry Pi Zero 2 W*
