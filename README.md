# 🔐 ZKP Compliance Wallet

A privacy-preserving digital wallet using real **Groth16 zk-SNARKs** (circom + snarkjs) for selective disclosure of identity and financial properties, with optional audit mode.

---

## What It Does

- Proves **age ≥ 18** without revealing date of birth
- Proves **KYC verified** without revealing identity details
- Proves **balance ≥ amount** without revealing actual balance
- Enforces **merchant allowlist** locally
- Generates **aggregate-only audit reports** signed with Ed25519
- All three ZK proofs are real Groth16 proofs over BN254

---

## Stack

| Layer | Technology |
|---|---|
| ZK Circuits | circom 2.2.3 |
| ZK Proof Generation | snarkjs 0.7.6 |
| ZK-friendly Hash | circomlibjs |
| Circuit Primitives | circomlib |
| Backend | Python 3.11+ / Flask |
| Signing | Ed25519 via Python cryptography library |
| Frontend | HTML / CSS / Vanilla JS |

---

## Prerequisites

You need **three things** installed before anything else:

### 1. Node.js (v18 or higher)
Download from https://nodejs.org and install normally on Windows.

### 2. Python 3.11+
Download from https://python.org and install normally on Windows.

### 3. WSL (Windows Subsystem for Linux)
This project requires WSL because circom 2 only has a Linux binary.

Open PowerShell as Administrator and run:
```powershell
wsl --install
```
Restart your PC when prompted. This installs Ubuntu by default.

---

## Important — Two Environments

This project uses **two environments** and you need to know which is which:

| Environment | Used for | How to open |
|---|---|---|
| WSL terminal | Compiling circuits (setup.sh) | In VS Code: terminal dropdown → select Ubuntu/WSL |
| Windows PowerShell | Running Flask app | Normal VS Code terminal |

---

## First-Time Setup

Follow these steps **in order**. Do each step completely before moving to the next.

---

### Step 1 — Install Node.js inside WSL

WSL is a separate Linux environment and does not share the Windows Node.js installation. You must install Node.js inside WSL separately.

Open a **WSL terminal** and run:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt-get install -y nodejs
```

Verify:
```bash
node --version
npm --version
```
Both should print version numbers. If node shows v20.x.x you are good.

---

### Step 2 — Install circom 2 inside WSL

circom must be version 2. The npm version (`npm install -g circom`) installs the old v0.5 which does NOT support `pragma circom 2.0.0` syntax. Install the binary directly:

```bash
cd ~
curl -L https://github.com/iden3/circom/releases/latest/download/circom-linux-amd64 -o circom
chmod +x circom
sudo mv circom /usr/local/bin/
```

If `circom --version` still shows old version after this, run:
```bash
hash -r
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify:
```bash
circom --version
```
Must show `circom compiler 2.x.x`. If it still shows 0.5.x, uninstall the npm version first:
```bash
sudo npm uninstall -g circom
```

---

### Step 3 — Install snarkjs inside WSL

```bash
sudo npm install -g snarkjs
```

Verify:
```bash
snarkjs --version
```

---

### Step 4 — Install circomlib in project folder (WSL)

Navigate to your project folder in WSL and install circomlib:

```bash
cd /mnt/c/Users/YourName/Desktop/zkp_wallet
npm install circomlib
```

Replace `YourName` with your actual Windows username. Your Windows Desktop is accessible from WSL at `/mnt/c/Users/YourName/`.

Verify:
```bash
ls node_modules/circomlib/circuits/comparators.circom
```
Should print the file path without error.

---

### Step 5 - Update src/wallet.py with specific details

Open `src/wallet.py` and find `SNARKJS` at the top of `_run_snarkjs_proof`. 
By default it is set to `"snarkjs"` which works if snarkjs is in your PATH.

If you get a `FileNotFoundError` for snarkjs, replace it with your full path:

1. Run in PowerShell:
```powershell
   npm config get prefix
```
2. Take that output (e.g. `C:\Users\YourName\AppData\Roaming\npm`) and update wallet.py:
```python
   SNARKJS = r"C:\Users\YourName\AppData\Roaming\npm\snarkjs.cmd"
```

### Step 6 — Compile the circuits (WSL)

Still in WSL, inside the project folder:

```bash
bash setup.sh
```

This will:
1. Run Powers of Tau ceremony
2. Compile AgeCheck.circom → .r1cs + .wasm
3. Compile BalanceCheck.circom → .r1cs + .wasm
4. Compile KYCCheck.circom → .r1cs + .wasm
5. Generate proving keys (.zkey) for each circuit
6. Generate verification keys (_vkey.json) for each circuit

The FFT debug output looks like this — it is normal, do not close the terminal:
```
[DEBUG] snarkJS: tauG2: fft 14 join  11/14  6/8 0/1
[DEBUG] snarkJS: tauG2: fft 14 join  11/14  4/8 0/1
...
```

When finished you should see:
```
 All circuits compiled successfully!
```

Verify the keys folder was created:
```bash
ls keys/
```

You should see: `AgeCheck_js/`, `BalanceCheck_js/`, `KYCCheck_js/`, `agecheck_final.zkey`, `balancecheck_final.zkey`, `kyccheck_final.zkey` and matching `_vkey.json` files.

**Note:** If setup.sh is interrupted and you need to rerun it, the Powers of Tau step is skipped automatically because `keys/pot14_final.ptau` already exists. Rerunning only recompiles the circuits.

---

### Step 7 — Install Python dependencies (PowerShell)

Switch to a **PowerShell terminal** now. Navigate to your project folder:

```powershell
cd C:\Users\YourName\Desktop\zkp_wallet
pip install -r requirements.txt
```

Verify:
```powershell
python -c "import flask, cryptography; print('OK')"
```

---

### Step 8 — Install snarkjs on Windows (PowerShell)

The Flask app runs on Windows and calls snarkjs as a subprocess. snarkjs must also be installed on Windows:

```powershell
npm install -g snarkjs
```

Then find where npm installed it:
```powershell
npm config get prefix
```

This prints something like `C:\Users\YourName\AppData\Roaming\npm`. Open `src/wallet.py` and find this line near the top of `_run_snarkjs_proof`:

```python
SNARKJS = r"C:\Users\YourName\AppData\Roaming\npm\snarkjs.cmd"
```

Update the path to match what `npm config get prefix` returned, adding `\snarkjs.cmd` at the end.

---

### Step 9 — Install circomlibjs (PowerShell)

The Flask app uses circomlibjs to compute Poseidon hashes that match the circuit:

```powershell
npm install circomlibjs
```

Run this inside the project folder.

---

## Running the App

Once all 8 setup steps are done, every time you want to run the app:

```powershell
cd C:\Users\YourName\Desktop\zkp_wallet
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

You should see:
```
🔐 ZKP Wallet running at http://127.0.0.1:5000
```

---

## Using the App

**Step 1 — Issue KYC Credential**
Fill in date of birth, balance, country, and allowed merchants (comma separated). Click "Issue KYC Credential". The right panel shows the Poseidon commitment — this is what gets registered publicly. Your DOB and identity are not in the output.

**Step 2 — Make a Payment**
Enter a merchant ID that is in your allowed list (e.g. `amazon`) and an amount. Click "Pay with ZK Proofs". You will see four proof cards. If circuits compiled correctly, each shows `REAL Groth16 zk-SNARK ✓` with actual π_a, π_b, π_c values.

**Step 3 — Test Blocked Merchant**
Click "Try Blocked Merchant". The merchant proof should show red FAIL and the payment should be rejected.

**Step 4 — Request Audit Report**
Click "Request Audit Report". You get transaction count, total spent, max single transaction — no merchant names, no individual transaction details.

---

## Verifying Everything Works

Run these tests in order to confirm all security properties:

**Valid payment:**
Set merchant `amazon`, amount `150`, DOB `1998-05-15`, balance `5000`. All four proofs should pass and payment should be accepted.

**Blocked merchant:**
Click "Try Blocked Merchant". Merchant proof should fail, payment rejected.

**Underage user:**
Open PowerShell and run:
```powershell
curl.exe -X POST http://127.0.0.1:5000/api/setup -H "Content-Type: application/json" -d '{\"dob\": \"2010-01-01\", \"balance\": 5000, \"country\": \"UAE\", \"merchants\": [\"amazon\"]}'
curl.exe -X POST http://127.0.0.1:5000/api/pay -H "Content-Type: application/json" -d '{\"merchant_id\": \"amazon\", \"amount\": \"100\"}'
```
AgeCheck public signal should be `"0"`.

**Insufficient balance:**
```powershell
curl.exe -X POST http://127.0.0.1:5000/api/setup -H "Content-Type: application/json" -d '{\"dob\": \"1998-05-15\", \"balance\": 50, \"country\": \"UAE\", \"merchants\": [\"amazon\"]}'
curl.exe -X POST http://127.0.0.1:5000/api/pay -H "Content-Type: application/json" -d '{\"merchant_id\": \"amazon\", \"amount\": \"500\"}'
```
BalanceCheck public signal should be `"0"`.

**Tamper test:**
```powershell
curl.exe -X POST http://127.0.0.1:5000/api/verify -H "Content-Type: application/json" -d '{\"payment\": {\"wallet_id\": \"anon_fake\", \"public_key\": \"0000000000000000000000000000000000000000000000000000000000000000\", \"authorization\": {\"wallet_id\": \"anon_fake\", \"merchant_hash\": \"abc\", \"amount\": \"100\", \"timestamp\": \"2025-01-01\"}, \"signature\": \"deadbeefdeadbeef\", \"proofs\": {}}}'
```
Should return `accepted: false`, `signature_valid: false`.

---

