pragma circom 2.0.0;

/*
 * KYCCheck Circuit
 * Proves: the user holds a valid KYC credential 
 * Private: credential_id, nonce
 * Public:  expected_hash (stored commitment from Identity Provider)
 * Output:  is_verified (1 = valid KYC, 0 = invalid)
 */

include "node_modules/circomlib/circuits/poseidon.circom";
include "node_modules/circomlib/circuits/comparators.circom";

template KYCCheck() {
    // Private inputs
    signal input credential_id;   // Numeric ID of the credential
    signal input nonce;           // Secret randomness used at issuance

    // Public input — the commitment registered by the Identity Provider
    signal input expected_hash;

    // Output
    signal output is_verified;

    // Recompute Poseidon(credential_id, nonce)
    component hasher = Poseidon(2);
    hasher.inputs[0] <== credential_id;
    hasher.inputs[1] <== nonce;

    // Check if computed hash matches the expected commitment
    component eq = IsEqual();
    eq.in[0] <== hasher.out;
    eq.in[1] <== expected_hash;

    is_verified <== eq.out;
}

component main {public [expected_hash]} = KYCCheck();
