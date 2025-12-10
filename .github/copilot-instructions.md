# GitHub Copilot Instructions

## Python Tooling Guidelines

1. Use `uv` for all Python related tasks instead of `python` or `pip` directly. This ensures that the correct Python environment is used.
2. All Python files should have type hints for better code clarity and maintainability.
3. All Python code should pass the `ruff` linter and `pyright` type checker without errors. It should also be formatted using `ruff`.

## Pull Request Guidelines

1. Ensure that `pre-commit` hooks are set up and passing before submitting a pull request.
