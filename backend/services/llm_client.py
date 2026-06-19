"""LLM client for Ollama/LM Studio integration."""

import logging
import time
from typing import Optional, List, Dict, Any
import uuid

import httpx
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)

DTC_FALLBACKS = {
    "P0300": "Random/Multiple Cylinder Misfire Detected - Check spark plugs, ignition coils, and fuel injectors.",
    "P0301": "Cylinder 1 Misfire Detected - Inspect spark plug and ignition coil for cylinder 1.",
    "P0302": "Cylinder 2 Misfire Detected - Inspect spark plug and ignition coil for cylinder 2.",
    "P0303": "Cylinder 3 Misfire Detected - Inspect spark plug and ignition coil for cylinder 3.",
    "P0304": "Cylinder 4 Misfire Detected - Inspect spark plug and ignition coil for cylinder 4.",
    "P0420": "Catalyst System Efficiency Below Threshold (Bank 1) - Check catalytic converter and oxygen sensors.",
    "P0430": "Catalyst System Efficiency Below Threshold (Bank 2) - Check catalytic converter and oxygen sensors.",
    "P0171": "System Too Lean (Bank 1) - Check for vacuum leaks, mass air flow sensor, fuel pressure.",
    "P0172": "System Too Rich (Bank 1) - Check fuel injectors, oxygen sensors, mass air flow sensor.",
    "P0440": "Evaporative Emission Control System Malfunction - Check gas cap, EVAP system for leaks.",
    "P0442": "Evaporative Emission Control System Leak Detected (small leak) - Check vapor canister and lines.",
    "P0455": "Evaporative Emission Control System Leak Detected (large leak) - Check gas cap and EVAP system.",
    "P0500": "Vehicle Speed Sensor Malfunction - Check VSS sensor and wiring.",
    "P0700": "Transmission Control System Malfunction - Check transmission fluid, shift solenoids.",
    "P0128": "Coolant Thermostat Temperature Below Regulating Temperature - Replace thermostat.",
}


class Message(BaseModel):
    """Chat message."""

    role: str  # "system", "user", "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str
    messages: List[Message]
    temperature: float = 0.3
    max_tokens: Optional[int] = None
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class CircuitBreaker:
    """Circuit breaker for LLM calls."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning("Circuit breaker opened - LLM calls will fail for 60s")

    def record_success(self) -> None:
        """Record a success and reset."""
        self.failures = 0
        self.state = "closed"

    def can_attempt(self) -> bool:
        """Check if a call should be attempted."""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker half-open - attempting LLM call")
                return True
            return False

        # half-open - allow one attempt
        return True


circuit_breaker = CircuitBreaker()


class LLMClient:
    """Async HTTP client for Ollama/LM Studio API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "llama3.1:8b",
        temperature: float = 0.3,
        timeout: int = 120,
    ):
        self.base_url = (
            str(settings.LM_STUDIO_URL)
            if settings.LM_STUDIO_URL
            else (base_url or "http://localhost:1234/v1")
        )
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request."""
        if not circuit_breaker.can_attempt():
            logger.warning("Circuit breaker open - returning fallback response")
            return self._fallback_response("Circuit breaker open")

        request_data = ChatCompletionRequest(
            model=self.model,
            messages=[Message(role=m["role"], content=m["content"]) for m in messages],
            temperature=temperature or self.temperature,
            max_tokens=max_tokens,
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=request_data.model_dump()
                )
                response.raise_for_status()

                data = response.json()
                circuit_breaker.record_success()

                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data.get("model", self.model),
                    "usage": data.get("usage", {}),
                    "id": data.get("id", str(uuid.uuid4())),
                }
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            circuit_breaker.record_failure()
            return self._fallback_response(str(e))

    def _fallback_response(self, error: str) -> Dict[str, Any]:
        """Return a fallback response when LLM is unavailable."""
        return {
            "content": f"AI service temporarily unavailable. Please try again later. (Error: {error})",
            "model": self.model,
            "usage": {},
            "id": str(uuid.uuid4()),
            "fallback": True,
        }

    def get_fallback_for_dtc(self, dtc_code: str) -> Optional[str]:
        """Get canned fallback response for common DTC codes."""
        return DTC_FALLBACKS.get(dtc_code.upper())

    async def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate completion from prompt."""
        if not circuit_breaker.can_attempt():
            return {
                "content": "AI service temporarily unavailable",
                "model": self.model,
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/completions",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "temperature": temperature or self.temperature,
                        "max_tokens": max_tokens,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                circuit_breaker.record_success()

                data = response.json()
                return {
                    "content": data.get("choices", [{}])[0].get("text", ""),
                    "model": data.get("model", self.model),
                    "usage": data.get("usage", {}),
                }
        except Exception as e:
            logger.error(f"LLM generate failed: {e}")
            circuit_breaker.record_failure()
            return {
                "content": "AI service temporarily unavailable",
                "model": self.model,
            }

    async def embeddings(self, text: str) -> List[float]:
        """Get embeddings for text."""
        if not circuit_breaker.can_attempt():
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json={"model": self.model, "input": text},
                )
                response.raise_for_status()
                circuit_breaker.record_success()

                data = response.json()
                return data.get("data", [{}])[0].get("embedding", [])
        except Exception as e:
            logger.error(f"LLM embeddings failed: {e}")
            circuit_breaker.record_failure()
            return []

    async def health_check(self) -> bool:
        """Check if LLM service is available."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/models")
                if response.status_code == 200:
                    circuit_breaker.record_success()
                return response.status_code == 200
        except Exception:
            circuit_breaker.record_failure()
            return False

    def get_circuit_state(self) -> str:
        """Get current circuit breaker state."""
        return circuit_breaker.state


class LLMError(Exception):
    """Base exception for LLM errors."""

    pass


class LLMTimeoutError(LLMError):
    """Timeout error."""

    pass


_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(model=settings.DEFAULT_LLM_MODEL)
    return _llm_client
