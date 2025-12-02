# Schema Compatibility Layer
# This file re-exports schemas from feature modules for backwards compatibility
# Direct imports from feature modules (e.g., app.books.schemas) are preferred

# Auth schemas
from app.auth.schema import (
    TokenDataSchema as Token,
    UserLoginRequestSchema as UserLogin,
    UserCreateSchema as UserRegister,
    UserReadSchema as User,
    UserCreateSchema as UserCreate,
)

# Book schemas
from app.books.schemas import (
    Book,
    BookCreate,
    BookUpdate,
    BookStructureInput,
    ChapterInput,
    SectionInput,
    BookWithSections,
)

# Plot schemas
from app.plots.schemas import (
    PlotOverviewCreate,
    PlotOverviewUpdate,
    PlotOverviewResponse,
    CharacterCreate,
    CharacterUpdate,
    CharacterResponse,
    CharacterArchetypeResponse,
    CharacterArchetypeMatch,
    ImageGenerationRequest,
)

# AI schemas
from app.ai.schemas import (
    AIRequest,
    AIResponse,
    QuizGenerationRequest,
    AnalyzeChapterSafetyRequest,
    ScriptGenerationRequest,
    ScriptResponse,
    ScriptRetrievalResponse,
)

# Video schemas
from app.videos.schemas import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoGenerationStatus,
    VideoQualityTier,
)

# Quiz schemas
from app.quizzes.schemas import (
    Quiz,
    QuizCreate,
    QuizAttempt,
    QuizAttemptCreate,
)

# Badge schemas
from app.badges.schemas import (
    Badge,
    BadgeCreate,
)

# NFT schemas
from app.nfts.schemas import (
    NFT,
    NFTCreate,
)

# Subscription schemas
# Note: SubscriptionCreate/Update may not exist in schemas.py
# Commenting out for now
# from app.subscriptions.schemas import (
#     SubscriptionTier,
#     SubscriptionCreate,
#     SubscriptionUpdate,
# )


# Image schemas - TODO: verify actual schema names
# from app.images.schemas import (...)

# Merge schemas
from app.merges.schemas import (
    MergeManualRequest,
    MergeManualResponse,
    MergeStatus,
    MergeStatusResponse,
    MergePreviewRequest,
    MergePreviewResponse,
)

__all__ = [
    # Auth
    "Token",
    "UserLogin",
    "UserRegister",
    "User",
    "UserCreate",
    # Books
    "Book",
    "BookCreate",
    "BookUpdate",
    "BookStructureInput",
    "ChapterInput",
    "SectionInput",
    "BookWithSections",
    # Plots
    "PlotOverviewCreate",
    "PlotOverviewUpdate",
    "PlotOverviewResponse",
    "CharacterCreate",
    "CharacterUpdate",
    "CharacterResponse",
    "CharacterArchetypeResponse",
    "CharacterArchetypeMatch",
    "ImageGenerationRequest",
    # AI
    "AIRequest",
    "AIResponse",
    "QuizGenerationRequest",
    "AnalyzeChapterSafetyRequest",
    "ScriptGenerationRequest",
    "ScriptResponse",
    "ScriptRetrievalResponse",
    # Videos
    "VideoGenerationRequest",
    "VideoGenerationResponse",
    "VideoGenerationStatus",
    "VideoQualityTier",
    # Quizzes
    "Quiz",
    "QuizCreate",
    "QuizAttempt",
    "QuizAttemptCreate",
    # Badges
    "Badge",
    "BadgeCreate",
    # NFTs
    "NFT",
    "NFTCreate",
    # Merges
    "MergeManualRequest",
    "MergeManualResponse",
    "MergeStatus",
    "MergeStatusResponse",
    "MergePreviewRequest",
    "MergePreviewResponse",
]
