# Implementation Plan - Dynamic Book Structure System

- [ ] 1. Database Schema Updates

  - Create book_parts table with proper relationships
  - Add part_id column to chapters table with foreign key
  - Create necessary indexes for performance
  - _Requirements: 5.1, 5.4_

- [ ] 2. Backend Structure Detection Service

  - [ ] 2.1 Create BookStructureDetector class

    - Implement part detection patterns (Part 1, Part I, etc.)
    - Implement chapter extraction within parts
    - Handle fallback to flat structure when no parts detected
    - _Requirements: 5.1, 5.2_

  - [ ] 2.2 Enhance chapter extraction flow
    - Modify extract_chapters_with_new_flow to use structure detection
    - Update database insertion to handle parts and hierarchical chapters
    - Maintain backward compatibility for books without parts
    - _Requirements: 5.2, 5.4, 5.5_

- [ ] 3. Backend API Endpoints

  - [ ] 3.1 Create book structure retrieval endpoint

    - GET /api/v1/books/{book_id}/structure endpoint
    - Return hierarchical structure with parts and chapters
    - Handle both flat and hierarchical book structures
    - _Requirements: 5.4_

  - [ ] 3.2 Create structure update endpoint
    - PUT /api/v1/books/{book_id}/structure endpoint
    - Validate structure changes before saving
    - Update parts and chapters in database
    - _Requirements: 6.2, 6.3, 6.5_

- [ ] 4. Frontend Dynamic Chapter Review

  - [ ] 4.1 Create hierarchical data structures

    - Define TypeScript interfaces for BookPart and BookStructure
    - Update existing Chapter interface to include part_id
    - Create utility functions for structure manipulation
    - _Requirements: 5.4, 6.1_

  - [ ] 4.2 Build dynamic chapter review component

    - Create ChapterReview component that detects structure type
    - Implement HierarchicalChapterReview for books with parts
    - Maintain existing FlatChapterReview for backward compatibility
    - _Requirements: 6.1, 5.5_

  - [ ] 4.3 Implement part section components
    - Create PartSection component with expand/collapse functionality
    - Add part editing capabilities (title, description)
    - Implement chapter management within parts (add, remove, reorder)
    - _Requirements: 6.1, 6.2_

- [ ] 5. Frontend Structure Management

  - [ ] 5.1 Add part management features

    - Implement "Add Part" functionality
    - Add part deletion with chapter reassignment
    - Create part reordering capabilities
    - _Requirements: 6.2, 6.4_

  - [ ] 5.2 Implement chapter movement between parts
    - Add drag-and-drop or move buttons for chapters
    - Update hierarchical structure when chapters move
    - Validate structure changes before applying
    - _Requirements: 6.3, 6.5_

- [ ] 6. Integration and Testing

  - [ ] 6.1 Update book upload flow

    - Modify step 4 to use new dynamic chapter review
    - Update book saving logic to handle hierarchical structure
    - Test with various book formats (PDF, DOCX, TXT)
    - _Requirements: 5.1, 5.2, 5.4_

  - [ ] 6.2 Add structure validation
    - Implement client-side structure validation
    - Add server-side validation for structure updates
    - Handle validation errors gracefully
    - _Requirements: 6.5_

- [ ] 7. Backward Compatibility and Migration

  - [ ] 7.1 Ensure existing books continue to work

    - Test existing flat chapter books display correctly
    - Verify no breaking changes to current upload flow
    - Add migration path for existing books if needed
    - _Requirements: 5.5_

  - [ ] 7.2 Add structure detection testing
    - Test part detection with various book samples
    - Test fallback behavior when structure detection fails
    - Verify chapter association accuracy
    - _Requirements: 5.1, 5.2_
