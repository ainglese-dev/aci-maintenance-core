# Stage 3: ACI Fabric Data Analyzer

## Purpose
Offline analysis and comparison of fabric snapshots collected by Stage 2. Generate reports, summaries, and highlight changes between snapshots.

## Input
- `inputs/snapshots/*.json` - Fabric snapshots from Stage 2

## Process
1. Load and parse snapshot files
2. Compare snapshots to identify changes
3. Analyze fabric health trends
4. Generate comparison reports and summaries
5. Create tabular views of differences

## Output
- `outputs/reports/comparison_YYYYMMDD_HHMMSS.html` - HTML comparison report
- `outputs/reports/health_summary_YYYYMMDD_HHMMSS.txt` - Health analysis
- `outputs/reports/changes_YYYYMMDD_HHMMSS.csv` - Change summary table

## Usage
```bash
cd stage3-analyzer
python stage3-tool.py compare --before <snapshot1> --after <snapshot2>
python stage3-tool.py analyze --snapshot <snapshot>
python stage3-tool.py health --all
```

## Analysis Types
- **Comparison**: Before/after snapshot differences
- **Health**: Fault analysis and trends
- **Inventory**: Hardware changes
- **Performance**: Interface utilization changes
- **Policy**: Configuration changes

## Requirements
- Snapshot files from Stage 2
- No network connectivity required (offline operation)