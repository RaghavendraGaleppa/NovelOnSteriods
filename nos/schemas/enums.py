from enum import Enum

class TranlsationStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    

class TranslationEntityType(str, Enum):
    TAGS = "tags"