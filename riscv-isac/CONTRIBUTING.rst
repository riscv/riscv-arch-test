.. See LICENSE.incore for details

.. highlight:: shell

============
Contributing
============

Your inputs are welcome and greatly appreciated! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

We develop with Github
----------------------

We use github to host code, to track issues and feature requests, as well as accept pull requests.

Git Strategy
------------

The repo adopts a simple git strategy where all contributions to the repo are made to the ``dev``
branch (i.e. all Pull-Requests must use ``dev`` as the target branch). On a monthly cadence (decided
and controlled by the SIG-ARCH-TEST members) the ``dev`` branch will be merged to the ``main`` to by
the official maintainers of the repo. This will create an official release capturing all the 
development over the month into a single release.

To implement the above strategy successfully the following needs be followed:

* Developers: All pull-requests from developers must target the ``dev`` branch and the PR must
contain an entry in the CHANGELOG.md file under `[WIP-DEV]` section.
* Maintainers: When a making a release the maintainers shall assign semantic version number by
updating the CHANGELOG and the respective python files before raising a PR from the `dev` to `main`.

All changes happen through Pull Requests
----------------------------------------

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `dev`.
2. If you have updated the docs, ensure that they render correctly in the respective format.
3. Make sure to create an entry in the CHANGELOG.md under the `WIP-DEV` section. 
4. Ensure the existing framework is not broken and still passes the basic checks.
5. Please include a comment with the SPDX license identifier in all source files, for example:
   ```
   // SPDX-License-Identifier: BSD-3-Clause
   ```
6. Issue that pull request - make sure the target is to the dev branch.

Checks for a PR
---------------

Make sure your PR meets all the following requirements:

1. You have made an entry in the CHANGELOG.md undet the `WIP-DEV` section.
3. The commit messages are verbose.
4. You PR doesn't break existing framework.

Versioning (for maintainers only)
---------------------------------

When issuing pull requests from the `dev` branch to the `main` branch, an entry in the CHANGELOG.md 
is mandatory. The repo adheres to the [`Semantic Versioning`](https://semver.org/spec/v2.0.0.html) scheme. 
Following guidelines must be followed while assigning a new version number :

- Patch-updates: all doc updates (like typos, more clarification,etc) will be patches. Beautification enhancements will also be treated as patch updates. Certain bug fixes to existing code may be treated as patches as well.
- Minor-updates: Updates to code with new extensions, features, run time optimizations can be
  treated as minor updates.
- Major-updates: Changes to the framework flow (backward compatible or incompatible) will be treated
  as major updates.

Note: You can have either a patch or minor or major update.

Each PR will also require the tools version to be bumped. This can be achieved using the following
commands::

  $ bumpversion --allow-dirty --no-tag --config-file setup.cfg patch  #options: major / minor / patch

bumpversion can be installed using `pip install bumpversion`

All contributions will be under the permissive open-source License
------------------------------------------------------------------

In short, when you submit code changes, your submissions are understood to be under a permissive open source license like BSD-3, Apache-2.0 and CC, etc that covers the project. Feel free to contact the maintainers if that's a concern.

Report bugs using Github's `issues <https://github.com/riscv/riscv-isac/issues>`_
------------------------------------------------------------------------------------

We use GitHub issues to track public bugs. Report a bug by `opening a new issue <https://github.com/riscv/riscv-isac/issues/new>`_  it's that easy!

Write bug reports with detail, background, and sample code
----------------------------------------------------------

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can. 
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)
