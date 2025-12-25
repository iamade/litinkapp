import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  ArrowRight,
  Play,
  Star,
  Brain,
  CheckCircle2,
  X,
  ChevronDown,
  Video,
  Twitter,
  Github,
  Linkedin
} from "lucide-react";
import { subscriptionService, SubscriptionTier } from "../services/subscriptionService";
import SubscriptionTierCard from "../components/Subscription/SubscriptionTierCard";

export default function HomePage() {
  const navigate = useNavigate();
  const [tiers, setTiers] = useState<SubscriptionTier[]>([]);
  const [loadingTiers, setLoadingTiers] = useState(true);
  const [isVideoOpen, setIsVideoOpen] = useState(false);

  // Fetch subscription tiers
  useEffect(() => {
    const fetchTiers = async () => {
      try {
        const data = await subscriptionService.getSubscriptionTiers();
        setTiers(data);
      } catch (error) {
        console.error("Failed to fetch subscription tiers", error);
      } finally {
        setLoadingTiers(false);
      }
    };
    fetchTiers();
  }, []);

  const handleSubscribe = (_tier: SubscriptionTier) => {
    navigate('/subscription');
  };

  const steps = [
    {
      num: "01",
      title: "Upload Your Content",
      desc: "Upload any book, script, or document. Our AI analyzes the structure and characters instantly."
    },
    {
      num: "02",
      title: "Customize Settings",
      desc: "Choose your preferred style, tone, and visual aesthetic. Select AI voices for your characters."
    },
    {
      num: "03",
      title: "Generate Assets",
      desc: "Watch as AI generates scripts, storyboards, images, and voiceovers automatically."
    },
    {
      num: "04",
      title: "Export Video",
      desc: "Preview your masterpiece, make final tweaks, and export in 4K resolution ready for sharing."
    }
  ];

  const faqs = [
    {
      q: "How does the AI video generation work?",
      a: "Our platform uses advanced multimodal AI models to analyze your text, generate relevant visuals, synthesized voices, and perfectly timed animations to create cohesive videos."
    },
    {
      q: "Can I use my own voice?",
      a: "Yes! Pro and Team plans include voice cloning capabilities, allowing you to use your own voice or custom voice actors for your characters."
    },
    {
      q: "What file formats do you support?",
      a: "We support PDF, EPUB, DOCX, and TXT for uploads. Videos are exported in MP4 (H.264) format, compatible with all major platforms."
    },
    {
      q: "Is there a free trial?",
      a: "Yes, our Free tier lets you generate up to 2 videos per month so you can experience the power of Litink AI before upgrading."
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0F0F23] text-gray-900 dark:text-white selection:bg-purple-500/30 transition-colors duration-300">
      
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full z-0 pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/10 dark:bg-purple-600/20 rounded-full blur-[120px] animate-pulse"></div>
          <div className="absolute top-[20%] right-[-10%] w-[40%] h-[40%] bg-blue-600/10 dark:bg-blue-600/20 rounded-full blur-[120px] animate-pulse delay-1000"></div>
          <div className="absolute bottom-[-10%] left-[20%] w-[40%] h-[40%] bg-pink-600/10 dark:bg-pink-600/20 rounded-full blur-[120px] animate-pulse delay-2000"></div>
        </div>

        <div className="container mx-auto px-4 relative z-10 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-200 dark:bg-white/5 border border-gray-300 dark:border-white/10 mb-8 animate-fade-in-up">
            <span className="flex h-2 w-2 rounded-full bg-green-500"></span>
            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">New: Multi-Language Support Available</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-tight max-w-5xl mx-auto">
            Turn Any Idea or Script Into <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400">
              Engaging AI Video
            </span> — Instantly
          </h1>

          <p className="text-xl text-gray-600 dark:text-gray-400 mb-10 max-w-3xl mx-auto leading-relaxed">
            Create professional-quality videos for education or entertainment with just a prompt or a script upload. 
            Litink AI analyzes your text, generates scenes, characters, and voiceovers, transforming static content into 
            cinematic experiences in minutes. No cameras. No editing. No limits.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
            <Link
              to="/auth"
              className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 rounded-full font-bold text-lg text-white hover:shadow-lg hover:shadow-purple-500/25 transition-all transform hover:scale-105 flex items-center gap-2"
            >
              Start Creating Free
              <ArrowRight className="w-5 h-5" />
            </Link>
            <button 
              onClick={() => setIsVideoOpen(true)}
              className="px-8 py-4 bg-gray-200 dark:bg-white/5 border border-gray-300 dark:border-white/10 rounded-full font-bold text-lg hover:bg-gray-300 dark:hover:bg-white/10 transition-all flex items-center gap-2 backdrop-blur-sm"
            >
              <Play className="w-5 h-5 fill-current" />
              Watch Demo
            </button>
          </div>

          {/* Hero Visual */}
          <div className="relative max-w-5xl mx-auto rounded-2xl overflow-hidden shadow-2xl border border-gray-200 dark:border-white/10 group">
            <div className="absolute inset-0 bg-gradient-to-t from-gray-50 dark:from-[#0F0F23] via-transparent to-transparent z-10"></div>
            
            {/* CSS Animated Loop Image */}
            <div className="aspect-video relative overflow-hidden bg-gray-200 dark:bg-gray-900 group cursor-pointer" onClick={() => setIsVideoOpen(true)}>
               <img 
                src="/images/hero-1.png" 
                alt="AI Video Creation Interface" 
                className="w-full h-full object-cover opacity-80 animate-slow-zoom transition-transform duration-700 group-hover:scale-105"
              />
              
              {/* Overlay UI Elements to simulate interface */}
              <div className="absolute inset-0 z-20 flex items-center justify-center">
                 <div className="w-16 h-16 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center border border-white/30 cursor-pointer group-hover:scale-110 transition-transform hover:bg-white/30">
                    <Play className="w-8 h-8 text-white fill-white ml-1" />
                 </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 bg-gray-100 dark:bg-[#0A0A1B] relative transition-colors duration-300">
        <div className="container mx-auto px-4 relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">How <span className="text-purple-500 dark:text-purple-400">It Works</span></h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">From text to video in four simple steps. No video editing skills required.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {steps.map((step, idx) => (
              <div key={idx} className="relative group">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-gray-200 dark:border-white/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                  <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">{step.num}</span>
                </div>
                <h3 className="text-xl font-bold mb-3">{step.title}</h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">{step.desc}</p>
                
                {idx < steps.length - 1 && (
                  <div className="hidden md:block absolute top-8 left-[60%] w-[80%] h-[2px] bg-gradient-to-r from-purple-500/20 to-transparent"></div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Key Features */}
      <section className="py-24 relative overflow-hidden">
        <div className="container mx-auto px-4">
          <div className="flex flex-col lg:flex-row items-center gap-16">
            <div className="lg:w-1/2">
              <span className="text-purple-500 dark:text-purple-400 font-semibold tracking-wider uppercase text-sm mb-2 block">Key Features</span>
              <h2 className="text-4xl md:text-5xl font-bold mb-6">Create Professional Videos <br />Without a Camera</h2>
              <p className="text-gray-600 dark:text-gray-400 text-lg mb-8">
                Access a suite of AI tools designed to automate the entire video production workflow.
              </p>

              <div className="space-y-6">
                {[
                  { title: "AI Script Analysis", desc: "Automatically breaks down your text into scenes and shots." },
                  { title: "Cinematic Visuals", desc: "Generates consistent characters and environments." },
                  { title: "Voice Synthesis", desc: "Ultra-realistic AI voices in 50+ languages." },
                  { title: "Smart Editing", desc: "Auto-syncs audio, visuals, and transitions." }
                ].map((item, i) => (
                  <div key={i} className="flex gap-4 p-4 rounded-xl bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/5 hover:border-purple-500/30 transition-colors">
                    <div className="mt-1">
                      <CheckCircle2 className="w-5 h-5 text-purple-500 dark:text-purple-400" />
                    </div>
                    <div>
                      <h4 className="font-bold mb-1">{item.title}</h4>
                      <p className="text-gray-600 dark:text-gray-400 text-sm">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="lg:w-1/2 relative">
               <div className="relative rounded-2xl overflow-hidden border border-gray-200 dark:border-white/10 shadow-2xl">
                  <img 
                    src="https://images.unsplash.com/photo-1535930749574-1399327ce78f?q=80&w=1000&auto=format&fit=crop" 
                    alt="AI Video Features" 
                    className="w-full h-auto"
                  />
                  <div className="absolute bottom-6 left-6 right-6">
                     <div className="bg-black/60 backdrop-blur-md p-4 rounded-xl border border-white/10">
                        <div className="flex items-center gap-3 mb-2">
                           <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                           <span className="text-xs font-mono text-green-400">GENERATING SCENE 4/12...</span>
                        </div>
                        <div className="w-full h-1 bg-gray-700 rounded-full overflow-hidden">
                           <div className="w-[65%] h-full bg-gradient-to-r from-purple-500 to-pink-500"></div>
                        </div>
                     </div>
                  </div>
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="py-24 bg-gray-100 dark:bg-[#0A0A1B] transition-colors duration-300">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <span className="text-pink-500 dark:text-pink-400 font-semibold tracking-wider uppercase text-sm mb-2 block">Use Cases</span>
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Who is <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-400">Litink</span> For?</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="group p-8 rounded-3xl bg-gradient-to-b from-purple-100 dark:from-purple-900/20 to-transparent border border-gray-200 dark:border-white/5 hover:border-purple-500/30 transition-all hover:-translate-y-2">
              <div className="w-14 h-14 rounded-full bg-purple-500/20 flex items-center justify-center mb-6 text-purple-500 dark:text-purple-400">
                <Brain className="w-7 h-7" />
              </div>
              <h3 className="text-2xl font-bold mb-4">For Educators</h3>
              <p className="text-gray-600 dark:text-gray-400 leading-relaxed mb-6">
                Transform textbooks into interactive lessons with AI quizzes and progress tracking. 
                Make learning immersive and engaging for every student.
              </p>
              <Link to="/learn" className="text-purple-500 dark:text-purple-400 font-semibold flex items-center gap-2 group-hover:gap-3 transition-all">
                Start Teaching <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="group p-8 rounded-3xl bg-gradient-to-b from-blue-100 dark:from-blue-900/20 to-transparent border border-gray-200 dark:border-white/5 hover:border-blue-500/30 transition-all hover:-translate-y-2">
              <div className="w-14 h-14 rounded-full bg-blue-500/20 flex items-center justify-center mb-6 text-blue-500 dark:text-blue-400">
                <BriefcaseIcon className="w-7 h-7" />
              </div>
              <h3 className="text-2xl font-bold mb-4">For Businesses</h3>
              <p className="text-gray-600 dark:text-gray-400 leading-relaxed mb-6">
                 Create professional training videos and onboarding content at scale. 
                 Maintain consistency across your organization without expensive production teams.
              </p>
              <Link to="/auth" className="text-blue-500 dark:text-blue-400 font-semibold flex items-center gap-2 group-hover:gap-3 transition-all">
                Get Started <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="group p-8 rounded-3xl bg-gradient-to-b from-pink-100 dark:from-pink-900/20 to-transparent border border-gray-200 dark:border-white/5 hover:border-pink-500/30 transition-all hover:-translate-y-2">
              <div className="w-14 h-14 rounded-full bg-pink-500/20 flex items-center justify-center mb-6 text-pink-500 dark:text-pink-400">
                <Video className="w-7 h-7" />
              </div>
              <h3 className="text-2xl font-bold mb-4">For Creators</h3>
              <p className="text-gray-600 dark:text-gray-400 leading-relaxed mb-6">
                 Turn your stories into animated videos with AI-generated visuals and voices.
                 Build your audience with high-quality content produced in record time.
              </p>
              <Link to="/creator" className="text-pink-500 dark:text-pink-400 font-semibold flex items-center gap-2 group-hover:gap-3 transition-all">
                Start Creating <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-24 relative">
        <div className="container mx-auto px-4">
           <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Simple, Transparent <span className="text-cyan-500 dark:text-cyan-400">Pricing</span></h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">Start for free, upgrade when you're ready.</p>
          </div>

          {loadingTiers ? (
            <div className="flex justify-center py-12">
               <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 dark:border-white"></div>
            </div>
          ) : (
             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {tiers.filter(t => t.is_active).map(tier => (
                   <SubscriptionTierCard 
                      key={tier.tier} 
                      tier={tier} 
                      onSelect={handleSubscribe} 
                   />
                ))}
             </div>
          )}
        </div>
      </section>

      {/* FAQ */}
      <section className="py-24 bg-gray-100 dark:bg-[#0A0A1B] transition-colors duration-300">
        <div className="container mx-auto px-4">
           <div className="flex flex-col lg:flex-row gap-16">
              <div className="lg:w-1/3">
                 <h2 className="text-4xl font-bold mb-6">Frequently Asked <br />Questions</h2>
                 <p className="text-gray-600 dark:text-gray-400 mb-8">
                    Can't find the answer you're looking for? Reach out to our customer support team.
                 </p>
                 <button className="px-6 py-3 bg-gray-200 dark:bg-white/5 border border-gray-300 dark:border-white/10 rounded-lg font-semibold hover:bg-gray-300 dark:hover:bg-white/10 transition-all">
                    Contact Support
                 </button>
              </div>

              <div className="lg:w-2/3 space-y-4">
                 {faqs.map((faq, i) => (
                    <div key={i} className="border border-gray-200 dark:border-white/10 rounded-xl bg-white dark:bg-white/5 overflow-hidden">
                       <details className="group">
                          <summary className="flex justify-between items-center font-medium cursor-pointer p-6">
                             <span className="text-lg font-semibold">{faq.q}</span>
                             <span className="transition group-open:rotate-180">
                                <ChevronDown className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                             </span>
                          </summary>
                          <div className="text-gray-600 dark:text-gray-400 mt-0 px-6 pb-6 leading-relaxed">
                             {faq.a}
                          </div>
                       </details>
                    </div>
                 ))}
              </div>
           </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 relative">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Loved by <span className="text-purple-500 dark:text-purple-400">Thousands</span></h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">See what creators and educators are saying about Litink.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                text: "Litink has completely transformed how I create content. What used to take me weeks now takes hours.",
                author: "Sarah J.",
                role: "Content Creator"
              },
              {
                text: "The ability to turn my textbooks into interactive lessons has engaged my students like never before.",
                author: "Prof. Michael R.",
                role: "Educator"
              },
              {
                text: "We use Litink for all our internal training videos. It's scalable, consistent, and incredibly cost-effective.",
                author: "Elena T.",
                role: "L&D Manager"
              }
            ].map((t, i) => (
              <div key={i} className="p-8 rounded-2xl bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/5 hover:border-purple-500/30 transition-all">
                <div className="flex gap-1 mb-4 text-yellow-400">
                  {[...Array(5)].map((_, j) => <Star key={j} className="w-4 h-4 fill-current" />)}
                </div>
                <p className="text-gray-700 dark:text-gray-300 mb-6 italic">"{t.text}"</p>
                <div>
                  <div className="font-bold">{t.author}</div>
                  <div className="text-purple-500 dark:text-purple-400 text-sm">{t.role}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24">
         <div className="container mx-auto px-4">
            <div className="relative rounded-3xl overflow-hidden p-12 text-center">
               <div className="absolute inset-0 bg-gradient-to-r from-purple-900 to-blue-900 z-0"></div>
               <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1550745165-9bc0b252726f?q=80&w=2070&auto=format&fit=crop')] opacity-20 bg-cover bg-center"></div>
               
               <div className="relative z-10 max-w-3xl mx-auto text-white">
                  <h2 className="text-4xl md:text-5xl font-bold mb-6">Ready to Start Creating?</h2>
                  <p className="text-xl text-gray-200 mb-10">
                     Join thousands of creators, educators, and businesses transforming their content with Litink AI.
                  </p>
                  <Link 
                     to="/auth"
                     className="inline-flex items-center gap-2 px-10 py-5 bg-white text-purple-900 rounded-full font-bold text-lg hover:bg-gray-100 transform hover:scale-105 transition-all shadow-xl"
                  >
                     Create Your First Video
                     <ArrowRight className="w-5 h-5" />
                  </Link>
               </div>
            </div>
         </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-white/10 bg-white dark:bg-[#050510] py-16 transition-colors duration-300">
         <div className="container mx-auto px-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
               <div>
                  <Link to="/" className="text-2xl font-bold mb-6 block">
                     <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">Litink.ai</span>
                  </Link>
                  <p className="text-gray-500 mb-6">
                     Empowering creators with AI to turn distinct ideas into visual reality instantly.
                  </p>
                  <div className="flex gap-4">
                     {[Twitter, Github, Linkedin].map((Icon, i) => (
                        <a key={i} href="#" className="w-10 h-10 rounded-full bg-gray-100 dark:bg-white/5 flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-purple-600 hover:text-white transition-all">
                           <Icon className="w-5 h-5" />
                        </a>
                     ))}
                  </div>
               </div>
               
               <div>
                  <h4 className="font-bold mb-6">Product</h4>
                  <ul className="space-y-4 text-gray-500 dark:text-gray-400">
                     <li><Link to="/features" className="hover:text-gray-900 dark:hover:text-white transition-colors">Features</Link></li>
                     <li><Link to="/subscription" className="hover:text-gray-900 dark:hover:text-white transition-colors">Pricing</Link></li>
                     <li><Link to="/showcase" className="hover:text-gray-900 dark:hover:text-white transition-colors">Showcase</Link></li>
                     <li><Link to="/roadmap" className="hover:text-gray-900 dark:hover:text-white transition-colors">Roadmap</Link></li>
                  </ul>
               </div>

               <div>
                   <h4 className="font-bold mb-6">Company</h4>
                  <ul className="space-y-4 text-gray-500 dark:text-gray-400">
                     <li><Link to="/about" className="hover:text-gray-900 dark:hover:text-white transition-colors">About Us</Link></li>
                     <li><Link to="/blog" className="hover:text-gray-900 dark:hover:text-white transition-colors">Blog</Link></li>
                     <li><Link to="/careers" className="hover:text-gray-900 dark:hover:text-white transition-colors">Careers</Link></li>
                     <li><Link to="/contact" className="hover:text-gray-900 dark:hover:text-white transition-colors">Contact</Link></li>
                  </ul>
               </div>

               <div>
                   <h4 className="font-bold mb-6">Legal</h4>
                  <ul className="space-y-4 text-gray-500 dark:text-gray-400">
                     <li><Link to="/privacy" className="hover:text-gray-900 dark:hover:text-white transition-colors">Privacy Policy</Link></li>
                     <li><Link to="/terms" className="hover:text-gray-900 dark:hover:text-white transition-colors">Terms of Service</Link></li>
                     <li><Link to="/cookies" className="hover:text-gray-900 dark:hover:text-white transition-colors">Cookie Policy</Link></li>
                  </ul>
               </div>
            </div>
            
            <div className="border-t border-gray-200 dark:border-white/5 pt-8 text-center text-gray-500 dark:text-gray-600 text-sm">
               © 2025 Litink AI. All rights reserved.
            </div>
         </div>
      </footer>

      {/* Video Modal */}
      {isVideoOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md p-4 animate-fade-in">
          <div className="relative w-full max-w-5xl aspect-video bg-black rounded-2xl overflow-hidden shadow-2xl border border-white/10">
            <button 
              onClick={() => setIsVideoOpen(false)}
              className="absolute top-4 right-4 z-50 p-2 bg-black/50 hover:bg-white/20 text-white rounded-full transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
            
            {/* Cinematic Simulation */}
            <div className="w-full h-full relative overflow-hidden group">
               <img 
                src="/images/hero-1.png" 
                alt="Cinematic Preview" 
                className="w-full h-full object-cover animate-pan-zoom"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/40"></div>
              
              <div className="absolute bottom-10 left-10 right-10">
                 <div className="space-y-2">
                    <div className="inline-block px-3 py-1 bg-red-600 text-white text-xs font-bold rounded uppercase tracking-wider mb-2 animate-pulse">
                       Live Preview
                    </div>
                    <h3 className="text-3xl font-bold text-white mb-2 drop-shadow-lg">The Future of Storytelling</h3>
                    <p className="text-gray-200 text-lg max-w-2xl drop-shadow-md">
                       Experience your stories like never before. AI-generated visuals, voices, and emotions combined into one seamless cinematic journey.
                    </p>
                 </div>
              </div>

              {/* Progress Bar Simulation */}
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-800">
                 <div className="h-full bg-red-600 w-1/3 animate-progress"></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Icon for Business Use Case
function BriefcaseIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      <rect width="20" height="14" x="2" y="6" rx="2" />
    </svg>
  );
}
