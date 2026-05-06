# app.py
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from identity_provider import IdentityProvider
from wallet import Wallet
from crypto_utils import verify_signature, deserialize_public_key

app = Flask(__name__)
CORS(app)

_idp = IdentityProvider("TrustedKYC_Authority")
_wallet: Wallet | None = None
_audit_log: list[dict] = []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/setup", methods=["POST"])
def setup():
    global _wallet
    data = request.json

    dob = data.get("dob", "1998-01-01")
    balance = float(data.get("balance", 5000))
    country = data.get("country", "UAE")
    merchants = data.get("merchants", ["amazon", "noon", "careem"])

    credential = _idp.issue_credential({
        "kyc_level": "full",
        "country": country,
    })

    _wallet = Wallet(date_of_birth=dob, balance=balance)
    _wallet.load_kyc_credential(credential)
    _wallet.set_allowed_merchants(merchants)

    return jsonify({
        "success": True,
        "wallet_id": _wallet.wallet_id,
        "credential_id": str(credential["credential_id"]),
        "commitment": str(credential["commitment"]),
        "issuer": credential["issuer"],
        "issued_at": credential["issued_at"],
        "message": "KYC credential issued and wallet initialized."
    })


@app.route("/api/pay", methods=["POST"])
def pay():
    if _wallet is None:
        return jsonify({"error": "Wallet not initialized. Run setup first."}), 400

    data = request.json
    merchant_id = data.get("merchant_id", "amazon")
    amount = float(data.get("amount", 100))

    result = _wallet.pay(merchant_id=merchant_id, amount=amount)
    return jsonify(result)


@app.route("/api/verify", methods=["POST"])
def verify():
    data = request.json
    payment = data.get("payment")

    if not payment:
        return jsonify({"error": "No payment data provided"}), 400

    # Verify Ed25519 signature
    try:
        pub_key = deserialize_public_key(payment["public_key"])
        print("auth for verify:", json.dumps(payment["authorization"], sort_keys=True))
        sig_valid = verify_signature(pub_key, payment["authorization"], payment["signature"])
        print("sig_valid result:", sig_valid)
        try:
            pub_key2 = deserialize_public_key(payment["public_key"])
            sig_bytes = bytes.fromhex(payment["signature"])
            pub_key2.verify(sig_bytes, test_msg)
            print("direct verify: SUCCESS")
        except Exception as e:
            print("direct verify ERROR:", str(e))
    except Exception as e:
        sig_valid = False

    # Check all proof results
    proofs = payment.get("proofs", {})
    proof_results = {}

    for name, proof in proofs.items():
        if name == "merchant_proof":
            passed = proof.get("result", False)
        elif proof.get("status") == "success":
            sigs = proof.get("public_signals", [])
            passed = len(sigs) > 0 and sigs[0] == "1"
        else:
            passed = proof.get("result", False)

        proof_results[name] = {
            "passed": passed,
            "claim": proof.get("claim", ""),
            "status": proof.get("status", "unknown")
        }

    all_passed = sig_valid and all(p["passed"] for p in proof_results.values())

    print("=== CHECK STATUS ===")
    print("auth received:", json.dumps(payment["authorization"], sort_keys=True))
    print("sig received:", payment["signature"])
    print("pubkey:", payment["public_key"])
    print("sig length:", len(payment["signature"]))
    test_msg = json.dumps(payment["authorization"], sort_keys=True).encode()
    print("message bytes:", test_msg)

    return jsonify({
        "accepted": all_passed,
        "signature_valid": sig_valid,
        "proof_results": proof_results,
        "wallet_id": payment.get("wallet_id"),
    })



@app.route("/api/audit", methods=["GET"])
def audit():
    if _wallet is None:
        return jsonify({"error": "Wallet not initialized"}), 400

    report = _wallet.generate_audit_report()

    try:
        pub_key = deserialize_public_key(report["public_key"])
        sig = report.pop("wallet_signature")
        pub_key_str = report.pop("public_key")
        sig_valid = verify_signature(pub_key, report, sig)
        report["wallet_signature"] = sig
        report["public_key"] = pub_key_str
    except Exception:
        sig_valid = False

    _audit_log.append(report)

    return jsonify({
        **report,
        "signature_valid": sig_valid,
        "note": "Full transaction history NOT disclosed. Aggregates only."
    })


@app.route("/api/status", methods=["GET"])
def status():
    if _wallet is None:
        return jsonify({"initialized": False})
    return jsonify({"initialized": True, **_wallet.get_status()})


@app.route("/api/reset", methods=["POST"])
def reset():
    global _wallet
    _wallet = None
    return jsonify({"success": True, "message": "Wallet reset."})


if __name__ == "__main__":
    print("🔐 ZKP Wallet running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)