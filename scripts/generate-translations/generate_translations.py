#!/usr/bin/env python3
"""Generate translations for all supported languages from English source.

This unified script replaces the individual generate_complete_*.py scripts.
It uses language-specific translation dictionaries stored in the
translation_dictionaries/ subfolder.

Usage:
    # Generate all languages
    python generate_all_translations.py --all

    # Generate single language
    python generate_all_translations.py --language de

    # Generate multiple specific languages
    python generate_all_translations.py --language de fr it
"""

import argparse
import copy
import importlib
import json
import sys
from pathlib import Path

# Language configuration: code -> (name, dictionary module name)
LANGUAGE_CONFIG = {
    "de": ("German", "de"),
    "es": ("Spanish", "es"),
    "et": ("Estonian", "et"),
    "fi": ("Finnish", "fi"),
    "fr": ("French", "fr"),
    "it": ("Italian", "it"),
    "nb": ("Norwegian Bokmål", "nb"),
    "pt": ("Portuguese", "pt"),
    "sv": ("Swedish", "sv"),
}


def load_translation_dict(lang_code: str) -> dict[str, str]:
    """Load translation dictionary for a language."""
    try:
        module = importlib.import_module(f"translation_dictionaries.{lang_code}")
    except ImportError as e:
        print(f"✗ Failed to load dictionary for {lang_code}: {e}")
        sys.exit(1)
    else:
        return module.TRANSLATIONS


def translate(text: str, translations: dict[str, str]) -> str:
    """Translate English text using the translation map.

    Sorts by length (longest first) to avoid partial replacements.
    """
    result = text
    for english in sorted(translations.keys(), key=len, reverse=True):
        translated = translations[english]
        result = result.replace(english, translated)
    return result


def translate_options_section(
    options_data: dict, translations_dict: dict[str, str]
) -> int:
    """Translate the options section in-place.

    Returns count of translated strings.
    """
    count = 0
    init_step = options_data.get("step", {}).get("init", {})

    # Translate title
    if "title" in init_step:
        init_step["title"] = translate(init_step["title"], translations_dict)
        count += 1

    # Translate description
    if "description" in init_step:
        init_step["description"] = translate(init_step["description"], translations_dict)
        count += 1

    # Translate data labels
    for key, value in init_step.get("data", {}).items():
        init_step["data"][key] = translate(value, translations_dict)
        count += 1

    # Translate data descriptions
    for key, value in init_step.get("data_description", {}).items():
        init_step["data_description"][key] = translate(value, translations_dict)
        count += 1

    return count


def generate_translations(lang_code: str, lang_name: str) -> bool:
    """Generate translations for a single language.

    Returns True on success, False on failure.
    """
    # Paths
    translations_dir = Path("custom_components/abb_fimer_pvi_vsn_rest/translations")
    en_file = translations_dir / "en.json"
    lang_file = translations_dir / f"{lang_code}.json"

    # Validate paths
    if not en_file.exists():
        print(f"✗ English source not found: {en_file}")
        return False

    if not lang_file.exists():
        print(f"✗ Language file not found: {lang_file}")
        return False

    # Load dictionaries
    translations_dict = load_translation_dict(lang_code)

    # Load English source
    with open(en_file, encoding="utf-8") as f:
        en_data = json.load(f)

    # Load target language (to preserve config/options sections)
    with open(lang_file, encoding="utf-8") as f:
        lang_data = json.load(f)

    # Translate all sensors from English
    sensor_count = 0
    for key, value in en_data["entity"]["sensor"].items():
        english_name = value["name"]
        translated_name = translate(english_name, translations_dict)
        lang_data["entity"]["sensor"][key] = {"name": translated_name}
        sensor_count += 1

    # Copy and translate options section from English
    options_count = 0
    if "options" in en_data:
        lang_data["options"] = copy.deepcopy(en_data["options"])
        options_count = translate_options_section(lang_data["options"], translations_dict)

    # Save updated translations
    with open(lang_file, "w", encoding="utf-8") as f:
        json.dump(lang_data, f, ensure_ascii=False, indent=2)

    print(
        f"✓ {lang_name} ({lang_code}) - {sensor_count} sensors, {options_count} options translated"
    )
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Home Assistant translations for ABB/FIMER PVI VSN REST"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate translations for all supported languages",
    )
    parser.add_argument(
        "--language",
        "-l",
        nargs="+",
        choices=list(LANGUAGE_CONFIG.keys()),
        help="Generate translations for specific language(s)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all supported languages",
    )

    args = parser.parse_args()

    # List mode
    if args.list:
        print("Supported languages:")
        for code, (name, _) in sorted(LANGUAGE_CONFIG.items()):
            print(f"  {code}: {name}")
        return

    # Determine which languages to process
    if args.all:
        languages = list(LANGUAGE_CONFIG.keys())
    elif args.language:
        languages = args.language
    else:
        parser.print_help()
        print("\nError: Specify --all or --language")
        sys.exit(1)

    # Generate translations
    print(f"Generating translations for {len(languages)} language(s)...\n")

    success_count = 0
    for lang_code in languages:
        lang_name, _ = LANGUAGE_CONFIG[lang_code]
        if generate_translations(lang_code, lang_name):
            success_count += 1

    print(f"\nCompleted: {success_count}/{len(languages)} languages")

    if success_count < len(languages):
        sys.exit(1)


if __name__ == "__main__":
    main()
