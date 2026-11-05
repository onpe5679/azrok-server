# -*- coding: utf-8 -*-
"""
Search Windows Registry for Hansol/Azrok related keys.
The game likely stores server address and port in the registry.
"""
import winreg
import sys

def search_key_recursive(root, root_name, path, keywords, depth=0, max_depth=6):
    """Recursively search registry for keys/values containing keywords."""
    results = []
    if depth > max_depth:
        return results

    full_path = f"{root_name}\\{path}" if path else root_name

    try:
        key = winreg.OpenKey(root, path) if path else winreg.OpenKey(root, "")
    except (PermissionError, OSError):
        return results

    # Check values
    try:
        i = 0
        while True:
            try:
                name, value, vtype = winreg.EnumValue(key, i)
                name_lower = name.lower() if name else ""
                value_str = str(value).lower() if value else ""
                path_lower = path.lower() if path else ""

                for kw in keywords:
                    if kw in name_lower or kw in value_str or kw in path_lower:
                        results.append({
                            'path': full_path,
                            'name': name,
                            'value': value,
                            'type': vtype
                        })
                        break
                i += 1
            except OSError:
                break
    except Exception:
        pass

    # Check subkeys
    try:
        i = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey_lower = subkey_name.lower()
                subpath = f"{path}\\{subkey_name}" if path else subkey_name

                # If subkey name matches, enumerate ALL its values
                for kw in keywords:
                    if kw in subkey_lower:
                        try:
                            sk = winreg.OpenKey(root, subpath)
                            j = 0
                            while True:
                                try:
                                    name, value, vtype = winreg.EnumValue(sk, j)
                                    results.append({
                                        'path': f"{root_name}\\{subpath}",
                                        'name': name,
                                        'value': value,
                                        'type': vtype
                                    })
                                    j += 1
                                except OSError:
                                    break
                            winreg.CloseKey(sk)
                        except (PermissionError, OSError):
                            pass
                        break

                # Recurse into subkeys
                results.extend(search_key_recursive(root, root_name, subpath, keywords, depth+1, max_depth))
                i += 1
            except OSError:
                break
    except Exception:
        pass

    winreg.CloseKey(key)
    return results


def main():
    print("=" * 60)
    print("  Azrok Plaza - Registry Search")
    print("=" * 60)
    print()

    keywords = ['hansol', 'azrok', 'azrok_plaza']

    search_locations = [
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\WOW6432Node"),
        (winreg.HKEY_CURRENT_USER, "HKCU", "SOFTWARE"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
    ]

    all_results = []

    for root, root_name, path in search_locations:
        print(f"Searching {root_name}\\{path}...")
        results = search_key_recursive(root, root_name, path, keywords, max_depth=5)
        all_results.extend(results)

    # Also directly check some likely paths
    direct_paths = [
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\Hansol"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\WOW6432Node\\Hansol"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\Hansol Education"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\WOW6432Node\\Hansol Education"),
        (winreg.HKEY_CURRENT_USER, "HKCU", "SOFTWARE\\Hansol"),
        (winreg.HKEY_CURRENT_USER, "HKCU", "SOFTWARE\\Hansol Education"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\Azrok"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\WOW6432Node\\Azrok"),
    ]

    print()
    print("Checking direct paths...")
    for root, root_name, path in direct_paths:
        try:
            key = winreg.OpenKey(root, path)
            print(f"  [FOUND] {root_name}\\{path}")
            # Enumerate all values
            i = 0
            while True:
                try:
                    name, value, vtype = winreg.EnumValue(key, i)
                    all_results.append({
                        'path': f"{root_name}\\{path}",
                        'name': name,
                        'value': value,
                        'type': vtype
                    })
                    i += 1
                except OSError:
                    break
            # Enumerate subkeys
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(key, i)
                    print(f"    Subkey: {subkey}")
                    try:
                        sk = winreg.OpenKey(root, f"{path}\\{subkey}")
                        j = 0
                        while True:
                            try:
                                name, value, vtype = winreg.EnumValue(sk, j)
                                all_results.append({
                                    'path': f"{root_name}\\{path}\\{subkey}",
                                    'name': name,
                                    'value': value,
                                    'type': vtype
                                })
                                j += 1
                            except OSError:
                                break
                        winreg.CloseKey(sk)
                    except (PermissionError, OSError):
                        pass
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except (FileNotFoundError, PermissionError, OSError):
            pass

    # Print results
    print()
    print("=" * 60)
    print(f"  Found {len(all_results)} registry entries")
    print("=" * 60)

    seen = set()
    for r in all_results:
        key = (r['path'], r['name'])
        if key in seen:
            continue
        seen.add(key)

        type_names = {1: 'REG_SZ', 2: 'REG_EXPAND_SZ', 3: 'REG_BINARY',
                      4: 'REG_DWORD', 7: 'REG_MULTI_SZ', 11: 'REG_QWORD'}
        tname = type_names.get(r['type'], f"type={r['type']}")

        value_display = r['value']
        if isinstance(value_display, bytes):
            value_display = value_display.hex(' ')
        elif isinstance(value_display, int):
            value_display = f"{value_display} (0x{value_display:X})"

        print(f"\n  Path:  {r['path']}")
        print(f"  Name:  {r['name']}")
        print(f"  Value: {value_display}")
        print(f"  Type:  {tname}")

    if not all_results:
        print("\n  No Hansol/Azrok registry entries found!")
        print("  The game may not have been properly installed,")
        print("  or the installer didn't create registry keys.")
        print()
        print("  Alternative: We can patch the game to use a fixed")
        print("  server address (127.0.0.1) and port (e.g., 9000).")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
