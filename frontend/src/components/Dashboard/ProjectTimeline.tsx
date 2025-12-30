import React from "react";
import { CheckCircle2, Circle, Clock, AlertCircle, ArrowRight } from "lucide-react";
import { Project } from "../../services/projectService";

interface ProjectTimelineProps {
  project: Project;
  currentStep?: string; // Optional override
}

export default function ProjectTimeline({ project }: ProjectTimelineProps) {
  // Infer steps based on project type for now, or use data from project if available
  // In future, project.pipeline_steps would drive this.
  const steps = [
    { id: "prompt", label: "Concept", status: "completed" },
    { id: "plot", label: "Structure", status: project.status === "draft" ? "current" : "completed" },
    { id: "script", label: "Script", status: "pending" },
    { id: "production", label: "Production", status: "pending" },
  ];

  if (project.project_type === 'entertainment') {
      // entertainment specific mapping if needed
  }

  return (
    <div className="w-full py-4">
      <div className="flex items-center justify-between relative">
        {/* Connecting Line */}
        <div className="absolute left-0 top-1/2 w-full h-1 bg-gray-100 -z-10"></div>
        
        {steps.map((step, index) => {
          let icon = <Circle className="h-5 w-5 text-gray-300" />;
          let colorClass = "text-gray-400 bg-white";
          let borderClass = "border-gray-200";

          if (step.status === "completed") {
            icon = <CheckCircle2 className="h-6 w-6 text-green-500" />;
            colorClass = "text-green-600 bg-green-50";
            borderClass = "border-green-200";
          } else if (step.status === "current") {
            icon = <Clock className="h-5 w-5 text-purple-600 animate-pulse" />;
            colorClass = "text-purple-600 bg-purple-50 ring-4 ring-purple-100";
            borderClass = "border-purple-200";
          } else if (step.status === "error") {
            icon = <AlertCircle className="h-5 w-5 text-red-500" />;
            colorClass = "text-red-600 bg-red-50";
            borderClass = "border-red-200";
          }

          return (
            <div key={step.id} className="flex flex-col items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${borderClass} ${colorClass} transition-all duration-300 z-10`}
              >
                {icon}
              </div>
              <span className={`mt-2 text-xs font-semibold uppercase tracking-wider ${
                  step.status === 'current' ? 'text-purple-600' : 'text-gray-500'
              }`}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
