# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (using `scripts/lint`).
4. Test you contribution.
5. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People _love_ thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Use [ruff](https://docs.astral.sh/ruff/) to make sure the code follows the style (see `script/lint`).

## Development environment

### With Docker / VS Code Dev Container

This project includes a Dev Container configuration for Visual Studio Code. With this container
you will have a standalone Home Assistant instance running and already configured with the included
[`configuration.yaml`](./config/configuration.yaml) file.

### With NixOS / Nix Flakes

This project provides a `flake.nix` for a reproducible development environment on NixOS or any
system with Nix installed.

**Prerequisites:**
- [Nix](https://nixos.org/download/) with [Flakes enabled](https://wiki.nixos.org/wiki/Flakes)
- [direnv](https://direnv.net/) (optional, but recommended for automatic activation)

**Getting started:**

```bash
# Option 1 — automatic activation with direnv (recommended)
direnv allow

# Option 2 — manual activation
nix develop
```

On first activation, the shell will automatically:
1. Create a `.venv` Python 3.12 virtual environment
2. Install all dependencies from `requirements.txt` (including Home Assistant)

**Daily workflow:**

```bash
# Start Home Assistant locally (available at http://localhost:8123)
script/develop

# Lint and format
script/lint

# Run tests
pytest

# Update dependencies after changing requirements.txt
uv pip install -r requirements.txt
```

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
