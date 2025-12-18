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
import { projectService, IntentAnalysisResult } from "../../services/projectService";
import { toast } from "react-hot-toast";

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
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [recentProjects, setRecentProjects] = useState<any[]>([]);

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

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    // Reset uploaded book if file changes
    setUploadedBook(null);
  };

  /* 
     REMOVED: Old uploadFile logic that created a Book. 
     Now we handle uploads directly during project creation.
  */

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const handleAnalyze = async () => {
    if (!prompt.trim() && !selectedFile) return;

    setIsAnalyzing(true);
    try {
      // Analyze Intent
      const textToAnalyze = prompt || (selectedFile ? `Create a project from the file ${selectedFile.name}` : "");
      
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

  const handleCreateProject = async () => {
    if (!analysis) return;
    
    // Show loading toast
    const loadingToast = toast.loading("Creating your project...");
    
    try {
      let projectId;

      if (selectedFile) {
        // Create project from upload
        // We append the prompt to the upload if available
         const data = await projectService.createProjectFromUpload(selectedFile, analysis.primary_intent, prompt);
         projectId = data.id;
      } else {
        // Create text-only project
        const data = await projectService.createProject({
          title: `Project: ${prompt.slice(0, 20) || "Untitled"}...`, 
          input_prompt: prompt,
          project_type: analysis.primary_intent,
          workflow_mode: "creator_interactive",
        });
        projectId = data.id;
      }
      
      toast.success("Project created! Redirecting...", { id: loadingToast });
      window.location.href = `/project/${projectId}`;
    } catch (e) {
      console.error(e);
      toast.error("Failed to create project.", { id: loadingToast });
    }
  };

  const handleDeleteProject = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation(); // Prevent navigation
    if (!confirm("Are you sure you want to delete this project?")) return;

    try {
      await projectService.deleteProject(projectId);
      setRecentProjects((prev) => prev.filter((p) => p.id !== projectId));
      toast.success("Project deleted");
    } catch (error) {
      console.error(error);
      toast.error("Failed to delete project");
    }
  };

  return (
    <div className="space-y-8">
      <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
        <div className="p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
            <Sparkles className="h-6 w-6 text-purple-600 mr-2" />
            Creator Studio
          </h2>
          <p className="text-gray-600 mb-8">
            The professional workspace for your media projects. Start by describing your vision.
          </p>

          {/* Hidden File Input */}
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            className="hidden" 
            accept=".pdf,.epub,.txt,.docx"
          />

          {/* Studio Input Area */}
          <div className="relative mb-6">
            <textarea
              value={prompt}
              onChange={(e) => {
                 setPrompt(e.target.value);
                 if (analysis) setAnalysis(null); 
              }}
              placeholder="Describe your project in detail. E.g. 'I want to create a training video series about cybersecurity for new employees, using our existing PDF manual...'"
              className="w-full h-40 p-4 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none text-lg"
            />
            
            {/* Attached File Display */}
            {(selectedFile || uploadedBook) && (
              <div className="absolute bottom-16 left-4 right-4 bg-white border border-purple-100 rounded-lg p-2 flex items-center gap-3 shadow-sm animate-in fade-in slide-in-from-bottom-2">
                 <div className="bg-purple-100 p-1 rounded">
                    <FileIcon className="h-4 w-4 text-purple-600" />
                 </div>
                 <div className="flex-1 text-sm">
                    <span className="font-semibold text-gray-900">
                      {selectedFile?.name || uploadedBook?.title}
                    </span>
                    <span className="ml-2 text-xs text-gray-500">
                      ({uploadedBook ? uploadedBook.status : 'Ready to upload'})
                    </span>
                 </div>
                 <button 
                    onClick={() => {
                      setSelectedFile(null);
                      setUploadedBook(null);
                    }} 
                    className="text-gray-400 hover:text-red-500"
                  >
                    <X className="h-4 w-4" />
                 </button>
              </div>
            )}

            <div className="absolute bottom-4 right-4 flex gap-2">
               <button 
                  onClick={triggerFileUpload}
                  className="p-2 rounded-lg transition-colors flex items-center gap-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200"
                  title="Upload Source Material"
               >
                <Upload className="h-5 w-5" />
              </button>
              <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors" title="Record Voice">
                <Mic className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex justify-between items-center">
             <div className="flex gap-4 text-sm text-gray-500">
                <span className="flex items-center gap-1"><BookOpen className="h-4 w-4"/> Books</span>
                <span className="flex items-center gap-1"><FileText className="h-4 w-4"/> Scripts</span>
                <span className="flex items-center gap-1"><Video className="h-4 w-4"/> Video</span>
                <span className="flex items-center gap-1"><MonitorPlay className="h-4 w-4"/> Training</span>
             </div>

             <button
              onClick={analysis ? handleCreateProject : handleAnalyze}
              disabled={isAnalyzing || (!prompt.trim() && !selectedFile && !uploadedBook)}
              className="bg-purple-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-purple-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isAnalyzing ? (
                <Loader2 className="h-5 w-5 animate-spin" />
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

          {/* Analysis Result Preview */}
          {analysis && (
            <div className="mt-8 bg-purple-50 rounded-xl p-6 border border-purple-100 animate-in fade-in slide-in-from-top-4">
               <h3 className="font-bold text-gray-900 mb-2">Analysis Results</h3>
               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                     <span className="text-xs font-semibold text-purple-600 uppercase tracking-wider">Detected Type</span>
                     <div className="text-lg font-medium text-gray-900 capitalize">{analysis.primary_intent.replace('_', ' ')}</div>
                  </div>
                  <div>
                     <span className="text-xs font-semibold text-purple-600 uppercase tracking-wider">Suggested Workflow</span>
                     <div className="text-lg font-medium text-gray-900 capitalize">{analysis.suggested_mode.replace('_', ' ')}</div>
                  </div>
                  <div className="md:col-span-2">
                     <span className="text-xs font-semibold text-purple-600 uppercase tracking-wider">Reasoning</span>
                     <p className="text-gray-700">{analysis.reasoning}</p>
                  </div>
                  <div className="md:col-span-2">
                     <span className="text-xs font-semibold text-purple-600 uppercase tracking-wider">Pipeline Steps</span>
                     <div className="flex gap-2 mt-1">
                        {analysis.detected_pipeline.map((step, i) => (
                          <span key={i} className="px-3 py-1 bg-white border border-purple-100 rounded-full text-sm text-purple-700">
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
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
          <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
            <FileText className="h-6 w-6 text-purple-600 mr-2" />
            Recent Projects
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recentProjects.map((project) => (
              <div 
                key={project.id} 
                onClick={() => window.location.href = `/book/${project.id}`}
                className="group border border-gray-200 rounded-xl p-4 hover:border-purple-200 hover:shadow-md transition-all cursor-pointer relative"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className={`p-2 rounded-lg ${
                    project.status === 'READY' || project.status === 'completed' || project.status === 'published' ? 'bg-green-100 text-green-600' : 
                    project.status === 'FAILED' ? 'bg-red-100 text-red-600' : 'bg-yellow-100 text-yellow-600'
                  }`}>
                    {(project.status === 'READY' || project.status === 'completed' || project.status === 'published') ? <CheckCircle2 className="h-5 w-5" /> : <Loader2 className="h-5 w-5" />}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">{project.project_type || project.book_type}</span>
                    <button
                      onClick={(e) => handleDeleteProject(e, project.id)}
                      className="text-gray-400 hover:text-red-500 p-1 rounded-full hover:bg-red-50 transition-colors"
                      title="Delete Project"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <h4 className="font-semibold text-gray-900 mb-1 group-hover:text-purple-600 transition-colors truncate pr-8">{project.title}</h4>
                <p className="text-sm text-gray-500 mb-4 line-clamp-2">{project.description || "No description"}</p>
                <div className="flex items-center text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <BookOpen className="h-4 w-4" /> {project.pipeline_steps?.length || project.chapters?.length || 0} Steps
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
