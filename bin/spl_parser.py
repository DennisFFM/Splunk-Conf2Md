import re

def extract_splunk_fields(spl: str) -> list[str]:
    """Extract field names from a Splunk SPL string with filters for aliases, macros, and special commands."""

    fields = set()

    # Remove backtick macros entirely (e.g. `macro_name(...)`)
    spl = re.sub(r'`[^`]*`', '', spl)

    # Remove known function calls that aren't field-related
    spl = re.sub(r'\b(drop_dm_object_name|security_content_ctime|lookup|eval|tostring)\s*\(.*?\)', '', spl, flags=re.IGNORECASE)

    # Remove escape sequences (e.g. Windows paths)
    spl = spl.replace("\\", "")

    # Remove string literals (e.g. "*.exe")
    spl = re.sub(r'"[^"]*"', '', spl)

    # Match field=value or field IN (...) or field!=... or field>=...
    fields.update(re.findall(r'\b([a-zA-Z0-9_.]+)\s*(?:=|!=|>=|<=|IN|>|<)', spl))

    # Match "by" clauses (e.g. stats by field1, field2)
    by_clauses = re.findall(r'\bby\s+([^\|\n]+)', spl, flags=re.IGNORECASE)
    for clause in by_clauses:
        fields.update([f.strip() for f in clause.split(",")])

    # Match "rex field=fieldname" (but only the value of field=, not "field" as a key)
    fields.update(re.findall(r'\brex\s+field=([a-zA-Z0-9_.]+)', spl))

    # Match simple function calls with field arguments (e.g. min(_time), max(score))
    fields.update(re.findall(r'\b(?:min|max|count|avg|sum|dc|stdev)\s*\(\s*([a-zA-Z0-9_.]+)\s*\)', spl, flags=re.IGNORECASE))

    # Clean up: remove empty strings, 'as' aliases, known keywords
    filtered_fields = {
        f.strip()
        for f in fields
        if f and f.lower() not in {"field", "datamodel", "from"} and not f.lower().startswith("all_traffic")
    }

    return sorted(filtered_fields)


# === Example usage ===
if __name__ == "__main__":
    spl = r'''
| tstats `security_content_summariesonly` count min(_time) as firstTime max(_time) as lastTime from datamodel=Network_Traffic.All_Traffic 
  where (All_Traffic.app IN ("*Regsvcs.exe", "*\\Ftp.exe", "*OfflineScannerShell.exe")) 
  by All_Traffic.action, All_Traffic.app, All_Traffic.dest, All_Traffic.dest_ip, All_Traffic.dest_port, All_Traffic.direction, 
     All_Traffic.dvc, All_Traffic.protocol, All_Traffic.protocol_version, All_Traffic.src, All_Traffic.src_ip, 
     All_Traffic.src_port, All_Traffic.transport, All_Traffic.user, All_Traffic.vendor_product 
| `drop_dm_object_name(All_Traffic)` 
| `security_content_ctime(firstTime)` 
| `security_content_ctime(lastTime)` 
| rex field=app ".*\\\(?<process_name>.*)$" 
| `lolbas_with_network_traffic_filter`
    '''

    fields = extract_splunk_fields(spl)
    print("Extracted fields:", fields)
