from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VoiceOption:
    id: str
    name: str
    provider: str
    language: Optional[str] = None
    gender: Optional[str] = None
    preview_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSResult:
    status: str
    provider: str
    model: str
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    voice_id: Optional[str] = None
    characters_used: Optional[int] = None
    estimated_cost: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "audio_url": self.audio_url,
            "duration_seconds": self.duration_seconds,
            "voice_id": self.voice_id,
            "characters_used": self.characters_used,
            "estimated_cost": self.estimated_cost,
            "error": self.error,
            "metadata": self.metadata,
        }


class TTSProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def synthesize(self, text: str, voice_id: Optional[str] = None, model: Optional[str] = None, **kwargs: Any) -> TTSResult:
        raise NotImplementedError

    @abstractmethod
    async def list_voices(self, **kwargs: Any) -> List[VoiceOption]:
        raise NotImplementedError

    @abstractmethod
    def get_cost_estimate(self, text: str, model: Optional[str] = None, **kwargs: Any) -> float:
        raise NotImplementedError

    @abstractmethod
    def max_chars_per_request(self, model: Optional[str] = None) -> int:
        raise NotImplementedError
