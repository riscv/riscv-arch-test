# Contributing to RISC-V Architectural Certification Tests

Your inputs are welcome and greatly appreciated! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new tests or coverpoints
- Becoming a maintainer

## We Develop with GitHub

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Development Setup

Before contributing, make sure you have the development environment set up. Refer to the [README](./README.md#getting-started) for full installation and setup instructions.

In addition to the runtime prerequisites, contributors should set up the following development tools:

### Pre-commit Hooks

This project uses [`pre-commit`](https://pre-commit.com/) to run automated checks before each commit, including linting, formatting, type checking, and spell checking. Install the hooks with:

```bash
uv run pre-commit install
```

Once installed, the hooks will run automatically on `git commit`. You can also run them manually on all files with:

```bash
uv run pre-commit run --all-files
```

### Code Quality Tools

All Python code must pass the following checks:

- **[Ruff](https://docs.astral.sh/ruff/)** for linting and formatting
- **[Pyright](https://github.com/microsoft/pyright)** for type checking

These tools are run automatically by the pre-commit hooks, but can also be run manually:

```bash
# Lint and type check
make lint

# Auto-fix lint issues
make lint-fix

# Format code
make format
```

All Python code should include type hints. Configuration for Ruff and Pyright is in [`pyproject.toml`](./pyproject.toml).

## Pull Requests

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `act4`.
2. Set up pre-commit hooks and ensure all checks pass (see [Development Setup](#development-setup)).
3. If you have added or modified tests, ensure they compile and pass by running `make` with an appropriate [DUT configuration](./README.md#configuration). A good choice for testing is `make spike`. To also verify coverage, run `make coverage`.
4. If you have added or modified coverpoints or test generators, refer to the [Developer's Guide](./docs/DeveloperGuide.md) for the expected workflow.
5. If you have updated the docs, ensure that they render correctly in the respective format.
6. Include a comment with the SPDX license identifier in all source files, for example:
   ```
   // SPDX-License-Identifier: Apache-2.0
   ```
7. Issue the pull request with a clear description of the changes and the motivation behind them.

## Licensing

When you submit code changes, your submissions are understood to be under the permissive open source licenses that cover the project. In general:

- Code is licensed under the [BSD 3-Clause License](./COPYING.BSD) or the [Apache License 2.0](./COPYING.APACHE).
- Documentation is licensed under the [Creative Commons Attribution 4.0 International License](./COPYING.CC).

Please include an appropriate SPDX license identifier in all source files. Feel free to contact the maintainers if licensing is a concern.

## Reporting Bugs

We use GitHub issues to track bugs. Report a bug by [opening a new issue](https://github.com/riscv/riscv-arch-test/issues/new/choose) using the appropriate issue template.

**Great bug reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)
