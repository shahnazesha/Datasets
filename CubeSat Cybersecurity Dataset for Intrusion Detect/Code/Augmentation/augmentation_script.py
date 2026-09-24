#!/usr/bin/env python3
"""
CubeSat IDS Dataset Augmentation Script
=======================================
Deterministically regenerates the augmented/noised dataset from raw CSV files.

Usage:
    python augmentation_script.py --input <raw_consolidated.csv> --output <augmented.csv>

Or use default paths:
    python augmentation_script.py

The script applies realistic telemetry noise patterns to simulate:
    1. White Noise: Gaussian jitter on analog features
    2. Analog Outliers: Spike/drop scaling on continuous features
    3. Gaps: Packet loss simulation via Δt metric inflation
    4. Trends: Memory gauge drift (simulates memory leaks)
    5. Signal Shifts: Clock glitch step offsets on Δt features
    6. Frequency Changes: Multiplicative time warp on Δt features
    7. Sensor Dropout: Zero-out memory gauges for random rows
    8. Magnitude Warping: Spline-based gain drift
    9. Window Time Warp: Contiguous block time warp

Fixed random seed (SEED=7) ensures deterministic reproducibility.

"""

import argparse
import numpy as np
import pandas as pd
import random
import scipy.interpolate

# =============================================================================
# FIXED RANDOM SEED FOR REPRODUCIBILITY
# =============================================================================
SEED = 7

# =============================================================================
# VALID LABEL VALUES
# =============================================================================
VALID_LABELS = {0, 1, 2, 3, 4}

# =============================================================================
# INVARIANT FEATURES REMOVED (zero-variance / header-constant)
# =============================================================================
INVARIANT_FEATURES = [
    'HeaderVersion',
    'MsgType',
    'HasSecondaryHeader',
    'SegmentationFlag',
    'SequenceCount',
    'CommandErrorCounter',
    'IngestErrors',
    'MemoryPageFaults',
]

# =============================================================================
# NOISE PARAMETERS 
# =============================================================================
NOISE_PARAMS = {
    'seed': SEED,
    'white_noise_pct': 0.24,
    'white_noise_scale': 0.042,
    'analog_outlier_pct': 0.38,
    'gap_pct': 0.33,
    'trend_drift': 0.17,
    'sd_row_pct': 0.04,
    'mw_rows_pct': 0.10,
    'mw_sigma': 0.58,
    'mw_knots': 6,
    'tw_row_pct': 0.09,
    'tw_sigma': 0.42,
    'tw_knots': 5,
    'gap_window_duration': 20.0,
    'gap_time_range': (0.7, 1.5),
    'gap_decay': 0.42,
    'gap_segments': 5,
    'trend_shift_range': (0.12, 0.88),
}

# =============================================================================
# FEATURE DEFINITIONS
# =============================================================================
ANALOG_FEATURES = [
    'FlowLengthInWindow', 'SlidingWindowMeanIntervalSec',
    'SlidingWindowMaxIntervalSec', 'SlidingWindowMinIntervalSec',
    'AverageMessageLengthInWindow', 'StdDevMessageLengthInWindow',
    'MessageRateInWindow', 'MemoryAnonMB', 'MemoryFileMB',
    'MemoryKernelstackMB', 'MemoryPageTableMB', 'MemorySocketMB',
    'MemoryPercpuMB', 'MemoryShmemMB', 'MemorySlabUnreclaimableMB'
]

MEMORY_COLUMNS = [
    'MemoryAnonMB', 'MemoryFileMB', 'MemoryKernelstackMB', 'MemoryPageTableMB',
    'MemorySocketMB', 'MemoryPercpuMB', 'MemoryShmemMB',
    'MemorySlabUnreclaimableMB'
]

DELTA_T_FEATURES = [
    'SlidingWindowMeanIntervalSec',
    'SlidingWindowMaxIntervalSec',
    'SlidingWindowMinIntervalSec'
]

WARP_TARGETS = [
    'FlowLengthInWindow', 'SlidingWindowMeanIntervalSec',
    'SlidingWindowMaxIntervalSec', 'SlidingWindowMinIntervalSec',
    'MessageRateInWindow'
]

MW_FEATURES = [
    'MemoryAnonMB', 'MemoryFileMB', 'MemoryKernelstackMB', 'MemoryPageTableMB',
    'MemorySocketMB', 'MemoryPercpuMB', 'MemoryShmemMB',
    'MemorySlabUnreclaimableMB',
    'FlowLengthInWindow', 'SlidingWindowMeanIntervalSec',
    'SlidingWindowMaxIntervalSec', 'SlidingWindowMinIntervalSec',
    'MessageRateInWindow', 'StdDevMessageLengthInWindow'
]


def _validate_labels(df):
    """Validate that Label column contains only valid integer labels {0,1,2,3,4}."""
    if 'Label' not in df.columns:
        raise ValueError("Input CSV must contain a 'Label' column.")

    # Convert to int (handles float like 0.0 -> 0)
    if pd.api.types.is_float_dtype(df['Label']):
        if not all(float(v).is_integer() for v in df['Label'].dropna()):
            raise ValueError("Label column contains non-integer float values.")
        df['Label'] = df['Label'].astype(int)
    elif not pd.api.types.is_integer_dtype(df['Label']):
        raise ValueError(
            f"Label column must contain integers. Found dtype: {df['Label'].dtype}"
        )

    # Validate values are in valid set
    labels_unique = set(df['Label'].unique())
    invalid = labels_unique - VALID_LABELS
    if invalid:
        raise ValueError(
            f"Label column contains invalid values: {sorted(invalid)}. "
            f"Expected only: {sorted(VALID_LABELS)}"
        )

    print(f"Labels validated: {sorted(labels_unique)}")
    return df


def _drop_invariant_features(df):
    drop_cols = [c for c in INVARIANT_FEATURES if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)
        print(f"Dropped invariant features: {drop_cols}")
    return df


def inject_noise(
    df,
    seed=SEED,
    white_noise_pct=0.24,
    white_noise_scale=0.042,
    analog_outlier_pct=0.38,
    gap_pct=0.33,
    trend_drift=0.17,
    sd_row_pct=0.04,
    mw_rows_pct=0.10,
    mw_sigma=0.58,
    mw_knots=6,
    tw_row_pct=0.09,
    tw_sigma=0.42,
    tw_knots=5,
    gap_window_duration=20.0,
    gap_time_range=(0.7, 1.5),
    gap_decay=0.42,
    gap_segments=5,
    trend_shift_range=(0.12, 0.88),
):
    """
    Inject realistic noise types into DataFrame for telemetry augmentation.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with telemetry features and 'Label' column.
    seed : int
        Random seed for reproducibility (default: 7).
    white_noise_pct : float
        Fraction of rows to add Gaussian noise (0-1).
    white_noise_scale : float
        Scale factor for noise relative to feature std.
    analog_outlier_pct : float
        Fraction of rows to apply outlier scaling.
    gap_pct : float
        Fraction of rows for gap injection/dropping.
    trend_drift : float
        Total drift magnitude (MB) for memory trends.
    sd_row_pct : float
        Fraction of rows for sensor dropout.
    mw_rows_pct : float
        Fraction of rows for magnitude warping.
    mw_sigma : float
        Sigma for magnitude warp spline knots.
    mw_knots : int
        Number of knots for magnitude warp spline.
    tw_row_pct : float
        Fraction of rows for time warping.
    tw_sigma : float
        Sigma for time warp spline knots.
    tw_knots : int
        Number of knots for time warp spline.
    gap_window_duration : float
        Sliding window duration in seconds.
    gap_time_range : tuple
        (min, max) fraction of window for gap time.
    gap_decay : float
        Exponential decay factor for class-imbalanced gaps.
    gap_segments : int
        Number of gap segments per class.
    trend_shift_range : tuple
        (min, max) fraction for trend change point.

    Returns
    -------
    pd.DataFrame
        Augmented DataFrame with injected noise.
    """
    # Set random seeds for reproducibility
    np.random.seed(seed)
    random.seed(seed)

    orig_df = df.copy()
    df_noised = df.copy()
    n_original = len(df_noised)
    n = n_original

    # Cast integer columns to float for noise addition (except Label)
    for c in df_noised.select_dtypes(include=['int64', 'int32']).columns:
        if c != 'Label':
            df_noised[c] = df_noised[c].astype(float)
    idx = df_noised.index.to_numpy()

    # =========================================================================
    # 1. WHITE NOISE (Gaussian jitter on analog features)
    # =========================================================================
    wn_pct = min(white_noise_pct, 1.0)
    n_wn = int(n * wn_pct)
    if n_wn > 0:
        wn_idx = np.random.choice(idx, size=n_wn, replace=False if n >= n_wn else True)
        print(f"[White-Noise] Adding Gaussian noise to {n_wn} rows "
              f"(pct={wn_pct:.2f}, scale={white_noise_scale:.3f})")
        for c in ANALOG_FEATURES:
            if c in df_noised.columns:
                sigma = orig_df[c].std() * white_noise_scale
                df_noised.loc[wn_idx, c] += np.random.normal(0, sigma, size=n_wn)

    # =========================================================================
    # 2. ANALOG OUTLIERS (two-pass spike/drop scaling)
    # =========================================================================
    ao_pct = min(analog_outlier_pct, 1.0)
    n_total_ao = int(n * ao_pct)
    if n_total_ao > 0:
        combined_idx = np.random.choice(idx, size=n_total_ao, replace=False)
        n_ao1 = n_total_ao // 2
        n_ao2 = n_total_ao - n_ao1
        ao_idx1 = combined_idx[:n_ao1]
        ao_idx2 = combined_idx[n_ao1:]

        rng1 = (5.0, 10.0)  # Large spike/dip
        rng2 = (3.0, 6.0)   # Moderate spike/dip
        factors1 = np.random.uniform(rng1[0], rng1[1], size=n_ao1)
        factors2 = np.random.uniform(rng2[0], rng2[1], size=n_ao2)

        print(f"[Analog Outliers] Pass 1: scaling {n_ao1} rows by factors in {rng1}, "
              f"Pass 2: scaling {n_ao2} rows by factors in {rng2}")
        for c in ANALOG_FEATURES:
            if c in df_noised.columns:
                df_noised.loc[ao_idx1, c] *= factors1
                df_noised.loc[ao_idx2, c] *= factors2

    # =========================================================================
    # 3. GAPS (Δt spike injection for packet loss simulation)
    # =========================================================================
    n_gap = int(n * gap_pct)
    if n_gap > 0:
        gap_idx = np.random.choice(df_noised.index, size=n_gap, replace=False)
        print(f"[Gaps] Injecting gap-effects on {n_gap} rows ({gap_pct*100:.0f}%)")

        for i in gap_idx:
            if all(c in df_noised.columns for c in [
                'SlidingWindowMeanIntervalSec', 'SlidingWindowMaxIntervalSec',
                'SlidingWindowMinIntervalSec', 'MessageCountInWindow', 'MessageRateInWindow'
            ]):
                orig_mean = df_noised.at[i, 'SlidingWindowMeanIntervalSec']
                orig_max = df_noised.at[i, 'SlidingWindowMaxIntervalSec']
                count = df_noised.at[i, 'MessageCountInWindow']

                gap_time = np.random.uniform(
                    gap_time_range[0] * gap_window_duration,
                    gap_time_range[1] * gap_window_duration
                )

                if count > 1:
                    total_time_without_gap = orig_mean * (count - 1)
                    new_total_time = total_time_without_gap + gap_time
                    new_mean = new_total_time / (count - 1)
                else:
                    new_mean = gap_time

                new_max = orig_max + gap_time

                df_noised.at[i, 'SlidingWindowMeanIntervalSec'] = new_mean
                df_noised.at[i, 'SlidingWindowMaxIntervalSec'] = new_max
                df_noised.at[i, 'MessageRateInWindow'] = (
                    count / gap_window_duration if gap_window_duration > 0 else 0.0
                )

    # Gap dropping (label-aware consecutive drops with exponential decay)
    print(f"[Gaps] Dropping up to {gap_pct*100:.1f}% per class (exp-decay, consecutive)")
    rng = np.random.default_rng(seed)
    drop_idxs = []

    labels = sorted(df_noised['Label'].unique())
    for i, lbl in enumerate(labels):
        cls_idx = df_noised[df_noised['Label'] == lbl].index.to_numpy()
        rate = gap_pct * (gap_decay ** i)
        n_drop = int(len(cls_idx) * rate)

        seg_len, extra = divmod(n_drop, gap_segments)
        for s in range(gap_segments):
            length = seg_len + (1 if s < extra else 0)
            if length == 0:
                continue
            if len(cls_idx) <= length:
                continue
            start = rng.choice(cls_idx[:-length])
            end = start + length
            drop_idxs.extend(cls_idx[(cls_idx >= start) & (cls_idx < end)])

    df_noised = df_noised.drop(drop_idxs).reset_index(drop=True)
    idx = df_noised.index.to_numpy()
    n = len(df_noised)
    print(f"DataFrame shape after creating gaps: {df_noised.shape}")

    # =========================================================================
    # 4. TRENDS (per-class memory gauge drift)
    # =========================================================================
    drift_prob_per_class = 0.85
    if 'Label' in df_noised.columns and len(df_noised) > 0:
        for lbl, group in df_noised.groupby('Label'):
            class_indices = group.index.to_list()
            class_n = len(class_indices)
            if class_n < 2:
                continue

            if random.random() > drift_prob_per_class:
                print(f"[Trends] Skipping drift for class '{lbl}'")
                continue

            shift_pt_frac = np.random.uniform(trend_shift_range[0], trend_shift_range[1])
            shift_pos = int(class_n * shift_pt_frac)
            shift_pos = max(1, min(class_n - 1, shift_pos))
            drift_length = class_n - shift_pos
            if drift_length <= 0:
                continue

            mean_step = trend_drift / drift_length
            std_step = abs(mean_step)
            steps = np.random.normal(loc=mean_step, scale=std_step, size=drift_length)
            drift_vec = np.cumsum(steps)

            drift_indices = class_indices[shift_pos:]
            print(f"[Trends] Class '{lbl}': drifting {drift_length} rows "
                  f"from pos {shift_pos} (frac={shift_pt_frac:.2f}), total drift≈{trend_drift:.2f} MB")
            for j, df_idx in enumerate(drift_indices):
                for c in MEMORY_COLUMNS:
                    if c in df_noised.columns:
                        df_noised.at[df_idx, c] += drift_vec[j]

    # =========================================================================
    # 5. SIGNAL SHIFTS (per-class Δt step offset)
    # =========================================================================
    drift_prob_per_class = 0.8
    for lbl, group in df_noised.groupby('Label'):
        class_indices = group.index.to_list()
        class_n = len(class_indices)
        if class_n < 2:
            continue

        if random.random() > drift_prob_per_class:
            print(f"[Signal-Shifts] No shift for class '{lbl}'.")
            continue

        shift_pt_frac = np.random.uniform(0.2, 0.8)
        shift_pos = int(class_n * shift_pt_frac)
        shift_pos = max(1, min(class_n - 1, shift_pos))
        drift_start_index = class_indices[shift_pos]

        sv = random.choice([random.uniform(5.0, 8.0), random.uniform(-8.0, -5.0)])
        print(f"[Signal-Shifts] Class '{lbl}': glitch at pos {shift_pos} "
              f"(global idx {drift_start_index}), sv={sv:.2f} s")

        for c in DELTA_T_FEATURES:
            if c in df_noised.columns:
                df_noised.loc[df_noised.index >= drift_start_index, c] += sv

    # =========================================================================
    # 6. FREQUENCY CHANGES (per-class Δt multiplicative warp)
    # =========================================================================
    freq_change_prob_per_class = 0.7
    for lbl, group in df_noised.groupby('Label'):
        class_indices = group.index.to_list()
        class_n = len(class_indices)
        if class_n < 5:
            continue

        if random.random() > freq_change_prob_per_class:
            print(f"[Frequency Changes] No skew for class '{lbl}'.")
            continue

        freq_change_pct = 0.10
        seg_len = max(1, int(class_n * freq_change_pct))
        start_offset = np.random.randint(0, class_n - seg_len + 1)
        end_offset = start_offset + seg_len - 1
        start_idx = class_indices[start_offset]
        end_idx = class_indices[end_offset]

        if random.random() < 0.5:
            f = np.random.uniform(0.85, 0.95)
        else:
            f = np.random.uniform(1.05, 1.15)

        print(f"[Frequency Changes] Class '{lbl}': skew f={f:.2f} "
              f"for rows {start_offset}..{start_offset+seg_len-1} "
              f"(global idx {start_idx}..{end_idx})")

        for c in DELTA_T_FEATURES:
            if c in df_noised.columns:
                mask = (df_noised.index >= start_idx) & (df_noised.index <= end_idx)
                df_noised.loc[mask, c] *= f

    # =========================================================================
    # 7. SENSOR DROPOUT (zero out memory gauges for random rows)
    # =========================================================================
    mem_gauge_cols = [c for c in MEMORY_COLUMNS if c in df_noised.columns]
    if mem_gauge_cols and len(df_noised) > 0:
        n_rows = len(df_noised)
        n_rows_sd = int(n_rows * sd_row_pct)
        dropout_rows = np.random.choice(df_noised.index, size=n_rows_sd, replace=False)
        df_noised.loc[dropout_rows, mem_gauge_cols] = 0.0
        print(f"[Sensor Dropout] Zeroed memory gauges on {n_rows_sd} rows")

    # =========================================================================
    # 8. MAGNITUDE WARPING (smooth spline-based gain drift)
    # =========================================================================
    cur_idx = df_noised.index.to_numpy()
    n_cur = len(cur_idx)
    if n_cur > 0:
        print(f"[Magnitude Warping] Targeting ≈{mw_rows_pct*100:.0f}% of rows "
              f"(σ={mw_sigma}, knots={mw_knots})")
        mw_cols = [c for c in MW_FEATURES if c in df_noised.columns]
        for col in mw_cols:
            target_rows = int(n_cur * mw_rows_pct)
            warped = 0
            while warped < target_rows:
                seg_min = mw_knots
                seg_len = np.random.randint(seg_min, max(seg_min + 1, int(n_cur * 0.2)))
                if seg_len < seg_min:
                    break
                start = np.random.randint(0, n_cur - seg_len + 1)
                seg = cur_idx[start:start + seg_len]
                seg = [i for i in seg if i in orig_df.index]
                if len(seg) < seg_min:
                    continue
                baseline = (
                    orig_df.loc[seg, col]
                    .interpolate('linear', limit_direction='both')
                    .fillna(0)
                    .to_numpy()
                )
                x_knots = np.linspace(0, 1, mw_knots)
                y_knots = np.abs(np.random.normal(1.0, mw_sigma, mw_knots)) + 1e-3
                if mw_knots >= 4:
                    spline = scipy.interpolate.CubicSpline(x_knots, y_knots, extrapolate=True)
                else:
                    spline = scipy.interpolate.interp1d(
                        x_knots, y_knots, kind='linear', fill_value='extrapolate'
                    )
                scale = spline(np.linspace(0, 1, len(seg)))
                warped_vals = baseline * scale
                if col == 'StdDevMessageLengthInWindow':
                    warped_vals = np.abs(warped_vals)
                df_noised.loc[seg, col] = np.clip(warped_vals, 0, None)
                warped += len(seg)

    # =========================================================================
    # 9. WINDOW TIME WARP (single contiguous block time warp)
    # =========================================================================
    cur_idx = df_noised.index.to_numpy()
    n_cur = len(cur_idx)
    warp_cols = [c for c in WARP_TARGETS if c in df_noised.columns]
    if warp_cols and n_cur > 0:
        n_tw = max(tw_knots, int(n_cur * tw_row_pct))
        start = np.random.randint(0, n_cur - n_tw + 1)
        seg = cur_idx[start:start + n_tw]
        xk = np.linspace(0, 1, tw_knots)
        yk = np.abs(np.random.normal(1.0, tw_sigma, tw_knots)) + 1e-3
        f_t = scipy.interpolate.CubicSpline(xk, yk, extrapolate=True)(np.linspace(0, 1, n_tw))
        for col in warp_cols:
            if col == 'MessageRateInWindow':
                df_noised.loc[seg, col] = df_noised.loc[seg, col] / f_t
            else:
                df_noised.loc[seg, col] = df_noised.loc[seg, col] * f_t
        print(f"[Window Time Warp] Warped Δt features on rows {start}:{start+n_tw-1} "
              f"(σ={tw_sigma}, knots={tw_knots})")

    # =========================================================================
    # Final summary
    # =========================================================================
    if 'Label' in df_noised.columns:
        df_noised['Label'] = df_noised['Label'].astype(int)

    final_n = len(df_noised)
    if final_n != n_original:
        print(f"Row count changed from {n_original} to {final_n}.")
    else:
        print(f"[Done] No rows dropped. Final row count = {final_n} (same as original).")

    return df_noised


def load_raw_data(input_path):
    """
    Load consolidated raw CSV data.

    Parameters
    ----------
    input_path : str
        Path to consolidated CSV file with 'Label' column (string or integer).

    Returns
    -------
    pd.DataFrame
        DataFrame with integer-encoded labels and invariant fields removed.
    """
    print(f"Loading data from: {input_path}")
    df = pd.read_csv(input_path, header=0)

    # Validate labels are integers in {0,1,2,3,4}
    df = _validate_labels(df)

    # Remove invariant columns (zero-variance / header-constant)
    df = _drop_invariant_features(df)

    print(f"Loaded {len(df)} rows with {df['Label'].nunique()} classes")
    return df


def main():
    parser = argparse.ArgumentParser(
        description="CubeSat IDS Dataset Augmentation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='Data/Raw/consolidated_dataset_raw.csv',
        help='Path to input raw CSV file (default: Data/Raw/consolidated_dataset_raw.csv)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='Data/Augmented/noised_dataset.csv',
        help='Path to output augmented CSV file (default: Data/Augmented/noised_dataset.csv)'
    )
    parser.add_argument(
        '--seed', '-s',
        type=int,
        default=SEED,
        help=f'Random seed for reproducibility (default: {SEED})'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("CubeSat IDS Dataset Augmentation")
    print("=" * 70)
    print(f"Random Seed: {args.seed}")
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print("=" * 70)

    # Load raw data
    df = load_raw_data(args.input)

    # Apply noise injection with fixed parameters
    params = NOISE_PARAMS.copy()
    params['seed'] = args.seed
    params['df'] = df

    print("\nApplying noise injection...")
    print("-" * 70)
    df_noised = inject_noise(**params)

    # Save augmented dataset
    print("-" * 70)
    df_noised.to_csv(args.output, index=False)
    print(f"\nSaved augmented dataset to: {args.output}")
    print(f"Final shape: {df_noised.shape}")

    # Print class distribution
    print("\nClass distribution after augmentation:")
    for lbl in sorted(df_noised['Label'].unique()):
        count = (df_noised['Label'] == lbl).sum()
        pct = count / len(df_noised) * 100
        print(f"  Class {lbl}: {count:>5} ({pct:.1f}%)")

    print("\nDone!")
    return df_noised


if __name__ == "__main__":
    main()
