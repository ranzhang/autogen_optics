import json

INPUT_FILE = 'optics_recommendations.json'
OUTPUT_FILE = 'final_report.md'

def anonymize_ip(ip):
    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.x.x"
    return ip

def main():
    with open(INPUT_FILE) as f:
        recs = json.load(f)

    md_lines = []
    md_lines.append("# Optics QA Health Report\n")
    md_lines.append("Below is a summary per device and optics, reporting Q margin and recommendations.\n")

    for device_key, optics in recs.items():
        # Extract/parse hostname and IP
        # device_key is e.g. 'RON8201-1_10.89.200.13'
        try:
            hostname, ip = device_key.rsplit('_',1)
        except ValueError:
            hostname = device_key
            ip = ""
        md_lines.append(f"## Device: `{hostname}` ({anonymize_ip(ip)})\n")
        if "error" in optics:
            md_lines.append(f"> **Error collecting data:** {optics['error']}\n")
            continue

        md_lines.append("| Optics ID | Q Margin | Recommendation |\n")
        md_lines.append("|-----------|----------|----------------|\n")
        for optics_id, summary in optics.items():
            q_margin = summary.get("q_margin")
            rec = summary.get("recommendation", "").replace('\n',' ')
            q_margin_disp = str(q_margin) if q_margin is not None else "Not found"
            md_lines.append(f"| `{optics_id}` | {q_margin_disp} | {rec} |")
        md_lines.append("")  # blank line after table

        # Highlight optics which need further investigation
        issues = [
            optics_id for optics_id, s in optics.items()
            if (
                (s['state'].lower() not in ['up','in service']) or
                (s['q_margin'] is not None and s['q_margin'] <= 1) or
                (s.get('alarms'))
            )
        ]
        if issues:
            md_lines.append(f"**Note:** The following optics should be investigated: {', '.join('`'+x+'`' for x in issues)}\n")

    with open(OUTPUT_FILE, 'w') as f:
        f.write('\n'.join(md_lines))

    print(f"Markdown report written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()