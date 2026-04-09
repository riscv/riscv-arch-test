# csv-editing.md — CSV Testplan Editing Guide

## File Locations

| What                  | Where                                       |
| --------------------- | ------------------------------------------- |
| Canonical CSV source  | `working-testplans/*.csv`                   |
| Live CSVs (framework) | `testplans/*.csv` — **NEVER edit directly** |
| CSV editor script     | `csv_edit.py` (repo root)                   |

## csv_edit.py API

CSV name auto-resolves (e.g., `'Vf'`, `'Vls'`) to `working-testplans/`. Note: VfCustom is now merged into Vf (like VxCustom is part of Vx).

| Function         | Usage                                                        | Description                                  |
| ---------------- | ------------------------------------------------------------ | -------------------------------------------- |
| `read_structure` | `read_structure(csv_name)`                                   | Headers + first column (lightweight context) |
| `set_cells`      | `set_cells(csv_name, [(row, col), ...], value="x")`          | Set specific cells                           |
| `fill_column`    | `fill_column(csv_name, col_name, row_names=None, value="x")` | Fill a column                                |
| `fill_row`       | `fill_row(csv_name, row_name, col_names=None, value="x")`    | Fill a row                                   |
| `clear_cells`    | `clear_cells(csv_name, [(row, col), ...])`                   | Clear cells                                  |

Always call `read_structure()` first. Do NOT read full CSVs with the Read tool — they can be very large.

## Stateless Processing

CSV editor agents are launched fresh per row with NO conversation history. All knowledge must come from .md files. If you learn something new, add it to the appropriate guide before finishing.

## Knowledge Persistence

| Discovery Type                   | Add To                                                          |
| -------------------------------- | --------------------------------------------------------------- |
| New encoding / bit field value   | `guides/vector-reference.md`                                    |
| New script pitfall or API detail | `generators/testgen/scripts/custom/GUIDE.md`                    |
| New workflow step or tool        | `generators/testgen/scripts/custom/CLAUDE-coverage-workflow.md` |
| Custom coverpoint outcome/bug    | `generators/testgen/scripts/custom/claude-scripts/knowledge.md` |
