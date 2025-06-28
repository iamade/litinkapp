import React from 'react';
import { Link } from 'react-router-dom';
import { Brain, Sparkles, Users, ArrowRight, Play, Star, Award } from 'lucide-react';

export default function HomePage() {
  const features = [
    {
      icon: Brain,
      title: 'AI-Powered Learning',
      description: 'Transform any book into personalized interactive tutorials and smart quizzes powered by advanced AI.'
    },
    {
      icon: Sparkles,
      title: 'Interactive Stories',
      description: 'Convert novels into branching narrative experiences with voice-driven characters and AI-generated scenes.'
    },
    {
      icon: Award,
      title: 'Verified Credentials',
      description: 'Earn blockchain-verified badges and collect animated NFTs as you progress through your learning journey.'
    },
    {
      icon: Users,
      title: 'Multi-Language Support',
      description: 'Experience books in multiple languages with AI-powered narration and localized content.'
    }
  ];

  const testimonials = [
    {
      name: 'Sarah Chen',
      role: 'Student',
      content: 'Litink transformed how I study. The AI-generated quizzes help me retain information better than ever before.',
      rating: 5
    },
    {
      name: 'Marcus Johnson',
      role: 'Author',
      content: 'As an author, seeing my books come alive as interactive experiences is incredible. My readers are more engaged than ever.',
      rating: 5
    },
    {
      name: 'Elena Rodriguez',
      role: 'Educator',
      content: 'The learning mode has revolutionized my classroom. Students are excited about reading again.',
      rating: 5
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 lg:py-32">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700 opacity-90"></div>
        <div className="absolute inset-0 bg-black/20"></div>
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex justify-center mb-8">
            <img 
              src="/litink.png" 
              alt="Litink Logo" 
              className="h-24 w-24 object-contain"
            />
          </div>
          
          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold text-white mb-6 leading-tight">
            Reimagining Books as
            <span className="block bg-gradient-to-r from-yellow-400 to-orange-400 bg-clip-text text-transparent">
              Living Experiences
            </span>
          </h1>
          
          <p className="text-xl sm:text-2xl text-white/90 mb-12 max-w-3xl mx-auto leading-relaxed">
            Transform any book into immersive AI-powered learning adventures or interactive entertainment experiences. 
            The future of reading is here at Litink.com.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
            <Link
              to="/auth"
              className="group bg-white text-purple-600 px-8 py-4 rounded-full font-bold text-lg hover:bg-gray-100 transition-all transform hover:scale-105 flex items-center space-x-2 shadow-xl"
            >
              <span>Start Learning</span>
              <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            
            <Link
              to="/explore"
              className="group border-2 border-white text-white px-8 py-4 rounded-full font-bold text-lg hover:bg-white hover:text-purple-600 transition-all transform hover:scale-105 flex items-center space-x-2"
            >
              <Play className="h-5 w-5" />
              <span>Explore Stories</span>
            </Link>
          </div>

          {/* Quick Demo Access */}
          <div className="mt-8 p-4 bg-white/10 backdrop-blur-sm rounded-xl max-w-md mx-auto">
            <p className="text-white/90 text-sm mb-3">Experience Litink.com:</p>
            <div className="flex flex-col sm:flex-row gap-2 text-xs">
              <Link
                to="/auth"
                className="bg-green-500/20 text-white px-3 py-2 rounded-lg hover:bg-green-500/30 transition-colors"
              >
                Sign up as Explorer
              </Link>
              <Link
                to="/auth"
                className="bg-purple-500/20 text-white px-3 py-2 rounded-lg hover:bg-purple-500/30 transition-colors"
              >
                Sign up as Author
              </Link>
            </div>
          </div>
        </div>
        
        {/* Floating Elements */}
        <div className="absolute top-20 left-10 opacity-20">
          <img 
            src="/litink.png" 
            alt="Litink Logo" 
            className="h-16 w-16 object-contain animate-bounce"
          />
        </div>
        <div className="absolute top-20 right-10 opacity-20">
          <a
            href="https://bolt.new/"
            target="_blank"
            rel="noopener noreferrer"
            className="block"
            title="Powered by Bolt"
          >
            <img 
              src="/boltlogo.png" 
              alt="Powered by Bolt" 
              className="h-16 w-16 object-contain animate-bounce"
            />
          </a>
        </div>
        <div className="absolute bottom-20 right-10 opacity-20">
          <Sparkles className="h-12 w-12 text-white animate-pulse" />
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Powerful Features for Every Reader
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Whether you're learning or exploring, Litink.com provides cutting-edge tools to enhance your reading experience.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group p-8 rounded-2xl bg-gradient-to-br from-purple-50 to-blue-50 hover:from-purple-100 hover:to-blue-100 transition-all transform hover:scale-105 hover:shadow-xl"
              >
                <div className="bg-gradient-to-br from-purple-600 to-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <feature.icon className="h-8 w-8 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-4">{feature.title}</h3>
                <p className="text-gray-600 leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* User Paths Section */}
      <section className="py-20 bg-gradient-to-br from-gray-50 to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Choose Your Adventure on Litink.com
            </h2>
            <p className="text-xl text-gray-600">
              Two distinct paths tailored to your goals and interests.
            </p>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            {/* Learning Path */}
            <div className="group relative overflow-hidden rounded-3xl bg-white shadow-xl hover:shadow-2xl transition-all transform hover:scale-105">
              <div className="absolute inset-0 bg-gradient-to-br from-green-400 to-blue-500 opacity-10 group-hover:opacity-20 transition-opacity"></div>
              <div className="relative p-10">
                <div className="bg-gradient-to-br from-green-500 to-blue-600 w-20 h-20 rounded-2xl flex items-center justify-center mb-8">
                  <Brain className="h-10 w-10 text-white" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">Learning Mode</h3>
                <p className="text-gray-600 mb-8 text-lg leading-relaxed">
                  Transform educational books into interactive tutorials, personalized lessons, and smart quizzes. 
                  Earn verified credentials and track your progress with AI-powered learning analytics.
                </p>
                <ul className="space-y-3 mb-8">
                  <li className="flex items-center text-gray-700">
                    <ArrowRight className="h-5 w-5 text-green-500 mr-3" />
                    AI-generated personalized lessons
                  </li>
                  <li className="flex items-center text-gray-700">
                    <ArrowRight className="h-5 w-5 text-green-500 mr-3" />
                    Interactive tutorials and quizzes
                  </li>
                  <li className="flex items-center text-gray-700">
                    <ArrowRight className="h-5 w-5 text-green-500 mr-3" />
                    Blockchain-verified badges
                  </li>
                  <li className="flex items-center text-gray-700">
                    <ArrowRight className="h-5 w-5 text-green-500 mr-3" />
                    Voice interaction support
                  </li>
                </ul>
                <Link
                  to="/learn"
                  className="inline-flex items-center space-x-2 bg-gradient-to-r from-green-500 to-blue-600 text-white px-6 py-3 rounded-full font-semibold hover:from-green-600 hover:to-blue-700 transition-all"
                >
                  <span>Start Learning</span>
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </div>
            </div>
            
            {/* Entertainment Path */}
            <div className="group relative overflow-hidden rounded-3xl bg-white shadow-xl hover:shadow-2xl transition-all transform hover:scale-105">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-400 to-pink-500 opacity-10 group-hover:opacity-20 transition-opacity"></div>
              <div className="relative p-10">
                <div className="bg-gradient-to-br from-purple-500 to-pink-600 w-20 h-20 rounded-2xl flex items-center justify-center mb-8">
                  <Sparkles className="h-10 w-10 text-white" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">Entertainment Mode</h3>
                <p className="text-gray-600 mb-8 text-lg leading-relaxed">
                  Convert novels and stories into branching narrative experiences with voice-driven characters, 
                  AI-generated scenes, and collectible animated NFTs.
                </p>
                <ul className="space-y-3 mb-8">
                  <li className="flex items-center text-gray-700">
                    <ArrowRight className="h-5 w-5 text-purple-500 mr-3" />
                    Choose-your-path adventures
                  </li>
                  <li className="flex items-center text-gray-700">
                    <ArrowRight className="h-5 w-5 text-purple-500 mr-3" />
                    AI-driven character voices
                  </li>
                  <li className="flex items-center text-gray-700">
                    <ArrowRight className="h-5 w-5 text-purple-500 mr-3" />
                    Animated NFT collectibles
                  </li>
                  <li className="flex items-center text-gray-700">
                    <ArrowRight className="h-5 w-5 text-purple-500 mr-3" />
                    Video scene generation
                  </li>
                </ul>
                <Link
                  to="/explore"
                  className="inline-flex items-center space-x-2 bg-gradient-to-r from-purple-500 to-pink-600 text-white px-6 py-3 rounded-full font-semibold hover:from-purple-600 hover:to-pink-700 transition-all"
                >
                  <span>Explore Stories</span>
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              What Our Litink.com Users Say
            </h2>
            <p className="text-xl text-gray-600">
              Join thousands of readers who have transformed their reading experience.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <div
                key={index}
                className="bg-gradient-to-br from-purple-50 to-blue-50 p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
              >
                <div className="flex items-center mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="h-5 w-5 text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className="text-gray-700 mb-6 italic leading-relaxed">
                  "{testimonial.content}"
                </p>
                <div>
                  <p className="font-semibold text-gray-900">{testimonial.name}</p>
                  <p className="text-purple-600">{testimonial.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
            Ready to Transform Your Reading Experience?
          </h2>
          <p className="text-xl text-white/90 mb-12">
            Join Litink.com today and discover a new way to learn, explore, and engage with books.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-6 justify-center">
            <Link
              to="/learn"
              className="bg-white text-purple-600 px-8 py-4 rounded-full font-bold text-lg hover:bg-gray-100 transition-all transform hover:scale-105 shadow-xl"
            >
              For Learners
            </Link>
            <Link
              to="/explore"
              className="bg-transparent border-2 border-white text-white px-8 py-4 rounded-full font-bold text-lg hover:bg-white hover:text-purple-600 transition-all transform hover:scale-105"
            >
              For Explorers
            </Link>
            <Link
              to="/auth"
              className="bg-gradient-to-r from-yellow-400 to-orange-500 text-white px-8 py-4 rounded-full font-bold text-lg hover:from-yellow-500 hover:to-orange-600 transition-all transform hover:scale-105 shadow-xl"
            >
              For Authors
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}