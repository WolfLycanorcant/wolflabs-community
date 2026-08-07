import argparse
import sys
from pathlib import Path
import yaml

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "onboarding.yml"

VALID_STYLES = ["primary", "secondary", "success", "danger"]

def add_button(label: str, role: str, emoji: str, style: str, row: int) -> bool:
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found at {CONFIG_PATH}", file=sys.stderr)
        return False

    # Normalize inputs
    label = label.strip()
    role = role.strip() if role else label
    emoji = emoji.strip()
    style = style.strip().lower() if style else "primary"
    
    if style not in VALID_STYLES:
        print(f"Error: Invalid style '{style}'. Must be one of {VALID_STYLES}", file=sys.stderr)
        return False
        
    if not (0 <= row <= 4):
        print(f"Error: Invalid row '{row}'. Must be between 0 and 4.", file=sys.stderr)
        return False

    # Read existing content and parse YAML to ensure it's valid
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        data = yaml.safe_load(content)
    except Exception as e:
        print(f"Error parsing existing YAML file: {e}", file=sys.stderr)
        return False

    if not isinstance(data, dict) or "onboarding" not in data or "roles" not in data["onboarding"]:
        print("Error: Invalid YAML structure (missing onboarding.roles)", file=sys.stderr)
        return False

    # Check for duplicate role or label
    existing_roles = data["onboarding"]["roles"] or []
    for r in existing_roles:
        if isinstance(r, dict) and r.get("label", "").lower() == label.lower():
            print(f"Warning: A button with label '{label}' already exists.")
            break

    # Build the YAML snippet formatted cleanly matching existing style
    # Format:
    #     - label: "..."
    #       role: "..."
    #       emoji: "..."
    #       style: "..."
    #       row: ...
    new_entry = f'\n    - label: "{label}"\n      role: "{role}"\n      emoji: "{emoji}"\n      style: "{style}"\n      row: {row}\n'

    # Ensure file ends with newline before appending
    updated_content = content
    if not updated_content.endswith("\n"):
        updated_content += "\n"
    updated_content += new_entry

    # Verify that updated_content parses cleanly
    try:
        updated_data = yaml.safe_load(updated_content)
        roles = updated_data["onboarding"]["roles"]
        assert len(roles) == len(existing_roles) + 1
    except Exception as e:
        print(f"Error: Generated content failed YAML validation: {e}", file=sys.stderr)
        return False

    # Write back to onboarding.yml
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print("\n✅ Successfully added button to onboarding.yml!")
    print(f"  • Label: {label}")
    print(f"  • Role:  {role}")
    print(f"  • Emoji: {emoji if emoji else '(none)'}")
    print(f"  • Style: {style}")
    print(f"  • Row:   {row}\n")
    return True

def prompt_interactive():
    print("========================================")
    print("    Add Onboarding Button / Role       ")
    print("========================================\n")
    
    label = input("Button Label (e.g. VIP Member): ").strip()
    while not label:
        print("Label cannot be empty!")
        label = input("Button Label: ").strip()

    role = input(f"Role Name (press Enter for '{label}'): ").strip()
    if not role:
        role = label

    emoji = input("Emoji (e.g. ⭐, 🎲, 👑, press Enter for none): ").strip()

    print(f"Available styles: {', '.join(VALID_STYLES)}")
    style = input("Style [primary]: ").strip().lower()
    if not style or style not in VALID_STYLES:
        style = "primary"

    row_str = input("Row (0-4) [0]: ").strip()
    try:
        row = int(row_str) if row_str else 0
    except ValueError:
        row = 0

    return add_button(label, role, emoji, style, row)

def main():
    parser = argparse.ArgumentParser(description="Add a role button to config/onboarding.yml")
    parser.add_argument("--label", "-l", help="Button label text")
    parser.add_argument("--role", "-r", help="Discord role name (defaults to label)")
    parser.add_argument("--emoji", "-e", default="", help="Emoji icon")
    parser.add_argument("--style", "-s", default="primary", choices=VALID_STYLES, help="Button style")
    parser.add_argument("--row", "-w", type=int, default=0, help="Action row (0-4)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Force interactive mode")

    args = parser.parse_args()

    if args.interactive or not args.label:
        success = prompt_interactive()
    else:
        success = add_button(
            label=args.label,
            role=args.role or args.label,
            emoji=args.emoji,
            style=args.style,
            row=args.row
        )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
