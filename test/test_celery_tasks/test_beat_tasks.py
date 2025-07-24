import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import List
from pymongo.database import Database
from logging import Logger

from nos.celery_tasks.beat_tasks import beat_update_tags_of_novels
from nos.schemas.scraping_schema import NovelData
from nos.schemas.translation_entities_schema import TranslationEntity
from nos.schemas.enums import TranslationEntityType
from nos.schemas.translator_schemas import LLMCallResponseSchema


class TestBeatUpdateTagsOfNovels:
    """Test cases for the beat_update_tags_of_novels celery task"""

    def setup_method(self):
        """Setup test data before each test"""
        # Sample novel data with raw tags
        self.sample_novels = [
            {
                "source_name": "1qxs",
                "novel_source_id": "test1",
                "novel_url": "http://test1.com",
                "chapter_list_url": "http://test1.com/chapters",
                "image_url": "http://test1.com/image.jpg",
                "title_raw": "测试小说1",
                "author_raw": "测试作者1",
                "description_raw": "测试描述1",
                "classification_raw": ["玄幻"],
                "tags_raw": ["穿越", "修仙", "热血"],
                "fingerprint": "test1_fingerprint",
                "all_data_parsed": False
            },
            {
                "source_name": "1qxs", 
                "novel_source_id": "test2",
                "novel_url": "http://test2.com",
                "chapter_list_url": "http://test2.com/chapters",
                "image_url": "http://test2.com/image.jpg",
                "title_raw": "测试小说2",
                "author_raw": "测试作者2",
                "description_raw": "测试描述2",
                "classification_raw": ["都市"],
                "tags_raw": ["重生", "修仙", "系统"],
                "fingerprint": "test2_fingerprint",
                "all_data_parsed": False
            }
        ]

        # Sample existing translation entities
        self.existing_translations = [
            {
                "key": "修仙",
                "value": "Cultivation",
                "type": TranslationEntityType.TAGS.value
            }
        ]

    def test_no_novels_with_missing_tags(self, db: Database, logger: Logger):
        """Test when there are no novels with missing tags"""
        
        # Setup: Create novels with tags already present
        novels_with_tags = []
        for novel_data in self.sample_novels:
            novel_data["tags"] = ["Time Travel", "Cultivation", "Hot-blooded"]
            novel = NovelData(**novel_data)
            novel.update(db)
            novels_with_tags.append(novel)

        # Execute
        result = beat_update_tags_of_novels()

        # Assert
        assert result == ({}, {})  # Both dictionaries should be empty

    def test_novels_with_missing_tags_no_existing_translations(self, db: Database, logger: Logger):
        """Test when novels have missing tags and no existing translations"""
        
        # Setup: Create novels without tags
        novels_without_tags = []
        for novel_data in self.sample_novels:
            novel = NovelData(**novel_data)
            novel.update(db)
            novels_without_tags.append(novel)

        # Mock the translator
        mock_translation_response = {
            "穿越": "Time Travel",
            "修仙": "Cultivation", 
            "热血": "Hot-blooded",
            "重生": "Rebirth",
            "系统": "System"
        }

        mock_llm_response = LLMCallResponseSchema(
            response_content=mock_translation_response,
            input_tokens=100,
            output_tokens=50,
            remaining_requests=99,
            remaining_tokens=4950
        )

        with patch('nos.celery_tasks.beat_tasks.Translator') as mock_translator_class:
            mock_translator = Mock()
            mock_translator.run_translation.return_value = Mock(llm_call_metadata=mock_llm_response)
            mock_translator_class.return_value = mock_translator

            # Execute
            all_tags_kv, untranslated_kv = beat_update_tags_of_novels()

        # Assert
        assert len(all_tags_kv) == 5  # All unique tags
        assert len(untranslated_kv) == 5  # All were untranslated initially
        assert all_tags_kv["穿越"] == "Time Travel"
        assert all_tags_kv["修仙"] == "Cultivation"
        assert all_tags_kv["热血"] == "Hot-blooded"
        assert all_tags_kv["重生"] == "Rebirth"
        assert all_tags_kv["系统"] == "System"

        # Verify novels were updated with translated tags
        updated_novels = NovelData.load(db=db, query={"tags": {"$exists": True, "$ne": None, "$ne": []}}, many=True)
        assert len(updated_novels) == 2
        
        for novel in updated_novels:
            assert novel.tags is not None
            assert len(novel.tags) > 0
            assert all(tag in mock_translation_response.values() for tag in novel.tags)

        # Verify translation entities were created
        translation_entities = TranslationEntity.load(
            db=db, 
            query={"type": TranslationEntityType.TAGS.value}, 
            many=True
        )
        assert len(translation_entities) == 5

    def test_novels_with_mixed_translation_state(self, db: Database, logger: Logger):
        """Test when some tags are already translated and others are not"""
        
        # Setup: Create existing translation entities
        existing_entity = TranslationEntity(**self.existing_translations[0])
        existing_entity.update(db)

        # Setup: Create novels without tags
        novels_without_tags = []
        for novel_data in self.sample_novels:
            novel = NovelData(**novel_data)
            novel.update(db)
            novels_without_tags.append(novel)

        # Mock translator for new tags only
        mock_translation_response = {
            "穿越": "Time Travel",
            "热血": "Hot-blooded", 
            "重生": "Rebirth",
            "系统": "System"
        }

        mock_llm_response = LLMCallResponseSchema(
            response_content=mock_translation_response,
            input_tokens=80,
            output_tokens=40,
            remaining_requests=98,
            remaining_tokens=4920
        )

        with patch('nos.celery_tasks.beat_tasks.Translator') as mock_translator_class:
            mock_translator = Mock()
            mock_translator.run_translation.return_value = Mock(llm_call_metadata=mock_llm_response)
            mock_translator_class.return_value = mock_translator

            # Execute
            all_tags_kv, untranslated_kv = beat_update_tags_of_novels()

        # Assert
        assert len(all_tags_kv) == 5  # All unique tags
        assert len(untranslated_kv) == 4  # Only new untranslated tags
        assert all_tags_kv["修仙"] == "Cultivation"  # From existing translation
        assert all_tags_kv["穿越"] == "Time Travel"   # From new translation
        
        # Verify translator was called only for untranslated tags
        mock_translator.run_translation.assert_called_once()
        called_tags = mock_translator.run_translation.call_args[0][0]
        assert "修仙" not in called_tags  # Should not re-translate existing
        assert set(called_tags) == {"穿越", "热血", "重生", "系统"}

    def test_novels_with_empty_tags_raw(self, db: Database, logger: Logger):
        """Test when novels have empty tags_raw lists"""
        
        # Setup: Create novels with empty tags_raw
        for novel_data in self.sample_novels:
            novel_data["tags_raw"] = []
            novel = NovelData(**novel_data)
            novel.update(db)

        # Execute
        result = beat_update_tags_of_novels()

        # Assert
        assert result == ({}, {})  # Should return empty dictionaries

    def test_novels_with_null_tags_field(self, db: Database, logger: Logger):
        """Test when novels have tags field set to None"""
        
        # Setup: Create novels with tags set to None
        novels_with_null_tags = []
        for novel_data in self.sample_novels:
            novel_data["tags"] = None
            novel = NovelData(**novel_data)
            novel.update(db)
            novels_with_null_tags.append(novel)

        # Mock translator
        mock_translation_response = {
            "穿越": "Time Travel",
            "修仙": "Cultivation",
            "热血": "Hot-blooded",
            "重生": "Rebirth", 
            "系统": "System"
        }

        mock_llm_response = LLMCallResponseSchema(
            response_content=mock_translation_response,
            input_tokens=100,
            output_tokens=50,
            remaining_requests=99,
            remaining_tokens=4950
        )

        with patch('nos.celery_tasks.beat_tasks.Translator') as mock_translator_class:
            mock_translator = Mock()
            mock_translator.run_translation.return_value = Mock(llm_call_metadata=mock_llm_response)
            mock_translator_class.return_value = mock_translator

            # Execute
            all_tags_kv, untranslated_kv = beat_update_tags_of_novels()

        # Assert that novels with null tags are processed
        assert len(all_tags_kv) == 5
        assert len(untranslated_kv) == 5

        # Verify novels were updated
        updated_novels = NovelData.load(db=db, query={"tags": {"$ne": None, "$ne": []}}, many=True)
        assert len(updated_novels) == 2

    def test_translator_error_handling(self, db: Database, logger: Logger):
        """Test error handling when translator fails"""
        
        # Setup: Create novels without tags
        for novel_data in self.sample_novels:
            novel = NovelData(**novel_data)
            novel.update(db)

        # Mock translator to raise an exception
        with patch('nos.celery_tasks.beat_tasks.Translator') as mock_translator_class:
            mock_translator = Mock()
            mock_translator.run_translation.side_effect = Exception("Translation service unavailable")
            mock_translator_class.return_value = mock_translator

            # Execute and expect exception
            with pytest.raises(Exception) as exc_info:
                beat_update_tags_of_novels()
            
            assert "Translation service unavailable" in str(exc_info.value)

    def test_incomplete_translation_response(self, db: Database, logger: Logger):
        """Test when translator returns incomplete response"""
        
        # Setup: Create novels without tags
        for novel_data in self.sample_novels:
            novel = NovelData(**novel_data)
            novel.update(db)

        # Mock translator with incomplete response (missing some tags)
        mock_translation_response = {
            "穿越": "Time Travel",
            "修仙": "Cultivation"
            # Missing "热血", "重生", "系统"
        }

        mock_llm_response = LLMCallResponseSchema(
            response_content=mock_translation_response,
            input_tokens=100,
            output_tokens=50,
            remaining_requests=99,
            remaining_tokens=4950
        )

        with patch('nos.celery_tasks.beat_tasks.Translator') as mock_translator_class:
            mock_translator = Mock()
            mock_translator.run_translation.return_value = Mock(llm_call_metadata=mock_llm_response)
            mock_translator_class.return_value = mock_translator

            # Execute and expect KeyError due to missing translations
            with pytest.raises(KeyError):
                beat_update_tags_of_novels()

    def test_duplicate_tag_handling(self, db: Database, logger: Logger):
        """Test handling of duplicate tags across novels"""
        
        # Setup: Create novels with overlapping tags
        novel_data_1 = self.sample_novels[0].copy()
        novel_data_1["tags_raw"] = ["穿越", "修仙"]
        
        novel_data_2 = self.sample_novels[1].copy()
        novel_data_2["tags_raw"] = ["修仙", "热血"]  # "修仙" is duplicate

        novel1 = NovelData(**novel_data_1)
        novel2 = NovelData(**novel_data_2)
        novel1.update(db)
        novel2.update(db)

        # Mock translator
        mock_translation_response = {
            "穿越": "Time Travel",
            "修仙": "Cultivation",
            "热血": "Hot-blooded"
        }

        mock_llm_response = LLMCallResponseSchema(
            response_content=mock_translation_response,
            input_tokens=60,
            output_tokens=30,
            remaining_requests=99,
            remaining_tokens=4970
        )

        with patch('nos.celery_tasks.beat_tasks.Translator') as mock_translator_class:
            mock_translator = Mock()
            mock_translator.run_translation.return_value = Mock(llm_call_metadata=mock_llm_response)
            mock_translator_class.return_value = mock_translator

            # Execute
            all_tags_kv, untranslated_kv = beat_update_tags_of_novels()

        # Assert that unique tags are handled correctly
        assert len(all_tags_kv) == 3  # Should have 3 unique tags
        assert all_tags_kv["修仙"] == "Cultivation"
        
        # Verify translator was called only once with unique tags
        mock_translator.run_translation.assert_called_once()
        called_tags = mock_translator.run_translation.call_args[0][0]
        assert len(called_tags) == 3  # Should only translate unique tags

    @patch('nos.celery_tasks.beat_tasks.secrets')
    def test_configuration_dependencies(self, mock_secrets, db: Database, logger: Logger):
        """Test that the function uses proper configuration"""
        
        # Setup mock secrets
        mock_secrets.providers = ["test_provider"]
        
        # Setup: Create novels without tags
        for novel_data in self.sample_novels:
            novel = NovelData(**novel_data)
            novel.update(db)

        # Mock translator
        mock_translation_response = {"穿越": "Time Travel", "修仙": "Cultivation", "热血": "Hot-blooded", "重生": "Rebirth", "系统": "System"}
        mock_llm_response = LLMCallResponseSchema(
            response_content=mock_translation_response,
            input_tokens=100,
            output_tokens=50,
            remaining_requests=99,
            remaining_tokens=4950
        )

        with patch('nos.celery_tasks.beat_tasks.Translator') as mock_translator_class:
            mock_translator = Mock()
            mock_translator.run_translation.return_value = Mock(llm_call_metadata=mock_llm_response)
            mock_translator_class.return_value = mock_translator

            # Execute
            beat_update_tags_of_novels()

            # Verify Translator was initialized with correct providers
            mock_translator_class.assert_called_once_with(providers=["test_provider"])
            mock_translator.run_translation.assert_called_once_with(
                ["穿越", "修仙", "热血", "重生", "系统"], 
                "tag_translation"
            )


class TestBeatUpdateTagsOfNovelsIntegration:
    """Integration tests for beat_update_tags_of_novels that use real translation services"""

    @pytest.mark.integration
    def test_real_translation_small_batch(self, db: Database, logger: Logger):
        """Integration test with real translation service using minimal tags to reduce costs"""
        
        # Setup: Create a single novel with minimal tags for cost efficiency
        minimal_novel_data = {
            "source_name": "1qxs",
            "novel_source_id": "integration_test_1",
            "novel_url": "http://integration-test.com",
            "chapter_list_url": "http://integration-test.com/chapters",
            "image_url": "http://integration-test.com/image.jpg",
            "title_raw": "集成测试小说",
            "author_raw": "测试作者",
            "description_raw": "集成测试描述",
            "classification_raw": ["测试"],
            "tags_raw": ["修仙"],  # Only one tag to minimize cost
            "fingerprint": "integration_test_fingerprint",
            "all_data_parsed": False
        }
        
        novel = NovelData(**minimal_novel_data)
        novel.update(db)

        # Execute with real translation
        all_tags_kv, untranslated_kv = beat_update_tags_of_novels()

        # Assert
        assert len(all_tags_kv) == 1
        assert "修仙" in all_tags_kv
        assert all_tags_kv["修仙"] is not None  # Should have real translation
        assert isinstance(all_tags_kv["修仙"], str)
        assert len(all_tags_kv["修仙"]) > 0

        # Verify the novel was updated with real translation
        updated_novel = NovelData.load(db=db, query={"novel_source_id": "integration_test_1"})
        assert updated_novel is not None
        assert updated_novel.tags is not None
        assert len(updated_novel.tags) == 1
        assert updated_novel.tags[0] == all_tags_kv["修仙"]

        # Verify translation entity was created
        translation_entity = TranslationEntity.load(
            db=db,
            query={"key": "修仙", "type": TranslationEntityType.TAGS.value}
        )
        assert translation_entity is not None
        assert translation_entity.value == all_tags_kv["修仙"]

        logger.info(f"Real translation result: 修仙 -> {all_tags_kv['修仙']}")

    @pytest.mark.integration
    def test_real_translation_with_existing_entities(self, db: Database, logger: Logger):
        """Integration test that combines real translation with existing translation entities"""
        
        # Setup: Create an existing translation entity
        existing_entity = TranslationEntity(
            key="玄幻",
            value="Fantasy",
            type=TranslationEntityType.TAGS
        )
        existing_entity.update(db)

        # Setup: Create a novel with one existing and one new tag
        novel_data = {
            "source_name": "1qxs",
            "novel_source_id": "integration_test_2",
            "novel_url": "http://integration-test-2.com",
            "chapter_list_url": "http://integration-test-2.com/chapters", 
            "image_url": "http://integration-test-2.com/image.jpg",
            "title_raw": "集成测试小说2",
            "author_raw": "测试作者2",
            "description_raw": "集成测试描述2",
            "classification_raw": ["测试"],
            "tags_raw": ["玄幻", "都市"],  # One existing, one new
            "fingerprint": "integration_test_2_fingerprint",
            "all_data_parsed": False
        }
        
        novel = NovelData(**novel_data)
        novel.update(db)

        # Execute
        all_tags_kv, untranslated_kv = beat_update_tags_of_novels()

        # Assert
        assert len(all_tags_kv) == 2
        assert all_tags_kv["玄幻"] == "Fantasy"  # From existing entity
        assert "都市" in all_tags_kv
        assert all_tags_kv["都市"] is not None  # Should have real translation
        assert len(untranslated_kv) == 1  # Only "都市" was newly translated
        assert "都市" in untranslated_kv

        # Verify the novel was updated correctly
        updated_novel = NovelData.load(db=db, query={"novel_source_id": "integration_test_2"})
        assert updated_novel is not None
        assert updated_novel.tags is not None
        assert len(updated_novel.tags) == 2
        assert "Fantasy" in updated_novel.tags
        assert all_tags_kv["都市"] in updated_novel.tags

        logger.info(f"Mixed translation result: 玄幻 -> Fantasy (existing), 都市 -> {all_tags_kv['都市']} (new)")

    @pytest.mark.integration
    @pytest.mark.skipif(
        "not hasattr(__import__('nos.config', fromlist=['secrets']).secrets, 'providers') or "
        "len(__import__('nos.config', fromlist=['secrets']).secrets.providers) == 0",
        reason="No translation providers configured"
    )
    def test_real_translation_api_connectivity(self, db: Database, logger: Logger):
        """Lightweight integration test to verify API connectivity"""
        
        # Setup: Create a novel with a single common tag
        connectivity_novel_data = {
            "source_name": "1qxs",
            "novel_source_id": "connectivity_test",
            "novel_url": "http://connectivity-test.com",
            "chapter_list_url": "http://connectivity-test.com/chapters",
            "image_url": "http://connectivity-test.com/image.jpg", 
            "title_raw": "连接测试",
            "author_raw": "测试",
            "description_raw": "连接测试",
            "classification_raw": ["测试"],
            "tags_raw": ["爱情"],  # Common tag that should translate well
            "fingerprint": "connectivity_test_fingerprint",
            "all_data_parsed": False
        }
        
        novel = NovelData(**connectivity_novel_data)
        novel.update(db)

        # Execute - this will use real APIs
        try:
            all_tags_kv, untranslated_kv = beat_update_tags_of_novels()
            
            # Basic connectivity verification
            assert isinstance(all_tags_kv, dict)
            assert isinstance(untranslated_kv, dict)
            assert len(all_tags_kv) > 0
            assert "爱情" in all_tags_kv
            
            # Verify translation quality (should be reasonable)
            translation = all_tags_kv["爱情"]
            assert isinstance(translation, str)
            assert len(translation.strip()) > 0
            assert translation.lower() in ["love", "romance", "romantic"]  # Expected translations
            
            logger.info(f"API connectivity verified: 爱情 -> {translation}")
            
        except Exception as e:
            pytest.fail(f"Integration test failed due to API connectivity issues: {str(e)}")

    @pytest.mark.integration 
    @pytest.mark.slow
    def test_real_translation_performance_benchmark(self, db: Database, logger: Logger):
        """Integration test to benchmark performance with multiple tags"""
        import time
        
        # Setup: Create novels with multiple tags to test batch processing
        performance_novels = [
            {
                "source_name": "1qxs",
                "novel_source_id": f"perf_test_{i}",
                "novel_url": f"http://perf-test-{i}.com",
                "chapter_list_url": f"http://perf-test-{i}.com/chapters",
                "image_url": f"http://perf-test-{i}.com/image.jpg",
                "title_raw": f"性能测试{i}",
                "author_raw": f"测试作者{i}",
                "description_raw": f"性能测试描述{i}",
                "classification_raw": ["测试"],
                "tags_raw": ["武侠", "历史", "军事"][:(i % 3) + 1],  # Varying number of tags
                "fingerprint": f"perf_test_{i}_fingerprint",
                "all_data_parsed": False
            }
            for i in range(3)  # Keep small for cost control
        ]
        
        for novel_data in performance_novels:
            novel = NovelData(**novel_data)
            novel.update(db)

        # Execute with timing
        start_time = time.time()
        all_tags_kv, untranslated_kv = beat_update_tags_of_novels()
        end_time = time.time()
        
        execution_time = end_time - start_time

        # Assert performance and correctness
        assert len(all_tags_kv) == 3  # Should have 3 unique tags
        assert execution_time < 30  # Should complete within 30 seconds
        assert all(isinstance(v, str) and len(v) > 0 for v in all_tags_kv.values())

        # Verify all novels were updated
        updated_novels = NovelData.load(
            db=db, 
            query={"novel_source_id": {"$regex": "^perf_test_"}}, 
            many=True
        )
        assert len(updated_novels) == 3
        assert all(novel.tags is not None and len(novel.tags) > 0 for novel in updated_novels)

        logger.info(f"Performance test completed in {execution_time:.2f}s with {len(all_tags_kv)} tags translated") 