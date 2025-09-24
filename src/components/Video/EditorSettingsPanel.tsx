// src/components/Video/EditorSettingsPanel.tsx
import React from 'react';
import {
  Monitor,
  Film,
  Sliders,
  Droplet,
  Type,
  Image
} from 'lucide-react';
import type { EditorSettings } from '../../types/videoProduction';

interface EditorSettingsPanelProps {
  settings: EditorSettings;
  onUpdateSettings: (settings: Partial<EditorSettings>) => void;
}

const EditorSettingsPanel: React.FC<EditorSettingsPanelProps> = ({
  settings,
  onUpdateSettings
}) => {
  return (
    <div className="space-y-6">
      <h4 className="text-lg font-semibold text-gray-900">Export Settings</h4>

      {/* Resolution Settings */}
      <div className="bg-gray-50 rounded-lg p-4 space-y-4">
        <div className="flex items-center space-x-2 mb-3">
          <Monitor className="w-5 h-5 text-gray-600" />
          <h5 className="font-medium text-gray-900">Video Quality</h5>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Resolution
            </label>
            <select
              value={settings.resolution}
              onChange={(e) => onUpdateSettings({ 
                resolution: e.target.value as EditorSettings['resolution'] 
              })}
              className="w-full border rounded-lg px-3 py-2"
            >
              <option value="720p">720p (HD)</option>
              <option value="1080p">1080p (Full HD)</option>
              <option value="4k">4K (Ultra HD)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Frame Rate
            </label>
            <select
              value={settings.fps}
              onChange={(e) => onUpdateSettings({ 
                fps: parseInt(e.target.value) as EditorSettings['fps'] 
              })}
              className="w-full border rounded-lg px-3 py-2"
            >
              <option value="24">24 fps (Cinematic)</option>
              <option value="30">30 fps (Standard)</option>
              <option value="60">60 fps (Smooth)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Aspect Ratio
            </label>
            <select
              value={settings.aspectRatio}
              onChange={(e) => onUpdateSettings({ 
                aspectRatio: e.target.value as EditorSettings['aspectRatio'] 
              })}
              className="w-full border rounded-lg px-3 py-2"
            >
              <option value="16:9">16:9 (Widescreen)</option>
              <option value="4:3">4:3 (Standard)</option>
              <option value="1:1">1:1 (Square)</option>
              <option value="9:16">9:16 (Vertical)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Output Format
            </label>
            <select
              value={settings.outputFormat}
              onChange={(e) => onUpdateSettings({ 
                outputFormat: e.target.value as EditorSettings['outputFormat'] 
              })}
              className="w-full border rounded-lg px-3 py-2"
            >
              <option value="mp4">MP4</option>
              <option value="webm">WebM</option>
              <option value="mov">MOV</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Quality Preset
          </label>
          <div className="flex space-x-2">
            {(['low', 'medium', 'high', 'ultra'] as const).map((quality) => (
              <button
                key={quality}
                onClick={() => onUpdateSettings({ quality })}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                  settings.quality === quality
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border text-gray-700 hover:bg-gray-50'
                }`}
              >
                {quality.charAt(0).toUpperCase() + quality.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Watermark Settings */}
      <div className="bg-gray-50 rounded-lg p-4 space-y-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Droplet className="w-5 h-5 text-gray-600" />
            <h5 className="font-medium text-gray-900">Watermark</h5>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.watermark?.enabled || false}
              onChange={(e) => onUpdateSettings({
                watermark: {
                  ...settings.watermark,
                  enabled: e.target.checked
                }
              })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>

        {settings.watermark?.enabled && (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Watermark Text
              </label>
              <input
                type="text"
                value={settings.watermark.text || ''}
                onChange={(e) => onUpdateSettings({
                  watermark: {
                    ...settings.watermark,
                    text: e.target.value
                  }
                })}
                placeholder="© Your Name"
                className="w-full border rounded-lg px-3 py-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Position
              </label>
              <div className="grid grid-cols-2 gap-2">
                {(['top-left', 'top-right', 'bottom-left', 'bottom-right'] as const).map((position) => (
                  <button
                    key={position}
                    onClick={() => onUpdateSettings({
                      watermark: {
                        ...settings.watermark!,
                        position
                      }
                    })}
                    className={`py-2 px-3 rounded text-sm ${
                      settings.watermark?.position === position
                        ? 'bg-blue-600 text-white'
                        : 'bg-white border text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {position.replace('-', ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Preset Templates */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h5 className="font-medium text-gray-900 mb-3">Quick Presets</h5>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => onUpdateSettings({
              resolution: '1080p',
              fps: 30,
              aspectRatio: '16:9',
              quality: 'high'
            })}
            className="p-3 bg-white border rounded-lg hover:bg-gray-50 text-left"
          >
            <div className="font-medium text-gray-900">YouTube</div>
            <div className="text-xs text-gray-600">1080p, 30fps, 16:9</div>
          </button>
          <button
            onClick={() => onUpdateSettings({
              resolution: '1080p',
              fps: 30,
              aspectRatio: '1:1',
              quality: 'high'
            })}
            className="p-3 bg-white border rounded-lg hover:bg-gray-50 text-left"
          >
            <div className="font-medium text-gray-900">Instagram</div>
            <div className="text-xs text-gray-600">1080p, 30fps, 1:1</div>
          </button>
          <button
            onClick={() => onUpdateSettings({
              resolution: '720p',
              fps: 30,
              aspectRatio: '9:16',
              quality: 'medium'
            })}
            className="p-3 bg-white border rounded-lg hover:bg-gray-50 text-left"
          >
            <div className="font-medium text-gray-900">TikTok</div>
            <div className="text-xs text-gray-600">720p, 30fps, 9:16</div>
          </button>
          <button
            onClick={() => onUpdateSettings({
              resolution: '4k',
              fps: 24,
              aspectRatio: '16:9',
              quality: 'ultra'
            })}
            className="p-3 bg-white border rounded-lg hover:bg-gray-50 text-left"
          >
            <div className="font-medium text-gray-900">Cinema</div>
            <div className="text-xs text-gray-600">4K, 24fps, 16:9</div>
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditorSettingsPanel;
