from enum import Enum

class TranlsationStatus(Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    

class TranslationEntityType(Enum):
    TAGS = "tags"