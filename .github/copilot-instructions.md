# GitHub Copilot Instructions

## General Guidelines

1. Always run `make coverage` after making changes to verify that all tests generate and run correctly and that coverage targets are met. Look at `_overall_coverage.txt` for coverage results. There may be multiple coverage reports if tests are run for different configurations.

## Python Tooling Guidelines

1. Use `uv` for all Python related tasks instead of `python` or `pip` directly. This ensures that the correct Python environment is used.
2. All Python files should have type hints for better code clarity and maintainability.
3. All Python code should pass the `ruff` linter and `pyright` type checker without errors. It should also be formatted using `ruff`. Always run these tools via `uv` to ensure consistency and make sure to run them after all changes to Python files.

## Pull Request Guidelines

1. Ensure that `pre-commit` hooks are set up and passing before submitting a pull request.
