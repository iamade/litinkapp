import OpenAI from 'openai';

// Initialize OpenAI with fallback for demo mode
const openai = new OpenAI({
  apiKey: import.meta.env.VITE_OPENAI_API_KEY || 'demo_key_for_development',
  dangerouslyAllowBrowser: true
});

export interface QuizQuestion {
  id: number;
  question: string;
  options: string[];
  correct: number;
  explanation: string;
}

export interface LessonContent {
  title: string;
  content: string;
  keyPoints: string[];
  examples: string[];
}

export class AIService {
  static async generateQuiz(bookContent: string, difficulty: 'easy' | 'medium' | 'hard' = 'medium'): Promise<QuizQuestion[]> {
    try {
      // Check if we have a real API key
      const apiKey = import.meta.env.VITE_OPENAI_API_KEY;
      if (!apiKey || apiKey === 'demo_key_for_development') {
        // Return mock data for demo
        return this.getMockQuiz(difficulty);
      }

      const response = await openai.chat.completions.create({
        model: "gpt-3.5-turbo",
        messages: [
          {
            role: "system",
            content: `You are an expert educator. Generate ${difficulty} level quiz questions based on the provided content. Return exactly 5 questions in JSON format with this structure: {"questions": [{"id": 1, "question": "...", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "..."}]}`
          },
          {
            role: "user",
            content: `Generate quiz questions for this content: ${bookContent.substring(0, 2000)}`
          }
        ],
        temperature: 0.7,
        max_tokens: 1500
      });

      const result = JSON.parse(response.choices[0].message.content || '{}');
      return result.questions || this.getMockQuiz(difficulty);
    } catch (error) {
      console.warn('OpenAI API error, using mock data:', error);
      return this.getMockQuiz(difficulty);
    }
  }

  static async generateLesson(bookContent: string, topic: string): Promise<LessonContent> {
    try {
      const apiKey = import.meta.env.VITE_OPENAI_API_KEY;
      if (!apiKey || apiKey === 'demo_key_for_development') {
        return this.getMockLesson(topic);
      }

      const response = await openai.chat.completions.create({
        model: "gpt-3.5-turbo",
        messages: [
          {
            role: "system",
            content: "You are an expert educator. Create an engaging lesson based on the provided content. Return JSON format: {\"title\": \"...\", \"content\": \"...\", \"keyPoints\": [...], \"examples\": [...]}"
          },
          {
            role: "user",
            content: `Create a lesson about "${topic}" from this content: ${bookContent.substring(0, 2000)}`
          }
        ],
        temperature: 0.7,
        max_tokens: 1000
      });

      const result = JSON.parse(response.choices[0].message.content || '{}');
      return result || this.getMockLesson(topic);
    } catch (error) {
      console.warn('OpenAI API error, using mock data:', error);
      return this.getMockLesson(topic);
    }
  }

  private static getMockQuiz(difficulty: string): QuizQuestion[] {
    const questions = {
      easy: [
        {
          id: 1,
          question: "What is the main purpose of a neural network?",
          options: [
            "To store data efficiently",
            "To mimic the human brain's learning process",
            "To create user interfaces",
            "To manage databases"
          ],
          correct: 1,
          explanation: "Neural networks are designed to mimic how the human brain processes information and learns patterns."
        }
      ],
      medium: [
        {
          id: 1,
          question: "Which component of a neural network adjusts during training?",
          options: [
            "Input data",
            "Output labels",
            "Weights and biases",
            "Network architecture"
          ],
          correct: 2,
          explanation: "During training, the weights and biases are adjusted to minimize the error between predicted and actual outputs."
        }
      ],
      hard: [
        {
          id: 1,
          question: "What is the vanishing gradient problem in deep neural networks?",
          options: [
            "Gradients become too large during backpropagation",
            "Gradients become very small in early layers during backpropagation",
            "The network fails to converge",
            "The learning rate becomes zero"
          ],
          correct: 1,
          explanation: "The vanishing gradient problem occurs when gradients become exponentially smaller as they propagate back through the network, making it difficult to train early layers effectively."
        }
      ]
    };

    return questions[difficulty as keyof typeof questions] || questions.medium;
  }

  private static getMockLesson(topic: string): LessonContent {
    return {
      title: `Understanding ${topic}`,
      content: `This lesson covers the fundamental concepts of ${topic}. We'll explore the key principles, practical applications, and real-world examples to help you master this important topic.`,
      keyPoints: [
        `Core concepts of ${topic}`,
        "Practical applications",
        "Real-world examples",
        "Best practices"
      ],
      examples: [
        "Example 1: Basic implementation",
        "Example 2: Advanced use case",
        "Example 3: Industry application"
      ]
    };
  }
}

// Create and export an instance for named import
export const aiService = new AIService();