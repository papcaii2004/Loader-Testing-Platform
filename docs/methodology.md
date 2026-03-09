
# Multi-Stage Shellcode Loader Framework

## Overview

Traditional shellcode loaders are typically implemented as **single opaque executables**, making it difficult for researchers, learners, and defenders to clearly understand their internal behavior.

To address this problem, this project introduces a **structured loader framework** that decomposes the execution pipeline into a series of well-defined stages.

Each stage represents a **distinct functional responsibility** within the loader lifecycle.  
By separating these responsibilities, we can:

- systematically study evasion techniques
- experiment with different technique combinations
- map detection opportunities for security monitoring systems

This approach is conceptually similar to structured threat models such as **MITRE ATT&CK**, where attacker behavior is categorized into discrete tactics and techniques.

---

# Design Goals

The framework was designed with the following goals:

### 1. Standardization

Provide a **consistent model** for describing shellcode loaders.

Instead of describing loaders in vague terms, researchers can reference **specific stages and techniques**.

Example:

```

Loader = L0 + L1 + L2 + L3 + L4 + L5

```

---

### 2. Modular Experimentation

Each stage may contain **multiple interchangeable techniques**.

This allows controlled experiments such as:

- changing only the encryption method
- changing only the injection technique
- comparing detection results between implementations

---

### 3. Detection Mapping

Breaking loaders into stages allows defenders to **map detection points** more precisely.

For example:

| Stage | Detection Surface |
|------|-------------------|
| Storage | Network monitoring |
| Allocation | Memory allocation APIs |
| Writing | Process memory modification |
| Execution | Thread creation |

---

# Loader Execution Pipeline

The framework divides loader behavior into **six stages**.

```

L0 → L1 → L2 → L3 → L4 → L5

Anti-Analysis → Storage → Allocation → Transformation → Writing → Execution

```

Each stage is responsible for a specific part of the loader lifecycle.

---

# Stage Definitions

## L0 — Anti-Analysis

This stage performs checks to determine whether the program is running in an **analysis environment**.

Common targets include:

- sandboxes
- virtual machines
- debuggers
- automated malware analysis systems

Example techniques:

- CPU / RAM size checks
- debugger detection
- sleep delays
- sandbox artifact detection

Purpose:

Prevent execution in environments likely used for malware analysis.

---

## L1 — Storage

This stage defines **how the shellcode payload is stored before execution**.

The payload may originate from several sources.

Example techniques:

| Technique | Description |
|----------|-------------|
| Embedded | Shellcode stored directly in the loader |
| File | Shellcode loaded from disk |
| Network | Shellcode downloaded from remote server |

Purpose:

Define the **payload delivery mechanism**.

---

## L2 — Allocation

Before execution, memory must be allocated for the shellcode.

This stage prepares the memory region where the payload will be executed.

Example techniques:

| Technique | Description |
|----------|-------------|
| Local allocation | Memory allocated in the current process |
| Remote allocation | Memory allocated in another process |
| New process | Spawn process and allocate inside it |

Typical APIs:

- `VirtualAlloc`
- `VirtualAllocEx`
- `NtAllocateVirtualMemory`

Purpose:

Prepare executable memory space.

---

## L3 — Transformation

To evade static detection, shellcode is typically stored in an **encoded or encrypted format**.

This stage restores the original shellcode.

Example techniques:

| Technique | Description |
|----------|-------------|
| XOR | Simple XOR encryption |
| AES | AES encrypted payload |
| Custom encoding | Proprietary encoding scheme |

Purpose:

Decode or decrypt the payload prior to execution.

---

## L4 — Writing

This stage writes the decoded shellcode into the allocated memory region.

Example techniques:

| Technique | Description |
|----------|-------------|
| memcpy | Direct memory copy |
| WriteProcessMemory | Write into remote process memory |

Purpose:

Place the executable payload into memory.

---

## L5 — Execution

The final stage triggers execution of the shellcode.

Example techniques:

| Technique | Description |
|----------|-------------|
| CreateThread | Start thread in current process |
| NtCreateThreadEx | Native API thread creation |
| APC | Asynchronous Procedure Call execution |

Purpose:

Transfer control to the shellcode.

---

# Technique Identification

Techniques are identified using the following convention:

```

L<stage>.T<technique>

```

Example:

```

L3.T1 → XOR Decryption
L3.T2 → AES Decryption

L5.T1 → CreateThread
L5.T2 → APC Execution

```

A loader can therefore be represented as a **combination of techniques**.

Example loader configuration:

```

L0.T1 + L1.T1 + L2.T1 + L3.T2 + L4.T1 + L5.T1

```

---

# Relationship With This Repository

This repository implements:

- a **loader implementation framework**
- an **automated testing platform**

The platform automatically generates loaders using combinations of techniques and evaluates them against AV / EDR systems in controlled virtual environments.

This enables systematic research into:

- which techniques trigger detection
- which stages are most monitored
- how detection varies across security products

---

# Limitations

This framework is intended for **research and defensive analysis only**.

It does not aim to model every possible loader implementation, but rather to provide a **structured baseline** for studying shellcode execution pipelines.

All experiments should be performed **only in isolated research environments**.

---

# Future Work

Future improvements may include:

- additional loader stages
- expanded technique taxonomy
- automated detection analysis
- visualization of technique effectiveness
