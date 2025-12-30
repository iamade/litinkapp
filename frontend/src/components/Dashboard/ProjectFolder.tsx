import React from "react";
import { Loader2, Trash2 } from "lucide-react";

interface ProjectFolderProps {
  project: any;
  onDelete: (e: React.MouseEvent, id: string) => void;
  onClick: () => void;
}

export default function ProjectFolder({ project, onDelete, onClick }: ProjectFolderProps) {
  // Determine status color for a small indicator dot or similar if needed, 
  // but the main request is the folder icon. We'll keep the status loop simple.
  
  return (
    <div 
      onClick={onClick}
      className="group flex flex-col cursor-pointer"
    >
      <div className="relative w-full aspect-[4/3] mb-3 transition-transform transform group-hover:-translate-y-1 duration-200">
        {/* Folder SVG */}
        <svg viewBox="0 0 100 80" className="w-full h-full drop-shadow-xl" preserveAspectRatio="none">
          {/* Back Tab */}
          <path 
            d="M 10 20 L 35 20 L 40 10 L 60 10 L 65 20 L 90 20 C 95 20 100 24 100 30 L 100 70 C 100 76 95 80 90 80 L 10 80 C 5 80 0 76 0 70 L 0 30 C 0 24 5 20 10 20 Z" 
            fill="#a78bfa" /* Lighter purple for the tab/back */
          />
          {/* Main Body (Front) */}
          <path 
            d="M 10 25 L 90 25 C 95 25 100 29 100 35 L 100 70 C 100 76 95 80 90 80 L 10 80 C 5 80 0 76 0 70 L 0 35 C 0 29 5 25 10 25 Z" 
            fill="#4c1d95" /* Darker purple (violet-900) for body */
            className="group-hover:fill-[#5b21b6] transition-colors"
          />
        </svg>

        {/* Status Indicator (Overlay) - Only show for processing/failed states */}
        {project.status === 'FAILED' ? (
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <Trash2 className="w-8 h-8 text-red-400" />
          </div>
        ) : (project.status !== 'READY' && project.status !== 'completed' && project.status !== 'published') ? (
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <Loader2 className="w-8 h-8 animate-spin text-white/50" />
          </div>
        ) : null}
        
        {/* Delete Button (Overlay) */}
        <button
            onClick={(e) => onDelete(e, project.id)}
            className="absolute top-8 right-2 p-1.5 bg-black/20 hover:bg-red-500/80 rounded-full text-white/70 hover:text-white opacity-0 group-hover:opacity-100 transition-all backdrop-blur-sm"
            title="Delete Project"
        >
            <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Info */}
      <div className="px-1">
        <h4 className="font-semibold text-gray-900 dark:text-gray-100 truncate text-base mb-0.5">
          {project.title}
        </h4>
        <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
           {/* Approximate "10 files" look from image */}
          <span>
             {project.pipeline_steps?.length || project.chapters?.length || 0} items
          </span>
          <span className="mx-2">•</span>
          <span className="uppercase tracking-wide text-[10px]">{project.project_type || 'Unknown'}</span>
        </div>
      </div>
    </div>
  );
}
