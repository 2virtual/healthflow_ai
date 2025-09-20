# app/validate_symptoms.py
import json
import sys
from pathlib import Path

def validate_symptoms_file():
    # Updated path to match your current structure
    file_path = Path(__file__).parent / "endpoints" / "data" / "symptoms.json"
    
    print(f"🔍 Validating {file_path}...")

    # Check if file exists
    if not file_path.exists():
        print(f"❌ ERROR: {file_path} not found!")
        sys.exit(1)

    # Check if it's valid JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        sys.exit(1)

    # Basic schema check
    required_keys = {"id", "category", "keywords", "response"}
    errors = []

    for i, rule in enumerate(data):
        missing = required_keys - rule.keys()
        if missing:
            errors.append(f"Rule {i}: missing keys {missing}")

        if not isinstance(rule.get("keywords"), list):
            errors.append(f"Rule {i}: 'keywords' must be a list")

        if not isinstance(rule.get("response"), str):
            if isinstance(rule.get("response"), dict):
                pass  # OK if multilingual
            else:
                errors.append(f"Rule {i}: 'response' must be a string or object")

    if errors:
        for err in errors:
            print(f"❌ {err}")
        sys.exit(1)

    print(f"✅ {len(data)} symptom rules validated successfully.")

if __name__ == "__main__":
    validate_symptoms_file()
