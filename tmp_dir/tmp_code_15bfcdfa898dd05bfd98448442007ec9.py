import json
import re

INPUT_FILE = 'optics_data.json'
OUTPUT_FILE = 'optics_recommendations.json'

def extract_state(output_block):
    """
    Look for Controller State or Derived State in the output block.
    """
    for line in output_block.splitlines():
        if re.match(r'\s*(Controller State|Derived State)\s*[:=]', line, re.I):
            # Example: Derived State : In Service
            return line.split(':',1)[1].strip()
    return None

def extract_alarms(output_block):
    """
    Find and extract alarm lines or report None.
    """
    alarms = []
    for line in output_block.splitlines():
        if re.search(r'alarm', line, re.I) or re.search(r'Alarm', line, re.I):
            if ':' in line:
                val = line.split(':',1)[1].strip()
                if val and val.lower() not in ['none','no alarm']:
                    alarms.append(val)
    return alarms if alarms else None

def extract_qmargin(output_block):
    """
    Try to extract Q Margin value from the block (commonly 'Q Margin', 'Qmargin', etc.)
    """
    for line in output_block.splitlines():
        m = re.search(r'Q[\s-]?Margin\s*[:= ]\s*([-.\d]+)', line, re.I)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                continue
    return None

def analyze_optics_data():
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)

    recommendations = {}  # device -> optics -> dict

    for dev_key, dev_data in data.items():
        dev_summary = {}
        if 'error' in dev_data:
            dev_summary['error'] = dev_data['error']
        else:
            optics_data = dev_data.get('optics_data', {})
            for optics_id, block in optics_data.items():
                # We use the two command blocks: 'show controller optics <id>' (basic), and 'show controller CoherentDSP <id>' (DSP/advanced)
                optics_output = block.get(f'show controller optics {optics_id}', {})
                dsp_output = block.get(f'show controller CoherentDSP {optics_id}', {})

                optics_block = optics_output.get('output_block','')
                dsp_block = dsp_output.get('output_block','')

                # Extract state info (Controller or Derived) -- found in optics_block
                state = extract_state(optics_block) or extract_state(dsp_block)
                # Extract alarms: look for "Alarm:" section or similar anywhere
                alarms = extract_alarms(optics_block) or extract_alarms(dsp_block)
                # Q Margin: usually in Coherent DSP output
                q_margin = extract_qmargin(dsp_block)

                # Begin building summary
                summary = {
                    'state': state or 'UNKNOWN',
                    'alarms': alarms or [],
                    'q_margin': q_margin,
                    'recommendation': '',
                }

                # Best practice evaluation
                rec_msgs = []
                if state and state.lower() in ['up', 'in service']:
                    rec_msgs.append('State: OK')
                else:
                    rec_msgs.append('State: Investigate - not Up/In Service')

                if alarms:
                    rec_msgs.append(f'Alarms detected: {", ".join(alarms)} (Investigate)')
                else:
                    rec_msgs.append('Alarms: None')

                if q_margin is not None:
                    if q_margin > 1:
                        rec_msgs.append(f'Q Margin: {q_margin} (Good)')
                    else:
                        rec_msgs.append(f'Q Margin: {q_margin} (Low - Investigate)')
                else:
                    rec_msgs.append('Q Margin: Not found')

                summary['recommendation'] = '; '.join(rec_msgs)
                dev_summary[optics_id] = summary
        recommendations[dev_key] = dev_summary

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(recommendations, f, indent=2)
    print(f"\nAnalysis complete. Recommendations written to {OUTPUT_FILE}")

if __name__ == '__main__':
    analyze_optics_data()