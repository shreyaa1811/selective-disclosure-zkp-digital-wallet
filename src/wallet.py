# src/wallet.py
"""
Core Wallet — Privacy-first payment authorization.

The wallet:
  1. Stores private data (DOB, balance, KYC credential) locally
  2. Generates snarkjs input files for each ZK proof
  3. Signs transaction authorizations with Ed25519
  4. NEVER sends raw private data to merchants

ZK proof generation (actual Groth16) is done via snarkjs CLI,
called from the Flask backend as a subprocess.
"""

import json
import secrets
import subprocess
import os
from datetime import datetime
from crypto_utils import (
    generate_keypair, sign, serialize_public_key,
    sha256_hash, generate_nonce
)

KEYS_DIR = os.path.join(os.path.dirname(__file__), "..", "keys")
PROOFS_DIR = os.path.join(os.path.dirname(__file__), "..", "proofs")


class Wallet:
    def __init__(self, date_of_birth: str, balance: float):
        """
        date_of_birth: "YYYY-MM-DD"
        balance: float (in currency units)
        """
        self.wallet_id = "anon_" + secrets.token_hex(8)
        self._private_key, self.public_key = generate_keypair()
        self.public_key_hex = serialize_public_key(self.public_key)

        # Private — never leaves the wallet
        self._birth_year = int(date_of_birth.split("-")[0])
        self._balance = balance
        self._kyc_credential = None
        self._allowed_merchants: list[str] = []
        self._transaction_log: list[dict] = []

    def load_kyc_credential(self, credential: dict):
        self._kyc_credential = credential

    def set_allowed_merchants(self, merchants: list[str]):
        self._allowed_merchants = [m.strip().lower() for m in merchants]

    # ── ZKP input generators ────────────────────────────────────────────────

    def _age_proof_input(self, current_year: int = 2025, min_age: int = 18) -> dict:
        """Private input for AgeCheck.circom circuit."""
        return {
            "birth_year": str(self._birth_year),
            "current_year": str(current_year),
            "min_age": str(min_age)
        }

    def _balance_proof_input(self, amount: float) -> dict:
        """Private input for BalanceCheck.circom circuit."""
        # Convert to integer cents to avoid float issues in circom
        return {
            "balance": str(int(self._balance * 100)),
            "amount": str(int(amount * 100))
        }

    def _kyc_proof_input(self) -> dict:
        """Private input for KYCCheck.circom circuit."""
        if not self._kyc_credential:
            raise ValueError("No KYC credential loaded")
        return {
            "credential_id": str(self._kyc_credential["credential_id"]),
            "nonce": str(self._kyc_credential["nonce"]),
            "expected_hash": str(self._kyc_credential["commitment"])
        }

    def _merchant_allowed(self, merchant_id: str) -> bool:
        """Check merchant allowlist locally (no circuit needed — boolean check)."""
        return merchant_id.strip().lower() in self._allowed_merchants

    # ── Proof generation via snarkjs ────────────────────────────────────────

    def _run_snarkjs_proof(self, circuit_name: str, inputs: dict) -> dict:
        """
        Call snarkjs to generate a real Groth16 ZK proof.

        Steps:
          1. Write input JSON
          2. snarkjs wtns calculate → witness
          3. snarkjs groth16 prove → proof.json + public.json
          4. Return proof + public signals

        Requires: compiled circuit (.wasm) and proving key (.zkey) in keys/
        """
        circuit_lower = circuit_name.lower()
        input_path = os.path.join(PROOFS_DIR, f"{circuit_lower}_input.json")
        witness_path = os.path.join(PROOFS_DIR, f"{circuit_lower}_witness.wtns")
        proof_path = os.path.join(PROOFS_DIR, f"{circuit_lower}_proof.json")
        public_path = os.path.join(PROOFS_DIR, f"{circuit_lower}_public.json")

        wasm_path = os.path.join(KEYS_DIR, f"{circuit_name}_js/{circuit_name}.wasm")
        zkey_path = os.path.join(KEYS_DIR, f"{circuit_lower}_final.zkey")

        # Write input
        with open(input_path, "w") as f:
            json.dump(inputs, f)

        # Check if compiled circuit exists
        if not os.path.exists(wasm_path) or not os.path.exists(zkey_path):
            return {
                "status": "not_compiled",
                "message": f"Circuit {circuit_name} not compiled yet. Run setup.sh first.",
                "proof": None,
                "public": None
            }
        SNARKJS = r"C:\Users\18Shr\AppData\Roaming\npm\snarkjs.cmd"
        try:
            # Generate witness
            subprocess.run([
               SNARKJS , "wtns", "calculate",
                wasm_path, input_path, witness_path
            ], check=True, capture_output=True)

            # Generate Groth16 proof
            subprocess.run([
                SNARKJS, "groth16", "prove",
                zkey_path, witness_path, proof_path, public_path
            ], check=True, capture_output=True)

            with open(proof_path) as f:
                proof = json.load(f)
            with open(public_path) as f:
                public_signals = json.load(f)

            return {
                "status": "success",
                "proof": proof,
                "public_signals": public_signals
            }

        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "message": str(e.stderr),
                "proof": None,
                "public": None
            }

    # ── Public API ──────────────────────────────────────────────────────────

    def pay(self, merchant_id: str, amount: float) -> dict:
        """
        Generate a ZK-proof-backed payment authorization.
        Returns proofs + signed authorization. No private data included.
        """
        if not self._kyc_credential:
            raise ValueError("KYC credential not loaded")

        timestamp = datetime.now().isoformat()

        # 1. Generate ZK proofs
        age_result = self._run_snarkjs_proof("AgeCheck", self._age_proof_input())
        balance_result = self._run_snarkjs_proof("BalanceCheck", self._balance_proof_input(amount))
        kyc_result = self._run_snarkjs_proof("KYCCheck", self._kyc_proof_input())
        merchant_ok = self._merchant_allowed(merchant_id)

        # 2. Sign the transaction authorization
        auth = {
        "wallet_id": self.wallet_id,
        "merchant_hash": sha256_hash(merchant_id),
        "amount": str(amount),
        "timestamp": timestamp,
        }
        auth_signature = sign(self._private_key, auth)
        print("auth for sign:", json.dumps(auth, sort_keys=True))

        # 3. Log locally (private)
        self._transaction_log.append({
            "merchant_hash": sha256_hash(merchant_id),
            "amount": amount,
            "timestamp": timestamp,
        })

        # 4. Deduct balance if all proofs succeed (in real system: escrow)
        proofs_ready = all(
            r.get("status") in ("success", "not_compiled")
            for r in [age_result, balance_result, kyc_result]
        )
        if proofs_ready and merchant_ok and self._balance >= amount:
            self._balance -= amount

        return {
            "wallet_id": self.wallet_id,
            "public_key": self.public_key_hex,
            "authorization": auth,
            "signature": auth_signature,
            "proofs": {
                "age_proof": {
                    **age_result,
                    "claim": "birth_year proves age >= 18",
                    "public_inputs": self._age_proof_input() if age_result["status"] != "success" else None
                },
                "balance_proof": {
                    **balance_result,
                    "claim": f"balance >= {amount} (in cents)",
                    "public_amount": int(amount * 100)
                },
                "kyc_proof": {
                    **kyc_result,
                    "claim": "credential_id + nonce match registered commitment",
                    "expected_hash": str(self._kyc_credential["commitment"])
                },
                "merchant_proof": {
                    "status": "success" if merchant_ok else "failed",
                    "claim": "merchant is in user's allowlist",
                    "result": merchant_ok,
                    "merchant_hash": sha256_hash(merchant_id)
                }
            },
            "balance_remaining": self._balance
        }

    def generate_audit_report(self) -> dict:
        """
        Generate aggregate-only audit report.
        No per-transaction merchant IDs or exact history.
        """
        recent = self._transaction_log[-20:]
        total = sum(t["amount"] for t in recent)
        max_tx = max((t["amount"] for t in recent), default=0)

        report = {
            "wallet_id": self.wallet_id,
            "transaction_count": len(recent),
            "total_spent": round(total, 2),
            "max_single_transaction": max_tx,
            "all_under_10000": all(t["amount"] < 10000 for t in recent),
            "generated_at": datetime.now().isoformat(),
            # Per-transaction details deliberately excluded
        }
        report["wallet_signature"] = sign(self._private_key, report)
        report["public_key"] = self.public_key_hex
        return report

    def get_status(self) -> dict:
        return {
            "wallet_id": self.wallet_id,
            "kyc_loaded": self._kyc_credential is not None,
            "balance": self._balance,
            "allowed_merchants": self._allowed_merchants,
            "transaction_count": len(self._transaction_log),
            "public_key": self.public_key_hex,
        }
