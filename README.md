# CubeSat IDS Telemetry (NOS3/cFS): Raw + Noised Labelled Events 

## What's here
- Raw consolidated telemetry: 25,000 rows, 31 columns ("/Data/Raw/consolidated_dataset_raw.csv") 
- Noised/augmented telemetry for robustness studies: 22,465 rows, 23 columns ("/Data/Augmented/noised_dataset.csv") 
- COSMOS/NOS3 scripts to reproduce each scenario ("/Code/Scripts/") 

## Provenance
Generated in NASA NOS3 with cFS + COSMOS. Five scenarios, 5,000 events each:
- Normal operations
- Command flooding
- Data (GPS) injection
- Storage exhaustion
- Defence impairment (LC/CS manipulation)

## Label mapping
0=command_flooding, 1=data_injection, 2=defence_impairment, 3=normal, 4=storage_exhaustion

## Columns (raw)
MsgId, CmdCode, TimeRadians, SequenceCount, MsgLength, HasSecondaryHeader, MsgType, ApId, HeaderVersion, SegmentationFlag,
FlowLengthInWindow, SlidingWindowMeanIntervalSec, SlidingWindowMaxIntervalSec, SlidingWindowMinIntervalSec, MessageCountInWindow,
UniqueMessageIDsInWindow, AverageMessageLengthInWindow, MessageRateInWindow, StdDevMessageLengthInWindow,
CommandErrorCounter, IngestErrors, MemoryAnonMB, MemoryFileMB, MemoryKernelstackMB, MemoryPageTableMB, MemorySocketMB,
MemoryPercpuMB, MemoryShmemMB, MemorySlabUnreclaimableMB, MemoryPageFaults, Label

## Columns (noised)
Subset of features above (23 columns) + Label; zero-variance and header-constant fields removed.

## CSV snippets

Raw (subset of columns; first 5 rows):
```csv
MsgId,CmdCode,TimeRadians,SequenceCount,MsgLength,HasSecondaryHeader,MsgType,ApId,HeaderVersion,SegmentationFlag,FlowLengthInWindow,SlidingWindowMeanIntervalSec,SlidingWindowMaxIntervalSec,SlidingWindowMinIntervalSec,MessageCountInWindow,UniqueMessageIDsInWindow,AverageMessageLengthInWindow,MessageRateInWindow,StdDevMessageLengthInWindow,CommandErrorCounter,IngestErrors,MemoryAnonMB,MemoryFileMB,MemoryKernelstackMB,MemoryPageTableMB,MemorySocketMB,MemoryPercpuMB,MemoryShmemMB,MemorySlabUnreclaimableMB,MemoryPageFaults,Label
6323,0,1.682673,0,8,1,1,179,0,4,1.715681,1.715681,1.715681,1.715681,2,2,8,0.1,0.0,0,0,5.55078125,4.5390625,0.78125,0.296875,0.0234375,0.000514984,1.25390625,0.727630615,0,3
6323,1,1.682717,0,12,1,1,179,0,4,2.324121,1.16206,1.715681,0.60844,3,2,9,0.15,1.91,0,0,5.5546875,4.546875,0.78125,0.296875,0.0234375,0.000514984,1.25390625,0.728157044,0,3
6276,0,1.682747,0,8,1,1,132,0,4,2.734382,0.911461,1.715681,0.410261,4,3,9,0.2,1.73,0,0,5.5546875,4.546875,0.78125,0.296875,0.0234375,0.000514984,1.25390625,0.727378845,0,3
6277,4,1.682777,0,8,1,1,133,0,4,3.145189,0.786297,1.715681,0.410261,5,4,8,0.25,1.79,0,0,5.55859375,4.546875,0.78125,0.296875,0.0234375,0.000514984,1.25390625,0.735267639,0,3
6298,0,1.682807,0,8,1,1,154,0,4,3.558012,0.711602,1.715681,0.410261,6,5,8,0.3,1.63,0,0,5.55859375,4.546875,0.78125,0.296875,0.0234375,0.000514984,1.25390625,0.726402283,0,3
```

Noised/augmented (subset of columns; first 5 rows):
```csv
MsgId,CmdCode,TimeRadians,MsgLength,ApId,FlowLengthInWindow,SlidingWindowMeanIntervalSec,SlidingWindowMaxIntervalSec,SlidingWindowMinIntervalSec,MessageCountInWindow,UniqueMessageIDsInWindow,AverageMessageLengthInWindow,MessageRateInWindow,StdDevMessageLengthInWindow,MemoryAnonMB,MemoryFileMB,MemoryKernelstackMB,MemoryPageTableMB,MemorySocketMB,MemoryPercpuMB,MemoryShmemMB,MemorySlabUnreclaimableMB,Label
6323.0,0.0,1.682673,8.0,179.0,1.715681,30.013085640817184,30.013085640817184,1.715681,2.0,2.0,8.0,0.1,0.0,5.55078125,4.5390625,0.78125,0.296875,0.0234375,0.000514984,1.25390625,0.727630615,3.0
6323.0,1.0,1.682717,12.0,179.0,15.884277892937796,7.942135529203211,11.725875623357569,4.15840226958023,3.0,2.0,61.51078237167521,1.0251797061945869,13.053954925544405,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,3.0
6276.0,0.0,1.682747,8.0,132.0,3.0635835949530343,7.161091771184779,20.57631423753152,0.3095581105142085,4.0,3.0,7.369632614379972,0.2,1.861072548087925,5.694260884449976,4.532496303429393,0.7807475771329438,0.2950751391635641,0.0235904369303063,0.0005170502545071,1.2093150080155668,0.7333448769405669,3.0
6277.0,4.0,1.682777,8.0,133.0,3.145189,0.786297,1.715681,0.410261,5.0,4.0,8.0,0.25,1.79,5.55859375,4.546875,0.78125,0.296875,0.0234375,0.000514984,1.25390625,0.735267639,3.0
6298.0,0.0,1.682807,8.0,154.0,3.558012,4.915462365259477,22.734982826297383,0.410261,6.0,5.0,8.0,0.3,1.63,5.55859375,4.546875,0.78125,0.296875,0.0234375,0.000514984,1.25390625,0.726402283,3.0
```

## Noise-to-feature eligibility matrix

The augmented dataset was generated using the provided augmentation script. The table below clarifies, for each feature present in Data/Augmented/noised_dataset.csv, whether it is eligible for modification under each noise category (✓ = eligible, x = never modified).

Legend: WN=White Noise, AO=Analog Outliers, G=Gaps, TR=Trends, SS=Signal Shifts,
FC=Frequency Changes, SD=Sensor Dropout, MW=Magnitude Warping, WTW=Window Time Warping

Feature                        WN  AO  G   TR  SS  FC  SD  MW  WTW
-----------------------------  --- --- --- --- --- --- --- --- ---
MsgId                          x   x   x   x   x   x   x   x   x
ApId                           x   x   x   x   x   x   x   x   x
CmdCode                        x   x   x   x   x   x   x   x   x
TimeRadians                    x   x   x   x   x   x   x   x   x
MessageCountInWindow           x   x   x   x   x   x   x   x   x
UniqueMessageIDsInWindow       x   x   x   x   x   x   x   x   x
FlowLengthInWindow             ✓   ✓   x   x   x   x   x   ✓   ✓
AverageMessageLengthInWindow   ✓   ✓   x   x   x   x   x   x   x
StdDevMessageLengthInWindow    ✓   ✓   x   x   x   x   x   ✓   x
MsgLength                      x   x   x   x   x   x   x   x   x
SlidingWindowMeanIntervalSec   ✓   ✓   ✓   x   ✓   ✓   x   ✓   ✓
SlidingWindowMaxIntervalSec    ✓   ✓   ✓   x   ✓   ✓   x   ✓   ✓
SlidingWindowMinIntervalSec    ✓   ✓   x   x   ✓   ✓   x   ✓   ✓
MessageRateInWindow            ✓   ✓   ✓   x   x   x   x   ✓   ✓
MemoryAnonMB                   ✓   ✓   x   ✓   x   x   ✓   ✓   x
MemoryFileMB                   ✓   ✓   x   ✓   x   x   ✓   ✓   x
MemoryKernelstackMB            ✓   ✓   x   ✓   x   x   ✓   ✓   x
MemoryPageTableMB              ✓   ✓   x   ✓   x   x   ✓   ✓   x
MemorySocketMB                 ✓   ✓   x   ✓   x   x   ✓   ✓   x
MemoryPercpuMB                 ✓   ✓   x   ✓   x   x   ✓   ✓   x
MemoryShmemMB                  ✓   ✓   x   ✓   x   x   ✓   ✓   x
MemorySlabUnreclaimableMB      ✓   ✓   x   ✓   x   x   ✓   ✓   x
Label                          x   x   x   x   x   x   x   x   x


## How to load (Python)
```python
import pandas as pd
raw = pd.read_csv("data/raw/consolidated_dataset_raw.csv")
noised = pd.read_csv("data/augmented/noised_dataset.csv")
label_map = {0:"command_flooding",1:"data_injection",2:"defence_impairment",3:"normal",4:"storage_exhaustion"}
```

## Usage Notes

### Recommended Train/Test Split Strategies

**Do NOT use random splits.** Telemetry data is inherently temporal. Random shuffling leaks future information into training sets and inflates reported accuracy.

**Option 1: Time-based split (recommended)**
```python
def time_based_train_test_split_multiclass(df, time_column="TimeRadians", label_column="Label", test_ratio=0.2):
    df_sorted = df.sort_values(by=time_column)
    train_parts, test_parts = [], []
    for cls in df_sorted[label_column].unique():
        class_data = df_sorted[df_sorted[label_column] == cls]
        test_size = int(len(class_data) * test_ratio)
        train_parts.append(class_data.iloc[:-test_size] if test_size > 0 else class_data)
        test_parts.append(class_data.iloc[-test_size:] if test_size > 0 else pd.DataFrame())
    return pd.concat(train_parts), pd.concat(test_parts)
```

**Option 2: Labels-wise split (leave-one-out)**
```python
# Train on 4 classes, test on 1 held-out class
train_df = df[df["Label"] != held_out_label]
test_df  = df[df["Label"] == held_out_label]
```

**Option 3: Cross-label generalization**
```python
from sklearn.model_selection import LeaveOneGroupOut
logo = LeaveOneGroupOut()
for train_idx, test_idx in logo.split(X, y, groups=attackTypes_ids):
    # Evaluate generalization to unseen attack types
```

### Data Leakage Warning (Sliding-Window Features)

The dataset contains pre-computed sliding-window features:
- `SlidingWindowMeanIntervalSec`, `SlidingWindowMaxIntervalSec`, `SlidingWindowMinIntervalSec`
- `FlowLengthInWindow`, `MessageCountInWindow`, `MessageRateInWindow`, etc.

**Leakage risk:** These features aggregate information over a temporal window. If you create lag features or use random splits:
1. Adjacent rows share overlapping window statistics
2. Future information may leak into the training set
3. Reported accuracy will be **overestimated** vs. real-world deployment

**Mitigation strategies:**
- Use strict temporal splits with a gap buffer between train/test
- When creating lag features, drop the first N rows of the test set:
```python
# After time-based split, drop rows where lag features would depend on train data
num_lags = 5
test_df = test_df.iloc[num_lags:]
```
- For cross-validation, use `TimeSeriesSplit` or blocked CV that respects temporal ordering

## File Integrity Verification

After download, verify file integrity using the provided `checksums.txt`:

```bash
# Linux/macOS
sha256sum -c Data/Metadata/checksums.txt

# Windows (PowerShell)
Get-FileHash -Algorithm SHA256 Data/Raw/consolidated_dataset_raw.csv
Get-FileHash -Algorithm SHA256 Data/Augmented/noised_dataset.csv
```

## Dataset Validation (Schema, Dtypes, and Dimensions)

To validate that your downloaded files match the released schema and expected dimensions, run:

```bash
python Code/Validation/validate_and_load.py \
  --raw Data/Raw/consolidated_dataset_raw.csv \
  --augmented Data/Augmented/noised_dataset.csv \
  --label-schema Data/Metadata/label_schema.json \
  --checksums Data/Metadata/checksums.txt
```