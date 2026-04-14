{
  description = "Home Assistant Ecocito integration - development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        # Home Assistant requires Python 3.12
        python = pkgs.python312;
        # Use nixpkgs numpy (pip wheels have unpatched ELF paths, fail on NixOS)
        numpyPkg = pkgs.python312Packages.numpy;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python
            uv
            git
            ruff
          ];

          shellHook = ''
            # Recreate venv if HA version doesn't match requirements
            EXPECTED_HA="2024.6.0"
            CURRENT_HA=""
            if [ -f .venv/lib/python3.12/site-packages/homeassistant/const.py ]; then
              CURRENT_HA=$(grep '__version__' .venv/lib/python3.12/site-packages/homeassistant/const.py | head -1 | sed 's/.*"\(.*\)".*/\1/')
            fi
            if [ ! -d .venv ] || [ "$CURRENT_HA" != "$EXPECTED_HA" ]; then
              if [ -d .venv ] && [ "$CURRENT_HA" != "$EXPECTED_HA" ]; then
                echo "⚠️  HA version mismatch (found $CURRENT_HA, expected $EXPECTED_HA) — recreating venv..."
                rm -rf .venv
              else
                echo "🔧 Creating Python virtual environment..."
              fi
              uv venv .venv --python ${python}/bin/python3.12
              echo "📦 Installing dependencies..."
              uv pip install -r requirements.txt
              # Pin transitive deps not fully constrained by HA 2024.6.0
              uv pip install "josepy<2.0" "mutagen" "pycares<5.0" -q
              # Remove pip-installed numpy — we use nixpkgs numpy (NixOS-patched ELF)
              uv pip uninstall numpy -q 2>/dev/null || true
              # Replace venv uv with a wrapper to nixpkgs uv (HA installs packages
              # on-demand at startup using .venv/bin/uv which is a generic ELF binary
              # incompatible with NixOS)
              echo "#!/bin/sh" > .venv/bin/uv
              echo "exec ${pkgs.uv}/bin/uv \"\$@\"" >> .venv/bin/uv
              chmod +x .venv/bin/uv
            fi

            source .venv/bin/activate

            # Inject nixpkgs numpy (properly patched for NixOS) ahead of any pip numpy
            export PYTHONPATH="${numpyPkg}/lib/python3.12/site-packages''${PYTHONPATH:+:$PYTHONPATH}"

            # Ensure nix-provided tools override pip-installed binaries (e.g. ruff)
            export PATH="${pkgs.ruff}/bin:$PATH"

            # Make the custom component visible to Home Assistant and pytest
            export PYTHONPATH="''${PYTHONPATH:+$PYTHONPATH:}$(pwd)/custom_components"

            echo "✅ Ecocito dev environment ready."
            echo "   • Run 'script/develop' to start Home Assistant locally"
            echo "   • Run 'script/lint' to lint and format"
            echo "   • Run 'pytest' to run tests"
            echo "   • Run 'uv pip install -r requirements.txt' to refresh dependencies"
          '';
        };
      });
}
