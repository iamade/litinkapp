import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { apiClient } from "../lib/api";
import { toast } from "react-hot-toast";
import { User, Shield } from "lucide-react";

// Step 1: Personal Info
const Step1 = ({ data, updateData }: { data: any; updateData: (d: any) => void }) => {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold dark:text-white">Let's get to know you</h2>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">First Name</label>
          <input
            type="text"
            required
            value={data.firstName || ""}
            onChange={(e) => updateData({ firstName: e.target.value })}
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Last Name</label>
          <input
            type="text"
            required
            value={data.lastName || ""}
            onChange={(e) => updateData({ lastName: e.target.value })}
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Username</label>
        <input
          type="text"
          required
          value={data.username || ""}
          onChange={(e) => updateData({ username: e.target.value })}
          className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Security Question</label>
        <select
          required
          value={data.securityQuestion || ""}
          onChange={(e) => updateData({ securityQuestion: e.target.value })}
          className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="">Select Question</option>
          <option value="mother_maiden_name">Mother's maiden name?</option>
          <option value="childhood_friend">Childhood friend's name?</option>
          <option value="favorite_color">Favorite color?</option>
          <option value="birth_city">Birth city?</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Security Answer</label>
        <input
          type="text"
          required
          value={data.securityAnswer || ""}
          onChange={(e) => updateData({ securityAnswer: e.target.value })}
          className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
      </div>
       <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Profile Type</label>
        <div className="mt-2 flex gap-4">
             <div
                className="flex-1 py-3 px-4 rounded-xl border-2 border-gray-200 dark:border-gray-700 opacity-60 cursor-not-allowed relative overflow-hidden"
            >
                <div className="absolute top-1 right-1 bg-purple-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                  Coming Soon
                </div>
                <div className="font-semibold dark:text-white">Explorer</div>
                <div className="text-xs text-gray-500">I want to discover and watch content</div>
             </div>
             <button
                type="button"
                onClick={() => updateData({ primaryRole: "creator" })}
                className={`flex-1 py-3 px-4 rounded-xl border-2 transition-all ${data.primaryRole === 'creator' ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/20' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'}`}
            >    
                <div className="font-semibold dark:text-white">Author/Creator</div>
                <div className="text-xs text-gray-500">I want to create and publish content</div>
            </button>
        </div>
      </div>
    </div>
  );
};

// Step 2: Role Details (Only if creator is selected or generally asked?)
// Requirement: "Page 2 = What’s your role"
const Step2 = ({ data, updateData }: { data: any; updateData: (d: any) => void }) => {
     const roles = ["Writer", "Artist", "Filmmaker", "Animator", "Marketing", "Producer", "Other"];
     return(
        <div className="space-y-4">
             <h2 className="text-xl font-semibold dark:text-white">What's your specific role?</h2>
             <div className="grid grid-cols-2 gap-3">
                 {roles.map(role => (
                     <button
                        key={role}
                        type="button"
                        onClick={() => updateData({ professionalRole: role })}
                        className={`p-3 rounded-xl border text-left transition-all ${data.professionalRole === role ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-white' : 'border-gray-200 dark:border-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                     >
                         {role}
                     </button>
                 ))}
             </div>
        </div>
     )
}

// Step 3: Team Size
const Step3 = ({ data, updateData }: { data: any; updateData: (d: any) => void }) => {
    const sizes = ["Just me", "2-10", "11-50", "51-500", "501-2000", "2001-5000", "5000+"];
     return(
        <div className="space-y-4">
             <h2 className="text-xl font-semibold dark:text-white">How big is your team?</h2>
             <div className="grid grid-cols-1 gap-2">
                 {sizes.map(size => (
                     <button
                        key={size}
                        type="button"
                        onClick={() => updateData({ teamSize: size })}
                        className={`p-3 rounded-xl border text-left transition-all ${data.teamSize === size ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-white' : 'border-gray-200 dark:border-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                     >
                         {size}
                     </button>
                 ))}
             </div>
        </div>
     )
}

// Step 4: Discovery
const Step4 = ({ data, updateData }: { data: any; updateData: (d: any) => void }) => {
     const sources = ["IG", "X (Twitter)", "Youtube", "AI Communities", "Tiktok", "Friends", "ChatGPT", "Google search", "LinkedIn", "Other"];
     return(
        <div className="space-y-4">
             <h2 className="text-xl font-semibold dark:text-white">How did you discover us?</h2>
              <div className="grid grid-cols-2 gap-3">
                 {sources.map(source => (
                     <button
                        key={source}
                        type="button"
                        onClick={() => updateData({ discoverySource: source })}
                        className={`p-3 rounded-xl border text-left transition-all ${data.discoverySource === source ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-white' : 'border-gray-200 dark:border-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                     >
                         {source}
                     </button>
                 ))}
             </div>
        </div>
     )
}

// Step 5: Interests
const Step5 = ({ data, updateData }: { data: any; updateData: (d: any) => void }) => {
    const interests = ["Image creations", "Video creation", "Children stories", "Adverts", "Movies", "Animation", "Shorts", "Series"];
    
    const toggleInterest = (interest: string) => {
        const current = data.interests || [];
        if (current.includes(interest)) {
            updateData({ interests: current.filter((i: string) => i !== interest) });
        } else {
             updateData({ interests: [...current, interest] });
        }
    };

     return(
        <div className="space-y-4">
             <h2 className="text-xl font-semibold dark:text-white">What do you want to create?</h2>
              <div className="grid grid-cols-2 gap-3">
                 {interests.map(interest => (
                     <button
                        key={interest}
                        type="button"
                        onClick={() => toggleInterest(interest)}
                        className={`p-3 rounded-xl border text-left transition-all ${data.interests?.includes(interest) ? 'border-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-white' : 'border-gray-200 dark:border-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                     >
                         {interest}
                     </button>
                 ))}
             </div>
        </div>
     )
}


export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
      firstName: "",
      lastName: "",
      username: "",
      securityQuestion: "",
      securityAnswer: "",
      primaryRole: "creator", // Default
      professionalRole: "",
      teamSize: "",
      discoverySource: "",
      interests: [] as string[]
  });
  const [loading, setLoading] = useState(false);
  const { user } = useAuth();
  const navigate = useNavigate();

  // If user already has name/username (e.g. from social login if we supported it fully, or previously filled), we could skip step 1.
  // But per req, if signing up via email/pass, they come here. If via social, skip step 1.
  // We can infer social login if user.display_name is set or we can check a flag. 
  // For now, let's just show Step 1 if names are missing.
  
  React.useEffect(() => {
     if(user) {
         // Check if basic info is present to potentially skip step 1
         const hasBasicInfo = user.display_name && (user as any).first_name && (user as any).last_name;
         if (hasBasicInfo && step === 1) {
             setStep(2);
         }
         
         // Pre-fill
        setFormData(prev => ({
            ...prev,
            firstName: (user as any).first_name || "",
            lastName: (user as any).last_name || "",
            username: user.display_name || "",
        }));
     }
  }, [user]);


  const updateData = (newData: any) => {
    setFormData((prev) => ({ ...prev, ...newData }));
  };

  const handleNext = () => {
      // Validation for Step 1
      if (step === 1) {
           if (!formData.firstName || !formData.lastName || !formData.username || !formData.securityQuestion || !formData.securityAnswer) {
               toast.error("Please fill in all required fields");
               return;
           }
      }
      setStep(prev => prev + 1);
  };
  
  const handleBack = () => {
      setStep(prev => prev - 1);
  };

  const handleSubmit = async () => {
      setLoading(true);
      try {
          // Send to backend
          // We need a new endpoint for this: POST /api/v1/user/onboarding
          await apiClient.post("/users/me/onboarding", formData);
          
          toast.success("Profile setup complete!");
          
          // Route based on user's selected role
          const destination = formData.primaryRole === "creator" ? "/creator" : "/dashboard";
          navigate(destination);
          window.location.reload(); // Refresh to update user context with new roles/status
      } catch (error) {
          console.error(error);
          toast.error("Failed to save profile details");
      } finally {
          setLoading(false);
      }
  };


  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-[#0F0F23] p-4">
      <div className="w-full max-w-lg bg-white dark:bg-[#13132B] rounded-3xl shadow-2xl p-8 border border-gray-200 dark:border-white/5">
        <div className="mb-8">
            <div className="flex gap-2 mb-4">
                {[1, 2, 3, 4, 5].map(s => (
                    <div key={s} className={`h-1.5 flex-1 rounded-full ${s <= step ? 'bg-purple-600' : 'bg-gray-200 dark:bg-gray-700'}`} />
                ))}
            </div>
        </div>

        {step === 1 && <Step1 data={formData} updateData={updateData} />}
        {step === 2 && <Step2 data={formData} updateData={updateData} />}
        {step === 3 && <Step3 data={formData} updateData={updateData} />}
        {step === 4 && <Step4 data={formData} updateData={updateData} />}
        {step === 5 && <Step5 data={formData} updateData={updateData} />}

        <div className="mt-8 flex justify-between">
           {step > 1 && (
             <button
                onClick={handleBack}
                className="px-6 py-2.5 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors font-medium text-sm"
             >
                 Back
             </button>
           )}
           
           {step < 5 ? (
               <button
                  onClick={handleNext}
                  className="ml-auto px-8 py-2.5 bg-[#635BFF] hover:bg-[#5B36F5] text-white rounded-xl font-bold shadow-lg shadow-purple-900/20 transition-all text-sm"
               >
                   Next
               </button>
           ) : (
                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="ml-auto px-8 py-2.5 bg-[#635BFF] hover:bg-[#5B36F5] text-white rounded-xl font-bold shadow-lg shadow-purple-900/20 transition-all text-sm disabled:opacity-50"
               >
                   {loading ? "Completing..." : "Complete Setup"}
               </button>
           )}
        </div>
      </div>
    </div>
  );
}
