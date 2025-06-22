import React, { useState, useEffect } from 'react';
import { aiService, QuizQuestion } from '../services/aiService';
import { blockchainService } from '../services/blockchainService';
import { Brain, CheckCircle, XCircle, Award, Loader } from 'lucide-react';

interface AIQuizComponentProps {
  content: string;
  onComplete: (score: number) => void;
  difficulty?: 'easy' | 'medium' | 'hard';
}

export default function AIQuizComponent({ content, onComplete, difficulty = 'medium' }: AIQuizComponentProps) {
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [answers, setAnswers] = useState<number[]>([]);
  const [showResult, setShowResult] = useState(false);
  const [loading, setLoading] = useState(true);
  const [earnedBadge, setEarnedBadge] = useState<any>(null);
  const [generatingBadge, setGeneratingBadge] = useState(false);

  useEffect(() => {
    generateQuiz();
  }, [content, difficulty]);

  const generateQuiz = async () => {
    setLoading(true);
    try {
      const generatedQuestions = await aiService.generateQuiz(content, difficulty);
      setQuestions(generatedQuestions);
    } catch (error) {
      console.error('Error generating quiz:', error);
      // Use fallback questions
      setQuestions([
        {
          id: '1',
          question: 'What is the main concept discussed in this chapter?',
          options: ['Neural networks learn patterns', 'Computers store data', 'Programming languages', 'Database management'],
          correctAnswer: 0,
          explanation: 'Neural networks are designed to learn and recognize patterns in data, similar to how the human brain processes information.',
          difficulty: 'medium'
        },
        {
          id: '2',
          question: 'Which component receives the initial data in a neural network?',
          options: ['Hidden layer', 'Output layer', 'Input layer', 'Processing layer'],
          correctAnswer: 2,
          explanation: 'The input layer is the first layer that receives and processes the initial data before passing it to hidden layers.',
          difficulty: 'easy'
        },
        {
          id: '3',
          question: 'What happens in the hidden layers of a neural network?',
          options: ['Data storage', 'Data transformation and processing', 'Final output generation', 'Error correction'],
          correctAnswer: 1,
          explanation: 'Hidden layers are responsible for transforming and processing the data through weighted connections and activation functions.',
          difficulty: 'medium'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSelect = (answerIndex: number) => {
    setSelectedAnswer(answerIndex);
  };

  const handleNextQuestion = () => {
    if (selectedAnswer === null) return;

    const newAnswers = [...answers, selectedAnswer];
    setAnswers(newAnswers);

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
      setSelectedAnswer(null);
    } else {
      // Quiz completed
      const score = calculateScore(newAnswers);
      setShowResult(true);
      onComplete(score);
      
      // Award badge if score is high enough
      if (score >= 80) {
        awardBadge(score);
      }
    }
  };

  const calculateScore = (userAnswers: number[]): number => {
    const correct = userAnswers.reduce((count, answer, index) => {
      return count + (answer === questions[index]?.correctAnswer ? 1 : 0);
    }, 0);
    return Math.round((correct / questions.length) * 100);
  };

  const awardBadge = async (score: number) => {
    setGeneratingBadge(true);
    try {
      const badgeName = score === 100 ? 'Perfect Score' : score >= 90 ? 'Quiz Master' : 'Knowledge Seeker';
      const badge = await blockchainService.simulateEarnBadge(badgeName);
      setEarnedBadge(badge);
    } catch (error) {
      console.error('Error awarding badge:', error);
    } finally {
      setGeneratingBadge(false);
    }
  };

  const resetQuiz = () => {
    setCurrentQuestion(0);
    setSelectedAnswer(null);
    setAnswers([]);
    setShowResult(false);
    setEarnedBadge(null);
    generateQuiz();
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
        <div className="text-center">
          <Loader className="h-12 w-12 text-purple-600 mx-auto mb-4 animate-spin" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Generating AI Quiz</h3>
          <p className="text-gray-600">Creating personalized questions based on your content...</p>
        </div>
      </div>
    );
  }

  if (showResult) {
    const score = calculateScore(answers);
    
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
        <div className="text-center mb-6">
          <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4 ${
            score >= 80 ? 'bg-green-100' : score >= 60 ? 'bg-yellow-100' : 'bg-red-100'
          }`}>
            {score >= 80 ? (
              <CheckCircle className="h-10 w-10 text-green-600" />
            ) : (
              <XCircle className="h-10 w-10 text-red-600" />
            )}
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-2">Quiz Complete!</h3>
          <p className="text-4xl font-bold text-purple-600 mb-2">{score}%</p>
          <p className="text-gray-600">
            You got {answers.filter((answer, index) => answer === questions[index]?.correctAnswer).length} out of {questions.length} questions correct
          </p>
        </div>

        {/* Badge Award */}
        {(earnedBadge || generatingBadge) && (
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl p-6 mb-6">
            {generatingBadge ? (
              <div className="text-center">
                <Loader className="h-8 w-8 text-purple-600 mx-auto mb-2 animate-spin" />
                <p className="text-purple-800 font-medium">Minting your achievement badge...</p>
              </div>
            ) : earnedBadge ? (
              <div className="text-center">
                <Award className="h-12 w-12 text-purple-600 mx-auto mb-3" />
                <h4 className="text-lg font-bold text-purple-900 mb-2">🎉 Badge Earned!</h4>
                <p className="text-purple-800 font-medium">{earnedBadge.name}</p>
                <p className="text-sm text-purple-600 mt-1">Blockchain-verified achievement</p>
                <div className="mt-3 text-xs text-purple-600">
                  Asset ID: {earnedBadge.assetId} | TX: {earnedBadge.transactionId?.substring(0, 8)}...
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* Answer Review */}
        <div className="space-y-4 mb-6">
          <h4 className="font-semibold text-gray-900">Review Your Answers:</h4>
          {questions.map((question, index) => (
            <div key={question.id} className="border border-gray-200 rounded-lg p-4">
              <p className="font-medium text-gray-900 mb-2">{question.question}</p>
              <div className="space-y-2">
                {question.options.map((option, optionIndex) => (
                  <div
                    key={optionIndex}
                    className={`p-2 rounded text-sm ${
                      optionIndex === question.correctAnswer
                        ? 'bg-green-100 text-green-800 border border-green-300'
                        : optionIndex === answers[index]
                        ? 'bg-red-100 text-red-800 border border-red-300'
                        : 'bg-gray-50 text-gray-700'
                    }`}
                  >
                    {option}
                    {optionIndex === question.correctAnswer && ' ✓'}
                    {optionIndex === answers[index] && optionIndex !== question.correctAnswer && ' ✗'}
                  </div>
                ))}
              </div>
              <p className="text-sm text-gray-600 mt-2 italic">{question.explanation}</p>
            </div>
          ))}
        </div>

        <div className="flex space-x-4">
          <button
            onClick={resetQuiz}
            className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 px-6 rounded-full font-medium hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105"
          >
            Try Again
          </button>
          <button
            onClick={() => window.history.back()}
            className="flex-1 border border-gray-300 text-gray-700 py-3 px-6 rounded-full font-medium hover:bg-gray-50 transition-colors"
          >
            Continue Learning
          </button>
        </div>
      </div>
    );
  }

  const currentQ = questions[currentQuestion];
  if (!currentQ) return null;

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Question {currentQuestion + 1} of {questions.length}</span>
          <span>{difficulty.charAt(0).toUpperCase() + difficulty.slice(1)} Level</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-gradient-to-r from-purple-600 to-blue-600 h-2 rounded-full transition-all"
            style={{ width: `${((currentQuestion + 1) / questions.length) * 100}%` }}
          ></div>
        </div>
      </div>

      {/* Question */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <Brain className="h-6 w-6 text-purple-600 mr-2" />
          <h3 className="text-xl font-bold text-gray-900">AI-Generated Question</h3>
        </div>
        <p className="text-lg text-gray-800 leading-relaxed">{currentQ.question}</p>
      </div>

      {/* Answer Options */}
      <div className="space-y-3 mb-8">
        {currentQ.options.map((option, index) => (
          <button
            key={index}
            onClick={() => handleAnswerSelect(index)}
            className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
              selectedAnswer === index
                ? 'border-purple-500 bg-purple-50 text-purple-900'
                : 'border-gray-300 hover:border-purple-300 hover:bg-purple-50 text-gray-700'
            }`}
          >
            <span className="font-medium text-gray-900 mr-3">
              {String.fromCharCode(65 + index)}.
            </span>
            {option}
          </button>
        ))}
      </div>

      {/* Next Button */}
      <div className="flex justify-end">
        <button
          onClick={handleNextQuestion}
          disabled={selectedAnswer === null}
          className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-8 py-3 rounded-full font-medium hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105"
        >
          {currentQuestion < questions.length - 1 ? 'Next Question' : 'Complete Quiz'}
        </button>
      </div>
    </div>
  );
}