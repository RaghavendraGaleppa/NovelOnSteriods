from pydantic import BaseModel, Field
from typing import ClassVar

from nos.schemas.enums import TranslationEntityType
from nos.schemas.mixins import DBFuncMixin


class TranslationEntity(DBFuncMixin):
    """ The translation entity is a collection which is basically like a key value store for word/words that occur very commonly withing the novel or its description. An example of this is the tags of the novel."""

    _collection_name: ClassVar[str] = "translation_entities"

    key: str = Field(description="The key of the translation entity. This will in raw chinese")
    value: str = Field(description="The translated value of the key")
    type: TranslationEntityType = Field(description="The type of the translation entity")
