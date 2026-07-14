export type ImageUrlAsset = {
  image_url?: string | null;
  imageUrl?: string | null;
  watermarked_image_url?: string | null;
  watermarked_url?: string | null;
  watermarkedImageUrl?: string | null;
};

export function resolveDisplayImageUrl(asset?: ImageUrlAsset | null): string {
  if (!asset) return '';

  return (
    asset.image_url ||
    asset.imageUrl ||
    asset.watermarked_image_url ||
    asset.watermarked_url ||
    asset.watermarkedImageUrl ||
    ''
  );
}
