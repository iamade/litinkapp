import React, { useState, useRef } from "react";
import { 
  Sparkles, 
  Upload, 
  ArrowRight, 
  Loader2, 
  Video, 
  BookOpen, 
  FileText,
  Mic,
  MonitorPlay,
  File as FileIcon,
  X,
  CheckCircle2,
  Trash2
} from "lucide-react";
import { projectService, IntentAnalysisResult, Project } from "../../services/projectService";
import { toast } from "react-hot-toast";
import ProjectFolder from "./ProjectFolder";
import { checkFileAccessible } from "../../lib/fileValidation";
import { AIConsultationModal } from "../Consultation/AIConsultationModal";
import UploadProgress from "./UploadProgress";

interface UploadedBook {
  id: string;
  title: string;
  status: string;
}

export default function CreatorStudio() {
  const [prompt, setPrompt] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<IntentAnalysisResult | null>(null);
  
  // File Upload State
  const fileInputRef = useRef<HTMLInputElement>(null);
  // const [isUploading, setIsUploading] = useState(false); // Unused now
  const [uploadedBook, setUploadedBook] = useState<UploadedBook | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [recentProjects, setRecentProjects] = useState<any[]>([]);
  
  // Upload progress state
  const [uploadingProjectId, setUploadingProjectId] = useState<string | null>(null);

  // Delete confirmation modal state
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch recent projects
  React.useEffect(() => {
    const fetchProjects = async () => {
      try {
        const projects = await projectService.getProjects();
        setRecentProjects(projects);
      } catch (e) {
        console.error("Failed to fetch projects", e);
      }
    };
    fetchProjects();
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    const newFiles: File[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      // Validate file accessibility (catches iCloud files not downloaded locally)
      const validationResult = await checkFileAccessible(file);
      if (!validationResult.accessible) {
        toast.error(`${file.name}: ${validationResult.error || "File is not accessible"}`);
        continue;
      }
      newFiles.push(file);
    }
    
    if (newFiles.length > 0) {
      // Append to existing selection
      setSelectedFiles(prev => [...prev, ...newFiles]);
      // Reset uploaded book state and analysis when files change
      setUploadedBook(null);
      setAnalysis(null);
    }
    
    // Reset the file input so the same file can be selected again if needed
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  /* 
     REMOVED: Old uploadFile logic that created a Book. 
     Now we handle uploads directly during project creation.
  */

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  // State for AI Consultation Modal
  const [showConsultationModal, setShowConsultationModal] = useState(false);

  const handleAnalyze = async () => {
    if (!prompt.trim() && selectedFiles.length === 0) return;

    setIsAnalyzing(true);
    try {
      if (selectedFiles.length > 0) {
        // Unified flow: all file uploads go through AI consultation
        setShowConsultationModal(true);
        setIsAnalyzing(false);
        return;
      }
      
      // Text-only flow keeps intent analysis preview
      const fileNames = selectedFiles.map(f => f.name).join(', ');
      const textToAnalyze = prompt || (selectedFiles.length > 0 ? `Create a project from the files: ${fileNames}` : "");
      
      const result = await projectService.analyzeIntent(textToAnalyze);
      setAnalysis(result);
      toast.success(`Detected intent: ${result.primary_intent}`);
    } catch (error) {
      console.error(error);
      toast.error("Could not analyze intent.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle consultation modal completion
  const handleConsultationComplete = async (config: {
    projectType: string;
    contentType: string;
    terminology: string;
    universeName?: string;
    consultationData?: {
      conversation: Array<{ role: string; content: string }>;
      agreements: {
        universe_name?: string;
        phases?: any[];
        terminology?: string;
        content_type?: string;
      };
    };
  }) => {
    setShowConsultationModal(false);

    try {
      const data = await projectService.createProjectFromUpload(
        selectedFiles,
        config.projectType,
        prompt,
        {
          content_terminology: config.terminology,
          universe_name: config.universeName,
          content_type: config.contentType,
          consultation_data: config.consultationData,
        }
      );
      setUploadingProjectId(data.project_id);
    } catch (e) {
      console.error(e);
      toast.error("Failed to create project.");
    }
  };

  const handleCreateProject = async () => {
    if (!analysis) return;

    try {
      if (selectedFiles.length > 0) {
        const data = await projectService.createProjectFromUpload(
          selectedFiles,
          analysis.primary_intent,
          prompt
        );
        setUploadingProjectId(data.project_id);
      } else {
        // Text-only project: keep simple toast flow
        const loadingToast = toast.loading("Creating your project...");
        try {
          const data = await projectService.createProject({
            title: `Project: ${prompt.slice(0, 20) || "Untitled"}...`,
            input_prompt: prompt,
            project_type: analysis.primary_intent,
            workflow_mode: "creator_interactive",
          });
          toast.success("Project created! Redirecting...", { id: loadingToast });
          window.location.href = `/project/${data.id}`;
        } catch (e) {
          console.error(e);
          toast.error("Failed to create project.", { id: loadingToast });
        }
      }
    } catch (e) {
      console.error(e);
      toast.error("Failed to start project upload.");
    }
  };

  const handleSkipConsultation = async () => {
    if (selectedFiles.length === 0) return;

    setShowConsultationModal(false);
    try {
      const data = await projectService.createProjectFromUpload(
        selectedFiles,
        "entertainment",
        prompt,
        {
          content_terminology: "Film",
          content_type: "single_script",
          universe_name: ((selectedFiles[0]?.name?.split(".").slice(0, -1).join(".")) || selectedFiles[0]?.name) || "Untitled Project",
        }
      );
      setUploadingProjectId(data.project_id);
    } catch (e) {
      console.error(e);
      toast.error("Failed to create project.");
    }
  };

  const handleUploadComplete = (project: Project) => {
    setUploadingProjectId(null);
    toast.success("Project created!");
    window.location.href = `/project/${project.id}`;
  };

  const handleUploadError = (_error: string) => {
    setUploadingProjectId(null);
    setSelectedFiles([]);
    setAnalysis(null);
  };

  const handleDeleteProject = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation(); // Prevent navigation
    setProjectToDelete(projectId);
    setDeleteModalOpen(true);
  };

  const confirmDeleteProject = async () => {
    if (!projectToDelete) return;
    
    setIsDeleting(true);
    try {
      await projectService.deleteProject(projectToDelete);
      setRecentProjects((prev) => prev.filter((p) => p.id !== projectToDelete));
      toast.success("Project deleted");
    } catch (error) {
      console.error(error);
      toast.error("Failed to delete project");
    } finally {
      setIsDeleting(false);
      setDeleteModalOpen(false);
      setProjectToDelete(null);
    }
  };

  if (uploadingProjectId) {
    return (
      <div className="space-y-8">
        <UploadProgress
          projectId={uploadingProjectId}
          onComplete={handleUploadComplete}
          onError={handleUploadError}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="bg-white dark:bg-gray-800/50 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 overflow-hidden transition-colors duration-300">
        <div className="p-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2 flex items-center">
            <Sparkles className="h-6 w-6 text-purple-600 dark:text-purple-400 mr-2" />
            Creator Studio
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-8">
            Upload a book or describe your vision — we'll generate scripts, images, audio, and video for you.
          </p>

          {/* Hidden File Input */}
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            className="hidden" 
            accept=".pdf,.epub,.txt,.docx"
            multiple
          />

          {/* Studio Input Area */}
          <div className="mb-4">
            <div className="relative">
              <textarea
                value={prompt}
                onChange={(e) => {
                   setPrompt(e.target.value);
                   if (analysis) setAnalysis(null); 
                }}
                placeholder={`Try something like:
• "Turn my uploaded novel into a cinematic script with scenes and dialogue"
• "Create an original sci-fi short film about time travel"
• "Generate a training video series on workplace safety from our PDF manual"
• "Write a children's story about a brave little fox and generate illustrations"

You can also just upload a book and we'll handle the rest!`}
                className="w-full h-40 p-4 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none text-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-colors"
              />
              
              <div className="absolute bottom-4 right-4 flex gap-2">
                 <button 
                    onClick={triggerFileUpload}
                    className="p-2 rounded-lg transition-colors flex items-center gap-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700"
                    title="Upload Source Material"
                 >
                  <Upload className="h-5 w-5" />
                </button>
                <button className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors" title="Record Voice">
                  <Mic className="h-5 w-5" />
                </button>
              </div>
            </div>
            
            {/* Attached Files Display - Below Textarea */}
            {(selectedFiles.length > 0 || uploadedBook) && (
              <div className="mt-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider">
                    Attached Files ({selectedFiles.length})
                  </span>
                  {selectedFiles.length > 1 && (
                    <button
                      onClick={() => { setSelectedFiles([]); setAnalysis(null); }}
                      className="text-xs text-gray-500 hover:text-red-500 transition-colors"
                    >
                      Clear all
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedFiles.map((file, index) => (
                    <div 
                      key={`${file.name}-${index}`} 
                      className="flex items-center gap-2 bg-white dark:bg-gray-800 border border-purple-200 dark:border-purple-700 rounded-full px-3 py-1.5 text-sm group"
                    >
                      <FileIcon className="h-3.5 w-3.5 text-purple-600 dark:text-purple-400 flex-shrink-0" />
                      <span className="text-gray-900 dark:text-white truncate max-w-[200px]" title={file.name}>
                        {file.name}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        ({(file.size / 1024).toFixed(0)}KB)
                      </span>
                      <button
                        onClick={() => { setSelectedFiles(prev => prev.filter((_, i) => i !== index)); setAnalysis(null); }}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                        title="Remove file"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                  {uploadedBook && (
                    <div className="flex items-center gap-2 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-full px-3 py-1.5 text-sm">
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
                      <span className="text-gray-900 dark:text-white">{uploadedBook.title}</span>
                      <span className="text-xs text-gray-500">({uploadedBook.status})</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Action Bar */}
          <div className="flex justify-between items-center">
             <div className="flex gap-4 text-sm text-gray-500 dark:text-gray-400">
                <span className="flex items-center gap-1"><BookOpen className="h-4 w-4"/> Books</span>
                <span className="flex items-center gap-1"><FileText className="h-4 w-4"/> Scripts</span>
                <span className="flex items-center gap-1"><Video className="h-4 w-4"/> Video</span>
                <span className="flex items-center gap-1"><MonitorPlay className="h-4 w-4"/> Training</span>
             </div>

             <div className="flex items-center gap-2">
             {selectedFiles.length > 0 && (
               <button
                onClick={handleSkipConsultation}
                disabled={isAnalyzing}
                className="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-4 py-3 rounded-xl font-semibold hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Skip Consultation
              </button>
             )}
             <button
              onClick={selectedFiles.length > 0 ? handleAnalyze : (analysis ? handleCreateProject : handleAnalyze)}
              disabled={isAnalyzing || (!prompt.trim() && selectedFiles.length === 0 && !uploadedBook)}
              className="bg-purple-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-purple-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isAnalyzing ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : selectedFiles.length > 0 ? (
                <>
                  Analyze & Start
                </>
              ) : analysis ? (
                <>
                  Create Project <ArrowRight className="h-5 w-5" />
                </>
              ) : (
                <>
                  Analyze & Start
                </>
              )}
            </button>
            </div>
          </div>

          {/* Analysis Result Preview */}
          {analysis && selectedFiles.length === 0 && (
            <div className="mt-8 bg-purple-50 dark:bg-purple-900/20 rounded-xl p-6 border border-purple-100 dark:border-purple-800 animate-in fade-in slide-in-from-top-4">
               <div className="flex items-center justify-between mb-2">
                 <h3 className="font-bold text-gray-900 dark:text-white">Analysis Results</h3>
                 <button
                   onClick={() => setAnalysis(null)}
                   className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                   title="Dismiss"
                 >
                   <X className="h-4 w-4" />
                 </button>
               </div>
               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                     <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider">Detected Type</span>
                     <div className="text-lg font-medium text-gray-900 dark:text-white capitalize">{analysis.primary_intent.replace('_', ' ')}</div>
                  </div>
                  <div>
                     <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider">Suggested Workflow</span>
                     <div className="text-lg font-medium text-gray-900 dark:text-white capitalize">{analysis.suggested_mode.replace('_', ' ')}</div>
                  </div>
                  <div className="md:col-span-2">
                     <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider">Reasoning</span>
                     <p className="text-gray-700 dark:text-gray-300">{analysis.reasoning}</p>
                  </div>
                  <div className="md:col-span-2">
                     <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider">Pipeline Steps</span>
                     <div className="flex gap-2 mt-1">
                        {analysis.detected_pipeline.map((step, i) => (
                          <span key={i} className="px-3 py-1 bg-white dark:bg-gray-800 border border-purple-100 dark:border-purple-700 rounded-full text-sm text-purple-700 dark:text-purple-300">
                            {step}
                          </span>
                        ))}
                     </div>
                  </div>
               </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Recent Projects Section */}
      {recentProjects.length > 0 && (
        <div className="bg-white dark:bg-gray-800/50 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 p-8 transition-colors duration-300">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <FileText className="h-6 w-6 text-purple-600 dark:text-purple-400 mr-2" />
            Recent Projects
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recentProjects.map((project) => (
              <ProjectFolder 
                key={project.id}
                project={project}
                onDelete={handleDeleteProject}
                onClick={() => window.location.href = `/project/${project.id}`}
              />
            ))}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-in fade-in">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 animate-in zoom-in-95">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-red-100 dark:bg-red-900/30 p-2 rounded-full">
                <Trash2 className="h-6 w-6 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                Delete Project
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-300 mb-6">
              Are you sure you want to delete this project? This action cannot be undone and all associated data will be permanently removed.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setDeleteModalOpen(false);
                  setProjectToDelete(null);
                }}
                disabled={isDeleting}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteProject}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4" />
                    Delete Project
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Consultation Modal */}
      {showConsultationModal && (
        <AIConsultationModal
          files={selectedFiles}
          initialPrompt={prompt}
          onComplete={handleConsultationComplete}
          onSkip={handleSkipConsultation}
          onCancel={() => { setShowConsultationModal(false); setAnalysis(null); }}
        />
      )}
    </div>
  );
}
