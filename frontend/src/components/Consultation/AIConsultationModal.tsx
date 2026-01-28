import React, { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  Loader2,
  Send,
  Film,
  FileText,
  Video,
  BookOpen,
  Target,
  ChevronRight,
  X,
  Check,
  MonitorPlay,
  Wand2,
} from "lucide-react";
import { apiClient } from "../../lib/api";

interface ConsultationMessage {
  role: "user" | "assistant";
  content: string;
  actions?: SuggestedAction[];
  timestamp: Date;
}

interface SuggestedAction {
  id: string;
  label: string;
  description: string;
  recommended: boolean;
  disabled: boolean;
  disabled_reason?: string | null;
}

interface ContentAnalysis {
  document_type: string;
  title: string;
  summary: string;
  quality_assessment: string;
  detected_elements?: {
    story_count?: number;
    character_count?: number;
    scene_count?: number;
    themes?: string[];
  };
}

interface ProjectConfig {
  projectType: "entertainment" | "training" | "marketing";
  contentType: string;
  terminology: "Film" | "Episode" | "Part" | "Module";
  universeName?: string;
  selectedStories?: string[];
  // New: Include conversation data for saving
  consultationData?: {
    conversation: Array<{ role: string; content: string }>;
    agreements: {
      universe_name?: string;
      phases?: any[];
      terminology?: string;
      content_type?: string;
    };
  };
}

interface AIConsultationModalProps {
  files: File[];
  initialPrompt: string;
  onComplete: (config: ProjectConfig) => void;
  onCancel: () => void;
}

const ACTION_ICONS: Record<string, React.ReactNode> = {
  cinematic_universe: <Film className="h-5 w-5" />,
  script_expansion: <FileText className="h-5 w-5" />,
  storyboard: <MonitorPlay className="h-5 w-5" />,
  training_content: <BookOpen className="h-5 w-5" />,
  marketing_ad: <Target className="h-5 w-5" />,
  video_production: <Video className="h-5 w-5" />,
};

export function AIConsultationModal({
  files,
  initialPrompt,
  onComplete,
  onCancel,
}: AIConsultationModalProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(true);
  const [messages, setMessages] = useState<ConsultationMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [analysis, setAnalysis] = useState<ContentAnalysis | null>(null);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const [projectConfig, setProjectConfig] = useState<Partial<ProjectConfig>>({});
  const [readyToCreate, setReadyToCreate] = useState(false);
  const [hasUnansweredQuestions, setHasUnansweredQuestions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Initial analysis on mount
  useEffect(() => {
    analyzeFiles();
  }, []);

  const analyzeFiles = async () => {
    setIsAnalyzing(true);
    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      if (initialPrompt) {
        formData.append("prompt", initialPrompt);
      }

      // Use upload for FormData - returns parsed JSON directly
      const data = await apiClient.upload<{
        status: string;
        content_analysis?: ContentAnalysis;
        ai_message?: string;
        suggested_actions?: SuggestedAction[];
        recommended_action?: string;
      }>("/ai/consultation/analyze", formData);

      if (data.content_analysis) {
        setAnalysis(data.content_analysis);
      }

      // Create initial AI message
      const aiMessage: ConsultationMessage = {
        role: "assistant",
        content: data.ai_message || `I've analyzed your ${files.length > 1 ? "files" : "file"}. What would you like to create?`,
        actions: data.suggested_actions || [],
        timestamp: new Date(),
      };

      setMessages([aiMessage]);

      // Set recommended action
      if (data.recommended_action) {
        setSelectedAction(data.recommended_action);
      }
    } catch (error) {
      console.error("Analysis failed:", error);
      setMessages([
        {
          role: "assistant",
          content: "I had trouble analyzing your files. Would you like to tell me what you'd like to create?",
          actions: [
            {
              id: "script_expansion",
              label: "Expand into Script",
              description: "Develop into a screenplay",
              recommended: true,
              disabled: false,
            },
            {
              id: "cinematic_universe",
              label: "Create Universe",
              description: "Organize into films/episodes",
              recommended: false,
              disabled: false,
            },
          ],
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const sendMessage = async (content: string) => {
    if (!content.trim()) return;

    // Add user message
    const userMessage: ConsultationMessage = {
      role: "user",
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsTyping(true);

    try {
      const data = await apiClient.post<{
        ai_message?: string;
        ready_to_proceed?: boolean;
        follow_up_questions?: string[];
        project_config?: {
          project_type?: string;
          content_type?: string;
          terminology?: string;
          universe_name?: string;
          phases?: any[];
        };
      }>("/ai/consultation/chat", {
        message: content,
        context: {
          messages: messages.map((m) => ({ role: m.role, content: m.content })),
          file_summary: analysis?.summary || "",
        },
      });

      // Add AI response
      const aiMessage: ConsultationMessage = {
        role: "assistant",
        content: data.ai_message || "I understand. Let me help you with that.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);

      // Track if AI is asking follow-up questions
      const hasQuestions = data.follow_up_questions && data.follow_up_questions.length > 0;
      setHasUnansweredQuestions(hasQuestions || false);

      // Check if ready to proceed
      if (data.ready_to_proceed && data.project_config) {
        setProjectConfig({
          projectType: (data.project_config.project_type || "entertainment") as "entertainment" | "training" | "marketing",
          contentType: data.project_config.content_type || "single_script",
          terminology: (data.project_config.terminology || "Film") as "Film" | "Episode" | "Part" | "Module",
          universeName: data.project_config.universe_name,
        });
        setReadyToCreate(true);
        setHasUnansweredQuestions(false);
      }
    } catch (error) {
      console.error("Chat failed:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I'm having trouble processing that. Could you try again?",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleActionClick = async (action: SuggestedAction) => {
    if (action.disabled) return;

    setSelectedAction(action.id);

    // Map action to project config
    const configMap: Record<string, Partial<ProjectConfig>> = {
      cinematic_universe: {
        projectType: "entertainment",
        contentType: "cinematic_universe",
        terminology: "Film",
      },
      script_expansion: {
        projectType: "entertainment",
        contentType: "single_script",
        terminology: "Film",
      },
      storyboard: {
        projectType: "entertainment",
        contentType: "storyboard",
        terminology: "Film",
      },
      training_content: {
        projectType: "training",
        contentType: "training_video",
        terminology: "Module",
      },
      marketing_ad: {
        projectType: "marketing",
        contentType: "ad",
        terminology: "Part",
      },
    };

    const config = configMap[action.id] || { projectType: "entertainment", contentType: action.id };
    setProjectConfig(config);

    // Send action selection as message
    await sendMessage(`I want to ${action.label.toLowerCase()}`);
  };

  const handleCreateProject = () => {
    // Build conversation data to save
    const conversationData = {
      conversation: messages.map((m) => ({ role: m.role, content: m.content })),
      agreements: {
        universe_name: projectConfig.universeName || analysis?.title,
        terminology: projectConfig.terminology || "Film",
        content_type: projectConfig.contentType,
      },
    };

    if (!projectConfig.projectType || !projectConfig.contentType) {
      // Default config if not fully set
      onComplete({
        projectType: "entertainment",
        contentType: selectedAction || "single_script",
        terminology: "Film",
        universeName: analysis?.title,
        consultationData: conversationData,
      });
    } else {
      onComplete({
        projectType: projectConfig.projectType,
        contentType: projectConfig.contentType,
        terminology: projectConfig.terminology || "Film",
        universeName: projectConfig.universeName || analysis?.title,
        consultationData: conversationData,
      });
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20">
          <div className="flex items-center gap-3">
            <div className="bg-purple-100 dark:bg-purple-800/50 p-2 rounded-xl">
              <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h2 className="font-bold text-gray-900 dark:text-white">AI Creative Consultant</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {files.length} file{files.length > 1 ? "s" : ""} uploaded
              </p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isAnalyzing ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <div className="relative">
                <div className="absolute inset-0 bg-purple-400 rounded-full blur-xl opacity-30 animate-pulse" />
                <Loader2 className="h-10 w-10 text-purple-600 animate-spin relative" />
              </div>
              <p className="text-gray-600 dark:text-gray-400 animate-pulse">
                Analyzing your content...
              </p>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      message.role === "user"
                        ? "bg-purple-600 text-white"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>

                    {/* Action Cards */}
                    {message.actions && message.actions.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {message.actions.map((action) => (
                          <button
                            key={action.id}
                            onClick={() => handleActionClick(action)}
                            disabled={action.disabled}
                            className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left ${
                              selectedAction === action.id
                                ? "bg-purple-100 dark:bg-purple-900/40 border-purple-400 dark:border-purple-500"
                                : "bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-500"
                            } ${action.disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:shadow-md"}`}
                          >
                            <div
                              className={`p-2 rounded-lg ${
                                action.recommended
                                  ? "bg-purple-100 dark:bg-purple-800 text-purple-600 dark:text-purple-400"
                                  : "bg-gray-100 dark:bg-gray-600 text-gray-600 dark:text-gray-300"
                              }`}
                            >
                              {ACTION_ICONS[action.id] || <Wand2 className="h-5 w-5" />}
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-gray-900 dark:text-white">
                                  {action.label}
                                </span>
                                {action.recommended && (
                                  <span className="text-xs bg-purple-600 text-white px-2 py-0.5 rounded-full">
                                    Recommended
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-gray-500 dark:text-gray-400">
                                {action.description}
                              </p>
                            </div>
                            {selectedAction === action.id && (
                              <Check className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                            )}
                            <ChevronRight className="h-4 w-4 text-gray-400" />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          {readyToCreate ? (
            <button
              onClick={handleCreateProject}
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white py-3 px-6 rounded-xl font-bold flex items-center justify-center gap-2 transition-all transform hover:scale-[1.02] shadow-lg"
            >
              <Sparkles className="h-5 w-5" />
              Create Project
            </button>
          ) : (
            <div className="flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage(inputValue)}
                placeholder="Type a message or select an option above..."
                className="flex-1 px-4 py-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900 dark:text-white placeholder-gray-400"
                disabled={isAnalyzing || isTyping}
              />
              <button
                onClick={() => sendMessage(inputValue)}
                disabled={!inputValue.trim() || isAnalyzing || isTyping}
                className="p-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-colors"
              >
                <Send className="h-5 w-5" />
              </button>
              {selectedAction && !hasUnansweredQuestions && (
                <button
                  onClick={handleCreateProject}
                  className="px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-xl font-medium flex items-center gap-2 transition-colors"
                >
                  <Check className="h-4 w-4" />
                  Confirm & Create
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AIConsultationModal;
