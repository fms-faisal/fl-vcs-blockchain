import argparse
import json
import pathlib
from web3 import Web3
from dotenv import set_key

# --- Helper Functions ---
ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

def _load_abi_bytecode(name: str):
    artifact_path = ARTIFACTS / f"contracts/FLLedger.sol/{name}.json"
    with open(artifact_path) as f:
        data = json.load(f)
    return data["abi"], data["bytecode"]

def deploy(w3: Web3, pk: str):
    acct = w3.eth.account.from_key(pk)
    print(f"Deploying contracts from account: {acct.address}")

    # FIX: Pass the contract name to the helper function for correct logging
    def send_tx(contract_name: str, contract, constructor_args=None):
        tx_hash = contract.constructor(*constructor_args if constructor_args else []).transact({"from": acct.address})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        # FIX: Use the passed-in name instead of guessing from the ABI
        print(f"✅ {contract_name} deployed at: {receipt.contractAddress}")
        return w3.eth.contract(address=receipt.contractAddress, abi=contract.abi)

    # --- Deployment Sequence ---
    print("\n--- Starting Deployment ---")
    reg_abi, reg_bin = _load_abi_bytecode("Registry")
    Registry = w3.eth.contract(abi=reg_abi, bytecode=reg_bin)
    # FIX: Pass name to send_tx
    registry = send_tx("Registry", Registry)

    pol_abi, pol_bin = _load_abi_bytecode("PolicyRegistry")
    Policy = w3.eth.contract(abi=pol_abi, bytecode=pol_bin)
    # FIX: Pass name to send_tx
    policy_registry = send_tx("PolicyRegistry", Policy)

    cl_abi, cl_bin = _load_abi_bytecode("CommitLedger")
    CL = w3.eth.contract(abi=cl_abi, bytecode=cl_bin)
    # FIX: Pass name to send_tx
    commit_ledger = send_tx("CommitLedger", CL)

    bm_abi, bm_bin = _load_abi_bytecode("BranchManager")
    BM = w3.eth.contract(abi=bm_abi, bytecode=bm_bin)
    # FIX: Pass name to send_tx
    branch_manager = send_tx("BranchManager", BM, constructor_args=[commit_ledger.address, policy_registry.address])
    
    # --- Wire up registry ---
    print("\n--- Configuring Registry ---")
    def register_contract(name, address):
        tx_hash = registry.functions.set(Web3.keccak(text=name), address).transact({'from': acct.address})
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Registered {name} -> {address}")

    register_contract("CommitLedger", commit_ledger.address)
    register_contract("BranchManager", branch_manager.address)
    register_contract("PolicyRegistry", policy_registry.address)
    
    print("\n--- Deployment Complete ---")
    return {
        "REGISTRY_ADDRESS": registry.address,
        "DEPLOYER_ADDRESS": acct.address,
    }
    acct = w3.eth.account.from_key(pk)
    print(f"Deploying contracts from account: {acct.address}")

    def send_tx(contract, constructor_args=None):
        tx_hash = contract.constructor(*constructor_args if constructor_args else []).transact({"from": acct.address})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"✅ {contract.abi[0]['name']} deployed at: {receipt.contractAddress}")
        return w3.eth.contract(address=receipt.contractAddress, abi=contract.abi)

    # --- Deployment Sequence ---
    print("\n--- Starting Deployment ---")
    reg_abi, reg_bin = _load_abi_bytecode("Registry")
    Registry = w3.eth.contract(abi=reg_abi, bytecode=reg_bin)
    registry = send_tx(Registry)

    pol_abi, pol_bin = _load_abi_bytecode("PolicyRegistry")
    Policy = w3.eth.contract(abi=pol_abi, bytecode=pol_bin)
    policy_registry = send_tx(Policy)

    cl_abi, cl_bin = _load_abi_bytecode("CommitLedger")
    CL = w3.eth.contract(abi=cl_abi, bytecode=cl_bin)
    commit_ledger = send_tx(CL)

    bm_abi, bm_bin = _load_abi_bytecode("BranchManager")
    BM = w3.eth.contract(abi=bm_abi, bytecode=bm_bin)
    branch_manager = send_tx(BM, constructor_args=[commit_ledger.address, policy_registry.address])
    
    # --- Wire up registry ---
    print("\n--- Configuring Registry ---")
    def register_contract(name, address):
        tx_hash = registry.functions.set(Web3.keccak(text=name), address).transact({'from': acct.address})
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Registered {name} -> {address}")

    register_contract("CommitLedger", commit_ledger.address)
    register_contract("BranchManager", branch_manager.address)
    register_contract("PolicyRegistry", policy_registry.address)
    
    print("\n--- Deployment Complete ---")
    return {
        "REGISTRY_ADDRESS": registry.address,
        "DEPLOYER_ADDRESS": acct.address,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy FL-VCS contracts.")
    parser.add_argument("--rpc", default="http://127.0.0.1:8545", help="RPC URL of the Ethereum node.")
    parser.add_argument("--pk", required=True, help="Private key of the deployer account.")
    parser.add_argument("--save", default=".env.deployed", help="File to save deployed addresses.")
    args = parser.parse_args()

    w3 = Web3(Web3.HTTPProvider(args.rpc))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to RPC at {args.rpc}")

    addresses = deploy(w3, args.pk)
    
    env_file = pathlib.Path(args.save)
    for key, value in addresses.items():
        set_key(str(env_file), key, value)
    
    print(f"\n✅ Deployed addresses saved to {env_file.name}")
    print("\n".join([f"{k}={v}" for k, v in addresses.items()]))
