# Federated Learning Version Control System (FL-VCS) on a Blockchain

Welcome! This guide provides a detailed walkthrough for setting up and running the Federated Learning Version Control System (FL-VCS) on a local blockchain. Follow these steps carefully to get from a fresh project clone to a fully functional simulation.

---

## Part 1: Project Structure 🏗️

The repository is organized into the following structure:

```
fl-vcs-blockchain/
├── contracts/
│   └── FLLedger.sol            // Core Solidity smart contract - logic for the ledger, branching, access control, and policies
├── scripts/
│   └── deploy.py               // Python script for contract deployment
├── src/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── flvcs.py            // Command-line interface (CLI) logic
│   └── ledger/
│       ├── __init__.py
│       ├── interfaces.py       // Python class to interact with contracts
│       └── ipfs_store.py       // Local IPFS simulator for artifacts
├── .gitignore
├── hardhat.config.js           // Hardhat configuration file
├── package.json                // Node.js dependencies
└── requirements.txt            // Python dependencies
```

---

## Part 2: Prerequisites ⚙️

Before you begin, ensure you have the following software installed on your system.

1.  **Git**: You'll need Git to clone the project repository.
    * [Download Git](https://git-scm.com/downloads)
2.  **Node.js** (v20.x recommended): We use Node.js to run the Hardhat development environment for our local blockchain.
    * [Download Node.js](https://nodejs.org/en)
3.  **Python** (v3.8+ required): The deployment and command-line scripts are written in Python.
    * [Download Python](https://www.python.org/downloads/)
4.  **VS Code (Recommended)**: A code editor will make it much easier to view and edit files.
    * [Download VS Code](https://code.visualstudio.com/download)

---

## Part 3: Project Setup and Installation 📂

First, get the code and install all the necessary dependencies for both the blockchain and Python environments.

### 1. Clone the Repository

Open your terminal or command prompt, navigate to where you want to store the project, and run:

```bash
git clone https://github.com/fms-faisal/fl-vcs-blockchain.git
cd fl-vcs-blockchain
```

### 2. Install Dependencies

Once the files are in place, install the necessary dependencies.

1.  **Install Node.js Dependencies**
    ```bash
    npm install
    ```

2.  **Set Up the Python Environment**
    * **Create the virtual environment:**
        ```bash
        python -m venv venv
        ```
    * **Activate the virtual environment:**
        * On **Windows (PowerShell/CMD)**:
            ```cmd
            venv\Scripts\activate
            ```
        * On **macOS/Linux**:
            ```bash
            source venv/bin/activate
            ```
        *You'll know it's active when you see `(venv)` at the start of your terminal prompt.*

    * **Install Python packages:**
        ```bash
        pip install -r requirements.txt
        ```

---

## Part 4: Running the End-to-End Workflow ▶️

This is the core of the process. You will need **three separate terminal windows** open simultaneously.

### Terminal 1: Start the Local Blockchain ⛓️

This terminal's only job is to run the blockchain. You will start it and leave it running.

1.  Open your **first** terminal window.
2.  Navigate to the `fl-vcs-blockchain` project directory.
3.  Run the Hardhat node:
    ```bash
    npx hardhat node
    ```
4.  Hardhat will start and display a list of 20 test accounts. **Copy the Private Key for Account #0**. You will need this for the next steps.
5.  **Keep this terminal open!** Closing it will shut down your blockchain.

### Terminal 2: Compile & Deploy Contracts 🚀

1.  Open a **new, second** terminal window.
2.  Navigate to the project directory.
3.  **Activate the Python virtual environment** (`venv\Scripts\activate` or `source venv/bin/activate`).
4.  **Compile the smart contracts**. This step creates the `artifacts` folder that the deployment script needs.
    ```bash
    npx hardhat compile
    ```
5.  **Deploy the contracts**. Paste the private key you copied from Terminal 1 in place of `<YOUR_PRIVATE_KEY>`.
    ```bash
    python scripts/deploy.py --pk <YOUR_PRIVATE_KEY>
    ```
    *Upon success, this will print the deployed contract addresses and create a `.env.deployed` file.*

### Terminal 3: Use the FL-VCS CLI 💻

This is where you will interact with your deployed contracts.

1.  Open a **new, third** terminal window.
2.  Navigate to the project directory and **activate the virtual environment**.
3.  **Set Environment Variables**. This is a critical step.

    * **On PowerShell**:
        ```powershell
        # This command sets the FLVCS_PK variable
        $env:FLVCS_PK="<YOUR_PRIVATE_KEY>"

        # This command reads the registry address and sets the FLVCS_REGISTRY variable
        $env:FLVCS_REGISTRY=(Get-Content .env.deployed | Select-String -Pattern "REGISTRY_ADDRESS").Line.Split('=')[1]
        ```
    * **On Command Prompt (cmd.exe)**:
        ```cmd
        :: First, open the .env.deployed file and copy the registry address, then run:
        set FLVCS_PK=<YOUR_PRIVATE_KEY>
        set FLVCS_REGISTRY=<PASTE_THE_REGISTRY_ADDRESS_HERE>
        ```
    * **On macOS/Linux**:
        ```bash
        export $(cat .env.deployed | xargs)
        export FLVCS_PK=<YOUR_PRIVATE_KEY>
        export FLVCS_REGISTRY=$REGISTRY_ADDRESS
        ```

4.  **Simulate the FL Workflow**. Now you can run the commands.

    * **Create a dummy model file:**
        ```bash
        echo "This is a dummy model for round 1" > model_round_1.bin
        ```
    * **Commit Round 1** (This will output a Commit ID. Copy it.):
        ```bash
        python -m src.cli.flvcs commit --artifact model_round_1.bin --round 1
        ```
    * **Create the 'main' branch** (use the Commit ID from Round 1):
        ```bash
        python -m src.cli.flvcs branch-create --name main --head <COMMIT_ID_1>
        ```
    * **Create a model file for Round 2:**
        ```bash
        echo "This is an updated model from round 2" > model_round_2.bin
        ```
    * **Commit Round 2** (This will output a new Commit ID. Copy it.):
        ```bash
        python -m src.cli.flvcs commit --artifact model_round_2.bin --round 2
        ```
    * **Advance the 'main' branch** (use the Commit ID from Round 2):
        ```bash
        python -m src.cli.flvcs advance --name main --new-head <COMMIT_ID_2>
        ```

Congratulations! You have successfully run the entire simulation.

---

## Part 5: Troubleshooting Guide 🔍

During development, we encountered several issues. Here is a summary of the errors and their solutions for future reference.

* **ERROR 1: `FileNotFoundError: ... Registry.json`**
    * **Cause**: The Python deployment script couldn't find the compiled contract files. This was due to either the contracts not being compiled yet, or a mismatch in the file paths. All contracts are in `FLLedger.sol`, but the script was looking for `Registry.sol`, `CommitLedger.sol`, etc.
    * **Solution**:
        1.  Ensure you run `npx hardhat compile` before deploying.
        2.  Correct the file paths in `scripts/deploy.py` and `src/ledger/interfaces.py` to point to `contracts/FLLedger.sol/{name}.json` instead of `contracts/{name}.sol/{name}.json`.

* **ERROR 2: `KeyError: 'name'` during deployment**
    * **Cause**: The deployment script was trying to print the contract's name by incorrectly parsing the ABI, causing it to crash.
    * **Solution**: The `send_tx` helper function in `scripts/deploy.py` was modified to accept the contract name as a direct argument, ensuring correct and safe logging.

* **ERROR 3: `Error: --registry address is required`**
    * **Cause**: The CLI script could not find the `FLVCS_REGISTRY` environment variable. This was due to a mismatch between the variable name set (`REGISTRY_ADDRESS`) and the one the app expected (`FLVCS_REGISTRY`).
    * **Solution**: Manually set the environment variable with the correct name: `$env:FLVCS_REGISTRY="0x..."`. The instructions in this guide have been updated to prevent this issue.

* **ERROR 4: `NameError: name 'abi' is not defined`**
    * **Cause**: The CLI script (`src/cli/flvcs.py`) used a function `abi.encode()` without importing the necessary library.
    * **Solution**: Add the line `from eth_abi import abi` to the top of `src/cli/flvcs.py`.

* **ERROR 5: `Error: No such command 'branch_create'`**
    * **Cause**: The CLI command was defined in the script as `branch_create` but the user-friendly name `branch-create` was intended.
    * **Solution**: Modify the Click decorator in `src/cli/flvcs.py` to `@cli.command(name="branch-create")` to expose the command with a hyphen.
