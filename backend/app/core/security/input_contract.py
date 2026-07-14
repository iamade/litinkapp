"""
SEC-01: Untrusted-Input Contract — Prompt Injection Defense Layer

Defines trust boundaries between system (trusted) and user (untrusted) input,
with injection detection, sanitization, and validation at every AI prompt boundary.

KAN-377 / KAN-378 — SEC EPIC
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class TrustBoundary(Enum):
    """Defines the trust level of input sources."""
    SYSTEM = "system"       # Fully trusted: config, internal constants, hardcoded prompts
    INTERNAL = "internal"   # Semi-trusted: database content, generated content from our models
    USER = "user"           # Untrusted: direct user input, uploaded content, external API responses
    EXTERNAL = "external"   # Fully untrusted: third-party API responses, webhook payloads


@dataclass
class InputValidationResult:
    """Result of input validation against the untrusted-input contract."""
    is_valid: bool
    sanitized_text: str
    original_length: int
    sanitized_length: int
    warnings: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)
    trust_boundary: TrustBoundary = TrustBoundary.USER

    @property
    def was_modified(self) -> bool:
        return self.sanitized_text != self.original_text if hasattr(self, 'original_text') else self.original_length != self.sanitized_length

    @property
    def is_blocked(self) -> bool:
        return len(self.blocked_patterns) > 0


class InputContract:
    """
    SEC-01 Untrusted-Input Contract.

    Enforces boundaries between trusted and untrusted input at every AI prompt
    construction site. Detects and neutralizes prompt injection attempts including:
    - Delimiter injection (injecting fake system/user/assistant markers)
    - Role confusion (pretending to be the system or assistant)
    - Instruction override ("ignore previous instructions", "you are now...")
    - Context manipulation (injecting fake conversation history)
    - Token smuggling (encoding tricks to bypass filters)
    """

    # ── Injection patterns ──────────────────────────────────────────────

    # Delimiter injection: attempts to inject fake message boundaries
    DELIMITER_PATTERNS = [
        # OpenAI-style delimiters
        r'<\|im_start\|>',
        r'<\|im_end\|>',
        r'<\|system\|>',
        r'<\|user\|>',
        r'<\|assistant\|>',
        # Anthropic-style delimiters
        r'Human:\s*$',
        r'Assistant:\s*$',
        r'\n\nHuman:',
        r'\n\nAssistant:',
        # Generic role markers
        r'\[SYSTEM\]',
        r'\[USER\]',
        r'\[ASSISTANT\]',
        r'System:',
        r'User:',
        r'Assistant:',
        # XML-style injection
        r'<system>',
        r'</system>',
        r'<user>',
        r'</user>',
        r'<assistant>',
        r'</assistant>',
        r'<instruction>',
        r'</instruction>',
    ]

    # Instruction override: attempts to hijack the model's behavior
    INSTRUCTION_OVERRIDE_PATTERNS = [
        r'ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|messages?|context)',
        r'disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|messages?)',
        r'forget\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|messages?)',
        r'override\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?)',
        r'you\s+are\s+now\s+(a\s+)?(different|new)\s+(model|assistant|ai|bot|system)',
        r'you\s+are\s+no\s+longer\s+(an?\s+)?(assistant|ai|bot|helper)',
        r'pretend\s+you\s+are\s+(a\s+)?(different|someone\s+else|not\s+an?\s+ai)',
        r'act\s+as\s+if\s+you\s+are\s+(a\s+)?(different|unrestricted|unfiltered)',
        r'new\s+system\s+prompt\s*:',
        r'new\s+instructions?\s*:',
        r'your\s+new\s+(role|task|job|purpose)\s+is',
        r'from\s+now\s+on\s+you\s+(are|will\s+be|must)',
        r'do\s+not\s+follow\s+(your\s+)?(instructions?|guidelines?|rules?)',
        r'bypass\s+(your\s+)?(restrictions?|limitations?|filters?|safeguards?)',
        r'jailbreak',
        r'DAN\s+mode',
        r'developer\s+mode',
    ]

    # Role confusion: pretending to be the system
    ROLE_CONFUSION_PATTERNS = [
        r'I\s+am\s+(the\s+)?(system|developer|admin|administrator|owner|creator)',
        r'this\s+is\s+(the\s+)?(system|developer|admin)\s+speaking',
        r'system\s+message\s*:',
        r'system\s+prompt\s*:',
        r'internal\s+(message|instruction|directive)\s*:',
        r'urgent\s+system\s+(message|update|override)\s*:',
    ]

    # Context manipulation: injecting fake conversation
    CONTEXT_MANIPULATION_PATTERNS = [
        r'previous\s+(conversation|chat|messages?)\s+(was|were)\s+(about|regarding)',
        r'as\s+(we|you|I)\s+(discussed|agreed|established|decided)\s+(earlier|before|previously)',
        r'recall\s+(that|when)\s+(we|you|I)\s+(said|mentioned|discussed|agreed)',
        r'continuing\s+(our|the)\s+(previous|earlier)\s+(conversation|discussion)',
    ]

    # Token smuggling: encoding tricks
    TOKEN_SMUGGLING_PATTERNS = [
        r'\\x[0-9a-fA-F]{2}',           # Hex escapes
        r'\\u[0-9a-fA-F]{4}',           # Unicode escapes
        r'\\U[0-9a-fA-F]{8}',           # Long Unicode escapes
        r'&#x?[0-9a-fA-F]+;',           # HTML entities
        r'%[0-9a-fA-F]{2}',             # URL encoding
        r'\\[0]{2,}[0-9a-fA-F]+',       # Octal-style escapes
    ]

    # ── Validation methods ───────────────────────────────────────────────

    @classmethod
    def validate(
        cls,
        text: str,
        boundary: TrustBoundary = TrustBoundary.USER,
        max_length: int = 32000,
        strict: bool = False,
    ) -> InputValidationResult:
        """
        Validate and sanitize input against the untrusted-input contract.

        Args:
            text: The input text to validate
            boundary: Trust boundary of the input source
            max_length: Maximum allowed length (truncates if exceeded)
            strict: If True, block (return empty) on any injection pattern match

        Returns:
            InputValidationResult with sanitized text and validation details
        """
        if not text:
            return InputValidationResult(
                is_valid=True,
                sanitized_text="",
                original_length=0,
                sanitized_length=0,
                trust_boundary=boundary,
            )

        original_length = len(text)
        warnings: List[str] = []
        blocked_patterns: List[str] = []
        sanitized = text

        # System/internal input skips injection checks
        if boundary in (TrustBoundary.SYSTEM, TrustBoundary.INTERNAL):
            # Still apply basic sanitization
            sanitized = cls._basic_sanitize(sanitized)
            sanitized = cls._truncate(sanitized, max_length)
            return InputValidationResult(
                is_valid=True,
                sanitized_text=sanitized,
                original_length=original_length,
                sanitized_length=len(sanitized),
                trust_boundary=boundary,
            )

        # ── Phase 1: Detect injection patterns ──────────────────────────
        blocked_patterns = cls._detect_injection_patterns(sanitized)

        if blocked_patterns:
            logger.warning(
                f"[SEC-01] Injection patterns detected in {boundary.value} input: "
                f"{', '.join(blocked_patterns[:5])}"
            )
            if strict:
                return InputValidationResult(
                    is_valid=False,
                    sanitized_text="",
                    original_length=original_length,
                    sanitized_length=0,
                    warnings=[f"Input blocked: injection patterns detected"],
                    blocked_patterns=blocked_patterns,
                    trust_boundary=boundary,
                )

        # ── Phase 2: Neutralize injection patterns ───────────────────────
        sanitized = cls._neutralize_delimiters(sanitized)
        sanitized = cls._neutralize_instruction_overrides(sanitized)
        sanitized = cls._neutralize_role_confusion(sanitized)
        sanitized = cls._neutralize_context_manipulation(sanitized)
        sanitized = cls._neutralize_token_smuggling(sanitized)

        # ── Phase 3: Basic sanitization ──────────────────────────────────
        sanitized = cls._basic_sanitize(sanitized)

        # ── Phase 4: Length enforcement ──────────────────────────────────
        sanitized = cls._truncate(sanitized, max_length)

        if len(sanitized) < original_length:
            warnings.append(
                f"Input truncated/cleaned: {original_length} → {len(sanitized)} chars"
            )

        return InputValidationResult(
            is_valid=True,
            sanitized_text=sanitized,
            original_length=original_length,
            sanitized_length=len(sanitized),
            warnings=warnings,
            blocked_patterns=blocked_patterns,
            trust_boundary=boundary,
        )

    # ── Detection ────────────────────────────────────────────────────────

    @classmethod
    def _detect_injection_patterns(cls, text: str) -> List[str]:
        """Detect all injection patterns and return matched pattern descriptions."""
        detected: List[str] = []

        for pattern in cls.DELIMITER_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(f"delimiter:{pattern}")

        for pattern in cls.INSTRUCTION_OVERRIDE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(f"instruction_override:{pattern}")

        for pattern in cls.ROLE_CONFUSION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(f"role_confusion:{pattern}")

        for pattern in cls.CONTEXT_MANIPULATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(f"context_manipulation:{pattern}")

        for pattern in cls.TOKEN_SMUGGLING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(f"token_smuggling:{pattern}")

        return detected

    # ── Neutralization ───────────────────────────────────────────────────

    @classmethod
    def _neutralize_delimiters(cls, text: str) -> str:
        """Replace delimiter injection patterns with safe alternatives."""
        replacements = {
            r'<\|im_start\|>': '[START]',
            r'<\|im_end\|>': '[END]',
            r'<\|system\|>': '[system]',
            r'<\|user\|>': '[user]',
            r'<\|assistant\|>': '[assistant]',
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    @classmethod
    def _neutralize_instruction_overrides(cls, text: str) -> str:
        """Neutralize instruction override attempts by redacting key phrases."""
        for pattern in cls.INSTRUCTION_OVERRIDE_PATTERNS:
            text = re.sub(pattern, '[instruction_override_redacted]', text, flags=re.IGNORECASE)
        return text

    @classmethod
    def _neutralize_role_confusion(cls, text: str) -> str:
        """Neutralize role confusion attempts."""
        for pattern in cls.ROLE_CONFUSION_PATTERNS:
            text = re.sub(pattern, '[role_claim_redacted]', text, flags=re.IGNORECASE)
        return text

    @classmethod
    def _neutralize_context_manipulation(cls, text: str) -> str:
        """Neutralize context manipulation attempts."""
        for pattern in cls.CONTEXT_MANIPULATION_PATTERNS:
            text = re.sub(pattern, '[context_claim_redacted]', text, flags=re.IGNORECASE)
        return text

    @classmethod
    def _neutralize_token_smuggling(cls, text: str) -> str:
        """Neutralize token smuggling via encoding tricks."""
        # Remove hex/unicode escape sequences
        text = re.sub(r'\\x[0-9a-fA-F]{2}', '', text)
        text = re.sub(r'\\u[0-9a-fA-F]{4}', '', text)
        text = re.sub(r'\\U[0-9a-fA-F]{8}', '', text)
        # Decode HTML entities to their plain form (prevents obfuscation)
        text = re.sub(r'&#x?[0-9a-fA-F]+;', '', text)
        # Remove URL-encoded sequences
        text = re.sub(r'%[0-9a-fA-F]{2}', '', text)
        return text

    # ── Basic sanitization ───────────────────────────────────────────────

    @classmethod
    def _basic_sanitize(cls, text: str) -> str:
        """Basic text sanitization: null bytes, control chars, normalization."""
        if not text:
            return ""
        # Remove null bytes
        text = text.replace('\x00', '').replace('\u0000', '')
        # Remove zero-width characters
        text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text

    @classmethod
    def _truncate(cls, text: str, max_length: int) -> str:
        """Truncate text to max_length, preserving word boundaries."""
        if len(text) <= max_length:
            return text
        truncated = text[:max_length]
        # Try to break at last space
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            return truncated[:last_space] + '…'
        return truncated + '…'


# ── Convenience functions ────────────────────────────────────────────────

def validate_untrusted_input(
    text: str,
    max_length: int = 32000,
    strict: bool = False,
) -> InputValidationResult:
    """Validate user input against the SEC-01 contract."""
    return InputContract.validate(
        text, boundary=TrustBoundary.USER, max_length=max_length, strict=strict
    )


def sanitize_user_prompt(text: str, max_length: int = 32000) -> str:
    """Sanitize a user prompt for AI consumption. Returns cleaned text."""
    result = InputContract.validate(
        text, boundary=TrustBoundary.USER, max_length=max_length, strict=False
    )
    return result.sanitized_text
