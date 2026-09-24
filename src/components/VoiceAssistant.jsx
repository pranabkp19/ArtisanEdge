import React, { useState, useEffect, useRef } from "react";
import { Mic, MicOff, Volume2, VolumeX, X, MessageSquare, Sparkles, Languages } from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import "./VoiceAssistant.css";

export default function VoiceAssistant() {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [language, setLanguage] = useState("en"); // "en" or "hi"
  const [isListening, setIsListening] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [speechEnabled, setSpeechEnabled] = useState(true);
  const [statusMessage, setStatusMessage] = useState("");

  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);

  // Recommended Quick Commands
  const quickCommands = [
    { en: "Say Hello", hi: "नमस्ते कहें" },
    { en: "Check Credit Score", hi: "क्रेडिट स्कोर देखें" },
    { en: "Inventory Details", hi: "इन्वेंट्री विवरण" },
    { en: "Total Transactions", hi: "कुल लेनदेन" },
    { en: "Paid Transactions", hi: "भुगतान किए गए लेनदेन" },
    { en: "Overdue Transactions", hi: "समय सीमा पार लेनदेन" },
    { en: "Pending Transactions", hi: "लंबित लेनदेन" },
    { en: "Eligible Schemes", hi: "पात्र योजनाएं" }
  ];

  // Initialize Speech Recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = language === "hi" ? "hi-IN" : "en-US";

      rec.onstart = () => {
        setIsListening(true);
        setStatusMessage(language === "hi" ? "सुन रहा हूँ..." : "Listening...");
      };

      rec.onend = () => {
        setIsListening(false);
      };

      rec.onerror = (e) => {
        console.error("Speech Recognition Error:", e);
        setIsListening(false);
        setStatusMessage(
          language === "hi" 
            ? "आवाज़ पहचानने में त्रुटि हुई।" 
            : "Speech recognition error."
        );
      };

      rec.onresult = async (event) => {
        const text = event.results[0][0].transcript;
        if (text.strip?.() === "" || text === "") return;
        
        setStatusMessage("");
        const userMsg = { sender: "user", text };
        setChatHistory(prev => [...prev, userMsg]);

        try {
          setStatusMessage(language === "hi" ? "सोच रहा हूँ..." : "Thinking...");
          const res = await api.post("/chatbot/ask", {
            question: text,
            language: language
          });
          
          setStatusMessage("");
          const aiMsg = { sender: "ai", text: res.answer };
          setChatHistory(prev => [...prev, aiMsg]);

          if (speechEnabled) {
            speakText(res.answer);
          }
        } catch (err) {
          console.error("Failed to ask chatbot:", err);
          const errMsg = language === "hi" 
            ? "क्षमा करें, मैं अभी जवाब देने में असमर्थ हूँ।" 
            : "Sorry, I am unable to reply at the moment.";
          setChatHistory(prev => [...prev, { sender: "ai", text: errMsg }]);
          setStatusMessage("");
        }
      };

      recognitionRef.current = rec;
    } else {
      console.warn("Web Speech API is not supported in this browser.");
    }
  }, [language, speechEnabled]);

  // Adjust SpeechRecognition language whenever toggle switches
  useEffect(() => {
    if (recognitionRef.current) {
      recognitionRef.current.lang = language === "hi" ? "hi-IN" : "en-US";
    }
  }, [language]);

  // Auto-scroll chat history
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, statusMessage]);

  // Speak response aloud using native SpeechSynthesis
  const speakText = (text) => {
    if (!synthRef.current) return;
    
    synthRef.current.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language === "hi" ? "hi-IN" : "en-US";
    
    const voices = synthRef.current.getVoices();
    const matchingVoice = voices.find(v => v.lang.startsWith(language));
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    synthRef.current.speak(utterance);
  };

  // Handle Quick Command Chip Clicks
  const handleCommandClick = async (commandText) => {
    if (synthRef.current) synthRef.current.cancel();
    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
    }

    setChatHistory(prev => [...prev, { sender: "user", text: commandText }]);

    try {
      setStatusMessage(language === "hi" ? "सोच रहा हूँ..." : "Thinking...");
      const res = await api.post("/chatbot/ask", {
        question: commandText,
        language: language
      });
      
      setStatusMessage("");
      setChatHistory(prev => [...prev, { sender: "ai", text: res.answer }]);

      if (speechEnabled) {
        speakText(res.answer);
      }
    } catch (err) {
      console.error("Quick command execution failed:", err);
      const errMsg = language === "hi" 
        ? "क्षमा करें, मैं अभी विवरण प्राप्त करने में असमर्थ हूँ।" 
        : "Sorry, I am unable to fetch details at the moment.";
      setChatHistory(prev => [...prev, { sender: "ai", text: errMsg }]);
      setStatusMessage("");
    }
  };

  // Toggle listening state
  const handleMicClick = () => {
    if (!recognitionRef.current) {
      alert("Voice recognition is not supported or initialized in your browser.");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      if (synthRef.current) {
        synthRef.current.cancel();
      }
      recognitionRef.current.start();
    }
  };

  return (
    <>
      {/* Floating Action Button (FAB) - Claymorphism style */}
      <button
        id="voice-assistant-fab"
        onClick={() => setIsOpen(true)}
        style={{
          background: "rgba(15, 23, 42, 0.9)",
          borderRadius: "9999px",
          boxShadow: "inset 4px 4px 8px rgba(255,255,255,0.06), inset -4px -4px 8px rgba(0,0,0,0.6), 0 8px 32px rgba(16,185,129,0.15)",
          border: "1px solid rgba(16,185,129,0.3)"
        }}
        className="fixed bottom-6 right-6 w-14 h-14 flex items-center justify-center text-emerald-400 hover:text-emerald-300 hover:scale-105 active:scale-95 transition-all duration-300 cursor-pointer z-[999] hover:shadow-[0_0_25px_rgba(16,185,129,0.5)] animate-bounce"
        title="Voice Assistant"
      >
        <Mic className="w-6 h-6 animate-pulse" />
      </button>

      {/* Drawer Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[998] transition-opacity duration-300"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Slide-out Drawer Panel - Glassmorphism theme */}
      <div
        style={{
          background: "rgba(10, 15, 30, 0.75)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderLeft: "1px solid rgba(255, 255, 255, 0.1)",
          boxShadow: "-8px 0 32px rgba(0, 0, 0, 0.5)",
          transform: isOpen ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
        }}
        className="fixed top-0 right-0 h-full w-full sm:w-[420px] flex flex-col z-[1000] overflow-hidden"
      >
        {/* Drawer Header */}
        <div className="p-5 border-b border-white/5 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              {language === "hi" ? "सहायक एआई" : "Artisan Voice Assistant"}
            </h3>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Audio Toggle */}
            <button
              onClick={() => {
                setSpeechEnabled(!speechEnabled);
                if (synthRef.current) synthRef.current.cancel();
              }}
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white cursor-pointer transition-colors"
              title={speechEnabled ? "Mute Speech" : "Unmute Speech"}
            >
              {speechEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>

            {/* Language Switch Toggle */}
            <div className="flex items-center bg-white/5 p-0.5 rounded-lg border border-white/5">
              <button
                onClick={() => setLanguage("en")}
                className={`px-2.5 py-1 text-[10px] font-bold rounded-md transition-all cursor-pointer ${
                  language === "en" ? "bg-emerald-500 text-slate-950" : "text-slate-400 hover:text-white"
                }`}
              >
                EN
              </button>
              <button
                onClick={() => setLanguage("hi")}
                className={`px-2.5 py-1 text-[10px] font-bold rounded-md transition-all cursor-pointer ${
                  language === "hi" ? "bg-emerald-500 text-slate-950" : "text-slate-400 hover:text-white"
                }`}
              >
                हिन्दी
              </button>
            </div>

            {/* Close Drawer Button */}
            <button
              onClick={() => {
                setIsOpen(false);
                if (synthRef.current) synthRef.current.cancel();
                if (recognitionRef.current) recognitionRef.current.stop();
              }}
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white cursor-pointer transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Quick Commands Recommendation Section */}
        <div className="px-5 py-3 border-b border-white/5 bg-slate-950/20 flex-shrink-0">
          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest block mb-2">
            {language === "hi" ? "त्वरित कमांड" : "Quick Commands"}
          </span>
          <div className="flex flex-wrap gap-1.5 max-h-[75px] overflow-y-auto pr-1 select-none">
            {quickCommands.map((cmd, idx) => {
              const label = language === "hi" ? cmd.hi : cmd.en;
              return (
                <button
                  key={idx}
                  onClick={() => handleCommandClick(label)}
                  style={{
                    background: "rgba(30, 41, 59, 0.4)",
                    border: "1px solid rgba(255, 255, 255, 0.05)",
                    borderRadius: "20px",
                    boxShadow: "inset 1px 1px 2px rgba(255, 255, 255, 0.05), 0 2px 4px rgba(0, 0, 0, 0.15)"
                  }}
                  className="quick-command-chip px-2 py-0.5 text-[9px] text-emerald-400 hover:text-emerald-300 font-semibold cursor-pointer active:scale-95 hover:scale-[1.02] transition-all hover:bg-slate-800/30"
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Chat Scrolling Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {chatHistory.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <MessageSquare className="w-6 h-6" />
              </div>
              {(() => {
                const userName = user?.full_name || user?.username || (language === "hi" ? "आर्टिसन" : "Artisan");
                return (
                  <>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                      {language === "hi" ? `नमस्ते ${userName}!` : `Hello ${userName}!`}
                    </h4>
                    <p className="text-[10px] text-slate-400 max-w-[240px] leading-relaxed">
                      {language === "hi"
                        ? "मैं आर्टिसनएज का आपका वॉइस असिस्टेंट हूँ। आज मैं इन्वेंट्री, वित्त या मांग पूर्वानुमानों को प्रबंधित करने में आपकी क्या सहायता कर सकता हूँ?"
                        : "I am your Voice Assistant for ArtisanEdge. How can I help you manage your inventory, finances, or forecasts today?"}
                    </p>
                  </>
                );
              })()}
            </div>
          )}

          {chatHistory.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"} animate-fadeIn`}
            >
              <div
                style={{
                  background: msg.sender === "user" ? "rgba(16, 185, 129, 0.15)" : "rgba(255, 255, 255, 0.03)",
                  border: msg.sender === "user" ? "1px solid rgba(16, 185, 129, 0.25)" : "1px solid rgba(255, 255, 255, 0.08)",
                  borderRadius: msg.sender === "user" ? "1.25rem 1.25rem 0.25rem 1.25rem" : "1.25rem 1.25rem 1.25rem 0.25rem"
                }}
                className="max-w-[85%] px-4 py-3 text-xs text-slate-355 leading-relaxed shadow-md"
              >
                {msg.text}
              </div>
            </div>
          ))}

          {statusMessage && (
            <div className="flex justify-start animate-pulse">
              <div className="bg-white/2 border border-white/5 rounded-2xl px-4 py-2.5 text-[10px] text-slate-400 font-medium">
                {statusMessage}
              </div>
            </div>
          )}
          
          <div ref={chatEndRef} />
        </div>

        {/* Microphones Control Panel */}
        <div className="p-6 border-t border-white/5 flex flex-col items-center gap-3 flex-shrink-0">
          {/* Pulsing microphone outer circle */}
          <div className="relative">
            {isListening && (
              <span className="absolute inset-0 rounded-full bg-emerald-500/20 border border-emerald-500/30 animate-ping" />
            )}
            
            <button
              onClick={handleMicClick}
              style={{
                background: isListening ? "rgba(239, 68, 68, 0.2)" : "rgba(30, 41, 59, 0.6)",
                border: isListening ? "1px solid rgba(239, 68, 68, 0.4)" : "1px solid rgba(255, 255, 255, 0.05)",
                boxShadow: "inset 3px 3px 6px rgba(255, 255, 255, 0.05), inset -3px -3px 6px rgba(0, 0, 0, 0.3), 0 4px 16px rgba(0, 0, 0, 0.25)",
                borderRadius: "9999px"
              }}
              className={`w-16 h-16 flex items-center justify-center cursor-pointer active:scale-95 transition-all duration-300 ${
                isListening ? "text-red-400 hover:text-red-300" : "text-emerald-400 hover:text-emerald-300 hover:scale-105"
              }`}
            >
              {isListening ? <MicOff className="w-6 h-6 animate-pulse" /> : <Mic className="w-6 h-6" />}
            </button>
          </div>

          <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
            {isListening 
              ? (language === "hi" ? "सुन रहा हूँ... बोलें" : "Listening... Speak now") 
              : (language === "hi" ? "पूछने के लिए दबाएं" : "Press to ask AI")
            }
          </span>
        </div>
      </div>
    </>
  );
}
