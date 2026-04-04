# AP Vendor Vulnerability Database
# Known CVEs and security issues by vendor, model, and firmware patterns
# Used to flag vulnerable APs detected during network scanning

AP_VULNERABILITIES = [
    # ===== UBIQUITI =====
    {
        'vendor_match': ['Ubiquiti', 'UniFi'],
        'model_match': [],
        'title': 'Ubiquiti UniFi default credentials',
        'severity': 'high',
        'cve': '',
        'description': 'UniFi APs ship with default SSH credentials (ubnt/ubnt). If not changed during adoption, attackers with network access can gain root shell.',
        'recommendation': 'Ensure all UniFi APs are adopted through the controller and default SSH passwords are changed.',
        'affected_versions': 'All versions with default credentials',
    },
    {
        'vendor_match': ['Ubiquiti', 'UniFi'],
        'model_match': ['UAP', 'U6', 'U7'],
        'title': 'CVE-2024-42028 — UniFi AP command injection',
        'severity': 'high',
        'cve': 'CVE-2024-42028',
        'description': 'Authenticated command injection in UniFi Network Application allows privilege escalation. Affects UniFi Network Application < 8.4.59.',
        'recommendation': 'Update UniFi Network Application to 8.4.59 or later.',
        'affected_versions': 'UniFi Network < 8.4.59',
    },

    # ===== TP-LINK =====
    {
        'vendor_match': ['TP-Link', 'TP-LINK'],
        'model_match': [],
        'title': 'TP-Link default admin panel exposed',
        'severity': 'medium',
        'cve': '',
        'description': 'TP-Link APs typically expose their web management interface on the default IP. Default credentials (admin/admin) are widely known.',
        'recommendation': 'Change default admin password. Restrict management interface access to VLAN or specific IPs.',
        'affected_versions': 'All consumer models',
    },
    {
        'vendor_match': ['TP-Link', 'TP-LINK'],
        'model_match': ['Archer', 'Deco', 'EAP'],
        'title': 'CVE-2024-5035 — TP-Link command injection',
        'severity': 'critical',
        'cve': 'CVE-2024-5035',
        'description': 'Unauthenticated command injection via the rftest binary exposed on TCP port 8888 on TP-Link Archer C5400X and other models.',
        'recommendation': 'Update firmware to latest version. Check if port 8888 is exposed.',
        'affected_versions': 'Archer C5400X < 1.1.7, various Archer models',
    },
    {
        'vendor_match': ['TP-Link', 'TP-LINK'],
        'model_match': [],
        'title': 'CVE-2023-1389 — TP-Link Archer AX21 RCE',
        'severity': 'critical',
        'cve': 'CVE-2023-1389',
        'description': 'Unauthenticated remote code execution via the web management interface locale API. Actively exploited by Mirai botnet.',
        'recommendation': 'Update firmware immediately. This vulnerability is actively exploited in the wild.',
        'affected_versions': 'Archer AX21 < 1.1.4 Build 20230219',
    },

    # ===== NETGEAR =====
    {
        'vendor_match': ['Netgear', 'NETGEAR'],
        'model_match': [],
        'title': 'Netgear default credentials and exposed management',
        'severity': 'medium',
        'cve': '',
        'description': 'Netgear routers/APs use well-known default credentials (admin/password). Management interface often exposed on all interfaces.',
        'recommendation': 'Change default password. Disable remote management.',
        'affected_versions': 'Most consumer models',
    },
    {
        'vendor_match': ['Netgear', 'NETGEAR'],
        'model_match': ['RAX', 'WAX', 'Orbi'],
        'title': 'CVE-2023-35722 — Netgear RAX RCE',
        'severity': 'critical',
        'cve': 'CVE-2023-35722',
        'description': 'Stack-based buffer overflow in Netgear RAX30 allows unauthenticated remote code execution via crafted HTTP requests.',
        'recommendation': 'Update to latest firmware.',
        'affected_versions': 'RAX30 < 1.0.11.96, multiple RAX models',
    },

    # ===== D-LINK =====
    {
        'vendor_match': ['D-Link', 'D-link', 'DLink'],
        'model_match': [],
        'title': 'D-Link end-of-life — no security patches',
        'severity': 'high',
        'cve': '',
        'description': 'Many D-Link consumer routers and APs are end-of-life with known unpatched vulnerabilities. D-Link has publicly stated they will not patch older models.',
        'recommendation': 'Replace end-of-life D-Link devices with actively supported hardware.',
        'affected_versions': 'DIR-8xx, DAP-xxxx series and older',
    },
    {
        'vendor_match': ['D-Link', 'D-link'],
        'model_match': ['DIR'],
        'title': 'CVE-2024-0769 — D-Link DIR backdoor',
        'severity': 'critical',
        'cve': 'CVE-2024-0769',
        'description': 'Multiple D-Link DIR series routers contain hardcoded backdoor credentials and unauthenticated RCE vulnerabilities. No patches available for EOL models.',
        'recommendation': 'Replace the device. D-Link will not patch EOL models.',
        'affected_versions': 'DIR-859, DIR-822, DIR-600 and others (EOL)',
    },

    # ===== CISCO =====
    {
        'vendor_match': ['Cisco'],
        'model_match': ['RV', 'WAP'],
        'title': 'Cisco small business router/AP vulnerabilities',
        'severity': 'high',
        'cve': 'Multiple',
        'description': 'Cisco RV and WAP series small business devices have multiple known vulnerabilities including authentication bypass and RCE. Some models are EOL.',
        'recommendation': 'Update firmware or migrate to Catalyst/Meraki if EOL.',
        'affected_versions': 'RV110W, RV130, RV215W, WAP131, WAP150, WAP361',
    },

    # ===== CISCO MERAKI =====
    {
        'vendor_match': ['Cisco Meraki', 'Meraki'],
        'model_match': ['MR'],
        'title': 'Meraki cloud dependency — offline risk',
        'severity': 'info',
        'cve': '',
        'description': 'Meraki APs require cloud connectivity for management. If the cloud license expires, APs may lose configuration features. Not a vulnerability per se, but an operational risk.',
        'recommendation': 'Ensure Meraki license is current. Plan for offline operation scenarios.',
        'affected_versions': 'All Meraki models',
    },

    # ===== ARUBA =====
    {
        'vendor_match': ['Aruba'],
        'model_match': [],
        'title': 'CVE-2023-22747 — Aruba ArubaOS critical RCE',
        'severity': 'critical',
        'cve': 'CVE-2023-22747',
        'description': 'Multiple buffer overflow vulnerabilities in ArubaOS allow unauthenticated remote code execution via PAPI (UDP port 8211).',
        'recommendation': 'Update ArubaOS to 10.3.1.1, 8.10.0.5, or later.',
        'affected_versions': 'ArubaOS < 10.3.1.1, < 8.10.0.5',
    },

    # ===== ASUS =====
    {
        'vendor_match': ['ASUSTek', 'ASUS'],
        'model_match': [],
        'title': 'ASUS router known vulnerabilities',
        'severity': 'high',
        'cve': 'CVE-2023-39238 through CVE-2023-39240',
        'description': 'Multiple ASUS routers have format string vulnerabilities allowing unauthenticated RCE. ASUS routers frequently targeted by botnets.',
        'recommendation': 'Update firmware to latest version. Enable automatic firmware updates.',
        'affected_versions': 'RT-AX55, RT-AX56U_V2, RT-AC86U and others',
    },

    # ===== HUAWEI =====
    {
        'vendor_match': ['Huawei', 'HUAWEI'],
        'model_match': [],
        'title': 'Huawei — supply chain and backdoor concerns',
        'severity': 'medium',
        'cve': '',
        'description': 'Multiple governments have raised concerns about potential backdoors in Huawei networking equipment. Several countries have restricted or banned Huawei from critical infrastructure.',
        'recommendation': 'Assess risk based on your threat model. Consider replacing in sensitive environments.',
        'affected_versions': 'All models — policy concern, not specific CVE',
    },

    # ===== LINKSYS =====
    {
        'vendor_match': ['Linksys', 'Cisco-Linksys'],
        'model_match': [],
        'title': 'Linksys consumer router vulnerabilities',
        'severity': 'medium',
        'cve': 'Multiple',
        'description': 'Linksys consumer routers have had multiple authentication bypass and information disclosure vulnerabilities. Older models are EOL.',
        'recommendation': 'Update firmware. Replace EOL models.',
        'affected_versions': 'E-series, WRT-series older models',
    },

    # ===== ZYXEL =====
    {
        'vendor_match': ['ZyXEL', 'Zyxel'],
        'model_match': [],
        'title': 'CVE-2023-28771 — Zyxel OS command injection',
        'severity': 'critical',
        'cve': 'CVE-2023-28771',
        'description': 'Unauthenticated OS command injection in Zyxel firewalls and APs via IKE packet processing. Actively exploited by Mirai botnet.',
        'recommendation': 'Update firmware immediately.',
        'affected_versions': 'ZyWALL, USG, ATP, VPN, NWA series — multiple firmware versions',
    },

    # ===== FORTINET =====
    {
        'vendor_match': ['Fortinet'],
        'model_match': [],
        'title': 'CVE-2024-21762 — FortiOS out-of-bound write',
        'severity': 'critical',
        'cve': 'CVE-2024-21762',
        'description': 'Critical RCE in FortiOS SSL VPN. Actively exploited in the wild. Affects FortiGate firewalls which also manage FortiAP access points.',
        'recommendation': 'Update FortiOS immediately. CISA added to Known Exploited Vulnerabilities catalog.',
        'affected_versions': 'FortiOS 6.x, 7.0.x < 7.0.14, 7.2.x < 7.2.7, 7.4.x < 7.4.3',
    },

    # ===== GENERIC CONSUMER ROUTERS =====
    {
        'vendor_match': ['Tenda', 'Comfast', 'Xiaomi', 'Redmi'],
        'model_match': [],
        'title': 'Budget consumer router — limited security updates',
        'severity': 'low',
        'cve': '',
        'description': 'Budget consumer routers from this vendor typically receive infrequent firmware updates. Known vulnerabilities may remain unpatched.',
        'recommendation': 'Check vendor website for latest firmware. Consider replacing with a vendor that provides regular security updates.',
        'affected_versions': 'Most consumer models',
    },

    # ===== OLD/UNKNOWN HARDWARE =====
    {
        'vendor_match': ['Belkin', 'Buffalo', 'Sagemcom'],
        'model_match': [],
        'title': 'Potentially outdated hardware',
        'severity': 'low',
        'cve': '',
        'description': 'This vendor has reduced or discontinued its Wi-Fi product line. Hardware may no longer receive security updates.',
        'recommendation': 'Verify firmware is up to date. Consider replacing if no updates are available.',
        'affected_versions': 'Older models',
    },
]


def check_ap_vulnerabilities(vendor, model_name='', model_number='', device_name='', manufacturer=''):
    """
    Check a detected AP against the vulnerability database.
    Returns list of matching vulnerabilities.
    """
    matches = []
    # Build searchable strings
    all_text = f"{vendor} {manufacturer} {model_name} {model_number} {device_name}".lower()

    for vuln in AP_VULNERABILITIES:
        # Check vendor match
        vendor_matched = False
        for v in vuln['vendor_match']:
            if v.lower() in all_text:
                vendor_matched = True
                break

        if not vendor_matched:
            continue

        # Check model match (if specified, at least one must match)
        model_patterns = vuln['model_match']
        if model_patterns:
            model_matched = any(m.lower() in all_text for m in model_patterns)
            if not model_matched:
                continue

        matches.append({
            'severity': vuln['severity'],
            'title': vuln['title'],
            'cve': vuln.get('cve', ''),
            'description': vuln['description'],
            'recommendation': vuln['recommendation'],
            'affected_versions': vuln.get('affected_versions', ''),
        })

    return matches
