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
  Coins,
} from "lucide-react";
import { apiClient } from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";

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
  onSkip?: () => void;
  onCancel: () => void;
}

interface ConsultationChatResponse {
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
  cap_reached?: boolean;
  requires_credit?: boolean;
  credit_cost?: number;
  messages_used?: number;
  messages_remaining?: number;
  message_limit?: number;
  consultation_message_count?: number;
}

const USER_MESSAGE_MAX_CHARS = 500;
const MESSAGE_COOLDOWN_SECONDS = 12;

const TIER_MESSAGE_LIMITS: Record<string, number> = {
  free: 15,
  basic: 30,
  standard: 50,
  pro: 50,
  premium: 100,
  professional: 250,
  enterprise: 250,
};

const normalizeTier = (tier?: string): string => {
  const raw = (tier || "free").toLowerCase();
  if (raw === "starter") return "basic";
  if (raw === "creator") return "standard";
  return raw;
};

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
  onSkip,
  onCancel,
}: AIConsultationModalProps) {
  const { user } = useAuth();
  const normalizedTier = normalizeTier(user?.subscription_tier);
  const tierLimit = TIER_MESSAGE_LIMITS[normalizedTier] ?? TIER_MESSAGE_LIMITS.free;

  const [isAnalyzing, setIsAnalyzing] = useState(true);
  const [messages, setMessages] = useState<ConsultationMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [analysis, setAnalysis] = useState<ContentAnalysis | null>(null);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const [projectConfig, setProjectConfig] = useState<Partial<ProjectConfig>>({});
  const [readyToCreate, setReadyToCreate] = useState(false);
  const [hasUnansweredQuestions, setHasUnansweredQuestions] = useState(false);
  const [cooldownRemaining, setCooldownRemaining] = useState(0);

  const [fileSummary, setFileSummary] = useState("");
  const [messagesUsed, setMessagesUsed] = useState(0);
  const [messagesRemaining, setMessagesRemaining] = useState(tierLimit);
  const [messageLimit, setMessageLimit] = useState(tierLimit);
  const [sessionMessageCount, setSessionMessageCount] = useState(0);
  const [capReached, setCapReached] = useState(false);

  const [showCreditConfirm, setShowCreditConfirm] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [pendingCreditCost, setPendingCreditCost] = useState(1);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    analyzeFiles();
  }, []);

  useEffect(() => {
    setMessageLimit(tierLimit);
    setMessagesRemaining((prev) => (messagesUsed > 0 ? prev : tierLimit));
  }, [tierLimit, messagesUsed]);

  useEffect(() => {
    if (cooldownRemaining <= 0) return;

    const interval = setInterval(() => {
      setCooldownRemaining((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(interval);
  }, [cooldownRemaining]);

  const analyzeFiles = async () => {
    setIsAnalyzing(true);
    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      if (initialPrompt) {
        formData.append("prompt", initialPrompt);
      }

      const data = await apiClient.upload<{
        status: string;
        content_analysis?: ContentAnalysis;
        ai_message?: string;
        suggested_actions?: SuggestedAction[];
        recommended_action?: string;
        file_summary?: string;
      }>("/ai/consultation/analyze", formData);

      if (data.content_analysis) {
        setAnalysis(data.content_analysis);
      }
      setFileSummary(data.file_summary || "");
      // Analysis consumes the first consultation message.
      setMessagesUsed(1);
      setMessagesRemaining(Math.max(0, messageLimit - 1));

      const aiMessage: ConsultationMessage = {
        role: "assistant",
        content:
          data.ai_message ||
          `I've analyzed your ${files.length > 1 ? "files" : "file"}. What would you like to create?`,
        actions: data.suggested_actions || [],
        timestamp: new Date(),
      };

      setMessages([aiMessage]);

      if (data.recommended_action) {
        setSelectedAction(data.recommended_action);
      }
    } catch (error) {
      console.error("Analysis failed:", error);
      setMessages([
        {
          role: "assistant",
          content:
            "I had trouble analyzing your files. Would you like to tell me what you'd like to create?",
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

  const applyUsageFromResponse = (data: ConsultationChatResponse) => {
    const nextLimit = data.message_limit ?? messageLimit;
    const nextUsed = data.messages_used ?? messagesUsed;
    const nextRemaining =
      data.messages_remaining ?? Math.max(0, nextLimit - nextUsed);

    setMessageLimit(nextLimit);
    setMessagesUsed(nextUsed);
    setMessagesRemaining(nextRemaining);

    if (typeof data.consultation_message_count === "number") {
      setSessionMessageCount(data.consultation_message_count);
    } else {
      setSessionMessageCount(nextUsed);
    }
  };

  const sendMessage = async (
    content: string,
    options?: { creditConfirmed?: boolean; force?: boolean }
  ) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    if (trimmed.length > USER_MESSAGE_MAX_CHARS || cooldownRemaining > 0) {
      return;
    }

    const isPaidTier = normalizedTier !== "free";
    if (!options?.force && messagesRemaining <= 0 && isPaidTier) {
      setPendingMessage(trimmed);
      setPendingCreditCost(1);
      setShowCreditConfirm(true);
      return;
    }

    if (!options?.force && messagesRemaining <= 0 && !isPaidTier) {
      setCapReached(true);
      return;
    }

    const userMessage: ConsultationMessage = {
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };
    const nextMessages = [...messages, userMessage];

    setMessages(nextMessages);
    setInputValue("");
    setIsTyping(true);

    try {
      const data = await apiClient.post<ConsultationChatResponse>(
        "/ai/consultation/chat",
        {
          message: trimmed,
          context: {
            messages: nextMessages.map((m) => ({ role: m.role, content: m.content })),
            file_summary: fileSummary,
            consultation_message_count: sessionMessageCount,
            credit_confirmed: options?.creditConfirmed || false,
          },
        }
      );
      setCooldownRemaining(MESSAGE_COOLDOWN_SECONDS);
      applyUsageFromResponse(data);

      if (data.cap_reached) {
        setCapReached(true);
      }

      if (data.requires_credit && !options?.creditConfirmed) {
        setPendingMessage(trimmed);
        setPendingCreditCost(data.credit_cost || 1);
        setShowCreditConfirm(true);
        return;
      }

      const aiMessage: ConsultationMessage = {
        role: "assistant",
        content: data.ai_message || "I understand. Let me help you with that.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);

      const hasQuestions =
        data.follow_up_questions && data.follow_up_questions.length > 0;
      setHasUnansweredQuestions(hasQuestions || false);

      if (data.ready_to_proceed && data.project_config) {
        setProjectConfig({
          projectType: (data.project_config.project_type ||
            "entertainment") as "entertainment" | "training" | "marketing",
          contentType: data.project_config.content_type || "single_script",
          terminology: (data.project_config.terminology ||
            "Film") as "Film" | "Episode" | "Part" | "Module",
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

  const handleSkipAndCreate = () => {
    if (onSkip) {
      onSkip();
      return;
    }
    handleCreateProject();
  };

  const handleActionClick = async (action: SuggestedAction) => {
    if (action.disabled) return;

    setSelectedAction(action.id);

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

    const config = configMap[action.id] || {
      projectType: "entertainment",
      contentType: action.id,
    };
    setProjectConfig(config);

    await sendMessage(`I want to ${action.label.toLowerCase()}`);
  };

  const handleCreateProject = () => {
    const conversationData = {
      conversation: messages.map((m) => ({ role: m.role, content: m.content })),
      agreements: {
        universe_name: projectConfig.universeName || analysis?.title,
        terminology: projectConfig.terminology || "Film",
        content_type: projectConfig.contentType,
      },
    };

    if (!projectConfig.projectType || !projectConfig.contentType) {
      onComplete({
        projectType: "entertainment",
        contentType: selectedAction || "single_script",
        terminology: "Film",
        universeName: analysis?.title,
        consultationData: conversationData,
      });
      return;
    }

    onComplete({
      projectType: projectConfig.projectType,
      contentType: projectConfig.contentType,
      terminology: projectConfig.terminology || "Film",
      universeName: projectConfig.universeName || analysis?.title,
      consultationData: conversationData,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col border border-gray-200 dark:border-gray-700 overflow-hidden">
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
              <p className="text-xs text-purple-700 dark:text-purple-300 mt-1">
                {messagesUsed}/{messageLimit} messages used
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSkipAndCreate}
              className="px-3 py-2 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              Skip & Create
            </button>
            <button
              onClick={onCancel}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

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

        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <div className="flex items-center justify-between mb-2 text-xs">
            <span
              className={
                inputValue.length > USER_MESSAGE_MAX_CHARS
                  ? "text-red-500"
                  : "text-gray-500 dark:text-gray-400"
              }
            >
              {inputValue.length}/{USER_MESSAGE_MAX_CHARS}
            </span>
            <div className="flex items-center gap-3">
              <span className="text-gray-500 dark:text-gray-400">
                {messagesRemaining} remaining
              </span>
              {cooldownRemaining > 0 && (
                <span className="text-amber-600 dark:text-amber-400">
                  Please wait {cooldownRemaining}s
                </span>
              )}
            </div>
          </div>

          {capReached && normalizedTier === "free" && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-900/20 p-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">
                  Free message cap reached
                </p>
                <p className="text-xs text-amber-800 dark:text-amber-300">
                  Upgrade your plan to continue chatting, or create your project now.
                </p>
              </div>
              <button
                onClick={() => {
                  window.location.href = "/subscription";
                }}
                className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium"
              >
                Upgrade
              </button>
            </div>
          )}
          <div className="flex gap-2">
            {!(capReached && normalizedTier === "free") && (
              <>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value.slice(0, USER_MESSAGE_MAX_CHARS))}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void sendMessage(inputValue);
                    }
                  }}
                  placeholder="Type a message or select an option above..."
                  className="flex-1 px-4 py-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900 dark:text-white placeholder-gray-400"
                  disabled={isAnalyzing || isTyping}
                />
                <button
                  onClick={() => sendMessage(inputValue)}
                  disabled={!inputValue.trim() || isAnalyzing || isTyping || cooldownRemaining > 0}
                  className="p-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-colors"
                >
                  <Send className="h-5 w-5" />
                </button>
              </>
            )}
            <button
              onClick={handleSkipAndCreate}
              className="px-4 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-100 rounded-xl font-medium transition-colors"
            >
              Skip & Create
            </button>
            {(readyToCreate || (capReached && messages.length > 1)) && (
              <button
                onClick={handleCreateProject}
                className="px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg"
              >
                <Sparkles className="h-5 w-5" />
                Create Project
              </button>
            )}
            {!readyToCreate && selectedAction && !hasUnansweredQuestions && (
              <button
                onClick={handleCreateProject}
                className="px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-xl font-medium flex items-center gap-2 transition-colors"
              >
                <Check className="h-4 w-4" />
                Confirm & Create
              </button>
            )}
          </div>
        </div>
      </div>

      {showCreditConfirm && (
        <div className="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4">
          <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900 p-5 shadow-xl">
            <div className="flex items-center gap-2 mb-2">
              <div className="rounded-full bg-amber-100 p-2 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                <Coins className="h-4 w-4" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">Credit Required</h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
              Continue for {pendingCreditCost} credit?
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowCreditConfirm(false);
                  setPendingMessage(null);
                }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const toSend = pendingMessage;
                  setShowCreditConfirm(false);
                  setPendingMessage(null);
                  if (toSend) {
                    void sendMessage(toSend, { creditConfirmed: true, force: true });
                  }
                }}
                className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AIConsultationModal;
