pragma circom 2.0.0;

/*
 * BalanceCheck Circuit
 * Proves: balance >= amount
 * Private: balance (the real wallet balance)
 * Public:  amount (the transaction amount)
 * Output:  has_enough (1 = sufficient, 0 = insufficient)
 */

include "node_modules/circomlib/circuits/comparators.circom";

template BalanceCheck() {
    // Private — the verifier never sees this
    signal input balance;

    // Public — merchant knows what they're charging
    signal input amount;

    // Output
    signal output has_enough;

    // Check: amount <= balance  i.e.  amount < balance + 1
    component lt = LessThan(64);
    lt.in[0] <== amount;
    lt.in[1] <== balance + 1;

    has_enough <== lt.out;
}

component main {public [amount]} = BalanceCheck();
