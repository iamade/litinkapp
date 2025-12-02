from app.auth.schema import (
    TokenDataSchema as Token,
    UserLoginRequestSchema as UserLogin,
    UserCreateSchema as UserRegister,
    UserReadSchema as User,
    UserCreateSchema as UserCreate,
)

# UserUpdate is missing in auth schema, aliasing to UserCreate for now if needed, or omitting.
# Omitting UserUpdate for now.

from app.books.schemas import (
    Book,
    BookCreate,
    BookUpdate,
    BookStructureInput,
    ChapterInput,
    SectionInput,
    BookWithSections,
)

# Commenting out unverified modules to prevent import errors
# from .quiz import Quiz, QuizCreate, QuizAttempt, QuizAttemptCreate
# from .badge import Badge, BadgeCreate
# from .nft import NFT, NFTCreate
# from .ai import AIRequest, AIResponse, QuizGenerationRequest, AnalyzeChapterSafetyRequest

__all__ = [
    "Token",
    "UserLogin",
    "UserRegister",
    "User",
    "UserCreate",
    "Book",
    "BookCreate",
    "BookUpdate",
    "BookStructureInput",
    "ChapterInput",
    "SectionInput",
    "BookWithSections",
    # "Quiz", "QuizCreate", "QuizAttempt", "QuizAttemptCreate",
    # "Badge", "BadgeCreate",
    # "NFT", "NFTCreate",
    # "AIRequest", "AIResponse", "QuizGenerationRequest", "AnalyzeChapterSafetyRequest"
]
