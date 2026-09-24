#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


RAW_EXPECTED_SHAPE = (25000, 31)
AUG_EXPECTED_SHAPE = (22465, 23)

RAW_COLUMNS: List[str] = [
    "MsgId","CmdCode","TimeRadians","SequenceCount","MsgLength","HasSecondaryHeader",
    "MsgType","ApId","HeaderVersion","SegmentationFlag","FlowLengthInWindow",
    "SlidingWindowMeanIntervalSec","SlidingWindowMaxIntervalSec","SlidingWindowMinIntervalSec",
    "MessageCountInWindow","UniqueMessageIDsInWindow","AverageMessageLengthInWindow",
    "MessageRateInWindow","StdDevMessageLengthInWindow","CommandErrorCounter","IngestErrors",
    "MemoryAnonMB","MemoryFileMB","MemoryKernelstackMB","MemoryPageTableMB","MemorySocketMB",
    "MemoryPercpuMB","MemoryShmemMB","MemorySlabUnreclaimableMB","MemoryPageFaults","Label"
]

AUG_COLUMNS: List[str] = [
    "MsgId","CmdCode","TimeRadians","MsgLength","ApId","FlowLengthInWindow",
    "SlidingWindowMeanIntervalSec","SlidingWindowMaxIntervalSec","SlidingWindowMinIntervalSec",
    "MessageCountInWindow","UniqueMessageIDsInWindow","AverageMessageLengthInWindow",
    "MessageRateInWindow","StdDevMessageLengthInWindow","MemoryAnonMB","MemoryFileMB",
    "MemoryKernelstackMB","MemoryPageTableMB","MemorySocketMB","MemoryPercpuMB","MemoryShmemMB",
    "MemorySlabUnreclaimableMB","Label"
]

RAW_INT_COLS = {
    "MsgId","CmdCode","SequenceCount","MsgLength","HasSecondaryHeader","MsgType","ApId",
    "HeaderVersion","SegmentationFlag","MessageCountInWindow","UniqueMessageIDsInWindow",
    "AverageMessageLengthInWindow","CommandErrorCounter","IngestErrors","MemoryPageFaults","Label"
}
RAW_FLOAT_COLS = {
    "TimeRadians","FlowLengthInWindow","SlidingWindowMeanIntervalSec","SlidingWindowMaxIntervalSec",
    "SlidingWindowMinIntervalSec","MessageRateInWindow","StdDevMessageLengthInWindow",
    "MemoryAnonMB","MemoryFileMB","MemoryKernelstackMB","MemoryPageTableMB","MemorySocketMB",
    "MemoryPercpuMB","MemoryShmemMB","MemorySlabUnreclaimableMB"
}

AUG_INTLIKE_COLS = {
    "MsgId","CmdCode","MsgLength","ApId","MessageCountInWindow","UniqueMessageIDsInWindow","Label"
}


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)

def ok(msg: str) -> None:
    print(f"[OK] {msg}")

def warn(msg: str) -> None:
    print(f"[WARN] {msg}")

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()

def parse_checksums(checksums_path: str) -> Dict[str, str]:
    """
    Accepts lines like:
      <sha256>  <path>
    """
    mapping: Dict[str, str] = {}
    with open(checksums_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            digest = parts[0].strip().lower()
            relpath = " ".join(parts[1:]).strip()
            mapping[os.path.normpath(relpath)] = digest
    return mapping

def enforce_shape(df: pd.DataFrame, expected_shape: Tuple[int, int]) -> None:
    if df.shape != expected_shape:
        fail(f"Shape mismatch. Expected {expected_shape}, got {df.shape}")
    ok(f"Shape validated: {df.shape}")

def enforce_columns(df: pd.DataFrame, expected: List[str], strict_order: bool) -> None:
    got = list(df.columns)
    if strict_order:
        if got != expected:
            fail("Column order or names do not match expected schema.")
    else:
        if set(got) != set(expected):
            extra = sorted(set(got) - set(expected))
            missing = sorted(set(expected) - set(got))
            fail(f"Column set mismatch. Extra: {extra} Missing: {missing}")
    ok("Schema columns validated.")

def enforce_no_missing(df: pd.DataFrame) -> None:
    if df.isna().any().any():
        miss = df.isna().sum()
        miss = miss[miss > 0].sort_values(ascending=False)
        fail("Missing values detected:\n" + miss.to_string())
    ok("No missing values.")

def enforce_all_numeric(df: pd.DataFrame) -> None:
    non_numeric = [(c, str(df[c].dtype)) for c in df.columns if not pd.api.types.is_numeric_dtype(df[c].dtype)]
    if non_numeric:
        fail(f"Non-numeric columns detected: {non_numeric}")
    ok("All columns are numeric.")

def enforce_raw_dtypes(df: pd.DataFrame) -> None:
    bad = []
    for c in sorted(RAW_INT_COLS):
        if c in df.columns and not pd.api.types.is_integer_dtype(df[c].dtype):
            bad.append((c, f"expected int, got {df[c].dtype}"))
    for c in sorted(RAW_FLOAT_COLS):
        if c in df.columns and not pd.api.types.is_float_dtype(df[c].dtype):
            bad.append((c, f"expected float, got {df[c].dtype}"))
    if bad:
        fail("Raw dtype check failed:\n" + "\n".join([f"  - {c}: {msg}" for c, msg in bad]))
    ok("Raw dtypes validated (int vs float).")

def enforce_intlike(df: pd.DataFrame, cols: set) -> None:
    bad = []
    for c in sorted(cols):
        if c not in df.columns:
            continue
        s = df[c].to_numpy()
        if not np.all(np.isfinite(s)):
            bad.append((c, "non-finite values"))
            continue
        if not np.all(np.isclose(s, np.round(s))):
            bad.append((c, "non-integer-like values"))
    if bad:
        fail("Integer-like check failed:\n" + "\n".join([f"  - {c}: {msg}" for c, msg in bad]))
    ok("Integer-like columns validated.")

def validate_labels(df: pd.DataFrame, schema_path: str) -> None:
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    if "mapping" not in schema:
        fail("label_schema.json missing 'mapping'.")
    expected_labels = sorted(int(k) for k in schema["mapping"].keys())

    if "Label" not in df.columns:
        fail("No 'Label' column present.")
    labels = sorted(set(int(x) for x in np.unique(df["Label"].to_numpy())))
    if labels != expected_labels:
        fail(f"Label values mismatch. Expected {expected_labels}, got {labels}")
    ok("Label schema validated.")

def verify_checksums(checksums_path: str, raw_path: str, aug_path: str) -> None:
    expected = parse_checksums(checksums_path)

    def lookup_expected(path: str) -> str | None:
        keys = [
            os.path.normpath(path),
            os.path.normpath(os.path.relpath(path)),
            os.path.normpath(os.path.basename(path)),
        ]
        for k in keys:
            if k in expected:
                return expected[k]
        return None

    for path in [raw_path, aug_path]:
        exp = lookup_expected(path)
        if exp is None:
            warn(f"No checksum entry found for {path}. Skipping hash check.")
            continue
        got = sha256_file(path)
        if got != exp:
            fail(f"Checksum mismatch for {path}. Expected {exp}, got {got}")
        ok(f"Checksum verified for {os.path.basename(path)}.")

def main() -> None:
    p = argparse.ArgumentParser(description="Validate CubeSat IDS raw and augmented datasets.")
    p.add_argument("--raw", required=True, help="Path to Data/Raw/consolidated_dataset_raw.csv")
    p.add_argument("--augmented", required=True, help="Path to Data/Augmented/noised_dataset.csv")
    p.add_argument("--label-schema", required=True, help="Path to Data/Metadata/label_schema.json")
    p.add_argument("--checksums", default=None, help="Optional path to Data/Metadata/checksums.txt for SHA-256 verification")
    p.add_argument("--strict-order", action="store_true", help="Require exact column order in addition to names")
    args = p.parse_args()

    if args.checksums:
        verify_checksums(args.checksums, args.raw, args.augmented)

    raw_df = pd.read_csv(args.raw, low_memory=False)
    aug_df = pd.read_csv(args.augmented, low_memory=False)

    print("\nValidating RAW dataset")
    enforce_shape(raw_df, RAW_EXPECTED_SHAPE)
    enforce_columns(raw_df, RAW_COLUMNS, strict_order=args.strict_order)
    enforce_no_missing(raw_df)
    enforce_all_numeric(raw_df)
    enforce_raw_dtypes(raw_df)
    validate_labels(raw_df, args.label_schema)

    print("\nValidating AUGMENTED dataset")
    enforce_shape(aug_df, AUG_EXPECTED_SHAPE)
    enforce_columns(aug_df, AUG_COLUMNS, strict_order=args.strict_order)
    enforce_no_missing(aug_df)
    enforce_all_numeric(aug_df)
    enforce_intlike(aug_df, AUG_INTLIKE_COLS)
    validate_labels(aug_df, args.label_schema)

    ok("\nAll validations passed.")

if __name__ == "__main__":
    main()
