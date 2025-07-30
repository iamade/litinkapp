# Requirements Document

## Introduction

This feature addresses critical issues in the book upload system that are preventing successful book uploads and causing data inconsistencies. The system currently has problems with book type persistence, AI validation errors, storage conflicts, and frontend state management during the upload process.

## Requirements

### Requirement 1

**User Story:** As an author, I want my selected book type (entertainment/learning) to be correctly saved in the database, so that my book is categorized properly.

#### Acceptance Criteria

1. WHEN a user selects "entertainment" as book_type THEN the system SHALL save "entertainment" in the database
2. WHEN a user selects "learning" as book_type THEN the system SHALL save "learning" in the database
3. WHEN the book upload process completes THEN the book_type in the database SHALL match the user's selection
4. IF the book_type is not provided in the request THEN the system SHALL return a validation error

### Requirement 2

**User Story:** As a system, I want AI validation requests to be properly formatted, so that chapter validation completes without errors.

#### Acceptance Criteria

1. WHEN making AI validation requests THEN the system SHALL include the word "json" in the messages to enable json_object response format
2. WHEN AI validation fails due to format errors THEN the system SHALL log the specific error and retry with correct formatting
3. WHEN AI validation succeeds THEN the system SHALL proceed with the validated chapter data
4. IF AI validation fails after retries THEN the system SHALL return a meaningful error to the user

### Requirement 3

**User Story:** As an author, I want to be able to re-upload files without encountering duplicate errors, so that I can successfully complete my book upload.

#### Acceptance Criteria

1. WHEN a file with the same name already exists in storage THEN the system SHALL either overwrite it or generate a unique filename
2. WHEN a storage duplicate error occurs THEN the system SHALL handle it gracefully without failing the entire upload
3. WHEN handling duplicate files THEN the system SHALL maintain data consistency between database records and storage files
4. IF a file upload fails due to duplicates THEN the system SHALL provide clear feedback to the user

### Requirement 4

**User Story:** As an author, I want the frontend to progress to the chapter review step after successful chapter extraction, so that I can complete my book upload workflow.

#### Acceptance Criteria

1. WHEN chapter extraction completes successfully THEN the frontend SHALL automatically progress to step 4 (chapter review)
2. WHEN the backend returns successful chapter data THEN the frontend SHALL update its state to reflect the completion
3. WHEN errors occur during upload THEN the frontend SHALL display appropriate error messages and not progress to the next step
4. IF the upload process is interrupted THEN the frontend SHALL maintain the current step and allow retry

### Requirement 5

**User Story:** As an author, I want the system to automatically detect and preserve my book's hierarchical structure (parts and chapters), so that the organization of my content is maintained.

#### Acceptance Criteria

1. WHEN a book contains hierarchical sections (e.g., "Part 1", "Part 2", "Part 3" or "TABLET I", "TABLET II", "TABLET III") THEN the system SHALL detect and extract the hierarchical structure
2. WHEN chapters exist within parts THEN the system SHALL associate each chapter with its correct part
3. WHEN displaying the chapter review interface THEN the system SHALL show parts as collapsible sections with their respective chapters
4. WHEN saving the book structure THEN the system SHALL preserve the hierarchical relationship between parts and chapters
5. IF a book has no parts THEN the system SHALL display chapters in a flat structure as currently implemented

### Requirement 6

**User Story:** As an author, I want to review and edit my book's structure in step 4, so that I can reorganize parts and chapters before finalizing my upload.

#### Acceptance Criteria

1. WHEN viewing step 4 THEN the system SHALL display parts as expandable/collapsible sections
2. WHEN editing within a part THEN the system SHALL allow adding, removing, and reordering chapters within that part
3. WHEN moving chapters between parts THEN the system SHALL update the hierarchical structure accordingly
4. WHEN adding a new part THEN the system SHALL allow creating empty parts and moving chapters into them
5. IF the book structure changes THEN the system SHALL validate the new structure before allowing progression to step 5

### Requirement 7

**User Story:** As a system administrator, I want comprehensive error handling and logging, so that I can diagnose and resolve upload issues quickly.

#### Acceptance Criteria

1. WHEN any upload error occurs THEN the system SHALL log detailed error information including request data and stack traces
2. WHEN the upload process fails THEN the system SHALL clean up any partially created resources
3. WHEN errors are returned to the frontend THEN they SHALL include actionable information for the user
4. IF critical errors occur THEN the system SHALL alert administrators while providing fallback behavior
