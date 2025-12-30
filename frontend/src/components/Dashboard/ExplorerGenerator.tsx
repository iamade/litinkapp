import React, { useState } from "react";
import { Sparkles, Upload, ArrowRight, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { projectService } from "../../services/projectService";
import { toast } from "react-hot-toast";

export default function ExplorerGenerator() {
  const [prompt, setPrompt] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const navigate = useNavigate();

  const handleMagicGenerate = async () => {
    if (!prompt.trim()) return;

    setIsAnalyzing(true);
    try {
      // 1. Analyze Intent (Backend decides if it's a book, movie, etc.)
      const intent = await projectService.analyzeIntent(prompt);

      // 2. Create Project (Automated Flow)
      // For Explorer, we default to the backend's suggested 'agentic' mode 
      // but force 'explorer_agentic' just to be safe if that's the UX we want.
      const newProject = await projectService.createProject({
        title: `Generated: ${prompt.slice(0, 30)}...`, // Temporary title
        input_prompt: prompt,
        project_type: intent.primary_intent,
        workflow_mode: "explorer_agentic", 
      });

      toast.success(`Starting generation for your ${intent.primary_intent}!`);
      
      // 3. Redirect to Project View (or stay on dashboard with progress)
      // For now, let's assume we go to a project status page (to be built)
      // or just refresh dashboard. Let's go to Author Panel style view for now?
      // Or maybe a specific /project/:id? 
      // Strategy says: "One-click generation... fire and forget".
      // Let's reload dashboard to show it in the list (ProjectTimeline component later).
      window.location.reload(); 

    } catch (error) {
      console.error(error);
      toast.error("Something went wrong with the magic generation.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-8 text-white shadow-xl relative overflow-hidden">
      {/* Abstract Background Shapes */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-white opacity-10 rounded-full blur-3xl"></div>
      <div className="absolute bottom-0 left-0 -ml-16 -mb-16 w-64 h-64 bg-purple-400 opacity-10 rounded-full blur-3xl"></div>

      <div className="relative z-10 max-w-3xl mx-auto text-center">
        <h2 className="text-3xl font-bold mb-4 flex items-center justify-center gap-3">
          <Sparkles className="h-8 w-8 text-yellow-300" />
          What do you want to create today?
        </h2>
        <p className="text-purple-100 mb-8 text-lg">
          Describe an idea, or upload a book/script. We'll handle the rest.
        </p>

        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-2 flex flex-col sm:flex-row gap-2 border border-white/20 items-center transition-all focus-within:ring-2 focus-within:ring-white/40 shadow-inner">
           {/* File Upload Trigger */}
           <button className="p-3 text-purple-200 hover:text-white hover:bg-white/10 rounded-xl transition-colors" title="Upload File">
            <Upload className="h-6 w-6" />
          </button>
          
          <input
            type="text"
            className="flex-1 bg-transparent border-none text-white placeholder-purple-200 focus:ring-0 text-lg px-4 py-2 w-full"
            placeholder="e.g. 'A sci-fi thriller about a time-traveling detective...'"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleMagicGenerate()}
          />

          <button
            onClick={handleMagicGenerate}
            disabled={isAnalyzing || !prompt.trim()}
            className="bg-white text-purple-600 hover:bg-purple-50 px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-transform active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed shadow-lg"
          >
            {isAnalyzing ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                Generate
                <ArrowRight className="h-5 w-5" />
              </>
            )}
          </button>
        </div>
        <p className="text-xs text-purple-200 mt-4 opacity-70">
          Supports: Text Prompts, PDF, DOCX, TXT • Auto-detects Books, Scripts, Music Videos
        </p>
      </div>
    </div>
  );
}
