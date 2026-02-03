# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Generate platform-specific command documentation from YAML specs."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from anima.commands.specs.models import CommandSpec

# Available platforms
PLATFORMS = ["claude", "opencode", "antigravity"]


def get_anima_root() -> Path:
    """Get the root directory of the anima package."""
    return Path(__file__).parent.parent


def load_spec(spec_path: Path) -> CommandSpec:
    """Load a command specification from a YAML file."""
    with open(spec_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return CommandSpec(**data)


def load_all_specs() -> list[CommandSpec]:
    """Load all command specifications from the specs directory."""
    specs_dir = get_anima_root() / "commands" / "specs"
    specs = []
    for spec_file in sorted(specs_dir.glob("*.yaml")):
        specs.append(load_spec(spec_file))
    return specs


def get_template(platform: str) -> str:
    """Load the Jinja2 template for a platform."""
    template_path = get_anima_root() / "platforms" / platform / "template.md.j2"
    with open(template_path, encoding="utf-8") as f:
        return f.read()


def render_command(spec: CommandSpec, platform: str) -> str:
    """Render a command specification for a platform."""
    template_dir = get_anima_root() / "platforms" / platform
    # nosec B701: autoescape not needed - generating markdown, not HTML
    env = Environment(loader=FileSystemLoader(str(template_dir)), keep_trailing_newline=True)  # nosec B701
    template = env.get_template("template.md.j2")

    # Build context
    name = spec.get_name(platform)
    title = name.replace("-", " ").title()

    # Substitute {platform} in examples
    examples = [ex.replace("{platform}", platform) for ex in spec.examples]

    context = {
        "name": name,
        "title": title,
        "description": spec.get_description(platform),
        "detailed_description": spec.detailed_description,
        "arguments": spec.arguments,
        "options": spec.options,
        "examples": examples,
        "execution": spec.get_execution(platform),
        "output_message": spec.output_message,
        "extra_sections": spec.extra_sections,
    }

    return template.render(**context)


def get_output_path(spec: CommandSpec, platform: str) -> Path:
    """Get the output file path for a generated command."""
    name = spec.get_name(platform)
    return get_anima_root() / "platforms" / platform / "commands" / f"{name}.md"


def generate_commands(
    platform: str | None = None,
    check_only: bool = False,
    verbose: bool = False,
) -> int:
    """Generate platform-specific command documentation.

    Args:
        platform: Generate for specific platform, or all if None
        check_only: Validate without writing (return 1 if drift detected)
        verbose: Print detailed output

    Returns:
        0 on success, 1 on error or drift detected
    """
    specs = load_all_specs()
    platforms = [platform] if platform else PLATFORMS
    errors: list[str] = []
    generated = 0
    skipped = 0

    for plat in platforms:
        if verbose:
            print(f"\n=== Platform: {plat} ===")

        for spec in specs:
            if spec.should_skip(plat):
                if verbose:
                    print(f"  Skip: {spec.name} (marked skip for {plat})")
                skipped += 1
                continue

            output_path = get_output_path(spec, plat)
            content = render_command(spec, plat)

            if check_only:
                # Compare with existing file
                if not output_path.exists():
                    errors.append(f"Missing: {output_path}")
                    continue

                existing = output_path.read_text(encoding="utf-8")
                if existing != content:
                    errors.append(f"Drift: {output_path}")
                    if verbose:
                        print(f"  Drift: {spec.get_name(plat)}")
                else:
                    if verbose:
                        print(f"  OK: {spec.get_name(plat)}")
            else:
                # Write the file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content, encoding="utf-8")
                generated += 1
                if verbose:
                    print(f"  Generated: {output_path.name}")

    if check_only:
        if errors:
            print(f"\n{len(errors)} file(s) have drift:")
            for err in errors:
                print(f"  - {err}")
            print("\nRun 'uv run anima generate-commands' to regenerate.")
            return 1
        print(f"All {len(specs) * len(platforms) - skipped} files are up to date.")
        return 0
    else:
        print(f"Generated {generated} command files, skipped {skipped}.")
        return 0


def run(args: list[str]) -> int:
    """CLI entry point for generate-commands."""
    platform = None
    check_only = False
    verbose = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--platform", "-p"):
            if i + 1 >= len(args):
                print("Error: --platform requires a value")
                return 1
            platform = args[i + 1]
            if platform not in PLATFORMS:
                print(f"Error: Unknown platform '{platform}'. Must be one of: {', '.join(PLATFORMS)}")
                return 1
            i += 2
        elif arg in ("--check", "-c"):
            check_only = True
            i += 1
        elif arg in ("--verbose", "-v"):
            verbose = True
            i += 1
        elif arg in ("--help", "-h"):
            print("Generate platform-specific command documentation")
            print("")
            print("Usage: uv run anima generate-commands [options]")
            print("")
            print("Options:")
            print("  --platform, -p PLATFORM  Generate for specific platform (claude, opencode, antigravity)")
            print("  --check, -c              Validate without writing (exit 1 if drift)")
            print("  --verbose, -v            Show detailed output")
            print("  --help, -h               Show this help")
            return 0
        else:
            print(f"Error: Unknown argument '{arg}'")
            return 1

    return generate_commands(platform=platform, check_only=check_only, verbose=verbose)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
