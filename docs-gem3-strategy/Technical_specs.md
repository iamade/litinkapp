Unified Creator Mode - Technical Specification
This document details the technical implementation for the Unified Creator Mode, designed to consolidate content generation into a single, intelligent interface.

1. Architecture Overview
The system transitions from a fragmented, type-specific generation flow (separate Book/Script/Video inputs) to a Unified Intent-Based Architecture.

Core Components
Unified Frontend: A single entry point (/creator) that accepts text prompts and file uploads.
Creator Service (Backend): A new orchestration layer that:
Detects user intent (Book vs. Script vs. Video).
Manages the "Project" lifecycle.
Orchestrates the "Human-in-the-loop" workflow steps.
AI Service (Enhanced): Updated to support intent classification and workflow planning.
2. Backend Implementation Details
2.1 Data Models (
app/services/creator_service.py
)
We will introduce lightweight enums to manage the state, while utilizing the existing 
Book
 model as the primary data container (polymorphic storage).

class ContentType(str, Enum):
    BOOK = "book"       # Standard novel/textbook
    SCRIPT = "script"   # Screenplay/Stage play
    VIDEO = "video"     # Video production project
class WorkflowStep(str, Enum):
    INTENT = "intent"     # Analyzing user input
    PLOT = "plot"         # Generating/Editing Plot
    SCRIPT = "script"     # Generating/Editing Script
    MEDIA = "media"       # Generating Images/Video
    COMPLETE = "complete" # Finished
2.2 Creator Service Logic
The CreatorService acts as the state machine for the generation process.

Key Methods:

detect_intent(prompt, file):
Calls 
AIService
 with a classification prompt.
Returns: { type: "video", confidence: 0.9, plan: [...] }
create_project(user, type, title, prompt):
Creates a 
Book
 record with book_type="entertainment" (or specific type).
Stores the 
prompt
 and 
type
 in metadata.
Returns project_id.
advance_workflow(project_id, current_step, feedback):
Input: current_step="plot", feedback="Make it scarier"
Action:
Retrieves current project state.
Calls AI to generate the next asset (e.g., if Plot is approved -> Generate Script).
Updates the DB.
Output: The generated content for the next step (e.g., the Script text).
2.3 API Endpoints (
app/api/routes/creator/routes.py
)
New endpoints to support the interactive flow.

Method	Endpoint	Description	Payload	Response
POST	/creator/detect-intent	Analyze input	
prompt
, 
file
{ type, confidence, plan }
POST	/creator/create	Initialize Project	
type
, 
title
, 
prompt
{ project_id, status }
POST	/creator/workflow/{id}/next	Advance Step	current_step, feedback	{ next_step, data }
3. Frontend Implementation Details
3.1 Components
UnifiedInput Component

UI: Large text area with integrated drag-and-drop zone.
Behavior:
On "Generate" click -> Calls /detect-intent.
Displays "Analyzing..." animation.
Shows Intent Confirmation Modal: "We think you want to make a [Video]. Is this correct?"
WorkflowTimeline Component

Visual progress bar: [ Idea ] -> [ Plot ] -> [ Script ] -> [ Production ]
Highlights the current active step.
InteractionPanel Component

The main workspace for "Human-in-the-loop" editing.
State: Plot Review: Shows text editor with generated plot. Buttons: "Regenerate", "Approve & Next".
State: Script Review: Shows script view. Buttons: "Edit Scene", "Approve & Generate Video".
3.2 Service Layer (
frontend/src/services/creatorService.ts
)
interface IntentResult {
  type: 'book' | 'script' | 'video';
  confidence: number;
  reasoning: string;
  plan: { steps: string[], summary: string };
}
// Methods matching the API endpoints
detectIntent(prompt: string, file?: File): Promise<IntentResult>;
createProject(type: string, title: string, prompt: string): Promise<ProjectResult>;
advanceWorkflow(projectId: string, step: string, feedback?: string): Promise<WorkflowResult>;
4. Agentic Workflow Logic
The system distinguishes between Explorer (Auto) and Creator (Interactive) modes based on user choice or profile.

Explorer Mode (Auto-Pilot)
User Input: "Make a video about cats."
Intent: VIDEO.
System:
Generates Plot (Auto-approved).
Generates Script (Auto-approved).
Generates Video.
User Notification: "Your video is ready."
Creator Mode (Co-Pilot)
User Input: "Make a video about cats."
Intent: VIDEO.
System: Generates Plot. PAUSE.
User: Reviews Plot. "Add a dog." -> Approve.
System: Generates Script (with dog). PAUSE.
User: Reviews Script. -> Approve.
System: Generates Video.
5. Future Considerations
Project Model: Eventually, we may need a dedicated Project table if the 
Book
 model becomes too constrained for complex video projects.
State Persistence: Currently, intermediate steps (like a rejected plot) might not be saved. Future versions could version-control every step.