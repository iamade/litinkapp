// src/components/Video/EditorSettingsPanel.tsx
import React, { useState } from 'react';
import {
  Monitor,
  Film,
  Sliders,
  Droplet,
  ChevronDown,
  ChevronUp,
  Lock,
  Youtube,
  Instagram,
  Smartphone,
  Clapperboard
} from 'lucide-react';
import type { EditorSettings } from '../../types/videoProduction';

interface EditorSettingsPanelProps {
  settings: EditorSettings;
  onUpdateSettings: (settings: Partial<EditorSettings>) => void;
  compact?: boolean; // Compact mode for embedding in Timeline
  userTier?: 'free' | 'basic' | 'pro' | 'enterprise';
}

const EditorSettingsPanel: React.FC<EditorSettingsPanelProps> = ({
  settings,
  onUpdateSettings,
  compact = false,
  userTier = 'free'
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const isPaidTier = userTier !== 'free';

  // Platform preset cards
  const presets = [
    {
      name: 'YouTube',
      icon: Youtube,
      settings: { resolution: '1080p' as const, fps: 30 as const, aspectRatio: '16:9' as const, quality: 'high' as const },
      subtitle: '1080p · 30fps · 16:9',
      color: 'red'
    },
    {
      name: 'Instagram',
      icon: Instagram,
      settings: { resolution: '1080p' as const, fps: 30 as const, aspectRatio: '1:1' as const, quality: 'high' as const },
      subtitle: '1080p · 30fps · 1:1',
      color: 'pink'
    },
    {
      name: 'TikTok',
      icon: Smartphone,
      settings: { resolution: '720p' as const, fps: 30 as const, aspectRatio: '9:16' as const, quality: 'medium' as const },
      subtitle: '720p · 30fps · 9:16',
      color: 'cyan'
    },
    {
      name: 'Cinema',
      icon: Clapperboard,
      settings: { resolution: '4k' as const, fps: 24 as const, aspectRatio: '16:9' as const, quality: 'ultra' as const },
      subtitle: '4K · 24fps · 16:9',
      color: 'amber'
    }
  ];

  const isPresetActive = (preset: typeof presets[0]) => {
    return (
      settings.resolution === preset.settings.resolution &&
      settings.fps === preset.settings.fps &&
      settings.aspectRatio === preset.settings.aspectRatio
    );
  };

  // Compact view for Timeline integration
  if (compact) {
    return (
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl border border-gray-200 dark:border-gray-600 overflow-hidden transition-all duration-300">
        {/* Header - always visible */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 dark:bg-blue-400/10 flex items-center justify-center">
              <Sliders className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="text-left">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Video Settings
              </h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {settings.resolution} · {settings.fps}fps · {settings.aspectRatio} · {settings.outputFormat.toUpperCase()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Current preset badge */}
            {presets.find(p => isPresetActive(p)) && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-medium">
                {presets.find(p => isPresetActive(p))?.name}
              </span>
            )}
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </div>
        </button>

        {/* Quick presets - always visible */}
        <div className="px-4 pb-3 flex gap-2">
          {presets.map((preset) => {
            const Icon = preset.icon;
            const active = isPresetActive(preset);
            return (
              <button
                key={preset.name}
                onClick={() => onUpdateSettings(preset.settings)}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-medium transition-all duration-200 ${
                  active
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                    : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{preset.name}</span>
              </button>
            );
          })}
        </div>

        {/* Expanded settings */}
        {isExpanded && (
          <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-600 space-y-4">
            {/* Resolution & FPS Row */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Resolution
                </label>
                <select
                  value={settings.resolution}
                  onChange={(e) => onUpdateSettings({ resolution: e.target.value as EditorSettings['resolution'] })}
                  className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="720p">720p (HD)</option>
                  <option value="1080p">1080p (Full HD)</option>
                  <option value="4k">4K (Ultra HD)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Frame Rate
                </label>
                <select
                  value={settings.fps}
                  onChange={(e) => onUpdateSettings({ fps: parseInt(e.target.value) as EditorSettings['fps'] })}
                  className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="24">24 fps (Cinematic)</option>
                  <option value="30">30 fps (Standard)</option>
                  <option value="60">60 fps (Smooth)</option>
                </select>
              </div>
            </div>

            {/* Aspect Ratio & Format Row */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Aspect Ratio
                </label>
                <select
                  value={settings.aspectRatio}
                  onChange={(e) => onUpdateSettings({ aspectRatio: e.target.value as EditorSettings['aspectRatio'] })}
                  className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="16:9">16:9 (Widescreen)</option>
                  <option value="4:3">4:3 (Standard)</option>
                  <option value="1:1">1:1 (Square)</option>
                  <option value="9:16">9:16 (Vertical)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Output Format
                </label>
                <select
                  value={settings.outputFormat}
                  onChange={(e) => onUpdateSettings({ outputFormat: e.target.value as EditorSettings['outputFormat'] })}
                  className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="mp4">MP4</option>
                  <option value="webm">WebM</option>
                  <option value="mov">MOV</option>
                </select>
              </div>
            </div>

            {/* Quality Preset */}
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Quality Preset
              </label>
              <div className="flex gap-2">
                {(['low', 'medium', 'high', 'ultra'] as const).map((quality) => (
                  <button
                    key={quality}
                    onClick={() => onUpdateSettings({ quality })}
                    className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium transition-all duration-200 ${
                      settings.quality === quality
                        ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                        : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    {quality.charAt(0).toUpperCase() + quality.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Watermark - Tier-based */}
            <div className="pt-2 border-t border-gray-200 dark:border-gray-600">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Droplet className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Watermark</span>
                </div>
                {isPaidTier ? (
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.watermark?.enabled || false}
                      onChange={(e) => onUpdateSettings({
                        watermark: { ...settings.watermark, enabled: e.target.checked }
                      })}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-gray-200 dark:bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                ) : (
                  <div className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
                    <Lock className="w-3 h-3" />
                    <span>LitinkAI • Free Tier</span>
                  </div>
                )}
              </div>
              {isPaidTier && settings.watermark?.enabled && (
                <div className="mt-2 space-y-2">
                  <input
                    type="text"
                    value={settings.watermark?.text || ''}
                    onChange={(e) => onUpdateSettings({
                      watermark: { ...settings.watermark, text: e.target.value }
                    })}
                    placeholder="Custom watermark text"
                    className="w-full text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Full standalone view (kept for backwards compatibility)
  return (
    <div className="space-y-6">
      <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Export Settings</h4>

      {/* Resolution Settings */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-4">
        <div className="flex items-center space-x-2 mb-3">
          <Monitor className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h5 className="font-medium text-gray-900 dark:text-gray-100">Video Quality</h5>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Resolution
            </label>
            <select
              value={settings.resolution}
              onChange={(e) => onUpdateSettings({ 
                resolution: e.target.value as EditorSettings['resolution'] 
              })}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="720p">720p (HD)</option>
              <option value="1080p">1080p (Full HD)</option>
              <option value="4k">4K (Ultra HD)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Frame Rate
            </label>
            <select
              value={settings.fps}
              onChange={(e) => onUpdateSettings({ 
                fps: parseInt(e.target.value) as EditorSettings['fps'] 
              })}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="24">24 fps (Cinematic)</option>
              <option value="30">30 fps (Standard)</option>
              <option value="60">60 fps (Smooth)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Aspect Ratio
            </label>
            <select
              value={settings.aspectRatio}
              onChange={(e) => onUpdateSettings({ 
                aspectRatio: e.target.value as EditorSettings['aspectRatio'] 
              })}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="16:9">16:9 (Widescreen)</option>
              <option value="4:3">4:3 (Standard)</option>
              <option value="1:1">1:1 (Square)</option>
              <option value="9:16">9:16 (Vertical)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Output Format
            </label>
            <select
              value={settings.outputFormat}
              onChange={(e) => onUpdateSettings({ 
                outputFormat: e.target.value as EditorSettings['outputFormat'] 
              })}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="mp4">MP4</option>
              <option value="webm">WebM</option>
              <option value="mov">MOV</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
                    : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                {quality.charAt(0).toUpperCase() + quality.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Watermark Settings - Tier-based */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Droplet className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h5 className="font-medium text-gray-900 dark:text-gray-100">Watermark</h5>
          </div>
          {isPaidTier ? (
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
              <div className="w-11 h-6 bg-gray-200 dark:bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
              <Lock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <span className="text-xs font-medium text-amber-700 dark:text-amber-300">LitinkAI Watermark • Free Tier</span>
            </div>
          )}
        </div>

        {isPaidTier && settings.watermark?.enabled && (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
                className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
                        : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    {position.replace('-', ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {!isPaidTier && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Upgrade to a paid plan to customize or remove the watermark.
          </p>
        )}
      </div>

      {/* Preset Templates */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <h5 className="font-medium text-gray-900 dark:text-gray-100 mb-3">Quick Presets</h5>
        <div className="grid grid-cols-2 gap-3">
          {presets.map((preset) => {
            const Icon = preset.icon;
            return (
              <button
                key={preset.name}
                onClick={() => onUpdateSettings(preset.settings)}
                className={`p-3 rounded-lg text-left transition-all duration-200 ${
                  isPresetActive(preset)
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon className={`w-4 h-4 ${isPresetActive(preset) ? 'text-white' : 'text-gray-600 dark:text-gray-400'}`} />
                  <span className={`font-medium ${isPresetActive(preset) ? 'text-white' : 'text-gray-900 dark:text-gray-100'}`}>
                    {preset.name}
                  </span>
                </div>
                <div className={`text-xs mt-1 ${isPresetActive(preset) ? 'text-blue-100' : 'text-gray-600 dark:text-gray-400'}`}>
                  {preset.subtitle}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default EditorSettingsPanel;
