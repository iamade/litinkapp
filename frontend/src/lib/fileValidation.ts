/**
 * File validation utilities for checking file accessibility
 * Helps catch issues like iCloud files that aren't downloaded locally
 */

/**
 * Check if a File object is accessible by attempting to read a small slice
 * This catches iCloud files that haven't been downloaded and other access issues
 */
export const checkFileAccessible = async (
  file: File
): Promise<{ accessible: boolean; error?: string }> => {
  try {
    // Attempt to read first byte
    const slice = file.slice(0, 1);
    await slice.arrayBuffer();
    return { accessible: true };
  } catch (error) {
    return {
      accessible: false,
      error:
        "Cannot access file. If stored in iCloud, ensure it's downloaded locally and iCloud is properly signed in.",
    };
  }
};
