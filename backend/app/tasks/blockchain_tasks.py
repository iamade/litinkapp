from app.tasks.celery_app import celery_app
from app.core.services.blockchain import BlockchainService


@celery_app.task(bind=True)
def create_badge_nft_task(
    self, badge_name: str, description: str, image_url: str, recipient_address: str
):
    """Background task to create badge NFT"""
    try:
        blockchain_service = BlockchainService()
        result = blockchain_service.create_badge_nft_sync(
            badge_name, description, image_url, recipient_address
        )

        return {"status": "SUCCESS", "result": result}
    except Exception as e:
        return {"status": "FAILURE", "error": str(e)}


@celery_app.task(bind=True)
def create_story_nft_task(
    self,
    name: str,
    description: str,
    image_url: str,
    story_moment: str,
    recipient_address: str,
):
    """Background task to create story NFT"""
    try:
        blockchain_service = BlockchainService()
        result = blockchain_service.create_story_nft_sync(
            name, description, image_url, story_moment, recipient_address
        )

        return {"status": "SUCCESS", "result": result}
    except Exception as e:
        return {"status": "FAILURE", "error": str(e)}
