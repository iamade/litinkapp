import { apiClient as api } from '../api';

export interface UpscaleResponse {
    upscaled_url: string;
}

/**
 * Upscale an image using the ModelsLab V6 service.
 * @param imageUrl URL of the image to upscale
 * @param userTier User's subscription tier (affects model selection)
 * @param faceEnhance Whether to apply face enhancement (default: false)
 * @returns Promise with upscaled image URL
 */
export async function upscaleImage(
    imageUrl: string, 
    userTier: string = 'free',
    faceEnhance: boolean = false
): Promise<UpscaleResponse> {
    const response = await api.post<UpscaleResponse>('/api/v1/images/upscale', {
        image_url: imageUrl,
        user_tier: userTier,
        face_enhance: faceEnhance
    });
    return response;
}
