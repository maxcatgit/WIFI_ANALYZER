# Alternative Hardware to Raspberry Pi 5

## Why Look Beyond Raspberry Pi?

The Pi shortage of 2021-2023 proved that depending on a single supplier is a risk. For a commercial product, we need:
- Multiple sourcing options
- Long-term availability guarantees
- Industrial-grade reliability
- Our software runs on standard Linux — it works on ANY ARM/x86 board

---

## Top Recommendations (Short List)

| Board | CPU | RAM | USB 3.0 | Ethernet | Price | Best For |
|---|---|---|---|---|---|---|
| **Radxa Rock 5B** | 8-core RK3588 @ 2.4GHz | 4-16GB | 2x | 2.5 GbE | $75-$130 | Best overall Pi 5 alternative |
| **Orange Pi 5 Plus** | 8-core RK3588 @ 2.4GHz | 4-32GB | 2x | 2x 2.5 GbE | $90-$150 | Best value, dual Ethernet |
| **ODROID-M2** | 8-core RK3588S @ 2.4GHz | 4-16GB | 2x | 2.5 GbE | $70-$120 | Most reliable supplier |
| **NanoPi R6S** | 8-core RK3588S @ 2.4GHz | 8GB | 2x | 2x 2.5G + 1x GbE | $80-$90 | Ready-made appliance |
| **LattePanda 3 Delta** | Intel N5105 x86 @ 2.9GHz | 8GB | 3x | Gigabit | $220-$260 | Zero driver issues (x86) |
| **Raspberry Pi 5** | 4-core BCM2712 @ 2.4GHz | 4-8GB | 2x | Gigabit | $60-$80 | Best community support |

---

## Detailed Comparison

### Radxa Rock 5B — Best Overall Alternative

```
CPU:      4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz (8 cores)
RAM:      4 / 8 / 16 GB LPDDR4X
USB:      2x USB 3.0, 2x USB 2.0
Ethernet: 2.5 GbE
Storage:  NVMe M.2, eMMC, microSD
GPIO:     40-pin (Pi-compatible layout)
PoE:      Official PoE HAT available
Price:    $75 (4GB), $100 (8GB), $130 (16GB)
```

**Pros:** Pi-compatible GPIO, PoE HAT, NVMe, 2.5GbE, strong Armbian support, Radxa contributes upstream kernel patches. Good international distribution.
**Cons:** Slightly more expensive than Orange Pi. Not as large a community as Raspberry Pi.
**Linux:** Armbian (excellent), Radxa Debian images. Kernel 6.1+ available.
**WiFi adapters:** All standard adapters work via Armbian.

### Orange Pi 5 Plus — Best Value

```
CPU:      4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz (8 cores)
RAM:      4 / 8 / 16 / 32 GB LPDDR4X
USB:      2x USB 3.0, 2x USB 2.0
Ethernet: 2x 2.5 GbE (dual!)
Storage:  NVMe M.2, eMMC, microSD
GPIO:     26-pin header
Price:    $90 (4GB), $110 (8GB), $150 (16GB)
```

**Pros:** Dual 2.5GbE (use one for management, one for sensor traffic). Up to 32GB RAM. NVMe. Cheapest 8-core board.
**Cons:** GPIO not Pi-compatible. No official PoE. China-centric distribution (AliExpress).
**Linux:** Armbian, vendor Ubuntu/Debian. Good community support.
**Best for:** Network appliance use where dual Ethernet is valuable.

### ODROID-M2 — Most Reliable Supply Chain

```
CPU:      4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz (8 cores)
RAM:      4 / 8 / 16 GB LPDDR5
USB:      2x USB 3.0, 1x USB 2.0
Ethernet: 2.5 GbE
Storage:  NVMe M.2, eMMC module, microSD
GPIO:     40-pin (Pi-compatible)
Price:    $70 (4GB), $90 (8GB), $120 (16GB)
```

**Pros:** Hardkernel (South Korea) has the best SBC supply chain track record in the industry. Never had the shortages Pi had. Active community forum. Long product lifecycle commitments.
**Cons:** Slightly smaller community than Radxa/Orange Pi.
**Linux:** Hardkernel Ubuntu, Armbian.
**Best for:** Commercial product where supply chain matters most.

### NanoPi R6S — Ready-Made Network Appliance

```
CPU:      4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz (8 cores)
RAM:      8 GB LPDDR4X (fixed)
USB:      2x USB 3.0, 1x USB-C
Ethernet: 2x 2.5 GbE + 1x Gigabit (3 ports!)
Storage:  32GB eMMC onboard, microSD
Case:     Metal enclosure included
Price:    $80-$90
```

**Pros:** Ships in a metal case ready for deployment. Triple Ethernet. 32GB eMMC built-in (no SD card needed). Compact form factor. FriendlyElec has reliable supply.
**Cons:** No GPIO header. Fixed 8GB RAM. Router-oriented form factor limits expansion.
**Linux:** FriendlyCore (Ubuntu), FriendlyWrt (OpenWrt). Armbian community support.
**Best for:** Commercial WIDS sensor — already looks like a product, not a hobbyist board.

### LattePanda 3 Delta — Zero Driver Issues

```
CPU:      Intel Celeron N5105, 4 cores @ 2.9GHz (x86!)
RAM:      8 GB LPDDR4X
USB:      3x USB 3.0, 1x USB-C
Ethernet: Gigabit
Storage:  64GB eMMC, M.2 NVMe
GPIO:     Arduino-compatible header
Price:    $220-$260
```

**Pros:** x86 architecture means EVERY Linux WiFi driver works. No ARM kernel/driver quirks. Run standard Ubuntu/Debian/Kali. Aircrack-ng suite works natively. Zero compatibility testing needed.
**Cons:** Higher power (15-25W vs 5-10W for ARM). More expensive. Larger form factor.
**Linux:** Standard x86 Ubuntu/Debian — same as any laptop. Perfect driver support.
**Best for:** If you're tired of fighting ARM driver issues, this eliminates them completely.

---

## Performance Comparison

All boards vs Raspberry Pi 5 for Wi-Fi analysis workloads:

| Board | CPU Score (relative) | tshark Speed | USB Bandwidth | Power Draw |
|---|---|---|---|---|
| **Pi 5** | 1.0x (baseline) | 1.0x | 5 Gbps (USB 3.0) | 5-7W |
| **Rock 5B** | 1.6-1.8x | ~1.7x | 5 Gbps | 6-10W |
| **Orange Pi 5 Plus** | 1.6-1.8x | ~1.7x | 5 Gbps | 6-12W |
| **ODROID-M2** | 1.6-1.8x | ~1.7x | 5 Gbps | 6-10W |
| **NanoPi R6S** | 1.6-1.8x | ~1.7x | 5 Gbps | 5-8W |
| **LattePanda 3 Delta** | 1.5-2.0x | ~1.8x | 5 Gbps | 15-25W |

The RK3588/RK3588S boards are all **faster than Pi 5** because they have 8 cores (4x A76 + 4x A55) vs Pi 5's 4 cores (4x A76). The extra 4 small cores help with background tasks while tshark processes on the big cores.

---

## Supply Chain Reliability Ranking

| Rank | Manufacturer | Track Record | Notes |
|---|---|---|---|
| 1 | **Hardkernel (ODROID)** | Excellent | South Korea. Never had major shortages. 10+ year history. |
| 2 | **Radxa** | Good | China + international distro (Allnet, OKdo). Growing presence. |
| 3 | **FriendlyElec (NanoPi)** | Good | China. Reliable stock. Ships worldwide. |
| 4 | **Raspberry Pi Foundation** | Recovered | UK. Shortage 2021-2023 was severe. Now normalised. |
| 5 | **Orange Pi (Xunlong)** | Adequate | China (AliExpress-centric). Stock usually available. |
| 6 | **LattePanda (DFRobot)** | Adequate | China. Niche x86 market. |
| 7 | **Banana Pi (Sinovoip)** | Poor | Inconsistent availability and documentation. |
| 8 | **Pine64** | Poor | Organisational issues, long shipping delays. |

---

## WiFi Adapter Compatibility Matrix

**This matters more than the SBC.** The same adapter works on ALL these boards if the kernel driver is available.

| SBC | Kernel | MT7921AU (WiFi 6) | RTL8812AU (WiFi 5) | AR9271 (WiFi 4) |
|---|---|---|---|---|
| Rock 5B (Armbian 6.1+) | 6.1+ | Works (mainline) | Works (out-of-tree) | Works (mainline) |
| Orange Pi 5 (Armbian 6.1+) | 6.1+ | Works | Works | Works |
| ODROID-M2 (Armbian 6.1+) | 6.1+ | Works | Works | Works |
| NanoPi R6S (FriendlyCore) | 5.10/6.1 | Works | Needs driver build | Works |
| LattePanda (Ubuntu x86) | Any | Works | Works | Works |
| Pi 5 (Raspberry Pi OS) | 6.1+ | Works | Works | Works |

**Key takeaway:** Use **Armbian with kernel 6.1+** on any RK3588 board and all standard WiFi adapters work. The board choice is about supply chain, form factor, and price — not WiFi compatibility.

---

## Industrial/Commercial Options

For a commercial WIDS product, consider:

| Option | Type | Price | Certifications | Use Case |
|---|---|---|---|---|
| **Radxa CM5** | Compute module (RK3588S) | ~$50-$80 | CE available | Design into custom carrier board |
| **NanoPi R6S** | Ready-made appliance | $85 | CE/FCC | Ship as-is in metal case |
| **ODROID-M2** | Dev board | $90 | CE | Prototype → production path |
| **Toradex Verdin iMX8M** | Industrial module | $100-$200 | CE/FCC/UL, industrial temp | 10+ year availability guarantee |
| **Kontron/Advantech** | Industrial PC | $200-$500 | Full industrial cert | Enterprise/government |

**For MVP/startup:** NanoPi R6S (ships in a case, looks professional) or ODROID-M2 (reliable supply, active community).
**For scale production:** Radxa CM5 compute module on custom carrier board (lowest BOM cost, your own design).
**For enterprise/government:** Toradex or similar industrial module (certifications, 10-year availability).

---

## Recommendation for WIDS Sensor Product

### Phase 1 (MVP, 1-100 units): Support Pi 5 + ODROID-M2

Both run Armbian, same kernel, same software. ODROID-M2 as the backup if Pi supply tightens. Test with both during development.

### Phase 2 (Scale, 100-1000 units): NanoPi R6S as primary

- Ships in a metal case (no enclosure design needed)
- Triple Ethernet (management + sensor + spare)
- 32GB eMMC (no SD card failures)
- $85/unit, reliable supply
- Looks like a product, not a hobbyist project

### Phase 3 (Volume, 1000+ units): Custom carrier board + Radxa CM5

- Lowest BOM cost (~$50-$60 for compute module)
- Custom carrier board with PoE, USB for adapters, LED indicators
- Your own branding, form factor, certifications
- Injection-moulded enclosure

### Always support x86 as option

Keep the software running on standard x86 Linux. Customers with existing Intel NUCs or mini PCs can self-deploy. No hardware sale needed — pure SaaS revenue.

---

## Boards to AVOID for Wi-Fi Analysis

| Board | Why |
|---|---|
| Any RISC-V (Milk-V, Star64) | WiFi driver ecosystem too immature |
| Khadas VIM4 (Amlogic) | Poor mainline kernel support, driver compilation issues |
| Orange Pi 3B (RK3566) | Too weak for tshark workloads |
| ODROID-M1S (RK3566) | Too weak |
| Libre Computer boards | Budget-focused, none match Pi 5 performance |
| Pine64 boards | Supply chain and organisational concerns |
| Banana Pi boards | Inconsistent documentation and support |

---

*Document generated: 2026-04-03*
