# Wi-Fi Capacity Planning Engine
# Implements airtime-budget methodology used by enterprise planning tools

import math

# ===== REFERENCE DATA =====

# Realistic per-client effective throughput by Wi-Fi generation (Mbps)
# These are goodput (actual data) at moderate signal (-65 dBm), single spatial stream
WIFI_GEN_THROUGHPUT = {
    'wifi4': {'label': 'Wi-Fi 4 (11n)', 'conservative': 8, 'moderate': 15, 'optimistic': 25},
    'wifi5': {'label': 'Wi-Fi 5 (11ac)', 'conservative': 20, 'moderate': 40, 'optimistic': 70},
    'wifi6': {'label': 'Wi-Fi 6 (11ax)', 'conservative': 30, 'moderate': 55, 'optimistic': 90},
    'wifi6e': {'label': 'Wi-Fi 6E', 'conservative': 35, 'moderate': 65, 'optimistic': 110},
    'wifi7': {'label': 'Wi-Fi 7 (11be)', 'conservative': 50, 'moderate': 120, 'optimistic': 200},
}

# MAC efficiency by generation (fraction of airtime that becomes goodput)
WIFI_GEN_EFFICIENCY = {
    'wifi4': 0.45,
    'wifi5': 0.55,
    'wifi6': 0.67,
    'wifi6e': 0.72,
    'wifi7': 0.78,
}

# Application profiles: bandwidth requirements per client (Mbps)
APPLICATION_PROFILES = {
    'voip': {
        'label': 'VoIP / Voice',
        'down_mbps': 0.1, 'up_mbps': 0.1,
        'latency_ms': 150, 'jitter_ms': 30,
        'min_rssi': -67, 'min_snr': 25,
        'description': 'Voice calls (G.711/Opus)',
    },
    'video_conf': {
        'label': 'Video Conferencing (HD)',
        'down_mbps': 3.0, 'up_mbps': 2.0,
        'latency_ms': 150, 'jitter_ms': 30,
        'min_rssi': -67, 'min_snr': 25,
        'description': 'Zoom, Teams, WebEx (720p-1080p)',
    },
    'video_conf_gallery': {
        'label': 'Video Conf (Gallery View)',
        'down_mbps': 6.0, 'up_mbps': 2.5,
        'latency_ms': 150, 'jitter_ms': 30,
        'min_rssi': -65, 'min_snr': 25,
        'description': 'Video call with 10-25 participant gallery',
    },
    'web_browsing': {
        'label': 'Web Browsing',
        'down_mbps': 3.0, 'up_mbps': 0.5,
        'latency_ms': 300, 'jitter_ms': None,
        'min_rssi': -72, 'min_snr': 20,
        'description': 'General web, SaaS apps, Office 365',
    },
    'email': {
        'label': 'Email',
        'down_mbps': 0.5, 'up_mbps': 0.5,
        'latency_ms': None, 'jitter_ms': None,
        'min_rssi': -75, 'min_snr': 15,
        'description': 'Email with occasional attachments',
    },
    'streaming_hd': {
        'label': 'Video Streaming (HD)',
        'down_mbps': 6.0, 'up_mbps': 0.1,
        'latency_ms': 500, 'jitter_ms': None,
        'min_rssi': -72, 'min_snr': 20,
        'description': 'Netflix, YouTube at 1080p',
    },
    'streaming_4k': {
        'label': 'Video Streaming (4K)',
        'down_mbps': 25.0, 'up_mbps': 0.1,
        'latency_ms': 500, 'jitter_ms': None,
        'min_rssi': -67, 'min_snr': 25,
        'description': '4K streaming content',
    },
    'cloud_file_sync': {
        'label': 'Cloud / File Sync',
        'down_mbps': 10.0, 'up_mbps': 5.0,
        'latency_ms': None, 'jitter_ms': None,
        'min_rssi': -72, 'min_snr': 20,
        'description': 'OneDrive, Dropbox, large file transfers',
    },
    'iot_sensor': {
        'label': 'IoT Sensor',
        'down_mbps': 0.05, 'up_mbps': 0.05,
        'latency_ms': None, 'jitter_ms': None,
        'min_rssi': -80, 'min_snr': 12,
        'description': 'Low-rate telemetry, environmental sensors',
    },
    'iot_camera': {
        'label': 'IoT Camera',
        'down_mbps': 1.0, 'up_mbps': 5.0,
        'latency_ms': 300, 'jitter_ms': None,
        'min_rssi': -72, 'min_snr': 20,
        'description': 'IP cameras, video upload',
    },
    'ar_vr': {
        'label': 'AR/VR',
        'down_mbps': 75.0, 'up_mbps': 15.0,
        'latency_ms': 20, 'jitter_ms': 5,
        'min_rssi': -60, 'min_snr': 30,
        'description': 'Augmented/virtual reality headsets',
    },
}

# Composite user profiles (shortcuts)
USER_PROFILES = {
    'light': {
        'label': 'Light User',
        'total_mbps': 1.5,
        'description': 'Email, basic web, messaging',
        'apps': {'email': 1, 'web_browsing': 0.3},
    },
    'medium': {
        'label': 'Medium User (Office)',
        'total_mbps': 6.0,
        'description': 'Web, occasional video calls, cloud apps',
        'apps': {'web_browsing': 1, 'video_conf': 0.3, 'email': 1},
    },
    'heavy': {
        'label': 'Heavy User (Knowledge Worker)',
        'total_mbps': 12.0,
        'description': 'Frequent video calls, cloud sync, web',
        'apps': {'video_conf': 0.7, 'web_browsing': 1, 'cloud_file_sync': 0.5, 'email': 1},
    },
    'very_heavy': {
        'label': 'Very Heavy User',
        'total_mbps': 25.0,
        'description': 'Media production, 4K, large transfers',
        'apps': {'video_conf_gallery': 0.5, 'streaming_4k': 0.3, 'cloud_file_sync': 1, 'web_browsing': 1},
    },
    'iot_only': {
        'label': 'IoT Device',
        'total_mbps': 0.1,
        'description': 'Sensors, low-rate telemetry',
        'apps': {'iot_sensor': 1},
    },
}

# Environment presets
ENVIRONMENT_PRESETS = {
    'open_office': {
        'label': 'Open Office',
        'area_per_user_sqm': 8,
        'description': '~8 sq m per person, moderate density',
    },
    'dense_office': {
        'label': 'Dense Office / Call Centre',
        'area_per_user_sqm': 5,
        'description': '~5 sq m per person, high density',
    },
    'conference_room': {
        'label': 'Conference / Meeting Room',
        'area_per_user_sqm': 2,
        'description': '~2 sq m per person, very dense',
    },
    'lecture_hall': {
        'label': 'Lecture Hall / Auditorium',
        'area_per_user_sqm': 1.2,
        'description': '~1.2 sq m per seat',
    },
    'warehouse': {
        'label': 'Warehouse / Retail Floor',
        'area_per_user_sqm': 50,
        'description': 'Large area, few users, coverage-driven',
    },
    'hospital_ward': {
        'label': 'Hospital Ward',
        'area_per_user_sqm': 10,
        'description': 'Patients + staff + medical devices',
    },
    'hotel_rooms': {
        'label': 'Hotel Rooms',
        'area_per_user_sqm': 15,
        'description': '~1-2 devices per room, coverage-driven',
    },
    'stadium': {
        'label': 'Stadium / Arena',
        'area_per_user_sqm': 0.6,
        'description': 'Extreme density, capacity-driven',
    },
    'classroom': {
        'label': 'Classroom / Training Room',
        'area_per_user_sqm': 2.5,
        'description': '~30 students per room',
    },
}

# Coverage area per AP by environment (sq m at -72 dBm)
# These are rough estimates for typical ceiling-mounted APs
AP_COVERAGE_AREA = {
    'open_plan': 350,       # Open space, few walls
    'light_walls': 250,     # Drywall/glass partitions
    'medium_walls': 180,    # Standard office with some walls
    'heavy_walls': 100,     # Concrete/brick walls
    'outdoor': 700,         # Outdoor open area
}


def calculate_capacity(params):
    """
    Main capacity planning calculation.

    params: {
        'zones': [
            {
                'name': str,
                'area_sqm': float,
                'num_devices': int,
                'user_profile': str (key from USER_PROFILES) or None,
                'throughput_per_device': float (Mbps, used if user_profile is None),
                'device_mix': {'wifi4': %, 'wifi5': %, 'wifi6': %, 'wifi6e': %, 'wifi7': %},
                'band_split': {'2.4ghz': %, '5ghz': %, '6ghz': %},
                'applications': [{'app_id': str, 'users': int}] or None,
            }
        ],
        'ap_model': {
            'max_clients_per_radio': int,
            'num_radios': int,  # typically 2 or 3
            'tx_power_5': int (dBm),
            'wifi_gen': str,
        },
        'ssid_count': int,
        'wall_type': str (key from AP_COVERAGE_AREA),
        'design_margin': float (0.0 to 0.3, default 0.2 = 20%),
        'throughput_assumption': str ('conservative', 'moderate', 'optimistic'),
    }

    Returns: detailed breakdown per zone and overall recommendation.
    """
    zones = params.get('zones', [])
    ap_info = params.get('ap_model', {})
    ssid_count = params.get('ssid_count', 3)
    wall_type = params.get('wall_type', 'medium_walls')
    design_margin = params.get('design_margin', 0.2)
    throughput_mode = params.get('throughput_assumption', 'moderate')

    max_clients_per_radio = ap_info.get('max_clients_per_radio', 60)
    num_radios = ap_info.get('num_radios', 2)
    max_clients_per_ap = max_clients_per_radio * num_radios
    ap_wifi_gen = ap_info.get('wifi_gen', 'wifi6')

    coverage_area_per_ap = AP_COVERAGE_AREA.get(wall_type, 180)

    # Beacon overhead: ~1.5% per SSID
    beacon_overhead = ssid_count * 0.015
    # Management overhead: ~4%
    mgmt_overhead = 0.04
    # Safety margin
    safety = design_margin
    # Usable airtime fraction per AP
    usable_airtime = max(0.1, 1.0 - beacon_overhead - mgmt_overhead - safety)

    zone_results = []
    total_aps_coverage = 0
    total_aps_capacity = 0
    total_aps_client = 0
    total_devices = 0
    total_area = 0

    for zone in zones:
        zname = zone.get('name', 'Zone')
        area = zone.get('area_sqm', 0)
        num_devices = zone.get('num_devices', 0)
        total_devices += num_devices
        total_area += area

        # Determine throughput per device
        profile_key = zone.get('user_profile')
        if profile_key and profile_key in USER_PROFILES:
            tp_per_device = USER_PROFILES[profile_key]['total_mbps']
        else:
            tp_per_device = zone.get('throughput_per_device', 6.0)

        # Device mix (defaults)
        device_mix = zone.get('device_mix', {
            'wifi4': 5, 'wifi5': 30, 'wifi6': 55, 'wifi6e': 8, 'wifi7': 2
        })
        # Normalise to fractions
        mix_total = sum(device_mix.values()) or 100
        mix_frac = {k: v / mix_total for k, v in device_mix.items()}

        # Band split (defaults)
        band_split = zone.get('band_split', {'2.4ghz': 15, '5ghz': 75, '6ghz': 10})
        bs_total = sum(band_split.values()) or 100
        bs_frac = {k: v / bs_total for k, v in band_split.items()}

        # ---- Calculate airtime demand ----
        total_airtime_demand = 0.0
        airtime_detail = []

        for gen, frac in mix_frac.items():
            if frac <= 0:
                continue
            n_clients = num_devices * frac
            gen_data = WIFI_GEN_THROUGHPUT.get(gen)
            if not gen_data:
                continue
            effective_rate = gen_data.get(throughput_mode, gen_data['moderate'])
            efficiency = WIFI_GEN_EFFICIENCY.get(gen, 0.55)

            # Airtime per client = throughput_needed / effective_rate
            # (effective_rate is already goodput, not PHY rate)
            airtime_per_client = tp_per_device / effective_rate
            airtime_this_group = n_clients * airtime_per_client

            total_airtime_demand += airtime_this_group
            airtime_detail.append({
                'generation': gen_data['label'],
                'clients': round(n_clients, 1),
                'effective_rate_mbps': effective_rate,
                'efficiency': round(efficiency * 100),
                'airtime_per_client_pct': round(airtime_per_client * 100, 2),
                'total_airtime_pct': round(airtime_this_group * 100, 1),
            })

        # ---- Three-way AP calculation ----

        # 1. Coverage-based
        aps_coverage = math.ceil(area / coverage_area_per_ap) if area > 0 else 0

        # 2. Capacity-based (airtime)
        aps_capacity = math.ceil(total_airtime_demand / usable_airtime) if usable_airtime > 0 else 0

        # 3. Client-limit-based
        aps_client = math.ceil(num_devices / max_clients_per_ap) if max_clients_per_ap > 0 else 0

        # Final = max of all three
        aps_required = max(aps_coverage, aps_capacity, aps_client, 1 if num_devices > 0 else 0)

        # Determine which constraint is binding
        if aps_required == aps_capacity and aps_capacity >= aps_coverage and aps_capacity >= aps_client:
            binding = 'capacity'
        elif aps_required == aps_client and aps_client >= aps_coverage:
            binding = 'client_limit'
        else:
            binding = 'coverage'

        # Per-AP stats at recommended count
        clients_per_ap = round(num_devices / aps_required, 1) if aps_required > 0 else 0
        airtime_per_ap_pct = round((total_airtime_demand / aps_required) * 100, 1) if aps_required > 0 else 0
        area_per_ap = round(area / aps_required, 1) if aps_required > 0 else 0

        total_aps_coverage += aps_coverage
        total_aps_capacity += aps_capacity
        total_aps_client += aps_client

        # Minimum RSSI (strictest application in this zone)
        min_rssi = -75
        if profile_key:
            profile = USER_PROFILES.get(profile_key, {})
            for app_id in profile.get('apps', {}):
                app = APPLICATION_PROFILES.get(app_id, {})
                if app.get('min_rssi') and app['min_rssi'] > min_rssi:
                    min_rssi = app['min_rssi']

        zone_results.append({
            'name': zname,
            'area_sqm': area,
            'num_devices': num_devices,
            'throughput_per_device': tp_per_device,
            'total_throughput_mbps': round(tp_per_device * num_devices, 1),
            'total_airtime_demand_pct': round(total_airtime_demand * 100, 1),
            'airtime_detail': airtime_detail,
            'aps_coverage': aps_coverage,
            'aps_capacity': aps_capacity,
            'aps_client_limit': aps_client,
            'aps_required': aps_required,
            'binding_constraint': binding,
            'clients_per_ap': clients_per_ap,
            'airtime_per_ap_pct': airtime_per_ap_pct,
            'area_per_ap_sqm': area_per_ap,
            'min_rssi': min_rssi,
        })

    total_aps = sum(z['aps_required'] for z in zone_results)

    # Recommendations
    recommendations = []
    for z in zone_results:
        if z['airtime_per_ap_pct'] > 70:
            recommendations.append(f"{z['name']}: Airtime utilisation is high ({z['airtime_per_ap_pct']}% per AP). Consider adding more APs or reducing SSIDs.")
        if z['clients_per_ap'] > 50:
            recommendations.append(f"{z['name']}: {z['clients_per_ap']} clients per AP is high. Target < 50 for reliable performance.")
        if z['binding_constraint'] == 'capacity':
            recommendations.append(f"{z['name']}: Capacity-driven design. AP count driven by airtime demand, not coverage area.")
        if z['binding_constraint'] == 'client_limit':
            recommendations.append(f"{z['name']}: Client-limit-driven. AP hardware supports max {max_clients_per_ap} clients. Consider higher-capacity APs.")

    if ssid_count > 4:
        recommendations.append(f"Reduce SSID count from {ssid_count} to 3-4. Each SSID adds ~1.5% beacon overhead.")

    return {
        'zones': zone_results,
        'total_aps': total_aps,
        'total_devices': total_devices,
        'total_area_sqm': total_area,
        'usable_airtime_pct': round(usable_airtime * 100, 1),
        'beacon_overhead_pct': round(beacon_overhead * 100, 1),
        'coverage_area_per_ap_sqm': coverage_area_per_ap,
        'max_clients_per_ap': max_clients_per_ap,
        'recommendations': recommendations,
        'parameters': {
            'ssid_count': ssid_count,
            'wall_type': wall_type,
            'design_margin_pct': round(design_margin * 100),
            'throughput_assumption': throughput_mode,
        },
    }


def get_reference_data():
    """Return all reference tables for the frontend."""
    return {
        'wifi_generations': WIFI_GEN_THROUGHPUT,
        'wifi_efficiency': {k: round(v * 100) for k, v in WIFI_GEN_EFFICIENCY.items()},
        'applications': APPLICATION_PROFILES,
        'user_profiles': USER_PROFILES,
        'environments': ENVIRONMENT_PRESETS,
        'wall_types': {k: {'label': k.replace('_', ' ').title(), 'area_sqm': v} for k, v in AP_COVERAGE_AREA.items()},
    }
