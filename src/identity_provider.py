# src/identity_provider.py
import uuid
import secrets
import subprocess
import tempfile
import os
from datetime import datetime
from crypto_utils import generate_keypair, sign, serialize_public_key


class IdentityProvider:
    def __init__(self, name: str = "TrustedKYC_Authority"):
        self.name = name
        self._private_key, self.public_key = generate_keypair()
        self.commitment_registry: dict[str, int] = {}

    def _compute_poseidon(self, a: int, b: int) -> int:
        """
        Compute Poseidon(a, b) using circomlibjs in Node.js.
        This is the EXACT same Poseidon the KYCCheck.circom circuit uses.
        """
        script = """
const { buildPoseidon } = require("circomlibjs");
(async () => {
    try {
        const poseidon = await buildPoseidon();
        const F = poseidon.F;
        const hash = poseidon([BigInt("%s"), BigInt("%s")]);
        console.log(F.toString(hash));
    } catch(e) {
        console.error(e);
        process.exit(1);
    }
})();
""" % (str(a), str(b))

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.js', delete=False, dir='.'
        ) as f:
            f.write(script)
            tmp = f.name

        try:
            result = subprocess.run(
                ["node", tmp],
                capture_output=True, text=True, check=True
            )
            return int(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Poseidon computation failed: {e.stderr}")
        finally:
            os.unlink(tmp)

    def issue_credential(self, user_data: dict) -> dict:
        credential_id_int = int(secrets.token_hex(8), 16)   
        nonce_int = int(secrets.token_hex(8), 16)            

        commitment = self._compute_poseidon(credential_id_int, nonce_int)

        self.commitment_registry[str(credential_id_int)] = commitment

        credential = {
            "credential_id": credential_id_int,
            "nonce": nonce_int,
            "commitment": commitment,
            "issuer": self.name,
            "kyc_level": user_data.get("kyc_level", "standard"),
            "country": user_data.get("country", ""),
            "verified": True,
            "issued_at": datetime.now().isoformat(),
        }

        signable = {
            "credential_id": str(credential_id_int),
            "commitment": str(commitment),
            "issuer": self.name,
            "issued_at": credential["issued_at"],
        }
        credential["issuer_signature"] = sign(self._private_key, signable)
        credential["issuer_public_key"] = serialize_public_key(self.public_key)

        return credential

    def get_commitment(self, credential_id_int: int) -> int:
        return self.commitment_registry.get(str(credential_id_int), 0)