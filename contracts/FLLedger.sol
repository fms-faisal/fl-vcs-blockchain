// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Types and shared errors
library Types {
    struct Scores {
        uint32 accTimes1e4; // accuracy * 1e4
        uint32 lossTimes1e4; // loss * 1e4
    }

    struct CommitInput {
        bytes32 id; // commit id = keccak256 of canonical tuple off chain
        bytes32[] parents; // 1 for normal round, 2 for merge commit
        uint64 round; // FL round number
        bytes32 clientsHash; // hash of participating client ids
        bytes32 hyperparamsHash; // hash of {lr, bs, dp_epsilon, seed, etc}
        bytes32 artifactHash; // hash of model artifact bytes
        string artifactURI; // e.g., ipfs://CID or s3://bucket/key
        Scores scores; // optional metrics
        bytes aggregatorSig; // aggregator signature over id
    }

    struct CommitMeta {
        bool exists;
        bytes32[] parents;
        uint64 round;
        bytes32 clientsHash;
        bytes32 hyperparamsHash;
        bytes32 artifactHash;
        string artifactURI;
        Scores scores;
        uint64 timestamp;
        address submitter;
    }

    struct Policy {
        bool exists;
        bytes32 id; // keccak256(name)
        string name;
        uint32 minAccTimes1e4; // minimum accuracy * 1e4
        bool dpRequired; // require dp
        string anomalyFilter; // descriptor of server side filter
    }

    error NotAuthorized();
    error AlreadyExists();
    error DoesNotExist();
    error InvalidInput();
}

/// @title Minimal access control
contract Access {
    address public owner;
    mapping(address => bool) public admins;
    event OwnerChanged(address indexed oldOwner, address indexed newOwner);
    event AdminSet(address indexed account, bool isAdmin);

    constructor() {
        owner = msg.sender;
        emit OwnerChanged(address(0), owner);
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert Types.NotAuthorized();
        _;
    }

    modifier onlyAdmin() {
        if (msg.sender != owner && !admins[msg.sender]) revert Types.NotAuthorized();
        _;
    }

    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero");
        emit OwnerChanged(owner, newOwner);
        owner = newOwner;
    }

    function setAdmin(address account, bool isAdmin) external onlyOwner {
        admins[account] = isAdmin;
        emit AdminSet(account, isAdmin);
    }
}

/// @title Policy Registry for acceptance rules
contract PolicyRegistry is Access {
    mapping(bytes32 => Types.Policy) private policies; // id => policy

    event PolicyUpsert(bytes32 indexed id, string name, uint32 minAccTimes1e4, bool dpRequired, string anomalyFilter);
    event PolicyRemove(bytes32 indexed id);

    function upsertPolicy(string calldata name, uint32 minAccTimes1e4, bool dpRequired, string calldata anomalyFilter) external onlyAdmin {
        bytes32 id = keccak256(abi.encodePacked(name));
        Types.Policy storage p = policies[id];
        p.exists = true;
        p.id = id;
        p.name = name;
        p.minAccTimes1e4 = minAccTimes1e4;
        p.dpRequired = dpRequired;
        p.anomalyFilter = anomalyFilter;
        emit PolicyUpsert(id, name, minAccTimes1e4, dpRequired, anomalyFilter);
    }

    function removePolicy(bytes32 id) external onlyAdmin {
        if (!policies[id].exists) revert Types.DoesNotExist();
        delete policies[id];
        emit PolicyRemove(id);
    }

    function getPolicy(bytes32 id) external view returns (Types.Policy memory) {
        if (!policies[id].exists) revert Types.DoesNotExist();
        return policies[id];
    }
}

/// @title Commit Ledger stores immutable commits and tags
contract CommitLedger is Access {
    mapping(bytes32 => Types.CommitMeta) private commits; // commit id => meta
    mapping(bytes32 => bytes32) public tags; // tagId => commitId

    event CommitAdded(bytes32 indexed id, uint64 round, bytes32 artifactHash, string artifactURI, address submitter);
    event TagSet(bytes32 indexed tagId, bytes32 indexed commitId, string tagName);

    function hasCommit(bytes32 id) public view returns (bool) {
        return commits[id].exists;
    }

    function addCommit(Types.CommitInput calldata in_) external onlyAdmin {
        if (in_.id == bytes32(0)) revert Types.InvalidInput();
        if (commits[in_.id].exists) revert Types.AlreadyExists();
        if (in_.parents.length == 0 || in_.parents.length > 2) revert Types.InvalidInput();
        if (bytes(in_.artifactURI).length == 0) revert Types.InvalidInput();

        Types.CommitMeta storage m = commits[in_.id];
        m.exists = true;
        m.parents = in_.parents;
        m.round = in_.round;
        m.clientsHash = in_.clientsHash;
        m.hyperparamsHash = in_.hyperparamsHash;
        m.artifactHash = in_.artifactHash;
        m.artifactURI = in_.artifactURI;
        m.scores = in_.scores;
        m.timestamp = uint64(block.timestamp);
        m.submitter = msg.sender;

        emit CommitAdded(in_.id, in_.round, in_.artifactHash, in_.artifactURI, msg.sender);
    }

    function getCommit(bytes32 id) external view returns (Types.CommitMeta memory) {
        if (!commits[id].exists) revert Types.DoesNotExist();
        return commits[id];
    }

    function setTag(string calldata name, bytes32 commitId) external onlyAdmin {
        if (!commits[commitId].exists) revert Types.DoesNotExist();
        bytes32 tagId = keccak256(abi.encodePacked(name));
        tags[tagId] = commitId;
        emit TagSet(tagId, commitId, name);
    }
}

/// @title Branch Manager maintains branch heads
contract BranchManager is Access {
    CommitLedger public immutable ledger;
    PolicyRegistry public immutable policyReg;

    struct BranchInfo {
        bool exists;
        bytes32 nameId; // keccak256(name)
        string name;
        bytes32 head; // commit id
        bytes32 policyId; // acceptance policy
    }

    mapping(bytes32 => BranchInfo) public branches; // nameId => info

    event BranchCreated(bytes32 indexed nameId, string name, bytes32 head, bytes32 policyId);
    event BranchAdvanced(bytes32 indexed nameId, bytes32 fromCommit, bytes32 toCommit);
    event BranchRolledBack(bytes32 indexed nameId, bytes32 fromCommit, bytes32 toCommit);

    constructor(address _ledger, address _policyReg) {
        ledger = CommitLedger(_ledger);
        policyReg = PolicyRegistry(_policyReg);
    }

    function createBranch(string calldata name, bytes32 head, bytes32 policyId) external onlyAdmin {
        bytes32 nameId = keccak256(abi.encodePacked(name));
        if (branches[nameId].exists) revert Types.AlreadyExists();
        require(ledger.hasCommit(head), "Head commit does not exist");
        if (policyId != bytes32(0)) policyReg.getPolicy(policyId);

        branches[nameId] = BranchInfo({exists: true, nameId: nameId, name: name, head: head, policyId: policyId});
        emit BranchCreated(nameId, name, head, policyId);
    }

    function advance(string calldata name, bytes32 newHead) external onlyAdmin {
        bytes32 nameId = keccak256(abi.encodePacked(name));
        BranchInfo storage b = branches[nameId];
        if (!b.exists) revert Types.DoesNotExist();
        require(ledger.hasCommit(newHead), "New head commit does not exist");
        
        bytes32 old = b.head;
        b.head = newHead;
        emit BranchAdvanced(nameId, old, newHead);
    }

    function rollback(string calldata name, bytes32 target) external onlyAdmin {
        bytes32 nameId = keccak256(abi.encodePacked(name));
        BranchInfo storage b = branches[nameId];
        if (!b.exists) revert Types.DoesNotExist();
        require(ledger.hasCommit(target), "Target commit does not exist");

        bytes32 old = b.head;
        b.head = target;
        emit BranchRolledBack(nameId, old, target);
    }
}

/// @title Simple registry to find core contracts
contract Registry is Access {
    mapping(bytes32 => address) public addrs;
    event AddressSet(bytes32 indexed id, address addr);

    function set(bytes32 id, address addr) external onlyOwner {
        addrs[id] = addr;
        emit AddressSet(id, addr);
    }

    function get(bytes32 id) external view returns (address) {
        return addrs[id];
    }
}
