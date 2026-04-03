# Hardware Upgrade Path: Closing the Gap with Ekahau & AirMagnet

## Current Setup

- Raspberry Pi Zero 2 W (quad-core A53 @ 1 GHz, 512 MB RAM, 1x micro-USB OTG)
- Comfast tri-band Wi-Fi 6E/7 adapter (2.4 + 5 + 6 GHz, MediaTek MT7921AU)
- Total cost: ~$60

## What's Missing vs Ekahau & AirMagnet

| Missing Capability | Needed Hardware | Needed Software |
|---|---|---|
| Spectrum analysis (non-Wi-Fi interference) | RF analyzer or SDR | Sweep + waterfall display |
| Floor plan heatmap surveys | None (click-to-walk is industry standard) | Heatmap rendering in web UI |
| Faster pcap processing | More powerful SBC | Same software, runs faster |
| Simultaneous multi-band capture | Multiple USB adapters | Already supported in code |
| 2.4 GHz spectral scan (free) | Atheros AR9271 adapter | ath9k spectral scan driver |
| Outdoor GPS tagging | USB GPS module | gpsd integration |
| Better USB bandwidth | Pi with USB 3.0 ports | None |

---

## Upgrade Tiers

### Tier 1: Essential Upgrade (~$110 additional)

**Upgrade the Pi. This is the single biggest improvement.**

| Component | Product | Price | Why |
|---|---|---|---|
| SBC upgrade | **Raspberry Pi 5 (8GB)** | ~$80 | 2-3x faster pcap processing. 8 GB RAM handles large captures. 2x USB 3.0 ports eliminates bandwidth bottleneck. |
| Power supply | Pi 5 official 27W USB-C | ~$12 | Required for Pi 5 |
| MicroSD | 128 GB A2 class | ~$15 | Faster storage for captures |

**What this gets you:**
- Process pcap files 2-3x faster (Cortex-A76 @ 2.4 GHz vs Cortex-A53 @ 1 GHz)
- No more RAM-related packet drops on large captures
- USB 3.0 ports for the Wi-Fi adapter (no more USB hub needed)
- Can run multiple tshark passes simultaneously
- All existing software runs unchanged

---

### Tier 2: Multi-Band Simultaneous Capture (~$240 additional on top of Tier 1)

**Add dedicated adapters per band so you can capture 2.4 + 5 + 6 GHz at the same time.**

| Component | Product | Chipset | Driver | Price |
|---|---|---|---|---|
| 2.4 GHz adapter | **Alfa AWUS036NHA** | Atheros AR9271 | ath9k_htl (in-kernel) | ~$30 |
| 5 GHz adapter | **Alfa AWUS036ACH** | Realtek RTL8812AU | aircrack-ng/rtl8812au | ~$50 |
| 6 GHz adapter | Keep existing Comfast | MediaTek MT7921AU | mt76 (in-kernel) | $0 (already owned) |
| USB hub (if needed) | Powered 4-port USB 3.0 hub | - | - | ~$18 |

**What this gets you:**
- Capture all three bands simultaneously (no channel hopping across bands)
- The Alfa AWUS036NHA also gives you free **spectral scan** on 2.4 GHz via ath9k driver
- Each adapter on its own channel means zero gaps in capture
- Pi 5 has enough USB ports (2x USB 3.0 + 2x USB 2.0) for all three adapters without a hub

**Power budget:** Three adapters draw ~1.0-1.4A total. Pi 5 with 27W supply can handle this, but a powered hub adds margin.

**Note on USB 3.0 interference:** USB 3.0 ports emit RF noise in the 2.4 GHz range. Put the 2.4 GHz adapter (AWUS036NHA) on a USB 2.0 port, or use a short USB extension cable to create distance.

---

### Tier 3: Spectrum Analysis (~$300-$400 additional)

**This is the one feature that requires dedicated hardware. Two options:**

#### Option A: RF Explorer 6G Combo (~$400-$460)

| Attribute | Detail |
|---|---|
| Frequency range | 15 MHz - 6.1 GHz (covers 2.4 + 5 + 6 GHz) |
| Interface | USB serial (FTDI/CP2102) |
| Linux support | Yes, via /dev/ttyUSBx |
| Python library | `RFExplorer` on PyPI, fully functional |
| Form factor | Small handheld, USB-powered |
| Dynamic range | ~90 dB (professional grade) |
| Sweep width | ~112 MHz per sweep (must step through bands) |

**Pros:** Best dynamic range, established product, Python API, professional-grade measurements.
**Cons:** Narrow sweep width means stepping through frequencies. Most expensive option.

#### Option B: HackRF One (~$300-$350)

| Attribute | Detail |
|---|---|
| Frequency range | 1 MHz - 6 GHz (covers everything) |
| Interface | USB 2.0 |
| Linux support | Excellent (libhackrf, hackrf_sweep) |
| Sweep capability | `hackrf_sweep` covers 2.4-6 GHz in ~1 second |
| Form factor | Small board, USB-powered |
| Dynamic range | ~48 dB (8-bit ADC, less precise) |

**Pros:** Wideband sweep in one pass, cheaper, well-supported on Linux, `hackrf_sweep` does FFT on the FPGA so Pi CPU isn't stressed.
**Cons:** Lower dynamic range (48 dB vs 90 dB). Fine for detecting interference sources, not for precise power measurements.

#### Option C: Free Spectral Scan (2.4 GHz only, $0)

If you added the Alfa AWUS036NHA in Tier 2, you already have hardware spectral scan capability on 2.4 GHz:

- The **ath9k driver** exposes FFT data via `/sys/kernel/debug/ieee80211/phyX/ath9k/spectral_scan_ctl`
- Shows per-packet FFT data at 20/40 MHz channel width
- Can detect microwave ovens, Bluetooth, cordless phones, baby monitors
- Open-source tools: `ath_spectral`, OpenWrt spectral scan visualiser
- **Limitation:** 2.4 GHz only, per-channel (must hop)

**Recommendation:** Start with the free ath9k spectral scan (Tier 2 gives you the hardware). Add HackRF One later if full 5/6 GHz spectrum analysis is needed.

---

### Tier 4: Floor Plan Heatmap Surveys (~$0 hardware, software feature)

**This is NOT a hardware problem. It's a software feature.**

Both Ekahau and AirMagnet use the same approach:

1. User uploads a floor plan image
2. User sets scale (click two points, enter real-world distance)
3. User walks the site, tapping their position on the floor plan in the app
4. System records Wi-Fi measurements at each tapped position
5. Software interpolates between points and generates a heatmap

**No beacons, no UWB, no IMU, no GPS.** The industry standard is manual click-to-walk. This is purely a web UI feature to build.

Implementation approach for your tool:
- New "Survey" page in the web UI
- Upload floor plan image, set scale
- Tap to mark position while walking
- At each point, trigger a scan (or use live monitor data) and record signal strengths per BSSID
- Use the scan data + positions to generate an interpolated heatmap (HTML5 Canvas)
- Overlay on the floor plan image

**This would be the single most impactful feature to add.** It's the main reason people buy Ekahau ($5,000+), and you can implement it in software for $0 additional hardware.

---

### Tier 5: GPS for Outdoor Surveys (~$15)

| Component | Product | Price | Notes |
|---|---|---|---|
| USB GPS | **VK-162 G-Mouse** | ~$15 | u-blox 7, plug-and-play on Linux via gpsd, ~2.5m accuracy |

**Better option if budget allows:**

| Component | Product | Price | Notes |
|---|---|---|---|
| USB GPS | **u-blox NEO-M9N module** | ~$35 | Multi-GNSS (GPS+GLONASS+Galileo+BeiDou), ~1.5m accuracy |

**Integration:**
```
sudo apt install gpsd gpsd-clients
sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock
```
- Python reads position via `gpsd-py3` library
- Tag each scan/capture with lat/lon/altitude
- Display on map (Leaflet.js with OpenStreetMap tiles)
- Enables outdoor coverage mapping and wardriving-style surveys

---

## Summary: Complete Build Configurations

### Config 1: "Budget Pro" (~$170 total)

For consultants who need better performance but want to keep costs minimal.

| Component | Product | Price |
|---|---|---|
| SBC | Raspberry Pi 5 (8GB) | $80 |
| Wi-Fi adapter | Keep existing Comfast tri-band | $0 |
| Power | Pi 5 27W PSU | $12 |
| Storage | 128 GB A2 MicroSD | $15 |
| GPS | VK-162 G-Mouse | $15 |
| **Total** | | **~$122 + existing $60 = ~$182** |

Matches Ekahau/AirMagnet in: scanning, analysis, security, troubleshooting, reporting, outdoor GPS.
Still missing: heatmaps (software feature), spectrum analysis.

---

### Config 2: "Full Coverage" (~$400 total)

For serious professionals who want simultaneous multi-band capture.

| Component | Product | Price |
|---|---|---|
| SBC | Raspberry Pi 5 (8GB) | $80 |
| 2.4 GHz adapter | Alfa AWUS036NHA (+ spectral scan) | $30 |
| 5 GHz adapter | Alfa AWUS036ACH | $50 |
| 6 GHz adapter | Comfast (existing) | $0 |
| Power | Pi 5 27W PSU | $12 |
| Storage | 128 GB A2 MicroSD | $15 |
| GPS | VK-162 G-Mouse | $15 |
| **Total** | | **~$202 + existing $60 = ~$262** |

Matches Ekahau/AirMagnet in: everything in Config 1, plus simultaneous 3-band capture and basic 2.4 GHz spectral scan.
Still missing: full spectrum analysis (5/6 GHz), heatmaps (software).

---

### Config 3: "Enterprise Rival" (~$700 total)

The complete kit that matches or exceeds both Ekahau and AirMagnet combined.

| Component | Product | Price |
|---|---|---|
| SBC | Raspberry Pi 5 (8GB) | $80 |
| 2.4 GHz adapter | Alfa AWUS036NHA (+ spectral scan) | $30 |
| 5 GHz adapter | Alfa AWUS036ACH | $50 |
| 6 GHz adapter | Comfast (existing) | $0 |
| Spectrum analyzer | HackRF One | $320 |
| Power | Pi 5 27W PSU | $12 |
| Storage | 128 GB A2 MicroSD | $15 |
| GPS | u-blox NEO-M9N | $35 |
| Case | 3D printed / project box | $15 |
| **Total** | | **~$557 + existing $60 = ~$617** |

Plus heatmap survey feature (software, $0 hardware).

**This $617 kit replaces:**
- Ekahau AI Pro + Sidekick 2: $5,000-$7,500/year
- AirMagnet full suite: $13,000-$20,000
- **Combined: $18,000-$27,500**

**Your cost is 2-3% of the enterprise solution cost.**

---

## Priority Order for Implementation

| Priority | Feature | Hardware Needed | Software Effort | Impact |
|---|---|---|---|---|
| 1 | **Pi 5 upgrade** | Pi 5 (8GB) | None (drop-in replacement) | High - immediate performance boost |
| 2 | **Floor plan heatmap survey** | None | High (new web UI page) | Highest - this is why people buy Ekahau |
| 3 | **Multi-band simultaneous capture** | 2-3 Alfa adapters | Low (already supported) | Medium - completeness |
| 4 | **GPS outdoor mapping** | USB GPS dongle | Medium (gpsd + map UI) | Medium - outdoor surveys |
| 5 | **2.4 GHz spectral scan** | Alfa AWUS036NHA (from #3) | Medium (ath9k integration) | Medium - free with Alfa adapter |
| 6 | **Full spectrum analysis** | HackRF One or RF Explorer | High (new sweep + display UI) | Low-medium - nice to have |

The floor plan heatmap survey feature (Priority 2) requires **zero hardware investment** and would be the single most commercially impactful addition. It's the primary reason organisations pay $5,000+ for Ekahau.

---

*Document generated: 2026-04-02*
