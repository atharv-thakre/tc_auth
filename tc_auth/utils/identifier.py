def get_identifier_type(identifier: str) -> str:
    if not identifier or not isinstance(identifier, str):
        return "handle"

    identifier = identifier.strip()

    if "@" in identifier:
        return "email"

    return "handle"


def normalize_identifier(identifier: str) -> str:
    if not identifier or not isinstance(identifier, str):
        return ""

    return identifier.strip().lower()
