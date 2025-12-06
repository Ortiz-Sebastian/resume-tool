# Secondary Column Ratio Feature

## Overview

The **secondary_column_ratio** is a sophisticated metric that measures **what percentage of your resume's content is in non-primary columns** (sidebar, right column, etc.). This provides much more nuanced feedback than just "has multi-column: yes/no".

## Why It Matters

ATS systems typically read left-to-right, top-to-bottom. Content in secondary columns (column 2, 3, etc.) is often:
- Read out of order
- Ignored completely
- Misinterpreted

**Example:**
- Resume A: 5% of content in column 2 (small contact sidebar) → Low risk
- Resume B: 40% of content in column 2 (major skills/experience section) → High risk

## How It Works

### 1. Column Detection (`ats_view_generator.py`)

```python
def _detect_columns_and_ratio(self, blocks: List[Dict[str, Any]]) -> Tuple[bool, float]:
    """
    1. Extract x-position (left edge) of each text block
    2. Find significant gaps (> 20% of page width)
    3. Assign column numbers based on position
    4. Compute character count per column
    5. Calculate ratio of content NOT in column 1
    """
```

**Visual Example:**

```
Page Width: 612 points

Blocks:
┌─────────────────────┬───────────────┐
│ Column 1 (x=72)     │ Column 2      │
│                     │ (x=450)       │
│ John Doe            │ Skills:       │
│ Engineer            │ • Python      │
│ • Developed...      │ • Java        │
│ • Improved...       │ • SQL         │
│                     │               │
│ (1000 chars)        │ (500 chars)   │
└─────────────────────┴───────────────┘

Gap at x=450 (378 pts from x=72) → Multi-column detected!

Calculation:
- Column 1: 1000 characters
- Column 2: 500 characters  
- Total: 1500 characters
- Secondary ratio = 1 - (1000/1500) = 0.333 (33.3%)
```

### 2. Ratio Computation (`ats_issues.py`)

```python
def compute_secondary_column_ratio(blocks: List[Dict[str, Any]]) -> float:
    """
    For each block:
        1. Get column number (1, 2, 3, ...)
        2. Count characters in that column
    
    Return: 1 - (column_1_chars / total_chars)
    
    Examples:
        - All in column 1 → 0.0 (perfect)
        - 70% in col 1, 30% in col 2 → 0.3 (minor issue)
        - 50% in col 1, 50% in col 2 → 0.5 (major issue)
    """
```

### 3. Penalty Calculation (`compute_complexity_metric()`)

```python
# Multi-column penalty (weighted by how much content is in secondary columns)
if has_multi_column:
    base_penalty = 20  # Base penalty for having multi-column
    ratio_penalty = secondary_column_ratio * 20  # Up to +20 more
    total_penalty = base_penalty + ratio_penalty
    
    score += total_penalty
```

**Penalty Examples:**

| Secondary Ratio | Base | Ratio Penalty | Total | Interpretation |
|----------------|------|---------------|-------|----------------|
| 0.05 (5%)      | +20  | +1            | 21    | Minor sidebar (acceptable) |
| 0.20 (20%)     | +20  | +4            | 24    | Moderate sidebar |
| 0.30 (30%)     | +20  | +6            | 26    | Significant content in column 2 |
| 0.50 (50%)     | +20  | +10           | 30    | Half content in secondary (bad) |
| 0.70 (70%)     | +20  | +14           | 34    | Most content in secondary (very bad) |

## Data Flow

```
1. PDF Upload
   ↓
2. ats_view_generator.py
   - Extract blocks from PDF (PyMuPDF)
   - Detect columns based on x-positions
   - Compute secondary_column_ratio
   ↓
3. Returns ats_diagnostics with:
   {
     "has_multi_column": true,
     "secondary_column_ratio": 0.33,
     ...
   }
   ↓
4. scorer.py or ats_issue_detector.py
   - Calls compute_complexity_metric()
   - Passes secondary_column_ratio
   ↓
5. complexity_metric
   {
     "score": 45,
     "label": "complex",
     "contributing_factors": [
       "Multi-column layout with 33% content in secondary columns"
     ]
   }
   ↓
6. Frontend displays:
   "Resume Complexity: 45/100 (Complex)"
   "Issue: Multi-column layout with 33% content in secondary columns"
```

## API Response Example

```json
{
  "ats_diagnostics": {
    "has_multi_column": true,
    "secondary_column_ratio": 0.33,
    "complexity_metric": {
      "score": 45,
      "label": "complex",
      "contributing_factors": [
        "Multi-column layout with 33% content in secondary columns",
        "Contains 2 images"
      ]
    }
  }
}
```

## Frontend Display Ideas

### Progress Bar (Inverted - Lower is Better)
```
Complexity Score: 45/100
[█████████░░░░░░░░░░] Complex

Contributing Factors:
⚠️ Multi-column layout with 33% content in secondary columns
⚠️ Contains 2 images
```

### Detailed Breakdown
```
Layout Analysis:
├─ Multi-column detected: Yes
├─ Primary column content: 67%
├─ Secondary column content: 33% ⚠️
└─ Recommendation: Move skills and education to primary column
```

## Testing

```python
# Test 1: Single column (ideal)
blocks = [
    {"text": "John Doe", "column": 1},
    {"text": "Engineer", "column": 1},
]
ratio = compute_secondary_column_ratio(blocks)
assert ratio == 0.0  # All in primary

# Test 2: Small sidebar (acceptable)
blocks = [
    {"text": "A" * 1000, "column": 1},  # 1000 chars
    {"text": "B" * 100, "column": 2},   # 100 chars
]
ratio = compute_secondary_column_ratio(blocks)
assert ratio ≈ 0.09  # 9% in secondary

# Test 3: Major secondary content (bad)
blocks = [
    {"text": "A" * 500, "column": 1},   # 500 chars
    {"text": "B" * 500, "column": 2},   # 500 chars
]
ratio = compute_secondary_column_ratio(blocks)
assert ratio == 0.5  # 50% in secondary - major issue!
```

## Benefits

### For Users
1. **Specific feedback**: "33% of your content is in column 2" vs. just "multi-column detected"
2. **Prioritization**: Know if it's a minor sidebar or major layout problem
3. **Track improvements**: See ratio go from 0.4 → 0.1 as they fix layout

### For Developers
1. **Nuanced scoring**: Small sidebar penalized less than major two-column layout
2. **Data-driven**: Based on actual content distribution, not boolean flags
3. **Extensible**: Can add more column metrics (e.g., critical sections in secondary columns)

## Edge Cases

### Three Columns
```
┌───────┬──────────┬─────────┐
│ Col 1 │  Col 2   │  Col 3  │
│ 40%   │   40%    │   20%   │
└───────┴──────────┴─────────┘

Secondary ratio = 1 - 0.40 = 0.60 (60% NOT in primary)
```

### Unbalanced Columns
```
┌────────────────┬───┐
│    Column 1    │ C │
│                │ o │
│                │ l │
│    95%         │ 5%│
└────────────────┴───┘

Secondary ratio = 0.05 (5% in sidebar - acceptable)
```

## Future Enhancements

1. **Section-specific analysis**: Flag if Experience/Education is in secondary column (worse than Skills)
2. **Reading order simulation**: Predict exact ATS reading order
3. **Confidence scoring**: How confident are we in column detection?
4. **Visual heatmap**: Show on frontend which blocks are in which columns

## Summary

The **secondary_column_ratio** transforms a binary yes/no flag into a **quantitative, actionable metric** that:
- ✅ Provides specific, measurable feedback
- ✅ Allows proportional penalty calculation
- ✅ Helps users understand severity
- ✅ Tracks improvements over time

It's a perfect example of using **data-driven insights** instead of simple boolean flags!

