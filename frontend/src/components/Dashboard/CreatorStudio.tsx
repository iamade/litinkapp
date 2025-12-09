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
  CheckCircle2
} from "lucide-react";
import { projectService, IntentAnalysisResult } from "../../services/projectService";
import { toast } from "react-hot-toast";
import { apiClient } from "../../lib/api";

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
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedBook, setUploadedBook] = useState<UploadedBook | null>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const toastId = toast.loading("Uploading and processing book...");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("book_type", "entertainment"); // Default to entertainment for Studio
      formData.append("title", file.name);
      formData.append("description", "Uploaded via Creator Studio");

      // 1. Upload
      // Using apiClient.upload which handles multipart/form-data
      const response = await apiClient.upload<any>("/books/upload", formData);

      // 2. Poll for status (Simple version of BookUpload logic)
      let bookId = response.id;
      if (!bookId && response.book_id) bookId = response.book_id; // Handle potential varied response

      if (bookId) {
         // Start polling
         const pollInterval = setInterval(async () => {
            try {
               const statusRes = await apiClient.get<any>(`/books/${bookId}/status`);
               if (statusRes.status === "READY" || statusRes.status === "PROCESSING" || statusRes.status === "GENERATING") {
                  // We consider it "uploaded enough" to link to a project once it exists and is processing
                  clearInterval(pollInterval);
                  setUploadedBook({
                    id: bookId,
                    title: statusRes.title || file.name,
                    status: statusRes.status
                  });
                  toast.success("Book attached successfully!", { id: toastId });
                  setIsUploading(false);
               } else if (statusRes.status === "FAILED") {
                  clearInterval(pollInterval);
                  toast.error("Book processing failed.", { id: toastId });
                  setIsUploading(false);
               }
            } catch (e) {
               console.error("Polling error", e);
               // Don't clear interval immediately on transient error, but maybe limit retries in real prod
            }
         }, 2000);
      } else {
        throw new Error("No Book ID returned");
      }

    } catch (error) {
      console.error(error);
      toast.error("Failed to upload book.", { id: toastId });
      setIsUploading(false);
    }
  };

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const handleAnalyze = async () => {
    if (!prompt.trim() && !uploadedBook) return; // Allow analyze if just book uploaded

    setIsAnalyzing(true);
    try {
      // 1. Analyze Intent
      // If we have an upload, we might hint that to the intent service?
      const textToAnalyze = prompt || (uploadedBook ? `Create a project from the book ${uploadedBook.title}` : "");
      
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
    
    try {
      await projectService.createProject({
        title: `Project: ${prompt.slice(0, 20) || uploadedBook?.title || "Untitled"}...`, 
        input_prompt: prompt,
        project_type: analysis.primary_intent,
        workflow_mode: "creator_interactive",
        // Pass source material URL/ID if backend supports it. 
        // For now, we assume the backend might derive it or we add a field.
        // Let's assume we pass it in the payload structure as source_material_url (using ID for internal ref)
        source_material_url: uploadedBook ? `book://${uploadedBook.id}` : undefined
      });
      toast.success("Project created! Redirecting to workspace...");
      // navigate(`/project/${newProject.id}/workspace`);
      // For now:
      window.location.reload();
    } catch (e) {
      toast.error("Failed to create project.");
    }
  };

  return (
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
          {uploadedBook && (
            <div className="absolute bottom-16 left-4 right-4 bg-white border border-purple-100 rounded-lg p-2 flex items-center gap-3 shadow-sm animate-in fade-in slide-in-from-bottom-2">
               <div className="bg-purple-100 p-1 rounded">
                  <FileIcon className="h-4 w-4 text-purple-600" />
               </div>
               <div className="flex-1 text-sm">
                  <span className="font-semibold text-gray-900">{uploadedBook.title}</span>
                  <span className="ml-2 text-xs text-gray-500">({uploadedBook.status})</span>
               </div>
               <button onClick={() => setUploadedBook(null)} className="text-gray-400 hover:text-red-500">
                  <X className="h-4 w-4" />
               </button>
            </div>
          )}

          <div className="absolute bottom-4 right-4 flex gap-2">
             <button 
                onClick={triggerFileUpload}
                disabled={isUploading}
                className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${
                   isUploading ? "bg-purple-50 text-purple-400 cursor-wait" : "text-gray-400 hover:text-gray-600 hover:bg-gray-200"
                }`} 
                title="Upload Source Material"
             >
              {isUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
              {isUploading && <span className="text-xs font-semibold">Processing...</span>}
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
            disabled={isAnalyzing || (!prompt.trim() && !uploadedBook)}
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
  );
}
