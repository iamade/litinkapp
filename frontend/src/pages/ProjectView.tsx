
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { projectService, Project, ProjectStatus } from "../services/projectService";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "react-hot-toast";
import { 
  ArrowLeft, 
  FileText, 
  Settings, 
  MoreVertical, 
  Play, 
  BookOpen, 
  Clock,
  ExternalLink
} from "lucide-react";

const ProjectView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [artifacts, setArtifacts] = useState<any[]>([]);

  useEffect(() => {
    if (id) {
      loadProject(id);
    }
  }, [id]);

  const loadProject = async (projectId: string) => {
    try {
      setLoading(true);
      const data = await projectService.getProject(projectId);
      setProject(data);
      if (data.artifacts) {
        setArtifacts(data.artifacts);
      }
    } catch (error) {
      console.error("Failed to load project", error);
      toast.error("Failed to load project details");
      navigate("/creator");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-gray-500">
        <h2 className="text-xl font-semibold mb-2">Project Not Found</h2>
        <button 
          onClick={() => navigate("/creator")}
          className="text-purple-600 hover:text-purple-700 font-medium flex items-center gap-2"
        >
          <ArrowLeft size={16} />
          Back to Creator Studio
        </button>
      </div>
    );
  }

  const chapters = artifacts
    .filter(a => a.artifact_type === 'chapter')
    .sort((a, b) => (a.content.chapter_number || 0) - (b.content.chapter_number || 0));

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <button 
                onClick={() => navigate("/creator")}
                className="p-2 -ml-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <ArrowLeft size={20} />
              </button>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  {project.title}
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${
                    project.status === 'completed' ? 'bg-green-100 text-green-700 border-green-200' :
                    project.status === 'published' ? 'bg-blue-100 text-blue-700 border-blue-200' :
                    'bg-gray-100 text-gray-600 border-gray-200'
                  }`}>
                    {project.status.replace('_', ' ')}
                  </span>
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    Last updated {new Date(project.updated_at).toLocaleDateString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <BookOpen size={12} />
                    {chapters.length} Chapters
                  </span>
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <button className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                <Settings size={20} />
              </button>
              <button className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                <MoreVertical size={20} />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Content: Chapters */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Chapters</h2>
              <button className="px-4 py-2 text-sm font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 rounded-lg transition-colors">
                Regenerate All
              </button>
            </div>

            {chapters.length === 0 ? (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
                <FileText size={48} className="mx-auto text-gray-300 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Chapters Yet</h3>
                <p className="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
                  Upload a book or source material to extract chapters, or generate them from a prompt.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {chapters.map((chapter) => (
                  <div 
                    key={chapter.id}
                    className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow cursor-pointer"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                            Chapter {chapter.content.chapter_number}
                          </span>
                        </div>
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white truncate pr-4">
                          {chapter.content.title}
                        </h3>
                        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
                          {chapter.content.content}
                        </p>
                      </div>
                      <button className="p-2 text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity">
                        <ExternalLink size={18} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sidebar: Project Info & Actions */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                Actions
              </h2>
              <div className="space-y-3">
                <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors shadow-sm">
                  <Play size={18} />
                  Start Generation
                </button>
                <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 font-medium rounded-lg transition-colors">
                  View Source Material
                </button>
              </div>
            </div>

            {/* Project Details */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                Project Details
              </h2>
              <dl className="space-y-4">
                <div>
                  <dt className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Type</dt>
                  <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-white">{project.project_type}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Mode</dt>
                  <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-white">{project.workflow_mode}</dd>
                </div>
                {project.input_prompt && (
                  <div>
                    <dt className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Original Prompt</dt>
                    <dd className="mt-1 text-sm text-gray-600 dark:text-gray-300 italic">" {project.input_prompt} "</dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectView;
