import httpx

from app.config import settings


class OllamaClient:
    """Thin async wrapper around the Ollama REST API."""

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def generate(self, prompt: str) -> str:
        """Send a prompt to Ollama and return the generated text."""
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json().get("response", "")

    async def health_check(self) -> bool:
        """Return True if the Ollama service is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except httpx.HTTPError:
            return False


ollama_client = OllamaClient()
