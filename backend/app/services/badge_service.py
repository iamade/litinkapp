from sqlalchemy.ext.asyncio import AsyncSession
from app.models.badge import Badge, UserBadge
from app.models.quiz import QuizAttempt
from app.models.progress import UserProgress
from app.services.blockchain_service import BlockchainService


class BadgeService:
    """Service for managing badge awards"""
    
    def __init__(self):
        self.blockchain_service = BlockchainService()
    
    async def check_quiz_badges(self, db: AsyncSession, user_id: str, score: int):
        """Check and award quiz-related badges"""
        # Perfect Score badge
        if score == 100:
            await self._award_badge_if_not_exists(db, user_id, "Perfect Score")
        
        # Quiz Master badge (90%+ on 10 quizzes)
        if score >= 90:
            high_score_attempts = await self._count_high_score_attempts(db, user_id)
            if high_score_attempts >= 10:
                await self._award_badge_if_not_exists(db, user_id, "Quiz Master")
    
    async def check_reading_badges(self, db: AsyncSession, user_id: str):
        """Check and award reading-related badges"""
        progress_list = await UserProgress.get_by_user(db, user_id)
        completed_books = [p for p in progress_list if p.completed_at]
        
        # First Steps badge
        if len(completed_books) >= 1:
            await self._award_badge_if_not_exists(db, user_id, "First Steps")
        
        # Bookworm badge
        if len(completed_books) >= 5:
            await self._award_badge_if_not_exists(db, user_id, "Bookworm")
    
    async def check_story_badges(self, db: AsyncSession, user_id: str):
        """Check and award story-related badges"""
        # Get completed entertainment books
        progress_list = await UserProgress.get_by_user(db, user_id)
        # This would need to join with books table to check book_type
        # Simplified for now
        
        # Story Master badge (10 interactive stories)
        # Implementation would check for entertainment book completions
        pass
    
    async def _award_badge_if_not_exists(self, db: AsyncSession, user_id: str, badge_name: str):
        """Award badge if user doesn't already have it"""
        # Check if user already has badge
        existing_badges = await UserBadge.get_by_user(db, user_id)
        badge = await Badge.get_by_name(db, badge_name)
        
        if not badge:
            return
        
        # Check if already awarded
        if any(ub.badge_id == badge.id for ub in existing_badges):
            return
        
        # Create blockchain NFT
        nft_result = await self.blockchain_service.create_badge_nft(
            badge.name,
            badge.description,
            badge.image_url,
            user_id
        )
        
        # Award badge
        await UserBadge.create(
            db,
            user_id=user_id,
            badge_id=str(badge.id),
            blockchain_asset_id=nft_result.get("asset_id") if nft_result else None,
            transaction_id=nft_result.get("transaction_id") if nft_result else None
        )
    
    async def _count_high_score_attempts(self, db: AsyncSession, user_id: str) -> int:
        """Count quiz attempts with 90%+ score"""
        attempts = await QuizAttempt.get_by_user(db, user_id)
        return len([a for a in attempts if a.score >= 90])