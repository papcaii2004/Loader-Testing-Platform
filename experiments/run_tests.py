#!/usr/bin/env python3
"""
experiments/run_tests.py — Automated test-matrix runner for 5 research questions.

Research-driven phase structure: orthogonal ablation study with L2/L5 constraints.
Each phase isolates a specific RQ; L2/L4/L5 pairings enforced by loader architecture.
ALL phases test across BOTH API modes (winapi + syscalls).

Constraints:
  IF L5 ∈ {local, monitors, fiber}
    THEN L2 ∈ {local, local_rw} AND L4 ∈ {local, local_rx}
  IF L5 == remote_thread
    THEN L2 ∈ {remote, spawn} AND L4 == remote

    Phase A — RQ1 Baseline
              Does the loader work at all?
              Config: baseline (L2=local, L4=local, L5=local) × 3 reps
    
    Phase B — RQ2 Local Allocations
              How do L2 allocation choices (local vs local_rw) affect detection?
              Vary: L2 ∈ {local, local_rw} + all L0/L1/L3/L5_local × 2 APIs
              L5_local = {local, monitors, fiber} (same-process methods only)
              Runs: 2 × 3 × 2 × 6 × 3 × 2 = 432 runs
    
    Phase C — RQ3 Remote Allocations
              How do cross-process L2 choices affect detection?
              Vary: L2 ∈ {remote, spawn} + all L0/L1/L3 × 2 APIs
              Fix: L4=remote, L5=remote_thread (enforced)
              Runs: 2 × 3 × 2 × 6 × 2 = 144 runs
    
    Phase D — RQ4 Cryptography
              Which L3 encryption/transformation is most evasive?
              Vary: L3 ∈ {none, xor, aes, rc4, chacha20, bitwise} × 2 APIs
              Fix: L0/L1/L2/L4/L5 to baseline
              Runs: 6 × 2 = 12 runs
    
    Phase E — RQ5 Anti-Analysis
              Which L0 anti-debug technique works?
              Vary: L0 ∈ {none, antidebug, sleep_skew} × 2 APIs
              Fix: L1/L2/L3/L4/L5 to baseline
              Runs: 3 × 2 = 6 runs

Total: 3 (sanity) + 432 + 144 + 12 + 6 = 597 runs

Per-batch output:
  experiments/runs/<batch_timestamp>/
      matrix.csv                  # all runs: config + outcome code + Defender events
      run_<id>_<rep>.log          # per-run builder/harness output + raw log
      guest_<id>_<rep>.txt        # Defender + Sysmon telemetry from VM

Usage:
  python experiments/run_tests.py -s shellcodes/payload.bin
  python experiments/run_tests.py -s ... --phases A,B,C,D,E --dry-run
  python experiments/run_tests.py -s ... --resume experiments/runs/20260425_120000
  python experiments/run_tests.py -s ... --summarize experiments/runs/20260425_120000
"""

import argparse
import collections
import csv
import hashlib
import logging
import os
import re
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, REPO_ROOT)

from controller import core_engine  # noqa: E402 — import after sys.path tweak
from controller.config import VMS_CONFIG, PROJECT_ROOT  # noqa: E402
from controller.modules.definitions import STAGE_FLAGS, API_FLAGS  # noqa: E402

BATCH_ROOT = os.path.join(HERE, "runs")  # experiments/runs/

T0_TECHNIQUES = list(STAGE_FLAGS["t0"].keys())
T1_TECHNIQUES = list(STAGE_FLAGS["t1"].keys())
T3_TECHNIQUES = list(STAGE_FLAGS["t3"].keys())
API_METHODS = list(API_FLAGS.keys())

LOCAL_EXEC_TECHNIQUES = [
    tech for tech in STAGE_FLAGS["t5"].keys()
    if tech != "remote_thread"
]
REMOTE_EXEC_TECHNIQUE = "remote_thread"


# ---------------------------------------------------------------------------
# Logging setup (overrides core_engine's basicConfig default of INFO)
# ---------------------------------------------------------------------------

def configure_logging(verbose_count):
    """
    verbose_count == 0 -> WARNING (quiet, default)
    verbose_count == 1 -> INFO    (-v)
    verbose_count >= 2 -> DEBUG   (-vv)
    """
    level = logging.WARNING
    if verbose_count == 1:
        level = logging.INFO
    elif verbose_count >= 2:
        level = logging.DEBUG

    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers:
        h.setLevel(level)


# ---------------------------------------------------------------------------
# Test plan
# ---------------------------------------------------------------------------

def _baseline(**overrides):
    cfg = {
        "t0": "none", "t1": "rdata",
        "t2": "local", "t4": "local",
        "t3": "none", "t5": "local",
        "api_method": "winapi", "debug": False,
    }
    cfg.update(overrides)
    return cfg


def _get_valid_l5_for_l2(l2_value):
    """Get valid L5 execution methods for L2 allocation strategy.
    
    Constraint: same-process L5 methods (local, monitors, fiber) only work
    with same-process L2 (local, local_rw). Cross-process requires remote_thread.
    """
    if l2_value in ("local", "local_rw"):
        return ["local", "monitors", "fiber"]  # Same-process L5 methods
    elif l2_value in ("remote", "spawn"):
        return ["remote_thread"]  # Cross-process only
    return ["local"]


def _pair_for_l2(l2_value):
    """Map L2 allocation strategy to required L4 value.
    
    Constraint: L4 must be paired with L2:
      - local → local
      - local_rw → local_rx (allows write-then-execute on W^X)
      - remote/spawn → remote (cross-process write)
    """
    pairs = {
        "local": "local",
        "local_rw": "local_rx",
        "remote": "remote",
        "spawn": "remote",
    }
    return pairs.get(l2_value, "local")


def _phase_vary_one(prefix, vary_stage, vary_values, fixed_overrides=None):
    """Generic: vary ONE stage, fix others to baseline, cross product with APIs.
    
    Args:
        prefix: phase ID prefix ("B", "C", "D", "E")
        vary_stage: stage to vary ("t0", "t1", "t2", "t3", "t4", "t5")
        vary_values: list of values for that stage
        fixed_overrides: dict of other stages to fix (merges with baseline)
    
    Returns:
        list of (id, config, reps) tuples
    """
    configs = []
    idx = 1
    overrides = fixed_overrides or {}
    
    for val in vary_values:
        for api in API_METHODS:  # Option C: all phases × 2 APIs
            cfg = _baseline(**overrides)
            cfg[vary_stage] = val
            cfg["api_method"] = api
            
            # If changing L2, update paired L4/L5
            if vary_stage == "t2":
                l4, l5 = _pair_for_l2(val)
                cfg["t4"] = l4
                if l5 is not None:
                    cfg["t5"] = l5
            
            configs.append((f"{prefix}{idx}", cfg, 1))
            idx += 1
    
    return configs


def phase_a():
    """RQ1: Baseline — does the loader work?
    
    Sanity check: baseline config × 3 reps to measure platform variance.
    """
    return [("A1", _baseline(), 3)]


def phase_b():
    """RQ2: Local Allocations — how do L2 allocation choices affect detection?
    
    Vary: L2 ∈ {local, local_rw} paired with L4 + all L0/L1/L3/L5_local-compatible × 2 APIs
    Fix: L4 auto-paired per L2 (local→local, local_rw→local_rx)
    Constraint: L5 limited to same-process methods {local, monitors, fiber}
    """
    configs = []
    idx = 1
    
    # Same-process L2 allocations
    local_l2s = ["local", "local_rw"]
    
    for l2 in local_l2s:
        l4 = _pair_for_l2(l2)
        valid_l5s = _get_valid_l5_for_l2(l2)  # Constraint: same-process L5s only
        
        for t3 in T3_TECHNIQUES:
            for t5 in valid_l5s:
                for api in API_METHODS:  # × 2 APIs
                    configs.append((
                        f"B{idx}",
                        _baseline(
                            t0="none", 
                            t1="rdata", 
                            t2=l2, t3=t3,
                            t4=l4, t5=t5, api_method=api
                        ),
                        1,
                    ))
                    idx += 1
    return configs


def phase_c():
    """RQ3: Remote Allocations — how do cross-process L2 choices affect detection?
    
    Vary: L2 ∈ {remote, spawn} with L0/L1/L3 × 2 APIs
    Fix: L4=remote, L5=remote_thread (required for cross-process)
    """
    configs = []
    idx = 1
    
    # Cross-process L2 allocations
    remote_l2s = ["remote", "spawn"]
    
    for l2 in remote_l2s:
        l4 = _pair_for_l2(l2)  # Always "remote"
        l5 = "remote_thread"  # Enforced: cross-process requires remote_thread
        
        for t3 in T3_TECHNIQUES:
            for api in API_METHODS:  # × 2 APIs
                configs.append((
                    f"C{idx}",
                    _baseline(
                        t0="none", 
                        t1="rdata",
                        t2=l2, t3=t3,
                        t4=l4, t5=l5, api_method=api
                    ),
                    1,
                ))
                idx += 1
    return configs


def phase_d():
    """RQ4: Cryptography — which L3 transformation/encryption is most evasive?
    
    Vary: L3 ∈ {none, xor, aes, rc4, chacha20, bitwise} × 2 APIs
    Fix: L0/L1/L2/L4/L5 to baseline (best local allocation)
    Ablation: isolate L3 impact on detection within same-process context.
    """
    configs = []
    idx = 1

    contexts = [
        {"t2": "local", "t4": "local", "t5": "local"},
        {"t2": "remote", "t4": "remote", "t5": "remote_thread"},
    ]

    for ctx in contexts:
        for t3 in T3_TECHNIQUES:
            for api in API_METHODS:
                configs.append((
                    f"D{idx}",
                    _baseline(
                        t0="none",
                        t1="rdata",
                        t2=ctx["t2"],
                        t4=ctx["t4"],
                        t5=ctx["t5"],
                        t3=t3,
                        api_method=api
                    ),
                    1,
                ))
                idx += 1

    return configs


def phase_e():
    """RQ5: Anti-Analysis — effectiveness across execution contexts.

    Vary: L0 × 2 APIs × 2 contexts
    Fix: L1/L2/L3/L4/L5 otherwise
    """
    configs = []
    idx = 1

    contexts = [
        {"t2": "local", "t4": "local", "t5": "local"},
        {"t2": "remote", "t4": "remote", "t5": "remote_thread"},
    ]

    for ctx in contexts:
        for t0 in STAGE_FLAGS["t0"].keys():
            for api in API_METHODS:
                configs.append((
                    f"E{idx}",
                    _baseline(
                        t0=t0,
                        t1="rdata",
                        t2=ctx["t2"],
                        t4=ctx["t4"],
                        t5=ctx["t5"],
                        t3="none",
                        api_method=api
                    ),
                    1,
                ))
                idx += 1

    return configs

PHASES = {
    "A": phase_a, "B": phase_b, "C": phase_c,
    "D": phase_d, "E": phase_e,
}


# ---------------------------------------------------------------------------
# Outcome classification
# ---------------------------------------------------------------------------
#
# Taxonomy aligned with Defender telemetry (parsed from guest log body):
#
#   CB      — callback received; no Defender 1116/1117
#             (clean bypass: loader reached shellcode AND Defender said nothing)
#   LD      — callback received; Defender 1116 and/or 1117 present
#             (late detection: shellcode phoned home before or despite
#             remediation — common when 1117 Action = "No Action")
#   EB      — no callback; Defender 1116/1117 present
#             (Defender blocked or terminated the chain; "Execution Blocked")
#   BLOCKED — no callback; no Defender events observed
#             (listener timed out, no visible Defender action — investigate
#             the guest log manually: possible crash, missing telemetry,
#             or collector anchor miss)
#   TB      — file blocked during transfer (Defender caught it on copy)
#   ERROR   — infrastructure / build failure
#   UNKNOWN — unparseable status (should not happen in practice)
#
# Prior single-argument classify(raw_status) mapped every "SUCCESS" to "S"
# regardless of Defender events, producing false positives in the matrix
# whenever the shellcode won a race against slow ML detection. The 5-way
# taxonomy above uses the guest log body to separate clean bypasses (CB)
# from late detections (LD) and provides an EB category that mirrors
# Defender's own "detected + remediated" outcome.


def parse_defender(log_body):
    """Extract Defender 1116/1117 counts + first 1117 Action from log body.

    The guest log format is produced by log_collectors/collect_all.ps1:
        Time:     ...
        EventID:  1116|1117|1118
        Threat:   ...
        Severity: ...
        File:     ...
        Action:   <Name> (id=<n>)
    One block per event. Parser is tolerant of the collector's empty-Action
    legacy output as well as the fixed "Name (id=N)" format.
    """
    body = log_body or ""
    n1116 = len(re.findall(r"EventID:\s+1116\b", body))
    n1117 = len(re.findall(r"EventID:\s+1117\b", body))
    action = ""
    # Grab the Action value from the first 1117 block if present.
    # Use [ \t]* (not \s*) after "Action:" so we only consume same-line
    # whitespace; \s* would greedily jump past the line terminator and
    # capture the next line (the "---..." separator) when Action is empty.
    m = re.search(r"EventID:\s+1117\b.*?\nAction:[ \t]*([^\n]*)", body, re.S)
    if m:
        action = m.group(1).strip()
    return {"def_1116": n1116, "def_1117": n1117, "def_action": action}


def classify(raw_status, def_info):
    """Map (raw_status, Defender counts) -> paper outcome code.

    See taxonomy block above the function for the meaning of each code.
    """
    s = (raw_status or "").upper()
    if "BUILD_FAILED" in s or "EXCEPTION" in s:
        return "ERROR"
    if "TRANSFER BLOCKED" in s:
        return "TB"

    callback = "SUCCESS" in s
    detected = (def_info["def_1116"] + def_info["def_1117"]) > 0

    if callback and not detected:
        return "CB"
    if callback and detected:
        return "LD"
    if not callback and detected:
        return "EB"
    # No callback and no Defender events — the listener timed out but the
    # cause is not observable in the Defender log. Could be crash, guest
    # collector failure, or telemetry anchor miss. Surface distinctly so
    # these don't silently merge with EB.
    if "EXECUTION BLOCKED" in s or "FAILED" in s:
        return "BLOCKED"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def short_name(cfg):
    return (
        f"t0={cfg['t0']} t1={cfg['t1']} t2={cfg['t2']} t3={cfg['t3']} "
        f"t4={cfg['t4']} t5={cfg['t5']} api={cfg['api_method']}"
    )


def sha256_short(path, n=16):
    if not path or not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def build_plan(phase_keys):
    runs = []
    for key in phase_keys:
        if key not in PHASES:
            print(f"[!] Unknown phase: {key}. Valid: {list(PHASES.keys())}")
            continue
        runs.extend(PHASES[key]())
    return runs


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

FIELDNAMES = [
    "id", "rep", "started_at",
    "t0", "t1", "t2", "t3", "t4", "t5", "api",
    "payload_sha256", "raw_status", "code",
    "def_1116", "def_1117", "def_action",
    "wall_time_s", "log_file",
]


def resolve_batch_dir(resume_arg):
    """Resolve --resume argument to (batch_dir, csv_path).

    Accepts either:
      - path to a batch directory (e.g., experiments/runs/20260420_170000)
      - path to matrix.csv inside a batch directory
      - path to a legacy experiment_matrix_*.csv in test_logs/ (older runs)
    """
    if not resume_arg:
        return None, None
    p = os.path.abspath(resume_arg)
    if os.path.isdir(p):
        return p, os.path.join(p, "matrix.csv")
    if os.path.isfile(p):
        return os.path.dirname(p), p
    return None, None


def load_done_keys(csv_path):
    done = set()
    if not csv_path or not os.path.isfile(csv_path):
        return done
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add((row["id"], str(row["rep"])))
    return done


def run_all(shellcode_path, vm_name, phase_keys, resume_arg=None):
    # Resolve batch directory: resume into existing, or create new.
    resume_dir, resume_csv = resolve_batch_dir(resume_arg)
    if resume_dir:
        batch_dir = resume_dir
        out_csv = resume_csv
        mode = "a"
        done = load_done_keys(resume_csv)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = os.path.join(BATCH_ROOT, stamp)
        os.makedirs(batch_dir, exist_ok=True)
        out_csv = os.path.join(batch_dir, "matrix.csv")
        mode = "w"
        done = set()

    runs = build_plan(phase_keys)
    total = sum(reps for _, _, reps in runs)
    print(f"[plan]      {total} runs across phases {','.join(phase_keys)}")
    print(f"[batch]     {batch_dir}")
    print(f"[vm]        {vm_name}")
    print(f"[shellcode] {shellcode_path}  sha256={sha256_short(shellcode_path)}")

    f_csv = open(out_csv, mode, newline="", encoding="utf-8")
    writer = csv.DictWriter(f_csv, fieldnames=FIELDNAMES)
    if mode == "w":
        writer.writeheader()
        f_csv.flush()

    idx = 0
    try:
        for cfg_id, cfg, reps in runs:
            for rep in range(1, reps + 1):
                idx += 1
                key = (cfg_id, str(rep))
                if key in done:
                    print(f"[{idx}/{total}] SKIP {cfg_id}/{rep} (resumed)")
                    continue

                started = datetime.now().strftime("%Y%m%d_%H%M%S")
                print(f"\n[{idx}/{total}] {cfg_id}/{rep}  {short_name(cfg)}")
                t0 = time.time()

                run_log_name = f"run_{cfg_id}_{rep}.log"
                guest_log_name = f"guest_{cfg_id}_{rep}.txt"

                raw_status = "UNKNOWN"
                log_body = ""
                payload_path = None
                try:
                    payload_path = core_engine.build_payload(shellcode_path, cfg)
                    if not payload_path:
                        raw_status = "BUILD_FAILED"
                        log_body = "core_engine.build_payload returned None"
                    else:
                        result = core_engine.run_single_test(
                            vm_name, payload_path, cfg,
                            log_dir=batch_dir,
                            log_name=guest_log_name,
                        )
                        raw_status = result.get("status", "UNKNOWN")
                        log_body = result.get("log", "") or ""
                except Exception as exc:
                    raw_status = f"EXCEPTION: {exc}"
                    log_body = f"Python exception: {exc}"

                wall = round(time.time() - t0, 1)
                def_info = parse_defender(log_body)
                code = classify(raw_status, def_info)

                # Per-run run_*.log (build+status summary + log body tail)
                run_log_path = os.path.join(batch_dir, run_log_name)
                with open(run_log_path, "w", encoding="utf-8", errors="replace") as lf:
                    lf.write(f"id={cfg_id} rep={rep}\n")
                    lf.write(f"started={started}\n")
                    lf.write(f"config={cfg}\n")
                    lf.write(f"raw_status={raw_status}\n")
                    lf.write(f"code={code}\n")
                    lf.write(f"def_1116={def_info['def_1116']} "
                             f"def_1117={def_info['def_1117']} "
                             f"def_action={def_info['def_action']!r}\n")
                    lf.write(f"wall_time_s={wall}\n")
                    lf.write(f"payload={payload_path}\n")
                    lf.write("---\n")
                    lf.write(log_body)

                writer.writerow({
                    "id": cfg_id,
                    "rep": rep,
                    "started_at": started,
                    "t0": cfg["t0"], "t1": cfg["t1"], "t2": cfg["t2"],
                    "t3": cfg["t3"], "t4": cfg["t4"], "t5": cfg["t5"],
                    "api": cfg["api_method"],
                    "payload_sha256": sha256_short(payload_path),
                    "raw_status": raw_status,
                    "code": code,
                    "def_1116": def_info["def_1116"],
                    "def_1117": def_info["def_1117"],
                    "def_action": def_info["def_action"],
                    "wall_time_s": wall,
                    "log_file": run_log_name,
                })
                f_csv.flush()
                print(f"       -> code={code}  1116={def_info['def_1116']} "
                      f"1117={def_info['def_1117']}  ({wall}s)  raw={raw_status}")
    finally:
        f_csv.close()

    print(f"\n[done] batch: {batch_dir}")
    summarize_csv(out_csv)
    return batch_dir


# ---------------------------------------------------------------------------
# Error analysis: extract ERROR/EXCEPTION runs for re-testing or manual review
# ---------------------------------------------------------------------------


def fix_and_update_csv(shellcode_path, vm_name, resume_arg):
    batch_dir, csv_path = resolve_batch_dir(resume_arg)
    if not csv_path or not os.path.isfile(csv_path):
        print(f"[!] Cannot resolve batch: {resume_arg}")
        return

    # đọc toàn bộ CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    updated = 0

    for row in rows:
        raw = (row.get("raw_status") or "").upper()
        code = (row.get("code") or "").upper()

        if not (
            code in ("ERROR", "UNKNOWN")
            or any(x in raw for x in ["EXCEPTION", "TIMEOUT", "SSH"])
        ):
            continue

        cfg = {
            "t0": row["t0"],
            "t1": row["t1"],
            "t2": row["t2"],
            "t3": row["t3"],
            "t4": row["t4"],
            "t5": row["t5"],
            "api_method": row["api"],
            "debug": False,
        }

        cfg_id = row["id"]
        rep = row["rep"]

        print(f"[fix] {cfg_id}/{rep}  {short_name(cfg)}")

        started = datetime.now().strftime("%Y%m%d_%H%M%S")
        t0_time = time.time()

        run_log_name = f"run_{cfg_id}_{rep}.log"
        guest_log_name = f"guest_{cfg_id}_{rep}.txt"

        raw_status = "UNKNOWN"
        log_body = ""
        payload_path = None

        try:
            payload_path = core_engine.build_payload(shellcode_path, cfg)
            if not payload_path:
                raw_status = "BUILD_FAILED"
            else:
                result = core_engine.run_single_test(
                    vm_name, payload_path, cfg,
                    log_dir=batch_dir,
                    log_name=guest_log_name,
                )
                raw_status = result.get("status", "UNKNOWN")
                log_body = result.get("log", "") or ""
        except Exception as exc:
            raw_status = f"EXCEPTION: {exc}"
            log_body = str(exc)

        wall = round(time.time() - t0_time, 1)
        def_info = parse_defender(log_body)
        code_new = classify(raw_status, def_info)

        # update row
        row.update({
            "started_at": started,
            "raw_status": raw_status,
            "code": code_new,
            "def_1116": def_info["def_1116"],
            "def_1117": def_info["def_1117"],
            "def_action": def_info["def_action"],
            "wall_time_s": wall,
            "payload_sha256": sha256_short(payload_path),
            "log_file": run_log_name,
        })

        # overwrite log
        with open(os.path.join(batch_dir, run_log_name), "w", encoding="utf-8") as lf:
            lf.write(f"id={cfg_id} rep={rep}\n")
            lf.write(f"config={cfg}\n")
            lf.write(f"raw_status={raw_status}\n")
            lf.write(f"code={code_new}\n")
            lf.write("---\n")
            lf.write(log_body)

        updated += 1

    # backup
    backup = csv_path + ".bak"
    if not os.path.isfile(backup):
        with open(csv_path, "r", encoding="utf-8") as src, \
             open(backup, "w", encoding="utf-8") as dst:
            dst.write(src.read())

    # ghi lại CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[fix-run] updated {updated} rows")


# ---------------------------------------------------------------------------
# Summary (used both at end of batch and via --summarize)
# ---------------------------------------------------------------------------

def summarize_csv(csv_path):
    if not os.path.isfile(csv_path):
        print(f"[!] CSV not found: {csv_path}")
        return

    by_phase = collections.defaultdict(collections.Counter)
    by_phase_time = collections.defaultdict(float)
    total_time = 0.0
    total_runs = 0
    reps_per_id = collections.defaultdict(list)

    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            phase = row["id"][0] if row["id"] else "?"
            code = row["code"]
            by_phase[phase][code] += 1
            try:
                t = float(row["wall_time_s"])
            except (ValueError, TypeError):
                t = 0.0
            by_phase_time[phase] += t
            total_time += t
            total_runs += 1
            reps_per_id[row["id"]].append(code)

    print("\n" + "=" * 60)
    print(" Experiment summary")
    print("=" * 60)

    phase_names = {
        "A": "RQ1: Baseline",
        "B": "RQ2: Local Allocations",
        "C": "RQ3: Remote Allocations",
        "D": "RQ4: Cryptography",
        "E": "RQ5: Anti-Analysis",
    }
    for phase in sorted(by_phase):
        counts = by_phase[phase]
        total = sum(counts.values())
        t = by_phase_time[phase]
        pretty = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        name = phase_names.get(phase, phase)
        print(f"Phase {phase} ({name:<12}): {total:2d} runs | {pretty:<32s} | {t/60:5.1f} min")

    # Flag disagreements within a config id (only meaningful if rep>1)
    disagreements = [
        (cid, codes) for cid, codes in reps_per_id.items()
        if len(codes) > 1 and len(set(codes)) > 1
    ]
    if disagreements:
        print("\n[!] Non-deterministic outcomes within same config id:")
        for cid, codes in disagreements:
            print(f"    {cid}: {codes}")

    m = int(total_time // 60)
    s = int(total_time % 60)
    print(f"\nTotal runs: {total_runs}  |  Total wall time: {m}m {s}s")
    print(f"Batch:  {os.path.dirname(csv_path)}")
    print(f"CSV:    {csv_path}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Reclassify: rebuild matrix.csv from existing run_*.log files
# ---------------------------------------------------------------------------

def _extract_log_body(run_log_path):
    """Read a run_*.log produced by this runner and return the log_body.

    File layout (see run_all()):
        id=...
        started=...
        ...
        ---
        <log_body>
    """
    try:
        with open(run_log_path, "r", encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except OSError:
        return ""
    parts = txt.split("\n---\n", 1)
    return parts[1] if len(parts) == 2 else txt


def reclassify_batch(arg):
    """Rebuild matrix.csv from per-run logs using the current classifier.

    Reads run_<id>_<rep>.log for each row, re-parses Defender events, and
    rewrites matrix.csv with the new schema (adds def_1116 / def_1117 /
    def_action columns and the 5-way code). The original CSV is saved
    alongside as matrix.csv.bak so the old labels are not lost.
    """
    batch_dir, csv_path = resolve_batch_dir(arg)
    if not csv_path or not os.path.isfile(csv_path):
        print(f"[!] Cannot resolve batch CSV from: {arg}")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        old_rows = list(csv.DictReader(f))
    if not old_rows:
        print(f"[!] CSV has no data rows: {csv_path}")
        return

    # Backup
    backup = csv_path + ".bak"
    if not os.path.isfile(backup):
        with open(csv_path, "r", encoding="utf-8") as src, \
             open(backup, "w", encoding="utf-8", newline="") as dst:
            dst.write(src.read())
        print(f"[backup] saved original -> {backup}")

    # Rewrite with new schema
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        transitions = collections.Counter()
        for old in old_rows:
            cfg_id = old.get("id", "")
            rep = old.get("rep", "")
            run_log = os.path.join(batch_dir, f"run_{cfg_id}_{rep}.log")
            body = _extract_log_body(run_log)
            def_info = parse_defender(body)
            new_code = classify(old.get("raw_status", ""), def_info)

            old_code = old.get("code", "")
            transitions[(old_code, new_code)] += 1

            out = {k: old.get(k, "") for k in FIELDNAMES}
            out["code"] = new_code
            out["def_1116"] = def_info["def_1116"]
            out["def_1117"] = def_info["def_1117"]
            out["def_action"] = def_info["def_action"]
            writer.writerow(out)

    print(f"[reclassify] wrote {len(old_rows)} rows to {csv_path}")
    print(f"[reclassify] label transitions (old -> new):")
    for (a, b), n in sorted(transitions.items(), key=lambda kv: (-kv[1], kv[0])):
        arrow = "    " if a == b else " -> "
        print(f"   {a:>8}{arrow}{b:<8}  {n}")
    print()
    summarize_csv(csv_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("-s", "--shellcode",
                        help="Path to shellcode .bin (relative to repo or absolute). "
                             "Required unless --dry-run or --summarize is used.")
    parser.add_argument("--vm", default="Defender",
                        help="VM name from controller/config.py (default: 'Windows Defender')")
    parser.add_argument("--phases", default="A,B,C,D,E",
                        help="Comma-separated phase keys (A/B/C/D/E). Default: all.")
    parser.add_argument("--resume", metavar="DIR_OR_CSV",
                        help="Existing batch folder (or its matrix.csv) to resume.")
    parser.add_argument("--fix-run", metavar="DIR_OR_CSV",
                        help="Rerun only ERROR/EXCEPTION cases from an existing batch.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the test plan and exit without running.")
    parser.add_argument("--summarize", metavar="DIR_OR_CSV",
                        help="Print summary of an existing batch folder or matrix.csv "
                             "and exit (no new runs).")
    parser.add_argument("--reclassify", metavar="DIR_OR_CSV",
                        help="Re-parse each run's log_body and rewrite matrix.csv with "
                             "the current classifier (5-way: CB/LD/EB/BLOCKED/TB/ERROR). "
                             "Saves a .bak of the original CSV. Exits without new runs.")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase log verbosity: -v for INFO, -vv for DEBUG. "
                             "Default is WARNING only.")
    args = parser.parse_args()

    configure_logging(args.verbose)

    # --summarize: re-analyze existing batch folder or csv and exit
    if args.summarize:
        _, csv_path = resolve_batch_dir(args.summarize)
        if csv_path:
            summarize_csv(csv_path)
        else:
            print(f"[!] Cannot resolve: {args.summarize}")
        return

    # --reclassify: rebuild matrix.csv from logs and exit
    if args.reclassify:
        reclassify_batch(args.reclassify)
        return

    phase_keys = [p.strip().upper() for p in args.phases.split(",") if p.strip()]
    for k in phase_keys:
        if k not in PHASES:
            print(f"[!] Unknown phase '{k}'. Valid: {list(PHASES.keys())}")
            sys.exit(1)

    if args.dry_run:
        runs = build_plan(phase_keys)
        total = 0
        for cfg_id, cfg, reps in runs:
            for rep in range(1, reps + 1):
                total += 1
                print(f"{cfg_id:<4} rep={rep}  {short_name(cfg)}")
        print(f"\nTotal: {total} runs")
        return

    # From here on, we actually execute runs — require shellcode + valid VM.
    if not args.shellcode:
        parser.error("--shellcode is required unless --dry-run or --summarize is given.")
    if args.vm not in VMS_CONFIG:
        print(f"[!] VM '{args.vm}' not in controller/config.py")
        print(f"    Available: {list(VMS_CONFIG.keys())}")
        sys.exit(1)

    if args.fix_run:
        if not args.shellcode:
            parser.error("--shellcode is required for --fix-run")

        shellcode = args.shellcode
        if not os.path.isabs(shellcode):
            shellcode = os.path.join(PROJECT_ROOT, shellcode)

        fix_and_update_csv(shellcode, args.vm, args.fix_run)
        return

    shellcode = args.shellcode
    if not os.path.isabs(shellcode):
        shellcode = os.path.join(PROJECT_ROOT, shellcode)
    if not os.path.isfile(shellcode):
        alt_shellcode = None
        base = os.path.basename(shellcode)
        parent = os.path.dirname(shellcode)

        # Repo historically used "defaul_..." in the filename.
        if base.startswith("default_"):
            candidate = os.path.join(parent, base.replace("default_", "defaul_", 1))
            if os.path.isfile(candidate):
                alt_shellcode = candidate

        if alt_shellcode:
            print(f"[i] Shellcode not found at requested path, using: {alt_shellcode}")
            shellcode = alt_shellcode
        else:
            print(f"[!] Shellcode not found: {shellcode}")
            sys.exit(1)

    run_all(shellcode, args.vm, phase_keys, resume_arg=args.resume)


if __name__ == "__main__":
    main()
