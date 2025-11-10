import uuid
def short_id():
    return uuid.uuid4().hex[:8]

