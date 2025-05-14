import csv
import json
import re
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

ROUTERS_CSV = 'routers.csv'
OUTPUT_JSON = 'optics_data.json'

def parse_routers_csv(csv_file):
    routers = []
    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            routers.append({
                'hostname': row['hostname'],
                'ip': row['ip_address'],
                'username': row['username'],
                'password': row['password'],
                'device_type': row['device_type'],
            })
    return routers

def find_optics_ids(output):
    """
    Parses output of 'show running | include controller Optics'
    Returns a list of optics IDs, e.g. ['0/0/0/2']
    """
    ids = []
    regex = r'controller Optics([0-9/]+)'
    for line in output.splitlines():
        m = re.search(regex, line)
        if m:
            ids.append(m.group(1))
    return ids

def main():
    routers = parse_routers_csv(ROUTERS_CSV)
    all_device_data = {}

    for router in routers:
        hostname = router['hostname']
        ip = router['ip']
        print(f"\nConnecting to {hostname} ({ip})...")

        device = {
            'device_type': 'cisco_xr',  # Netmiko uses 'cisco_xr' for IOS-XR
            'host': ip,
            'username': router['username'],
            'password': router['password'],
            'global_delay_factor': 2,
            'fast_cli': False,
        }

        device_result = {}
        try:
            with ConnectHandler(**device) as conn:
                # Step 1.1: Find Optics IDs
                cmd1 = 'show running | include controller Optics'
                prompt = conn.find_prompt()
                output = conn.send_command(cmd1, expect_string=r"#")
                optics_ids = find_optics_ids(output)
                device_result['optics_ids'] = optics_ids
                device_result['optics_data'] = {}

                print(f"  Found optics IDs: {optics_ids}")
                
                # Step 1.2: For each optics ID, run both commands and save outputs
                for optics_id in optics_ids:
                    optics_block = {}

                    for subcmd in [
                        f"show controller optics {optics_id}",
                        f"show controller CoherentDSP {optics_id}"
                    ]:
                        prompt_before = conn.find_prompt()
                        command_output = conn.send_command(subcmd, expect_string=r"#", strip_prompt=False, strip_command=False)
                        # Save prompt, command, and full block!
                        optics_block[subcmd] = {
                            "prompt": prompt_before,
                            "command": subcmd,
                            "output_block": command_output
                        }
                        print(f"    Collected '{subcmd}'")

                    device_result['optics_data'][optics_id] = optics_block

        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            print(f"  ERROR connecting to {hostname} ({ip}): {e}")
            device_result['error'] = str(e)
        
        all_device_data[f"{hostname}_{ip}"] = device_result

    with open(OUTPUT_JSON, 'w') as outf:
        json.dump(all_device_data, outf, indent=2)
    print(f"\nData collection complete. Results written to {OUTPUT_JSON}")

if __name__ == '__main__':
    main()