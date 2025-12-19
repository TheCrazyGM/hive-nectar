#!/usr/bin/env python3
"""Generate version files for nectar packages."""

import re


def get_version():
    """Get version from pyproject.toml."""
    try:
        import tomli

        with open("pyproject.toml", "rb") as f:
            data = tomli.load(f)
            return data["project"]["version"]
    except ImportError:
        # Fall back to regex if tomli is not available
        with open("pyproject.toml") as f:
            content = f.read()
            version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if version_match:
                return version_match.group(1)
            raise ValueError("Could not find version in pyproject.toml")


def write_version_py(filename, version):
    """Write version."""
    content = f'''"""THIS FILE IS GENERATED FROM nectar PYPROJECT.TOML."""

version = "{version}"
'''
    with open(filename, "w") as file:
        file.write(content)


def main():
    """Main function."""
    version = get_version()
    print(f"Generating version files for version {version}")

    # Write version files for all packages
    write_version_py("src/nectar/version.py", version)
    write_version_py("src/nectarbase/version.py", version)
    write_version_py("src/nectarapi/version.py", version)
    write_version_py("src/nectargraphenebase/version.py", version)

    print("Version files generated successfully!")


if __name__ == "__main__":
    main()
