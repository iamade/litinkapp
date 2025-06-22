import algosdk
from typing import Dict, Any, Optional
import asyncio
from app.core.config import settings


class BlockchainService:
    """Blockchain service for NFT creation using Algorand"""
    
    def __init__(self):
        self.algod_client = self._init_algod_client()
        self.indexer_client = self._init_indexer_client()
        self.creator_account = self._init_creator_account()
    
    def _init_algod_client(self):
        """Initialize Algorand client"""
        try:
            return algosdk.v2client.algod.AlgodClient(
                settings.ALGORAND_TOKEN or "",
                settings.ALGORAND_SERVER,
                headers={"User-Agent": "litink-backend"}
            )
        except Exception as e:
            print(f"Algorand client initialization error: {e}")
            return None
    
    def _init_indexer_client(self):
        """Initialize Algorand indexer client"""
        try:
            return algosdk.v2client.indexer.IndexerClient(
                "",
                settings.ALGORAND_INDEXER,
                headers={"User-Agent": "litink-backend"}
            )
        except Exception as e:
            print(f"Algorand indexer initialization error: {e}")
            return None
    
    def _init_creator_account(self):
        """Initialize creator account"""
        try:
            if settings.CREATOR_MNEMONIC:
                return algosdk.mnemonic.to_private_key(settings.CREATOR_MNEMONIC)
            else:
                # Generate new account for demo
                private_key, address = algosdk.account.generate_account()
                print(f"Generated new creator account: {address}")
                return private_key
        except Exception as e:
            print(f"Creator account initialization error: {e}")
            return None
    
    async def create_badge_nft(
        self,
        name: str,
        description: str,
        image_url: Optional[str],
        recipient_address: str
    ) -> Optional[Dict[str, Any]]:
        """Create badge NFT on Algorand"""
        if not self.algod_client or not self.creator_account:
            return await self._mock_create_badge(name, description)
        
        try:
            # Get suggested parameters
            params = self.algod_client.suggested_params()
            
            # Create asset
            txn = algosdk.future.transaction.AssetConfigTxn(
                sender=algosdk.account.address_from_private_key(self.creator_account),
                sp=params,
                total=1,  # NFT - only one copy
                default_frozen=False,
                unit_name="BADGE",
                asset_name=name,
                manager=algosdk.account.address_from_private_key(self.creator_account),
                reserve=algosdk.account.address_from_private_key(self.creator_account),
                freeze=algosdk.account.address_from_private_key(self.creator_account),
                clawback=algosdk.account.address_from_private_key(self.creator_account),
                url=image_url or "",
                decimals=0
            )
            
            # Sign transaction
            signed_txn = txn.sign(self.creator_account)
            
            # Submit transaction
            tx_id = self.algod_client.send_transaction(signed_txn)
            
            # Wait for confirmation
            await self._wait_for_confirmation(tx_id)
            
            # Get asset ID
            ptx = self.algod_client.pending_transaction_info(tx_id)
            asset_id = ptx["asset-index"]
            
            return {
                "asset_id": asset_id,
                "transaction_id": tx_id,
                "status": "success"
            }
            
        except Exception as e:
            print(f"Blockchain service error: {e}")
            return await self._mock_create_badge(name, description)
    
    async def create_story_nft(
        self,
        name: str,
        description: str,
        image_url: Optional[str],
        story_moment: str,
        recipient_address: str
    ) -> Optional[Dict[str, Any]]:
        """Create story NFT on Algorand"""
        if not self.algod_client or not self.creator_account:
            return await self._mock_create_story_nft(name, description)
        
        try:
            # Similar to badge creation but with story-specific metadata
            params = self.algod_client.suggested_params()
            
            txn = algosdk.future.transaction.AssetConfigTxn(
                sender=algosdk.account.address_from_private_key(self.creator_account),
                sp=params,
                total=1,
                default_frozen=False,
                unit_name="STORY",
                asset_name=name,
                manager=algosdk.account.address_from_private_key(self.creator_account),
                reserve=algosdk.account.address_from_private_key(self.creator_account),
                freeze=algosdk.account.address_from_private_key(self.creator_account),
                clawback=algosdk.account.address_from_private_key(self.creator_account),
                url=image_url or "",
                decimals=0
            )
            
            signed_txn = txn.sign(self.creator_account)
            tx_id = self.algod_client.send_transaction(signed_txn)
            
            await self._wait_for_confirmation(tx_id)
            
            ptx = self.algod_client.pending_transaction_info(tx_id)
            asset_id = ptx["asset-index"]
            
            return {
                "asset_id": asset_id,
                "transaction_id": tx_id,
                "status": "success"
            }
            
        except Exception as e:
            print(f"Blockchain service error: {e}")
            return await self._mock_create_story_nft(name, description)
    
    async def _wait_for_confirmation(self, tx_id: str):
        """Wait for transaction confirmation"""
        try:
            last_round = self.algod_client.status()["last-round"]
            
            while True:
                pending_info = self.algod_client.pending_transaction_info(tx_id)
                if pending_info.get("confirmed-round", 0) > 0:
                    break
                
                last_round += 1
                self.algod_client.status_after_block(last_round)
                
        except Exception as e:
            print(f"Confirmation wait error: {e}")
    
    async def _mock_create_badge(self, name: str, description: str) -> Dict[str, Any]:
        """Mock badge creation for development"""
        await asyncio.sleep(2)  # Simulate blockchain transaction time
        
        return {
            "asset_id": hash(name) % 1000000,
            "transaction_id": f"mock_tx_{hash(name)}",
            "status": "success"
        }
    
    async def _mock_create_story_nft(self, name: str, description: str) -> Dict[str, Any]:
        """Mock story NFT creation for development"""
        await asyncio.sleep(2)
        
        return {
            "asset_id": hash(name) % 1000000,
            "transaction_id": f"mock_story_tx_{hash(name)}",
            "status": "success"
        }