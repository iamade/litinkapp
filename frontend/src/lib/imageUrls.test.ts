import { describe, expect, it } from 'vitest';
import { resolveDisplayImageUrl } from './imageUrls';

describe('resolveDisplayImageUrl', () => {
  it('uses backend tier-appropriate image_url first', () => {
    expect(
      resolveDisplayImageUrl({
        image_url: 'https://cdn.example.com/clean.png',
        watermarked_image_url: 'https://cdn.example.com/watermarked.png',
      })
    ).toBe('https://cdn.example.com/clean.png');
  });

  it('falls back to watermarked URLs when image_url is absent', () => {
    expect(
      resolveDisplayImageUrl({
        watermarked_image_url: 'https://cdn.example.com/proof.png',
      })
    ).toBe('https://cdn.example.com/proof.png');
  });

  it('supports camelCase image fields from frontend state', () => {
    expect(
      resolveDisplayImageUrl({
        imageUrl: 'https://cdn.example.com/frontend.png',
        watermarkedImageUrl: 'https://cdn.example.com/frontend-watermarked.png',
      })
    ).toBe('https://cdn.example.com/frontend.png');
  });
});
