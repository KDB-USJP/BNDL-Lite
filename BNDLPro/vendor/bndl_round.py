#!/usr/bin/env python3
"""BNDL number rounder - post-processes BNDL files to round float literals.
Does not modify the semantic meaning of the file, only rounds floats to the specified precision.

Configuration:
    SIGNIFICANT_DIGITS: Number of decimal places to keep (default: 3)
                       Can be 0 for integers, or any positive number for decimal precision.
                       Examples with different settings:
                       - 0: 1.23456 → 1
                       - 1: 1.23456 → 1.2
                       - 2: 1.23456 → 1.23
                       - 3: 1.23456 → 1.235 (default)
                       - 4: 1.23456 → 1.2346
"""

import re

# User configuration - adjust this value to control rounding precision
SIGNIFICANT_DIGITS = 3  # Default: 3 decimal places

def _format_num(x, ndigits=None):
    """Format a float string to at most ndigits decimal places.
    If ndigits is None, uses SIGNIFICANT_DIGITS from configuration.
    """
    try:
        f = float(x)
        # Use configured precision or passed-in value
        digits = SIGNIFICANT_DIGITS if ndigits is None else ndigits
        if not isinstance(digits, int) or digits < 0:
            print(f"[BNDL] Warning: Invalid precision {digits}, using 3")
            digits = 3
        # Use fixed-point with digits, then strip trailing zeros
        fmt = f"{f:.{digits}f}"
        txt = fmt.rstrip("0").rstrip(".")
        if txt == "-0":
            txt = "0"
        return txt
    except ValueError:
        return x

def round_floats_in_bndl(text, precision=None):
    """Round float literals in a BNDL file to 3 decimal places.
    Only affects numbers inside angle brackets < ... > and preserves non-numeric tokens.
    """
    def repl(m):
        # Get the content between angle brackets
        inner = m.group(1).strip()
        
        # Try to split on commas (for vectors)
        parts = [p.strip() for p in inner.split(',')]
        
        # Format each part that looks like a number
        rounded = []
        for p in parts:
            if re.match(r'^-?\d+\.?\d*$', p):
                rounded.append(_format_num(p))
            else:
                rounded.append(p)
        
        # Reassemble with original spacing
        return f"<{', '.join(rounded)}>"
    
    # Find angle-bracket enclosed values and process their contents
    # Negative lookahead (?!>) ensures we don't match the end of another bracket
    pattern = r'<((?:(?!>).)*?)>'
    return re.sub(pattern, repl, text)

def round_bndl_file(filepath):
    """Read a .bndl file, round its float literals, and write it back."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    rounded = round_floats_in_bndl(text)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(rounded)

def test_format():
    """Test the float rounding with some common cases and different precisions."""
    # Test default precision (3)
    print("\nTesting default precision (3):")
    tests = [
        # Single numbers
        ("<0.09999999403953552>", "<0.1>"),
        ("<0.8499999642372131>", "<0.85>"),
        ("<1.0>", "<1>"),
        ("<-0.0>", "<0>"),
        # Vectors
        ("<0.2, 0.8, 0.6>", "<0.2, 0.8, 0.6>"),
        ("<1.0, 2.0, 3.0>", "<1, 2, 3>"),
        # Mixed content
        ("§ Z § to <0.09999998>", "§ Z § to <0.1>"),
        ("Connect [ Node #1 ] ○ out to <0.5, 1, 0>", "Connect [ Node #1 ] ○ out to <0.5, 1, 0>"),
        # Non-numeric content (should be preserved)
        ("<True>", "<True>"),
        ("<False>", "<False>"),
        ("©some text©", "©some text©"),
    ]
    
    ok = True
    for inp, exp in tests:
        got = round_floats_in_bndl(inp)
        if got != exp:
            print(f"FAIL: {inp!r} → got {got!r}, want {exp!r}")
            ok = False
        else:
            print(f"OK  : {inp!r} → {got!r}")
    print(f"Default precision tests {'passed' if ok else 'failed'}!")
    
    # Test different precisions
    print("\nTesting various precisions:")
    number = 1.23456789
    precisions = [0, 1, 2, 4, 6]
    for p in precisions:
        global SIGNIFICANT_DIGITS
        SIGNIFICANT_DIGITS = p
        rounded = round_floats_in_bndl(f"<{number}>")
        print(f"Precision {p}: {number} → {rounded}")
    
    return ok

if __name__ == "__main__":
    # If run directly, run tests
    print("BNDL float rounder test suite")
    print("-----------------------------")
    print(f"Default precision setting: {SIGNIFICANT_DIGITS}")
    test_format()