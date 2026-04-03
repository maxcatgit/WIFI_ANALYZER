from flask import Flask, jsonify, request, send_file
import subprocess
import re
from datetime import datetime
import os
import time
from tzlocal import get_localzone
import pytz
import threading
import glob
import logging
import uuid
import math
from ap_models import AP_MODELS, get_vendors, search_models, get_wifi_gen_summary
from capacity_planner import calculate_capacity, get_reference_data

app = Flask(__name__, static_folder='static')

app.logger.disabled = True
app.config['PROPAGATE_EXCEPTIONS'] = True

log = logging.getLogger('werkzeug')
log.disabled = True

# Determine the running user and home directory dynamically
import pwd
RUNNING_USER = os.environ.get('USER') or os.environ.get('LOGNAME') or pwd.getpwuid(os.getuid()).pw_name
RUNNING_HOME = os.path.expanduser(f'~{RUNNING_USER}')

@app.after_request
def after_request(response):
    return response

log = logging.getLogger('werkzeug')
log.disabled = True

# Store adapter state and multi state
adapter_states = {}
multi_state = {}
previous_phies = set()

# Frequency to channel mapping with bandwidth info
FREQ_TO_CHANNEL = {
    2412: {'channel': '1', 'bandwidth': 'HT20'},
    2417: {'channel': '2', 'bandwidth': 'HT20'},
    2422: {'channel': '3', 'bandwidth': 'HT20'},
    2427: {'channel': '4', 'bandwidth': 'HT20'},
    2432: {'channel': '5', 'bandwidth': 'HT20'},
    2437: {'channel': '6', 'bandwidth': 'HT20'},
    2442: {'channel': '7', 'bandwidth': 'HT20'},
    2447: {'channel': '8', 'bandwidth': 'HT20'},
    2452: {'channel': '9', 'bandwidth': 'HT20'},
    2457: {'channel': '10', 'bandwidth': 'HT20'},
    2462: {'channel': '11', 'bandwidth': 'HT20'},
    2467: {'channel': '12', 'bandwidth': 'HT20'},
    2472: {'channel': '13', 'bandwidth': 'HT20'},
    2484: {'channel': '14', 'bandwidth': 'HT20'},

    # 5GHz channels
    5180: {'channel': '36', 'bandwidth': '80MHz'},
    5200: {'channel': '40', 'bandwidth': '80MHz'},
    5220: {'channel': '44', 'bandwidth': '80MHz'},
    5240: {'channel': '48', 'bandwidth': '80MHz'},
    5260: {'channel': '52', 'bandwidth': '80MHz'},
    5280: {'channel': '56', 'bandwidth': '80MHz'},
    5300: {'channel': '60', 'bandwidth': '80MHz'},
    5320: {'channel': '64', 'bandwidth': '80MHz'},
    5500: {'channel': '100', 'bandwidth': '80MHz'},
    5520: {'channel': '104', 'bandwidth': '80MHz'},
    5540: {'channel': '108', 'bandwidth': '80MHz'},
    5560: {'channel': '112', 'bandwidth': '80MHz'},
    5580: {'channel': '116', 'bandwidth': '80MHz'},
    5600: {'channel': '120', 'bandwidth': '80MHz'},
    5620: {'channel': '124', 'bandwidth': '80MHz'},
    5640: {'channel': '128', 'bandwidth': '80MHz'},
    5660: {'channel': '132', 'bandwidth': '80MHz'},
    5680: {'channel': '136', 'bandwidth': '80MHz'},
    5700: {'channel': '140', 'bandwidth': '80MHz'},
    5720: {'channel': '144', 'bandwidth': '80MHz'},
    5745: {'channel': '149', 'bandwidth': '80MHz'},
    5765: {'channel': '153', 'bandwidth': '80MHz'},
    5785: {'channel': '157', 'bandwidth': '80MHz'},
    5805: {'channel': '161', 'bandwidth': '80MHz'},
    5825: {'channel': '165', 'bandwidth': 'HT20'},

    # 6GHz channels
    5955: {'channel': '1', 'bandwidth': '80MHz'},
    5975: {'channel': '5', 'bandwidth': '80MHz'},
    5995: {'channel': '9', 'bandwidth': '80MHz'},
    6015: {'channel': '13', 'bandwidth': '80MHz'},
    6035: {'channel': '17', 'bandwidth': '80MHz'},
    6055: {'channel': '21', 'bandwidth': '80MHz'},
    6075: {'channel': '25', 'bandwidth': '80MHz'},
    6095: {'channel': '29', 'bandwidth': '80MHz'},
    6115: {'channel': '33', 'bandwidth': '80MHz'},
    6135: {'channel': '37', 'bandwidth': '80MHz'},
    6155: {'channel': '41', 'bandwidth': '80MHz'},
    6175: {'channel': '45', 'bandwidth': '80MHz'},
    6195: {'channel': '49', 'bandwidth': '80MHz'},
    6215: {'channel': '53', 'bandwidth': '80MHz'},
    6235: {'channel': '57', 'bandwidth': '80MHz'},
    6255: {'channel': '61', 'bandwidth': '80MHz'},
    6275: {'channel': '65', 'bandwidth': '80MHz'},
    6295: {'channel': '69', 'bandwidth': '80MHz'},
    6315: {'channel': '73', 'bandwidth': '80MHz'},
    6335: {'channel': '77', 'bandwidth': '80MHz'},
    6355: {'channel': '81', 'bandwidth': '80MHz'},
    6375: {'channel': '85', 'bandwidth': '80MHz'},
    6395: {'channel': '89', 'bandwidth': '80MHz'},
    6415: {'channel': '93', 'bandwidth': '80MHz'}
}

# Thread for channel hopping
channel_hopping_threads = {}

def cleanup_specific_session(session):
    try:
        if is_process_running(session):
            subprocess.run(['sudo', 'screen', '-S', session, '-X', 'quit'], capture_output=True, text=True, check=True, timeout=5)
    except Exception:
        pass

def get_interfaces_info():
    result = subprocess.run(["iw", "dev"], capture_output=True, text=True, check=True)
    lines = result.stdout.splitlines()

    interfaces = []
    current_phy = None
    current_iface = None

    for raw in lines:
        line = raw.strip()

        m_phy = re.match(r"^phy#(\d+)", line)
        if m_phy:
            current_phy = f"phy#{m_phy.group(1)}"
            current_iface = None
            continue

        m_iface = re.match(r"^Interface\s+(\S+)$", line)
        if m_iface and current_phy:
            current_iface = m_iface.group(1)
            continue

        m_type = re.match(r"^type\s+(\S+)$", line)
        if m_type and current_phy and current_iface:
            interfaces.append({
                "phy": current_phy,
                "interface": current_iface,
                "type": m_type.group(1)
            })
            current_iface = None

    return interfaces

def get_adapters():
    try:
        interfaces = get_interfaces_info()
        # Group by phy, prefer monitor-mode 'mon' interfaces
        phy_adapters = {}
        for i in interfaces:
            if i['phy'] == 'phy#0' or not i['interface'].startswith('wlan'):
                continue
            phy = i['phy']
            if phy not in phy_adapters:
                phy_adapters[phy] = []
            phy_adapters[phy].append(i)
        monitor_adapters = []
        for phy, ifaces in phy_adapters.items():
            # If a 'mon' interface exists for this phy, use only that
            mon_ifaces = [i for i in ifaces if i['type'] == 'monitor' and i['interface'].endswith('mon')]
            if mon_ifaces:
                monitor_adapters.extend([i['interface'] for i in mon_ifaces])
        return sorted(monitor_adapters)
    except Exception:
        return []

def is_monitor_mode(adapter):
    try:
        interfaces = get_interfaces_info()
        for i in interfaces:
            if i['interface'] == adapter and i['type'] == 'monitor':
                return True
        return False
    except Exception:
        return False

def is_process_running(session_name):
    try:
        cmd = ['sudo', 'screen', '-ls']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return session_name in result.stdout
        return False
    except subprocess.TimeoutExpired:
        return False
    except subprocess.CalledProcessError:
        return False

def channel_hopping_loop(adapter, frequencies, dwell_time):
    while adapter in channel_hopping_threads and channel_hopping_threads[adapter]['running']:
        for freq in frequencies:
            if not (adapter in channel_hopping_threads and channel_hopping_threads[adapter]['running']):
                break

            freq_info = FREQ_TO_CHANNEL.get(int(freq))
            if not freq_info:
                continue

            bandwidth = freq_info['bandwidth']

            cmd = ['sudo', 'iw', 'dev', adapter, 'set', 'freq', str(freq), bandwidth]
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass

            time.sleep(dwell_time / 1000.0)

def compute_capture_size(pcap_filename, split_time):
    size_bytes = 0
    if split_time > 0:
        base_no_ext = pcap_filename.rsplit('.', 1)[0]
        files = glob.glob(base_no_ext + '_*.pcap')
        for f in files:
            if os.path.exists(f):
                size_bytes += os.path.getsize(f)
    else:
        if os.path.exists(pcap_filename):
            size_bytes = os.path.getsize(pcap_filename)
    return round(size_bytes / (1024 * 1024), 2)

# ... (all previous code unchanged until build_capture_filter)

def build_capture_filter(selections):
    filters = []

    # Management
    if selections.get('mgt_all', False):
        filters.append('type mgt')
    elif selections.get('mgt_specific', False):
        mgt_sub = []
        if selections.get('beacon', False): mgt_sub.append('subtype beacon')
        if selections.get('probe_req', False): mgt_sub.append('subtype probe-req')
        if selections.get('probe_resp', False): mgt_sub.append('subtype probe-resp')
        if selections.get('auth', False): mgt_sub.append('subtype auth')
        if selections.get('assoc_req', False): mgt_sub.append('subtype assoc-req')
        if selections.get('assoc_resp', False): mgt_sub.append('subtype assoc-resp')
        if selections.get('reassoc_req', False): mgt_sub.append('subtype reassoc-req')
        if selections.get('reassoc_resp', False): mgt_sub.append('subtype reassoc-resp')
        if selections.get('disassoc', False): mgt_sub.append('subtype disassoc')
        if selections.get('deauth', False): mgt_sub.append('subtype deauth')
        if selections.get('atim', False): mgt_sub.append('subtype atim')
        if mgt_sub:
            filters.extend(mgt_sub)
    # if mgt_none → add nothing for management

    # Control
    if selections.get('ctl_all', False):
        filters.append('type ctl')
    elif selections.get('ctl_specific', False):
        ctl_sub = []
        if selections.get('rts', False): ctl_sub.append('subtype rts')
        if selections.get('cts', False): ctl_sub.append('subtype cts')
        if selections.get('ack', False): ctl_sub.append('subtype ack')
        if selections.get('ps_poll', False): ctl_sub.append('subtype ps-poll')
        if selections.get('cf_end', False): ctl_sub.append('subtype cf-end')
        if selections.get('cf_end_ack', False): ctl_sub.append('subtype cf-end-ack')
        if ctl_sub:
            filters.extend(ctl_sub)

    # Data
    if selections.get('data_all', False):
        filters.append('type data')
    elif selections.get('data_specific', False):
        data_sub = []
        if selections.get('eapol', False): data_sub.append('ether proto 0x888e')
        if selections.get('data_cf_ack', False): data_sub.append('subtype data-cf-ack')
        if selections.get('data_cf_poll', False): data_sub.append('subtype data-cf-poll')
        if selections.get('data_cf_ack_poll', False): data_sub.append('subtype data-cf-ack-poll')
        if selections.get('null', False): data_sub.append('subtype null')
        if selections.get('cf_ack', False): data_sub.append('subtype cf-ack')
        if selections.get('cf_poll', False): data_sub.append('subtype cf-poll')
        if selections.get('cf_ack_poll', False): data_sub.append('subtype cf-ack-poll')
        if selections.get('qos_data', False): data_sub.append('subtype qos-data')
        if selections.get('qos_data_cf_ack', False): data_sub.append('subtype qos-data-cf-ack')
        if selections.get('qos_data_cf_poll', False): data_sub.append('subtype qos-data-cf-poll')
        if selections.get('qos_data_cf_ack_poll', False): data_sub.append('subtype qos-data-cf-ack-poll')
        if selections.get('qos_null', False): data_sub.append('subtype qos')
        if selections.get('qos_cf_poll', False): data_sub.append('subtype qos-cf-poll')
        if selections.get('qos_cf_ack_poll', False): data_sub.append('subtype qos-cf-ack-poll')
        if data_sub:
            filters.extend(data_sub)

    return ' or '.join(filters) if filters else ''


def start_capture_func(adapters, filename, split_time, is_multi=False, capture_filter=''):
    if not adapters:
        return {'error': 'No adapters provided'}, 400

    if is_multi:
        if multi_state.get('busy', False):
            cleanup_specific_session('dumpcap_multi')
            pcap_filename = multi_state.get('pcap_file')
            st = multi_state.get('split_time', 0)
            last_size = compute_capture_size(pcap_filename, st) if pcap_filename else 0.0
            multi_state.update({
                'last_pcap_file': pcap_filename,
                'last_split_time': st,
                'last_filesize': last_size,
                'busy': False,
                'adapters': [],
                'pcap_file': None,
                'split_time': 0,
                'filesize': 0.0,
                'capture_filter': ''
            })
    else:
        adapter = adapters[0]
        state = adapter_states.get(adapter, {})
        if state.get('dumpcap_busy', False):
            session = f'dumpcap_{adapter}'
            cleanup_specific_session(session)
            pcap_filename = state.get('pcap_file')
            st = state.get('split_time', 0)
            last_size = compute_capture_size(pcap_filename, st) if pcap_filename else 0.0
            adapter_states[adapter].update({
                'last_pcap_file': pcap_filename,
                'last_split_time': st,
                'last_filesize': last_size,
                'dumpcap_busy': False,
                'pcap_file': None,
                'split_time': 0,
                'filesize': 0.0,
                'capture_filter': ''
            })

    session_name = 'dumpcap_multi' if is_multi else f'dumpcap_{adapters[0]}'

    local_tz = get_localzone()
    local_tz = pytz.timezone(str(local_tz))
    utc_now = datetime.now(pytz.UTC)
    local_now = utc_now.astimezone(local_tz)
    timestamp = local_now.strftime('%Y-%m-%d--%H-%M-%S')
    base_filename = re.sub(r'[^a-zA-Z0-9-_]', '', filename)[:50]
    if not base_filename:
        base_filename = 'capture'
    pcap_base = f'{RUNNING_HOME}/{timestamp}_{base_filename}'
    pcap_filename = pcap_base + '.pcap'

    try:
        os.makedirs(RUNNING_HOME, exist_ok=True)
        if not split_time:
            with open(pcap_filename, 'wb') as f:
                f.write(b'\xa1\xb2\xc3\xd4\x00\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x01\x00\x00\x00')
    except (OSError, PermissionError):
        return {'error': 'Cannot write capture file. Check disk space or permissions.'}, 500

    cmd = ['sudo', 'screen', '-dmS', session_name, 'sudo', '-u', RUNNING_USER, 'dumpcap']
    for adapter in adapters:
        cmd.extend(['-i', adapter])
        if capture_filter:
            cmd.extend(['-f', capture_filter])
    cmd.extend(['-w', pcap_filename])
    if split_time:
        cmd.extend(['-b', f'duration:{split_time}'])





    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        time.sleep(2)
        if not is_process_running(session_name):
            # Try to get the screen log to see why it failed
            diag = ''
            try:
                # Check if the interface exists and is up
                iface_check = subprocess.run(['ip', 'link', 'show', adapters[0]],
                                             capture_output=True, text=True, timeout=3)
                if iface_check.returncode != 0:
                    diag = f'Interface {adapters[0]} not found. '
                elif 'DOWN' in iface_check.stdout:
                    diag = f'Interface {adapters[0]} is DOWN. '
                # Try running dumpcap directly to see the error
                test_cmd = ['sudo', 'dumpcap', '-i', adapters[0], '-c', '1', '-w', '/dev/null']
                test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
                if test_result.returncode != 0:
                    diag += f'dumpcap error: {test_result.stderr.strip()}'
            except Exception:
                pass
            return {'error': f'Failed to start capture process. {diag}'.strip()}, 500
        if is_multi:
            multi_state.update({
                'busy': True,
                'adapters': adapters,
                'pcap_file': pcap_filename,
                'split_time': int(split_time) if split_time else 0,
                'filesize': 0.0,
                'capture_filter': capture_filter
            })
        else:
            adapter = adapters[0]
            adapter_states[adapter].update({
                'dumpcap_busy': True,
                'pcap_file': pcap_filename,
                'split_time': int(split_time) if split_time else 0,
                'filesize': 0.0,
                'status': 'Capturing',
                'capture_filter': capture_filter
            })
        return {
            'message': f'Capturing to {pcap_filename}' + (' (split files)' if split_time else ''),
            'pcap_file': pcap_filename,
            'filesize': 0.0
        }
    except subprocess.TimeoutExpired:
        return {'error': 'Operation timed out'}, 500
    except subprocess.CalledProcessError as e:
        return {'error': f'Failed to start capture: {e.stderr}'}, 500

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/adapters', methods=['GET'])
def adapters():
    global previous_phies
    try:
        interfaces = get_interfaces_info()
        current_phies = {i['phy'] for i in interfaces if i['phy'] != 'phy#0'}

        if current_phies != previous_phies:
            for adapter in list(adapter_states.keys()):
                state = adapter_states.get(adapter, {})
                if state.get('dumpcap_busy', False):
                    session = f'dumpcap_{adapter}'
                    cleanup_specific_session(session)
                    pcap_filename = state.get('pcap_file')
                    st = state.get('split_time', 0)
                    last_size = compute_capture_size(pcap_filename, st) if pcap_filename else 0.0
                    adapter_states[adapter].update({
                        'last_pcap_file': pcap_filename,
                        'last_split_time': st,
                        'last_filesize': last_size,
                        'dumpcap_busy': False,
                        'pcap_file': None,
                        'split_time': 0,
                        'filesize': 0.0,
                        'capture_filter': ''
                    })
            if multi_state.get('busy', False):
                cleanup_specific_session('dumpcap_multi')
                pcap_filename = multi_state.get('pcap_file')
                st = multi_state.get('split_time', 0)
                last_size = compute_capture_size(pcap_filename, st) if pcap_filename else 0.0
                multi_state.update({
                    'last_pcap_file': pcap_filename,
                    'last_split_time': st,
                    'last_filesize': last_size,
                    'busy': False,
                    'adapters': [],
                    'pcap_file': None,
                    'split_time': 0,
                    'filesize': 0.0,
                    'capture_filter': ''
                })

            for adapter in list(channel_hopping_threads.keys()):
                channel_hopping_threads[adapter]['running'] = False
                if channel_hopping_threads[adapter]['thread']:
                    channel_hopping_threads[adapter]['thread'].join(timeout=5)
                del channel_hopping_threads[adapter]
                if adapter in adapter_states:
                    adapter_states[adapter].update({
                        'hopping_active': False,
                        'frequencies': [],
                        'status': 'Enabled' if is_monitor_mode(adapter) else 'Disabled'
                    })

            mon_adapters = [i['interface'] for i in interfaces if i['phy'] != 'phy#0' and i['type'] == 'monitor' and i['interface'].startswith('wlan') and i['interface'].endswith('mon')]
            for ad_mon in mon_adapters:
                try:
                    subprocess.run(['sudo', 'airmon-ng', 'stop', ad_mon], capture_output=True, text=True, check=True, timeout=10)
                    if ad_mon in adapter_states:
                        adapter_states[ad_mon].update({'status': 'Disabled'})
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass

            interfaces = get_interfaces_info()
            non_mon = [i['interface'] for i in interfaces if i['phy'] != 'phy#0' and i['type'] == 'managed' and i['interface'].startswith('wlan') and not i['interface'].endswith('mon') and i['interface'] != 'wlan0']
            for ad in non_mon:
                try:
                    adapter_states[ad] = adapter_states.get(ad, {})
                    subprocess.run(['sudo', 'airmon-ng', 'start', ad], capture_output=True, text=True, check=True, timeout=10)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass
            previous_phies = current_phies

        adapters_list = get_adapters()
        adapter_info = []
        monitor_adapters = []

        for adapter in adapters_list:
            state = adapter_states.get(adapter, {})
            is_monitor = is_monitor_mode(adapter)
            if is_monitor:
                monitor_adapters.append(adapter)

            hopping_active = adapter in channel_hopping_threads and channel_hopping_threads[adapter]['running']
            dumpcap_busy = state.get('dumpcap_busy', False)
            status = 'Disabled'
            if is_monitor:
                status = 'Enabled'
            if hopping_active:
                status = 'Monitoring'
            if dumpcap_busy:
                status = 'Capturing'

            channels = [FREQ_TO_CHANNEL.get(int(freq), {}).get('channel', 'Unknown') for freq in state.get('frequencies', [])]

            adapter_states[adapter] = {
                'frequencies': state.get('frequencies', []),
                'dwell_time': state.get('dwell_time') or state.get('last_dwell_time', 200),
                'hopping_active': hopping_active,
                'dumpcap_busy': dumpcap_busy,
                'pcap_file': state.get('pcap_file', None),
                'split_time': state.get('split_time', 0),
                'filesize': state.get('filesize', 0.0),
                'last_pcap_file': state.get('last_pcap_file', None),
                'last_split_time': state.get('last_split_time', 0),
                'last_filesize': state.get('last_filesize', 0.0),
                'status': status,
                'capture_filter': state.get('capture_filter', '')
            }

            adapter_info.append({
                'name': adapter,
                'monitor': is_monitor,
                'frequencies': adapter_states[adapter]['frequencies'],
                'channels': channels,
                'dwell_time': adapter_states[adapter]['dwell_time'],
                'hopping_active': hopping_active,
                'dumpcap_busy': dumpcap_busy,
                'pcap_file': adapter_states[adapter]['pcap_file'],
                'split_time': adapter_states[adapter]['split_time'],
                'filesize': adapter_states[adapter]['filesize'],
                'last_pcap_file': adapter_states[adapter]['last_pcap_file'],
                'last_split_time': adapter_states[adapter]['last_split_time'],
                'last_filesize': adapter_states[adapter]['last_filesize'],
                'status': status,
                'is_monitor': is_monitor,
                'capture_filter': adapter_states[adapter]['capture_filter']
            })

        multi_possible = len(monitor_adapters) >= 2

        return jsonify({
            'adapters': adapter_info,
            'multi': multi_state,
            'multi_possible': multi_possible
        })
    except Exception:
        return jsonify({'adapters': [], 'multi': {}, 'multi_possible': False})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    try:
        subprocess.run(['sudo', 'poweroff'], check=True)
        return jsonify({'status': 'success'})
    except subprocess.CalledProcessError:
        return jsonify({'status': 'error', 'message': 'Failed'}), 500

@app.route('/monitor_on', methods=['POST'])
def monitor_on():
    data = request.get_json()
    adapter = data.get('adapter')
    if not adapter or not adapter.startswith('wlan') or adapter == 'wlan0':
        return jsonify({'error': 'Invalid adapter'}), 400
    try:
        state = adapter_states.get(adapter, {})
        if state.get('dumpcap_busy', False):
            session = f'dumpcap_{adapter}'
            cleanup_specific_session(session)
            pcap_filename = state.get('pcap_file')
            st = state.get('split_time', 0)
            last_size = compute_capture_size(pcap_filename, st) if pcap_filename else 0.0
            adapter_states[adapter].update({
                'last_pcap_file': pcap_filename,
                'last_split_time': st,
                'last_filesize': last_size,
                'dumpcap_busy': False,
                'pcap_file': None,
                'split_time': 0,
                'filesize': 0.0,
                'capture_filter': ''
            })
        if multi_state.get('busy', False) and adapter in multi_state.get('adapters', []):
            cleanup_specific_session('dumpcap_multi')
            pcap_filename = multi_state.get('pcap_file')
            st = multi_state.get('split_time', 0)
            last_size = compute_capture_size(pcap_filename, st) if pcap_filename else 0.0
            multi_state.update({
                'last_pcap_file': pcap_filename,
                'last_split_time': st,
                'last_filesize': last_size,
                'busy': False,
                'adapters': [],
                'pcap_file': None,
                'split_time': 0,
                'filesize': 0.0,
                'capture_filter': ''
            })
        result = subprocess.run(['sudo', 'airmon-ng', 'start', adapter], capture_output=True, text=True, check=True, timeout=10)
        adapter_states[adapter] = adapter_states.get(adapter, {})
        return jsonify({'message': f'Adapter {adapter} enabled'})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Operation timed out'}), 500
    except subprocess.CalledProcessError:
        return jsonify({'error': 'Failed to enable adapter. Check compatibility.'}), 500

@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    data = request.get_json()
    adapter = data.get('adapter')
    frequencies = data.get('frequencies', [])
    dwell_time = data.get('dwell_time')

    if not adapter or not adapter.endswith('mon'):
        return jsonify({'error': 'Adapter must be enabled'}), 400
    if not frequencies or not isinstance(frequencies, list):
        return jsonify({'error': 'Select at least one frequency'}), 400
    try:
        dwell_time = int(dwell_time)
        if dwell_time not in [200, 500, 1000, 5000, 10000, 60000, 300000]:
            return jsonify({'error': 'Invalid dwell time'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid dwell time format'}), 400

    if adapter in channel_hopping_threads:
        channel_hopping_threads[adapter]['running'] = False
        if channel_hopping_threads[adapter]['thread']:
            channel_hopping_threads[adapter]['thread'].join(timeout=5)
        del channel_hopping_threads[adapter]

    valid_frequencies = []
    valid_channels = []
    for freq in frequencies:
        try:
            freq_clean = str(freq).strip()
            freq_int = int(freq_clean)
            if freq_int in FREQ_TO_CHANNEL:
                valid_frequencies.append(freq_clean)
                valid_channels.append(FREQ_TO_CHANNEL[freq_int]['channel'])
        except (ValueError, TypeError):
            pass

    if not valid_frequencies:
        return jsonify({'error': 'No valid frequencies selected'}), 400

    if len(valid_frequencies) == 1:
        freq = valid_frequencies[0]
        bandwidth = FREQ_TO_CHANNEL[int(freq)]['bandwidth']
        cmd = ['sudo', 'iw', 'dev', adapter, 'set', 'freq', freq, bandwidth]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
            channel_hopping_threads[adapter] = {'running': True, 'thread': None}
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return jsonify({'error': 'Error setting frequency'}), 500
    else:
        channel_hopping_threads[adapter] = {
            'running': True,
            'thread': threading.Thread(target=channel_hopping_loop, args=(adapter, valid_frequencies, dwell_time))
        }
        channel_hopping_threads[adapter]['thread'].daemon = True
        channel_hopping_threads[adapter]['thread'].start()

    adapter_states[adapter] = adapter_states.get(adapter, {})
    adapter_states[adapter].update({
        'frequencies': valid_frequencies,
        'dwell_time': dwell_time,
        'hopping_active': True,
        'status': 'Monitoring'
    })

    return jsonify({
        'message': f'Monitoring frequencies on {adapter}',
        'channels': valid_channels
    })

@app.route('/start_capture', methods=['POST'])
def start_capture():
    data = request.get_json()
    adapter = data.get('adapter')
    filename = data.get('filename', '').strip()
    split_time = data.get('split_time')
    capture_filter = data.get('capture_filter', '')

    if not adapter or not adapter.endswith('mon'):
        return jsonify({'error': 'Adapter must be enabled'}), 400

    if split_time:
        try:
            split_time = int(split_time)
        except ValueError:
            return jsonify({'error': 'Invalid split time'}), 400

    adapters = [adapter]
    result = start_capture_func(adapters, filename, split_time, is_multi=False, capture_filter=capture_filter)
    if isinstance(result, tuple) and 'error' in result[0]:
        return jsonify(result[0]), result[1]
    return jsonify(result)

@app.route('/start_dumpcap', methods=['POST'])
def start_dumpcap():
    data = request.get_json()
    adapters = data.get('adapters', [])
    filename = data.get('filename', '').strip()
    split_time = data.get('split_time')
    capture_filter = data.get('capture_filter', '')

    if not adapters or not isinstance(adapters, list) or not all(adapter.endswith('mon') for adapter in adapters):
        return jsonify({'error': 'Select at least one enabled adapter'}), 400

    if len(adapters) < 2:
        return jsonify({'error': 'Multi capture requires at least two adapters'}), 400

    if split_time:
        try:
            split_time = int(split_time)
        except ValueError:
            return jsonify({'error': 'Invalid split time'}), 400

    result = start_capture_func(adapters, filename, split_time, is_multi=True, capture_filter=capture_filter)
    if isinstance(result, tuple) and 'error' in result[0]:
        return jsonify(result[0]), result[1]
    return jsonify(result)

@app.route('/stop_capture', methods=['POST'])
def stop_capture():
    data = request.get_json()
    adapter = data.get('adapter')
    if not adapter:
        return jsonify({'error': 'Invalid adapter'}), 400

    state = adapter_states.get(adapter, {})
    if not state.get('dumpcap_busy', False):
        return jsonify({'error': 'No active capture session'}), 400

    try:
        session_name = f'dumpcap_{adapter}'
        cleanup_specific_session(session_name)
        pcap_filename = state.get('pcap_file')
        split_time = state.get('split_time', 0)
        last_size = compute_capture_size(pcap_filename, split_time) if pcap_filename else 0.0
        adapter_states[adapter].update({
            'last_pcap_file': pcap_filename,
            'last_split_time': split_time,
            'last_filesize': last_size,
            'dumpcap_busy': False,
            'pcap_file': None,
            'split_time': 0,
            'filesize': 0.0,
            'capture_filter': '',
            'status': 'Monitoring' if adapter_states[adapter].get('hopping_active', False) else ('Enabled' if is_monitor_mode(adapter) else 'Disabled')
        })
        return jsonify({'message': f'Stopped capture on {adapter}'})
    except Exception:
        return jsonify({'error': 'Failed to stop capture.'}), 500

@app.route('/stop_dumpcap', methods=['POST'])
def stop_dumpcap():
    try:
        if not multi_state.get('busy', False):
            return jsonify({'error': 'No active multi capture session'}), 400
        cleanup_specific_session('dumpcap_multi')
        pcap_filename = multi_state.get('pcap_file')
        split_time = multi_state.get('split_time', 0)
        last_size = compute_capture_size(pcap_filename, split_time) if pcap_filename else 0.0
        multi_state.update({
            'last_pcap_file': pcap_filename,
            'last_split_time': split_time,
            'last_filesize': last_size,
            'busy': False,
            'adapters': [],
            'pcap_file': None,
            'split_time': 0,
            'filesize': 0.0,
            'capture_filter': ''
        })
        return jsonify({'message': 'Stopped multi capture'})
    except Exception:
        return jsonify({'error': 'Failed to stop dumpcap.'}), 500

@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    data = request.get_json()
    adapter = data.get('adapter')
    if not adapter or not adapter.endswith('mon'):
        return jsonify({'error': 'Invalid adapter'}), 400

    if not adapter_states.get(adapter, {}).get('hopping_active', False):
        return jsonify({'error': 'No active monitoring session'}), 400

    try:
        if adapter in channel_hopping_threads:
            channel_hopping_threads[adapter]['running'] = False
            if channel_hopping_threads[adapter]['thread']:
                channel_hopping_threads[adapter]['thread'].join(timeout=5)
            del channel_hopping_threads[adapter]

        adapter_states[adapter].update({
            'hopping_active': False,
            'frequencies': [],
            'status': 'Enabled',
            'last_dwell_time': adapter_states[adapter].get('dwell_time', 200)
        })
        return jsonify({'message': f'Stopped monitoring on {adapter}'})
    except Exception:
        return jsonify({'error': 'Failed to stop monitoring.'}), 500

@app.route('/filesize', methods=['POST'])
def filesize():
    data = request.get_json()
    adapter = data.get('adapter')
    if adapter == 'multi':
        if not multi_state.get('busy', False):
            return jsonify({'filesize': 0.0})
        pcap_filename = multi_state.get('pcap_file')
        split_time = multi_state.get('split_time', 0)
        size_mb = compute_capture_size(pcap_filename, split_time)
        multi_state['filesize'] = size_mb
        return jsonify({'filesize': size_mb})
    else:
        if not adapter or not adapter.endswith('mon'):
            return jsonify({'error': 'Invalid adapter'}), 400

        state = adapter_states.get(adapter, {})
        if not state.get('dumpcap_busy', False):
            return jsonify({'filesize': 0.0})

        pcap_filename = state.get('pcap_file')
        split_time = state.get('split_time', 0)
        size_mb = compute_capture_size(pcap_filename, split_time)
        state['filesize'] = size_mb
        return jsonify({'filesize': size_mb})

@app.route('/download/<adapter>', methods=['GET'])
def download(adapter):
    if adapter == 'multi':
        pcap_base = multi_state.get('pcap_file') or multi_state.get('last_pcap_file')
        split_time = multi_state.get('split_time', 0) if multi_state.get('busy', False) else multi_state.get('last_split_time', 0)
    else:
        if not adapter or not adapter.endswith('mon'):
            return jsonify({'error': 'Invalid adapter'}), 400

        state = adapter_states.get(adapter, {})
        pcap_base = state.get('pcap_file') or state.get('last_pcap_file')
        split_time = state.get('split_time', 0) if state.get('dumpcap_busy', False) else state.get('last_split_time', 0)

    if not pcap_base:
        return jsonify({'error': 'No capture file available'}), 404

    if split_time:
        files = glob.glob(pcap_base.replace('.pcap', '_*.pcap'))
        if not files:
            return jsonify({'error': 'No split files found'}), 404
        files.sort(key=lambda f: int(f.split('_')[-1].split('.')[0]))
        latest = files[-1]
    else:
        latest = pcap_base
    if not os.path.exists(latest):
        return jsonify({'error': 'Capture file not found'}), 404

    try:
        return send_file(latest, as_attachment=True)
    except OSError:
        return jsonify({'error': 'Failed to download file'}), 500

# --- Wi-Fi Network Scanner ---

scan_lock = threading.Lock()

# OUI database: try loading from ieee oui.txt file, fall back to built-in map
def _load_oui_file():
    """Try to load OUI data from a local copy of the IEEE OUI file."""
    oui_paths = [
        '/usr/share/ieee-data/oui.txt',
        '/usr/share/nmap/nmap-mac-prefixes',
        '/usr/share/wireshark/manuf',
        os.path.join(os.path.dirname(__file__), 'oui.txt'),
    ]
    loaded = {}
    for path in oui_paths:
        try:
            if not os.path.exists(path):
                continue
            with open(path, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # IEEE oui.txt format: "XX-XX-XX   (hex)		Vendor Name"
                    m = re.match(r'^([0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2})\s+\(hex\)\s+(.+)$', line)
                    if m:
                        prefix = m.group(1).upper().replace('-', ':')
                        vendor = m.group(2).strip()
                        loaded[prefix] = vendor
                        continue
                    # IEEE oui.txt alternate format: "XXXXXX     (base 16)		Vendor Name"
                    m = re.match(r'^([0-9A-Fa-f]{6})\s+\(base 16\)\s+(.+)$', line)
                    if m:
                        raw = m.group(1).upper()
                        prefix = f"{raw[0:2]}:{raw[2:4]}:{raw[4:6]}"
                        vendor = m.group(2).strip()
                        if prefix not in loaded:  # (hex) line takes precedence
                            loaded[prefix] = vendor
                        continue
                    # Wireshark manuf format: "XX:XX:XX	VendorShort	Vendor Long Name"
                    m = re.match(r'^([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})\s+(\S+)\s*(.*)?$', line)
                    if m:
                        prefix = m.group(1).upper()
                        vendor = m.group(3).strip() if m.group(3).strip() else m.group(2).strip()
                        loaded[prefix] = vendor
                        continue
                    # nmap-mac-prefixes format: "XXXXXX Vendor Name"
                    m = re.match(r'^([0-9A-Fa-f]{6})\s+(.+)$', line)
                    if m:
                        raw = m.group(1).upper()
                        prefix = f"{raw[0:2]}:{raw[2:4]}:{raw[4:6]}"
                        vendor = m.group(2).strip()
                        loaded[prefix] = vendor
                        continue
            if loaded:
                # Clean up any vendor names with "(base 16)" or "(hex)" artifacts
                for k in loaded:
                    v = loaded[k]
                    v = re.sub(r'\s*\(base 16\)\s*', '', v)
                    v = re.sub(r'\s*\(hex\)\s*', '', v)
                    loaded[k] = v.strip()
                return loaded
        except Exception:
            continue
    return None

_oui_from_file = _load_oui_file()

# Common OUI prefixes (first 3 octets) -> vendor name
_OUI_BUILTIN = {
    "00:00:5E": "IANA", "00:01:42": "Cisco", "00:03:6B": "Cisco",
    "00:03:93": "Apple", "00:05:69": "VMware", "00:0A:95": "Apple",
    "00:0C:29": "VMware", "00:0C:43": "Ralink", "00:0E:8E": "Aruba",
    "00:0F:66": "Cisco", "00:10:18": "Broadcom", "00:11:24": "Apple",
    "00:14:6C": "Netgear", "00:16:B6": "Cisco", "00:17:3F": "Belkin",
    "00:17:C4": "Quanta", "00:18:0A": "Cisco", "00:19:07": "Cisco",
    "00:1A:1E": "Aruba", "00:1A:2B": "Ayecom", "00:1B:2F": "Netgear",
    "00:1C:10": "Cisco", "00:1C:B3": "Apple", "00:1D:09": "Dell",
    "00:1E:58": "D-Link", "00:1F:33": "Netgear", "00:1F:3C": "Intel",
    "00:1F:5B": "Apple", "00:21:29": "Cisco", "00:21:6A": "Intel",
    "00:22:6B": "Cisco", "00:23:69": "Cisco", "00:24:D7": "Intel",
    "00:25:00": "Apple", "00:25:9C": "Cisco", "00:26:5A": "D-Link",
    "00:26:82": "Cisco", "00:26:BB": "Apple", "00:27:22": "Ubiquiti",
    "00:30:44": "Cisco", "00:30:BD": "Belkin", "00:40:96": "Cisco",
    "00:50:56": "VMware", "00:6B:F1": "Cisco", "00:90:4C": "Epigram",
    "04:18:D6": "Ubiquiti", "04:D5:90": "Fortinet",
    "08:36:C9": "Intel", "08:66:98": "Apple",
    "0C:75:BD": "Cisco", "0C:8D:DB": "Samsung",
    "10:0B:A9": "Intel", "10:40:F3": "Apple", "10:6F:3F": "EnGenius",
    "14:CC:20": "TP-Link", "14:CF:92": "TP-Link", "14:91:82": "TP-Link",
    "18:0F:76": "D-Link", "18:64:72": "Aruba", "18:E8:29": "Intel",
    "1C:87:2C": "ASUS", "1C:B7:2C": "ASUSTek",
    "20:A6:CD": "Hewlett Packard", "20:3C:AE": "Samsung",
    "24:0A:C4": "Espressif", "24:5A:4C": "Ubiquiti",
    "28:6C:07": "Xiaomi", "28:CF:DA": "Apple",
    "2C:30:33": "Netgear", "2C:F0:5D": "Micro-Star",
    "30:B5:C2": "TP-Link", "30:DE:4B": "TP-Link",
    "34:68:95": "Hon Hai", "34:98:B5": "Netgear",
    "38:1A:52": "Samsung", "38:2C:4A": "ASUSTek",
    "3C:37:86": "Netgear", "3C:7C:3F": "ASUSTek",
    "40:01:7A": "Cisco", "40:16:7E": "ASUSTek",
    "44:07:0B": "Google", "44:D9:E7": "Ubiquiti", "44:E9:DD": "TP-Link",
    "48:DA:35": "Google", "48:F8:B3": "Linksys",
    "4C:32:75": "Apple", "4C:E6:76": "Buffalo",
    "50:3E:AA": "TP-Link", "50:6A:03": "Netgear", "50:C7:BF": "TP-Link",
    "54:60:09": "Google", "54:A0:50": "ASUSTek",
    "58:D5:6E": "D-Link", "58:EF:68": "Belkin",
    "5C:5B:35": "Apple", "5C:CF:7F": "Espressif",
    "60:22:32": "Ubiquiti", "60:38:E0": "Belkin",
    "64:66:B3": "Apple", "64:70:02": "TP-Link",
    "68:72:51": "Ubiquiti", "68:7F:74": "Cisco",
    "6C:72:20": "D-Link", "6C:F3:7F": "Aruba",
    "70:3A:CB": "Google", "70:A7:41": "Ubiquiti",
    "74:DA:38": "EnGenius", "74:AC:B9": "Ubiquiti",
    "78:8A:20": "Ubiquiti", "78:45:58": "Juniper",
    "7C:10:C9": "Samsung", "7C:DD:90": "Shenzhen",
    "80:2A:A8": "Ubiquiti", "80:69:33": "Intel",
    "84:D8:1B": "TP-Link", "84:A4:23": "Sagemcom",
    "88:71:B1": "Ruckus", "88:DC:96": "EnGenius",
    "8C:68:C8": "Samsung", "8C:85:90": "Apple",
    "90:72:40": "Apple", "90:A7:C1": "Apple",
    "94:B8:6D": "TP-Link", "94:10:3E": "Belkin",
    "98:DA:C4": "TP-Link", "98:FC:11": "Cisco",
    "9C:5C:8E": "Apple", "9E:F4:AB": "Apple",
    "A0:63:91": "Netgear", "A0:F3:C1": "TP-Link",
    "A4:2B:B0": "TP-Link", "A4:CF:12": "Espressif",
    "A8:5E:45": "ASUSTek", "AC:22:0B": "ASUSTek", "AC:84:C6": "TP-Link",
    "B0:39:56": "Netgear", "B0:4E:26": "TP-Link", "B0:BE:76": "TP-Link",
    "B4:FB:E4": "Ubiquiti",
    "B8:27:EB": "Raspberry Pi", "B8:E8:56": "Apple",
    "C0:25:E9": "TP-Link", "C0:56:27": "Belkin", "C4:41:1E": "Belkin",
    "C4:E9:84": "TP-Link",
    "CC:32:E5": "TP-Link", "CC:40:D0": "Netgear",
    "D0:21:F9": "Ubiquiti", "D0:57:94": "Samsung",
    "D4:6E:0E": "TP-Link",
    "D8:47:32": "TP-Link", "D8:6C:63": "Google",
    "DC:9F:DB": "Ubiquiti", "DC:A6:32": "Raspberry Pi",
    "E0:63:DA": "Ubiquiti",
    "E4:38:83": "TP-Link", "E8:48:B8": "TP-Link", "E8:65:D4": "Tenda",
    "F0:9F:C2": "Ubiquiti", "F0:D5:BF": "Google",
    "F4:92:BF": "Ubiquiti", "F4:EC:38": "TP-Link",
    "FC:EC:DA": "Ubiquiti", "FC:F5:28": "ZyXEL",
    "2C:D0:5A": "Ruckus", "AC:A3:1E": "Aruba", "D4:20:B0": "Ruckus",
    "B4:5D:50": "Aruba", "6C:F3:7F": "Aruba", "24:F2:7F": "Aruba",
    "D8:C7:C8": "Aruba", "20:4C:03": "Aruba",
    "00:1A:A0": "Dell", "F8:DB:88": "Dell", "34:17:EB": "Dell",
    "00:1E:67": "Intel", "00:1F:3C": "Intel",
    "3C:A9:F4": "Intel", "7C:B2:7D": "Intel",
    "A0:36:9F": "Intel", "48:51:B7": "Intel",
    "00:24:6C": "Ruckus", "70:DF:2F": "Cisco Meraki",
    "00:18:74": "Cisco Meraki", "AC:17:02": "Cisco Meraki",
    "34:56:FE": "Cisco Meraki", "E0:CB:BC": "Cisco Meraki",
    "88:15:44": "Cisco Meraki", "0C:8D:DB": "Samsung",
    "C0:3F:0E": "Netgear", "A0:04:60": "Netgear",
    "E4:F0:42": "Google", "A4:77:33": "Google",
    "58:CB:52": "Google", "F4:F5:D8": "Google",
    # Additional common vendors
    "00:0C:E6": "Meru Networks", "00:12:0E": "AboCom", "00:12:17": "Cisco-Linksys",
    "00:13:46": "D-Link", "00:14:BF": "Cisco-Linksys", "00:15:6D": "Ubiquiti",
    "00:17:9A": "D-Link", "00:18:39": "Cisco-Linksys", "00:19:5B": "D-Link",
    "00:1A:70": "Cisco-Linksys", "00:1C:DF": "Belkin", "00:1D:7E": "Cisco-Linksys",
    "00:1E:E5": "Cisco-Linksys", "00:21:29": "Cisco", "00:22:6B": "Cisco",
    "00:23:69": "Cisco-Linksys", "00:24:01": "D-Link", "00:25:00": "Apple",
    "00:26:F2": "Netgear", "00:50:43": "Marvell",
    "04:D5:90": "Fortinet", "04:E5:36": "Apple",
    "08:00:27": "Oracle VirtualBox", "08:00:69": "Silicon Graphics",
    "08:BD:43": "Netgear", "08:EA:44": "Extreme Networks",
    "0C:47:C9": "Amazon", "0C:96:BF": "Huawei",
    "10:0C:6B": "Netgear", "10:5B:AD": "Mega Well",
    "10:DA:43": "Netgear", "10:E7:C6": "Huawei",
    "14:1A:A3": "Motorola", "14:59:C0": "Netgear",
    "14:AB:C5": "Intel", "14:DD:A9": "ASUSTek",
    "18:31:BF": "ASUSTek", "18:A6:F7": "TP-Link",
    "1C:3B:F3": "Espressif", "1C:69:7A": "Ubiquiti",
    "20:47:47": "Dell", "20:C9:D0": "Apple",
    "24:01:C7": "Cisco", "24:4B:FE": "ASUSTek",
    "24:A0:74": "Apple", "24:DA:9B": "Motorola",
    "28:16:AD": "Intel", "28:80:88": "Intel",
    "28:C6:8E": "Netgear", "28:D2:44": "LCFC",
    "2C:3A:FD": "Intel", "2C:4D:54": "ASUSTek",
    "2C:56:DC": "ASUSTek", "2C:6E:85": "Intel",
    "2C:91:AB": "CyberTAN", "2C:DB:07": "Intel",
    "30:24:32": "Apple", "30:91:8F": "Technicolor",
    "30:FD:38": "Google", "32:06:9A": "Samsung",
    "34:02:86": "Intel", "34:13:E8": "Intel",
    "34:29:8F": "Apple", "34:36:3B": "Apple",
    "34:7C:25": "Apple", "34:E1:2D": "Intel",
    "38:B1:DB": "HP", "38:C9:86": "Apple",
    "38:DE:AD": "Intel", "38:F9:D3": "Apple",
    "3C:06:30": "Apple", "3C:22:FB": "Apple",
    "3C:52:A1": "Apple", "3C:91:80": "Intel",
    "40:33:1A": "Apple", "40:49:0F": "Hon Hai",
    "40:88:05": "Motorola", "40:9C:28": "Apple",
    "40:B0:76": "ASUSTek", "40:CB:C0": "Apple",
    "40:D3:AE": "Samsung", "40:F0:2F": "Liteon",
    "44:03:2C": "Intel", "44:2A:60": "Apple",
    "44:6D:57": "Liteon", "44:85:00": "Intel",
    "48:2C:A0": "Xiaomi", "48:3B:38": "Apple",
    "48:45:20": "Intel", "48:A4:72": "Samsung",
    "48:D7:05": "Apple", "4C:34:88": "Intel",
    "4C:57:CA": "Apple", "4C:EB:42": "Intel",
    "50:32:37": "Apple", "50:ED:3C": "Apple",
    "50:F7:22": "Apple", "54:26:96": "Apple",
    "54:33:CB": "Apple", "54:72:4F": "Apple",
    "54:AE:27": "Apple", "54:E4:3A": "Apple",
    "58:1C:F8": "Samsung", "58:40:4E": "Apple",
    "58:55:CA": "Apple", "58:B0:35": "Apple",
    "5C:E9:1E": "Apple", "5C:F7:E6": "Apple",
    "60:01:94": "Apple", "60:69:44": "Apple",
    "60:8C:4A": "Apple", "60:A4:D0": "Samsung",
    "60:F8:1D": "Apple", "60:FE:C5": "Apple",
    "64:20:0C": "Apple", "64:4B:F0": "Huawei",
    "64:76:BA": "Apple", "64:9A:BE": "Apple",
    "64:B0:A6": "Apple", "68:5B:35": "Apple",
    "68:96:7B": "Apple", "68:AB:1E": "Apple",
    "68:D9:3C": "Apple", "68:DB:CA": "Apple",
    "6C:19:C0": "Apple", "6C:40:08": "Apple",
    "6C:4D:73": "Apple", "6C:70:9F": "Apple",
    "6C:94:66": "Apple", "6C:96:CF": "Apple",
    "70:11:24": "Apple", "70:48:0F": "Apple",
    "70:56:81": "Apple", "70:73:CB": "Apple",
    "70:DE:E2": "Apple", "70:EC:E4": "Apple",
    "70:F0:87": "Apple", "74:42:8B": "Intel",
    "74:8D:08": "Apple", "74:E2:F5": "Apple",
    "78:31:C1": "Apple", "78:67:D7": "Apple",
    "78:7E:61": "Apple", "78:88:6D": "Apple",
    "78:9F:70": "Apple", "78:CA:39": "Apple",
    "78:D7:5F": "Samsung", "7C:04:D0": "Apple",
    "7C:50:49": "Apple", "7C:6D:62": "Apple",
    "7C:9A:1D": "Apple", "7C:C3:A1": "Apple",
    "80:00:6E": "Apple", "80:49:71": "Apple",
    "80:82:23": "Apple", "80:B0:3D": "Apple",
    "80:E6:50": "Apple", "80:ED:2C": "Apple",
    "84:38:35": "Apple", "84:78:8B": "Apple",
    "84:85:06": "Apple", "84:AB:1A": "Apple",
    "84:B1:53": "Apple", "84:FC:AC": "Apple",
    "88:19:08": "Apple", "88:1F:A1": "Apple",
    "88:53:95": "Apple", "88:63:DF": "Apple",
    "88:66:A5": "Apple", "88:C9:D0": "Apple",
    "88:E8:7F": "Apple", "8C:00:6D": "Apple",
    "8C:29:37": "Apple", "8C:58:77": "Apple",
    "8C:7B:9D": "Apple", "8C:FA:BA": "Apple",
    "90:27:E4": "Apple", "90:3C:92": "Apple",
    "90:84:0D": "Apple", "90:8D:6C": "Apple",
    "90:B0:ED": "Apple", "90:B2:1F": "Apple",
    "90:B6:86": "Apple", "90:FD:61": "Apple",
    "94:E9:6A": "Apple", "94:F6:A3": "Apple",
    "98:01:A7": "Apple", "98:03:D8": "Apple",
    "98:46:0A": "Apple", "98:5A:EB": "Apple",
    "98:9E:63": "Apple", "98:B8:E3": "Apple",
    "98:D6:BB": "Apple", "98:E0:D9": "Apple",
    "98:F0:AB": "Apple", "98:FE:94": "Apple",
    "9C:20:7B": "Apple", "9C:35:EB": "Apple",
    "9C:4F:DA": "Apple", "9C:84:BF": "Apple",
    "9C:F4:8E": "Apple", "A0:11:65": "Intel",
    "A0:18:28": "Intel", "A0:78:17": "Apple",
    "A0:99:9B": "Apple", "A0:D7:95": "Apple",
    "A0:ED:CD": "Apple", "A4:5E:60": "Apple",
    "A4:67:06": "Apple", "A4:83:E7": "Apple",
    "A4:B1:97": "Apple", "A4:D1:8C": "Apple",
    "A4:D1:D2": "Intel", "A4:E9:75": "Apple",
    "A8:20:66": "Apple", "A8:5C:2C": "Apple",
    "A8:60:B6": "Apple", "A8:66:7F": "Apple",
    "A8:8E:24": "Apple", "A8:BB:CF": "Apple",
    "A8:FA:D8": "Apple", "AC:1F:74": "Apple",
    "AC:29:3A": "Apple", "AC:3C:0B": "Apple",
    "AC:BC:32": "Apple", "AC:CF:5C": "Apple",
    "AC:E4:B5": "Apple", "AC:FD:EC": "Apple",
    "B0:19:C6": "Apple", "B0:34:95": "Apple",
    "B0:48:1A": "Apple", "B0:65:BD": "Apple",
    "B0:70:2D": "Apple", "B0:9F:BA": "Apple",
    "B4:18:D1": "Apple", "B4:8B:19": "Apple",
    "B4:F0:AB": "Apple", "B8:09:8A": "Apple",
    "B8:17:C2": "Apple", "B8:41:A4": "Apple",
    "B8:44:D9": "Apple", "B8:63:4D": "Apple",
    "B8:78:2E": "Apple", "B8:C1:11": "Apple",
    "B8:F6:B1": "Apple", "B8:FF:61": "Apple",
    "BC:3A:EA": "Apple", "BC:52:B7": "Apple",
    "BC:54:36": "Apple", "BC:6C:21": "Apple",
    "BC:9F:EF": "Apple", "BC:A9:20": "Apple",
    "BC:D0:74": "Apple", "BC:E1:43": "Apple",
    "C0:1A:DA": "Apple", "C0:63:94": "Apple",
    "C0:84:7A": "Apple", "C0:A5:3E": "Apple",
    "C0:B6:58": "Apple", "C0:CC:F8": "Apple",
    "C0:D0:12": "Apple",
    "C4:2A:D0": "Apple", "C4:B3:01": "Apple",
    "C8:2A:14": "Apple", "C8:33:4B": "Apple",
    "C8:69:CD": "Apple", "C8:85:50": "Apple",
    "C8:B2:1E": "Apple", "C8:D0:83": "Apple",
    "CC:08:8D": "Apple", "CC:20:E8": "Apple",
    "CC:25:EF": "Apple", "CC:44:63": "Apple",
    "CC:78:5F": "Apple", "CC:C7:60": "Apple",
    "D0:03:4B": "Apple", "D0:25:98": "Apple",
    "D0:33:11": "Apple", "D0:4F:7E": "Apple",
    "D0:81:7A": "Apple", "D0:C5:F3": "Apple",
    "D0:D2:B0": "Apple", "D4:61:9D": "Apple",
    "D4:9A:20": "Apple", "D4:A3:3D": "Apple",
    "D4:DC:CD": "Apple", "D4:F4:6F": "Apple",
    "D8:00:4D": "Apple", "D8:1D:72": "Apple",
    "D8:30:62": "Apple", "D8:9E:3F": "Apple",
    "D8:A2:5E": "Apple", "D8:BB:2C": "Apple",
    "D8:CF:9C": "Apple",
    "DC:08:56": "Apple", "DC:0C:5C": "Apple",
    "DC:2B:2A": "Apple", "DC:41:5F": "Apple",
    "DC:56:E7": "Apple", "DC:86:D8": "Apple",
    "E0:33:8E": "Apple", "E0:5F:45": "Apple",
    "E0:66:78": "Apple", "E0:B5:2D": "Apple",
    "E0:C7:67": "Apple", "E0:C9:7A": "Apple",
    "E4:25:E7": "Apple", "E4:8B:7F": "Apple",
    "E4:C6:3D": "Apple", "E4:CE:8F": "Apple",
    "E4:E4:AB": "Apple", "E8:06:88": "Apple",
    "E8:80:2E": "Apple",
    "EC:35:86": "Apple", "EC:85:2F": "Apple",
    "F0:18:98": "Apple", "F0:72:EA": "Apple",
    "F0:99:BF": "Apple", "F0:B4:79": "Apple",
    "F0:C1:F1": "Apple", "F0:CB:A1": "Apple",
    "F0:D1:A9": "Apple", "F0:DB:E2": "Apple",
    "F4:06:16": "Apple", "F4:31:C3": "Apple",
    "F4:37:B7": "Apple", "F4:5C:89": "Apple",
    "F8:27:93": "Apple", "F8:38:80": "Apple",
    "F8:62:14": "Apple", "F8:E9:4E": "Apple",
    "FC:25:3F": "Apple", "FC:E9:98": "Apple",
    # Samsung
    "00:07:AB": "Samsung", "00:12:FB": "Samsung", "00:15:99": "Samsung",
    "00:16:32": "Samsung", "00:17:D5": "Samsung", "00:18:AF": "Samsung",
    "00:1B:98": "Samsung", "00:1C:43": "Samsung", "00:1D:25": "Samsung",
    "00:1E:E1": "Samsung", "00:1E:E2": "Samsung", "00:21:4C": "Samsung",
    "00:21:D1": "Samsung", "00:21:D2": "Samsung", "00:23:39": "Samsung",
    "00:23:D6": "Samsung", "00:23:D7": "Samsung", "00:24:54": "Samsung",
    "00:25:66": "Samsung", "00:25:67": "Samsung", "00:26:37": "Samsung",
    "14:49:E0": "Samsung", "14:89:FD": "Samsung", "18:3A:2D": "Samsung",
    "18:67:B0": "Samsung", "1C:62:B8": "Samsung", "24:18:1D": "Samsung",
    "2C:AE:2B": "Samsung", "30:C7:AE": "Samsung", "34:14:5F": "Samsung",
    "34:C3:AC": "Samsung", "38:01:97": "Samsung", "3C:5A:37": "Samsung",
    "40:4E:36": "Samsung", "44:78:3E": "Samsung", "48:44:F7": "Samsung",
    "4C:3C:16": "Samsung", "50:01:BB": "Samsung", "50:B7:C3": "Samsung",
    "50:CC:F8": "Samsung", "54:92:BE": "Samsung", "58:C3:8B": "Samsung",
    "5C:0A:5B": "Samsung", "5C:3C:27": "Samsung", "64:B3:10": "Samsung",
    "6C:F3:73": "Samsung", "78:47:1D": "Samsung", "78:52:1A": "Samsung",
    "78:AB:BB": "Samsung", "84:11:9E": "Samsung", "84:25:DB": "Samsung",
    "84:55:A5": "Samsung", "84:B5:41": "Samsung", "88:32:9B": "Samsung",
    "8C:F5:A3": "Samsung", "90:18:7C": "Samsung", "94:01:C2": "Samsung",
    "94:35:0A": "Samsung", "94:51:03": "Samsung", "98:0C:82": "Samsung",
    "9C:3A:AF": "Samsung", "A0:07:98": "Samsung", "A4:08:EA": "Samsung",
    "A8:7C:01": "Samsung", "AC:36:13": "Samsung", "B0:47:BF": "Samsung",
    "B0:72:BF": "Samsung", "B4:3A:28": "Samsung", "B4:79:A7": "Samsung",
    "B8:5A:73": "Samsung", "BC:14:EF": "Samsung", "BC:72:B1": "Samsung",
    "BC:76:5E": "Samsung", "C0:BD:D1": "Samsung", "C4:73:1E": "Samsung",
    "C8:BA:94": "Samsung", "CC:07:AB": "Samsung", "D0:22:BE": "Samsung",
    "D0:66:7B": "Samsung", "D0:87:E2": "Samsung", "D4:88:90": "Samsung",
    "D8:57:EF": "Samsung", "E4:12:1D": "Samsung", "E4:58:B8": "Samsung",
    "E8:3A:12": "Samsung", "EC:1F:72": "Samsung", "EC:E0:9B": "Samsung",
    "F0:25:B7": "Samsung", "F0:5A:09": "Samsung", "F4:7B:5E": "Samsung",
    "F8:04:2E": "Samsung", "FC:A1:3E": "Samsung",
    # Microsoft / Xbox
    "28:18:78": "Microsoft", "7C:1E:52": "Microsoft", "60:45:BD": "Microsoft",
    # Google / Nest
    "F8:8F:CA": "Google", "DC:E5:5B": "Google", "A4:C6:39": "Google",
    # Huawei / Honor
    "00:1E:10": "Huawei", "00:25:68": "Huawei", "00:25:9E": "Huawei",
    "00:46:4B": "Huawei", "04:02:1F": "Huawei", "04:B0:E7": "Huawei",
    "04:F9:38": "Huawei", "08:19:A6": "Huawei", "08:63:61": "Huawei",
    "0C:37:DC": "Huawei", "10:1B:54": "Huawei", "10:44:00": "Huawei",
    "14:30:04": "Huawei", "14:B9:68": "Huawei", "18:DE:D7": "Huawei",
    "20:08:ED": "Huawei", "20:A6:80": "Huawei", "20:F1:7C": "Huawei",
    "24:09:95": "Huawei", "24:44:27": "Huawei", "24:69:A5": "Huawei",
    "28:31:52": "Huawei", "28:6E:D4": "Huawei", "2C:9D:1E": "Huawei",
    "30:D1:7E": "Huawei", "34:00:A3": "Huawei", "34:CD:BE": "Huawei",
    "38:F8:89": "Huawei", "3C:47:11": "Huawei", "3C:DF:A9": "Huawei",
    "40:4D:8E": "Huawei", "44:55:B1": "Huawei", "48:00:31": "Huawei",
    "48:46:FB": "Huawei", "48:AD:08": "Huawei", "4C:1F:CC": "Huawei",
    "4C:B1:6C": "Huawei", "50:A7:2B": "Huawei", "54:A5:1B": "Huawei",
    "58:2A:F7": "Huawei", "5C:09:79": "Huawei", "5C:4C:A9": "Huawei",
    "60:DE:44": "Huawei", "60:E7:01": "Huawei", "64:16:F0": "Huawei",
    "68:A0:F6": "Huawei", "70:72:3C": "Huawei", "70:79:90": "Huawei",
    "74:88:2A": "Huawei", "78:D3:8D": "Huawei", "7C:60:97": "Huawei",
    "80:B6:86": "Huawei", "80:D0:9B": "Huawei", "84:A8:E4": "Huawei",
    "88:28:B3": "Huawei", "88:3F:D3": "Huawei", "88:53:D4": "Huawei",
    "8C:34:FD": "Huawei", "8C:E5:EF": "Huawei", "90:4E:2B": "Huawei",
    "94:04:9C": "Huawei", "94:77:2B": "Huawei", "98:9C:57": "Huawei",
    "9C:28:EF": "Huawei", "9C:74:1A": "Huawei", "A4:BA:76": "Huawei",
    "AC:61:EA": "Huawei", "AC:E2:15": "Huawei", "B4:15:13": "Huawei",
    "B4:CD:27": "Huawei", "C0:70:09": "Huawei", "C4:07:2F": "Huawei",
    "C8:14:79": "Huawei", "C8:D1:5E": "Huawei", "CC:96:A0": "Huawei",
    "D0:7A:B5": "Huawei", "D4:6A:A8": "Huawei", "D4:B1:10": "Huawei",
    "D8:49:0B": "Huawei", "DC:D2:FC": "Huawei", "E0:19:1D": "Huawei",
    "E0:24:7F": "Huawei", "E4:68:A3": "Huawei", "E8:08:8B": "Huawei",
    "EC:23:3D": "Huawei", "F4:4C:7F": "Huawei", "F4:63:1F": "Huawei",
    "F4:C7:14": "Huawei", "F8:01:13": "Huawei", "F8:4A:BF": "Huawei",
    "FC:48:EF": "Huawei",
    # Xiaomi / Redmi
    "00:9E:C8": "Xiaomi", "04:CF:8C": "Xiaomi", "08:C0:EB": "Xiaomi",
    "0C:1D:AF": "Xiaomi", "10:2A:B3": "Xiaomi", "14:F6:5A": "Xiaomi",
    "18:59:36": "Xiaomi", "1C:BF:CE": "Xiaomi", "20:34:FB": "Xiaomi",
    "28:E3:1F": "Xiaomi", "34:80:B3": "Xiaomi", "38:A4:ED": "Xiaomi",
    "3C:BD:3E": "Xiaomi", "44:23:7C": "Xiaomi", "50:64:2B": "Xiaomi",
    "54:48:E6": "Xiaomi", "58:44:98": "Xiaomi", "5C:B8:CB": "Xiaomi",
    "64:B4:73": "Xiaomi", "68:DF:DD": "Xiaomi", "6C:5C:3D": "Xiaomi",
    "74:23:44": "Xiaomi", "78:02:F8": "Xiaomi", "7C:8B:B5": "Xiaomi",
    "84:CE:32": "Xiaomi", "8C:BF:A6": "Xiaomi", "90:78:B2": "Xiaomi",
    "9C:99:A0": "Xiaomi", "A4:77:58": "Xiaomi", "AC:C1:EE": "Xiaomi",
    "B0:E2:35": "Xiaomi", "B4:A3:82": "Xiaomi", "C4:0B:CB": "Xiaomi",
    "C8:58:C0": "Xiaomi", "D4:61:DA": "Xiaomi", "E4:46:DA": "Xiaomi",
    "F0:B4:D2": "Xiaomi", "F8:A4:5F": "Xiaomi", "FC:64:BA": "Xiaomi",
    # OnePlus / OPPO / Realme
    "94:65:2D": "OnePlus", "C0:EE:FB": "OnePlus", "64:A2:F9": "OnePlus",
    # Lenovo
    "00:09:2D": "Lenovo", "28:D2:44": "Lenovo", "50:7B:9D": "Lenovo",
    "60:D8:19": "Lenovo", "74:E6:1C": "Lenovo", "8C:16:45": "Lenovo",
    "98:54:1B": "Lenovo", "A4:34:D9": "Lenovo", "C8:21:58": "Lenovo",
    "E8:2A:44": "Lenovo", "F0:03:8C": "Lenovo",
    # Dell
    "B0:83:FE": "Dell", "C8:1F:66": "Dell", "D4:BE:D9": "Dell",
    "F0:1F:AF": "Dell", "F8:B1:56": "Dell",
    # HP
    "00:14:38": "HP", "00:17:A4": "HP", "00:1A:4B": "HP",
    "00:1E:0B": "HP", "00:21:5A": "HP", "00:25:B3": "HP",
    "10:1F:74": "HP", "28:92:4A": "HP", "30:8D:99": "HP",
    "3C:D9:2B": "HP", "44:31:92": "HP", "48:0F:CF": "HP",
    "5C:B9:01": "HP", "68:B5:99": "HP", "80:CE:62": "HP",
    "94:57:A5": "HP", "A0:1D:48": "HP", "B4:99:BA": "HP",
    # Sony / PlayStation
    "00:04:1F": "Sony", "00:13:A9": "Sony", "00:1D:0D": "Sony",
    "00:24:BE": "Sony", "28:0D:FC": "Sony", "70:9E:29": "Sony",
    "AC:89:95": "Sony", "FC:0F:E6": "Sony",
    # Amazon / Kindle / Echo / Ring
    "00:FC:8B": "Amazon", "0C:47:C9": "Amazon", "10:CE:A9": "Amazon",
    "14:91:38": "Amazon", "18:74:2E": "Amazon", "34:D2:70": "Amazon",
    "38:F7:3D": "Amazon", "40:A2:DB": "Amazon", "44:65:0D": "Amazon",
    "4C:19:5D": "Amazon", "50:DC:E7": "Amazon", "58:A2:B5": "Amazon",
    "5C:41:5A": "Amazon", "68:37:E9": "Amazon", "68:54:FD": "Amazon",
    "74:75:48": "Amazon", "74:C2:46": "Amazon", "78:E1:03": "Amazon",
    "84:D6:D0": "Amazon", "A0:02:DC": "Amazon", "A4:08:01": "Amazon",
    "AC:63:BE": "Amazon", "B0:FC:36": "Amazon", "B4:7C:9C": "Amazon",
    "C8:FB:26": "Amazon", "CC:9E:A2": "Amazon", "F0:27:2D": "Amazon",
    "F0:81:73": "Amazon", "F0:F0:A4": "Amazon", "FC:65:DE": "Amazon",
    # Sonos
    "00:0E:58": "Sonos", "34:7E:5C": "Sonos", "48:A6:B8": "Sonos",
    "54:2A:1B": "Sonos", "5C:AA:FD": "Sonos", "78:28:CA": "Sonos",
    "94:9F:3E": "Sonos", "B8:E9:37": "Sonos",
    # Roku
    "00:0D:4B": "Roku", "08:05:81": "Roku", "10:59:32": "Roku",
    "20:EF:BD": "Roku", "3C:59:1E": "Roku", "84:EA:ED": "Roku",
    "B0:A7:B9": "Roku", "B8:3E:59": "Roku", "C8:3A:6B": "Roku",
    "D0:4D:C6": "Roku", "DC:3A:5E": "Roku",
}

# Merge: file-based OUI takes precedence, then built-in
OUI_MAP = dict(_OUI_BUILTIN)
if _oui_from_file:
    OUI_MAP.update(_oui_from_file)

def _parse_rsn_wpa_block(lines):
    """Parse RSN or WPA block lines into a dict. Works regardless of indentation format."""
    info = {'pairwise': [], 'akm': [], 'group': '', 'capabilities': ''}
    text = '\n'.join(lines)
    m = re.search(r'Group cipher:\s*(.+)', text)
    if m:
        info['group'] = m.group(1).strip()
    m = re.search(r'Pairwise ciphers?:\s*(.+)', text)
    if m:
        info['pairwise'] = [c.strip() for c in m.group(1).split()]
    m = re.search(r'Authentication suites?:\s*(.+)', text)
    if m:
        info['akm'] = [a.strip() for a in m.group(1).split()]
    m = re.search(r'Capabilities:\s*(.+)', text)
    if m:
        info['capabilities'] = m.group(1).strip()
    return info if (info['akm'] or info['pairwise'] or info['group']) else None


def parse_iw_scan(output):
    # Split output into per-BSS blocks first, then parse each block independently.
    # This avoids fragile line-by-line state tracking.
    bss_blocks = []
    current_lines = []
    current_bssid = None

    for line in output.splitlines():
        m = re.match(r'^BSS ([0-9a-f:]{17})', line)
        if m:
            if current_bssid:
                bss_blocks.append((current_bssid, current_lines))
            current_bssid = m.group(1).upper()
            current_lines = []
        elif current_bssid is not None:
            current_lines.append(line)
    if current_bssid:
        bss_blocks.append((current_bssid, current_lines))

    networks = []
    for bssid, lines in bss_blocks:
        text = '\n'.join(lines)
        net = {
            'bssid': bssid, 'ssid': '', 'freq': 0, 'channel': '', 'band': '',
            'signal': 0, 'capability': '',
            'ht': False, 'vht': False, 'he': False, 'he_eht': False,
            'ht_secondary_offset': '', 'vht_channel_width': '',
            'vendor': OUI_MAP.get(bssid[:8], 'Unknown'),
            'wps': False, 'wps_version': '', 'wps_state': 0,
            'pmf_capable': False, 'pmf_required': False,
            'rsn': None, 'wpa': None,
        }

        # SSID
        m = re.search(r'SSID: (.*)$', text, re.MULTILINE)
        if m:
            ssid = m.group(1).strip()
            if ssid and all(c == '\x00' for c in ssid):
                ssid = ''
            net['ssid'] = ssid

        # Frequency / channel / band
        m = re.search(r'freq: (\d+)', text)
        if m:
            freq = int(m.group(1))
            net['freq'] = freq
            freq_info = FREQ_TO_CHANNEL.get(freq, {})
            net['channel'] = freq_info.get('channel', str(freq))
            if freq < 3000: net['band'] = '2.4 GHz'
            elif freq < 5900: net['band'] = '5 GHz'
            else: net['band'] = '6 GHz'

        # Signal
        m = re.search(r'signal: ([\-\d.]+)', text)
        if m:
            net['signal'] = float(m.group(1))

        # Capability
        m = re.search(r'capability: (.+)$', text, re.MULTILINE)
        if m:
            net['capability'] = m.group(1).strip()

        # Wi-Fi standards
        if re.search(r'HT capabilities:', text): net['ht'] = True
        if re.search(r'VHT capabilities:', text): net['vht'] = True
        if re.search(r'HE capabilities:', text): net['he'] = True
        if re.search(r'EHT capabilities:', text): net['he_eht'] = True

        # HT secondary channel offset
        m = re.search(r'secondary channel offset: (.+)', text)
        if m:
            net['ht_secondary_offset'] = m.group(1).strip()

        # VHT channel width
        m = re.search(r'channel width: (\d+)', text)
        if m:
            net['vht_channel_width'] = m.group(1).strip()

        # WPS
        if re.search(r'WPS:|Wi-Fi Protected Setup', text):
            net['wps'] = True
            m = re.search(r'Version: (\S+)', text)
            if m:
                net['wps_version'] = m.group(1).strip()
            m = re.search(r'Wi-Fi Protected Setup State: (\d+)', text)
            if m:
                net['wps_state'] = int(m.group(1))

        # RSN block: find all lines between "RSN:" and the next top-level section
        rsn_match = re.search(r'^\tRSN:', text, re.MULTILINE)
        if rsn_match:
            rsn_start = rsn_match.start()
            # Find where RSN block ends (next single-tab line that's not a continuation)
            rsn_lines = []
            started = False
            for line in lines:
                stripped = line.strip()
                if not started:
                    if stripped.startswith('RSN:'):
                        started = True
                        rsn_lines.append(line)
                    continue
                # RSN content lines are indented more than one tab, or start with * after tabs
                if line.startswith('\t\t') or (line.startswith('\t') and stripped.startswith('*')):
                    rsn_lines.append(line)
                elif stripped == '':
                    continue
                else:
                    break
            net['rsn'] = _parse_rsn_wpa_block(rsn_lines)

            # PMF from RSN capabilities
            if net['rsn']:
                cap_text = net['rsn'].get('capabilities', '').upper()
                # Hex format: "0x000c"
                m_hex = re.search(r'0x([0-9a-fA-F]+)', cap_text)
                if m_hex:
                    cap_val = int(m_hex.group(1), 16)
                    if cap_val & 0x0040 or cap_val & 0x0080:
                        net['pmf_capable'] = True
                    if cap_val & 0x0080:
                        net['pmf_required'] = True
                # Text format: "MFPC MFPR" or "MFP-capable"
                if 'MFPC' in cap_text or 'MFP-CAPABLE' in cap_text or 'MANAGEMENTFRAMEPROTECTION' in cap_text:
                    net['pmf_capable'] = True
                if 'MFPR' in cap_text or 'MFP-REQUIRED' in cap_text:
                    net['pmf_required'] = True

        # WPA block: same approach
        wpa_started = False
        wpa_lines = []
        for line in lines:
            stripped = line.strip()
            if not wpa_started:
                if stripped.startswith('WPA:'):
                    wpa_started = True
                    wpa_lines.append(line)
                continue
            if line.startswith('\t\t') or (line.startswith('\t') and stripped.startswith('*')):
                wpa_lines.append(line)
            elif stripped == '':
                continue
            else:
                break
        if wpa_lines:
            net['wpa'] = _parse_rsn_wpa_block(wpa_lines)

        networks.append(net)

    # Post-process each network
    results = []
    for net in networks:
        # Security protocol
        security = []
        encryption = set()
        auth = set()
        has_rsn = bool(net['rsn'])
        has_wpa = bool(net['wpa'])
        has_sae = False
        has_psk = False
        has_enterprise = False
        has_owe = False

        if net['rsn']:
            akm_str = ' '.join(net['rsn'].get('akm', []))
            if 'SAE' in akm_str:
                security.append('WPA3')
                has_sae = True
            if 'OWE' in akm_str:
                security.append('WPA3-OWE')
                has_owe = True
            if 'PSK' in akm_str:
                security.append('WPA2')
                has_psk = True
            if 'IEEE 802.1X' in akm_str or '802.1X' in akm_str:
                security.append('WPA2-Enterprise')
                has_enterprise = True
            if not security:
                security.append('WPA2')
                has_psk = True
            for c in net['rsn'].get('pairwise', []):
                encryption.add(c)
            for a in net['rsn'].get('akm', []):
                auth.add(a)

        if net['wpa']:
            security.append('WPA')
            for c in net['wpa'].get('pairwise', []):
                encryption.add(c)
            for a in net['wpa'].get('akm', []):
                auth.add(a)

        is_open = False
        is_wep = False
        if not security:
            if 'Privacy' in net.get('capability', ''):
                security.append('WEP')
                is_wep = True
            else:
                security.append('Open')
                is_open = True

        # Wi-Fi standard
        if net['he_eht']:
            standard = '802.11be (Wi-Fi 7)'
        elif net['he']:
            standard = '802.11ax (Wi-Fi 6)'
        elif net['vht']:
            standard = '802.11ac (Wi-Fi 5)'
        elif net['ht']:
            standard = '802.11n (Wi-Fi 4)'
        else:
            if net['freq'] >= 5000:
                standard = '802.11a'
            else:
                standard = '802.11b/g'

        # Bandwidth
        if net['vht_channel_width'] == '1':
            bandwidth = '80 MHz'
        elif net['vht_channel_width'] == '2':
            bandwidth = '160 MHz'
        elif net['vht_channel_width'] == '3':
            bandwidth = '80+80 MHz'
        elif net['ht_secondary_offset'] and net['ht_secondary_offset'] != 'no secondary':
            bandwidth = '40 MHz'
        else:
            bandwidth = '20 MHz'

        # --- Vulnerability Assessment ---
        vulnerabilities = []

        # CRITICAL: No encryption at all
        if is_open and not has_owe:
            vulnerabilities.append({
                'severity': 'critical',
                'id': 'OPEN_NETWORK',
                'title': 'Open network - no encryption',
                'description': 'All traffic is transmitted in plaintext. Any device within range can intercept all data including credentials, emails, and browsing activity.',
                'recommendation': 'Enable WPA3-SAE or WPA2-PSK encryption. If this is a guest network, consider WPA3-OWE (Opportunistic Wireless Encryption) for encryption without a password.'
            })

        # CRITICAL: WEP encryption
        if is_wep:
            vulnerabilities.append({
                'severity': 'critical',
                'id': 'WEP_ENCRYPTION',
                'title': 'WEP encryption - cryptographically broken',
                'description': 'WEP uses RC4 with 24-bit IVs. It can be cracked in minutes by passively collecting packets (PTW/FMS/KoreK attacks). Tools like aircrack-ng automate this completely.',
                'recommendation': 'Upgrade immediately to WPA2-PSK (AES) or WPA3-SAE. WEP offers effectively no security.'
            })

        # HIGH: WPA with TKIP only
        if has_wpa and not has_rsn:
            vulnerabilities.append({
                'severity': 'high',
                'id': 'WPA_TKIP_ONLY',
                'title': 'WPA (TKIP) only - deprecated protocol',
                'description': 'WPA-TKIP has known cryptographic weaknesses. The Beck-Tews and Ohigashi-Morii attacks can decrypt short packets and inject forged frames. TKIP was deprecated by the Wi-Fi Alliance in 2012.',
                'recommendation': 'Upgrade to WPA2 (AES/CCMP) or WPA3-SAE.'
            })

        # HIGH: TKIP cipher still in use (even alongside CCMP)
        if 'TKIP' in encryption and ('CCMP' in encryption or 'CCMP-128' in encryption):
            vulnerabilities.append({
                'severity': 'high',
                'id': 'TKIP_MIXED_MODE',
                'title': 'TKIP cipher enabled alongside AES',
                'description': 'TKIP is still accepted as a pairwise cipher. A downgrade attack can force clients to use TKIP instead of the stronger CCMP/AES, exposing them to TKIP cryptographic weaknesses.',
                'recommendation': 'Disable TKIP and use CCMP/AES only in the AP configuration.'
            })

        # HIGH: WPA2-PSK without PMF (vulnerable to deauth + handshake capture)
        if has_psk and not has_sae and not net['pmf_required']:
            vulnerabilities.append({
                'severity': 'high',
                'id': 'WPA2_NO_PMF',
                'title': 'WPA2-PSK without mandatory PMF',
                'description': 'Without Protected Management Frames (802.11w), an attacker can send forged deauthentication frames to force clients to disconnect and reconnect. The captured 4-way handshake can then be brute-forced offline with tools like hashcat.',
                'recommendation': 'Enable PMF (802.11w) as required in AP settings. Upgrade to WPA3-SAE which mandates PMF.'
            })

        # HIGH: WPA/WPA2 mixed mode - downgrade attack
        if has_wpa and has_rsn and not has_sae:
            vulnerabilities.append({
                'severity': 'high',
                'id': 'WPA_WPA2_MIXED',
                'title': 'WPA/WPA2 mixed mode - downgrade possible',
                'description': 'The AP accepts both WPA (TKIP) and WPA2 (AES). An attacker can perform a downgrade attack by manipulating the handshake to force clients onto the weaker WPA-TKIP protocol.',
                'recommendation': 'Disable WPA and use WPA2-only or WPA3-only mode.'
            })

        # MEDIUM: WPA3 transition mode (SAE + PSK)
        if has_sae and has_psk:
            vulnerabilities.append({
                'severity': 'medium',
                'id': 'WPA3_TRANSITION_MODE',
                'title': 'WPA3 transition mode - downgrade to WPA2 possible',
                'description': 'The AP advertises both WPA3-SAE and WPA2-PSK. An attacker can set up a rogue AP that only offers WPA2-PSK, forcing clients to connect without SAE protections. The captured WPA2 handshake can then be brute-forced offline.',
                'recommendation': 'Switch to WPA3-only mode once all clients support WPA3. If transition mode is necessary, ensure PMF is required.'
            })

        # MEDIUM: WPS enabled
        if net['wps']:
            wps_desc = 'WPS PIN mode is vulnerable to brute-force attacks (Reaver). The 8-digit PIN is validated in two halves, reducing the keyspace from 100 million to ~11,000 attempts. The Pixie Dust attack can crack WPS offline in seconds on many chipsets.'
            if net.get('wps_version'):
                wps_desc += f' WPS version: {net["wps_version"]}.'
                if net['wps_version'] in ('1.0', '1', '0x10', '10'):
                    wps_desc += ' Version 1.0 has no lockout protection against brute-force.'
            vulnerabilities.append({
                'severity': 'medium',
                'id': 'WPS_ENABLED',
                'title': 'WPS (Wi-Fi Protected Setup) enabled',
                'description': wps_desc,
                'recommendation': 'Disable WPS entirely in AP settings. If WPS push-button is needed, ensure WPS PIN mode is disabled.'
            })

        # LOW: WPS unconfigured state
        if net['wps'] and net.get('wps_state') == 1:
            vulnerabilities.append({
                'severity': 'low',
                'id': 'WPS_UNCONFIGURED',
                'title': 'WPS in unconfigured state',
                'description': 'WPS is in unconfigured state (state 1). An external registrar can configure the AP via WPS, potentially taking control of the network.',
                'recommendation': 'Configure the AP through its management interface and disable WPS.'
            })

        # MEDIUM: No PMF at all (even capable) on WPA2
        if has_psk and not net['pmf_capable'] and not net['pmf_required'] and not has_sae:
            vulnerabilities.append({
                'severity': 'medium',
                'id': 'NO_PMF_SUPPORT',
                'title': 'No PMF (802.11w) support',
                'description': 'The AP does not support Protected Management Frames at all. Management frames (deauth, disassoc, beacon) can be freely spoofed, enabling denial-of-service attacks and evil twin setups.',
                'recommendation': 'Enable PMF support on the AP. Set to "capable" for backward compatibility or "required" for maximum security.'
            })

        # MEDIUM: WPA2-PSK with PMF capable but not required
        if has_psk and net['pmf_capable'] and not net['pmf_required'] and not has_sae:
            vulnerabilities.append({
                'severity': 'medium',
                'id': 'PMF_NOT_REQUIRED',
                'title': 'PMF capable but not required',
                'description': 'PMF is optional. Clients that do not support PMF will connect without it, leaving them vulnerable to deauthentication attacks and handshake capture.',
                'recommendation': 'Set PMF to required if all clients support it. This enforces management frame protection for all connections.'
            })

        # LOW: Hidden SSID
        if not net['ssid']:
            vulnerabilities.append({
                'severity': 'low',
                'id': 'HIDDEN_SSID',
                'title': 'Hidden SSID - false sense of security',
                'description': 'The SSID is hidden from beacons, but it is exposed in probe requests/responses when clients connect. Any passive monitoring reveals the SSID. Additionally, clients configured for hidden networks continuously broadcast probe requests for the network, which is a privacy leak.',
                'recommendation': 'Make the SSID visible. Hidden SSIDs provide no real security benefit and reduce client privacy.'
            })

        # LOW: Legacy Wi-Fi standard
        if standard in ('802.11a', '802.11b/g'):
            vulnerabilities.append({
                'severity': 'low',
                'id': 'LEGACY_STANDARD',
                'title': f'Legacy Wi-Fi standard ({standard})',
                'description': 'This AP uses a very old Wi-Fi standard, which may indicate outdated firmware that lacks patches for known vulnerabilities (KRACK, FragAttacks, etc.).',
                'recommendation': 'Consider upgrading to modern AP hardware supporting Wi-Fi 5 (802.11ac) or Wi-Fi 6 (802.11ax) with up-to-date firmware.'
            })

        # INFO: WPA2-PSK (general offline brute-force risk)
        if has_psk and not has_sae and not is_wep and not is_open:
            vulnerabilities.append({
                'severity': 'info',
                'id': 'WPA2_PSK_BRUTEFORCE',
                'title': 'WPA2-PSK susceptible to offline brute-force',
                'description': 'WPA2-PSK handshakes can be captured and cracked offline. The security depends entirely on password strength. Short or dictionary-based passwords can be cracked in hours with GPU-accelerated tools like hashcat.',
                'recommendation': 'Use a strong passphrase (15+ random characters). Consider upgrading to WPA3-SAE which is immune to offline brute-force attacks.'
            })

        # INFO: No WPA3 support
        if has_rsn and not has_sae and not has_owe and not is_open and not is_wep:
            vulnerabilities.append({
                'severity': 'info',
                'id': 'NO_WPA3',
                'title': 'No WPA3 support detected',
                'description': 'This AP does not advertise WPA3 (SAE). WPA3 provides stronger key exchange, forward secrecy, and mandatory PMF.',
                'recommendation': 'If AP hardware supports it, enable WPA3-SAE or WPA3 transition mode.'
            })

        # MEDIUM: Group cipher is TKIP
        if net['rsn'] and net['rsn'].get('group', '').upper() == 'TKIP':
            vulnerabilities.append({
                'severity': 'medium',
                'id': 'GROUP_CIPHER_TKIP',
                'title': 'Group cipher is TKIP',
                'description': 'Broadcast and multicast traffic is encrypted with TKIP, which has known cryptographic weaknesses, even though unicast may use AES.',
                'recommendation': 'Set group cipher to CCMP (AES) in AP configuration.'
            })

        # MEDIUM: Default SSID detected
        default_patterns = [
            'linksys', 'NETGEAR', 'netgear', 'dlink', 'D-Link', 'TP-LINK_', 'TP-Link_',
            'ASUS_', 'ASUS ', 'HUAWEI-', 'default', 'HOME-', 'SETUP',
            'AndroidAP', 'DIRECT-', 'HP-Print-', 'FRITZ!Box', 'Vodafone-',
            'xfinitywifi', 'ATT', 'Verizon', 'ARRIS', 'Actiontec', 'CenturyLink',
            'MySpectrumWiFi', 'ORBI', 'UPC', 'Telstra', 'Optus',
        ]
        ssid_name = net['ssid'] if net['ssid'] else ''
        is_default_ssid = any(ssid_name.startswith(p) or ssid_name.lower() == p.lower() for p in default_patterns)
        if is_default_ssid and ssid_name:
            vulnerabilities.append({
                'severity': 'medium',
                'id': 'DEFAULT_SSID',
                'title': 'Default SSID detected',
                'description': f'SSID "{ssid_name}" appears to be a factory default. Default configurations often include default passwords and unhardened settings.',
                'recommendation': 'Change SSID to a custom name and verify all security settings have been configured.'
            })

        # LOW: SSID reveals identifying information
        identify_patterns = [
            r'\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP-like
            r'(?i)(office|floor|room|building|dept|level|reception|boardroom|warehouse|store)\s*\d',
            r'(?i)(router|switch|ap|access.point|repeater|extender)\b',
        ]
        if ssid_name:
            for pat in identify_patterns:
                if re.search(pat, ssid_name):
                    vulnerabilities.append({
                        'severity': 'low',
                        'id': 'SSID_INFO_LEAK',
                        'title': 'SSID reveals infrastructure information',
                        'description': f'SSID "{ssid_name}" contains location, device, or organisational information that aids reconnaissance.',
                        'recommendation': 'Use generic SSID names that do not reveal internal infrastructure details.'
                    })
                    break

        # Count by severity
        sev_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        for v in vulnerabilities:
            sev_counts[v['severity']] = sev_counts.get(v['severity'], 0) + 1

        results.append({
            'ssid': net['ssid'] if net['ssid'] else '(Hidden)',
            'bssid': net['bssid'],
            'channel': net['channel'],
            'band': net['band'],
            'signal': net['signal'],
            'security': '/'.join(security),
            'encryption': ', '.join(sorted(encryption)) if encryption else 'None',
            'auth': ', '.join(sorted(auth)) if auth else 'None',
            'standard': standard,
            'bandwidth': bandwidth,
            'vendor': net['vendor'],
            'pmf': 'Required' if net['pmf_required'] else ('Capable' if net['pmf_capable'] else 'No'),
            'wps': net['wps'],
            'vulnerabilities': vulnerabilities,
            'vuln_counts': sev_counts,
        })

    # --- Cross-network security checks ---

    # Group results by SSID for cross-network analysis
    ssid_groups = {}
    for r in results:
        ssid_name = r['ssid']
        if ssid_name and ssid_name != '(Hidden)':
            ssid_groups.setdefault(ssid_name, []).append(r)

    for ssid_name, nets in ssid_groups.items():
        if len(nets) < 2:
            continue

        # CHECK: Same SSID with different security settings (rogue AP indicator)
        security_set = set(n['security'] for n in nets)
        if len(security_set) > 1:
            sec_list = ', '.join(sorted(security_set))
            bssids_involved = [n['bssid'] for n in nets]
            for n in nets:
                n['vulnerabilities'].append({
                    'severity': 'high',
                    'id': 'ROGUE_AP_SECURITY_MISMATCH',
                    'title': f'SSID "{ssid_name}" has mismatched security',
                    'description': f'Same SSID seen with different security: {sec_list}. BSSIDs: {", ".join(bssids_involved[:5])}. This may indicate a rogue AP or misconfiguration.',
                    'recommendation': 'Verify all APs for this SSID have identical security settings. Investigate unknown BSSIDs.'
                })
                n['vuln_counts']['high'] = n['vuln_counts'].get('high', 0) + 1

        # CHECK: Same SSID from different vendors (rogue AP indicator)
        vendor_set = set(n['vendor'] for n in nets if n['vendor'] != 'Unknown')
        if len(vendor_set) > 1:
            vendor_list = ', '.join(sorted(vendor_set))
            for n in nets:
                n['vulnerabilities'].append({
                    'severity': 'medium',
                    'id': 'ROGUE_AP_VENDOR_MISMATCH',
                    'title': f'SSID "{ssid_name}" from multiple vendors',
                    'description': f'Same SSID seen from different hardware vendors: {vendor_list}. May indicate a rogue or unauthorised AP.',
                    'recommendation': 'Verify all APs are part of the authorised deployment. Investigate unknown vendor BSSIDs.'
                })
                n['vuln_counts']['medium'] = n['vuln_counts'].get('medium', 0) + 1

        # CHECK: Same SSID with suspiciously similar BSSIDs (MAC spoofing)
        bssid_list = [n['bssid'] for n in nets]
        for i in range(len(bssid_list)):
            for j in range(i + 1, len(bssid_list)):
                b1 = bssid_list[i].replace(':', '')
                b2 = bssid_list[j].replace(':', '')
                if len(b1) == 12 and len(b2) == 12:
                    diff_bits = sum(c1 != c2 for c1, c2 in zip(b1, b2))
                    if diff_bits == 1:
                        for n in nets:
                            if n['bssid'] in (bssid_list[i], bssid_list[j]):
                                n['vulnerabilities'].append({
                                    'severity': 'medium',
                                    'id': 'SUSPICIOUS_BSSID_SIMILARITY',
                                    'title': 'Suspiciously similar BSSIDs',
                                    'description': f'BSSIDs {bssid_list[i]} and {bssid_list[j]} differ by only 1 nibble. One may be a cloned/spoofed AP.',
                                    'recommendation': 'Verify both BSSIDs belong to legitimate infrastructure.'
                                })
                                n['vuln_counts']['medium'] = n['vuln_counts'].get('medium', 0) + 1

    # Sort by signal strength descending
    results.sort(key=lambda x: x['signal'], reverse=True)
    return results

def get_monitor_adapter():
    """Find a monitor-mode adapter for scanning. Returns interface name or None."""
    try:
        interfaces = get_interfaces_info()
        for i in interfaces:
            if i['type'] == 'monitor' and i['interface'].startswith('wlan'):
                return i['interface']
    except Exception:
        pass
    return None


def scan_with_monitor(adapter, duration=6):
    """
    Scan using monitor adapter. Queries adapter's real supported frequencies,
    hops only through those, captures with dumpcap, parses with tshark.
    """
    # Find the phy for this adapter
    phy_name = None
    try:
        interfaces = get_interfaces_info()
        for iface in interfaces:
            if iface['interface'] == adapter:
                phy_name = iface['phy'].replace('#', '')
                break
    except Exception:
        pass

    # Get the adapter's actual supported frequencies (only non-disabled ones)
    scan_freqs = []
    if phy_name:
        bands, _ = _get_phy_bands(phy_name)
        # Pick representative channels: for 2.4 GHz use 1,6,11; for 5/6 GHz one per 80 MHz group
        for band_name, channels in bands.items():
            freqs = [ch['freq'] for ch in channels]
            if '2.4' in band_name:
                # Channels 1, 6, 11 (2412, 2437, 2462)
                for target in [2412, 2437, 2462]:
                    if target in freqs:
                        scan_freqs.append((target, 'HT20'))
            else:
                # One frequency per 80 MHz group
                seen_groups = set()
                for f in sorted(freqs):
                    group = f // 80  # rough 80 MHz grouping
                    if group not in seen_groups:
                        seen_groups.add(group)
                        bw = '80MHz' if f >= 5000 else 'HT20'
                        scan_freqs.append((f, bw))

    # Fallback if we couldn't detect frequencies
    if not scan_freqs:
        scan_freqs = [(2412, 'HT20'), (2437, 'HT20'), (2462, 'HT20')]

    dwell_ms = max(400, int((duration * 1000) / len(scan_freqs)))
    pcap_path = f'/tmp/wifi_scan_{uuid.uuid4().hex[:8]}.pcap'

    try:
        # Set to first frequency (known good) before starting capture
        first_freq, first_bw = scan_freqs[0]
        subprocess.run(['sudo', 'iw', 'dev', adapter, 'set', 'freq', str(first_freq), first_bw],
                       capture_output=True, text=True, timeout=2)
        time.sleep(0.1)

        # Start dumpcap in background via shell, hop channels, then stop
        shell_cmd = f'timeout {duration} dumpcap -i {adapter} -w {pcap_path} -q 2>/dev/null &'
        subprocess.run(shell_cmd, shell=True, timeout=3)
        time.sleep(0.5)

        # Hop through supported channels while dumpcap captures
        for freq, bw in scan_freqs:
            try:
                subprocess.run(['sudo', 'iw', 'dev', adapter, 'set', 'freq', str(freq), bw],
                               capture_output=True, text=True, timeout=2)
            except Exception:
                pass
            time.sleep(dwell_ms / 1000.0)

        # Wait for dumpcap to finish (timeout command kills it)
        time.sleep(1)

        # If pcap is empty or missing, return empty
        pcap_size = 0
        try:
            pcap_size = os.path.getsize(pcap_path)
        except OSError:
            pass
        if pcap_size < 100:
            return [], adapter

        # Parse beacons AND probe responses
        rows = run_tshark(pcap_path,
            'wlan.fc.type_subtype == 0x0008 || wlan.fc.type_subtype == 0x0005', [
            'wlan.bssid', 'wlan.ssid', 'radiotap.channel.freq',
            'radiotap.dbm_antsignal',
            'wlan.rsn.akms.type', 'wlan.rsn.pcs.type',
            'wlan.wfa.ie.wpa.akms.type', 'wlan.wfa.ie.wpa.pcs.type',
            'wlan.fixed.capabilities.privacy',
            'wlan.ht.capabilities', 'wlan.vht.capabilities',
            'wlan.tag.number', 'wlan.rsn.capabilities',
        ], timeout=30)

        # Deduplicate by BSSID, keep strongest signal
        bssid_map = {}
        for r in rows:
            b = r.get('wlan.bssid', '').upper()
            if not b or b == 'FF:FF:FF:FF:FF:FF':
                continue

            rssi_str = r.get('radiotap.dbm_antsignal', '')
            try:
                rssi = int(rssi_str.split(',')[0]) if rssi_str else -100
            except (ValueError, IndexError):
                rssi = -100

            if b in bssid_map and bssid_map[b]['signal'] >= rssi:
                # Keep existing if stronger, but fill in missing fields
                existing = bssid_map[b]
                if not existing['ssid'] and r.get('wlan.ssid'):
                    existing['ssid'] = r['wlan.ssid']
                continue

            freq_str = r.get('radiotap.channel.freq', '')
            try:
                freq = int(float(freq_str)) if freq_str else 0
            except ValueError:
                freq = 0

            band = ''
            if 0 < freq < 3000: band = '2.4 GHz'
            elif freq < 5900: band = '5 GHz'
            elif freq > 0: band = '6 GHz'

            ch = FREQ_TO_CHANNEL.get(freq, {}).get('channel', '') if freq else ''

            # Security from RSN/WPA fields
            rsn_akm = r.get('wlan.rsn.akms.type', '')
            rsn_pcs = r.get('wlan.rsn.pcs.type', '')
            wpa_akm = r.get('wlan.wfa.ie.wpa.akms.type', '')
            wpa_pcs = r.get('wlan.wfa.ie.wpa.pcs.type', '')
            privacy = r.get('wlan.fixed.capabilities.privacy', '')

            has_rsn = bool(rsn_akm or rsn_pcs)
            has_wpa_ie = bool(wpa_akm or wpa_pcs)

            # Build security string
            security = []
            encryption = set()
            auth = set()
            has_sae = False
            has_psk = False
            has_enterprise = False

            if rsn_akm:
                for t in rsn_akm.split(','):
                    t = t.strip()
                    if t == '8': security.append('WPA3'); has_sae = True
                    elif t == '2': security.append('WPA2'); has_psk = True
                    elif t == '1': security.append('WPA2-Enterprise'); has_enterprise = True
                    elif t == '6': security.append('WPA2'); has_psk = True
                    elif t == '18': security.append('WPA3-OWE')
                    elif t in ('3', '4'): security.append('FT')
                for t in rsn_pcs.split(','):
                    t = t.strip()
                    if t == '4': encryption.add('CCMP')
                    elif t == '2': encryption.add('TKIP')
                auth.update(a.strip() for a in rsn_akm.split(',') if a.strip())

            if wpa_akm:
                security.append('WPA')
                for t in wpa_pcs.split(','):
                    t = t.strip()
                    if t == '4': encryption.add('CCMP')
                    elif t == '2': encryption.add('TKIP')
                auth.update(a.strip() for a in wpa_akm.split(',') if a.strip())

            if not security:
                if privacy == '1':
                    security.append('WEP')
                else:
                    security.append('Open')

            # Wi-Fi generation
            has_ht = bool(r.get('wlan.ht.capabilities'))
            has_vht = bool(r.get('wlan.vht.capabilities'))
            tags = set(r.get('wlan.tag.number', '').split(',')) if r.get('wlan.tag.number') else set()
            has_he = '255' in tags

            if has_he: standard = '802.11ax (Wi-Fi 6)'
            elif has_vht: standard = '802.11ac (Wi-Fi 5)'
            elif has_ht: standard = '802.11n (Wi-Fi 4)'
            elif freq >= 5000: standard = '802.11a'
            else: standard = '802.11b/g'

            # PMF from RSN capabilities
            pmf_capable = False
            pmf_required = False
            rsn_cap_str = r.get('wlan.rsn.capabilities', '')
            if rsn_cap_str:
                try:
                    cap_val = int(rsn_cap_str, 0)
                    if cap_val & 0x0040: pmf_capable = True
                    if cap_val & 0x0080: pmf_required = True; pmf_capable = True
                except ValueError:
                    pass

            pmf = 'Required' if pmf_required else ('Capable' if pmf_capable else 'No')

            # Vulnerability assessment (simplified for monitor scan)
            vulnerabilities = []
            vuln_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}

            is_open = 'Open' in security
            is_wep = 'WEP' in security

            if is_open and 'WPA3-OWE' not in security:
                vulnerabilities.append({'severity': 'critical', 'id': 'OPEN_NETWORK',
                    'title': 'Open network - no encryption',
                    'description': 'All traffic in plaintext. Any device in range can intercept data.',
                    'recommendation': 'Enable WPA3-SAE or WPA2-PSK.'})
                vuln_counts['critical'] += 1
            if is_wep:
                vulnerabilities.append({'severity': 'critical', 'id': 'WEP_ENCRYPTION',
                    'title': 'WEP encryption - cryptographically broken',
                    'description': 'Can be cracked in minutes.',
                    'recommendation': 'Upgrade to WPA2/WPA3.'})
                vuln_counts['critical'] += 1
            if has_psk and not has_sae and not pmf_required:
                vulnerabilities.append({'severity': 'high', 'id': 'WPA2_NO_PMF',
                    'title': 'WPA2-PSK without mandatory PMF',
                    'description': 'Deauth attack + handshake capture possible.',
                    'recommendation': 'Enable PMF or upgrade to WPA3-SAE.'})
                vuln_counts['high'] += 1

            sec_str = '/'.join(sorted(set(security)))
            if encryption:
                sec_str += f' ({"/".join(sorted(encryption))})'

            ssid_name = r.get('wlan.ssid', '')
            if not ssid_name:
                ssid_name = '(Hidden)'

            bssid_map[b] = {
                'ssid': ssid_name,
                'bssid': b,
                'channel': ch,
                'band': band,
                'signal': rssi,
                'security': sec_str,
                'encryption': ', '.join(sorted(encryption)) if encryption else 'None',
                'auth': ', '.join(sorted(auth)) if auth else 'None',
                'standard': standard,
                'bandwidth': '80 MHz' if has_vht else ('40 MHz' if has_ht else '20 MHz'),
                'vendor': OUI_MAP.get(b[:8], 'Unknown'),
                'pmf': pmf,
                'wps': False,  # Can't reliably detect WPS from beacon tshark fields
                'vulnerabilities': vulnerabilities,
                'vuln_counts': vuln_counts,
                'freq': freq,
            }

        networks = sorted(bssid_map.values(), key=lambda n: n['signal'], reverse=True)
        return networks, adapter

    finally:
        try:
            os.unlink(pcap_path)
        except Exception:
            pass


@app.route('/networks')
def networks_page():
    return app.send_static_file('networks.html')

@app.route('/scan', methods=['GET'])
def scan_networks():
    """Default scan: always uses iw dev wlan0 scan (reliable, fast).
    Use /scan/monitor for the monitor-mode adapter scan."""
    if not scan_lock.acquire(blocking=False):
        return jsonify({'error': 'Scan already in progress'}), 429
    try:
        result = subprocess.run(
            ['sudo', 'iw', 'dev', 'wlan0', 'scan'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return jsonify({'error': result.stderr.strip() or 'Scan failed'}), 500
        networks = parse_iw_scan(result.stdout)
        local_tz = get_localzone()
        local_tz = pytz.timezone(str(local_tz))
        utc_now = datetime.now(pytz.UTC)
        local_now = utc_now.astimezone(local_tz)
        return jsonify({
            'networks': networks,
            'timestamp': local_now.strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(networks),
            'scan_method': 'iw',
            'adapter': 'wlan0',
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Scan timed out'}), 504
    finally:
        scan_lock.release()

@app.route('/scan/monitor', methods=['GET'])
def scan_networks_monitor():
    """Scan using the monitor-mode adapter (wlan1mon). Slower but sees all bands."""
    mon_adapter = get_monitor_adapter()
    if not mon_adapter:
        return jsonify({'error': 'No monitor-mode adapter found. Put an adapter in monitor mode first.'}), 400
    if not scan_lock.acquire(blocking=False):
        return jsonify({'error': 'Scan already in progress'}), 429
    try:
        networks, adapter_used = scan_with_monitor(mon_adapter, duration=5)
        local_tz = get_localzone()
        local_tz = pytz.timezone(str(local_tz))
        utc_now = datetime.now(pytz.UTC)
        local_now = utc_now.astimezone(local_tz)
        return jsonify({
            'networks': networks,
            'timestamp': local_now.strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(networks),
            'scan_method': 'monitor',
            'adapter': adapter_used,
        })
    except Exception as e:
        return jsonify({'error': f'Monitor scan failed: {str(e)}'}), 500
    finally:
        scan_lock.release()

@app.route('/scan/debug', methods=['GET'])
def scan_debug():
    """Step-by-step debug: tests each part of the monitor scan individually."""
    mon_adapter = get_monitor_adapter()
    steps = []
    pcap_path = f'/tmp/wifi_debug_{uuid.uuid4().hex[:8]}.pcap'

    steps.append({'step': 'detect_adapter', 'adapter': mon_adapter})

    if not mon_adapter:
        steps.append({'step': 'no_monitor', 'msg': 'No monitor adapter found'})
        return jsonify({'steps': steps})

    # Step 1: set channel
    try:
        r = subprocess.run(['sudo', 'iw', 'dev', mon_adapter, 'set', 'freq', '2437', 'HT20'],
                           capture_output=True, text=True, timeout=3)
        steps.append({'step': 'set_channel', 'ok': r.returncode == 0, 'stderr': r.stderr.strip()})
    except Exception as e:
        steps.append({'step': 'set_channel', 'ok': False, 'error': str(e)})

    # Step 2: run dumpcap for 3 seconds (BLOCKING, no background, no shell)
    try:
        r = subprocess.run(['dumpcap', '-i', mon_adapter, '-w', pcap_path, '-a', 'duration:3', '-q'],
                           capture_output=True, text=True, timeout=10)
        steps.append({'step': 'dumpcap', 'ok': r.returncode == 0,
                      'stdout': r.stdout[:500], 'stderr': r.stderr[:500]})
    except Exception as e:
        steps.append({'step': 'dumpcap', 'ok': False, 'error': str(e)})

    # Step 3: check file
    try:
        size = os.path.getsize(pcap_path)
        steps.append({'step': 'pcap_file', 'exists': True, 'size_bytes': size})
    except OSError:
        steps.append({'step': 'pcap_file', 'exists': False})
        return jsonify({'steps': steps})

    # Step 4: tshark - show ALL frame types in the pcap
    try:
        r = subprocess.run(['tshark', '-r', pcap_path, '-T', 'fields', '-e', 'wlan.fc.type_subtype'],
                           capture_output=True, text=True, timeout=10)
        frame_types = {}
        for line in r.stdout.strip().split('\n'):
            t = line.strip()
            if t:
                frame_types[t] = frame_types.get(t, 0) + 1
        steps.append({'step': 'frame_types', 'types': frame_types, 'total_frames': sum(frame_types.values())})
    except Exception as e:
        steps.append({'step': 'frame_types', 'error': str(e)})

    # Step 5: tshark - extract beacons specifically
    try:
        r = subprocess.run(['tshark', '-r', pcap_path,
                           '-Y', 'wlan.fc.type_subtype == 0x0008',
                           '-T', 'fields', '-e', 'wlan.bssid', '-e', 'wlan.ssid'],
                           capture_output=True, text=True, timeout=10)
        beacon_lines = [l for l in r.stdout.strip().split('\n') if l.strip()]
        steps.append({'step': 'beacons', 'count': len(beacon_lines),
                      'first_5': beacon_lines[:5], 'stderr': r.stderr[:300]})
    except Exception as e:
        steps.append({'step': 'beacons', 'error': str(e)})

    # Step 6: tshark - extract probe responses
    try:
        r = subprocess.run(['tshark', '-r', pcap_path,
                           '-Y', 'wlan.fc.type_subtype == 0x0005',
                           '-T', 'fields', '-e', 'wlan.bssid', '-e', 'wlan.ssid'],
                           capture_output=True, text=True, timeout=10)
        probe_lines = [l for l in r.stdout.strip().split('\n') if l.strip()]
        steps.append({'step': 'probe_responses', 'count': len(probe_lines),
                      'first_5': probe_lines[:5]})
    except Exception as e:
        steps.append({'step': 'probe_responses', 'error': str(e)})

    # Cleanup
    try:
        os.unlink(pcap_path)
    except Exception:
        pass

    return jsonify({'steps': steps})

# --- Pcap Analyzer ---

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
UPLOAD_DIR = os.path.join(RUNNING_HOME, 'analyzer_uploads')

analyzer_sessions = {}

VENDOR_GROUPING = {
    'meraki':   {'start': 0, 'length': 4},
    'ubiquiti': {'start': 0, 'length': 4},
    'cisco':    {'start': 0, 'length': 5},
    'aruba':    {'start': 0, 'length': 4},
    'mist':     {'start': 0, 'length': 4},
    'generic':  {'start': 1, 'length': 4},
}

def run_tshark(pcap_path, display_filter, fields, timeout=600):
    cmd = ['tshark', '-r', pcap_path, '-Y', display_filter,
           '-T', 'fields', '-E', 'separator=\t', '-E', 'occurrence=a']
    for f in fields:
        cmd.extend(['-e', f])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return []
        rows = []
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split('\t')
            while len(parts) < len(fields):
                parts.append('')
            rows.append(dict(zip(fields, parts)))
        return rows
    except Exception:
        return []

def detect_eapol_msg(key_info_str):
    try:
        ki = int(key_info_str, 0)
    except (ValueError, TypeError):
        return 0
    ack = bool(ki & 0x0080)
    mic = bool(ki & 0x0100)
    install = bool(ki & 0x0040)
    secure = bool(ki & 0x0200)
    if ack and not mic: return 1
    if not ack and mic and not install and not secure: return 2
    if ack and mic and install: return 3
    if not ack and mic and secure: return 4
    return 0

def ts_to_uptime(timestamp_us):
    try:
        ts = int(timestamp_us)
    except (ValueError, TypeError):
        return ''
    s = ts / 1_000_000
    d = int(s // 86400)
    h = int((s % 86400) // 3600)
    m = int((s % 3600) // 60)
    if d > 0: return f"{d}d {h}h {m}m"
    if h > 0: return f"{h}h {m}m"
    return f"{m}m"

def is_random_mac(mac):
    try:
        return bool(int(mac.split(':')[0], 16) & 0x02)
    except (ValueError, IndexError):
        return False

def group_bssids(bssids, vendor='generic'):
    p = VENDOR_GROUPING.get(vendor, VENDOR_GROUPING['generic'])
    groups = {}
    for bssid in bssids:
        octets = bssid.upper().split(':')
        if len(octets) != 6:
            continue
        key = ':'.join(octets[p['start']:p['start']+p['length']])
        groups.setdefault(key, []).append(bssid)
    return groups

def determine_security(rsn_akm, rsn_pcs, wpa_akm, wpa_pcs, privacy):
    parts = []
    cipher = set()
    if rsn_akm:
        for t in rsn_akm.split(','):
            t = t.strip()
            if t == '2': parts.append('WPA2-PSK')
            elif t == '1': parts.append('WPA2-Enterprise')
            elif t == '8': parts.append('WPA3-SAE')
            elif t == '6': parts.append('WPA2-PSK-SHA256')
            elif t == '18': parts.append('WPA3-OWE')
            elif t in ('3', '4'): parts.append('FT')
    if wpa_akm:
        parts.append('WPA')
    if not parts:
        parts.append('WEP' if privacy == '1' else 'Open')
    for src in (rsn_pcs, wpa_pcs):
        if src:
            for t in src.split(','):
                t = t.strip()
                if t == '4': cipher.add('CCMP')
                elif t == '2': cipher.add('TKIP')
    result = '/'.join(sorted(set(parts)))
    if cipher:
        result += f' ({"/".join(sorted(cipher))})'
    return result

def cleanup_old_sessions():
    cutoff = time.time() - 3600
    for sid in list(analyzer_sessions.keys()):
        s = analyzer_sessions[sid]
        try:
            upload_t = datetime.fromisoformat(s.get('upload_time', '')).timestamp()
            if upload_t < cutoff:
                pcap = s.get('pcap_path', '')
                if pcap and os.path.exists(pcap):
                    os.remove(pcap)
                del analyzer_sessions[sid]
        except Exception:
            pass

def phase1_processing(session_id):
    sess = analyzer_sessions.get(session_id)
    if not sess:
        return
    pcap = sess['pcap_path']

    try:
        # Pass 1: Beacons
        sess['progress'] = 'Extracting beacons...'
        sess['progress_pct'] = 5
        rows = run_tshark(pcap, 'wlan.fc.type_subtype == 0x0008', [
            'wlan.bssid', 'wlan.ssid', 'radiotap.channel.freq',
            'wlan.fixed.timestamp', 'wlan.fixed.capabilities.privacy'
        ])

        bmap = {}
        for r in rows:
            b = r['wlan.bssid'].upper()
            if not b or b == 'FF:FF:FF:FF:FF:FF':
                continue
            if b not in bmap:
                bmap[b] = {'bssid': b, 'ssid': r['wlan.ssid'],
                           'freq': r['radiotap.channel.freq'],
                           'timestamp': r['wlan.fixed.timestamp'],
                           'privacy': r['wlan.fixed.capabilities.privacy'],
                           'beacon_count': 0}
            bmap[b]['beacon_count'] += 1
            if r['wlan.ssid'] and not bmap[b]['ssid']:
                bmap[b]['ssid'] = r['wlan.ssid']
            if r['wlan.fixed.timestamp']:
                try:
                    if int(r['wlan.fixed.timestamp']) > int(bmap[b]['timestamp'] or '0'):
                        bmap[b]['timestamp'] = r['wlan.fixed.timestamp']
                except ValueError:
                    pass

        sess['bssid_map'] = bmap
        sess['total_bssids'] = len(bmap)

        ssid_set = {info['ssid'] for info in bmap.values() if info['ssid']}

        # Pass 2: Probe responses (hidden SSID deanonymization)
        sess['progress'] = 'Deanonymising hidden SSIDs...'
        sess['progress_pct'] = 8
        probe_rows = run_tshark(pcap, 'wlan.fc.type_subtype == 0x0005', ['wlan.bssid', 'wlan.ssid'])

        hidden_bssids = {b for b, info in bmap.items() if not info['ssid']}
        hidden_found = {}
        for r in probe_rows:
            b = r['wlan.bssid'].upper()
            ssid = r['wlan.ssid']
            if b in hidden_bssids and ssid:
                hidden_found[b] = ssid
                bmap[b]['ssid'] = ssid
                ssid_set.add(ssid)

        sess['hidden_ssids'] = hidden_found
        sess['hidden_count'] = len(hidden_found)
        sess['ssid_list'] = sorted(ssid_set)

        # Pass 3: EAPOL
        sess['progress'] = 'Analysing EAPOL handshakes...'
        sess['progress_pct'] = 12
        eapol_rows = run_tshark(pcap, 'eapol', [
            'wlan.sa', 'wlan.da', 'wlan.bssid', 'eapol.keydes.key_info', 'frame.time_epoch'
        ])

        eapol_by_pair = {}
        for r in eapol_rows:
            sa = r['wlan.sa'].upper()
            bssid = r['wlan.bssid'].upper()
            msg = detect_eapol_msg(r['eapol.keydes.key_info'])
            if not sa or not bssid or msg == 0:
                continue
            key = f"{sa}_{bssid}"
            eapol_by_pair.setdefault(key, {'client': sa, 'bssid': bssid, 'msgs': []})
            eapol_by_pair[key]['msgs'].append(msg)

        eapol_events = []
        for data in eapol_by_pair.values():
            msgs = data['msgs']
            msg12 = sum(1 for m in msgs if m in (1, 2))
            completed = any(m in (3, 4) for m in msgs)
            ssid_name = bmap.get(data['bssid'], {}).get('ssid', 'Unknown')
            if msg12 >= 4 and not completed:
                eapol_events.append({
                    'type': 'bad_password', 'client': data['client'],
                    'bssid': data['bssid'], 'ssid': ssid_name,
                    'attempts': msg12 // 2,
                    'description': f"Client {data['client']} attempted to connect to {ssid_name} {msg12 // 2} times without completing the 4-way handshake"
                })
            elif completed:
                eapol_events.append({
                    'type': 'success', 'client': data['client'],
                    'bssid': data['bssid'], 'ssid': ssid_name,
                    'description': f"Client {data['client']} completed 4-way handshake with {ssid_name}"
                })
        sess['eapol_events'] = eapol_events

        # Pass 4: Client associations (ToDS data frames)
        sess['progress'] = 'Mapping client associations...'
        sess['progress_pct'] = 16
        client_rows = run_tshark(pcap, 'wlan.fc.type == 2 && wlan.fc.tods == 1 && wlan.fc.fromds == 0', [
            'wlan.sa', 'wlan.bssid', 'frame.time_epoch'
        ])

        client_assoc = {}
        for r in client_rows:
            sa = r['wlan.sa'].upper()
            bssid = r['wlan.bssid'].upper()
            if not sa or not bssid or sa == bssid:
                continue
            client_assoc.setdefault(sa, {})
            client_assoc[sa].setdefault(bssid, {'count': 0, 'first': '', 'last': ''})
            client_assoc[sa][bssid]['count'] += 1
            ep = r.get('frame.time_epoch', '')
            if ep:
                if not client_assoc[sa][bssid]['first'] or ep < client_assoc[sa][bssid]['first']:
                    client_assoc[sa][bssid]['first'] = ep
                if not client_assoc[sa][bssid]['last'] or ep > client_assoc[sa][bssid]['last']:
                    client_assoc[sa][bssid]['last'] = ep
        sess['client_assoc'] = client_assoc

        # Pass 5: Wired hosts (FromDS data frames)
        sess['progress'] = 'Finding wired hosts...'
        sess['progress_pct'] = 20
        wired_rows = run_tshark(pcap, 'wlan.fc.type == 2 && wlan.fc.tods == 0 && wlan.fc.fromds == 1', [
            'wlan.da', 'wlan.bssid'
        ])

        wired_hosts = {}
        for r in wired_rows:
            da = r['wlan.da'].upper()
            bssid = r['wlan.bssid'].upper()
            if not da or da == 'FF:FF:FF:FF:FF:FF':
                continue
            if da not in client_assoc and da not in bmap:
                wired_hosts.setdefault(da, {'mac': da, 'vendor': OUI_MAP.get(da[:8], 'Unknown'), 'via': set()})
                wired_hosts[da]['via'].add(bssid)
        for info in wired_hosts.values():
            info['via'] = list(info['via'])
        sess['wired_hosts'] = wired_hosts

        # Pass 6: EAP identities
        sess['progress'] = 'Extracting 802.1X identities...'
        sess['progress_pct'] = 24
        eap_rows = run_tshark(pcap, 'eap.identity', ['wlan.sa', 'wlan.bssid', 'eap.identity'], timeout=120)
        eap_ids = {}
        for r in eap_rows:
            sa = r['wlan.sa'].upper()
            if sa and r['eap.identity']:
                eap_ids[sa] = {'identity': r['eap.identity'], 'bssid': r['wlan.bssid'].upper()}
        sess['eap_identities'] = eap_ids

        # Pass 6b: EAP method detection
        eap_type_rows = run_tshark(pcap, 'eap.type', ['wlan.bssid', 'eap.type'], timeout=120)
        eap_methods = {}
        EAP_TYPE_MAP = {'1': 'Identity', '3': 'NAK', '4': 'MD5', '6': 'GTC', '13': 'EAP-TLS',
                        '21': 'EAP-TTLS', '25': 'PEAP', '29': 'EAP-MSCHAPv2', '43': 'EAP-FAST',
                        '47': 'EAP-PSK', '48': 'EAP-SAKE', '52': 'TEAP', '254': 'Expanded'}
        for r in eap_type_rows:
            b = r.get('wlan.bssid', '').upper()
            etype = r.get('eap.type', '')
            if b and etype and etype not in ('1', '3'):  # Skip Identity and NAK
                method_name = EAP_TYPE_MAP.get(etype, f'Type-{etype}')
                eap_methods.setdefault(b, set()).add(method_name)
        sess['eap_methods'] = {k: list(v) for k, v in eap_methods.items()}

        # Pass 7: Certificates (enhanced with signature algo and issuer)
        sess['progress'] = 'Checking certificates...'
        sess['progress_pct'] = 28
        cert_rows = run_tshark(pcap, 'tls.handshake.certificate', [
            'wlan.bssid', 'x509sat.utf8String',
            'x509ce.validity.notBefore.utcTime', 'x509ce.validity.notAfter.utcTime',
            'x509af.algorithmIdentifier', 'x509if.issuer',
        ], timeout=120)
        certs = []
        for r in cert_rows:
            b = r['wlan.bssid'].upper()
            if b and (r['x509sat.utf8String'] or r['x509ce.validity.notAfter.utcTime']):
                subject = r['x509sat.utf8String']
                issuer = r.get('x509if.issuer', '')
                sig_algo = r.get('x509af.algorithmIdentifier', '')
                self_signed = bool(subject and issuer and subject == issuer)
                weak_sig = bool(sig_algo and ('sha1' in sig_algo.lower() or 'md5' in sig_algo.lower()))
                certs.append({
                    'bssid': b, 'ssid': bmap.get(b, {}).get('ssid', 'Unknown'),
                    'subject': subject, 'issuer': issuer,
                    'not_before': r['x509ce.validity.notBefore.utcTime'],
                    'not_after': r['x509ce.validity.notAfter.utcTime'],
                    'sig_algo': sig_algo, 'self_signed': self_signed, 'weak_sig': weak_sig,
                })
        sess['certificates'] = certs

        # Pass 8: Management attack detection (deauth, disassoc, auth frames)
        sess['progress'] = 'Scanning for management frame attacks...'
        sess['progress_pct'] = 32
        mgt_attack_rows = run_tshark(pcap, 'wlan.fc.type_subtype == 0x000c || wlan.fc.type_subtype == 0x000a || wlan.fc.type_subtype == 0x000b', [
            'wlan.fc.type_subtype', 'wlan.sa', 'wlan.da', 'wlan.bssid', 'frame.time_epoch'
        ], timeout=300)

        deauth_frames = []
        disassoc_frames = []
        auth_frames = []
        for r in mgt_attack_rows:
            st = r.get('wlan.fc.type_subtype', '')
            entry = {'sa': r.get('wlan.sa', '').upper(), 'da': r.get('wlan.da', '').upper(),
                     'bssid': r.get('wlan.bssid', '').upper(), 'time': r.get('frame.time_epoch', '')}
            if st == '0x000c' or st == '12': deauth_frames.append(entry)
            elif st == '0x000a' or st == '10': disassoc_frames.append(entry)
            elif st == '0x000b' or st == '11': auth_frames.append(entry)
        sess['deauth_frames'] = deauth_frames
        sess['disassoc_frames'] = disassoc_frames
        sess['auth_frames'] = auth_frames

        # Pass 9: Directed probe requests (client security analysis)
        sess['progress'] = 'Analysing client probe requests...'
        sess['progress_pct'] = 36
        probe_req_rows = run_tshark(pcap, 'wlan.fc.type_subtype == 0x0004', [
            'wlan.sa', 'wlan.ssid'
        ], timeout=300)

        client_probes = {}
        for r in probe_req_rows:
            sa = r.get('wlan.sa', '').upper()
            ssid = r.get('wlan.ssid', '')
            if sa and ssid:
                client_probes.setdefault(sa, set()).add(ssid)
        # Convert sets to lists
        sess['client_probes'] = {k: list(v) for k, v in client_probes.items()}

        # Pass 10: Beacon anomaly detection (compare security across beacons for same BSSID)
        sess['progress'] = 'Checking for beacon anomalies...'
        sess['progress_pct'] = 40
        beacon_sec_rows = run_tshark(pcap, 'wlan.fc.type_subtype == 0x0008', [
            'wlan.bssid', 'wlan.ssid', 'wlan.rsn.akms.type', 'wlan.rsn.pcs.type',
            'wlan.fixed.capabilities.privacy', 'frame.time_epoch'
        ], timeout=300)

        beacon_anomalies = []
        bssid_first_sec = {}
        for r in beacon_sec_rows:
            b = r.get('wlan.bssid', '').upper()
            if not b:
                continue
            sec_sig = f"{r.get('wlan.rsn.akms.type', '')}|{r.get('wlan.rsn.pcs.type', '')}|{r.get('wlan.fixed.capabilities.privacy', '')}"
            if b not in bssid_first_sec:
                bssid_first_sec[b] = {'sig': sec_sig, 'ssid': r.get('wlan.ssid', ''), 'time': r.get('frame.time_epoch', '')}
            else:
                if sec_sig != bssid_first_sec[b]['sig'] and sec_sig.replace('|', '') != '':
                    beacon_anomalies.append({
                        'bssid': b, 'ssid': bssid_first_sec[b]['ssid'],
                        'old_sec': bssid_first_sec[b]['sig'], 'new_sec': sec_sig,
                    })
                    bssid_first_sec[b]['sig'] = sec_sig
        sess['beacon_anomalies'] = beacon_anomalies

        # Pass 11: Protocol leakage (ARP, DHCP, CDP, LLDP, STP - works on unencrypted traffic)
        sess['progress'] = 'Detecting protocol leakage...'
        sess['progress_pct'] = 44
        protocol_leaks = {'arp': False, 'dhcp': False, 'cdp': False, 'lldp': False, 'stp': False, 'mdns': False, 'ssdp': False}

        # ARP
        arp_rows = run_tshark(pcap, 'arp', ['arp.src.hw_mac', 'arp.src.proto_ipv4', 'arp.dst.proto_ipv4'], timeout=60)
        if arp_rows:
            protocol_leaks['arp'] = True
            # ARP spoofing detection: multiple MACs claiming same IP
            ip_to_macs = {}
            for r in arp_rows:
                ip = r.get('arp.src.proto_ipv4', '')
                mac = r.get('arp.src.hw_mac', '').upper()
                if ip and mac:
                    ip_to_macs.setdefault(ip, set()).add(mac)
            arp_conflicts = {ip: list(macs) for ip, macs in ip_to_macs.items() if len(macs) > 1}
            sess['arp_conflicts'] = arp_conflicts

        # DHCP
        dhcp_rows = run_tshark(pcap, 'dhcp', ['dhcp.type', 'dhcp.option.dhcp_server_id', 'eth.src'], timeout=60)
        if dhcp_rows:
            protocol_leaks['dhcp'] = True
            dhcp_servers = set()
            for r in dhcp_rows:
                sid = r.get('dhcp.option.dhcp_server_id', '')
                if sid:
                    dhcp_servers.add(sid)
            sess['dhcp_servers'] = list(dhcp_servers)

        # CDP/LLDP
        cdp_rows = run_tshark(pcap, 'cdp', ['cdp.deviceid', 'cdp.platform', 'cdp.portid'], timeout=30)
        if cdp_rows:
            protocol_leaks['cdp'] = True
            sess['cdp_devices'] = [{'device': r.get('cdp.deviceid', ''), 'platform': r.get('cdp.platform', ''), 'port': r.get('cdp.portid', '')} for r in cdp_rows[:20]]

        lldp_rows = run_tshark(pcap, 'lldp', ['lldp.chassis.id', 'lldp.port.id', 'lldp.tlv.system.name'], timeout=30)
        if lldp_rows:
            protocol_leaks['lldp'] = True
            sess['lldp_devices'] = [{'chassis': r.get('lldp.chassis.id', ''), 'port': r.get('lldp.port.id', ''), 'name': r.get('lldp.tlv.system.name', '')} for r in lldp_rows[:20]]

        # STP
        stp_rows = run_tshark(pcap, 'stp', ['stp.root.hw'], timeout=30)
        if stp_rows:
            protocol_leaks['stp'] = True

        # mDNS / SSDP
        mdns_rows = run_tshark(pcap, 'mdns', ['dns.qry.name'], timeout=30)
        if mdns_rows:
            protocol_leaks['mdns'] = True

        sess['protocol_leaks'] = protocol_leaks

        # Pass 12: Probe response spoofing (responses from unknown BSSIDs)
        sess['progress'] = 'Checking for probe response spoofing...'
        sess['progress_pct'] = 48
        probe_resp_bssids = set()
        for r in run_tshark(pcap, 'wlan.fc.type_subtype == 0x0005', ['wlan.bssid'], timeout=120):
            b = r.get('wlan.bssid', '').upper()
            if b:
                probe_resp_bssids.add(b)
        beacon_bssids = set(bmap.keys())
        unknown_probe_resp = probe_resp_bssids - beacon_bssids
        sess['unknown_probe_resp'] = list(unknown_probe_resp)

        # Pass 13: Data frame analysis (retry rates, signal strength, airtime)
        sess['progress'] = 'Analysing data frames (retries, signal, airtime)...'
        sess['progress_pct'] = 55
        df_rows = run_tshark(pcap, 'wlan.fc.type == 2', [
            'wlan.sa', 'wlan.bssid', 'wlan.fc.retry', 'radiotap.dbm_antsignal',
            'radiotap.datarate', 'frame.len', 'wlan.fc.type_subtype', 'frame.time_epoch'
        ], timeout=600)

        df_stats = {}
        for r in df_rows:
            sa = r.get('wlan.sa', '').upper()
            bssid = r.get('wlan.bssid', '').upper()
            if not sa or not bssid:
                continue
            retry = r.get('wlan.fc.retry', '') == '1'
            rssi_str = r.get('radiotap.dbm_antsignal', '')
            rate_str = r.get('radiotap.datarate', '')
            flen_str = r.get('frame.len', '')
            subtype = r.get('wlan.fc.type_subtype', '')
            epoch = r.get('frame.time_epoch', '')

            try:
                rssi = int(rssi_str.split(',')[0]) if rssi_str else None
            except (ValueError, IndexError):
                rssi = None
            try:
                rate = float(rate_str.split(',')[0]) if rate_str else None
            except (ValueError, IndexError):
                rate = None
            try:
                flen = int(flen_str) if flen_str else 0
            except ValueError:
                flen = 0

            key = f"{sa}_{bssid}"
            if key not in df_stats:
                df_stats[key] = {
                    'sa': sa, 'bssid': bssid,
                    'total_frames': 0, 'retry_frames': 0,
                    'rssi_values': [], 'rates': [], 'frame_sizes': [],
                    'airtime_us': 0.0, 'low_rate_frames': 0,
                }
            s = df_stats[key]
            s['total_frames'] += 1
            if retry:
                s['retry_frames'] += 1
            if rssi is not None and -100 <= rssi <= 0:
                s['rssi_values'].append(rssi)
            if rate is not None and rate > 0:
                s['rates'].append(rate)
                airtime_est = (flen * 8) / (rate * 1e6) * 1e6 if rate > 0 else 0
                s['airtime_us'] += airtime_est
                if rate < 24:
                    s['low_rate_frames'] += 1
            s['frame_sizes'].append(flen)

        sess['data_frame_stats'] = df_stats

        # Pass 13b: Management frame stats for airtime overhead
        sess['progress_pct'] = 62
        mgt_count_rows = run_tshark(pcap, 'wlan.fc.type == 0', [
            'wlan.fc.type_subtype', 'wlan.bssid', 'frame.len'
        ], timeout=300)

        mgt_stats = {'total': 0, 'beacon': 0, 'probe_req': 0, 'by_bssid': {}}
        for r in mgt_count_rows:
            mgt_stats['total'] += 1
            st = r.get('wlan.fc.type_subtype', '')
            if st in ('0x0008', '8'):
                mgt_stats['beacon'] += 1
            elif st in ('0x0004', '4'):
                mgt_stats['probe_req'] += 1
            b = r.get('wlan.bssid', '').upper()
            if b:
                mgt_stats['by_bssid'].setdefault(b, 0)
                mgt_stats['by_bssid'][b] += 1
        sess['mgt_stats'] = mgt_stats

        # Total frame count for airtime percentage calculations
        total_all_frames = len(df_rows) + mgt_stats['total']
        sess['total_all_frames'] = total_all_frames

        # Pass 14: Client capabilities (from probe requests and association requests)
        sess['progress'] = 'Analysing client capabilities...'
        sess['progress_pct'] = 68
        cap_rows = run_tshark(pcap,
            'wlan.fc.type_subtype == 0x0004 || wlan.fc.type_subtype == 0x0000 || wlan.fc.type_subtype == 0x0002',
            [
                'wlan.sa', 'wlan.bssid', 'wlan.fc.type_subtype',
                'wlan.ht.capabilities', 'wlan.vht.capabilities',
                'wlan.tag.number', 'wlan.supported_rates',
                'radiotap.channel.freq',
            ], timeout=300)

        client_caps = {}
        for r in cap_rows:
            sa = r.get('wlan.sa', '').upper()
            if not sa:
                continue
            if sa not in client_caps:
                client_caps[sa] = {
                    'mac': sa, 'has_ht': False, 'has_vht': False, 'has_he': False,
                    'bands_probed': set(), 'supported_rates': '',
                    'assoc_bssid': '', 'subtype': '',
                }
            c = client_caps[sa]
            if r.get('wlan.ht.capabilities'):
                c['has_ht'] = True
            if r.get('wlan.vht.capabilities'):
                c['has_vht'] = True
            tags = set(r.get('wlan.tag.number', '').split(',')) if r.get('wlan.tag.number') else set()
            if '255' in tags:
                c['has_he'] = True
            if not c['supported_rates'] and r.get('wlan.supported_rates'):
                c['supported_rates'] = r['wlan.supported_rates']
            freq_str = r.get('radiotap.channel.freq', '')
            try:
                freq = int(float(freq_str)) if freq_str else 0
            except ValueError:
                freq = 0
            if freq > 0:
                if freq < 3000:
                    c['bands_probed'].add('2.4 GHz')
                elif freq < 5900:
                    c['bands_probed'].add('5 GHz')
                else:
                    c['bands_probed'].add('6 GHz')
            st = r.get('wlan.fc.type_subtype', '')
            if st in ('0x0000', '0', '0x0002', '2'):
                c['assoc_bssid'] = r.get('wlan.bssid', '').upper()
                c['subtype'] = st

        for c in client_caps.values():
            c['bands_probed'] = list(c['bands_probed'])
        sess['client_caps'] = client_caps

        # Pass 15: Roaming events (association and reassociation request/response frames)
        sess['progress'] = 'Analysing roaming events...'
        sess['progress_pct'] = 76
        roam_rows = run_tshark(pcap,
            'wlan.fc.type_subtype == 0x0000 || wlan.fc.type_subtype == 0x0001 || '
            'wlan.fc.type_subtype == 0x0002 || wlan.fc.type_subtype == 0x0003',
            [
                'wlan.sa', 'wlan.da', 'wlan.bssid', 'wlan.fc.type_subtype',
                'frame.time_epoch', 'radiotap.dbm_antsignal',
            ], timeout=300)

        roaming_events = []
        for r in roam_rows:
            sa = r.get('wlan.sa', '').upper()
            bssid = r.get('wlan.bssid', '').upper()
            st = r.get('wlan.fc.type_subtype', '')
            epoch = r.get('frame.time_epoch', '')
            rssi_str = r.get('radiotap.dbm_antsignal', '')
            try:
                rssi = int(rssi_str.split(',')[0]) if rssi_str else None
            except (ValueError, IndexError):
                rssi = None
            is_reassoc = st in ('0x0002', '2', '0x0003', '3')
            is_request = st in ('0x0000', '0', '0x0002', '2')
            roaming_events.append({
                'sa': sa, 'bssid': bssid, 'subtype': st,
                'epoch': epoch, 'rssi': rssi,
                'is_reassoc': is_reassoc, 'is_request': is_request,
            })
        sess['roaming_events'] = roaming_events

        # 802.11r Fast Transition detection (auth frames with algorithm=2)
        ft_auth_rows = run_tshark(pcap,
            'wlan.fc.type_subtype == 0x000b && wlan.fixed.auth.alg == 2',
            ['wlan.sa', 'wlan.bssid', 'frame.time_epoch'], timeout=120)
        sess['ft_auth_frames'] = ft_auth_rows

        # Pass 16: DHCP timing analysis
        sess['progress'] = 'Analysing DHCP transactions...'
        sess['progress_pct'] = 84
        dhcp_rows = run_tshark(pcap, 'dhcp', [
            'frame.time_epoch', 'eth.src', 'dhcp.type', 'dhcp.ip.your',
            'dhcp.hw.mac_addr', 'dhcp.option.dhcp_server_id'
        ], timeout=120)

        dhcp_transactions = {}
        for r in dhcp_rows:
            mac = r.get('dhcp.hw.mac_addr', r.get('eth.src', '')).upper()
            dtype = r.get('dhcp.type', '')
            epoch = r.get('frame.time_epoch', '')
            if not mac or not dtype or not epoch:
                continue
            try:
                t = float(epoch)
            except ValueError:
                continue
            dhcp_transactions.setdefault(mac, []).append({
                'type': dtype, 'time': t,
                'ip': r.get('dhcp.ip.your', ''),
                'server': r.get('dhcp.option.dhcp_server_id', ''),
            })
        sess['dhcp_timing'] = dhcp_transactions

        # Pass 17: DNS timing analysis
        sess['progress'] = 'Analysing DNS response times...'
        sess['progress_pct'] = 90
        dns_rows = run_tshark(pcap, 'dns', [
            'frame.time_epoch', 'dns.id', 'dns.flags.response', 'dns.qry.name',
            'ip.src', 'ip.dst'
        ], timeout=120)

        dns_queries = {}
        dns_responses = {}
        for r in dns_rows:
            dns_id = r.get('dns.id', '')
            is_resp = r.get('dns.flags.response', '') == '1'
            epoch = r.get('frame.time_epoch', '')
            qname = r.get('dns.qry.name', '')
            if not dns_id or not epoch:
                continue
            try:
                t = float(epoch)
            except ValueError:
                continue
            key = dns_id
            if not is_resp:
                dns_queries.setdefault(key, []).append({
                    'time': t, 'name': qname, 'dst': r.get('ip.dst', '')
                })
            else:
                dns_responses.setdefault(key, []).append({
                    'time': t, 'name': qname, 'src': r.get('ip.src', '')
                })

        dns_timing = []
        for qid, queries in dns_queries.items():
            responses = dns_responses.get(qid, [])
            for q in queries:
                matched = [r for r in responses if r['time'] >= q['time']]
                if matched:
                    resp = min(matched, key=lambda r: r['time'])
                    latency_ms = (resp['time'] - q['time']) * 1000
                    dns_timing.append({
                        'name': q['name'], 'server': q.get('dst', resp.get('src', '')),
                        'latency_ms': round(latency_ms, 1),
                    })
                else:
                    dns_timing.append({
                        'name': q['name'], 'server': q.get('dst', ''),
                        'latency_ms': None,
                    })
        sess['dns_timing'] = dns_timing

        # Pass 18: Probe request counts per client (for probe storm detection)
        sess['progress'] = 'Counting probe requests per client...'
        sess['progress_pct'] = 95
        probe_count_rows = run_tshark(pcap, 'wlan.fc.type_subtype == 0x0004', [
            'wlan.sa', 'frame.time_epoch'
        ], timeout=120)

        probe_counts = {}
        for r in probe_count_rows:
            sa = r.get('wlan.sa', '').upper()
            if sa:
                probe_counts.setdefault(sa, {'count': 0, 'times': []})
                probe_counts[sa]['count'] += 1
                try:
                    probe_counts[sa]['times'].append(float(r.get('frame.time_epoch', '0')))
                except ValueError:
                    pass
        sess['probe_counts'] = probe_counts

        sess['progress'] = 'Processing complete'
        sess['progress_pct'] = 100
        sess['status'] = 'ready'

    except Exception as e:
        sess['status'] = 'error'
        sess['progress'] = f'Error: {str(e)}'

def phase2_analysis(session_id, ssid, vendor='generic'):
    sess = analyzer_sessions.get(session_id)
    if not sess or sess['status'] != 'ready':
        return {'error': 'Session not ready'}

    bmap = sess['bssid_map']
    pcap = sess['pcap_path']
    ssid_bssids = [b for b, info in bmap.items() if info['ssid'] == ssid]
    if not ssid_bssids:
        return {'error': 'No BSSIDs found for this SSID'}

    # Detailed beacon extraction for these BSSIDs
    bfilter = ' || '.join([f'wlan.bssid == {b.lower()}' for b in ssid_bssids])
    detail_rows = run_tshark(pcap, f'wlan.fc.type_subtype == 0x0008 && ({bfilter})', [
        'wlan.bssid', 'wlan.ssid', 'radiotap.channel.freq', 'wlan.fixed.timestamp',
        'wlan.rsn.akms.type', 'wlan.rsn.pcs.type',
        'wlan.wfa.ie.wpa.akms.type', 'wlan.wfa.ie.wpa.pcs.type',
        'wlan.ht.capabilities', 'wlan.vht.capabilities',
        'wlan.supported_rates', 'wlan.extended_supported_rates',
        'wlan.bss_load.station_count', 'wlan.tag.number',
        'wlan.fixed.capabilities.privacy', 'wlan.txpower.level',
    ])

    bdetails = {}
    for r in detail_rows:
        b = r['wlan.bssid'].upper()
        if not b:
            continue
        if b not in bdetails:
            bdetails[b] = r
            bdetails[b]['wlan.bssid'] = b
        else:
            for k, v in r.items():
                if v and not bdetails[b].get(k):
                    bdetails[b][k] = v

    # Group into APs
    ap_groups_raw = group_bssids(ssid_bssids, vendor)

    # Also find related BSSIDs (same AP group but different SSIDs)
    all_related = set(ssid_bssids)
    for gkey, glist in ap_groups_raw.items():
        p = VENDOR_GROUPING.get(vendor, VENDOR_GROUPING['generic'])
        for b, info in bmap.items():
            octets = b.split(':')
            if len(octets) == 6:
                k = ':'.join(octets[p['start']:p['start']+p['length']])
                if k == gkey:
                    all_related.add(b)

    ap_groups = []
    ap_num = 1
    for gkey, glist in sorted(ap_groups_raw.items()):
        # Include related BSSIDs from same AP group
        p = VENDOR_GROUPING.get(vendor, VENDOR_GROUPING['generic'])
        full_group = set(glist)
        for b in bmap:
            octets = b.split(':')
            if len(octets) == 6:
                k = ':'.join(octets[p['start']:p['start']+p['length']])
                if k == gkey:
                    full_group.add(b)

        ap = {'name': f'AP {ap_num}', 'group_key': gkey, 'radios': {}, 'bssids': [],
              'total_stations': 0, 'ssids_on_ap': []}
        ssids_set = set()

        for b in sorted(full_group):
            det = bdetails.get(b, {})
            basic = bmap.get(b, {})
            freq_str = det.get('radiotap.channel.freq', basic.get('freq', ''))
            try:
                freq = int(float(freq_str)) if freq_str else 0
            except ValueError:
                freq = 0

            band = ''
            if 0 < freq < 3000: band = '2.4 GHz'
            elif freq < 5900: band = '5 GHz'
            elif freq > 0: band = '6 GHz'

            ch = FREQ_TO_CHANNEL.get(freq, {}).get('channel', '') if freq else ''
            ts_raw = det.get('wlan.fixed.timestamp', basic.get('timestamp', ''))
            uptime = ts_to_uptime(ts_raw)
            try:
                uptime_s = int(ts_raw) / 1_000_000 if ts_raw else 0
            except ValueError:
                uptime_s = 0

            tags = set(det.get('wlan.tag.number', '').split(',')) if det.get('wlan.tag.number') else set()
            has_ht = bool(det.get('wlan.ht.capabilities'))
            has_vht = bool(det.get('wlan.vht.capabilities'))
            has_he = '255' in tags

            if has_he: wifi_gen = 'Wi-Fi 6 (ax)'
            elif has_vht: wifi_gen = 'Wi-Fi 5 (ac)'
            elif has_ht: wifi_gen = 'Wi-Fi 4 (n)'
            else: wifi_gen = 'a/b/g' if freq >= 5000 else 'b/g'

            sec = determine_security(
                det.get('wlan.rsn.akms.type', ''), det.get('wlan.rsn.pcs.type', ''),
                det.get('wlan.wfa.ie.wpa.akms.type', ''), det.get('wlan.wfa.ie.wpa.pcs.type', ''),
                det.get('wlan.fixed.capabilities.privacy', basic.get('privacy', ''))
            )

            tx = det.get('wlan.txpower.level', '')
            try:
                sc = int(det.get('wlan.bss_load.station_count', '') or '0')
            except ValueError:
                sc = 0
            ap['total_stations'] += sc

            rates = det.get('wlan.supported_rates', '')
            ext_rates = det.get('wlan.extended_supported_rates', '')
            has_11k = '70' in tags
            has_11r = '54' in tags
            has_11v = '55' in tags

            bssid_ssid = det.get('wlan.ssid', basic.get('ssid', ''))
            ssids_set.add(bssid_ssid) if bssid_ssid else None

            ap['bssids'].append({
                'bssid': b, 'ssid': bssid_ssid, 'band': band, 'channel': ch,
                'uptime': uptime, 'uptime_s': uptime_s, 'wifi_gen': wifi_gen,
                'security': sec, 'tx_power': tx, 'station_count': sc,
                'rates': rates, 'ext_rates': ext_rates,
                'has_11k': has_11k, 'has_11r': has_11r, 'has_11v': has_11v,
                'vendor': OUI_MAP.get(b[:8], 'Unknown'),
            })

            if band and tx:
                try:
                    tp_val = int(tx.split(',')[0])
                    ap['radios'].setdefault(band, {'channel': ch, 'tx_powers': []})
                    ap['radios'][band]['tx_powers'].append(tp_val)
                    ap['radios'][band]['channel'] = ch
                except ValueError:
                    pass

        ap['ssids_on_ap'] = sorted(ssids_set)
        ap_groups.append(ap)
        ap_num += 1

    # TX power ranges across APs
    power_ranges = {}
    for band_name in ('2.4 GHz', '5 GHz', '6 GHz'):
        all_powers = []
        for ap in ap_groups:
            r = ap['radios'].get(band_name)
            if r and r.get('tx_powers'):
                all_powers.extend(r['tx_powers'])
        if all_powers:
            power_ranges[band_name] = {'min': min(all_powers), 'max': max(all_powers)}

    # Clients
    all_ap_bssids = set()
    for ap in ap_groups:
        for bi in ap['bssids']:
            all_ap_bssids.add(bi['bssid'])

    clients = []
    eap_ids = sess.get('eap_identities', {})
    for cmac, assocs in sess.get('client_assoc', {}).items():
        for b, info in assocs.items():
            if b in all_ap_bssids:
                clients.append({
                    'mac': cmac, 'vendor': OUI_MAP.get(cmac[:8], 'Unknown'),
                    'randomised': is_random_mac(cmac), 'bssid': b,
                    'ssid': bmap.get(b, {}).get('ssid', ''),
                    'frames': info['count'],
                    'username': eap_ids.get(cmac, {}).get('identity', ''),
                })

    # Roaming
    roaming = {}
    for cmac, assocs in sess.get('client_assoc', {}).items():
        relevant = [b for b in assocs if b in all_ap_bssids]
        if len(relevant) > 1:
            roaming[cmac] = [{
                'bssid': b, 'ssid': bmap.get(b, {}).get('ssid', ''),
                'frames': assocs[b]['count'],
                'first': assocs[b].get('first', ''), 'last': assocs[b].get('last', ''),
            } for b in relevant]

    # Wired hosts
    wired = [{'mac': m, 'vendor': i['vendor'], 'via': [b for b in i['via'] if b in all_ap_bssids]}
             for m, i in sess.get('wired_hosts', {}).items()
             if any(b in all_ap_bssids for b in i.get('via', []))]

    # EAPOL & certs for this SSID
    eapol = [e for e in sess.get('eapol_events', []) if e.get('bssid') in all_ap_bssids]
    certs = [c for c in sess.get('certificates', []) if c.get('bssid') in all_ap_bssids]

    # Problems
    problems = []
    related_ssids = set()
    for ap in ap_groups:
        for bi in ap['bssids']:
            if bi['ssid']:
                related_ssids.add(bi['ssid'])

    for ap in ap_groups:
        # TX power imbalance
        tp24 = ap['radios'].get('2.4 GHz', {}).get('tx_powers', [])
        tp5 = ap['radios'].get('5 GHz', {}).get('tx_powers', [])
        if tp24 and tp5:
            avg24 = sum(tp24) / len(tp24)
            avg5 = sum(tp5) / len(tp5)
            delta = abs(avg24 - avg5)
            if delta < 6:
                problems.append({'severity': 'high', 'title': f'TX power imbalance on {ap["name"]}',
                    'description': f'2.4 GHz: {avg24:.0f} dBm, 5 GHz: {avg5:.0f} dBm (delta: {delta:.0f} dBm). Should be at least 6 dBm separation.'})

        # Long uptime
        for bi in ap['bssids']:
            if bi['uptime_s'] > 180 * 86400:
                d = int(bi['uptime_s'] / 86400)
                problems.append({'severity': 'medium', 'title': f'Long uptime on {ap["name"]}',
                    'description': f'BSS uptime is {d} days. Firmware likely not updated recently.'})
                break

        # Legacy bit rates
        for bi in ap['bssids']:
            if bi['rates']:
                legacy = [r.strip() for r in bi['rates'].split(',')
                          if r.strip().rstrip('(B)').strip() in ('1.0', '2.0', '5.5', '11.0', '1', '2', '5.5', '11')]
                if legacy:
                    problems.append({'severity': 'medium', 'title': f'Legacy bit rates on {ap["name"]}',
                        'description': f'Low bit rates enabled: {", ".join(legacy)} Mbps. These slow down the entire BSS.'})
                    break

        # Missing roaming support
        for bi in ap['bssids']:
            if bi['ssid'] == ssid:
                missing = []
                if not bi['has_11k']: missing.append('802.11k')
                if not bi['has_11r']: missing.append('802.11r')
                if not bi['has_11v']: missing.append('802.11v')
                if missing and len(ap_groups) > 1:
                    problems.append({'severity': 'low', 'title': f'Missing roaming support on {ap["name"]}',
                        'description': f'Not advertising: {", ".join(missing)}.'})
                break

    if len(related_ssids) > 4:
        problems.append({'severity': 'high', 'title': f'Too many SSIDs ({len(related_ssids)})',
            'description': f'{", ".join(sorted(related_ssids))}. Each adds beacon overhead.'})

    for ev in eapol:
        if ev['type'] == 'bad_password':
            problems.append({'severity': 'high', 'title': 'Possible bad password', 'description': ev['description']})

    for cert in certs:
        na = cert.get('not_after', '')
        if na:
            for fmt in ('%y%m%d%H%M%SZ', '%Y%m%d%H%M%SZ'):
                try:
                    exp = datetime.strptime(na, fmt)
                    days_left = (exp - datetime.now()).days
                    if days_left < 0:
                        problems.append({'severity': 'critical', 'title': f'Expired certificate on {cert["ssid"]}',
                            'description': f'Certificate expired {abs(days_left)} days ago.'})
                    elif days_left < 30:
                        problems.append({'severity': 'high', 'title': f'Certificate expiring soon on {cert["ssid"]}',
                            'description': f'Certificate expires in {days_left} days.'})
                    break
                except ValueError:
                    continue
        # Weak certificate signature algorithm
        if cert.get('weak_sig'):
            problems.append({'severity': 'medium', 'title': f'Weak certificate signature on {cert["ssid"]}',
                'description': f'802.1X certificate uses a weak signature algorithm ({cert.get("sig_algo", "unknown")}). SHA-1 and MD5 are considered broken. Use SHA-256 or stronger.'})
        # Self-signed certificate
        if cert.get('self_signed'):
            problems.append({'severity': 'low', 'title': f'Self-signed certificate on {cert["ssid"]}',
                'description': f'802.1X certificate is self-signed (subject matches issuer). Clients may display certificate warnings, training users to accept untrusted certificates.'})

    # --- Security: EAP method analysis ---
    eap_methods = sess.get('eap_methods', {})
    for b in all_ap_bssids:
        methods = eap_methods.get(b, [])
        if methods:
            ssid_name = bmap.get(b, {}).get('ssid', '')
            if 'PEAP' in methods or 'EAP-MSCHAPv2' in methods:
                problems.append({'severity': 'medium',
                    'title': f'EAP-PEAP/MSCHAPv2 detected on {ssid_name or b}',
                    'description': f'BSSID {b} uses {", ".join(methods)}. MSCHAPv2 credentials can be captured by a rogue RADIUS server if clients do not properly validate the server certificate. Consider EAP-TLS with certificate-based authentication.'})
                break  # One per SSID
            if 'MD5' in methods:
                problems.append({'severity': 'high',
                    'title': f'EAP-MD5 detected on {ssid_name or b}',
                    'description': f'EAP-MD5 provides no server authentication and transmits credentials in a crackable hash. It should never be used on wireless networks.'})
                break

    # --- Security: Client on open while encrypted available ---
    open_bssids = {b for b, info in bmap.items() if not info.get('privacy') and not info.get('ssid', '').startswith('(')}
    encrypted_ssids = {info['ssid'] for b, info in bmap.items() if info.get('privacy') and info.get('ssid')}
    for c in clients:
        if c['bssid'] in open_bssids:
            c_ssid = bmap.get(c['bssid'], {}).get('ssid', '')
            if c_ssid and c_ssid in encrypted_ssids:
                problems.append({'severity': 'medium',
                    'title': f'Client on open network while encrypted version exists',
                    'description': f'Client {c["mac"]} is connected to the open version of "{c_ssid}" (BSSID {c["bssid"]}) while an encrypted version of the same SSID exists.'})
                break  # One example is enough

    hidden_in = [b for b in all_ap_bssids if b in sess.get('hidden_ssids', {})]
    if hidden_in:
        problems.append({'severity': 'low', 'title': f'Hidden SSIDs detected ({len(hidden_in)})',
            'description': 'Hidden SSIDs provide no security benefit and cause client privacy leaks via probe requests.'})

    # --- Security: Deauthentication storm detection ---
    deauth_frames = sess.get('deauth_frames', [])
    deauth_by_target = {}
    for f in deauth_frames:
        target = f['da']
        deauth_by_target.setdefault(target, []).append(f)
    for target, frames in deauth_by_target.items():
        if len(frames) >= 10:
            times = [float(f['time']) for f in frames if f['time']]
            if times:
                duration = max(times) - min(times)
                if duration < 60 and duration > 0:
                    sources = set(f['sa'] for f in frames)
                    problems.append({'severity': 'critical',
                        'title': f'Deauthentication storm detected',
                        'description': f'{len(frames)} deauth frames targeting {target} in {duration:.0f}s from {len(sources)} source(s): {", ".join(list(sources)[:3])}. This indicates an active deauthentication attack.'})
    if len(deauth_frames) > 50:
        problems.append({'severity': 'high',
            'title': f'High deauthentication frame count ({len(deauth_frames)})',
            'description': f'Total {len(deauth_frames)} deauth frames captured. Elevated deauth activity may indicate attack attempts or unstable infrastructure.'})

    # --- Security: Disassociation storm detection ---
    disassoc_frames = sess.get('disassoc_frames', [])
    if len(disassoc_frames) > 50:
        problems.append({'severity': 'high',
            'title': f'High disassociation frame count ({len(disassoc_frames)})',
            'description': f'{len(disassoc_frames)} disassociation frames captured. May indicate denial-of-service attack.'})

    # --- Security: Authentication flood detection ---
    auth_frames = sess.get('auth_frames', [])
    auth_by_target = {}
    for f in auth_frames:
        bssid = f['bssid']
        auth_by_target.setdefault(bssid, []).append(f)
    for bssid, frames in auth_by_target.items():
        unique_sources = set(f['sa'] for f in frames)
        if len(unique_sources) > 20 and len(frames) > 50:
            problems.append({'severity': 'medium',
                'title': f'Authentication flood on {bssid}',
                'description': f'{len(frames)} auth frames from {len(unique_sources)} unique sources targeting BSSID {bssid}. May indicate resource exhaustion attack.'})

    # --- Security: Beacon anomaly detection ---
    for anomaly in sess.get('beacon_anomalies', []):
        if anomaly['bssid'] in all_ap_bssids:
            problems.append({'severity': 'high',
                'title': f'Beacon anomaly on {anomaly["bssid"]}',
                'description': f'BSSID {anomaly["bssid"]} (SSID: {anomaly["ssid"]}) changed security parameters during capture. Security signature changed from [{anomaly["old_sec"]}] to [{anomaly["new_sec"]}]. May indicate AP compromise or spoofing.'})

    # --- Security: Rogue AP indicators (same SSID different security/vendor) ---
    ssid_security_map = {}
    for b, info in bmap.items():
        if info['ssid'] == ssid:
            ssid_security_map.setdefault(info.get('privacy', ''), set()).add(b)
    # Check vendors across all BSSIDs for this SSID
    ssid_vendors = set()
    for b in ssid_bssids:
        v = OUI_MAP.get(b[:8], 'Unknown')
        if v != 'Unknown':
            ssid_vendors.add(v)
    if len(ssid_vendors) > 1:
        problems.append({'severity': 'medium',
            'title': f'Multiple vendors for SSID "{ssid}"',
            'description': f'BSSIDs for this SSID come from different vendors: {", ".join(sorted(ssid_vendors))}. May indicate rogue AP if not expected.'})

    # --- Security: Username exposure in EAP identity ---
    eap_ids = sess.get('eap_identities', {})
    exposed_users = [(mac, info) for mac, info in eap_ids.items() if info.get('bssid') in all_ap_bssids and info.get('identity')]
    if exposed_users:
        usernames = [info['identity'] for _, info in exposed_users[:5]]
        # Check if outer identity is anonymous
        non_anon = [u for u in usernames if not u.lower().startswith('anonymous')]
        if non_anon:
            problems.append({'severity': 'medium',
                'title': f'Usernames exposed in EAP identity ({len(non_anon)} users)',
                'description': f'Real usernames visible in EAP Identity Response: {", ".join(non_anon[:5])}. The outer identity should use "anonymous@domain" to prevent username enumeration.',
            })

    # --- Security: Client probing for insecure networks ---
    insecure_ssid_names = {'Free WiFi', 'Free_WiFi', 'FreeWifi', 'Free Wi-Fi', 'guest', 'Guest',
        'PUBLIC', 'public', 'open', 'Open', 'FREE', 'Airport', 'airport', 'Hotel', 'hotel',
        'Starbucks', 'McDonalds', 'attwifi', 'xfinitywifi', 'Google Starbucks'}
    client_probes = sess.get('client_probes', {})
    clients_probing_insecure = {}
    for cmac, probed_ssids in client_probes.items():
        insecure_probed = [s for s in probed_ssids if s in insecure_ssid_names]
        if insecure_probed:
            clients_probing_insecure[cmac] = insecure_probed
    if clients_probing_insecure:
        count = len(clients_probing_insecure)
        example = list(clients_probing_insecure.items())[0]
        problems.append({'severity': 'low',
            'title': f'{count} client(s) probing for insecure networks',
            'description': f'Clients sending directed probe requests for known open/public network names. Example: {example[0]} probing for {", ".join(example[1][:3])}. These clients may auto-connect to rogue APs with matching names.'})

    # --- Security: Client broadcasting saved network list ---
    for cmac, probed_ssids in client_probes.items():
        if len(probed_ssids) > 5:
            problems.append({'severity': 'low',
                'title': f'Client {cmac} broadcasting {len(probed_ssids)} saved networks',
                'description': f'Client probing for: {", ".join(list(probed_ssids)[:8])}{"..." if len(probed_ssids) > 8 else ""}. This reveals previously connected networks and aids targeted attacks.'})
            if len([c for c in client_probes if len(client_probes[c]) > 5]) > 3:
                break  # Limit to avoid flooding

    # --- Security: Non-randomised MAC detection ---
    non_random_clients = []
    for c in clients:
        if not c.get('randomised', True) and c['mac'] not in [b['bssid'] for ap in ap_groups for b in ap['bssids']]:
            non_random_clients.append(c['mac'])
    if non_random_clients and len(non_random_clients) > 0:
        problems.append({'severity': 'info',
            'title': f'{len(non_random_clients)} client(s) not using MAC randomisation',
            'description': f'These clients use their real (globally unique) MAC address, making them trackable across locations: {", ".join(non_random_clients[:5])}{"..." if len(non_random_clients) > 5 else ""}.'})

    # --- Security: Protocol leakage ---
    leaks = sess.get('protocol_leaks', {})

    if leaks.get('cdp'):
        cdp_devs = sess.get('cdp_devices', [])
        desc = f'CDP frames detected on wireless. Reveals infrastructure details.'
        if cdp_devs:
            desc += f' Devices: {", ".join(d["device"] + " (" + d["platform"] + ")" for d in cdp_devs[:3] if d["device"])}.'
        problems.append({'severity': 'medium', 'title': 'CDP information leakage', 'description': desc})

    if leaks.get('lldp'):
        lldp_devs = sess.get('lldp_devices', [])
        desc = f'LLDP frames detected on wireless. Reveals switch model, port, and hostname.'
        if lldp_devs:
            desc += f' Devices: {", ".join(d["name"] or d["chassis"] for d in lldp_devs[:3] if d["name"] or d["chassis"])}.'
        problems.append({'severity': 'medium', 'title': 'LLDP information leakage', 'description': desc})

    if leaks.get('stp'):
        problems.append({'severity': 'medium',
            'title': 'STP BPDUs on wireless',
            'description': 'Spanning Tree Protocol frames detected on wireless network. Wired infrastructure topology is leaking. Apply bridge protocol filter on AP/switch ports.'})

    if leaks.get('mdns'):
        problems.append({'severity': 'low',
            'title': 'mDNS traffic on wireless',
            'description': 'Multicast DNS traffic detected. Reveals device names, services, and types on the network. Consider filtering multicast on wireless if not needed.'})

    # --- Security: ARP spoofing indicators ---
    arp_conflicts = sess.get('arp_conflicts', {})
    for ip, macs in arp_conflicts.items():
        problems.append({'severity': 'critical',
            'title': f'ARP conflict: IP {ip} claimed by multiple MACs',
            'description': f'IP address {ip} is claimed by {len(macs)} different MAC addresses: {", ".join(macs)}. This may indicate ARP spoofing / man-in-the-middle attack.'})

    # --- Security: Multiple DHCP servers ---
    dhcp_servers = sess.get('dhcp_servers', [])
    if len(dhcp_servers) > 1:
        problems.append({'severity': 'high',
            'title': f'Multiple DHCP servers detected ({len(dhcp_servers)})',
            'description': f'DHCP responses from multiple servers: {", ".join(dhcp_servers)}. A rogue DHCP server can redirect traffic through an attacker.'})

    # --- Security: Probe response spoofing ---
    unknown_pr = sess.get('unknown_probe_resp', [])
    if unknown_pr:
        problems.append({'severity': 'medium',
            'title': f'Probe responses from {len(unknown_pr)} unknown BSSID(s)',
            'description': f'Probe responses received from BSSIDs not seen in any beacon: {", ".join(unknown_pr[:5])}{"..." if len(unknown_pr) > 5 else ""}. May indicate evil twin or KARMA attack.'})

    # ===== RETRY ANALYSIS =====
    df_stats = sess.get('data_frame_stats', {})

    retry_per_client = {}
    retry_per_ap = {}
    signal_per_client = {}
    airtime_per_client = {}
    total_airtime_us = 0.0
    all_rssi_values = []
    all_rates = []

    for key, s in df_stats.items():
        sa = s['sa']
        bssid = s['bssid']
        if bssid not in all_ap_bssids:
            continue

        # Retry aggregation per client
        retry_per_client.setdefault(sa, {'total': 0, 'retry': 0, 'bssids': {}})
        retry_per_client[sa]['total'] += s['total_frames']
        retry_per_client[sa]['retry'] += s['retry_frames']
        retry_per_client[sa]['bssids'].setdefault(bssid, {'total': 0, 'retry': 0})
        retry_per_client[sa]['bssids'][bssid]['total'] += s['total_frames']
        retry_per_client[sa]['bssids'][bssid]['retry'] += s['retry_frames']

        # Retry aggregation per AP
        retry_per_ap.setdefault(bssid, {'total': 0, 'retry': 0})
        retry_per_ap[bssid]['total'] += s['total_frames']
        retry_per_ap[bssid]['retry'] += s['retry_frames']

        # Signal aggregation per client
        if s['rssi_values']:
            signal_per_client.setdefault(sa, {'values': [], 'bssid': bssid})
            signal_per_client[sa]['values'].extend(s['rssi_values'])
            all_rssi_values.extend(s['rssi_values'])

        # Airtime aggregation
        airtime_per_client.setdefault(sa, {'airtime_us': 0.0, 'frames': 0, 'low_rate': 0, 'bssid': bssid})
        airtime_per_client[sa]['airtime_us'] += s['airtime_us']
        airtime_per_client[sa]['frames'] += s['total_frames']
        airtime_per_client[sa]['low_rate'] += s['low_rate_frames']
        total_airtime_us += s['airtime_us']

        all_rates.extend(s['rates'])

    # Build retry analysis result
    retry_clients = []
    for mac, rd in retry_per_client.items():
        rate = (rd['retry'] / rd['total'] * 100) if rd['total'] > 0 else 0
        avg_rssi = None
        if mac in signal_per_client:
            vals = signal_per_client[mac]['values']
            avg_rssi = round(sum(vals) / len(vals)) if vals else None
        retry_clients.append({
            'mac': mac, 'vendor': OUI_MAP.get(mac[:8], 'Unknown'),
            'total_frames': rd['total'], 'retry_frames': rd['retry'],
            'retry_rate': round(rate, 1), 'avg_rssi': avg_rssi,
            'bssid': list(rd['bssids'].keys())[0] if rd['bssids'] else '',
        })
    retry_clients.sort(key=lambda x: x['retry_rate'], reverse=True)

    retry_aps = []
    for bssid, rd in retry_per_ap.items():
        rate = (rd['retry'] / rd['total'] * 100) if rd['total'] > 0 else 0
        ssid_name = bmap.get(bssid, {}).get('ssid', '')
        retry_aps.append({
            'bssid': bssid, 'ssid': ssid_name,
            'total_frames': rd['total'], 'retry_frames': rd['retry'],
            'retry_rate': round(rate, 1),
        })
    retry_aps.sort(key=lambda x: x['retry_rate'], reverse=True)

    retry_analysis = {'clients': retry_clients, 'aps': retry_aps}

    # Retry problems
    for rc in retry_clients:
        if rc['retry_rate'] > 20:
            problems.append({'severity': 'high',
                'title': f'Critical retry rate on client {rc["mac"]} ({rc["retry_rate"]}%)',
                'description': f'Client {rc["mac"]} ({rc["vendor"]}) has {rc["retry_rate"]}% retry rate ({rc["retry_frames"]}/{rc["total_frames"]} frames). Avg RSSI: {rc["avg_rssi"]} dBm. Likely significant interference or very weak signal.'})
        elif rc['retry_rate'] > 10:
            problems.append({'severity': 'medium',
                'title': f'High retry rate on client {rc["mac"]} ({rc["retry_rate"]}%)',
                'description': f'Client {rc["mac"]} ({rc["vendor"]}) has {rc["retry_rate"]}% retry rate. Avg RSSI: {rc["avg_rssi"]} dBm. Check distance or interference.'})
    for ra in retry_aps:
        if ra['retry_rate'] > 15:
            problems.append({'severity': 'medium',
                'title': f'High retry rate on AP {ra["bssid"]} ({ra["retry_rate"]}%)',
                'description': f'AP {ra["bssid"]} ({ra["ssid"]}) has {ra["retry_rate"]}% retry rate. Environmental issue affecting this AP\'s coverage area.'})

    # ===== SIGNAL STRENGTH ANALYSIS =====
    signal_clients = []
    for mac, sd in signal_per_client.items():
        vals = sd['values']
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        mn, mx = min(vals), max(vals)
        std = math.sqrt(sum((v - avg) ** 2 for v in vals) / len(vals)) if len(vals) > 1 else 0
        signal_clients.append({
            'mac': mac, 'vendor': OUI_MAP.get(mac[:8], 'Unknown'),
            'bssid': sd['bssid'],
            'avg_rssi': round(avg, 1), 'min_rssi': mn, 'max_rssi': mx,
            'std_rssi': round(std, 1), 'samples': len(vals),
        })
    signal_clients.sort(key=lambda x: x['avg_rssi'])

    # Signal distribution histogram
    signal_dist = {'excellent': 0, 'good': 0, 'fair': 0, 'weak': 0, 'very_weak': 0}
    for v in all_rssi_values:
        if v > -50: signal_dist['excellent'] += 1
        elif v > -65: signal_dist['good'] += 1
        elif v > -75: signal_dist['fair'] += 1
        elif v > -85: signal_dist['weak'] += 1
        else: signal_dist['very_weak'] += 1

    signal_analysis = {
        'clients': signal_clients,
        'distribution': signal_dist,
        'total_samples': len(all_rssi_values),
    }

    # Signal problems
    for sc in signal_clients:
        if sc['avg_rssi'] < -75:
            problems.append({'severity': 'medium',
                'title': f'Weak signal on client {sc["mac"]} (avg {sc["avg_rssi"]} dBm)',
                'description': f'Client {sc["mac"]} ({sc["vendor"]}) has weak signal (avg {sc["avg_rssi"]} dBm, range {sc["min_rssi"]} to {sc["max_rssi"]}). Check AP placement or client location.'})
    # Coverage gap: many weak clients on same AP
    ap_weak_counts = {}
    for sc in signal_clients:
        if sc['avg_rssi'] < -75:
            ap_weak_counts.setdefault(sc['bssid'], 0)
            ap_weak_counts[sc['bssid']] += 1
    for bssid, count in ap_weak_counts.items():
        if count >= 3:
            ssid_name = bmap.get(bssid, {}).get('ssid', '')
            problems.append({'severity': 'high',
                'title': f'{count} weak clients on AP {bssid}',
                'description': f'{count} clients on AP {bssid} ({ssid_name}) have signal below -75 dBm. Consider AP placement.'})

    # Signal vs retry correlation
    for sc in signal_clients:
        rc_match = next((rc for rc in retry_clients if rc['mac'] == sc['mac']), None)
        if rc_match and rc_match['retry_rate'] > 10 and sc['avg_rssi'] > -65:
            problems.append({'severity': 'medium',
                'title': f'Strong signal but high retries on {sc["mac"]}',
                'description': f'Client {sc["mac"]} has good signal ({sc["avg_rssi"]} dBm) but high retry rate ({rc_match["retry_rate"]}%). This suggests interference rather than distance.'})

    # ===== CLIENT CAPABILITY ANALYSIS =====
    client_caps_data = sess.get('client_caps', {})
    relevant_caps = {}
    for mac in set(c['mac'] for c in clients):
        if mac in client_caps_data:
            relevant_caps[mac] = client_caps_data[mac]

    cap_summary = {'wifi6': 0, 'wifi5': 0, 'wifi4': 0, 'legacy': 0, 'dual_band': 0, 'single_band': 0}
    cap_clients = []
    for mac, cd in relevant_caps.items():
        if cd['has_he']:
            gen = 'Wi-Fi 6 (ax)'
            cap_summary['wifi6'] += 1
        elif cd['has_vht']:
            gen = 'Wi-Fi 5 (ac)'
            cap_summary['wifi5'] += 1
        elif cd['has_ht']:
            gen = 'Wi-Fi 4 (n)'
            cap_summary['wifi4'] += 1
        else:
            gen = 'Legacy (a/b/g)'
            cap_summary['legacy'] += 1

        bands = cd.get('bands_probed', [])
        if len(bands) > 1:
            cap_summary['dual_band'] += 1
        elif len(bands) == 1 and '2.4 GHz' in bands:
            cap_summary['single_band'] += 1

        cap_clients.append({
            'mac': mac, 'vendor': OUI_MAP.get(mac[:8], 'Unknown'),
            'wifi_gen': gen, 'has_ht': cd['has_ht'], 'has_vht': cd['has_vht'],
            'has_he': cd['has_he'], 'bands': bands,
            'rates': cd.get('supported_rates', ''),
        })
    cap_clients.sort(key=lambda x: x['wifi_gen'])

    client_cap_analysis = {'clients': cap_clients, 'summary': cap_summary}

    # Capability problems
    for cc in cap_clients:
        if cc['wifi_gen'] == 'Legacy (a/b/g)':
            problems.append({'severity': 'medium',
                'title': f'Legacy client {cc["mac"]} ({cc["vendor"]})',
                'description': f'Client only supports 802.11a/b/g. This forces the AP to use compatibility mechanisms that slow down all other clients on the same AP.'})
    if cap_summary['legacy'] == 0 and cap_summary['wifi4'] == 0 and (cap_summary['wifi5'] + cap_summary['wifi6']) > 0:
        problems.append({'severity': 'info',
            'title': 'All clients support 802.11ac or newer',
            'description': 'Consider disabling 802.11n compatibility and legacy rates for improved performance.'})

    # ===== ROAMING ANALYSIS =====
    roaming_events = sess.get('roaming_events', [])
    ft_auth = sess.get('ft_auth_frames', [])
    ft_clients = set()
    for f in ft_auth:
        sa = f.get('wlan.sa', '').upper()
        if sa:
            ft_clients.add(sa)

    # Build roaming timeline per client
    client_roam_timeline = {}
    for ev in roaming_events:
        if ev['bssid'] not in all_ap_bssids:
            continue
        if ev['is_request']:
            sa = ev['sa']
            client_roam_timeline.setdefault(sa, []).append(ev)

    roam_details = []
    sticky_clients = []
    pingpong_clients = []
    for mac, events in client_roam_timeline.items():
        events.sort(key=lambda e: float(e['epoch']) if e['epoch'] else 0)
        bssid_sequence = []
        for e in events:
            epoch = float(e['epoch']) if e['epoch'] else 0
            bssid_sequence.append({
                'bssid': e['bssid'], 'ssid': bmap.get(e['bssid'], {}).get('ssid', ''),
                'epoch': epoch, 'rssi': e['rssi'], 'is_reassoc': e['is_reassoc'],
                'used_ft': mac in ft_clients,
            })

        # Calculate roaming gaps
        for i in range(1, len(bssid_sequence)):
            if bssid_sequence[i]['bssid'] != bssid_sequence[i-1]['bssid']:
                gap_ms = (bssid_sequence[i]['epoch'] - bssid_sequence[i-1]['epoch']) * 1000
                bssid_sequence[i]['roam_time_ms'] = round(gap_ms, 1)

        if len(bssid_sequence) > 1:
            roam_details.append({'mac': mac, 'vendor': OUI_MAP.get(mac[:8], 'Unknown'), 'events': bssid_sequence})

        # Sticky client detection
        for ev_item in bssid_sequence:
            if ev_item['rssi'] is not None and ev_item['rssi'] < -75:
                sticky_clients.append({
                    'mac': mac, 'bssid': ev_item['bssid'],
                    'rssi': ev_item['rssi'],
                    'ssid': ev_item['ssid'],
                })

        # Ping-pong detection
        if len(bssid_sequence) >= 4:
            bssid_list = [e['bssid'] for e in bssid_sequence]
            times = [e['epoch'] for e in bssid_sequence]
            for i in range(len(bssid_list) - 3):
                window = bssid_list[i:i+6]
                time_window = times[i:i+6]
                if len(time_window) >= 2 and (time_window[-1] - time_window[0]) < 300:
                    unique_in_window = set(window)
                    if len(unique_in_window) == 2:
                        transitions = sum(1 for j in range(1, len(window)) if window[j] != window[j-1])
                        if transitions >= 3:
                            pair = sorted(unique_in_window)
                            pingpong_clients.append({
                                'mac': mac, 'ap1': pair[0], 'ap2': pair[1],
                                'transitions': transitions,
                            })
                            break

    # Count FT vs full roams
    total_roams = sum(len([e for e in rd['events'] if e.get('roam_time_ms') is not None]) for rd in roam_details)
    ft_roams = sum(1 for rd in roam_details for e in rd['events'] if e.get('used_ft') and e.get('is_reassoc'))

    roaming_analysis = {
        'details': roam_details,
        'sticky_clients': sticky_clients,
        'pingpong_clients': pingpong_clients,
        'total_roams': total_roams,
        'ft_roams': ft_roams,
        'total_roaming_clients': len(roam_details),
    }

    # Roaming problems
    for rd in roam_details:
        for ev_item in rd['events']:
            gap = ev_item.get('roam_time_ms')
            if gap is not None and gap > 500:
                problems.append({'severity': 'high',
                    'title': f'Slow roam for client {rd["mac"]} ({gap:.0f} ms)',
                    'description': f'Client {rd["mac"]} took {gap:.0f} ms to roam to {ev_item["bssid"]}. Over 500 ms will drop voice/video calls.'})
            elif gap is not None and gap > 150:
                problems.append({'severity': 'medium',
                    'title': f'Noticeable roam delay for {rd["mac"]} ({gap:.0f} ms)',
                    'description': f'Roam to {ev_item["bssid"]} took {gap:.0f} ms. This is noticeable on voice/video.'})
    for sc in sticky_clients[:5]:
        problems.append({'severity': 'medium',
            'title': f'Sticky client {sc["mac"]} on {sc["bssid"]}',
            'description': f'Client {sc["mac"]} stayed on {sc["bssid"]} ({sc["ssid"]}) at {sc["rssi"]} dBm. Should have roamed to a closer AP.'})
    for pp in pingpong_clients[:3]:
        problems.append({'severity': 'medium',
            'title': f'Ping-pong roaming: {pp["mac"]}',
            'description': f'Client {pp["mac"]} roaming excessively between {pp["ap1"]} and {pp["ap2"]} ({pp["transitions"]} transitions). APs likely at similar signal levels.'})

    # ===== AIRTIME ANALYSIS =====
    airtime_clients = []
    for mac, ad in airtime_per_client.items():
        pct = (ad['airtime_us'] / total_airtime_us * 100) if total_airtime_us > 0 else 0
        low_rate_pct = (ad['low_rate'] / ad['frames'] * 100) if ad['frames'] > 0 else 0
        airtime_clients.append({
            'mac': mac, 'vendor': OUI_MAP.get(mac[:8], 'Unknown'),
            'bssid': ad['bssid'],
            'airtime_pct': round(pct, 1),
            'frames': ad['frames'], 'low_rate_frames': ad['low_rate'],
            'low_rate_pct': round(low_rate_pct, 1),
        })
    airtime_clients.sort(key=lambda x: x['airtime_pct'], reverse=True)

    # Rate distribution
    rate_dist = {'legacy': 0, 'ht': 0, 'vht': 0, 'he': 0}
    for r in all_rates:
        if r <= 54:
            rate_dist['legacy'] += 1
        elif r <= 300:
            rate_dist['ht'] += 1
        elif r <= 1733:
            rate_dist['vht'] += 1
        else:
            rate_dist['he'] += 1

    # Management overhead
    mgt_stats = sess.get('mgt_stats', {})
    total_all = sess.get('total_all_frames', 0)
    mgt_overhead_pct = round(mgt_stats.get('total', 0) / total_all * 100, 1) if total_all > 0 else 0
    beacon_pct = round(mgt_stats.get('beacon', 0) / total_all * 100, 1) if total_all > 0 else 0

    # Probe storm detection
    probe_counts = sess.get('probe_counts', {})
    probe_storms = []
    for mac, pc in probe_counts.items():
        if pc['times']:
            duration = max(pc['times']) - min(pc['times'])
            if duration > 0:
                per_min = pc['count'] / (duration / 60)
                if per_min > 100:
                    probe_storms.append({'mac': mac, 'count': pc['count'],
                        'per_min': round(per_min, 0), 'duration_s': round(duration, 0)})

    airtime_analysis = {
        'clients': airtime_clients[:50],
        'rate_distribution': rate_dist,
        'total_rates': len(all_rates),
        'mgt_overhead_pct': mgt_overhead_pct,
        'beacon_pct': beacon_pct,
        'probe_storms': probe_storms,
    }

    # Airtime problems
    low_rate_total = sum(1 for r in all_rates if r < 24)
    if all_rates and (low_rate_total / len(all_rates)) > 0.2:
        problems.append({'severity': 'medium',
            'title': f'High proportion of low data rates ({round(low_rate_total / len(all_rates) * 100)}%)',
            'description': f'{low_rate_total} of {len(all_rates)} data frames use rates below 24 Mbps. Check for legacy clients, weak signals, or interference.'})
    if beacon_pct > 10:
        problems.append({'severity': 'medium',
            'title': f'High beacon overhead ({beacon_pct}% of frames)',
            'description': f'Beacons account for {beacon_pct}% of all captured frames. Too many SSIDs per AP increases beacon overhead.'})
    for ps in probe_storms[:3]:
        problems.append({'severity': 'low',
            'title': f'Probe request storm from {ps["mac"]}',
            'description': f'Client {ps["mac"]} sent {ps["count"]} probe requests ({ps["per_min"]:.0f}/min). Excessive probing wastes airtime.'})
    for ac in airtime_clients[:3]:
        if ac['airtime_pct'] > 30:
            problems.append({'severity': 'medium',
                'title': f'Airtime hog: {ac["mac"]} ({ac["airtime_pct"]}%)',
                'description': f'Client {ac["mac"]} ({ac["vendor"]}) consuming {ac["airtime_pct"]}% of airtime. This impacts all other clients on the same AP.'})

    # ===== DHCP & DNS ANALYSIS =====
    dhcp_transactions = sess.get('dhcp_timing', {})
    dhcp_results = []
    # DHCP type mapping: 1=Discover, 2=Offer, 3=Request, 5=ACK, 6=NAK
    for mac, msgs in dhcp_transactions.items():
        discovers = [m for m in msgs if m['type'] in ('1',)]
        acks = [m for m in msgs if m['type'] in ('5',)]
        naks = [m for m in msgs if m['type'] in ('6',)]
        offers = [m for m in msgs if m['type'] in ('2',)]

        if discovers:
            first_discover = min(discovers, key=lambda m: m['time'])
            if acks:
                last_ack = min(acks, key=lambda m: m['time'])
                transaction_time = last_ack['time'] - first_discover['time']
                dhcp_results.append({
                    'mac': mac, 'ip': last_ack.get('ip', ''),
                    'server': last_ack.get('server', ''),
                    'transaction_time': round(transaction_time, 3),
                    'status': 'completed',
                    'discovers': len(discovers), 'offers': len(offers),
                    'naks': len(naks),
                })
            else:
                dhcp_results.append({
                    'mac': mac, 'ip': '',
                    'server': '',
                    'transaction_time': None,
                    'status': 'timeout' if not offers else 'incomplete',
                    'discovers': len(discovers), 'offers': len(offers),
                    'naks': len(naks),
                })
    dhcp_results.sort(key=lambda x: x.get('transaction_time') or 999, reverse=True)

    dns_timing = sess.get('dns_timing', [])
    dns_servers = {}
    dns_slow = []
    dns_timeouts = 0
    for d in dns_timing:
        server = d.get('server', 'unknown')
        dns_servers.setdefault(server, {'total': 0, 'latencies': [], 'timeouts': 0})
        dns_servers[server]['total'] += 1
        if d['latency_ms'] is not None:
            dns_servers[server]['latencies'].append(d['latency_ms'])
            if d['latency_ms'] > 200:
                dns_slow.append(d)
        else:
            dns_servers[server]['timeouts'] += 1
            dns_timeouts += 1

    dns_server_stats = []
    for server, stats in dns_servers.items():
        avg_lat = round(sum(stats['latencies']) / len(stats['latencies']), 1) if stats['latencies'] else None
        dns_server_stats.append({
            'server': server, 'queries': stats['total'],
            'avg_latency_ms': avg_lat,
            'max_latency_ms': round(max(stats['latencies']), 1) if stats['latencies'] else None,
            'timeouts': stats['timeouts'],
        })

    dhcp_dns_analysis = {
        'dhcp': dhcp_results,
        'dns_servers': dns_server_stats,
        'dns_slow_queries': dns_slow[:20],
        'dns_total_queries': len(dns_timing),
        'dns_timeouts': dns_timeouts,
    }

    # DHCP/DNS problems
    for dr in dhcp_results:
        if dr['status'] == 'timeout':
            problems.append({'severity': 'high',
                'title': f'DHCP timeout for client {dr["mac"]}',
                'description': f'Client {dr["mac"]} sent {dr["discovers"]} DHCP Discover(s) but received no Offer. DHCP server unreachable.'})
        elif dr['transaction_time'] is not None and dr['transaction_time'] > 5:
            problems.append({'severity': 'high',
                'title': f'Slow DHCP for {dr["mac"]} ({dr["transaction_time"]:.1f}s)',
                'description': f'DHCP transaction took {dr["transaction_time"]:.1f}s for client {dr["mac"]}. Check DHCP server.'})
        elif dr['transaction_time'] is not None and dr['transaction_time'] > 1:
            problems.append({'severity': 'medium',
                'title': f'Slow DHCP for {dr["mac"]} ({dr["transaction_time"]:.1f}s)',
                'description': f'DHCP took {dr["transaction_time"]:.1f}s (normal is under 1s). May indicate DHCP server load or network delay.'})
        if dr['naks'] > 0:
            problems.append({'severity': 'medium',
                'title': f'DHCP NAK for client {dr["mac"]}',
                'description': f'Client received {dr["naks"]} DHCP NAK(s). Address conflict or configuration issue.'})

    for ds in dns_server_stats:
        if ds['avg_latency_ms'] is not None and ds['avg_latency_ms'] > 200:
            problems.append({'severity': 'medium',
                'title': f'Slow DNS server {ds["server"]} (avg {ds["avg_latency_ms"]} ms)',
                'description': f'DNS server {ds["server"]} has average latency of {ds["avg_latency_ms"]} ms ({ds["queries"]} queries). Normal is under 50 ms.'})
        if ds['timeouts'] > 5:
            problems.append({'severity': 'high',
                'title': f'DNS timeouts from {ds["server"]} ({ds["timeouts"]} timeouts)',
                'description': f'DNS server {ds["server"]} had {ds["timeouts"]} unanswered queries out of {ds["queries"]}.'})

    # ===== HEALTH SCORE =====
    score = 100
    penalty_log = []

    # Security scoring
    for ap in ap_groups:
        for bi in ap['bssids']:
            sec = bi.get('security', '')
            if 'Open' in sec:
                score -= 20; penalty_log.append('Open network (-20)')
            elif 'WEP' in sec:
                score -= 15; penalty_log.append('WEP (-15)')
            elif 'WPA3' in sec:
                pass  # Best
            elif 'WPA2' in sec:
                score -= 2; penalty_log.append('WPA2 not WPA3 (-2)')

    # PMF - check from bssid details in ap_groups (we don't store PMF in pcap analysis per-bssid yet, skip)

    # Channel plan - already checked via problems
    # Retry rate
    overall_retry = 0
    total_df = sum(rd['total'] for rd in retry_per_ap.values())
    total_rf = sum(rd['retry'] for rd in retry_per_ap.values())
    if total_df > 0:
        overall_retry = total_rf / total_df * 100
        if overall_retry > 20: score -= 15; penalty_log.append(f'Very high retry rate {overall_retry:.0f}% (-15)')
        elif overall_retry > 10: score -= 8; penalty_log.append(f'High retry rate {overall_retry:.0f}% (-8)')
        elif overall_retry > 5: score -= 3; penalty_log.append(f'Moderate retry rate {overall_retry:.0f}% (-3)')

    # Client signal
    weak_clients = sum(1 for sc in signal_clients if sc['avg_rssi'] < -75)
    if weak_clients > 5: score -= 10; penalty_log.append(f'{weak_clients} weak signal clients (-10)')
    elif weak_clients > 2: score -= 5; penalty_log.append(f'{weak_clients} weak signal clients (-5)')

    # Firmware age
    for ap in ap_groups:
        for bi in ap['bssids']:
            if bi['uptime_s'] > 365 * 86400:
                score -= 5; penalty_log.append('Very long AP uptime (-5)')
                break

    # SSID count
    if len(related_ssids) > 6: score -= 10; penalty_log.append(f'{len(related_ssids)} SSIDs (-10)')
    elif len(related_ssids) > 4: score -= 5; penalty_log.append(f'{len(related_ssids)} SSIDs (-5)')

    # Roaming support
    for ap in ap_groups:
        for bi in ap['bssids']:
            if bi['ssid'] == ssid:
                if not bi['has_11r'] and len(ap_groups) > 1:
                    score -= 3; penalty_log.append('No 802.11r (-3)')
                if not bi['has_11k'] and len(ap_groups) > 1:
                    score -= 2; penalty_log.append('No 802.11k (-2)')
                break

    # Legacy rates
    if any(p['title'].startswith('Legacy bit rates') for p in problems):
        score -= 5; penalty_log.append('Legacy bit rates enabled (-5)')

    # Critical/high problems penalty
    crit_count = sum(1 for p in problems if p['severity'] == 'critical')
    high_count = sum(1 for p in problems if p['severity'] == 'high')
    if crit_count: score -= crit_count * 5
    if high_count > 3: score -= 5

    score = max(0, min(100, score))
    if score >= 90: grade = 'A'
    elif score >= 75: grade = 'B'
    elif score >= 60: grade = 'C'
    elif score >= 45: grade = 'D'
    else: grade = 'F'

    health_score = {'score': score, 'grade': grade, 'penalties': penalty_log}

    sev_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
    problems.sort(key=lambda p: sev_order.get(p.get('severity', 'info'), 5))

    ws_filter = ' || '.join([f'wlan.bssid == {b.lower()}' for b in sorted(all_ap_bssids)])

    return {
        'ssid': ssid, 'vendor': vendor,
        'ap_groups': ap_groups, 'related_ssids': sorted(related_ssids),
        'clients': clients, 'roaming': roaming,
        'wired_hosts': wired, 'eapol_events': eapol,
        'certificates': certs, 'problems': problems,
        'power_ranges': power_ranges, 'wireshark_filter': ws_filter,
        'retry_analysis': retry_analysis,
        'signal_analysis': signal_analysis,
        'client_capabilities': client_cap_analysis,
        'roaming_analysis': roaming_analysis,
        'airtime_analysis': airtime_analysis,
        'dhcp_dns_analysis': dhcp_dns_analysis,
        'health_score': health_score,
        'summary': {
            'total_aps': len(ap_groups),
            'total_bssids': len(all_ap_bssids),
            'total_clients': len(set(c['mac'] for c in clients)),
            'total_ssids': len(related_ssids),
            'vendor_name': vendor.capitalize(),
            'health_score': score,
            'health_grade': grade,
        }
    }

@app.route('/analyzer')
def analyzer_page():
    return app.send_static_file('analyzer.html')

@app.route('/analyzer/upload', methods=['POST'])
def analyzer_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'No file selected'}), 400
    if not (f.filename.endswith('.pcap') or f.filename.endswith('.pcapng')):
        return jsonify({'error': 'Please upload a .pcap or .pcapng file'}), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    cleanup_old_sessions()

    sid = str(uuid.uuid4())[:8]
    fname = re.sub(r'[^a-zA-Z0-9._-]', '', f.filename)[:100]
    pcap_path = os.path.join(UPLOAD_DIR, f'{sid}_{fname}')
    f.save(pcap_path)

    sz = round(os.path.getsize(pcap_path) / (1024 * 1024), 1)

    analyzer_sessions[sid] = {
        'status': 'processing', 'progress': 'Starting...', 'progress_pct': 0,
        'pcap_path': pcap_path, 'filename': fname, 'file_size_mb': sz,
        'upload_time': datetime.now().isoformat(),
        'ssid_list': [], 'bssid_map': {}, 'hidden_ssids': {}, 'hidden_count': 0,
        'total_bssids': 0, 'eapol_events': [], 'client_assoc': {},
        'wired_hosts': {}, 'eap_identities': {}, 'certificates': [],
        'data_frame_stats': {}, 'client_caps': {}, 'roaming_events': [],
        'dhcp_timing': [], 'dns_timing': [],
    }

    t = threading.Thread(target=phase1_processing, args=(sid,))
    t.daemon = True
    t.start()

    return jsonify({'session_id': sid, 'filename': fname, 'file_size_mb': sz})

@app.route('/analyzer/status/<session_id>')
def analyzer_status(session_id):
    sess = analyzer_sessions.get(session_id)
    if not sess:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify({
        'status': sess['status'], 'progress': sess['progress'],
        'progress_pct': sess.get('progress_pct', 0),
        'filename': sess.get('filename', ''), 'file_size_mb': sess.get('file_size_mb', 0),
        'ssid_list': sess.get('ssid_list', []),
        'total_bssids': sess.get('total_bssids', 0),
        'hidden_count': sess.get('hidden_count', 0),
    })

@app.route('/analyzer/analyze', methods=['POST'])
def analyzer_analyze():
    data = request.get_json()
    sid = data.get('session_id')
    ssid = data.get('ssid')
    vendor = data.get('vendor', 'generic')
    if not sid or not ssid:
        return jsonify({'error': 'Missing session_id or ssid'}), 400
    if vendor not in VENDOR_GROUPING:
        vendor = 'generic'
    result = phase2_analysis(sid, ssid, vendor)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route('/analyzer/report', methods=['POST'])
def analyzer_report():
    data = request.get_json()
    sid = data.get('session_id')
    ssid = data.get('ssid')
    vendor = data.get('vendor', 'generic')
    if not sid or not ssid:
        return jsonify({'error': 'Missing session_id or ssid'}), 400
    if vendor not in VENDOR_GROUPING:
        vendor = 'generic'
    result = phase2_analysis(sid, ssid, vendor)
    if 'error' in result:
        return jsonify(result), 400

    hs = result.get('health_score', {})
    grade = hs.get('grade', '?')
    score = hs.get('score', 0)
    penalties = hs.get('penalties', [])
    problems = result.get('problems', [])
    summary = result.get('summary', {})
    retry = result.get('retry_analysis', {})
    signal = result.get('signal_analysis', {})
    caps = result.get('client_capabilities', {})
    roam = result.get('roaming_analysis', {})
    airtime = result.get('airtime_analysis', {})
    dhcp_dns = result.get('dhcp_dns_analysis', {})

    grade_colors = {'A': '#198754', 'B': '#0d6efd', 'C': '#ffc107', 'D': '#fd7e14', 'F': '#dc3545'}
    gc = grade_colors.get(grade, '#666')

    def esc(s):
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    sev_colors = {'critical': '#dc3545', 'high': '#fd7e14', 'medium': '#ffc107', 'low': '#0dcaf0', 'info': '#6c757d'}

    problems_html = ''
    for p in problems:
        sc = sev_colors.get(p['severity'], '#ccc')
        problems_html += f'<div style="padding:0.6rem;margin-bottom:0.4rem;border-left:4px solid {sc};background:#fafafa;border-radius:0.25rem;"><strong style="color:{sc};">[{esc(p["severity"].upper())}]</strong> <strong>{esc(p["title"])}</strong><br><span style="color:#555;font-size:0.9rem;">{esc(p["description"])}</span></div>'

    # AP inventory
    ap_html = '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;"><tr style="background:#e9ecef;"><th style="padding:0.4rem;">AP</th><th>BSSIDs</th><th>Channels</th><th>Security</th><th>Clients</th></tr>'
    for ap in result.get('ap_groups', []):
        channels = set()
        secs = set()
        for bi in ap['bssids']:
            if bi['channel']: channels.add(f'{bi["band"]} Ch{bi["channel"]}')
            secs.add(bi['security'])
        ap_html += f'<tr style="border-top:1px solid #ddd;"><td style="padding:0.4rem;">{esc(ap["name"])}</td><td>{len(ap["bssids"])}</td><td>{esc(", ".join(sorted(channels)))}</td><td>{esc(", ".join(sorted(secs)))}</td><td>{ap["total_stations"]}</td></tr>'
    ap_html += '</table>'

    # Client table
    client_html = '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;"><tr style="background:#e9ecef;"><th style="padding:0.4rem;">MAC</th><th>Vendor</th><th>SSID</th><th>Frames</th></tr>'
    for c in result.get('clients', [])[:30]:
        client_html += f'<tr style="border-top:1px solid #ddd;"><td style="padding:0.4rem;">{esc(c["mac"])}</td><td>{esc(c["vendor"])}</td><td>{esc(c["ssid"])}</td><td>{c["frames"]}</td></tr>'
    client_html += '</table>'

    # Retry summary table
    retry_html = ''
    rc_list = retry.get('clients', [])
    if rc_list:
        retry_html = '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;"><tr style="background:#e9ecef;"><th style="padding:0.4rem;">Client</th><th>Retry Rate</th><th>Frames</th><th>Avg RSSI</th></tr>'
        for rc in rc_list[:20]:
            color = '#dc3545' if rc['retry_rate'] > 20 else '#fd7e14' if rc['retry_rate'] > 10 else '#333'
            retry_html += f'<tr style="border-top:1px solid #ddd;"><td style="padding:0.4rem;">{esc(rc["mac"])}</td><td style="color:{color};font-weight:bold;">{rc["retry_rate"]}%</td><td>{rc["total_frames"]}</td><td>{rc["avg_rssi"]} dBm</td></tr>'
        retry_html += '</table>'

    # Recommendations
    recs = []
    sev_counts = {}
    for p in problems:
        sev_counts[p['severity']] = sev_counts.get(p['severity'], 0) + 1
    if sev_counts.get('critical', 0):
        recs.append(f'Address {sev_counts["critical"]} critical issue(s) immediately.')
    if sev_counts.get('high', 0):
        recs.append(f'Investigate {sev_counts["high"]} high severity issue(s).')
    if any(p['title'].startswith('Legacy bit rates') for p in problems):
        recs.append('Disable legacy bit rates (1, 2, 5.5, 11 Mbps) to improve BSS performance.')
    if any(p['title'].startswith('Missing roaming') for p in problems):
        recs.append('Enable 802.11k/r/v for faster roaming.')
    if any('retry rate' in p['title'].lower() for p in problems):
        recs.append('Investigate high retry rates: check for interference sources and client distances.')
    if any('weak signal' in p['title'].lower() for p in problems):
        recs.append('Review AP placement for coverage gaps.')
    recs_html = ''.join(f'<li>{esc(r)}</li>' for r in recs) if recs else '<li>No specific recommendations.</li>'

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Wi-Fi Analysis Report - {esc(ssid)}</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 1000px; margin: 0 auto; padding: 2rem; color: #333; font-size: 0.9rem; }}
h1 {{ color: #1a1a2e; border-bottom: 3px solid #0d6efd; padding-bottom: 0.5rem; }}
h2 {{ color: #0d6efd; margin-top: 2rem; border-bottom: 1px solid #dee2e6; padding-bottom: 0.3rem; }}
.grade {{ display: inline-block; width: 80px; height: 80px; border-radius: 50%; background: {gc}; color: white; text-align: center; line-height: 80px; font-size: 2.5rem; font-weight: bold; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.5rem; margin: 1rem 0; }}
.summary-card {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 0.25rem; padding: 0.75rem; text-align: center; }}
.summary-card .val {{ font-size: 1.4rem; font-weight: bold; color: #0d6efd; }}
.summary-card .lbl {{ font-size: 0.8rem; color: #666; }}
.footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #dee2e6; color: #999; font-size: 0.8rem; text-align: center; }}
@media print {{ body {{ font-size: 0.8rem; }} h1 {{ font-size: 1.3rem; }} }}
</style></head><body>
<h1>Wi-Fi Analysis Report</h1>
<p><strong>SSID:</strong> {esc(ssid)} | <strong>Generated:</strong> {now} | <strong>AP Grouping:</strong> {esc(vendor.capitalize())}</p>

<h2>Executive Summary</h2>
<div style="display:flex;align-items:center;gap:1.5rem;margin:1rem 0;">
<div class="grade">{grade}</div>
<div><strong>Health Score: {score}/100</strong><br>
{summary.get("total_aps",0)} Access Points, {summary.get("total_bssids",0)} BSSIDs, {summary.get("total_clients",0)} Clients, {summary.get("total_ssids",0)} SSIDs<br>
{len(problems)} problem(s) detected</div></div>
<div class="summary-grid">
<div class="summary-card"><div class="val">{summary.get("total_aps",0)}</div><div class="lbl">Access Points</div></div>
<div class="summary-card"><div class="val">{summary.get("total_clients",0)}</div><div class="lbl">Clients</div></div>
<div class="summary-card"><div class="val">{len([p for p in problems if p["severity"]=="critical"])}</div><div class="lbl">Critical</div></div>
<div class="summary-card"><div class="val">{len([p for p in problems if p["severity"]=="high"])}</div><div class="lbl">High</div></div>
<div class="summary-card"><div class="val">{len([p for p in problems if p["severity"]=="medium"])}</div><div class="lbl">Medium</div></div>
<div class="summary-card"><div class="val">{len([p for p in problems if p["severity"]=="low"])}</div><div class="lbl">Low</div></div>
</div>

<h2>Network Inventory</h2>
{ap_html}

<h2>Problems ({len(problems)})</h2>
{problems_html if problems_html else '<p style="color:#198754;font-weight:bold;">No problems detected</p>'}

<h2>Client Inventory ({summary.get("total_clients",0)})</h2>
{client_html}

<h2>Retry Analysis</h2>
{retry_html if retry_html else '<p>No retry data available.</p>'}

<h2>Recommendations</h2>
<ol>{recs_html}</ol>

<h2>Health Score Breakdown</h2>
<ul>{"".join(f"<li>{esc(p)}</li>" for p in penalties) if penalties else "<li>No penalties - perfect score!</li>"}</ul>

<div class="footer">Generated by Wi-Fi Pcap Analyser | {now}</div>
</body></html>'''

    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

# --- Adapter Config Page ---

@app.route('/config')
def config_page():
    return app.send_static_file('config.html')

def _get_phy_bands(phy_name):
    """Get supported bands and frequencies for a phy."""
    bands = {}
    try:
        result = subprocess.run(['iw', 'phy', phy_name, 'info'],
                                capture_output=True, text=True, timeout=5)
        current_band = None
        for line in result.stdout.splitlines():
            m = re.match(r'\s+Band (\d+):', line)
            if m:
                band_num = int(m.group(1))
                if band_num == 1: current_band = '2.4 GHz'
                elif band_num == 2: current_band = '5 GHz'
                elif band_num == 4: current_band = '6 GHz'
                else: current_band = None
                if current_band:
                    bands[current_band] = []
                continue
            if current_band:
                m_freq = re.match(r'\s+\* (\d+) MHz \[(\d+)\](.*)$', line)
                if m_freq:
                    freq = int(m_freq.group(1))
                    ch = m_freq.group(2)
                    flags = m_freq.group(3).strip()
                    disabled = 'disabled' in flags
                    if not disabled:
                        bands[current_band].append({'freq': freq, 'channel': ch})
        # Check if monitor mode is supported
        supports_monitor = 'monitor' in result.stdout.lower().split('supported interface modes')[1] if 'Supported interface modes' in result.stdout else False
    except Exception:
        supports_monitor = False
    return bands, supports_monitor

@app.route('/api/config/adapters', methods=['GET'])
def api_config_adapters():
    """Detect all adapters, their phy, bands, mode, and monitor capability."""
    try:
        interfaces = get_interfaces_info()
    except Exception:
        return jsonify({'error': 'Cannot read interface info'}), 500

    adapters = []
    seen_phys = set()
    for iface in interfaces:
        phy = iface['phy']
        name = iface['interface']
        mode = iface['type']

        # Skip non-wlan interfaces
        if not name.startswith('wlan'):
            continue

        is_builtin = (phy == 'phy#0' or name == 'wlan0')
        phy_name = phy.replace('#', '')  # phy#1 -> phy1

        # Get band info (only once per phy)
        if phy not in seen_phys:
            bands, supports_monitor = _get_phy_bands(phy_name)
            seen_phys.add(phy)
        else:
            bands, supports_monitor = {}, True

        band_list = sorted(bands.keys())

        adapters.append({
            'interface': name,
            'phy': phy,
            'mode': mode,
            'is_builtin': is_builtin,
            'is_monitor': mode == 'monitor',
            'bands': band_list,
            'band_channels': bands,
            'supports_monitor': supports_monitor,
            'vendor': OUI_MAP.get(name[:8], ''),  # doesn't apply to interface names
        })

    return jsonify({'adapters': adapters})

@app.route('/api/config/setup_monitor', methods=['POST'])
def api_config_setup_monitor():
    """Put an adapter into monitor mode using airmon-ng (same as capture page)."""
    data = request.get_json()
    interface = data.get('interface', '')
    if not interface or not interface.startswith('wlan') or interface == 'wlan0':
        return jsonify({'error': 'Invalid adapter. Cannot use wlan0.'}), 400

    try:
        interfaces = get_interfaces_info()
        iface_info = next((i for i in interfaces if i['interface'] == interface), None)
        if not iface_info:
            return jsonify({'error': f'Interface {interface} not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    mon_name = interface + 'mon' if not interface.endswith('mon') else interface

    # Check if already in monitor mode
    existing_mon = next((i for i in interfaces if i['interface'] == mon_name and i['type'] == 'monitor'), None)
    if existing_mon:
        return jsonify({'ok': True, 'interface': mon_name, 'message': f'{mon_name} already in monitor mode'})
    if iface_info['type'] == 'monitor':
        return jsonify({'ok': True, 'interface': interface, 'message': f'{interface} already in monitor mode'})

    # Use airmon-ng start — same proven method as the capture page
    try:
        subprocess.run(['sudo', 'airmon-ng', 'start', interface],
                       capture_output=True, text=True, check=True, timeout=15)
        return jsonify({'ok': True, 'interface': mon_name,
                       'message': f'{interface} set to monitor mode ({mon_name})'})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'airmon-ng failed: {e.stderr.strip()}'}), 500

@app.route('/api/config/disable_monitor', methods=['POST'])
def api_config_disable_monitor():
    """Revert a monitor-mode interface back to managed mode."""
    data = request.get_json()
    interface = data.get('interface', '')
    if not interface or interface == 'wlan0':
        return jsonify({'error': 'Invalid adapter'}), 400

    try:
        subprocess.run(['sudo', 'airmon-ng', 'stop', interface],
                       capture_output=True, text=True, check=True, timeout=15)
        managed_name = interface.replace('mon', '') if interface.endswith('mon') else interface
        return jsonify({'ok': True, 'message': f'{interface} reverted to {managed_name} (managed mode)'})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'airmon-ng stop failed: {e.stderr.strip()}'}), 500

@app.route('/api/config/set_channel', methods=['POST'])
def api_config_set_channel():
    """Set a monitor adapter to a specific channel/frequency."""
    data = request.get_json()
    interface = data.get('interface', '')
    freq = data.get('freq', '')
    bandwidth = data.get('bandwidth', 'HT20')
    if not interface or not freq:
        return jsonify({'error': 'Missing interface or freq'}), 400
    try:
        cmd = ['sudo', 'iw', 'dev', interface, 'set', 'freq', str(freq), bandwidth]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            # Retry without bandwidth
            cmd2 = ['sudo', 'iw', 'dev', interface, 'set', 'freq', str(freq)]
            result = subprocess.run(cmd2, capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return jsonify({'error': result.stderr.strip()}), 500
        return jsonify({'ok': True, 'message': f'{interface} set to {freq} MHz'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/auto_setup', methods=['POST'])
def api_config_auto_setup():
    """Auto-detect USB adapters and assign bands. Keeps wlan0 untouched."""
    try:
        interfaces = get_interfaces_info()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Find all USB adapters (not phy#0/wlan0)
    usb_adapters = []
    for iface in interfaces:
        if iface['phy'] == 'phy#0' or iface['interface'] == 'wlan0':
            continue
        if not iface['interface'].startswith('wlan'):
            continue
        if iface['interface'].endswith('mon'):
            continue  # Skip existing monitor interfaces
        phy_name = iface['phy'].replace('#', '')
        bands, supports_monitor = _get_phy_bands(phy_name)
        if supports_monitor:
            usb_adapters.append({
                'interface': iface['interface'],
                'phy': iface['phy'],
                'phy_name': phy_name,
                'mode': iface['type'],
                'bands': bands,
            })

    if not usb_adapters:
        return jsonify({'error': 'No USB Wi-Fi adapters found'}), 400

    results = []
    band_assigned = set()

    # Strategy: assign one adapter per band if possible
    # Priority: 6 GHz first (rarest), then 5 GHz, then 2.4 GHz
    for target_band in ['6 GHz', '5 GHz', '2.4 GHz']:
        for adapter in usb_adapters:
            if adapter['interface'] in [r['interface'] for r in results]:
                continue  # Already assigned
            if target_band in adapter['bands'] and target_band not in band_assigned:
                iface_name = adapter['interface']
                mon_name = iface_name + 'mon'
                try:
                    # Check if already in monitor mode
                    existing = next((i for i in interfaces if i['interface'] == mon_name and i['type'] == 'monitor'), None)
                    if not existing:
                        # Use airmon-ng — same proven method as capture page
                        subprocess.run(['sudo', 'airmon-ng', 'start', iface_name],
                                       capture_output=True, text=True, check=True, timeout=15)

                    # Set to first channel of the assigned band
                    channels = adapter['bands'].get(target_band, [])
                    if channels:
                        freq = channels[0]['freq']
                        bw_info = FREQ_TO_CHANNEL.get(freq, {})
                        bw = bw_info.get('bandwidth', 'HT20')
                        subprocess.run(['sudo', 'iw', 'dev', mon_name, 'set', 'freq', str(freq), bw],
                                       capture_output=True, text=True, timeout=3)

                    band_assigned.add(target_band)
                    results.append({
                        'interface': mon_name,
                        'phy': adapter['phy'],
                        'assigned_band': target_band,
                        'status': 'ok',
                    })
                except Exception as e:
                    results.append({
                        'interface': adapter['interface'],
                        'assigned_band': target_band,
                        'status': 'error',
                        'error': str(e),
                    })

    # If only 1 adapter and it supports multiple bands, note it will channel-hop
    if len(usb_adapters) == 1 and len(results) <= 1:
        adapter = usb_adapters[0]
        all_bands = list(adapter['bands'].keys())
        if len(results) == 1:
            results[0]['note'] = f'Single adapter covers {", ".join(all_bands)} via channel hopping'
            results[0]['all_bands'] = all_bands

    return jsonify({
        'ok': True,
        'adapters_found': len(usb_adapters),
        'assignments': results,
        'bands_covered': sorted(band_assigned),
        'wlan0': 'untouched (managed mode for connectivity)',
    })

# Channel analysis page
@app.route('/channels')
def channels_page():
    return app.send_static_file('channels.html')

# --- AP Model Library ---

@app.route('/ap-models')
def ap_models_page():
    return app.send_static_file('ap_models.html')

@app.route('/api/ap-models', methods=['GET'])
def api_ap_models():
    query = request.args.get('q', '')
    vendor = request.args.get('vendor', '')
    wifi_gen = request.args.get('wifi_gen', '')

    results = AP_MODELS
    if query:
        results = search_models(query)
    if vendor:
        results = [ap for ap in results if ap['vendor'].lower() == vendor.lower()]
    if wifi_gen:
        results = [ap for ap in results if ap['wifi_gen'].lower() == wifi_gen.lower()]

    return jsonify({
        'models': results,
        'count': len(results),
        'vendors': get_vendors(),
        'wifi_gen_summary': get_wifi_gen_summary(),
    })

# --- Capacity Planning ---

@app.route('/capacity')
def capacity_page():
    return app.send_static_file('capacity.html')

@app.route('/api/capacity/reference', methods=['GET'])
def api_capacity_reference():
    ref = get_reference_data()
    # Also include AP models for the AP selector
    ref['ap_models'] = AP_MODELS
    return jsonify(ref)

@app.route('/api/capacity/calculate', methods=['POST'])
def api_capacity_calculate():
    params = request.get_json()
    if not params:
        return jsonify({'error': 'No parameters provided'}), 400
    result = calculate_capacity(params)
    return jsonify(result)

# --- Survey (Heatmap) ---

survey_projects = {}

@app.route('/survey')
def survey_page():
    return app.send_static_file('survey.html')

@app.route('/survey/create', methods=['POST'])
def survey_create():
    data = request.get_json() or {}
    pid = str(uuid.uuid4())[:8]
    survey_projects[pid] = {
        'id': pid,
        'name': data.get('name', 'Untitled Survey'),
        'created': datetime.now().isoformat(),
        'floor_plan': None,
        'scale_px_per_m': None,
        'points': [],
    }
    return jsonify({'id': pid, 'name': survey_projects[pid]['name']})

@app.route('/survey/upload_plan/<pid>', methods=['POST'])
def survey_upload_plan(pid):
    proj = survey_projects.get(pid)
    if not proj:
        return jsonify({'error': 'Project not found'}), 404
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['file']
    os.makedirs(os.path.join(UPLOAD_DIR, 'survey'), exist_ok=True)
    ext = os.path.splitext(f.filename)[1] or '.png'
    plan_path = os.path.join(UPLOAD_DIR, 'survey', f'{pid}_plan{ext}')
    f.save(plan_path)
    proj['floor_plan'] = plan_path
    return jsonify({'ok': True, 'path': f'/survey/plan_image/{pid}'})

@app.route('/survey/plan_image/<pid>')
def survey_plan_image(pid):
    proj = survey_projects.get(pid)
    if not proj or not proj.get('floor_plan'):
        return jsonify({'error': 'No floor plan'}), 404
    return send_file(proj['floor_plan'])

@app.route('/survey/set_scale/<pid>', methods=['POST'])
def survey_set_scale(pid):
    proj = survey_projects.get(pid)
    if not proj:
        return jsonify({'error': 'Project not found'}), 404
    data = request.get_json()
    proj['scale_px_per_m'] = data.get('px_per_m')
    return jsonify({'ok': True, 'scale': proj['scale_px_per_m']})

@app.route('/survey/record_point/<pid>', methods=['POST'])
def survey_record_point(pid):
    proj = survey_projects.get(pid)
    if not proj:
        return jsonify({'error': 'Project not found'}), 404
    data = request.get_json()
    x = data.get('x')
    y = data.get('y')
    networks = data.get('networks', [])
    proj['points'].append({
        'x': x, 'y': y,
        'networks': networks,
        'timestamp': datetime.now().isoformat(),
    })
    return jsonify({'ok': True, 'point_count': len(proj['points'])})

@app.route('/survey/points/<pid>')
def survey_points(pid):
    proj = survey_projects.get(pid)
    if not proj:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify({'points': proj['points'], 'scale': proj.get('scale_px_per_m')})

@app.route('/survey/heatmap/<pid>')
def survey_heatmap(pid):
    proj = survey_projects.get(pid)
    if not proj:
        return jsonify({'error': 'Project not found'}), 404
    points = proj['points']
    if len(points) < 2:
        return jsonify({'error': 'Need at least 2 measurement points'}), 400

    bssid_filter = request.args.get('bssid', '')
    layer = request.args.get('layer', 'signal')

    # Collect all BSSIDs seen
    all_bssids = {}
    for pt in points:
        for net in pt['networks']:
            b = net.get('bssid', '')
            if b:
                all_bssids.setdefault(b, {'ssid': net.get('ssid', ''), 'count': 0})
                all_bssids[b]['count'] += 1

    # Build per-point signal values
    point_data = []
    for pt in points:
        if layer == 'signal':
            if bssid_filter:
                vals = [n['signal'] for n in pt['networks'] if n.get('bssid') == bssid_filter and n.get('signal')]
                val = max(vals) if vals else None
            else:
                vals = [n['signal'] for n in pt['networks'] if n.get('signal')]
                val = max(vals) if vals else None
        elif layer == 'ap_count':
            val = len(pt['networks'])
        elif layer == 'channel':
            channels = set(n.get('channel') for n in pt['networks'] if n.get('channel'))
            val = len(channels)
        else:
            val = None

        if val is not None:
            point_data.append({'x': pt['x'], 'y': pt['y'], 'value': val})

    return jsonify({
        'points': point_data,
        'bssids': all_bssids,
        'layer': layer,
        'point_count': len(point_data),
    })

# --- File Manager ---

@app.route('/files')
def files_page():
    return app.send_static_file('files.html')

@app.route('/files/list', methods=['GET'])
def files_list():
    try:
        # Disk space
        st = os.statvfs(RUNNING_HOME)
        total_gb = round((st.f_frsize * st.f_blocks) / (1024**3), 1)
        free_gb = round((st.f_frsize * st.f_bavail) / (1024**3), 1)
        used_gb = round(total_gb - free_gb, 1)
    except Exception:
        total_gb = free_gb = used_gb = 0

    # Capture files in home dir
    captures = []
    try:
        for f in glob.glob(os.path.join(RUNNING_HOME, '*.pcap')):
            fname = os.path.basename(f)
            sz = os.path.getsize(f)
            mtime = os.path.getmtime(f)
            # Extract date prefix (YYYY-MM-DD) from filename like 2025-01-15--14-30-45_name.pcap
            date_prefix = fname[:10] if len(fname) >= 10 and fname[4] == '-' else ''
            # Extract name suffix (after timestamp_)
            parts = fname.split('_', 1)
            name_group = parts[1].rsplit('.', 1)[0] if len(parts) > 1 else fname.rsplit('.', 1)[0]
            captures.append({
                'path': f, 'name': fname, 'size': sz,
                'size_mb': round(sz / (1024 * 1024), 2),
                'mtime': mtime, 'date': date_prefix, 'group': name_group,
            })
    except Exception:
        pass

    # Analyzer uploads
    uploads = []
    try:
        upload_dir = os.path.join(RUNNING_HOME, 'analyzer_uploads')
        if os.path.isdir(upload_dir):
            for f in glob.glob(os.path.join(upload_dir, '*.pcap*')):
                fname = os.path.basename(f)
                sz = os.path.getsize(f)
                mtime = os.path.getmtime(f)
                uploads.append({
                    'path': f, 'name': fname, 'size': sz,
                    'size_mb': round(sz / (1024 * 1024), 2),
                    'mtime': mtime,
                })
    except Exception:
        pass

    captures.sort(key=lambda x: x['mtime'], reverse=True)
    uploads.sort(key=lambda x: x['mtime'], reverse=True)

    # Compute totals
    cap_total = round(sum(c['size'] for c in captures) / (1024**2), 1)
    upl_total = round(sum(u['size'] for u in uploads) / (1024**2), 1)

    # Group captures by date
    date_groups = {}
    for c in captures:
        d = c['date'] or 'Unknown'
        date_groups.setdefault(d, {'files': [], 'size': 0})
        date_groups[d]['files'].append(c)
        date_groups[d]['size'] += c['size']
    for d in date_groups:
        date_groups[d]['size_mb'] = round(date_groups[d]['size'] / (1024**2), 1)

    # Group captures by name suffix
    name_groups = {}
    for c in captures:
        g = c['group'] or 'Other'
        name_groups.setdefault(g, {'files': [], 'size': 0})
        name_groups[g]['files'].append(c)
        name_groups[g]['size'] += c['size']
    for g in name_groups:
        name_groups[g]['size_mb'] = round(name_groups[g]['size'] / (1024**2), 1)

    return jsonify({
        'disk': {'total_gb': total_gb, 'used_gb': used_gb, 'free_gb': free_gb},
        'captures': captures, 'uploads': uploads,
        'cap_total_mb': cap_total, 'upl_total_mb': upl_total,
        'date_groups': {d: {'count': len(g['files']), 'size_mb': g['size_mb'],
                            'files': [f['name'] for f in g['files']]}
                        for d, g in date_groups.items()},
        'name_groups': {n: {'count': len(g['files']), 'size_mb': g['size_mb'],
                            'files': [f['name'] for f in g['files']]}
                        for n, g in name_groups.items()},
    })

@app.route('/files/delete', methods=['POST'])
def files_delete():
    data = request.get_json()
    files = data.get('files', [])
    if not files:
        return jsonify({'error': 'No files specified'}), 400

    deleted = []
    errors = []
    for fname in files:
        # Security: only allow deleting .pcap/.pcapng files from known directories
        found = False
        for base_dir in [RUNNING_HOME, os.path.join(RUNNING_HOME, 'analyzer_uploads')]:
            full_path = os.path.join(base_dir, os.path.basename(fname))
            if os.path.isfile(full_path) and (full_path.endswith('.pcap') or full_path.endswith('.pcapng')):
                try:
                    os.remove(full_path)
                    deleted.append(fname)
                    found = True
                except OSError as e:
                    errors.append(f'{fname}: {str(e)}')
                    found = True
                break
        if not found:
            errors.append(f'{fname}: not found or not allowed')

    return jsonify({'deleted': deleted, 'errors': errors, 'deleted_count': len(deleted)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
