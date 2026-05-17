import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  AudioLines,
  Brain,
  Clapperboard,
  Film,
  Github,
  Image,
  Linkedin,
  PenLine,
  Sparkles,
  Twitter,
  Video
} from "lucide-react";

const features = [
  {
    title: "Script Generation",
    desc: "Transform prompts, chapters, or rough ideas into structured cinematic scripts with scenes, characters, and dialogue.",
    icon: PenLine
  },
  {
    title: "Image Generation",
    desc: "Create story-aligned visuals, characters, continuity frames, and concept art from the same narrative workspace.",
    icon: Image
  },
  {
    title: "Audio Generation",
    desc: "Produce narration, character dialogue, and immersive audio assets with AI-powered voice workflows.",
    icon: AudioLines
  },
  {
    title: "Video Generation",
    desc: "Move from scene plans to AI-generated clips with tools built for story structure and visual consistency.",
    icon: Video
  },
  {
    title: "Merge Studio",
    desc: "Assemble generated scripts, images, audio, and video into polished story experiences from one production hub.",
    icon: Clapperboard
  }
];

const workflow = [
  "Start with a prompt, book excerpt, script, or story idea.",
  "Let LitInkAI structure scenes, visuals, voice, and production assets.",
  "Review, refine, merge, and publish your AI-powered story."
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950 transition-colors duration-300 dark:bg-[#080817] dark:text-white">
      <main>
        <section className="relative overflow-hidden px-4 pb-20 pt-28 sm:px-6 lg:px-8 lg:pb-28 lg:pt-36">
          <div className="absolute inset-0 -z-10">
            <div className="absolute left-1/2 top-0 h-[28rem] w-[28rem] -translate-x-1/2 rounded-full bg-purple-500/20 blur-3xl dark:bg-purple-500/25" />
            <div className="absolute right-0 top-32 h-80 w-80 rounded-full bg-cyan-400/20 blur-3xl dark:bg-cyan-400/20" />
            <div className="absolute bottom-0 left-0 h-72 w-72 rounded-full bg-fuchsia-400/20 blur-3xl dark:bg-fuchsia-500/20" />
          </div>

          <div className="mx-auto grid max-w-7xl items-center gap-14 lg:grid-cols-[1.05fr_0.95fr]">
            <div>
              <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-purple-200 bg-white/80 px-4 py-2 text-sm font-semibold text-purple-700 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/5 dark:text-purple-200">
                <Sparkles className="h-4 w-4" />
                AI-powered storytelling studio
              </div>

              <h1 className="max-w-4xl text-5xl font-black tracking-tight text-slate-950 dark:text-white sm:text-6xl lg:text-7xl">
                Turn every story into a cinematic AI production.
              </h1>

              <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-600 dark:text-slate-300 sm:text-xl">
                LitInkAI helps creators generate scripts, images, audio, video, and merged story experiences from one modern production workflow — built for faster, richer storytelling.
              </p>

              <div className="mt-10 flex flex-col gap-4 sm:flex-row">
                <Link
                  to="/auth"
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 px-8 py-4 text-base font-bold text-white shadow-lg shadow-purple-500/25 transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-purple-500/30"
                >
                  Start Creating Free
                  <ArrowRight className="h-5 w-5" />
                </Link>
                <Link
                  to="/subscription"
                  className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white/80 px-8 py-4 text-base font-bold text-slate-900 transition hover:border-purple-300 hover:text-purple-700 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
                >
                  Explore Plans
                </Link>
              </div>
            </div>

            <div className="relative">
              <div className="absolute -inset-4 rounded-[2rem] bg-gradient-to-br from-purple-500/30 via-blue-500/20 to-cyan-400/30 blur-2xl" />
              <div className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white p-5 shadow-2xl dark:border-white/10 dark:bg-white/5">
                <div className="rounded-3xl bg-slate-950 p-5 text-white">
                  <div className="mb-5 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-red-400" />
                      <span className="h-3 w-3 rounded-full bg-yellow-400" />
                      <span className="h-3 w-3 rounded-full bg-green-400" />
                    </div>
                    <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-300">Live generation</span>
                  </div>
                  <div className="space-y-4">
                    <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                      <div className="mb-3 flex items-center gap-3">
                        <Brain className="h-5 w-5 text-purple-300" />
                        <span className="text-sm font-semibold text-purple-100">Story intelligence</span>
                      </div>
                      <p className="text-2xl font-bold">Scene 04: The Neon Archive</p>
                      <p className="mt-2 text-sm leading-6 text-slate-300">Generating storyboard frames, character voice lines, and cinematic shot prompts.</p>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        ["Script", "Ready"],
                        ["Images", "12 frames"],
                        ["Audio", "Mixing"],
                        ["Video", "Queued"]
                      ].map(([label, value]) => (
                        <div key={label} className="rounded-2xl bg-white/10 p-4">
                          <p className="text-xs uppercase tracking-widest text-slate-400">{label}</p>
                          <p className="mt-2 font-bold text-white">{value}</p>
                        </div>
                      ))}
                    </div>
                    <div className="rounded-2xl bg-gradient-to-r from-purple-500 to-blue-500 p-4">
                      <div className="flex items-center gap-3">
                        <Film className="h-6 w-6" />
                        <div>
                          <p className="font-bold">Merge Studio timeline</p>
                          <p className="text-sm text-purple-100">Combining assets into a polished story sequence.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-slate-200 bg-white px-4 py-20 dark:border-white/10 dark:bg-[#0d0d24] sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <div className="mx-auto max-w-3xl text-center">
              <p className="text-sm font-bold uppercase tracking-[0.3em] text-purple-600 dark:text-purple-300">One platform, every asset</p>
              <h2 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">Create the full story pipeline with AI</h2>
              <p className="mt-5 text-lg leading-8 text-slate-600 dark:text-slate-300">
                LitInkAI brings the core creative modules into a single workflow so teams can move from idea to multimedia story without stitching tools together manually.
              </p>
            </div>

            <div className="mt-14 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {features.map((feature) => {
                const Icon = feature.icon;
                return (
                  <div key={feature.title} className="group rounded-3xl border border-slate-200 bg-slate-50 p-6 transition hover:-translate-y-1 hover:border-purple-300 hover:shadow-xl dark:border-white/10 dark:bg-white/5 dark:hover:border-purple-400/50">
                    <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-600 to-blue-600 text-white shadow-lg shadow-purple-500/20">
                      <Icon className="h-6 w-6" />
                    </div>
                    <h3 className="text-xl font-bold">{feature.title}</h3>
                    <p className="mt-3 leading-7 text-slate-600 dark:text-slate-300">{feature.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="px-4 py-20 sm:px-6 lg:px-8">
          <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.3em] text-blue-600 dark:text-blue-300">Built for production</p>
              <h2 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">From blank page to finished sequence.</h2>
              <p className="mt-5 text-lg leading-8 text-slate-600 dark:text-slate-300">
                Whether you are drafting a short film, adapting a chapter, or building episodic content, LitInkAI keeps narrative context connected across every generated asset.
              </p>
            </div>
            <div className="grid gap-4">
              {workflow.map((item, index) => (
                <div key={item} className="flex gap-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-white/5">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-sm font-black text-white dark:bg-white dark:text-slate-950">
                    {index + 1}
                  </span>
                  <p className="text-lg font-semibold leading-7 text-slate-800 dark:text-slate-100">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="px-4 pb-24 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl overflow-hidden rounded-[2rem] bg-gradient-to-r from-purple-600 via-blue-600 to-cyan-500 p-10 text-center text-white shadow-2xl shadow-purple-500/20 sm:p-14">
            <Sparkles className="mx-auto h-10 w-10" />
            <h2 className="mt-5 text-4xl font-black tracking-tight sm:text-5xl">Ready to create your next AI-powered story?</h2>
            <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-purple-50">
              Start with a prompt, script, or idea. LitInkAI helps you generate the assets and assemble the experience.
            </p>
            <Link
              to="/auth"
              className="mt-8 inline-flex items-center justify-center gap-2 rounded-full bg-white px-8 py-4 text-base font-black text-purple-700 transition hover:-translate-y-0.5 hover:shadow-xl"
            >
              Sign Up and Start Creating
              <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white px-4 py-12 dark:border-white/10 dark:bg-[#080817] sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-10 md:grid-cols-4">
            <div className="md:col-span-2">
              <Link to="/" className="inline-flex items-center gap-2 text-2xl font-black">
                <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-600 to-blue-600 text-white">L</span>
                LitInkAI
              </Link>
              <p className="mt-4 max-w-md text-slate-600 dark:text-slate-400">
                AI-powered storytelling tools for creators building scripts, visuals, voices, video, and merged cinematic experiences.
              </p>
              <div className="mt-6 flex gap-3 text-slate-500 dark:text-slate-400">
                <a href="https://twitter.com" aria-label="Twitter" className="rounded-full border border-slate-200 p-2 transition hover:text-purple-600 dark:border-white/10 dark:hover:text-white"><Twitter className="h-5 w-5" /></a>
                <a href="https://github.com" aria-label="GitHub" className="rounded-full border border-slate-200 p-2 transition hover:text-purple-600 dark:border-white/10 dark:hover:text-white"><Github className="h-5 w-5" /></a>
                <a href="https://linkedin.com" aria-label="LinkedIn" className="rounded-full border border-slate-200 p-2 transition hover:text-purple-600 dark:border-white/10 dark:hover:text-white"><Linkedin className="h-5 w-5" /></a>
              </div>
            </div>

            <div>
              <h4 className="font-bold">Company</h4>
              <ul className="mt-5 space-y-3 text-slate-600 dark:text-slate-400">
                <li><Link to="/about" className="transition hover:text-slate-950 dark:hover:text-white">About</Link></li>
                <li><Link to="/blog" className="transition hover:text-slate-950 dark:hover:text-white">Blog</Link></li>
                <li><Link to="/careers" className="transition hover:text-slate-950 dark:hover:text-white">Careers</Link></li>
                <li><Link to="/contact" className="transition hover:text-slate-950 dark:hover:text-white">Contact</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold">Legal</h4>
              <ul className="mt-5 space-y-3 text-slate-600 dark:text-slate-400">
                <li><Link to="/privacy" className="transition hover:text-slate-950 dark:hover:text-white">Privacy Policy</Link></li>
                <li><Link to="/terms" className="transition hover:text-slate-950 dark:hover:text-white">Terms of Service</Link></li>
                <li><Link to="/cookies" className="transition hover:text-slate-950 dark:hover:text-white">Cookie Policy</Link></li>
              </ul>
            </div>
          </div>

          <div className="mt-10 border-t border-slate-200 pt-8 text-center text-sm text-slate-500 dark:border-white/10 dark:text-slate-500">
            © 2025 LitInkAI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
