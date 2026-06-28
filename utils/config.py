from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_interest():
    with open(ROOT / "config" / "interest.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_profile():
    with open(ROOT / "config" / "research_profile.md", "r", encoding="utf-8") as f:
        return f.read()
