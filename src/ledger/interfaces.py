from __future__ import annotations
import json
import pathlib
from dataclasses import dataclass
from web3 import Web3

ROOT = pathlib.Path(__file__).resolve().parents[2]
ARTIFACTS = (ROOT / "artifacts").resolve()

@dataclass
class Contracts:
    registry: any
    commit_ledger: any
    branch_manager: any
    policy_registry: any

class FLVCSWeb3:
    def __init__(self, rpc_url: str, private_key: str | None = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = None
        if private_key:
            self.account = self.w3.eth.account.from_key(private_key)

    def _load_abi(self, name: str) -> dict:
        artifact_path = ARTIFACTS / f"contracts/FLLedger.sol/{name}.json"
        with open(artifact_path) as f:
            data = json.load(f)
        return data["abi"]

    def _contract(self, address: str, name: str):
        abi = self._load_abi(name)
        return self.w3.eth.contract(address=self.w3.to_checksum_address(address), abi=abi)

    def load_contracts(self, registry_addr: str) -> Contracts:
        registry = self._contract(registry_addr, "Registry")
        def get_addr(name: str):
            key = self.w3.keccak(text=name)
            addr = registry.functions.get(key).call()
            if int(addr, 16) == 0:
                raise RuntimeError(f"Registry address missing for {name}")
            return addr
        
        commit_ledger = self._contract(get_addr("CommitLedger"), "CommitLedger")
        branch_manager = self._contract(get_addr("BranchManager"), "BranchManager")
        policy_registry = self._contract(get_addr("PolicyRegistry"), "PolicyRegistry")
        return Contracts(registry, commit_ledger, branch_manager, policy_registry)

    def send(self, tx_fn):
        if not self.account:
            raise RuntimeError("Private key not set to send transaction")
        
        tx = tx_fn.build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt