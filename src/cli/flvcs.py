import os
import pathlib
import click
from web3 import Web3
from eth_abi import abi  # <-- Add this line
from rich.console import Console
from src.ledger.interfaces import FLVCSWeb3
from src.ledger.ipfs_store import LocalIPFS

console = Console()

@click.group()
@click.option("--rpc", default=lambda: os.environ.get("FLVCS_RPC", "http://127.0.0.1:8545"), help="RPC URL")
@click.option("--pk", envvar="FLVCS_PK", help="Admin private key")
@click.option("--registry", envvar="FLVCS_REGISTRY", help="Registry contract address")
@click.pass_context
def cli(ctx, rpc, pk, registry):
    ctx.ensure_object(dict)
    if not registry:
        console.print("[bold red]Error:[/bold red] --registry address is required. Set FLVCS_REGISTRY env var.")
        exit(1)
    ctx.obj["w3_interface"] = FLVCSWeb3(rpc, pk)
    ctx.obj["contracts"] = ctx.obj["w3_interface"].load_contracts(registry)
    ctx.obj["pk"] = pk
    ctx.obj["rpc"] = rpc

@cli.command()
@click.option("--artifact", type=click.Path(exists=True, dir_okay=False), required=True, help="Path to the model artifact file.")
@click.option("--round", type=int, required=True)
@click.option("--parents", multiple=True, help="Parent commit hex hashes (for merges).")
@click.pass_context
def commit(ctx, artifact, round, parents):
    """Adds a new commit to the ledger."""
    w3_interface = ctx.obj["w3_interface"]
    contracts = ctx.obj["contracts"]
    ipfs = LocalIPFS()

    console.print(f"Reading artifact from [cyan]{artifact}[/cyan]...")
    data = pathlib.Path(artifact).read_bytes()
    artifact_hash_str, artifact_uri = ipfs.add_bytes(data)
    console.print(f"Stored artifact. Hash: [green]{artifact_hash_str[:12]}[/green], URI: [yellow]{artifact_uri}[/yellow]")

    # Create dummy hashes for other metadata
    clients_hash = Web3.keccak(text="client1,client2")
    hparams_hash = Web3.keccak(text="lr=0.01,bs=32")
    
    # Parents logic
    if parents:
        parent_bytes = [bytes.fromhex(p[2:]) for p in parents]
    else:
        # If no parent is specified, this is a root commit. It has a placeholder parent.
        parent_bytes = [b'\x00' * 32] 
    
    # Off-chain ID calculation
    commit_id = Web3.keccak(
        abi.encode(
            ['bytes32[]', 'uint64', 'bytes32', 'bytes32', 'bytes32', 'string'],
            [parent_bytes, round, clients_hash, hparams_hash, Web3.to_bytes(hexstr=artifact_hash_str), artifact_uri]
        )
    )

    commit_input = {
        "id": commit_id,
        "parents": parent_bytes,
        "round": round,
        "clientsHash": clients_hash,
        "hyperparamsHash": hparams_hash,
        "artifactHash": Web3.to_bytes(hexstr=artifact_hash_str),
        "artifactURI": artifact_uri,
        "scores": {"accTimes1e4": 0, "lossTimes1e4": 0},
        "aggregatorSig": b"",
    }

    console.print(f"Submitting commit to ledger. ID: [green]{commit_id.hex()}[/green]")
    tx = contracts.commit_ledger.functions.addCommit(commit_input)
    receipt = w3_interface.send(tx)
    console.print(f"✅ Commit added. Tx: [bold blue]{receipt.transactionHash.hex()}[/bold blue]")
    console.print(f"New commit ID: [bold green]{commit_id.hex()}[/bold green]")


@cli.command(name="branch-create")
@click.option("--name", required=True)
@click.option("--head", required=True, help="The commit ID for the branch head.")
@click.pass_context
def branch_create(ctx, name, head):
    """Creates a new branch."""
    w3_interface = ctx.obj["w3_interface"]
    contracts = ctx.obj["contracts"]
    tx = contracts.branch_manager.functions.createBranch(name, Web3.to_bytes(hexstr=head), b'\x00' * 32)
    rc = w3_interface.send(tx)
    console.print(f"✅ Branch '{name}' created. Tx: {rc.transactionHash.hex()}")

@cli.command()
@click.option("--name", required=True)
@click.option("--new-head", required=True)
@click.pass_context
def advance(ctx, name, new_head):
    """Advances a branch to a new commit."""
    w3_interface = ctx.obj["w3_interface"]
    contracts = ctx.obj["contracts"]
    tx = contracts.branch_manager.functions.advance(name, Web3.to_bytes(hexstr=new_head))
    rc = w3_interface.send(tx)
    console.print(f"✅ Advanced '{name}' to {new_head}. Tx: {rc.transactionHash.hex()}")

@cli.command()
@click.option("--name", required=True)
@click.option("--to", "to_commit", required=True)
@click.pass_context
def rollback(ctx, name, to_commit):
    """Rolls back a branch to a previous commit."""
    w3_interface = ctx.obj["w3_interface"]
    contracts = ctx.obj["contracts"]
    tx = contracts.branch_manager.functions.rollback(name, Web3.to_bytes(hexstr=to_commit))
    rc = w3_interface.send(tx)
    console.print(f"✅ Rolled back '{name}' to {to_commit}. Tx: {rc.transactionHash.hex()}")

if __name__ == "__main__":
    cli()
