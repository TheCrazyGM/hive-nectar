#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug elliptic curve implementation"""

import os
import sys

# Add src to path so we can import nectargraphenebase
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nectargraphenebase.account import (
    SECP256K1_B,
    SECP256K1_GX,
    SECP256K1_GY,
    SECP256K1_P,
    _is_on_curve,
)


def debug_curve():
    """
    Run a set of diagnostic checks and print human-readable outputs to verify the SECP256K1 curve constants and curve equation.
    
    Performs:
    - Prints imported SECP256K1 constants (P, B, Gx, Gy) in decimal and hex.
    - Verifies the curve equation y^2 ≡ x^3 + b (mod p) using the imported generator coordinates and via the helper _is_on_curve.
    - Compares the imported constants against canonical secp256k1 generator literals and re-evaluates the curve equation using the literal values.
    - If a mismatch is found, prints the modular difference and performs a small-number arithmetic sanity check.
    
    This function is purely diagnostic and has no return value; it writes results to stdout.
    """
    print("=== Elliptic Curve Debug ===")

    # Print the raw integer values
    print(f"P (prime): {SECP256K1_P}")
    print(f"B (curve parameter): {SECP256K1_B}")
    print(f"Gx: {SECP256K1_GX}")
    print(f"Gy: {SECP256K1_GY}")

    # Print hex representations
    print(f"\nP hex: 0x{SECP256K1_P:064x}")
    print(f"Gx hex: 0x{SECP256K1_GX:064x}")
    print(f"Gy hex: 0x{SECP256K1_GY:064x}")

    # Test the curve equation manually
    x, y = SECP256K1_GX, SECP256K1_GY
    left_side = (y * y) % SECP256K1_P
    right_side = (x * x * x + SECP256K1_B) % SECP256K1_P

    print("\nManual curve equation check:")
    print(f"y² mod p = 0x{left_side:064x}")
    print(f"x³ + b mod p = 0x{right_side:064x}")
    print(f"Are they equal? {left_side == right_side}")
    print(f"Difference: 0x{abs(left_side - right_side):064x}")

    # Test _is_on_curve function
    is_on_curve = _is_on_curve(x, y)
    print(f"_is_on_curve result: {is_on_curve}")

    # Let's manually verify the secp256k1 generator point
    print("\nManual verification of secp256k1 generator point:")

    # Standard secp256k1 generator point
    gx_str = "79BE667EF9DCBBAC55A06295CE870B07029BFCDB2D4"
    gy_str = "483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8"
    p_str = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F"

    gx_int = int(gx_str, 16)
    gy_int = int(gy_str, 16)
    p_int = int(p_str, 16)

    print(f"Manual Gx: 0x{gx_int:064x}")
    print(f"Manual Gy: 0x{gy_int:064x}")
    print(f"Manual P: 0x{p_int:064x}")

    # Check if they match our constants
    print(f"Gx matches: {gx_int == SECP256K1_GX}")
    print(f"Gy matches: {gy_int == SECP256K1_GY}")
    print(f"P matches: {p_int == SECP256K1_P}")

    # Manual curve equation check
    y_squared = (gy_int * gy_int) % p_int
    x_cubed_plus_7 = (gx_int * gx_int * gx_int + 7) % p_int

    print("\nManual curve check:")
    print(f"y² mod p = 0x{y_squared:064x}")
    print(f"x³ + 7 mod p = 0x{x_cubed_plus_7:064x}")
    print(f"Equal? {y_squared == x_cubed_plus_7}")

    # Let's also try with our constants
    print("\nUsing our constants:")
    y2_ours = (SECP256K1_GY * SECP256K1_GY) % SECP256K1_P
    x3_7_ours = (SECP256K1_GX * SECP256K1_GX * SECP256K1_GX + 7) % SECP256K1_P
    print(f"Our y² mod p = 0x{y2_ours:064x}")
    print(f"Our x³ + 7 mod p = 0x{x3_7_ours:064x}")
    print(f"Our equal? {y2_ours == x3_7_ours}")

    # Check if there's a difference
    if y2_ours != x3_7_ours:
        diff = (y2_ours - x3_7_ours) % SECP256K1_P
        print(f"Difference: 0x{diff:064x}")

        # Maybe the issue is with large integer arithmetic?
        print("\nChecking arithmetic with smaller numbers:")
        # Test with small known values
        small_x, small_y, small_p = 1, 1, 13
        small_y2 = (small_y * small_y) % small_p
        small_x3_7 = (small_x * small_x * small_x + 7) % small_p
        print(f"Small test: y²={small_y2}, x³+7={small_x3_7}, equal={small_y2 == small_x3_7}")


if __name__ == "__main__":
    debug_curve()
