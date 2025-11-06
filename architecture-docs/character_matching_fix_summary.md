# Character Matching Image Display Fix

## Problem
When users selected a plot character from the dropdown to match with a script character, only the character's name was displayed. The existing plot character's image was not being shown, even though the character had an image in the Plot Overview.

## Root Cause
The `onGenerate` handler in `ImagesPanel.tsx` was only using the selected plot character's description to generate a NEW image via AI, rather than checking if the plot character already had an existing image and using that directly.

## Solution Implemented

### 1. Enhanced Character Image State Management (`useImageGeneration.ts`)
- Added a new `setCharacterImage()` function to allow direct updates to the character images state
- This function accepts a character name and image data, updating the state without triggering AI generation

### 2. Updated Character Generation Logic (`ImagesPanel.tsx`)
The `onGenerate` handler now follows this flow:
1. **Check for existing image**: When a plot character is selected, first check if they have an `image_url`
2. **Use existing image**: If found, immediately update the character image state with the plot character's existing image
3. **Show success message**: Display a toast notification confirming the image is being used from the selected plot character
4. **Fallback to generation**: Only generate a new image if:
   - No plot character is selected, OR
   - The selected plot character doesn't have an existing image

### 3. Improved Character Selector UI
Enhanced the character selection dropdown with:
- **Visual indicators**: Shows a checkmark (✓) next to characters that have existing images
- **Image preview**: Displays a thumbnail of the selected plot character's image
- **Status feedback**: Shows whether the selected character has an image or will need generation
- **Dynamic button text**:
  - "Use Image" when selected character has an existing image
  - "Generate" when no image exists or no character is selected

### 4. Better User Experience
- Added image preview (12x12px thumbnail) in the selection panel
- Clear visual distinction between characters with and without images
- Immediate feedback when an image is available
- Success toast message confirming which character's image is being used

## Files Modified

1. **`src/hooks/useImageGeneration.ts`**
   - Added `setCharacterImage()` function
   - Exported the new function in the hook's return value

2. **`src/components/Images/ImagesPanel.tsx`**
   - Updated `onGenerate` handler to check for existing images first
   - Enhanced character selector dropdown with image preview
   - Added visual indicators for characters with images
   - Updated button text to reflect action (Use Image vs Generate)
   - Added `selectedPlotCharDetails` memo to track selected character
   - Updated `ImageActions` component to accept `selectedPlotCharHasImage` prop

## How It Works Now

1. User opens the character matching dropdown on a script character card
2. User sees a list of plot characters with checkmarks indicating which have images
3. User selects a plot character from the dropdown
4. A preview panel shows:
   - The plot character's thumbnail image (if available)
   - Character name and role
   - Status indicator (green "Has existing image" or orange "No image - will generate new")
5. User clicks the "Use Image" or "Generate" button
6. If the plot character has an existing image:
   - The image is immediately displayed on the script character card
   - A success toast shows "Using image from [Character Name]"
7. If no image exists:
   - AI generation is triggered using the plot character's description
   - Standard generation flow continues

## Benefits

- **Instant image display**: No waiting for AI generation when plot character already has an image
- **Clear user feedback**: Users know immediately if an image is available or needs to be generated
- **Reduced API costs**: Avoids unnecessary AI image generation when images already exist
- **Better user experience**: Visual previews and status indicators help users make informed decisions
- **Preserved flexibility**: Users can still generate new images if desired

## Testing Recommendations

1. Test matching a script character with a plot character that has an image
2. Test matching a script character with a plot character that has no image
3. Verify the image preview shows correctly in the dropdown
4. Confirm the button text changes appropriately
5. Test that regeneration still works for matched characters
6. Verify images persist after page refresh
