---
paths:
  - "**/*.py"
---

Python code in this project must follow these conventions:

- 120-character line length (ruff enforced)
- Type annotations on all functions (ANN rules enabled)
- Use `pathlib.Path` instead of `os.path` (PTH rules enabled)
- `print()` is allowed (no logging framework required)
- Every file needs the standard header with SPDX license:

```python
##################################
# filename.py
#
# Brief description.
# author@email.com Month Year
# SPDX-License-Identifier: Apache-2.0
##################################

"""Module docstring."""
```

- Run `make lint` (ruff check + pyright) before considering work complete
- Use `uv run` to execute any Python scripts or tools
