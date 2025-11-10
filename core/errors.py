class JarvisError(Exception):
    pass

class MemoryWriteError(JarvisError):
    pass

class MemoryReadError(JarvisError):
    pass

class IntentError(JarvisError):
    pass

