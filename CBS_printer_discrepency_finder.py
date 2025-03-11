import csv

file1 = 'POCANTICO HILLS CSD Master Printer List - Copy(Meter Comparison).csv'

file2 = 'Pocantico x CBS Printers Info - Copy(Sheet1).csv'  # Replace with your second CSV file name/path


def find_duplicate_ips_in_csv(filename):
    """
    Returns a dict { ip: [row_numbers] } for any IPs that appear
    more than once in the same CSV.
    """
    ip_to_rows = {}
    with open(filename, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row_number, row in enumerate(reader, start=2):  # Start=2 to account for the header
            ip = row['IP Address'].strip()
            if not ip:
                continue
            
            ip_to_rows.setdefault(ip, []).append(row_number)
    
    # Filter to only keep IPs with more than one occurrence
    duplicates_dict = {ip: rows for ip, rows in ip_to_rows.items() if len(rows) > 1}
    return duplicates_dict

def load_csv_as_dict(filename):
    """
    Reads the CSV, returns two structures:
      1) ip_dict: { ip: {'rows': [row_numbers], 'id_tag': str, 'serial_number': str} }
         (If multiple rows share an IP, only the *last* row's ID/Serial get stored here,
         since we only need one for cross-file comparison. For full row coverage, see 'rows'.)

      2) ip_set: A set of all IPs encountered.

    All ID Tags and Serial Numbers are converted to UPPERCASE.
    """
    ip_dict = {}
    ip_set = set()

    with open(filename, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row_number, row in enumerate(reader, start=2):
            ip = row['IP Address'].strip()
            if not ip:
                continue

            # Convert ID Tag & Serial to uppercase
            id_tag_upper = row['ID Tag'].strip().upper()
            serial_upper = row['Serial Number'].strip().upper()

            if ip not in ip_dict:
                # Store the first time we see this IP
                ip_dict[ip] = {
                    'rows': [row_number],
                    'id_tag': id_tag_upper,
                    'serial_number': serial_upper
                }
            else:
                # If we see the IP again, append row number
                ip_dict[ip]['rows'].append(row_number)
                # We'll overwrite ID/Serial with the last row's values
                ip_dict[ip]['id_tag'] = id_tag_upper
                ip_dict[ip]['serial_number'] = serial_upper

            ip_set.add(ip)

    return ip_dict, ip_set

def compare_csvs(file1, file2):
    """
    Performs cross-file comparisons, returning:
      - duplicates_across: exact matches by IP (same ID & Serial)
      - mismatches: same IP but different ID/Serial
      - cbs_only_ips: IPs in CBS Master that are not in Poco
      - poco_only_ips: IPs in Poco that are not in CBS Master
    """
    # Load CSVs into structures
    cbs_dict, cbs_set = load_csv_as_dict(file1)
    poco_dict, poco_set = load_csv_as_dict(file2)
    
    # 1) Identify IPs that appear in CBS only or Poco only
    cbs_only_ips = cbs_set - poco_set
    poco_only_ips = poco_set - cbs_set
    
    # 2) Compare IPs that appear in BOTH
    common_ips = cbs_set.intersection(poco_set)

    duplicates_across = []
    mismatches = []
    
    for ip in common_ips:
        # We'll compare the *last known* ID/Serial from each dict.
        cbs_info = cbs_dict[ip]
        poco_info = poco_dict[ip]

        # If ID Tag and Serial both match (already uppercased), it's a duplicate across
        if (cbs_info['id_tag'] == poco_info['id_tag'] and
            cbs_info['serial_number'] == poco_info['serial_number']):
            # We consider the last row in each file for the row numbers shown
            duplicates_across.append({
                'ip_address': ip,
                'cbs_master_rows': cbs_info['rows'],
                'poco_sheet_rows': poco_info['rows'],
                'id_tag': cbs_info['id_tag'],
                'serial_number': cbs_info['serial_number']
            })
        else:
            # Mismatch
            mismatches.append({
                'ip_address': ip,
                'cbs_master_rows': cbs_info['rows'],
                'poco_sheet_rows': poco_info['rows'],
                'file1_id_tag': cbs_info['id_tag'],
                'file1_serial': cbs_info['serial_number'],
                'file2_id_tag': poco_info['id_tag'],
                'file2_serial': poco_info['serial_number']
            })

    return duplicates_across, mismatches, cbs_only_ips, poco_only_ips

if __name__ == "__main__":
    # 1) Find duplicates within each sheet
    cbs_duplicates_dict = find_duplicate_ips_in_csv(file1)
    poco_duplicates_dict = find_duplicate_ips_in_csv(file2)
    
    # 2) Compare across the two sheets
    duplicates_across, mismatches, cbs_only_ips, poco_only_ips = compare_csvs(file1, file2)

    # === 1) DUPLICATES WITHIN CBS MASTER ===
    print("=== DUPLICATE IPs *WITHIN* CBS MASTER ===")
    if cbs_duplicates_dict:
        for ip, rows in cbs_duplicates_dict.items():
            rows_str = ", ".join(map(str, rows))
            print(f"IP: {ip:<15}  Rows: {rows_str}")
    else:
        print("No duplicate IPs found within CBS Master.")
    
    # === 2) DUPLICATES WITHIN POCO SHEET ===
    print("\n=== DUPLICATE IPs *WITHIN* POCO SHEET ===")
    if poco_duplicates_dict:
        for ip, rows in poco_duplicates_dict.items():
            rows_str = ", ".join(map(str, rows))
            print(f"IP: {ip:<15}  Rows: {rows_str}")
    else:
        print("No duplicate IPs found within Poco sheet.")
    
    # === 3) IPs FOUND ONLY IN ONE FILE (NOT IN THE OTHER) ===
    print("\n=== IPs IN CBS MASTER BUT *NOT* IN POCO SHEET ===")
    if cbs_only_ips:
        for ip in sorted(cbs_only_ips):
            print(f"IP: {ip}")
    else:
        print("No IPs are exclusive to CBS Master.")
    
    print("\n=== IPs IN POCO SHEET BUT *NOT* IN CBS MASTER ===")
    if poco_only_ips:
        for ip in sorted(poco_only_ips):
            print(f"IP: {ip}")
    else:
        print("No IPs are exclusive to Poco sheet.")
    
    # === 4) CROSS-FILE EXACT MATCHES ===
    print("\n=== CROSS-FILE EXACT MATCHES (SAME IP, SAME ID, SAME SERIAL) ===")
    if duplicates_across:
        for d in duplicates_across:
            # For multi-row IPs, we show the list of rows
            cbs_rows_str = ", ".join(map(str, d['cbs_master_rows']))
            poco_rows_str = ", ".join(map(str, d['poco_sheet_rows']))

            print(
                f"IP: {d['ip_address']:<15}"
                f"  CBS Rows: {cbs_rows_str:<6}"
                f"  Poco Rows: {poco_rows_str:<6}"
                f"  ID Tag: {d['id_tag']:<10}"
                f"  Serial: {d['serial_number']}"
            )
    else:
        print("No exact matches across files.")
    
    # === 5) CROSS-FILE POTENTIAL CONFLICTS ===
    print("\n=== CROSS-FILE POTENTIAL CONFLICTS (SAME IP, DIFFERENT ID OR SERIAL) ===")
    if mismatches:
        for m in mismatches:
            cbs_rows_str = ", ".join(map(str, m['cbs_master_rows']))
            poco_rows_str = ", ".join(map(str, m['poco_sheet_rows']))
            print(
                f"IP: {m['ip_address']:<15}"
                f"  CBS Rows: {cbs_rows_str:<6}"
                f"  ID Tag: {m['file1_id_tag']:<10}"
                f"  Serial: {m['file1_serial']:<12}"
                f"  Poco Rows: {poco_rows_str:<6}"
                f"  ID Tag: {m['file2_id_tag']:<10}"
                f"  Serial: {m['file2_serial']}"
            )
    else:
        print("No mismatches across files.")