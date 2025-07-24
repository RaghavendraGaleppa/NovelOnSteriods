# test/test_translators/test_models_mock.py
import json
import pytest
import datetime
from unittest.mock import Mock, patch, MagicMock
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from nos.translators.models import Translator
from nos.config import secrets
from nos.schemas.translator_schemas import LLMCallResponseSchema

class TestTranslatorCallProviderMocked:
    """Fast, cheap mock tests for core functionality"""
    
    @patch('nos.translators.models.OpenAI')
    def test_call_provider_text_response_mocked(self, mock_openai):
        """Test call_provider with mocked OpenAI response"""
        # Setup mock response
        mock_choice = Choice(
            index=0,
            message=ChatCompletionMessage(
                role="assistant",
                content="Hello, how can I help you?"
            ),
            finish_reason="stop"
        )
        
        mock_completion = ChatCompletion(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-3.5-turbo",
            choices=[mock_choice],
            usage=CompletionUsage(
                prompt_tokens=10,
                completion_tokens=8,
                total_tokens=18
            )
        )
        
        mock_response = Mock()
        mock_response.headers = {
            'x-ratelimit-remaining-requests': '100',
            'x-ratelimit-remaining-tokens': '5000'
        }
        mock_response.parse.return_value = mock_completion
        
        mock_client = Mock()
        mock_client.chat.completions.with_raw_response.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Test
        translator = Translator(secrets.providers)
        response = translator.call_provider(
            user_prompt="Hello",
            system_prompt="You are helpful",
            temperature=0.1,
            max_tokens=100
        )
        
        # Verify
        assert isinstance(response, LLMCallResponseSchema)
        assert response.response_content == "Hello, how can I help you?"
        assert response.input_tokens == 10
        assert response.output_tokens == 8
        assert response.remaining_requests == 100
        assert response.remaining_tokens == 5000

    @patch('nos.translators.models.OpenAI')
    def test_call_provider_json_response_mocked(self, mock_openai):
        """Test JSON response parsing with mocked data"""
        mock_choice = Choice(
            index=0,
            message=ChatCompletionMessage(
                role="assistant",
                content='{"greeting": "Hello World"}'
            ),
            finish_reason="stop"
        )
        
        mock_completion = ChatCompletion(
            id="test-id",
            object="chat.completion", 
            created=1234567890,
            model="gpt-3.5-turbo",
            choices=[mock_choice],
            usage=CompletionUsage(prompt_tokens=5, completion_tokens=3, total_tokens=8)
        )
        
        mock_response = Mock()
        mock_response.headers = {'x-ratelimit-remaining-requests': '99', 'x-ratelimit-remaining-tokens': '4995'}
        mock_response.parse.return_value = mock_completion
        
        mock_client = Mock()
        mock_client.chat.completions.with_raw_response.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        translator = Translator(secrets.providers)
        response = translator.call_provider(
            user_prompt="Generate JSON",
            response_format={"type": "json"}
        )
        
        assert isinstance(response.response_content, dict)
        assert response.response_content["greeting"] == "Hello World"

    @patch('nos.translators.models.OpenAI')
    def test_error_handling_mocked(self, mock_openai):
        """Test error scenarios with mocked exceptions"""
        from openai import RateLimitError
        
        mock_client = Mock()
        mock_client.chat.completions.with_raw_response.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=Mock(status_code=429),
            body=None
        )
        mock_openai.return_value = mock_client
        
        translator = Translator(secrets.providers)
        
        with pytest.raises(RateLimitError):
            translator.call_provider(user_prompt="Test")


class TestTranslatorIntegration:
    """Minimal integration tests for real API connectivity"""
    
    @pytest.mark.integration
    def test_api_connectivity_health_check(self):
        """Lightweight test to verify API keys and connectivity work"""
        translator = Translator(secrets.providers)
        
        # Use a very simple, cheap prompt
        response = translator.call_provider(
            user_prompt="Hi",
            max_tokens=5  # Keep it minimal to reduce cost
        )
        
        # Just verify we got a real response
        assert isinstance(response, LLMCallResponseSchema)
        assert response.response_content is not None
        assert response.input_tokens is not None
        assert response.output_tokens is not None

    @pytest.mark.integration
    @pytest.mark.skipif(len(secrets.providers) < 2, reason="Need multiple providers")
    def test_provider_switching_integration(self):
        """Test that provider switching actually works with real APIs"""
        translator = Translator(secrets.providers)
        
        # Test first provider
        response1 = translator.call_provider(user_prompt="Hi", max_tokens=5)
        provider1_name = translator.current_provider.name
        
        # Switch and test second provider  
        translator.switch_providers()
        response2 = translator.call_provider(user_prompt="Hi", max_tokens=5)
        provider2_name = translator.current_provider.name
        
        # Verify switching worked
        assert provider1_name != provider2_name
        assert isinstance(response1, LLMCallResponseSchema)
        assert isinstance(response2, LLMCallResponseSchema)