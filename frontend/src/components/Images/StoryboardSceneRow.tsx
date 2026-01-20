import React from 'react';
import { SceneImage } from '../../hooks/useImageGeneration';
import { Check, Maximize2, Trash2, Film, Camera, GripVertical, Star, X } from 'lucide-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  horizontalListSortingStrategy,
  useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface StoryboardSceneRowProps {
  sceneNumber: number;
  description: string;
  images: SceneImage[];
  selectedImageUrl?: string | null;
  onSelect: (url: string | null) => void;
  onDelete: (imageId: string) => void;
  onView: (url: string) => void;
  dragHandleListeners?: any; // Listeners for the parent sortable (Scene drag)
  onReorder?: (newImages: SceneImage[]) => void; // Callback when images are reordered
  // NEW: Storyboard configuration props
  keySceneImageId?: string;                       // ID of the key scene image for this scene
  deselectedImages?: Set<string>;                 // Set of excluded image IDs (opt-OUT)
  onSetKeyScene?: (imageId: string) => void;      // Callback to set key scene image
  onToggleDeselected?: (imageId: string) => void; // Callback to toggle image exclusion
}

const SortableImageCard = ({
    image,
    isSelected,
    onSelect,
    onView,
    onDelete,
    isKeyScene,
    isExcluded,
    onSetKeyScene,
    onToggleDeselected,
}: {
    image: SceneImage;
    isSelected: boolean;
    onSelect: () => void;
    onView: () => void;
    onDelete: () => void;
    isKeyScene?: boolean;
    isExcluded?: boolean;
    onSetKeyScene?: () => void;
    onToggleDeselected?: () => void;
}) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id: image.imageUrl }); // Use URL as ID for uniqueness

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        zIndex: isDragging ? 10 : 1
    };

    // Determine card styling based on exclusion state
    const cardBorderClass = isExcluded
        ? 'border-gray-300 opacity-50'  // Excluded: grayed out
        : isKeyScene
        ? 'border-yellow-500 shadow-lg ring-2 ring-yellow-500/20'  // Key scene: yellow border
        : isSelected
        ? 'border-purple-600 shadow-lg ring-2 ring-purple-600/20 translate-y-[-2px]'  // Selected: purple
        : 'border-transparent shadow hover:border-gray-300 hover:shadow-md';  // Default

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            className={`relative group w-full bg-white dark:bg-gray-800 rounded-lg border-2 transition-all duration-200 cursor-grab active:cursor-grabbing ${cardBorderClass}`}
            onClick={onSelect}
        >
            {/* Image Container */}
            <div className="aspect-video bg-gray-200 relative rounded-t-lg overflow-hidden pointer-events-none">
                 {/* pointer-events-none on content prevents dragging issues, but we re-enable for buttons */}
                 <img
                    src={image.imageUrl}
                    alt={image.prompt}
                    className={`w-full h-full object-cover ${isExcluded ? 'grayscale' : ''}`}
                 />

                 {/* Checkbox for include/exclude (top-left) */}
                 {onToggleDeselected && image.id && (
                     <div className="absolute top-2 left-2 pointer-events-auto z-10">
                         <button
                             onPointerDown={(e) => e.stopPropagation()}
                             onClick={(e) => { e.stopPropagation(); onToggleDeselected(); }}
                             className={`w-6 h-6 rounded border-2 flex items-center justify-center transition-colors ${
                                 isExcluded
                                     ? 'bg-gray-200 border-gray-400 text-gray-500'
                                     : 'bg-green-500 border-green-600 text-white'
                             }`}
                             title={isExcluded ? 'Include this image' : 'Exclude this image'}
                         >
                             {isExcluded ? <X className="w-4 h-4" /> : <Check className="w-4 h-4" />}
                         </button>
                     </div>
                 )}

                 {/* Star button for key scene (top-right, next to actions) */}
                 {onSetKeyScene && image.id && !isExcluded && (
                     <div className="absolute top-2 right-20 pointer-events-auto z-10">
                         <button
                             onPointerDown={(e) => e.stopPropagation()}
                             onClick={(e) => { e.stopPropagation(); onSetKeyScene(); }}
                             className={`p-1.5 rounded-full transition-all ${
                                 isKeyScene
                                     ? 'bg-yellow-400 text-yellow-900 shadow-md'
                                     : 'bg-black/50 text-white/70 hover:bg-yellow-400 hover:text-yellow-900'
                             }`}
                             title={isKeyScene ? 'Key scene (reference for suggested shots)' : 'Set as key scene'}
                         >
                             <Star className={`w-4 h-4 ${isKeyScene ? 'fill-current' : ''}`} />
                         </button>
                     </div>
                 )}

                 {/* Overlay Actions - Enable pointer events specifically */}
                 <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all flex items-start justify-end p-2 opacity-0 group-hover:opacity-100 pointer-events-auto">
                     <button
                         onPointerDown={(e) => e.stopPropagation()} // Prevent drag start
                         onClick={(e) => { e.stopPropagation(); onView(); }}
                         className="p-1.5 bg-black/60 text-white rounded-full hover:bg-black/80 mr-1"
                         title="View Fullscreen"
                     >
                         <Maximize2 className="w-4 h-4"/>
                     </button>
                     <button
                         onPointerDown={(e) => e.stopPropagation()} // Prevent drag start
                         onClick={(e) => { e.stopPropagation(); onDelete(); }}
                         className="p-1.5 bg-red-600/80 text-white rounded-full hover:bg-red-700"
                         title="Delete Image"
                     >
                         <Trash2 className="w-4 h-4"/>
                     </button>
                 </div>

                 {/* Key Scene Label (bottom-left) */}
                 {isKeyScene && !isExcluded && (
                     <div className="absolute bottom-2 left-2 pointer-events-none">
                         <span className="px-2 py-0.5 bg-yellow-400 text-yellow-900 text-xs font-bold rounded shadow-sm flex items-center">
                             <Star className="w-3 h-3 mr-1 fill-current" /> Key Scene
                         </span>
                     </div>
                 )}

                 {/* Excluded Label (bottom-left) */}
                 {isExcluded && (
                     <div className="absolute bottom-2 left-2 pointer-events-none">
                         <span className="px-2 py-0.5 bg-gray-500 text-white text-xs font-bold rounded shadow-sm flex items-center">
                             <X className="w-3 h-3 mr-1" /> Excluded
                         </span>
                     </div>
                 )}

                 {/* Active Indicator Overlay (when selected but not key scene) */}
                 {isSelected && !isKeyScene && !isExcluded && (
                     <div className="absolute inset-0 ring-inset ring-4 ring-purple-600/30 pointer-events-none rounded-t-lg">
                         <div className="absolute top-2 left-10 bg-purple-600 text-white p-1 rounded shadow-sm">
                             <Check className="w-4 h-4" />
                         </div>
                     </div>
                 )}
            </div>

            {/* Footer Info */}
            <div className="p-3 border-t border-gray-100 dark:border-gray-700 pointer-events-none">
                <div className="flex items-center justify-between mb-1">
                    <span className={`text-xs font-bold uppercase tracking-wider ${
                        isExcluded
                            ? 'text-gray-400'
                            : isKeyScene
                            ? 'text-yellow-600'
                            : isSelected
                            ? 'text-purple-600'
                            : 'text-gray-500'
                    }`}>
                        {isExcluded ? 'Excluded' : isKeyScene ? 'Key Scene' : isSelected ? 'Active Selection' : 'Option'}
                    </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2" title={image.prompt}>
                    {image.prompt}
                </p>
            </div>
        </div>
    );
};

export const StoryboardSceneRow: React.FC<StoryboardSceneRowProps> = ({
  sceneNumber,
  description,
  images,
  selectedImageUrl,
  onSelect,
  onDelete,
  onView,
  dragHandleListeners,
  onReorder,
  // NEW: Storyboard configuration props
  keySceneImageId,
  deselectedImages,
  onSetKeyScene,
  onToggleDeselected,
}) => {
  // Use images prop directly (assume it's the source of truth for order)
  const sensors = useSensors(
    useSensor(PointerSensor, {
        activationConstraint: {
            distance: 8, // Require movement to start drag, allowing clicks
        },
    }),
    useSensor(KeyboardSensor, {
        coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over && active.id !== over.id && onReorder) {
        const oldIndex = images.findIndex(img => img.imageUrl === active.id);
        const newIndex = images.findIndex(img => img.imageUrl === over.id);
        if (oldIndex !== -1 && newIndex !== -1) {
            const newOrder = arrayMove(images, oldIndex, newIndex);
            onReorder(newOrder);
        }
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
      <div className="flex justify-between items-start mb-4 border-b border-gray-100 dark:border-gray-700 pb-3">
         <div className="flex items-start">
            {/* Drag Handle for Scene */}
            <div 
                className="mr-4 mt-1 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700" 
                {...dragHandleListeners}
                title="Drag to reorder scene"
            >
                <GripVertical className="w-5 h-5" />
            </div>

            <div>
                <div className="flex items-center space-x-2 mb-1">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-bold rounded uppercase">
                        Scene {sceneNumber}
                    </span>
                    {selectedImageUrl && (
                        <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-medium flex items-center">
                        <Check className="w-3 h-3 mr-1"/> Selected
                        </span>
                    )}
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2 max-w-4xl font-medium">
                    {description}
                </p>
             </div>
         </div>
      </div>

      {images.length === 0 ? (
          <div className="p-8 bg-gray-50 dark:bg-gray-900/50 text-center rounded-lg border-2 border-dashed border-gray-200 dark:border-gray-700 ml-10">
              <Camera className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <p className="text-gray-500 text-sm">No visuals generated yet.</p>
          </div>
      ) : (
          <div className="ml-10"> {/* Indent to align with content, skipping handle */}
             <DndContext 
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
             >
                <SortableContext 
                    items={images.map(img => img.imageUrl)} 
                    strategy={horizontalListSortingStrategy}
                >
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                        {images.map((img) => (
                            <SortableImageCard
                                key={img.imageUrl} // Ensure URL is unique, usually is
                                image={img}
                                isSelected={img.imageUrl === selectedImageUrl}
                                onSelect={() => onSelect(img.imageUrl === selectedImageUrl ? null : img.imageUrl)}
                                onView={() => onView(img.imageUrl)}
                                onDelete={() => img.id && onDelete(img.id)}
                                // NEW: Storyboard configuration props
                                isKeyScene={img.id === keySceneImageId}
                                isExcluded={img.id ? deselectedImages?.has(img.id) : false}
                                onSetKeyScene={img.id && onSetKeyScene ? () => onSetKeyScene(img.id!) : undefined}
                                onToggleDeselected={img.id && onToggleDeselected ? () => onToggleDeselected(img.id!) : undefined}
                            />
                        ))}
                    </div>
                </SortableContext>
             </DndContext>
          </div>
      )}
    </div>
  );
};
