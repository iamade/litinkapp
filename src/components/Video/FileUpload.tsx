import React, { useState, useRef, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  Upload,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  FileVideo,
  FileAudio,
  RotateCcw
} from 'lucide-react';
import { apiClient } from '../../lib/api';

interface UploadedFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  progress: number;
  url?: string;
  error?: string;
  duration?: number;
  size: number;
  type: string;
}

interface FileUploadProps {
  onFilesUploaded: (files: UploadedFile[]) => void;
  maxFiles?: number;
  acceptedTypes?: string[];
  maxFileSize?: number; // in bytes
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFilesUploaded,
  maxFiles = 10,
  acceptedTypes = ['video/*', 'audio/*'],
  maxFileSize = 500 * 1024 * 1024 // 500MB
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): string | null => {
    // Check file size
    if (file.size > maxFileSize) {
      return `File size exceeds ${Math.round(maxFileSize / (1024 * 1024))}MB limit`;
    }

    // Check file type
    const isValidType = acceptedTypes.some(type => {
      if (type.endsWith('/*')) {
        const baseType = type.slice(0, -1);
        return file.type.startsWith(baseType);
      }
      return file.type === type;
    });

    if (!isValidType) {
      return `File type ${file.type} not supported. Allowed: ${acceptedTypes.join(', ')}`;
    }

    return null;
  }, [acceptedTypes, maxFileSize]);

  const getFileDuration = useCallback((file: File): Promise<number> => {
    return new Promise((resolve) => {
      if (file.type.startsWith('video/')) {
        const video = document.createElement('video');
        video.preload = 'metadata';
        video.onloadedmetadata = () => {
          resolve(video.duration);
        };
        video.onerror = () => resolve(0);
        video.src = URL.createObjectURL(file);
      } else if (file.type.startsWith('audio/')) {
        const audio = document.createElement('audio');
        audio.preload = 'metadata';
        audio.onloadedmetadata = () => {
          resolve(audio.duration);
        };
        audio.onerror = () => resolve(0);
        audio.src = URL.createObjectURL(file);
      } else {
        resolve(0);
      }
    });
  }, []);

  const uploadFile = useCallback(async (fileData: UploadedFile): Promise<void> => {
    // Set uploading status and progress
    setFiles(prev => prev.map(f =>
      f.id === fileData.id
        ? { ...f, status: 'uploading', progress: 10 }
        : f
    ));

    const formData = new FormData();
    formData.append('file', fileData.file);
    formData.append('file_type', fileData.type.startsWith('video/') ? 'video' : 'audio');

    try {
      // Simulate progress
      setTimeout(() => {
        setFiles(prev => prev.map(f =>
          f.id === fileData.id
            ? { ...f, progress: 50 }
            : f
        ));
      }, 500);

      const response = await apiClient.upload('/merge/upload', formData) as {
        file_url: string;
        file_type: string;
        file_size: number;
        upload_id: string;
      };

      setFiles(prev => prev.map(f =>
        f.id === fileData.id
          ? { ...f, status: 'completed', progress: 100, url: response.file_url }
          : f
      ));

      // Get duration after upload
      const duration = await getFileDuration(fileData.file);
      setFiles(prev => prev.map(f =>
        f.id === fileData.id
          ? { ...f, duration }
          : f
      ));

    } catch (error) {
      console.error('Upload failed:', error);
      setFiles(prev => prev.map(f =>
        f.id === fileData.id
          ? { ...f, status: 'failed', error: error instanceof Error ? error.message : 'Upload failed' }
          : f
      ));
    }
  }, [getFileDuration]);

  const processFiles = useCallback(async (newFiles: File[]) => {
    const validFiles: UploadedFile[] = [];
    const errors: string[] = [];

    for (const file of newFiles) {
      const validationError = validateFile(file);
      if (validationError) {
        errors.push(`${file.name}: ${validationError}`);
        continue;
      }

      const uploadedFile: UploadedFile = {
        id: `${Date.now()}-${Math.random()}`,
        file,
        status: 'pending',
        progress: 0,
        size: file.size,
        type: file.type
      };

      validFiles.push(uploadedFile);
    }

    if (errors.length > 0) {
      toast.error(`Some files were rejected:\n${errors.join('\n')}`);
    }

    if (validFiles.length === 0) return;

    // Check total file count
    setFiles(prev => {
      const totalFiles = prev.length + validFiles.length;
      if (totalFiles > maxFiles) {
        toast.error(`Maximum ${maxFiles} files allowed`);
        return prev;
      }
      return [...prev, ...validFiles];
    });

    // Start uploading
    setIsUploading(true);
    for (const fileData of validFiles) {
      await uploadFile(fileData);
    }
    setIsUploading(false);

    // Notify parent of completed uploads
    const completedFiles = files.filter(f => f.status === 'completed');
    onFilesUploaded(completedFiles);
  }, [validateFile, maxFiles, uploadFile, files, onFilesUploaded]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    processFiles(droppedFiles);
  }, [processFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles) {
      processFiles(Array.from(selectedFiles));
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [processFiles]);

  const removeFile = useCallback((fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  }, []);

  const retryUpload = useCallback((fileId: string) => {
    const fileData = files.find(f => f.id === fileId);
    if (fileData) {
      setFiles(prev => prev.map(f =>
        f.id === fileId
          ? { ...f, status: 'pending', error: undefined }
          : f
      ));
      uploadFile(fileData);
    }
  }, [files, uploadFile]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds || seconds === 0) return 'Unknown';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragOver
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <div className="space-y-2">
          <p className="text-lg font-medium text-gray-900">
            Drop files here or{' '}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="text-blue-600 hover:text-blue-500 font-medium"
            >
              browse
            </button>
          </p>
          <p className="text-sm text-gray-500">
            Support for {acceptedTypes.join(', ')} up to {formatFileSize(maxFileSize)} each
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-700">Uploaded Files</h4>
          {files.map((fileData) => (
            <div key={fileData.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center flex-shrink-0">
                  {fileData.type.startsWith('video/') ? (
                    <FileVideo className="w-4 h-4 text-blue-600" />
                  ) : (
                    <FileAudio className="w-4 h-4 text-blue-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {fileData.file.name}
                  </p>
                  <div className="flex items-center space-x-2 text-xs text-gray-500">
                    <span>{formatFileSize(fileData.size)}</span>
                    <span>•</span>
                    <span>{fileData.type}</span>
                    {fileData.duration && (
                      <>
                        <span>•</span>
                        <span>{formatDuration(fileData.duration)}</span>
                      </>
                    )}
                  </div>
                  {fileData.status === 'uploading' && (
                    <div className="mt-1">
                      <div className="w-full bg-gray-200 rounded-full h-1">
                        <div
                          className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                          style={{ width: `${fileData.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {fileData.error && (
                    <p className="text-xs text-red-600 mt-1">{fileData.error}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-2 flex-shrink-0">
                {fileData.status === 'completed' && (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                )}
                {fileData.status === 'uploading' && (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                )}
                {fileData.status === 'failed' && (
                  <>
                    <AlertCircle className="w-4 h-4 text-red-500" />
                    <button
                      onClick={() => retryUpload(fileData.id)}
                      className="p-1 text-gray-400 hover:text-blue-500"
                      title="Retry upload"
                    >
                      <RotateCcw className="w-3 h-3" />
                    </button>
                  </>
                )}
                <button
                  onClick={() => removeFile(fileData.id)}
                  className="p-1 text-gray-400 hover:text-red-500"
                  title="Remove file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Progress Summary */}
      {isUploading && (
        <div className="text-sm text-gray-600 text-center">
          Uploading files... {files.filter(f => f.status === 'completed').length} of {files.length} completed
        </div>
      )}
    </div>
  );
};

export default FileUpload;