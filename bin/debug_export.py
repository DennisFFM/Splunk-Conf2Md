#!/usr/bin/env python
# debug_export.py - Speichere dies als bin/debug_export.py

import sys
import os
from pathlib import Path

print("=== DEBUG START ===")
print(f"Python Version: {sys.version}")
print(f"Current Directory: {os.getcwd()}")
print(f"Script Location: {__file__}")

# Test 1: Kann config.txt geladen werden?
try:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    config_path = ROOT_DIR / "config.txt"
    print(f"\nLooking for config at: {config_path}")
    print(f"Config exists: {config_path.exists()}")
    
    if config_path.exists():
        with open(config_path) as f:
            lines = f.readlines()[:5]
            print(f"First 5 lines of config: {lines}")
except Exception as e:
    print(f"ERROR loading config: {e}")

# Test 2: Logger import
print("\n--- Testing Logger Import ---")
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from logger import get_logger
    print("✓ Logger import successful")
    logger = get_logger("test")
    logger.info("This is a test message")
except ImportError as e:
    print(f"✗ Logger import failed: {e}")
except Exception as e:
    print(f"✗ Logger error: {e}")

# Test 3: Export script import
print("\n--- Testing Export Script ---")
try:
    # Versuche das export script zu importieren
    import export_savedsearches_btool_v2
    print("✓ Export script import successful")
    
    # Hole die config
    config = export_savedsearches_btool_v2.config
    print(f"SPLUNK_BIN from config: {config.get('SPLUNK_BIN', 'NOT SET')}")
    print(f"EXPORT_BASE from config: {config.get('EXPORT_BASE', 'NOT SET')}")
    
    # Teste ob Splunk binary existiert
    splunk_exe = Path(config.get('SPLUNK_BIN', '/opt/splunk/bin/')) / "splunk"
    print(f"\nSplunk binary path: {splunk_exe}")
    print(f"Splunk binary exists: {splunk_exe.exists()}")
    
except Exception as e:
    print(f"✗ Export script error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Direkt die export Funktion aufrufen
print("\n--- Direct Function Call Test ---")
try:
    # Minimaler Test ohne btool
    from export_savedsearches_btool_v2 import sanitize_filename, extract_context_keys
    
    # Test sanitize_filename
    test_name = "Test Search @ 123"
    sanitized = sanitize_filename(test_name)
    print(f"Sanitize test: '{test_name}' -> '{sanitized}'")
    
    # Test template
    template_dir = ROOT_DIR / config.get("TEMPLATE_DIR", "templates")
    template_name = config.get("TEMPLATE_NAME", "example.md.j2")
    print(f"\nTemplate dir: {template_dir}")
    print(f"Template dir exists: {template_dir.exists()}")
    print(f"Template file: {template_dir / template_name}")
    print(f"Template exists: {(template_dir / template_name).exists()}")
    
    if (template_dir / template_name).exists():
        keys = extract_context_keys(template_dir, template_name)
        print(f"Template keys: {keys}")
    
except Exception as e:
    print(f"✗ Function test error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== DEBUG END ===")