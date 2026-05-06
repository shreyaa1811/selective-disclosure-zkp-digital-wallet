#!/bin/bash
set -e

CIRCUITS=("AgeCheck" "BalanceCheck" "KYCCheck")
KEYS_DIR="keys"
PTAU="$KEYS_DIR/pot14_final.ptau"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ZKP Wallet — Circuit Compilation Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p "$KEYS_DIR" proofs

# Step 1: Install circomlib if not present
if [ ! -d "node_modules/circomlib" ]; then
  echo ""
  echo " Installing circomlib..."
  npm install circomlib
fi

# Step 2: Powers of Tau (shared trusted setup, only needed once)
if [ ! -f "$PTAU" ]; then
  echo ""
  echo " Running Powers of Tau ceremony (this takes ~30 seconds)..."
  snarkjs powersoftau new bn128 14 "$KEYS_DIR/pot14_0000.ptau" -v
  snarkjs powersoftau contribute "$KEYS_DIR/pot14_0000.ptau" "$KEYS_DIR/pot14_0001.ptau" \
    --name="First contribution" -v -e="random entropy for zkp wallet"
  snarkjs powersoftau prepare phase2 "$KEYS_DIR/pot14_0001.ptau" "$PTAU" -v
  echo "✓ Powers of Tau complete."
fi

# Step 3: Compile each circuit
for CIRCUIT in "${CIRCUITS[@]}"; do
  CIRCUIT_LOWER=$(echo "$CIRCUIT" | tr '[:upper:]' '[:lower:]')
  echo ""
  echo "━━━ Compiling $CIRCUIT ━━━"

  # 3a. Compile circuit → r1cs + wasm
  circom "circuits/$CIRCUIT.circom" \
  --r1cs --wasm --sym \
  --output "$KEYS_DIR" \
  -l /mnt/c/Users/18Shr/Desktop/zkp_wallet

  echo "  ✓ Compiled to R1CS + WASM"

  # 3b. Groth16 trusted setup for this circuit
  snarkjs groth16 setup \
    "$KEYS_DIR/$CIRCUIT.r1cs" \
    "$PTAU" \
    "$KEYS_DIR/${CIRCUIT_LOWER}_0000.zkey"

  # 3c. Contribute randomness (in real production: multi-party ceremony)
  snarkjs zkey contribute \
    "$KEYS_DIR/${CIRCUIT_LOWER}_0000.zkey" \
    "$KEYS_DIR/${CIRCUIT_LOWER}_final.zkey" \
    --name="Wallet contributor" -v \
    -e="wallet zkp entropy $CIRCUIT"

  # 3d. Export verification key
  snarkjs zkey export verificationkey \
    "$KEYS_DIR/${CIRCUIT_LOWER}_final.zkey" \
    "$KEYS_DIR/${CIRCUIT_LOWER}_vkey.json"

  echo "  ✓ Proving key: keys/${CIRCUIT_LOWER}_final.zkey"
  echo "  ✓ Verification key: keys/${CIRCUIT_LOWER}_vkey.json"

  # Move wasm to expected location (circom outputs to keys/<circuit>_js/)
  if [ -d "$KEYS_DIR/${CIRCUIT}_js" ]; then
    mv "$KEYS_DIR/${CIRCUIT}_js" "$KEYS_DIR/${CIRCUIT_LOWER}_js" 2>/dev/null || true
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  All circuits compiled successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

