# Passive Wi-Fi Intrusion Detection Sensor — Business Feasibility Analysis

## The Idea

A low-cost, passive Wi-Fi monitoring device that sits on a corporate network 24/7, listens to all wireless traffic, detects attacks and security issues in real time, and reports to IT via dashboard/alerts. Sold as a product (hardware + SaaS subscription) to organisations that need continuous wireless security monitoring.

---

## Why This Market Exists

### The Problem
- Enterprise WIDS (Cisco, Aruba) costs **$100-$300/AP/year** and only works with that vendor's APs
- Dedicated overlay WIDS (AirMagnet Enterprise) costs **$2,000-$4,000 per sensor** plus $5,000-$15,000 server license
- PCI DSS, HIPAA, NIST, and SOX **require** wireless monitoring — companies MUST do this
- Most small/medium businesses do only **quarterly manual scans** (minimum PCI compliance) because continuous monitoring is too expensive
- There is no affordable, vendor-agnostic, plug-and-play solution

### The Opportunity
- Global WIDS/WIPS market: **$800M-$1.2B** (2024), growing 8-12% annually
- PCI DSS v4.0 (mandatory March 2025) strengthens wireless monitoring requirements
- Every retailer, restaurant, hotel, hospital, and bank processing card payments needs this

---

## What the Sensor Detects

### Real-Time Attack Detection (Passive, No Transmission)

| Attack | How Detected | Severity |
|---|---|---|
| **Deauthentication flood** | Anomalous volume of deauth frames from a source | Critical |
| **Evil twin / Rogue AP** | Same SSID with different BSSID, security, or vendor OUI | Critical |
| **KARMA attack** | AP responding to ANY probe request SSID | Critical |
| **Beacon flood** | Sudden appearance of hundreds of fake BSSIDs | Critical |
| **WPA handshake harvesting** | Deauth + immediate EAPOL exchange pattern | High |
| **Authentication flood** | Mass auth frames from spoofed MACs (DoS) | High |
| **Rogue AP on network** | Unauthorised BSSID appearing on the wire | High |
| **Unauthorised client** | Unknown MAC associating with corporate APs | Medium |
| **Ad-hoc network** | IBSS capability bit in beacon | Medium |
| **Probe request tracking** | Devices broadcasting saved network lists | Low |
| **Channel interference** | Sustained noise floor elevation or beacon loss | Medium |
| **Client isolation bypass** | Direct STA-to-STA data frames | Medium |

### Continuous Security Posture Monitoring

| Check | What It Reports |
|---|---|
| **WPA2 without PMF** | APs vulnerable to deauth attacks |
| **WPS enabled** | APs vulnerable to brute-force |
| **Legacy encryption** | WEP/TKIP still in use |
| **No WPA3** | APs not using latest security standard |
| **Open networks** | Unencrypted traffic exposure |
| **Vendor vulnerabilities** | Known CVEs for detected AP models |
| **Certificate issues** | Expired/weak 802.1X certificates |
| **SSID count** | Too many SSIDs (beacon overhead) |
| **Legacy bit rates** | 1/2/5.5/11 Mbps slowing the network |

---

## Hardware Design

### Per-Sensor Bill of Materials

| Component | Product | Cost |
|---|---|---|
| SBC | Raspberry Pi 4 (4GB) | $55 |
| PoE HAT | Official Pi PoE+ HAT | $20 |
| 2.4 GHz adapter | Alfa AWUS036NHA (AR9271) | $30 |
| 5 GHz adapter | Alfa AWUS036ACM (MT7612U) | $40 |
| MicroSD | 128GB endurance card | $20 |
| Enclosure | ABS project box + mounting | $20 |
| Cables + misc | Ethernet pigtail, USB cables | $10 |
| **Total BOM** | | **~$195** |
| **At volume (100+ units)** | | **~$130-$160** |

### Deployment

- **Power:** PoE from existing network switch (802.3at) — one Ethernet cable for power + data
- **Mounting:** Ceiling tile, above drop ceiling, or wall mount
- **Connectivity:** Gigabit Ethernet backhaul to corporate network
- **Coverage:** 1 sensor per 5,000-10,000 sq ft (same as a Wi-Fi AP)
- **Multi-band:** 2 adapters covering 2.4 GHz + 5 GHz simultaneously
- **Management:** Central cloud dashboard via secure HTTPS tunnel

### Upgraded Version (Premium Tier)

| Component | Product | Cost |
|---|---|---|
| SBC | Raspberry Pi 5 (8GB) | $80 |
| PoE | Industrial PoE carrier board | $50 |
| 2.4 GHz adapter | Alfa AWUS036NHA | $30 |
| 5 GHz adapter | Alfa AWUS036ACM | $40 |
| 6 GHz adapter | Alfa AWUS036AXML (MT7921AU) | $55 |
| Storage | 256GB USB SSD | $25 |
| Enclosure | Custom injection-moulded | $15 |
| GPS (optional) | VK-162 USB GPS | $15 |
| **Total BOM** | | **~$310** |

---

## Software Architecture

### Sensor Software (Runs on Pi)

```
Sensor (Raspberry Pi)
  |
  +-- Packet Capture Engine
  |     |-- dumpcap on each adapter (continuous monitor mode)
  |     |-- Channel hopping per-band
  |     |-- Ring buffer: keep last 30 min of pcap (forensic)
  |
  +-- Real-Time Analysis Engine
  |     |-- Frame parser (management/control/data)
  |     |-- Threat detection rules (deauth, rogue AP, etc.)
  |     |-- AP baseline comparison
  |     |-- Vendor vulnerability matching
  |
  +-- Alert Manager
  |     |-- Local alert queue
  |     |-- Severity classification (Critical/High/Medium/Low)
  |     |-- Deduplication (don't alert same attack every second)
  |
  +-- Uplink to Cloud
        |-- HTTPS/MQTT to cloud dashboard
        |-- Heartbeat every 60 sec
        |-- Alert push (immediate)
        |-- Network inventory sync (every 5 min)
        |-- Forensic pcap upload (on-demand)
```

### Cloud Platform (SaaS)

```
Cloud Dashboard
  |
  +-- Multi-Site Map View (all sensor locations)
  +-- Real-Time Alert Feed
  +-- Network Inventory (all APs, clients, security posture)
  +-- Compliance Reports (PCI DSS, HIPAA)
  +-- Historical Analytics
  +-- Sensor Management (firmware updates, config)
  +-- User/Role Management
  +-- API for SIEM Integration (Splunk, ELK, QRadar)
```

### Alerting Channels

| Channel | Implementation |
|---|---|
| Dashboard (web) | Real-time via WebSocket |
| Email | SMTP relay |
| Slack/Teams | Webhook |
| SMS | Twilio or similar |
| PagerDuty/OpsGenie | REST API |
| SNMP traps | For legacy NMS (Nagios, Zabbix) |
| Syslog | For SIEM integration |

---

## Pricing Model

### Option A: Hardware + SaaS Subscription

| Tier | Hardware | Monthly SaaS | Includes |
|---|---|---|---|
| **Basic** (1 sensor) | $299 one-time | $29/month | Real-time alerts, dashboard, 30-day history |
| **Pro** (1 sensor) | $449 one-time | $49/month | + Compliance reports, API, forensic capture |
| **Enterprise** (per sensor) | $399 one-time | $39/month | + Multi-site, SIEM integration, SLA |
| **MSSP** (per sensor) | $199 one-time | $19/month | White-label, bulk pricing, reseller margin |

### Option B: Managed Service (Sensor-as-a-Service)

| Plan | Monthly | Includes |
|---|---|---|
| **Per Location** | $79-$149/month | Sensor hardware (loaned), monitoring, alerts, compliance reports |
| **Multi-Site** (10+) | $59-$99/location/month | Volume discount, dedicated account manager |

### Revenue Projections

| Scenario | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| **Conservative** (100 sensors) | $120K | $200K | $300K |
| **Moderate** (500 sensors) | $450K | $800K | $1.2M |
| **Aggressive** (2,000 sensors) | $1.5M | $3M | $5M |

### Comparison to Competitors

| Solution | Cost per sensor/year | Vendor lock-in |
|---|---|---|
| **This product (Basic)** | **$648** ($299 + $29x12) | No |
| Cisco DNA wIPS | $150-$300/AP/year | Cisco only |
| Aruba RFProtect | $120-$180/AP/year | Aruba only |
| AirMagnet Enterprise | $2,000-$4,000/sensor + $5K server | No |
| Bastille Networks | $50K-$200K/facility | No |

**Key advantage:** $648 total year-1 cost (including hardware) vs $2,000-$4,000 for the cheapest vendor-agnostic competitor. **70-85% cheaper.**

---

## Target Markets (Priority Order)

### 1. Retail / Hospitality (Highest Volume)

- **Driver:** PCI DSS v4.0 mandatory wireless monitoring
- **Size:** Millions of retail locations worldwide process card payments
- **Pain point:** Current solutions too expensive for per-location deployment
- **Pitch:** "PCI wireless compliance for $79/month per store"
- **Entry:** Partner with payment processors or PCI QSAs (Qualified Security Assessors)

### 2. Healthcare

- **Driver:** HIPAA, IoMT (Internet of Medical Things) security
- **Size:** 6,000+ hospitals in the US alone, plus clinics and care facilities
- **Pain point:** Medical devices (infusion pumps, monitors) often on Wi-Fi with poor security
- **Pitch:** "Continuous monitoring of medical device wireless security"
- **Entry:** Partner with healthcare IT VARs or medical device security companies

### 3. Financial Services

- **Driver:** PCI DSS, GLBA, SOX
- **Size:** Community banks, credit unions, regional brokerages (underserved by enterprise WIDS)
- **Pain point:** Can't justify $100K+ for Cisco/Aruba WIDS overlay
- **Pitch:** "Bank-grade wireless security monitoring at 1/10th the cost"

### 4. Managed Security Service Providers (MSSPs)

- **Driver:** Resell monitoring-as-a-service
- **Size:** Thousands of MSSPs serving millions of SMBs
- **Pain point:** No affordable wireless monitoring to add to their service portfolio
- **Pitch:** "Add wireless IDS to your MSSP offering. $19/sensor/month wholesale."
- **Entry:** This is a force multiplier — one MSSP partnership = hundreds of sensor deployments

### 5. Education

- **Driver:** FERPA, large open campus networks, tight budgets
- **Size:** 4,000+ colleges/universities in the US
- **Pitch:** "Protect your campus Wi-Fi for the cost of a textbook per building"

### 6. Government / Defence

- **Driver:** NIST 800-171, CMMC, FedRAMP
- **Entry:** Requires FedRAMP authorization for cloud components. Long sales cycle.
- **Pitch:** "NIST-compliant wireless monitoring for federal contractors"

---

## Competitive Advantages

### vs Enterprise WIDS (Cisco, Aruba, Fortinet)

| Factor | Enterprise WIDS | This Product |
|---|---|---|
| Works with any AP vendor | No (vendor-locked) | **Yes** |
| Requires existing infrastructure | Yes ($100K+ AP deployment) | **No** (standalone) |
| Cost | $100-$300/AP/year | **$29-$49/sensor/month** |
| Deployment time | Weeks (integration) | **Minutes (plug in Ethernet)** |
| Cloud dashboard | Vendor-specific | **Vendor-agnostic** |

### vs Dedicated WIDS (AirMagnet, AirDefense)

| Factor | Dedicated WIDS | This Product |
|---|---|---|
| Sensor cost | $2,000-$4,000 | **$299-$449** |
| Server cost | $5,000-$15,000 | **Included (cloud)** |
| Maintenance | 15-20%/year | **Included in subscription** |
| Multi-site management | Extra cost | **Included** |
| Compliance reports | Manual | **Automated** |

### vs Open Source (Kismet, Nzyme)

| Factor | Open Source | This Product |
|---|---|---|
| Cost | Free | $29-$49/month |
| Setup effort | Hours-days of Linux expertise | **Plug and play** |
| Management dashboard | DIY | **Included** |
| Alerting | DIY | **Built-in (email, Slack, SIEM)** |
| Compliance reports | None | **PCI DSS, HIPAA templates** |
| Support | Community forums | **Commercial SLA** |
| Firmware updates | Manual | **Automatic OTA** |

---

## Compliance Reporting

### PCI DSS v4.0 Coverage

| PCI DSS Requirement | How Sensor Addresses It |
|---|---|
| 11.2.1 — Authorised/unauthorised wireless AP management | Continuous rogue AP detection with authorised AP whitelist |
| 11.2.2 — Identify and investigate detected wireless APs | Automated identification with BSSID, SSID, vendor, location |
| 1.2.3 — Wireless APs inventory | Automatic inventory of all detected APs with security posture |
| 12.10.5 — Monitor and respond to alerts from IDS/IPS | Real-time alerting with severity classification |
| 11.5.1 — Change detection on wireless configurations | Baseline comparison detects security parameter changes |

### HIPAA Coverage

| HIPAA Safeguard | Sensor Capability |
|---|---|
| §164.312(e) — Transmission security | Detects unencrypted wireless networks, WEP, weak encryption |
| §164.312(b) — Audit controls | Continuous audit log of wireless activity |
| §164.308(a)(1) — Security management | Risk analysis input: wireless threat and vulnerability data |

---

## Legal Considerations

### Is Passive Monitoring Legal?

**Yes, with proper authorisation.**

- **US:** The Wiretap Act / ECPA allows network operators to monitor their own networks for security purposes (provider exception, 18 U.S.C. § 2511(2)(a)(i)). 802.11 management frames (beacons, probes, deauth) are NOT considered "contents" of communications.
- **EU:** ePrivacy Directive permits security monitoring of own infrastructure.
- **FCC:** Receiving any radio signal is legal (47 U.S.C. § 605). Monitor mode is receive-only.
- **Industry precedent:** Every enterprise WIDS vendor (Cisco, Aruba, AirMagnet) operates on this legal basis.

### Privacy Requirements

| Concern | Mitigation |
|---|---|
| MAC addresses are personal data (GDPR) | Hash/anonymise after threat analysis. Retention policy: 72 hours for probe data |
| Probe requests reveal device history | Don't store SSID lists beyond real-time analysis |
| Employee monitoring concerns | Privacy notice informing occupants of wireless security monitoring |
| GDPR DPIA requirement | Conduct Data Protection Impact Assessment before deployment in EU |
| Data retention | Alerts: 1-3 years. Metadata: 90 days. Full pcap: 7-30 days or on-incident only |

### Required for Deployment

1. Written authorisation from network owner
2. Privacy notice (signage or policy document)
3. Data retention schedule
4. DPIA for EU/UK deployments
5. Data processing agreement if cloud platform stores personal data

---

## Implementation Roadmap

### Phase 1: MVP (3-6 months)
- Single-sensor product
- Core detections: rogue AP, deauth flood, evil twin, WPS, no PMF
- Web dashboard (self-hosted or simple cloud)
- Email + Slack alerting
- **Target:** Beta with 10-20 pilot customers

### Phase 2: Multi-Site Platform (6-12 months)
- Cloud dashboard with multi-site map view
- Compliance report generation (PCI DSS, HIPAA)
- SIEM integration (syslog, Splunk, ELK)
- OTA firmware updates for sensors
- **Target:** 100+ paying customers

### Phase 3: Scale (12-24 months)
- MSSP white-label programme
- API for third-party integration
- Machine learning anomaly detection
- RF fingerprinting for AP authentication
- Triangulation with multiple sensors
- **Target:** 1,000+ sensors deployed

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Enterprise vendors add affordable WIDS to their APs | Medium | High | Move fast. Vendor-agnostic is the differentiator |
| Pi supply chain issues | Low (post-2024) | Medium | Support alternative SBCs (Orange Pi, Rock Pi) |
| Customer churn | Medium | Medium | Annual contracts. Compliance requirement = sticky |
| False positive alerts | High initially | Medium | Tuning, baseline learning, severity filtering |
| Legal challenge on monitoring | Very low | High | Operate within established legal frameworks |
| Competitor copies approach | Medium | Medium | First-mover advantage. Platform/dashboard is the moat |

---

## Summary

**Is this feasible?** Yes. The technology already exists (we built most of it). The market demand is proven and growing. The price point ($200 hardware + $30/month) is 5-10x cheaper than any competing solution.

**What's needed:**
- Engineering: 3-6 months for MVP (sensor software + cloud dashboard)
- Hardware: ~$200/sensor BOM, $130-$160 at volume
- Cloud: Standard web platform (Django/Flask + PostgreSQL + WebSocket)
- Sales: PCI QSAs and MSSPs as channel partners

**The moat:** Not the sensor hardware (anyone can buy a Pi). It's the detection intelligence, the compliance reporting, the multi-site management platform, and the ease of deployment. A corporate IT person plugs in one Ethernet cable and gets a wireless security dashboard in 5 minutes.

**First target:** Retail chains needing PCI DSS wireless compliance. Thousands of locations, $79/month each. One 500-location chain = $474K ARR.

---

*Document generated: 2026-04-03*
