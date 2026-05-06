pragma circom 2.0.0;

/*
 * AgeCheck Circuit
 * Inputs:  birth_year (private), current_year (public), min_age (public)
 * Output:  is_old_enough (1 = true, 0 = false)
 * ZK property : Comparison verification of user age
 */

include "node_modules/circomlib/circuits/comparators.circom";

template AgeCheck() {
    // Private input — never revealed to verifier
    signal input birth_year;

    // Public inputs — known to both prover and verifier
    signal input current_year;
    signal input min_age;

    // Output signal
    signal output is_old_enough;

    // Compute threshold: current_year - min_age (e.g. 2025 - 18 = 2007)
    signal threshold;
    threshold <== current_year - min_age;

    // LessThan(n): checks if a < b using n-bit comparison
    // We check: birth_year <= threshold  i.e.  birth_year < threshold + 1
    component lt = LessThan(32);
    lt.in[0] <== birth_year;
    lt.in[1] <== threshold + 1;

    is_old_enough <== lt.out;
}

component main {public [current_year, min_age]} = AgeCheck();
