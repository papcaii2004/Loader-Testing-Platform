# Automated Loader Testing Platform
*(Research & Educational Use Only)*

## Overview

This project provides an **automated testing platform for evaluating shellcode loader techniques against AV and EDR solutions**.

The platform automates the entire testing workflow:

- build loader payloads
- deploy them to isolated virtual machines
- execute them in controlled environments
- collect detection logs
- analyze results across different techniques

The goal is to support **systematic research on shellcode loader behavior** and improve both **offensive experimentation (Red Team)** and **defensive detection analysis (Blue Team)**.

The loader techniques implemented in this repository follow a **structured multi-stage model**.  
Detailed documentation of the framework and techniques can be found in (here)[./docs/]

---

# Features

- Automated payload building
- Technique-based loader generation
- Virtual machine orchestration via `vmrun`
- Snapshot-based environment reset
- Automated log collection from target systems
- CLI-based experiment execution

---

# System Architecture

```

CLI → Core Engine → Builder → VMware VMs
↓
Logs Collector

```

| Component | Description |
|---|---|
| CLI | Interface for running experiments |
| Core Engine | Coordinates the testing workflow |
| Builder | Generates loader payloads |
| VM Manager | Controls VM lifecycle using `vmrun` |
| Logs Collector | Retrieves detection logs from VMs |

---

# Workflow

1. Select techniques and shellcode
2. Encrypt / prepare payload
3. Build loader executable
4. Reset VM to clean snapshot
5. Deploy payload to VM
6. Execute payload
7. Collect logs from target system
8. Store results for analysis

---

# Project Structure

```

.
├── src/
│   ├── api/                 # API execution modes
│   │   ├── normal/          # Standard Windows API
│   │   ├── indirect/        # Indirect syscall implementations
│   │   └── direct/          # Direct syscall implementations
│   │
│   ├── core/                # Windows internal definitions & utilities
│   │
│   └── techniques/          # Loader techniques grouped by stage
│
├── controller/
│   ├── modules/
│   │   ├── builder.py       # Payload builder
│   │   ├── crypto_utils.py  # Shellcode encryption utilities
│   │   └── vm_manager.py    # VMware automation via vmrun
│   │
│   ├── core_engine.py       # Main orchestration logic
│   └── config.py            # Paths, VM configuration, environment settings
│
├── logs_collector/          # Scripts for collecting logs from VMs
│
├── docs/                    # Research documentation
│   ├── framework.md
│   └── techniques/
│
├── cli.py                   # CLI entry point
│
├── shellcodes/              # Sample shellcodes
├── output/                  # Generated loader executables
└── test_logs/               # Execution & detection logs

````

---

# Technology Stack

| Technology | Purpose |
|---|---|
| Python | Experiment orchestration |
| C++ | Loader implementation |
| MinGW-w64 | Payload compilation |
| VMware | Virtualized test environment |
| vmrun | VM automation interface |

---

# Requirements

- Python **3.8+**
- **VMware Workstation / Player**
- `vmrun` CLI
- **MinGW-w64**
- Windows test VMs

VM setup requirements:

- VMware Tools installed
- Snapshot named `clean_snapshot`
- Target AV / EDR installed
- Sample submission disabled (to prevent payload leaks)

Recommended storage: **≥100GB**

---

# Documentation

Detailed research documentation is available in:

```
docs/
```

Contents include:

* loader framework design
* implemented techniques
* lab environment configuration
* detection analysis notes

---

# Research Scope

This platform is intended strictly for **security research and defensive analysis**.

All experiments must be performed in **isolated lab environments**.
Generated payloads must **never be distributed or executed outside controlled systems**.

---

# License

This project is intended for **educational and research purposes only**.
