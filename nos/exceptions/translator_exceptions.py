from nos.schemas.secrets_schema import Provider

class LLMNoResponseError(Exception):
    """
    This exception is raised when the llm does not return a response
    """
    def __init__(self, provider: Provider, model_idx: int):
        self.error_message = f"No response from provider: {provider}, model: {provider.model_names[model_idx]}"

    def __str__(self):
        return self.error_message


class LLMNoUsageError(Exception):
    """
    This exception is raised when the llm does not return usage information
    """
    def __init__(self, provider: Provider, model_idx: int):
        self.error_message = f"No usage information from provider: {provider}, model: {provider.model_names[model_idx]}"

    def __str__(self):
        return self.error_message


class NoProvidersAvailable(Exception):
    """
    This exception is raised when there are no providers available to switch to
    """
    def __init__(self):
        self.error_message = "No providers available to switch to"

    def __str__(self):
        return self.error_message