# Design Document - Dynamic Book Structure System

## Overview

This design addresses the need for a dynamic book structure system that can handle books with hierarchical organization (parts containing chapters) while maintaining backward compatibility with flat chapter structures.

## Architecture

### Data Model Changes

#### Database Schema Updates

**New `book_parts` table:**

```sql
CREATE TABLE book_parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    part_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_book_parts_book_id ON book_parts(book_id);
CREATE INDEX idx_book_parts_number ON book_parts(book_id, part_number);
```

**Update `chapters` table:**

```sql
ALTER TABLE chapters ADD COLUMN part_id UUID REFERENCES book_parts(id) ON DELETE SET NULL;
CREATE INDEX idx_chapters_part_id ON chapters(part_id);
```

#### TypeScript Interfaces

```typescript
interface BookPart {
  id: string;
  book_id: string;
  part_number: number;
  title: string;
  description?: string;
  chapters: Chapter[];
}

interface Chapter {
  id: string;
  book_id: string;
  part_id?: string; // Optional for backward compatibility
  chapter_number: number;
  title: string;
  content: string;
  summary?: string;
}

interface BookStructure {
  id: string;
  title: string;
  has_parts: boolean;
  parts: BookPart[];
  chapters: Chapter[]; // For books without parts
}
```

## Components and Interfaces

### Backend Services

#### 1. Structure Detection Service

```python
class BookStructureDetector:
    def detect_structure(self, content: str) -> Dict[str, Any]:
        """
        Detect if book has parts and extract hierarchical structure
        Returns: {
            "has_parts": bool,
            "parts": [{"title": str, "chapters": []}] or None,
            "chapters": [{"title": str, "content": str}]
        }
        """

    def _detect_parts(self, content: str) -> List[Dict]:
        """Detect part markers like 'Part 1', 'Part I', etc."""

    def _extract_chapters_by_part(self, content: str, parts: List) -> Dict:
        """Extract chapters and associate them with parts"""
```

#### 2. Enhanced Chapter Extraction

```python
async def extract_chapters_with_structure(
    self, content: str, book_type: str, filename: str, storage_path: str
) -> Dict[str, Any]:
    """
    Extract chapters with hierarchical structure detection
    """
    # 1. Detect book structure (parts vs flat)
    structure = self.structure_detector.detect_structure(content)

    # 2. Extract chapters based on structure
    if structure["has_parts"]:
        return await self._extract_hierarchical_chapters(content, structure, book_type)
    else:
        return await self._extract_flat_chapters(content, book_type)
```

### Frontend Components

#### 1. Dynamic Chapter Review Component

```typescript
interface ChapterReviewProps {
  bookStructure: BookStructure;
  onStructureChange: (structure: BookStructure) => void;
}

const ChapterReview: React.FC<ChapterReviewProps> = ({
  bookStructure,
  onStructureChange,
}) => {
  if (bookStructure.has_parts) {
    return (
      <HierarchicalChapterReview
        structure={bookStructure}
        onChange={onStructureChange}
      />
    );
  } else {
    return (
      <FlatChapterReview
        chapters={bookStructure.chapters}
        onChange={onStructureChange}
      />
    );
  }
};
```

#### 2. Hierarchical Chapter Review

```typescript
const HierarchicalChapterReview: React.FC = ({ structure, onChange }) => {
  return (
    <div className="space-y-6">
      {structure.parts.map((part, partIndex) => (
        <PartSection
          key={part.id}
          part={part}
          onPartChange={(updatedPart) =>
            handlePartChange(partIndex, updatedPart)
          }
          onChapterAdd={() => handleAddChapter(partIndex)}
          onChapterRemove={(chapterIndex) =>
            handleRemoveChapter(partIndex, chapterIndex)
          }
        />
      ))}
      <AddPartButton onClick={handleAddPart} />
    </div>
  );
};
```

#### 3. Part Section Component

```typescript
const PartSection: React.FC = ({
  part,
  onPartChange,
  onChapterAdd,
  onChapterRemove,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center space-x-2"
        >
          {isExpanded ? <ChevronDownIcon /> : <ChevronRightIcon />}
          <h3 className="text-lg font-semibold">{part.title}</h3>
        </button>
        <div className="flex space-x-2">
          <button onClick={onChapterAdd}>Add Chapter</button>
          <button onClick={() => onPartChange({ ...part, title: newTitle })}>
            Edit Part
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="space-y-4">
          {part.chapters.map((chapter, index) => (
            <ChapterEditor
              key={chapter.id}
              chapter={chapter}
              onChapterChange={(updatedChapter) =>
                handleChapterChange(index, updatedChapter)
              }
              onRemove={() => onChapterRemove(index)}
            />
          ))}
        </div>
      )}
    </div>
  );
};
```

## Data Models

### Structure Detection Patterns

```python
PART_PATTERNS = [
    r'(?i)^part\s+(\d+|[ivx]+)[\s\-:]*(.*)$',  # "Part 1: Title" or "Part I: Title"
    r'(?i)^book\s+(\d+|[ivx]+)[\s\-:]*(.*)$',  # "Book 1: Title"
    r'(?i)^section\s+(\d+|[ivx]+)[\s\-:]*(.*)$',  # "Section 1: Title"
]

CHAPTER_PATTERNS = [
    r'(?i)^chapter\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
    r'(?i)^(\d+)[\.\s]+(.*)$',  # "1. Chapter Title"
]
```

### Database Storage Strategy

```python
async def save_book_structure(self, book_id: str, structure: Dict) -> None:
    """Save hierarchical book structure to database"""

    if structure["has_parts"]:
        # Save parts
        for part_data in structure["parts"]:
            part_id = await self._create_part(book_id, part_data)

            # Save chapters within part
            for chapter_data in part_data["chapters"]:
                await self._create_chapter(book_id, chapter_data, part_id)
    else:
        # Save flat chapters (backward compatibility)
        for chapter_data in structure["chapters"]:
            await self._create_chapter(book_id, chapter_data, part_id=None)
```

## Error Handling

### Structure Detection Fallbacks

1. **Part Detection Failure**: Fall back to flat chapter structure
2. **Chapter Association Failure**: Assign orphaned chapters to a default part
3. **Malformed Structure**: Provide manual editing interface

### Validation Rules

```python
def validate_book_structure(structure: Dict) -> List[str]:
    """Validate book structure and return list of errors"""
    errors = []

    if structure["has_parts"]:
        if not structure["parts"]:
            errors.append("Books with parts must have at least one part")

        for part in structure["parts"]:
            if not part["chapters"]:
                errors.append(f"Part '{part['title']}' must have at least one chapter")
    else:
        if not structure["chapters"]:
            errors.append("Book must have at least one chapter")

    return errors
```

## Testing Strategy

### Unit Tests

1. **Structure Detection Tests**

   - Test various part/chapter patterns
   - Test edge cases (no parts, empty parts, malformed headers)
   - Test different book formats (PDF, DOCX, TXT)

2. **Database Operations Tests**
   - Test hierarchical data insertion
   - Test backward compatibility with existing flat structures
   - Test cascade deletions

### Integration Tests

1. **End-to-End Upload Tests**

   - Upload books with parts structure
   - Upload books without parts (flat)
   - Test structure editing in step 4

2. **API Tests**
   - Test structure retrieval endpoints
   - Test structure update endpoints
   - Test validation error handling

## Migration Strategy

### Database Migration

```sql
-- Migration script for existing books
UPDATE chapters SET part_id = NULL WHERE part_id IS NOT NULL;

-- Add migration flag to track converted books
ALTER TABLE books ADD COLUMN structure_migrated BOOLEAN DEFAULT FALSE;
```

### Backward Compatibility

- Existing books without parts continue to work as before
- New `part_id` field is nullable for backward compatibility
- Frontend automatically detects structure type and renders appropriately

## Performance Considerations

### Database Optimization

- Index on `book_parts.book_id` for fast part retrieval
- Index on `chapters.part_id` for fast chapter-by-part queries
- Consider denormalization for frequently accessed structure data

### Frontend Optimization

- Lazy loading of chapter content in collapsed parts
- Virtualization for books with many parts/chapters
- Debounced auto-save for structure changes

## Implementation Phases

### Phase 1: Backend Structure Detection

- Implement structure detection algorithms
- Create database schema changes
- Add API endpoints for structure management

### Phase 2: Frontend Dynamic UI

- Create hierarchical chapter review components
- Implement drag-and-drop for reorganization
- Add part management (add/remove/edit)

### Phase 3: Enhanced Features

- Advanced structure editing (merge/split parts)
- Structure templates for common book types
- Bulk operations (move multiple chapters)

### Phase 4: Migration and Optimization

- Migrate existing books to new structure
- Performance optimizations
- Advanced validation and error handling
