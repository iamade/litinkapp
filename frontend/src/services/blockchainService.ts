import { apiClient } from "../lib/api";

export interface NFT {
  id: string;
  name: string;
  description: string;
  asset_id: number;
  tx_id: string;
  metadata_url: string;
  owner_id: string;
  created_at: string;
}

export const blockchainService = {
  createNFT: async (
    name: string,
    description: string,
    metadata_url: string
  ): Promise<NFT> => {
    return apiClient.post<NFT>("/nfts/", { name, description, metadata_url });
  },

  getUserNFTs: async (userId: string): Promise<NFT[]> => {
    return apiClient.get<NFT[]>(`/nfts/user/${userId}`);
  },

  getNFTDetails: async (assetId: number): Promise<NFT> => {
    return apiClient.get<NFT>(`/nfts/${assetId}`);
  },
};
