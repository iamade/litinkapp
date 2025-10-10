import React from 'react';
import { showVideoGenerationError } from '../../utils/videoGenerationErrors';

export const ErrorNotificationTest: React.FC = () => {
  const testErrorScenarios = [
    {
      name: 'Merge Failure',
      error: {
        status: 'failed',
        message: 'Audio/Video merge failed: [MERGE] No valid scene videos found, aborting merge step',
        error: '[MERGE] No valid scene videos found, aborting merge step',
        step: 'merge',
        generationId: 'test-gen-12345'
      }
    },
    {
      name: 'Video Generation Failure',
      error: {
        status: 'failed',
        message: 'Video generation failed: No valid scenes created',
        error: 'No valid scene videos found',
        step: 'video_generation',
        generationId: 'test-gen-67890'
      }
    },
    {
      name: 'Audio Generation Failure',
      error: {
        status: 'failed',
        message: 'Audio generation timeout',
        error: 'API timeout after 30 seconds',
        step: 'audio_generation',
        generationId: 'test-gen-11111'
      }
    },
    {
      name: 'Safety Checker Failure',
      error: {
        status: 'failed',
        message: 'Content flagged by safety checker',
        error: 'safety checker violation: inappropriate content',
        step: 'image_generation',
        generationId: 'test-gen-22222'
      }
    },
    {
      name: 'Network Error',
      error: {
        status: 'failed',
        message: 'Network connection lost',
        error: 'network connection timeout',
        step: 'video_generation',
        generationId: 'test-gen-33333'
      }
    },
    {
      name: 'Generic Error',
      error: {
        status: 'failed',
        message: 'Unknown error occurred',
        error: 'Unexpected server error',
        generationId: 'test-gen-44444'
      }
    }
  ];

  return (
    <div className="p-6 bg-gray-100 rounded-lg border border-gray-300">
      <h3 className="text-lg font-semibold mb-4">Error Notification Test</h3>
      <p className="text-sm text-gray-600 mb-4">
        Click the buttons below to test different error notification scenarios.
        Each will show a toast notification with user-friendly error messages.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {testErrorScenarios.map((scenario, index) => (
          <button
            key={index}
            onClick={() => showVideoGenerationError(scenario.error)}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm"
          >
            Test: {scenario.name}
          </button>
        ))}
      </div>
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
        <h4 className="font-medium text-blue-900 mb-2">What to expect:</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Toast notifications will appear in the top-right corner</li>
          <li>• Error messages are translated to user-friendly language</li>
          <li>• Notifications persist for 15 seconds for reading</li>
          <li>• Generation IDs are shown for reference</li>
          <li>• Actionable advice is included for users</li>
        </ul>
      </div>
    </div>
  );
};