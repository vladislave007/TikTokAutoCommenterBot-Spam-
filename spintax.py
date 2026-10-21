import re
import random

def spin(template: str, target_user: str = None) -> str:
    """
    Recursively resolves {option1|option2|...} Spintax syntax
    and injects @{target_user} into the generated phrase.
    
    Supports:
      - Deeply nested Spintax: {a|{b|c}}
      - Target user injection: @{user} or {user}
      - Automatic whitespace and punctuation cleanup
    """
    if not template:
        return ""

    text = template

    # 1. Inject or remove @{user} / {user} placeholder first
    if target_user:
        clean_user = re.sub(r'[@\s]+', '', str(target_user)).strip()
        if clean_user:
            text = text.replace("@{user}", f"@{clean_user}").replace("{user}", clean_user)
        else:
            text = text.replace("@{user}", "").replace("{user}", "")
    else:
        text = text.replace("@{user}", "").replace("{user}", "")

    # 2. Resolve {a|b|c} Spintax recursively
    pattern = re.compile(r'\{([^{}]+)\}')
    for _ in range(10):
        if not pattern.search(text):
            break
        text = pattern.sub(lambda m: random.choice(m.group(1).split('|')), text)

    # 3. Clean double spaces and trim
    text = re.sub(r'\s+', ' ', text).strip()
    return text
