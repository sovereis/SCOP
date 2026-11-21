"""Shared signup validation, independent of Workspace and storage."""
import json
import re

def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate field")
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError("Invalid JSON constant")

def validate_signup(raw):
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys, parse_constant=reject_constant)
    if not isinstance(value, dict) or set(value) != {'email', 'tool', 'problem', 'consent'}:
        raise ValueError('Invalid fields')
    for name, maximum in [('email', 254), ('tool', 120), ('problem', 2000)]:
        text = value[name]
        if (not isinstance(text, str) or not 1 <= len(text.strip()) <= maximum
                or any(ord(char) < 32 and char not in '\n\t' for char in text)
                or any(0xD800 <= ord(char) <= 0xDFFF for char in text)):
            raise ValueError('Invalid text')
        value[name] = text.strip()
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", value['email']):
        raise ValueError('Invalid email')
    if value['consent'] is not True:
        raise ValueError('Consent required')
    return value

