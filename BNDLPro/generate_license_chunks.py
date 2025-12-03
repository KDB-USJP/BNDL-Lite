"""
URL Obfuscation Generator for BNDL-Pro License System

This script generates the obfuscated chunks to embed in license.py
Run this script to get the chunks, then copy them into license.py
"""

import base64
import hashlib

# Your Apps Script URL
URL = "https://script.google.com/macros/s/AKfycbxp7wL5iwo7K3Y4O_lzSo43KSHJ24xAoCtLR57Tufi1ZGqxTlkykg1tmNB6r9B7ZLij7w/exec"

def derive_key():
    """Generate obfuscation key from addon metadata."""
    # This matches what will be in the addon
    addon_name = "BNDL-Pro"
    addon_version = (1, 0, 0)  # Update if your version is different
    
    seed = f"{addon_name}{addon_version}"
    return hashlib.sha256(seed.encode()).digest()[:16]

def obfuscate_url(url):
    """Obfuscate URL for storage."""
    key = derive_key()
    
    # Split into 3 chunks
    chunk_size = len(url) // 3
    chunks = [
        url[:chunk_size],
        url[chunk_size:chunk_size*2],
        url[chunk_size*2:]
    ]
    
    # XOR + base64 each chunk
    encoded = []
    for i, chunk in enumerate(chunks):
        xor_key = key[i % len(key)]
        xored = bytes([ord(c) ^ xor_key for c in chunk])
        encoded.append(base64.b64encode(xored).decode())
    
    return encoded

def deobfuscate_url(chunks):
    """Reconstruct URL from obfuscated chunks (for testing)."""
    key = derive_key()
    decoded = []
    for i, chunk in enumerate(chunks):
        xor_key = key[i % len(key)]
        b64_decoded = base64.b64decode(chunk.encode())
        original = ''.join([chr(b ^ xor_key) for b in b64_decoded])
        decoded.append(original)
    
    return ''.join(decoded)

if __name__ == "__main__":
    print("=" * 60)
    print("BNDL-Pro License URL Obfuscation Generator")
    print("=" * 60)
    print()
    print("Original URL:")
    print(URL)
    print()
    
    # Generate obfuscated chunks
    chunks = obfuscate_url(URL)
    
    print("Obfuscated chunks (copy these into license.py):")
    print()
    print(f"_APPS_SCRIPT_CHUNK_A = \"{chunks[0]}\"")
    print(f"_APPS_SCRIPT_CHUNK_B = \"{chunks[1]}\"")
    print(f"_APPS_SCRIPT_CHUNK_C = \"{chunks[2]}\"")
    print()
    
    # Test deobfuscation
    reconstructed = deobfuscate_url(chunks)
    print("Verification (should match original):")
    print(reconstructed)
    print()
    
    if reconstructed == URL:
        print("✅ SUCCESS: Obfuscation/deobfuscation working correctly!")
    else:
        print("❌ ERROR: Mismatch detected!")
        print(f"Expected: {URL}")
        print(f"Got: {reconstructed}")
