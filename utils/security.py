def mask_token(s: str, keep=4):
    if not s: return s
    return s[:keep] + "****" + s[-keep:]

