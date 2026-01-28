import React, { useState, useEffect, useRef } from "react";
import {
  Loader2,
  Sparkles,
  Check,
  ChevronDown,
  ChevronRight,
  GripVertical,
  Film,
  Tv,
  Layers,
  Edit2,
  RefreshCw,
  Send,
  MessageSquare,
  FileText,
  Eye,
  Wand2,
  ArrowRight,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { apiClient } from "../../lib/api";

interface ConsultationPanelProps {
  projectId: string;
  inputPrompt?: string;
  onConsultationComplete?: (result: ConsultationResult) => void;
  onSkip?: () => void;
  onNavigateToScript?: (artifactId: string) => void;
}

interface Script {
  order: number;
  original_filename: string;
  suggested_title: string;
  role_in_universe: string;
  key_connections: string[];
}

interface Phase {
  phase_number: number;
  title: string;
  description: string;
  scripts: Script[];
}

interface ConsultationResult {
  suggested_names: string[];
  recommended_starting_point?: {
    filename: string;
    reason: string;
  };
  content_type: "film" | "series" | "anthology";
  content_type_label: string;
  phases: Phase[];
  shared_elements?: {
    characters: string[];
    themes: string[];
    mythology: string[];
  };
  expansion_opportunities?: string[];
  ai_commentary: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

interface MaterialArtifact {
  id: string;
  content: {
    title: string;
    content: string;
    chapter_number?: number;
  };
  source_file_url?: string;
  content_type_label?: string;
  script_order?: number;
}

type ActiveSection = "overview" | "chat" | "materials";

const CONTENT_TYPE_OPTIONS = [
  { value: "Film", icon: Film, label: "Film Series" },
  { value: "Episode", icon: Tv, label: "TV Series" },
  { value: "Part", icon: Layers, label: "Anthology/Parts" },
];

const ConsultationPanel: React.FC<ConsultationPanelProps> = ({
  projectId,
  inputPrompt,
  onConsultationComplete,
  onSkip,
  onNavigateToScript,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isAccepting, setIsAccepting] = useState(false);
  const [consultation, setConsultation] = useState<ConsultationResult | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [_hasSavedData, setHasSavedData] = useState(false);

  // Editable state
  const [selectedName, setSelectedName] = useState("");
  const [customName, setCustomName] = useState("");
  const [isEditingName, setIsEditingName] = useState(false);
  const [contentTypeLabel, setContentTypeLabel] = useState("Film");
  const [phases, setPhases] = useState<Phase[]>([]);
  const [expandedPhases, setExpandedPhases] = useState<Set<number>>(new Set());

  // Section navigation
  const [activeSection, setActiveSection] = useState<ActiveSection>("overview");

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isSendingChat, setIsSendingChat] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Materials state
  const [materials, setMaterials] = useState<MaterialArtifact[]>([]);
  const [expandedMaterial, setExpandedMaterial] = useState<string | null>(null);
  const [isLoadingMaterials, setIsLoadingMaterials] = useState(false);

  // Storyline completion state
  const [isExpandingStoryline, setIsExpandingStoryline] = useState<string | null>(null);

  // Scroll chat to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Fetch consultation analysis
  const fetchConsultation = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.post<{
        status: string;
        consultation?: ConsultationResult;
        error?: string;
      }>(
        `/projects/${projectId}/consultation`,
        {
          user_prompt: inputPrompt,
        }
      );

      if (response.status === "success" && response.consultation) {
        const result = response.consultation as ConsultationResult;
        setConsultation(result);

        if (result.suggested_names && result.suggested_names.length > 0) {
          setSelectedName(result.suggested_names[0]);
        }
        if (result.content_type_label) {
          setContentTypeLabel(result.content_type_label);
        }
        if (result.phases) {
          setPhases(result.phases);
          setExpandedPhases(new Set([1]));
        }
      } else {
        setError(response.error || "Failed to analyze scripts");
      }
    } catch (e) {
      console.error("Consultation error:", e);
      setError("Failed to analyze scripts. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Load saved consultation first, or fetch fresh if none exists
  const loadSavedConsultation = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const savedResponse = await apiClient.get<{
        status: string;
        consultation?: ConsultationResult;
        conversation?: Array<{ role: string; content: string }>;
        agreements?: {
          universe_name?: string;
          terminology?: string;
        };
      }>(
        `/projects/${projectId}/consultation/saved`
      );

      if (savedResponse.status === "success" && savedResponse.consultation) {
        const result = savedResponse.consultation as ConsultationResult;
        setConsultation(result);
        setHasSavedData(true);

        if (result.suggested_names && result.suggested_names.length > 0) {
          setSelectedName(savedResponse.agreements?.universe_name || result.suggested_names[0]);
        }
        if (result.content_type_label || savedResponse.agreements?.terminology) {
          setContentTypeLabel(savedResponse.agreements?.terminology || result.content_type_label || "Film");
        }
        if (result.phases) {
          setPhases(result.phases);
          setExpandedPhases(new Set([1]));
        }
        // Restore conversation history if available
        if (savedResponse.conversation && savedResponse.conversation.length > 0) {
          setChatMessages(
            savedResponse.conversation.map((msg) => ({
              role: msg.role as "user" | "assistant",
              content: msg.content,
            }))
          );
        }
        setIsLoading(false);
        return;
      }

      await fetchConsultation();
    } catch (e) {
      console.error("Failed to load saved consultation:", e);
      await fetchConsultation();
    }
  };

  // Load project materials/artifacts
  const loadMaterials = async () => {
    setIsLoadingMaterials(true);
    try {
      const response = await apiClient.get<{
        artifacts?: MaterialArtifact[];
        // Handle both response shapes
        [key: string]: any;
      }>(`/projects/${projectId}`);

      const artifacts = response.artifacts || [];
      const chapterArtifacts = artifacts.filter(
        (a: any) => a.artifact_type === "CHAPTER" || a.artifact_type === "chapter"
      );
      setMaterials(chapterArtifacts);
    } catch (e) {
      console.error("Failed to load materials:", e);
    } finally {
      setIsLoadingMaterials(false);
    }
  };

  useEffect(() => {
    loadSavedConsultation();
    loadMaterials();
  }, [projectId]);

  const handleAccept = async () => {
    if (!consultation) return;

    setIsAccepting(true);

    try {
      const universeName = isEditingName ? customName : selectedName;

      const response = await apiClient.put<{ status: string }>(
        `/projects/${projectId}/consultation/accept`,
        {
          universe_name: universeName,
          content_type_label: contentTypeLabel,
          phases: phases,
        }
      );

      if (response.status === "success") {
        toast.success("Cinematic universe structure applied!");
        onConsultationComplete?.({
          ...consultation,
          content_type_label: contentTypeLabel,
          phases: phases,
        });
      } else {
        toast.error("Failed to apply structure");
      }
    } catch (e) {
      console.error("Accept error:", e);
      toast.error("Failed to apply structure. Please try again.");
    } finally {
      setIsAccepting(false);
    }
  };

  // Send chat message to continue/refine consultation
  const handleSendChat = async () => {
    if (!chatInput.trim() || isSendingChat) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: chatInput.trim(),
      timestamp: new Date().toISOString(),
    };

    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    setIsSendingChat(true);

    try {
      const response = await apiClient.post<{
        status: string;
        ai_message?: string;
        ready_to_proceed?: boolean;
        project_config?: {
          universe_name?: string;
          terminology?: string;
        };
        follow_up_questions?: string[];
        error?: string;
      }>(`/projects/${projectId}/consultation/chat`, {
        message: userMessage.content,
        conversation_history: chatMessages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      });

      if (response.ai_message) {
        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: response.ai_message,
          timestamp: new Date().toISOString(),
        };
        setChatMessages((prev) => [...prev, assistantMessage]);

        // Update consultation state if AI suggests changes
        if (response.project_config?.universe_name) {
          setSelectedName(response.project_config.universe_name);
        }
        if (response.project_config?.terminology) {
          setContentTypeLabel(response.project_config.terminology);
        }
      }
    } catch (e) {
      console.error("Chat error:", e);
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: "Sorry, I had trouble processing that. Please try again.",
        timestamp: new Date().toISOString(),
      };
      setChatMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsSendingChat(false);
    }
  };

  // AI-assisted storyline expansion for a material
  const handleExpandStoryline = async (material: MaterialArtifact) => {
    setIsExpandingStoryline(material.id);
    try {
      const response = await apiClient.post<{
        status: string;
        ai_message?: string;
        error?: string;
      }>(`/projects/${projectId}/consultation/chat`, {
        message: `Please analyze and suggest storyline expansions for "${material.content.title}". Here's a summary of the content: ${material.content.content.substring(0, 1000)}. What plot gaps exist? What storyline threads could be developed further? Suggest 3-5 specific expansion opportunities.`,
        conversation_history: chatMessages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      });

      if (response.ai_message) {
        // Add to chat and switch to chat view
        const userMsg: ChatMessage = {
          role: "user",
          content: `Analyze storyline for "${material.content.title}"`,
          timestamp: new Date().toISOString(),
        };
        const aiMsg: ChatMessage = {
          role: "assistant",
          content: response.ai_message,
          timestamp: new Date().toISOString(),
        };
        setChatMessages((prev) => [...prev, userMsg, aiMsg]);
        setActiveSection("chat");
      }
    } catch (e) {
      console.error("Storyline expansion error:", e);
      toast.error("Failed to analyze storyline");
    } finally {
      setIsExpandingStoryline(null);
    }
  };

  const togglePhase = (phaseNumber: number) => {
    const newExpanded = new Set(expandedPhases);
    if (newExpanded.has(phaseNumber)) {
      newExpanded.delete(phaseNumber);
    } else {
      newExpanded.add(phaseNumber);
    }
    setExpandedPhases(newExpanded);
  };

  if (isLoading) {
    return (
      <div className="consultation-panel flex flex-col items-center justify-center min-h-[400px] p-8">
        <div className="relative mb-6">
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full blur-xl opacity-30 animate-pulse" />
          <Sparkles className="w-16 h-16 text-purple-400 animate-spin-slow relative z-10" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">
          Analyzing Your Cinematic Universe
        </h2>
        <p className="text-gray-400 text-center max-w-md">
          Our AI is reviewing your scripts to suggest the perfect structure for
          your cinematic universe...
        </p>
        <div className="flex items-center gap-2 mt-4 text-purple-400">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>This may take a minute</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="consultation-panel flex flex-col items-center justify-center min-h-[400px] p-8">
        <div className="text-red-400 mb-4 text-center">
          <p className="text-lg font-semibold">Analysis Failed</p>
          <p className="text-sm text-gray-400 mt-2">{error}</p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={fetchConsultation}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
          {onSkip && (
            <button
              onClick={onSkip}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              Skip Consultation
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!consultation) {
    return null;
  }

  // Section navigation tabs
  const sectionTabs = [
    { id: "overview" as ActiveSection, label: "Setup Overview", icon: Sparkles },
    { id: "chat" as ActiveSection, label: "Refine with AI", icon: MessageSquare },
    { id: "materials" as ActiveSection, label: "Materials", icon: FileText },
  ];

  return (
    <div className="consultation-panel p-6 space-y-6">
      {/* Header */}
      <div className="text-center mb-4">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-full mb-4">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <span className="text-purple-300 font-medium">AI Consultation</span>
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">
          Cinematic Universe Setup
        </h1>
        <p className="text-gray-400 max-w-2xl mx-auto">
          Review AI suggestions, refine your vision through conversation, and review uploaded materials.
        </p>
      </div>

      {/* Section Tabs */}
      <div className="flex gap-2 border-b border-gray-700 pb-0">
        {sectionTabs.map((tab) => {
          const isActive = activeSection === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? "border-purple-500 text-purple-400"
                  : "border-transparent text-gray-400 hover:text-gray-200"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {tab.id === "chat" && chatMessages.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-purple-500/20 text-purple-300 rounded-full">
                  {chatMessages.length}
                </span>
              )}
              {tab.id === "materials" && materials.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-gray-600 text-gray-300 rounded-full">
                  {materials.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ===== OVERVIEW SECTION ===== */}
      {activeSection === "overview" && (
        <div className="space-y-8">
          {/* Universe Name Selection */}
          <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-400" />
              Universe Name
            </h3>

            {!isEditingName ? (
              <div className="space-y-3">
                {consultation.suggested_names.map((name, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedName(name)}
                    className={`w-full text-left p-4 rounded-lg border transition-all ${
                      selectedName === name
                        ? "border-purple-500 bg-purple-500/10"
                        : "border-gray-600 hover:border-gray-500 bg-gray-800/50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-white font-medium">{name}</span>
                      {selectedName === name && (
                        <Check className="w-5 h-5 text-purple-400" />
                      )}
                    </div>
                  </button>
                ))}
                <button
                  onClick={() => {
                    setIsEditingName(true);
                    setCustomName(selectedName);
                  }}
                  className="flex items-center gap-2 text-purple-400 hover:text-purple-300 text-sm mt-2"
                >
                  <Edit2 className="w-4 h-4" />
                  Use custom name
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="Enter your universe name..."
                  className="w-full p-4 bg-gray-900 border border-gray-600 rounded-lg text-white focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                  autoFocus
                />
                <button
                  onClick={() => setIsEditingName(false)}
                  className="text-sm text-gray-400 hover:text-white"
                >
                  Back to suggestions
                </button>
              </div>
            )}
          </div>

          {/* Content Type Selection */}
          <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Content Type</h3>
            <p className="text-sm text-gray-400 mb-4">
              How should each entry in your universe be labeled?
            </p>
            <div className="grid grid-cols-3 gap-4">
              {CONTENT_TYPE_OPTIONS.map(({ value, icon: Icon, label }) => (
                <button
                  key={value}
                  onClick={() => setContentTypeLabel(value)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-lg border transition-all ${
                    contentTypeLabel === value
                      ? "border-purple-500 bg-purple-500/10"
                      : "border-gray-600 hover:border-gray-500"
                  }`}
                >
                  <Icon
                    className={`w-8 h-8 ${
                      contentTypeLabel === value
                        ? "text-purple-400"
                        : "text-gray-400"
                    }`}
                  />
                  <span
                    className={`text-sm font-medium ${
                      contentTypeLabel === value ? "text-white" : "text-gray-300"
                    }`}
                  >
                    {label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Phase Structure */}
          <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">
              Phase Structure
            </h3>
            <p className="text-sm text-gray-400 mb-4">
              {consultation.recommended_starting_point && (
                <>
                  <span className="text-purple-400 font-medium">
                    Recommended start:
                  </span>{" "}
                  {consultation.recommended_starting_point.filename} —{" "}
                  {consultation.recommended_starting_point.reason}
                </>
              )}
            </p>

            <div className="space-y-4">
              {phases.map((phase) => (
                <div
                  key={phase.phase_number}
                  className="border border-gray-700 rounded-lg overflow-hidden"
                >
                  <button
                    onClick={() => togglePhase(phase.phase_number)}
                    className="w-full flex items-center justify-between p-4 bg-gray-900/50 hover:bg-gray-800/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="px-3 py-1 bg-purple-500/20 text-purple-300 text-sm font-medium rounded-full">
                        Phase {phase.phase_number}
                      </span>
                      <span className="text-white font-medium">{phase.title}</span>
                    </div>
                    {expandedPhases.has(phase.phase_number) ? (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    )}
                  </button>

                  {expandedPhases.has(phase.phase_number) && (
                    <div className="p-4 space-y-3 border-t border-gray-700">
                      <p className="text-sm text-gray-400 mb-4">
                        {phase.description}
                      </p>
                      {phase.scripts.map((script, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-3 p-3 bg-gray-900/30 rounded-lg"
                        >
                          <GripVertical className="w-4 h-4 text-gray-500 cursor-grab" />
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-gray-500">
                                {contentTypeLabel} {script.order}
                              </span>
                              <span className="text-white font-medium">
                                {script.suggested_title}
                              </span>
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {script.original_filename} • {script.role_in_universe}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* AI Commentary */}
          {consultation.ai_commentary && (
            <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-xl p-6 border border-purple-500/20">
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-400" />
                AI Insights
              </h3>
              <p className="text-gray-300 whitespace-pre-wrap">
                {consultation.ai_commentary}
              </p>
            </div>
          )}

          {/* Shared Elements */}
          {consultation.shared_elements && (
            <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4">
                Shared Universe Elements
              </h3>
              <div className="grid grid-cols-3 gap-6">
                {consultation.shared_elements.characters.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-purple-400 mb-2">
                      Characters
                    </h4>
                    <ul className="space-y-1">
                      {consultation.shared_elements.characters.map((char, idx) => (
                        <li key={idx} className="text-sm text-gray-300">
                          {char}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {consultation.shared_elements.themes.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-purple-400 mb-2">
                      Themes
                    </h4>
                    <ul className="space-y-1">
                      {consultation.shared_elements.themes.map((theme, idx) => (
                        <li key={idx} className="text-sm text-gray-300">
                          {theme}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {consultation.shared_elements.mythology.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-purple-400 mb-2">
                      Mythology
                    </h4>
                    <ul className="space-y-1">
                      {consultation.shared_elements.mythology.map((myth, idx) => (
                        <li key={idx} className="text-sm text-gray-300">
                          {myth}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Expansion Opportunities */}
          {consultation.expansion_opportunities && consultation.expansion_opportunities.length > 0 && (
            <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Wand2 className="w-5 h-5 text-purple-400" />
                Expansion Opportunities
              </h3>
              <ul className="space-y-2">
                {consultation.expansion_opportunities.map((opp, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-300">
                    <ArrowRight className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
                    {opp}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ===== CHAT SECTION - Continue/Refine Consultation ===== */}
      {activeSection === "chat" && (
        <div className="flex flex-col h-[600px]">
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
            {chatMessages.length === 0 && (
              <div className="text-center py-12">
                <MessageSquare className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">
                  Continue the Conversation
                </h3>
                <p className="text-gray-400 max-w-md mx-auto mb-6">
                  Ask the AI to refine your universe structure, explore storyline ideas,
                  or adjust recommendations.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {[
                    "Suggest alternative phase structures",
                    "What storylines could connect these scripts?",
                    "How should the timeline flow?",
                    "Suggest character arcs across films",
                  ].map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => setChatInput(suggestion)}
                      className="px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-300 hover:border-purple-500 hover:text-purple-300 transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-purple-600 text-white"
                      : "bg-gray-800 border border-gray-700 text-gray-200"
                  }`}
                >
                  {msg.role === "assistant" && (
                    <div className="flex items-center gap-2 mb-1">
                      <Sparkles className="w-3 h-3 text-purple-400" />
                      <span className="text-xs text-purple-400 font-medium">AI Consultant</span>
                    </div>
                  )}
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}

            {isSendingChat && (
              <div className="flex justify-start">
                <div className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                    <span className="text-sm text-gray-400">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div className="border-t border-gray-700 pt-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendChat();
                  }
                }}
                placeholder="Ask the AI to refine your universe setup..."
                className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                disabled={isSendingChat}
              />
              <button
                onClick={handleSendChat}
                disabled={!chatInput.trim() || isSendingChat}
                className="px-4 py-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===== MATERIALS SECTION - Review Uploaded Scripts ===== */}
      {activeSection === "materials" && (
        <div className="space-y-4">
          {isLoadingMaterials ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-purple-400" />
              <span className="ml-3 text-gray-400">Loading materials...</span>
            </div>
          ) : materials.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No Materials Found</h3>
              <p className="text-gray-400">
                No uploaded scripts or documents were found for this project.
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold text-white">
                  Uploaded Materials ({materials.length})
                </h3>
              </div>

              {materials.map((material) => {
                const isExpanded = expandedMaterial === material.id;
                const isExpanding = isExpandingStoryline === material.id;
                const preview = material.content.content?.substring(0, 300) || "";

                return (
                  <div
                    key={material.id}
                    className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden"
                  >
                    {/* Material Header */}
                    <div
                      className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-800/80 transition-colors"
                      onClick={() =>
                        setExpandedMaterial(isExpanded ? null : material.id)
                      }
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-gray-400" />
                        <div>
                          <h4 className="text-white font-medium">
                            {material.content.title}
                          </h4>
                          <p className="text-xs text-gray-500">
                            {material.content_type_label || "Script"}{" "}
                            {material.script_order || material.content.chapter_number || ""}
                            {material.source_file_url && (
                              <span className="ml-2">
                                {material.source_file_url.split("/").pop()}
                              </span>
                            )}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {/* AI Storyline Expansion Button */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleExpandStoryline(material);
                          }}
                          disabled={isExpanding}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-purple-400 bg-purple-500/10 hover:bg-purple-500/20 rounded-lg transition-colors disabled:opacity-50"
                          title="AI storyline analysis"
                        >
                          {isExpanding ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Wand2 className="w-3 h-3" />
                          )}
                          Analyze Story
                        </button>

                        {/* View in Script Tab Button */}
                        {onNavigateToScript && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onNavigateToScript(material.id);
                            }}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                            title="View in Script tab"
                          >
                            <ArrowRight className="w-3 h-3" />
                            Script Tab
                          </button>
                        )}

                        {isExpanded ? (
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronRight className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                    </div>

                    {/* Expanded Material Content */}
                    {isExpanded && (
                      <div className="border-t border-gray-700 p-4">
                        <div className="bg-gray-900/50 rounded-lg p-4 max-h-96 overflow-y-auto">
                          <pre className="whitespace-pre-wrap text-sm text-gray-300 font-mono leading-relaxed">
                            {material.content.content || "No content available"}
                          </pre>
                        </div>
                        {!isExpanded && preview && (
                          <p className="text-sm text-gray-400 mt-2">
                            {preview}...
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}

      {/* Action Buttons - Always visible */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-700">
        <button
          onClick={fetchConsultation}
          className="flex items-center gap-2 px-4 py-2 text-gray-400 hover:text-white transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Regenerate Suggestions
        </button>
        <div className="flex gap-4">
          {onSkip && (
            <button
              onClick={onSkip}
              className="px-6 py-3 text-gray-400 hover:text-white transition-colors"
            >
              Skip
            </button>
          )}
          <button
            onClick={handleAccept}
            disabled={isAccepting || (!selectedName && !customName)}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isAccepting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Applying...
              </>
            ) : (
              <>
                <Check className="w-5 h-5" />
                Accept & Continue
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConsultationPanel;
