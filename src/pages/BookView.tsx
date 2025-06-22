import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Play, 
  Pause, 
  Volume2, 
  BookOpen, 
  Brain,
  CheckCircle,
  Star,
  Award,
  MessageCircle,
  Share2
} from 'lucide-react';
import AIQuizComponent from '../components/AIQuizComponent';
import VoiceStoryComponent from '../components/VoiceStoryComponent';

export default function BookView() {
  const { id } = useParams();
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentChapter, setCurrentChapter] = useState(1);
  const [showQuiz, setShowQuiz] = useState(false);
  const [showStoryMode, setShowStoryMode] = useState(false);

  // Mock book data - in real app, fetch based on ID
  const book = {
    id: 1,
    title: 'Introduction to Machine Learning',
    author: 'Dr. Sarah Chen',
    type: 'learning',
    progress: 45,
    totalChapters: 8,
    currentChapter: 3,
    image: 'https://images.pexels.com/photos/8386434/pexels-photo-8386434.jpeg?auto=compress&cs=tinysrgb&w=400',
    description: 'Learn the fundamentals of machine learning with interactive tutorials and real-world examples.'
  };

  // Determine if this is an entertainment book
  const isEntertainmentBook = id === '2' || id === '4' || id === '6';
  
  if (isEntertainmentBook) {
    book.title = 'The Crystal Chronicles';
    book.author = 'Elena Mystral';
    book.type = 'entertainment';
    book.description = 'An interactive fantasy adventure where your choices shape the story.';
  }

  const chapters = [
    { id: 1, title: 'What is Machine Learning?', duration: '15 min', completed: true },
    { id: 2, title: 'Types of Machine Learning', duration: '20 min', completed: true },
    { id: 3, title: 'Neural Networks Basics', duration: '25 min', completed: false, current: true },
    { id: 4, title: 'Training Your First Model', duration: '30 min', completed: false },
    { id: 5, title: 'Data Preprocessing', duration: '18 min', completed: false },
    { id: 6, title: 'Model Evaluation', duration: '22 min', completed: false },
    { id: 7, title: 'Advanced Techniques', duration: '35 min', completed: false },
    { id: 8, title: 'Real-World Applications', duration: '28 min', completed: false }
  ];

  const storyChapters = [
    { id: 1, title: 'The Mystical Forest', duration: '10 min', completed: true },
    { id: 2, title: 'The Guardian\'s Test', duration: '15 min', completed: true },
    { id: 3, title: 'The Crystal\'s Power', duration: '20 min', completed: false, current: true },
    { id: 4, title: 'The Ancient Prophecy', duration: '18 min', completed: false },
    { id: 5, title: 'The Final Choice', duration: '25 min', completed: false }
  ];

  const currentChapters = isEntertainmentBook ? storyChapters : chapters;

  const handleQuizComplete = (score: number) => {
    console.log('Quiz completed with score:', score);
    // Handle quiz completion
  };

  const handleStoryChoice = (choice: string, consequence: string) => {
    console.log('Story choice made:', choice, consequence);
    // Handle story progression
  };

  const chapterContent = isEntertainmentBook 
    ? "You stand at the threshold of an ancient crystal chamber, where mystical energies swirl around a floating gem of immense power. The air crackles with magic as you contemplate your next move in this enchanted realm."
    : "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) that process information and learn patterns from data.";

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <Link
                to={isEntertainmentBook ? "/explore" : "/learn"}
                className="flex items-center space-x-2 text-gray-600 hover:text-purple-600 transition-colors"
              >
                <ArrowLeft className="h-5 w-5" />
                <span>Back to {isEntertainmentBook ? 'Stories' : 'Learning'}</span>
              </Link>
              <div className="h-6 w-px bg-gray-300"></div>
              <h1 className="text-lg font-semibold text-gray-900 truncate">
                {book.title}
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                Progress: {book.progress}%
              </div>
              <div className="w-32 bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full transition-all ${
                    isEntertainmentBook 
                      ? 'bg-gradient-to-r from-purple-500 to-pink-600'
                      : 'bg-gradient-to-r from-green-500 to-blue-600'
                  }`}
                  style={{ width: `${book.progress}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar - Chapter List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 sticky top-24">
              <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
                <BookOpen className="h-5 w-5 text-purple-600 mr-2" />
                {isEntertainmentBook ? 'Story Chapters' : 'Chapters'}
              </h2>
              <div className="space-y-2">
                {currentChapters.map((chapter) => (
                  <button
                    key={chapter.id}
                    onClick={() => setCurrentChapter(chapter.id)}
                    className={`w-full text-left p-3 rounded-xl transition-all ${
                      chapter.current
                        ? 'bg-purple-50 border-2 border-purple-200'
                        : chapter.completed
                        ? 'bg-green-50 hover:bg-green-100'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                          chapter.completed
                            ? 'bg-green-500'
                            : chapter.current
                            ? 'bg-purple-500'
                            : 'bg-gray-300'
                        }`}>
                          {chapter.completed ? (
                            <CheckCircle className="h-4 w-4 text-white" />
                          ) : (
                            <span className="text-xs font-medium text-white">
                              {chapter.id}
                            </span>
                          )}
                        </div>
                        <div>
                          <p className={`text-sm font-medium ${
                            chapter.current ? 'text-purple-900' : 'text-gray-900'
                          }`}>
                            {chapter.title}
                          </p>
                          <p className="text-xs text-gray-500">{chapter.duration}</p>
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {/* AI Quiz Component */}
            {showQuiz && !isEntertainmentBook && (
              <div className="mb-8">
                <AIQuizComponent
                  content={chapterContent}
                  onComplete={handleQuizComplete}
                  difficulty="medium"
                />
              </div>
            )}

            {/* Voice Story Component */}
            {(showStoryMode || isEntertainmentBook) && isEntertainmentBook && (
              <div className="mb-8">
                <VoiceStoryComponent
                  storyContent={chapterContent}
                  onChoiceMade={handleStoryChoice}
                />
              </div>
            )}

            {/* Regular Content */}
            {!showQuiz && (!isEntertainmentBook || !showStoryMode) && (
              <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                {/* Content Header */}
                <div className={`p-6 text-white ${
                  isEntertainmentBook 
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600'
                    : 'bg-gradient-to-r from-purple-600 to-blue-600'
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h1 className="text-2xl font-bold mb-2">
                        {isEntertainmentBook ? 'The Crystal\'s Power' : 'Neural Networks Basics'}
                      </h1>
                      <p className="text-purple-100">
                        Chapter 3 of {currentChapters.length} • 25 minutes
                      </p>
                    </div>
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className="bg-white/20 backdrop-blur-sm p-3 rounded-full hover:bg-white/30 transition-colors"
                      >
                        {isPlaying ? (
                          <Pause className="h-6 w-6 text-white" />
                        ) : (
                          <Play className="h-6 w-6 text-white" />
                        )}
                      </button>
                      <button className="bg-white/20 backdrop-blur-sm p-3 rounded-full hover:bg-white/30 transition-colors">
                        <Volume2 className="h-6 w-6 text-white" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Content Body */}
                <div className="p-8">
                  <div className="prose max-w-none">
                    <h2 className="text-xl font-bold text-gray-900 mb-4">
                      {isEntertainmentBook ? 'The Chamber of Crystals' : 'Understanding Neural Networks'}
                    </h2>
                    
                    <p className="text-gray-700 mb-6 leading-relaxed">
                      {chapterContent}
                    </p>

                    {!isEntertainmentBook && (
                      <>
                        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-6">
                          <h3 className="font-semibold text-blue-900 mb-2 flex items-center">
                            <Brain className="h-5 w-5 mr-2" />
                            Key Concept
                          </h3>
                          <p className="text-blue-800">
                            A neural network learns by adjusting the strength of connections between 
                            neurons based on the data it processes, similar to how our brain forms 
                            new connections when we learn.
                          </p>
                        </div>

                        <h3 className="text-lg font-semibold text-gray-900 mb-3">
                          Components of a Neural Network
                        </h3>
                        
                        <ul className="space-y-3 mb-6">
                          <li className="flex items-start space-x-3">
                            <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                            <div>
                              <strong className="text-gray-900">Input Layer:</strong>
                              <span className="text-gray-700"> Receives the initial data</span>
                            </div>
                          </li>
                          <li className="flex items-start space-x-3">
                            <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                            <div>
                              <strong className="text-gray-900">Hidden Layers:</strong>
                              <span className="text-gray-700"> Process and transform the data</span>
                            </div>
                          </li>
                          <li className="flex items-start space-x-3">
                            <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                            <div>
                              <strong className="text-gray-900">Output Layer:</strong>
                              <span className="text-gray-700"> Produces the final result</span>
                            </div>
                          </li>
                        </ul>
                      </>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex justify-between items-center mt-8 pt-6 border-t border-gray-200">
                    <button className="flex items-center space-x-2 text-gray-600 hover:text-purple-600 transition-colors">
                      <MessageCircle className="h-5 w-5" />
                      <span>Ask AI Tutor</span>
                    </button>

                    <div className="flex space-x-3">
                      {isEntertainmentBook ? (
                        <button
                          onClick={() => setShowStoryMode(true)}
                          className="bg-gradient-to-r from-purple-500 to-pink-600 text-white px-6 py-3 rounded-full font-medium hover:from-purple-600 hover:to-pink-700 transition-all transform hover:scale-105"
                        >
                          Enter Interactive Mode
                        </button>
                      ) : (
                        <button
                          onClick={() => setShowQuiz(true)}
                          className="bg-gradient-to-r from-green-500 to-blue-600 text-white px-6 py-3 rounded-full font-medium hover:from-green-600 hover:to-blue-700 transition-all transform hover:scale-105"
                        >
                          Take AI Quiz
                        </button>
                      )}
                      
                      <button className="border border-purple-200 text-purple-600 px-6 py-3 rounded-full font-medium hover:bg-purple-50 transition-colors">
                        Next Chapter
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Achievement Notification */}
            <div className={`mt-6 rounded-2xl p-6 text-white ${
              isEntertainmentBook 
                ? 'bg-gradient-to-r from-purple-500 to-pink-600'
                : 'bg-gradient-to-r from-green-500 to-blue-600'
            }`}>
              <div className="flex items-center space-x-4">
                <div className="bg-white/20 p-3 rounded-full">
                  <Award className="h-8 w-8 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-lg">Achievement Unlocked!</h3>
                  <p className={isEntertainmentBook ? 'text-purple-100' : 'text-green-100'}>
                    {isEntertainmentBook 
                      ? 'Story Explorer - Begin your interactive adventure'
                      : 'Neural Network Explorer - Complete your first AI lesson'
                    }
                  </p>
                </div>
                <div className="ml-auto">
                  <button className="bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full hover:bg-white/30 transition-colors">
                    <Share2 className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}