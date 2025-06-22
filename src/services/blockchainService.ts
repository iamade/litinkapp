import algosdk from 'algosdk';

export interface Badge {
  id: string;
  name: string;
  description: string;
  imageUrl: string;
  criteria: string;
  rarity: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
  assetId?: number;
  transactionId?: string;
}

export interface NFTCollectible {
  id: string;
  name: string;
  description: string;
  imageUrl: string;
  animationUrl?: string;
  storyMoment: string;
  rarity: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
  assetId?: number;
  transactionId?: string;
}

class BlockchainService {
  private algodClient: algosdk.Algodv2;
  private indexerClient: algosdk.Indexer;
  private creatorAccount: algosdk.Account | null = null;

  constructor() {
    // Initialize Algorand clients (using Nodely endpoints)
    const algodToken = import.meta.env.VITE_ALGORAND_TOKEN || '';
    const algodServer = import.meta.env.VITE_ALGORAND_SERVER || 'https://testnet-api.algonode.cloud';
    const algodPort = '';

    const indexerToken = '';
    const indexerServer = import.meta.env.VITE_ALGORAND_INDEXER || 'https://testnet-idx.algonode.cloud';
    const indexerPort = '';

    this.algodClient = new algosdk.Algodv2(algodToken, algodServer, algodPort);
    this.indexerClient = new algosdk.Indexer(indexerToken, indexerServer, indexerPort);
  }

  async initializeCreatorAccount(): Promise<void> {
    try {
      // In production, load from secure storage
      const mnemonic = import.meta.env.VITE_CREATOR_MNEMONIC;
      if (mnemonic) {
        this.creatorAccount = algosdk.mnemonicToSecretKey(mnemonic);
      } else {
        // Generate new account for demo
        this.creatorAccount = algosdk.generateAccount();
        console.log('Generated new creator account:', this.creatorAccount.addr);
      }
    } catch (error) {
      console.error('Error initializing creator account:', error);
    }
  }

  async createBadgeNFT(badge: Badge, recipientAddress: string): Promise<Badge | null> {
    if (!this.creatorAccount) {
      await this.initializeCreatorAccount();
    }

    if (!this.creatorAccount) {
      console.error('Creator account not initialized');
      return null;
    }

    try {
      const params = await this.algodClient.getTransactionParams().do();
      
      const assetCreateTxn = algosdk.makeAssetCreateTxnWithSuggestedParamsFromObject({
        from: this.creatorAccount.addr,
        suggestedParams: params,
        defaultFrozen: false,
        unitName: 'BADGE',
        assetName: badge.name,
        manager: this.creatorAccount.addr,
        reserve: this.creatorAccount.addr,
        freeze: this.creatorAccount.addr,
        clawback: this.creatorAccount.addr,
        assetURL: badge.imageUrl,
        assetMetadataHash: undefined,
        total: 1, // NFT - only one copy
        decimals: 0,
      });

      const signedTxn = assetCreateTxn.signTxn(this.creatorAccount.sk);
      const { txId } = await this.algodClient.sendRawTransaction(signedTxn).do();
      
      // Wait for confirmation
      await this.waitForConfirmation(txId);
      
      // Get asset ID
      const ptx = await this.algodClient.pendingTransactionInformation(txId).do();
      const assetId = ptx['asset-index'];

      // Transfer to recipient
      await this.transferAsset(assetId, recipientAddress);

      return {
        ...badge,
        assetId,
        transactionId: txId
      };
    } catch (error) {
      console.error('Error creating badge NFT:', error);
      return null;
    }
  }

  async createStoryNFT(collectible: NFTCollectible, recipientAddress: string): Promise<NFTCollectible | null> {
    if (!this.creatorAccount) {
      await this.initializeCreatorAccount();
    }

    if (!this.creatorAccount) {
      console.error('Creator account not initialized');
      return null;
    }

    try {
      const params = await this.algodClient.getTransactionParams().do();
      
      const metadata = {
        name: collectible.name,
        description: collectible.description,
        image: collectible.imageUrl,
        animation_url: collectible.animationUrl,
        attributes: [
          { trait_type: 'Rarity', value: collectible.rarity },
          { trait_type: 'Story Moment', value: collectible.storyMoment },
          { trait_type: 'Type', value: 'Story Collectible' }
        ]
      };

      const assetCreateTxn = algosdk.makeAssetCreateTxnWithSuggestedParamsFromObject({
        from: this.creatorAccount.addr,
        suggestedParams: params,
        defaultFrozen: false,
        unitName: 'STORY',
        assetName: collectible.name,
        manager: this.creatorAccount.addr,
        reserve: this.creatorAccount.addr,
        freeze: this.creatorAccount.addr,
        clawback: this.creatorAccount.addr,
        assetURL: collectible.imageUrl,
        assetMetadataHash: undefined,
        total: 1,
        decimals: 0,
      });

      const signedTxn = assetCreateTxn.signTxn(this.creatorAccount.sk);
      const { txId } = await this.algodClient.sendRawTransaction(signedTxn).do();
      
      await this.waitForConfirmation(txId);
      
      const ptx = await this.algodClient.pendingTransactionInformation(txId).do();
      const assetId = ptx['asset-index'];

      await this.transferAsset(assetId, recipientAddress);

      return {
        ...collectible,
        assetId,
        transactionId: txId
      };
    } catch (error) {
      console.error('Error creating story NFT:', error);
      return null;
    }
  }

  private async transferAsset(assetId: number, recipientAddress: string): Promise<void> {
    if (!this.creatorAccount) return;

    try {
      const params = await this.algodClient.getTransactionParams().do();
      
      // Opt-in transaction for recipient (in real app, recipient would do this)
      const optInTxn = algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
        from: recipientAddress,
        to: recipientAddress,
        amount: 0,
        assetIndex: assetId,
        suggestedParams: params,
      });

      // Transfer transaction
      const transferTxn = algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
        from: this.creatorAccount.addr,
        to: recipientAddress,
        amount: 1,
        assetIndex: assetId,
        suggestedParams: params,
      });

      const signedTransferTxn = transferTxn.signTxn(this.creatorAccount.sk);
      const { txId } = await this.algodClient.sendRawTransaction(signedTransferTxn).do();
      
      await this.waitForConfirmation(txId);
    } catch (error) {
      console.error('Error transferring asset:', error);
    }
  }

  private async waitForConfirmation(txId: string): Promise<void> {
    let response = await this.algodClient.status().do();
    let lastround = response['last-round'];
    
    while (true) {
      const pendingInfo = await this.algodClient.pendingTransactionInformation(txId).do();
      if (pendingInfo['confirmed-round'] !== null && pendingInfo['confirmed-round'] > 0) {
        break;
      }
      lastround++;
      await this.algodClient.statusAfterBlock(lastround).do();
    }
  }

  async getUserAssets(userAddress: string): Promise<(Badge | NFTCollectible)[]> {
    try {
      const accountInfo = await this.indexerClient.lookupAccountByID(userAddress).do();
      const assets = accountInfo.account.assets || [];
      
      // In a real implementation, you'd fetch metadata for each asset
      // For now, return mock data
      return [];
    } catch (error) {
      console.error('Error fetching user assets:', error);
      return [];
    }
  }

  // Demo function to simulate earning badges
  async simulateEarnBadge(badgeName: string, userAddress: string = 'demo'): Promise<Badge> {
    const badge: Badge = {
      id: `badge-${Date.now()}`,
      name: badgeName,
      description: `Earned for completing ${badgeName}`,
      imageUrl: `https://images.pexels.com/photos/1029141/pexels-photo-1029141.jpeg?auto=compress&cs=tinysrgb&w=200`,
      criteria: 'Complete the required learning objectives',
      rarity: 'uncommon',
      assetId: Math.floor(Math.random() * 1000000),
      transactionId: `demo-tx-${Date.now()}`
    };

    // Simulate blockchain transaction delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return badge;
  }

  // Demo function to simulate earning story NFTs
  async simulateEarnNFT(storyMoment: string, userAddress: string = 'demo'): Promise<NFTCollectible> {
    const nft: NFTCollectible = {
      id: `nft-${Date.now()}`,
      name: `${storyMoment} Moment`,
      description: `A unique collectible from your story journey`,
      imageUrl: `https://images.pexels.com/photos/1029621/pexels-photo-1029621.jpeg?auto=compress&cs=tinysrgb&w=200`,
      animationUrl: `https://example.com/animations/story-${Date.now()}.mp4`,
      storyMoment,
      rarity: 'rare',
      assetId: Math.floor(Math.random() * 1000000),
      transactionId: `demo-tx-${Date.now()}`
    };

    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return nft;
  }
}

export const blockchainService = new BlockchainService();