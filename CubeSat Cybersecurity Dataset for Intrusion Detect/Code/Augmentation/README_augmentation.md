# CubeSat IDS Dataset Augmentation Script

Deterministically regenerates the augmented/noised dataset from the raw CubeSat telemetry CSV.

## Requirements

```
numpy
pandas
scipy
scikit-learn
```

Install with:
```bash
pip install numpy pandas scipy scikit-learn
```

## Usage

### Basic Usage (Default Paths)
```bash
python augmentation_script.py
```

### Custom Input/Output
```bash
python augmentation_script.py --input path/to/raw_data.csv --output path/to/augmented.csv
```

### Command Line Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--input` | `-i` | `Data/Raw/consolidated_dataset_raw.csv` | Path to input raw CSV file |
| `--output` | `-o` | `Data/Augmented/noised_dataset.csv` | Path to output augmented CSV |
| `--seed` | `-s` | `7` | Random seed for reproducibility |

## Input Format

The input CSV must contain:
- Telemetry feature columns
- A `Label` column (string class names or integer-encoded)

## Raw-to-Augmented Schema

To match the dataset schema described in the manuscript, the script drops the following invariant (zero variance) columns from the raw CSV before applying augmentation:

- `HeaderVersion`
- `MsgType`
- `HasSecondaryHeader`
- `SegmentationFlag`
- `SequenceCount`
- `CommandErrorCounter`
- `IngestErrors`
- `MemoryPageFaults`

## Reproducibility

**Fixed random seed (SEED=7)** ensures deterministic output. Running the script with the same input and seed will always produce identical results.

## Noise Injection Pipeline

The script applies 9 realistic telemetry noise patterns in sequence:

| # | Noise Type | Description |
|---|------------|-------------|
| 1 | **White Noise** | Gaussian jitter on analog features |
| 2 | **Analog Outliers** | Two-pass spike/drop scaling |
| 3 | **Gaps** | Packet loss simulation via delta-t (Δt) inflation + row dropping |
| 4 | **Trends** | Memory gauge drift (simulates memory leaks) |
| 5 | **Signal Shifts** | Clock glitch step offsets |
| 6 | **Frequency Changes** | Multiplicative delta-t (Δt) warp |
| 7 | **Sensor Dropout** | Zero-out memory gauges |
| 8 | **Magnitude Warping** | Spline-based gain drift |
| 9 | **Window Time Warp** | Contiguous block time warp |

## Configuration Parameters

All parameters are hardcoded for reproducibility:

```python
NOISE_PARAMS = {
    'seed': 7,
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
```
