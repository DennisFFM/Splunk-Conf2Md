#!/usr/bin/env python
# export_test_simple.py - Einfache Version zum Testen

print("Script started!")

import sys
from pathlib import Path

# Erste Ausgabe
print(f"Running from: {Path(__file__).resolve()}")

try:
    # Import basics
    import re
    import subprocess
    import os
    from collections import defaultdict
    from jinja2 import Environment, FileSystemLoader
    
    print("✓ Basic imports successful")
    
    # Setup paths
    ROOT_DIR = Path(__file__).resolve().parent.parent
    print(f"ROOT_DIR: {ROOT_DIR}")
    
    # Load config
    config = {}
    config_path = ROOT_DIR / "config.txt"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
        print(f"✓ Config loaded: {len(config)} entries")
    else:
        print(f"✗ Config not found at {config_path}")
    
    # Get important paths
    EXPORT_BASE = ROOT_DIR / config.get("EXPORT_BASE", "export/savedsearches")
    TEMPLATE_DIR = ROOT_DIR / config.get("TEMPLATE_DIR", "templates")
    TEMPLATE_NAME = config.get("TEMPLATE_NAME", "example.md.j2")
    SPLUNK_BIN = config.get("SPLUNK_BIN", "/opt/splunk/bin/")
    
    print(f"\nConfiguration:")
    print(f"  EXPORT_BASE: {EXPORT_BASE}")
    print(f"  TEMPLATE_DIR: {TEMPLATE_DIR}")
    print(f"  TEMPLATE_NAME: {TEMPLATE_NAME}")
    print(f"  SPLUNK_BIN: {SPLUNK_BIN}")
    
    # Check if paths exist
    print(f"\nPath checks:")
    print(f"  Template dir exists: {TEMPLATE_DIR.exists()}")
    print(f"  Template file exists: {(TEMPLATE_DIR / TEMPLATE_NAME).exists()}")
    print(f"  Splunk binary exists: {Path(SPLUNK_BIN, 'splunk').exists()}")
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    print(f"\nArguments:")
    print(f"  Dry run: {args.dry_run}")
    
    # If everything looks good, try to run btool
    if Path(SPLUNK_BIN, 'splunk').exists():
        print("\n✓ Would run btool command now...")
        if args.dry_run:
            print("[DRY RUN] Would export saved searches")
        else:
            print("Would export saved searches for real")
    else:
        print("\n✗ Cannot find Splunk binary!")
        
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\nScript finished!")