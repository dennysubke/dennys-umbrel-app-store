---
language:
- de
license: afl-3.0
task_categories:
- image-to-text
dataset_info:
  features:
  - name: image
    dtype: image
  - name: text
    dtype: string
  splits:
  - name: train
    num_bytes: 3795163553.91
    num_examples: 10854
  download_size: 1796789422
  dataset_size: 3795163553.91
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
size_categories:
- 10K<n<100K
---
# German handwriting

This dataset contains German handwriting images and corresponding text labels. In total, the dataset contains around 10,000 entries with handwriting from 15 different people.
The data was created with the help of transcripts from school and university.
The dataset was created as part of a handwriting recognition project at the FH-SWF.

## How to use:

```python
from datasets import load_dataset

dataset = load_dataset('fhswf/german_handwriting')
```