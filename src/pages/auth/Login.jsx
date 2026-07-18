import React, { useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { Phone, Lock, LogIn, AlertCircle, User, MapPin } from "lucide-react";

const translations = {
  en: {
    title: "ArtisanEdge",
    tagline: "Weaver Income Stability & Demand Forecasting",
    loginHeader: "Artisan Sign In",
    signUpHeader: "Create Weaver Account",
    phoneLabel: "Phone Number",
    phonePlaceholder: "Enter 10-digit mobile number",
    passwordLabel: "Password",
    passwordPlaceholder: "Enter password (min 6 chars)",
    nameLabel: "Full Name",
    namePlaceholder: "Enter your full name",
    locationLabel: "Location / Craft Cluster",
    locationPlaceholder: "e.g., Kanchipuram",
    loginBtn: "Sign In",
    loginLoading: "Signing In...",
    signUpBtn: "Sign Up",
    signUpLoading: "Creating Account...",
    toggleSignUp: "Don't have an account? Sign Up",
    toggleSignIn: "Already have an account? Sign In",
    validationPhone: "Please enter a valid 10-digit phone number.",
    validationPassword: "Password must be at least 6 characters.",
    validationName: "Please enter your full name (min 2 characters).",
    validationLocation: "Please enter your location / craft cluster.",
  },
  hi: {
    title: "ArtisanEdge",
    tagline: "बुनकर आय स्थिरता और मांग पूर्वानुमान",
    loginHeader: "कारीगर साइन इन",
    signUpHeader: "बुनकर खाता बनाएं",
    phoneLabel: "फ़ोन नंबर",
    phonePlaceholder: "10-अंकों का मोबाइल नंबर दर्ज करें",
    passwordLabel: "पासवर्ड",
    passwordPlaceholder: "पासवर्ड दर्ज करें (न्यूनतम 6 अंक)",
    nameLabel: "पूरा नाम",
    namePlaceholder: "अपना पूरा नाम दर्ज करें",
    locationLabel: "स्थान / शिल्प क्लस्टर",
    locationPlaceholder: "उदा. कांचीपुरम",
    loginBtn: "साइन इन करें",
    loginLoading: "साइन इन हो रहा है...",
    signUpBtn: "साइन अप करें",
    signUpLoading: "खाता बनाया जा रहा है...",
    toggleSignUp: "खाता नहीं है? साइन अप करें",
    toggleSignIn: "पहले से खाता है? साइन इन करें",
    validationPhone: "कृपया 10-अंकों का वैध फ़ोन नंबर दर्ज करें।",
    validationPassword: "पासवर्ड कम से कम 6 अक्षरों का होना चाहिए।",
    validationName: "कृपया अपना पूरा नाम दर्ज करें (न्यूनतम 2 अक्षर)।",
    validationLocation: "कृपया अपना स्थान / शिल्प क्लस्टर दर्ज करें।",
  },
};

export default function Login() {
  const { login, register, language, updateLanguage, error: authError, clearError } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [location, setLocation] = useState("");
  const [loading, setLoading] = useState(false);
  const [valError, setValError] = useState(null);

  const t = translations[language] || translations.en;

  // Clear errors on mount
  React.useEffect(() => {
    if (clearError) clearError();
    setValError(null);
  }, []);

  // Clear validation and context errors when user types or toggles mode
  React.useEffect(() => {
    setValError(null);
    if (clearError) clearError();
  }, [phoneNumber, password, fullName, location, isSignUp]);

  const toggleMode = () => {
    setIsSignUp(!isSignUp);
    setPhoneNumber("");
    setPassword("");
    setFullName("");
    setLocation("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValError(null);

    // Simple validation
    const cleanPhone = phoneNumber.replace(/\D/g, "");
    if (cleanPhone.length !== 10) {
      setValError(t.validationPhone);
      return;
    }
    if (password.length < 6) {
      setValError(t.validationPassword);
      return;
    }

    if (isSignUp) {
      if (fullName.trim().length < 2) {
        setValError(t.validationName);
        return;
      }
      if (location.trim().length < 2) {
        setValError(t.validationLocation);
        return;
      }
    }

    setLoading(true);
    try {
      if (isSignUp) {
        // Register weaver account
        await register({
          phone_number: cleanPhone,
          full_name: fullName,
          password: password,
          region: location,
          role: "weaver",
        });
      }
      // Log in
      await login(cleanPhone, password);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLaunchDemo = async () => {
    setLoading(true);
    setValError(null);
    if (clearError) clearError();

    const demoPhone = "9999999999";
    const demoPassword = "demopassword123";
    const demoName = "DemoArtisan";
    const demoLocation = "Kanchipuram";

    setPhoneNumber(demoPhone);
    setPassword(demoPassword);
    setFullName(demoName);
    setLocation(demoLocation);

    try {
      try {
        await register({
          phone_number: demoPhone,
          full_name: demoName,
          password: demoPassword,
          region: demoLocation,
          role: "weaver",
        });
      } catch (regErr) {
        console.log("Demo registration already exists, logging in directly...");
      }
      await login(demoPhone, demoPassword);
    } catch (err) {
      console.error(err);
      setValError(err.message || "Failed to launch Demo Mode");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 rounded-full bg-amber-500/10 blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 rounded-full bg-purple-500/10 blur-3xl pointer-events-none"></div>

      {/* Main Container */}
      <div className="max-w-md w-full relative z-10 space-y-6">
        
        {/* Language Switcher */}
        <div className="flex justify-end space-x-2">
          <button
            onClick={() => updateLanguage("en")}
            className={`px-3 py-1 text-xs font-semibold rounded-full transition-all duration-200 ${
              language === "en"
                ? "bg-amber-400 text-slate-950 shadow-md shadow-amber-400/20"
                : "bg-white/5 text-slate-400 hover:bg-white/10"
            }`}
          >
            English
          </button>
          <button
            onClick={() => updateLanguage("hi")}
            className={`px-3 py-1 text-xs font-semibold rounded-full transition-all duration-200 ${
              language === "hi"
                ? "bg-amber-400 text-slate-950 shadow-md shadow-amber-400/20"
                : "bg-white/5 text-slate-400 hover:bg-white/10"
            }`}
          >
            हिंदी
          </button>
        </div>

        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg shadow-amber-400/35 mb-2 animate-bounce-slow">
            <span className="text-3xl">🧵</span>
          </div>
          <h1 className="text-4xl font-extrabold bg-gradient-to-r from-amber-200 via-yellow-300 to-orange-400 bg-clip-text text-transparent tracking-tight">
            {t.title}
          </h1>
          <p className="text-sm text-slate-400 max-w-xs mx-auto">
            {t.tagline}
          </p>
        </div>

        {/* Glass Card */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-8 backdrop-blur-md shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-400 via-orange-500 to-purple-600"></div>

          <h2 className="text-xl font-bold text-white mb-6 text-center tracking-wide">
            {isSignUp ? t.signUpHeader : t.loginHeader}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Errors */}
            {(valError || authError) && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-start gap-2.5 text-xs text-red-400 animate-shake">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{valError || authError}</span>
              </div>
            )}

            {/* Name Input (Sign Up Only) */}
            {isSignUp && (
              <div className="space-y-1.5 animate-slideDown">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  {t.nameLabel}
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder={t.namePlaceholder}
                    className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-11 pr-4 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition-all duration-200"
                  />
                </div>
              </div>
            )}

            {/* Phone Input */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                {t.phoneLabel}
              </label>
              <div className="relative">
                <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type="text"
                  maxLength={15}
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder={t.phonePlaceholder}
                  className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-11 pr-4 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition-all duration-200"
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                {t.passwordLabel}
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t.passwordPlaceholder}
                  className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-11 pr-4 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition-all duration-200"
                />
              </div>
            </div>

            {/* Location Input (Sign Up Only) */}
            {isSignUp && (
              <div className="space-y-1.5 animate-slideDown">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  {t.locationLabel}
                </label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder={t.locationPlaceholder}
                    className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-11 pr-4 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition-all duration-200"
                  />
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-300 hover:to-orange-400 text-slate-950 font-bold py-3 px-4 rounded-xl shadow-lg shadow-amber-500/20 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 text-sm cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <span>{isSignUp ? t.signUpLoading : t.loginLoading}</span>
              ) : (
                <>
                  <span>{isSignUp ? t.signUpBtn : t.loginBtn}</span>
                  <LogIn className="w-4 h-4" />
                </>
              )}
            </button>

            {/* Launch Demo button */}
            <button
              type="button"
              disabled={loading}
              onClick={handleLaunchDemo}
              className="w-full bg-white/5 border border-purple-500/30 hover:border-purple-400/50 hover:bg-white/10 text-purple-300 font-semibold py-3 px-4 rounded-xl active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 text-sm cursor-pointer disabled:opacity-50"
            >
              <span>⚡ Launch Live Demo</span>
            </button>
          </form>

          {/* Toggle mode link */}
          <div className="mt-6 text-center">
            <button
              onClick={toggleMode}
              className="text-xs text-amber-400 hover:text-amber-300 font-semibold transition-colors duration-150 cursor-pointer"
            >
              {isSignUp ? t.toggleSignIn : t.toggleSignUp}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
