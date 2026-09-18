import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, 
  User, 
  Send, 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  Sparkles, 
  Clock, 
  FileText, 
  Trash2, 
  RefreshCw, 
  Copy, 
  Check, 
  Zap,
  MessageSquare,
  Keyboard,
  Paperclip,
  X,
  Image as ImageIcon,
  Globe,
  GraduationCap,
  Code,
  Play
} from 'lucide-react';
import zenLogo from './assets/zen_logo.jpeg';
import './App.css';

export default function App() {
  const [messages, setMessages] = useState([
    {
      sender: 'jarvis',
      text: "Systems Online. I am Zen, your AI assistant. How may I assist you today?",
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeakMode, setIsSpeakMode] = useState(false);
  const [speechLang, setSpeechLang] = useState('auto'); // 'auto' | 'ta-IN' | 'en-US'
  const [isLoading, setIsLoading] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [attachedFile, setAttachedFile] = useState(null); // { filename, mimeType, dataBase64, previewUrl, size }
  const [status, setStatus] = useState({ online: true, facts_count: 0, reminders_count: 0, tutor_mode: false });
  const [remindersList, setRemindersList] = useState([]);
  const [notesList, setNotesList] = useState('');
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [mobileTab, setMobileTab] = useState('chat'); // 'chat' | 'reminders' | 'notes' | 'controls'
  const [codeContent, setCodeContent] = useState('# Hands-On Python Practice\n\ndef greet(name):\n    return f"Hello, {name}!"\n\nprint(greet("Jarvis"))');
  const [isWorkspaceOpen, setIsWorkspaceOpen] = useState(false);

  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const fileInputRef = useRef(null);
  const isSpeakModeRef = useRef(false);
  const isLoadingRef = useRef(false);
  const isSpeakingRef = useRef(false);

  // Sync refs with state
  useEffect(() => {
    isSpeakModeRef.current = isSpeakMode;
  }, [isSpeakMode]);

  useEffect(() => {
    isLoadingRef.current = isLoading;
  }, [isLoading]);

  // Auto open workspace panel when tutor mode is enabled
  useEffect(() => {
    if (status.tutor_mode) {
      setIsWorkspaceOpen(true);
    }
  }, [status.tutor_mode]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Fetch status, reminders, and notes
  const fetchSystemData = async () => {
    try {
      const [resStatus, resReminders, resNotes] = await Promise.all([
        fetch('/api/status').then(r => r.json()).catch(() => null),
        fetch('/api/reminders').then(r => r.json()).catch(() => null),
        fetch('/api/notes').then(r => r.json()).catch(() => null)
      ]);

      if (resStatus) setStatus(resStatus);
      if (resReminders && resReminders.reminders) setRemindersList(resReminders.reminders);
      if (resNotes && resNotes.notes) setNotesList(resNotes.notes);
    } catch (e) {
      console.warn("Failed to fetch system data:", e);
    }
  };

  useEffect(() => {
    fetchSystemData();
    const interval = setInterval(fetchSystemData, 15000);
    return () => clearInterval(interval);
  }, []);

  // Web Audio API beep helper function (~1000Hz, ~0.3 seconds)
  const playBeep = () => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const audioCtx = new AudioCtx();
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(1000, audioCtx.currentTime);
      gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);

      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);

      oscillator.start();
      oscillator.stop(audioCtx.currentTime + 0.3);
    } catch (e) {
      console.warn("Web Audio API beep error:", e);
    }
  };

  // Client-side reminder polling effect (polls /reminders/check every 15s)
  useEffect(() => {
    const checkDueReminders = async () => {
      try {
        const response = await fetch('/reminders/check');
        if (!response.ok) return;
        const data = await response.json();
        if (data && Array.isArray(data.due) && data.due.length > 0) {
          const newChatItems = [];
          data.due.forEach(reminder => {
            // 1. Play a short beep using Web Audio API
            playBeep();

            const reminderMessage = `Reminder: ${reminder.task}`;
            const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            newChatItems.push({
              sender: 'jarvis',
              text: reminderMessage,
              time: timeStr
            });

            // 3. Speak it aloud using SpeechSynthesisUtterance (browser text-to-speech)
            if ('speechSynthesis' in window) {
              try {
                const utterance = new SpeechSynthesisUtterance(reminderMessage);
                utterance.rate = 1.0;
                window.speechSynthesis.speak(utterance);
              } catch (e) {
                console.warn("SpeechSynthesis error:", e);
              }
            }
          });

          if (newChatItems.length > 0) {
            // 2. Add message to chat like "Reminder: {task}"
            setMessages(prev => [...prev, ...newChatItems]);
          }

          fetchSystemData();
        }
      } catch (err) {
        console.warn("Error checking due reminders:", err);
      }
    };

    checkDueReminders();
    const interval = setInterval(checkDueReminders, 15000);
    return () => clearInterval(interval);
  }, []);

  // Web Speech Recognition setup
  const initSpeechRecognition = (lang) => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;

    const recognition = new SpeechRecognition();
    recognition.lang = lang === 'ta-IN' ? 'ta-IN' : 'en-US';
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const spokenText = event.results[0][0].transcript;
      setInput(spokenText);
      handleSend(spokenText);
    };

    recognition.onend = () => {
      setIsListening(false);
      // Auto-restart listening continuously if Speak Mode is active and AI is idle
      if (isSpeakModeRef.current && !isLoadingRef.current && !isSpeakingRef.current) {
        setTimeout(startListening, 300);
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      setIsListening(false);
      if (isSpeakModeRef.current && !isLoadingRef.current && !isSpeakingRef.current && event.error !== 'aborted') {
        setTimeout(startListening, 800);
      }
    };

    recognitionRef.current = recognition;
    return recognition;
  };

  useEffect(() => {
    initSpeechRecognition(speechLang);
  }, [speechLang]);

  const startListening = () => {
    if (isSpeakingRef.current || isLoadingRef.current) return;
    if (!recognitionRef.current) {
      initSpeechRecognition(speechLang);
    }
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch (e) {
      setIsListening(true);
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    setIsListening(false);
  };

  const toggleListening = () => {
    if (!recognitionRef.current && !initSpeechRecognition(speechLang)) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }
    if (isListening || isSpeakMode) {
      setIsSpeakMode(false);
      isSpeakModeRef.current = false;
      stopListening();
    } else {
      setIsSpeakMode(true);
      isSpeakModeRef.current = true;
      startListening();
    }
  };

  const toggleSpeakMode = () => {
    if (isSpeakMode) {
      setIsSpeakMode(false);
      isSpeakModeRef.current = false;
      stopListening();
    } else {
      setIsSpeakMode(true);
      isSpeakModeRef.current = true;
      startListening();
    }
  };

  // Male Voice Speech Output (Tamil & English) with Hands-Free Speak Mode Auto-Restart
  const speakText = (text) => {
    if (!ttsEnabled) {
      isSpeakingRef.current = false;
      if (isSpeakModeRef.current) {
        setTimeout(startListening, 600);
      }
      return;
    }
    let cleanText = text.replace(/\[Offline Mode\]/g, '').trim();

    // In Tutor Mode, strip long raw code blocks from spoken TTS so Jarvis gives concise, encouraging vocal summaries!
    if (status.tutor_mode && cleanText.includes("```")) {
      cleanText = cleanText
        .replace(/```[\s\S]*?```/g, " [Code block displayed in workspace.] ")
        .replace(/`([^`]+)`/g, "$1")
        .trim();
    }

    if (!cleanText) {
      isSpeakingRef.current = false;
      if (isSpeakModeRef.current) {
        setTimeout(startListening, 600);
      }
      return;
    }

    try {
      if (window.currentAudio) {
        window.currentAudio.pause();
      }
      isSpeakingRef.current = true;
      stopListening();

      const audio = new Audio(`/api/tts?text=${encodeURIComponent(cleanText)}`);
      window.currentAudio = audio;

      audio.onended = () => {
        isSpeakingRef.current = false;
        if (isSpeakModeRef.current) {
          setTimeout(startListening, 400);
        }
      };

      audio.onerror = () => {
        console.warn("Audio element error, trying fallback WebSpeech");
        fallbackWebSpeech(cleanText);
      };

      audio.play().catch(err => {
        console.warn("Audio play error, using WebSpeech fallback:", err);
        fallbackWebSpeech(cleanText);
      });
    } catch (e) {
      console.warn("Audio stream error:", e);
      fallbackWebSpeech(cleanText);
    }
  };

  const fallbackWebSpeech = (cleanText) => {
    if (!('speechSynthesis' in window)) {
      isSpeakingRef.current = false;
      if (isSpeakModeRef.current) {
        setTimeout(startListening, 500);
      }
      return;
    }
    window.speechSynthesis.cancel();
    isSpeakingRef.current = true;
    stopListening();

    const isTamil = /[\u0B80-\u0BFF]/.test(cleanText);
    const langCode = isTamil ? 'ta-IN' : 'en-US';
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = langCode;
    utterance.rate = 0.95;
    utterance.pitch = 0.85;

    const voices = window.speechSynthesis.getVoices();
    const targetVoice = voices.find(v => 
      (v.name.toLowerCase().includes('male') || v.name.toLowerCase().includes('valluvar') || v.name.toLowerCase().includes('david') || v.name.toLowerCase().includes('guy') || v.name.toLowerCase().includes('christopher')) && 
      (v.lang.startsWith(isTamil ? 'ta' : 'en'))
    ) || voices.find(v => v.lang.startsWith(isTamil ? 'ta' : 'en'));

    if (targetVoice) {
      utterance.voice = targetVoice;
    }

    utterance.onend = () => {
      isSpeakingRef.current = false;
      if (isSpeakModeRef.current) {
        setTimeout(startListening, 400);
      }
    };

    utterance.onerror = () => {
      isSpeakingRef.current = false;
      if (isSpeakModeRef.current) {
        setTimeout(startListening, 400);
      }
    };

    window.speechSynthesis.speak(utterance);
  };

  // File Attachment Handling
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      setAttachedFile({
        filename: file.name,
        mimeType: file.type || 'application/octet-stream',
        dataBase64: reader.result,
        previewUrl: file.type.startsWith('image/') ? reader.result : null,
        size: (file.size / 1024).toFixed(1) + ' KB'
      });
    };
    reader.readAsDataURL(file);
  };

  const removeAttachedFile = () => {
    setAttachedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Send Message Logic
  const handleSend = async (textToSend) => {
    const messageText = (textToSend || input).trim();
    if ((!messageText && !attachedFile) || isLoading) return;

    const lowerText = messageText.toLowerCase();

    // Check for "type mode" command verbally
    if (lowerText === "type mode" || lowerText.includes("switch to type mode") || lowerText.includes("turn off speak mode")) {
      setIsSpeakMode(false);
      isSpeakModeRef.current = false;
      stopListening();
      const userTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setMessages(prev => [
        ...prev,
        { sender: 'user', text: messageText, time: userTime },
        { sender: 'jarvis', text: "Switched to Type Mode.", time: userTime }
      ]);
      setInput('');
      speakText("Switched to Type Mode.");
      return;
    }

    // Check for "speak mode" command verbally
    if (lowerText === "speak mode" || lowerText.includes("switch to speak mode") || lowerText.includes("turn on speak mode")) {
      setIsSpeakMode(true);
      isSpeakModeRef.current = true;
      const userTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setMessages(prev => [
        ...prev,
        { sender: 'user', text: messageText, time: userTime },
        { sender: 'jarvis', text: "Speak Mode activated. Listening continuously.", time: userTime }
      ]);
      setInput('');
      speakText("Speak Mode activated. Listening continuously.");
      return;
    }

    const currentFile = attachedFile;
    setAttachedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';

    const userTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newMessages = [
      ...messages, 
      { 
        sender: 'user', 
        text: messageText, 
        time: userTime,
        file: currentFile
      }
    ];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: messageText,
          file: currentFile ? {
            data: currentFile.dataBase64,
            mime_type: currentFile.mimeType,
            filename: currentFile.filename
          } : null
        })
      });
      const data = await response.json();
      const replyText = data.reply || "No response generated.";
      const zenTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      setMessages(prev => [...prev, { sender: 'jarvis', text: replyText, time: zenTime }]);
      speakText(replyText);
      fetchSystemData();
    } catch (err) {
      console.error("Chat error:", err);
      setMessages(prev => [
        ...prev, 
        { sender: 'jarvis', text: "Connection error: Unable to communicate with Zen backend.", time: userTime }
      ]);
      if (isSpeakModeRef.current) {
        setTimeout(startListening, 1000);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearMemory = async () => {
    try {
      await fetch('/api/clear-memory', { method: 'POST' });
      setNotesList("You don't have any notes yet.");
      setMessages(prev => [
        ...prev,
        {
          sender: 'jarvis',
          text: "Memory wiped clean. Saved notes and facts reset.",
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
      fetchSystemData();
    } catch (e) {
      console.error("Clear memory error:", e);
    }
  };

  const copyToClipboard = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const quickActions = [
    { label: "🎓 Turn as Jarvis (Tutor Mode)", command: "turn as jarvis" },
    { label: "Python Hands-On Challenge", command: "teach me python hands-on" },
    { label: "JavaScript Hands-On", command: "teach me javascript hands-on" },
    { label: "Exit Tutor Mode", command: "exit tutor" },
    { label: "Speak Tamil (தமிழ்)", command: "Respond in Tamil: வணக்கம், Python கற்றுக் கொடுங்கள்" },
    { label: "Calculate 128 * 4", command: "calculate 128 * 4" },
    { label: "Remind me to call John at 5pm", command: "remind me to call John at 5pm" }
  ];

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <img src={zenLogo} alt="Zen AI Logo" className="brand-logo-img" />
          <span className="brand-title">ZEN AI</span>
        </div>

        <div className="header-meta">
          <div className={`status-badge ${status.online ? 'online' : 'offline'}`}>
            <span className="status-dot"></span>
            {status.online ? 'ONLINE' : 'OFFLINE'}
          </div>

          {status.tutor_mode && (
            <div 
              className="status-badge tutor-badge" 
              style={{ background: 'rgba(255, 184, 0, 0.15)', border: '1px solid #FFB800', color: '#FFD700', padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
              onClick={() => handleSend('exit tutor')}
              title="Tutor Mode Active! Click to exit."
            >
              <GraduationCap size={14} />
              <span>TUTOR MODE</span>
            </div>
          )}

          <button 
            className={`icon-btn ${isWorkspaceOpen ? 'active' : ''}`}
            onClick={() => setIsWorkspaceOpen(!isWorkspaceOpen)}
            title="Pop up Interactive Code Workspace Panel"
            style={isWorkspaceOpen ? { background: 'rgba(255, 215, 0, 0.2)', border: '1px solid #FFD700', color: '#FFD700' } : {}}
          >
            <Code size={15} />
            <span>Workspace</span>
          </button>

          <button 
            className={`icon-btn ${speechLang === 'ta-IN' ? 'active' : ''}`}
            onClick={() => setSpeechLang(speechLang === 'ta-IN' ? 'en-US' : 'ta-IN')}
            title="Toggle Voice Input Language (Tamil / English)"
          >
            <Globe size={14} />
            <span>{speechLang === 'ta-IN' ? 'தமிழ் (TA)' : 'English (EN)'}</span>
          </button>

          <button 
            className={`mode-toggle-btn ${isSpeakMode ? 'speak-mode' : 'type-mode'}`}
            onClick={toggleSpeakMode}
            title={isSpeakMode ? "Click to switch to Type Mode" : "Click to switch to Continuous Speak Mode"}
          >
            {isSpeakMode ? <Mic size={14} /> : <Keyboard size={14} />}
            <span>{isSpeakMode ? 'Speak Mode' : 'Type Mode'}</span>
          </button>

          <button 
            className={`icon-btn ${ttsEnabled ? 'active' : ''}`} 
            onClick={() => setTtsEnabled(!ttsEnabled)}
            title="Toggle Voice Speech Output"
          >
            {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>

          <button 
            className="icon-btn" 
            onClick={fetchSystemData} 
            title="Sync Data"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      {/* Mobile Navigation Bar */}
      <nav className="mobile-nav-tabs">
        <button 
          className={`mobile-tab-btn ${mobileTab === 'chat' ? 'active' : ''}`}
          onClick={() => setMobileTab('chat')}
        >
          <MessageSquare size={14} /> Chat
        </button>
        <button 
          className={`mobile-tab-btn ${mobileTab === 'controls' ? 'active' : ''}`}
          onClick={() => setMobileTab('controls')}
        >
          <Zap size={14} /> Voice & Actions
        </button>
        <button 
          className={`mobile-tab-btn ${mobileTab === 'reminders' ? 'active' : ''}`}
          onClick={() => setMobileTab('reminders')}
        >
          <Clock size={14} /> Reminders ({remindersList.filter(r => !r.done).length})
        </button>
        <button 
          className={`mobile-tab-btn ${mobileTab === 'notes' ? 'active' : ''}`}
          onClick={() => setMobileTab('notes')}
        >
          <FileText size={14} /> Notes
        </button>
      </nav>

      {/* Main Dashboard Layout */}
      <main className="dashboard-grid">
        {/* Left Sidebar (Desktop View / Drawer on Mobile) */}
        <aside className={`sidebar ${mobileTab !== 'chat' ? 'mobile-active' : ''}`}>
          {/* Voice Orb HUD Card */}
          {(mobileTab === 'controls' || window.innerWidth > 768) && (
            <div className="glass-panel voice-visualizer-card">
              <div 
                className={`voice-orb-container ${isListening ? 'listening' : ''}`}
                onClick={toggleListening}
                title="Click to Speak to Zen"
              >
                <div className="voice-ripple"></div>
                <div className="voice-orb">
                  {status.tutor_mode ? <GraduationCap size={28} color="#FFD700" /> : (isListening ? <Mic size={28} /> : <img src={zenLogo} alt="Zen Logo" className="voice-orb-logo" />)}
                </div>
              </div>
              <h3 className="voice-status-title">
                {status.tutor_mode 
                  ? "🎓 Friendly Tutor Active" 
                  : (isListening ? (isSpeakMode ? "Continuous Listening..." : "Listening...") : (isSpeakMode ? "Speak Mode Active" : "Zen HUD Active"))}
              </h3>
              <p className="voice-status-sub">
                {status.tutor_mode
                  ? "Hands-on coding mentor ready. Say 'exit tutor' to stop."
                  : (isSpeakMode 
                    ? "Hands-free active. Say 'type mode' to stop continuous listening." 
                    : "Click orb/mic or say 'turn as jarvis' for Tutor Mode")}
              </p>
            </div>
          )}

          {/* Quick Actions Card */}
          {(mobileTab === 'controls' || window.innerWidth > 768) && (
            <div className="glass-panel widget-card">
              <div className="section-header">
                <span>Quick Commands</span>
                <Sparkles size={14} color="#00F2FE" />
              </div>
              <div className="chip-group">
                {quickActions.map((action, idx) => (
                  <button 
                    key={idx} 
                    className="action-chip"
                    onClick={() => handleSend(action.command)}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Reminders Widget */}
          {(mobileTab === 'reminders' || window.innerWidth > 768) && (
            <div className="glass-panel widget-card">
              <div className="section-header">
                <span>Active Reminders</span>
                <Clock size={14} color="#00F2FE" />
              </div>
              <div className="widget-list">
                {remindersList.filter(r => !r.done).length > 0 ? (
                  remindersList.filter(r => !r.done).map((r, idx) => (
                    <div key={idx} className="widget-item">
                      <span className="widget-item-time">
                        {new Date(r.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span>{r.task}</span>
                    </div>
                  ))
                ) : (
                  <p className="empty-text">No active reminders found.</p>
                )}
              </div>
            </div>
          )}

          {/* Notes Widget */}
          {(mobileTab === 'notes' || window.innerWidth > 768) && (
            <div className="glass-panel widget-card">
              <div className="section-header">
                <span>Saved Notes & Memory</span>
                <FileText size={14} color="#00F2FE" />
              </div>
              <div className="widget-list">
                {notesList && !notesList.includes("don't have any notes") ? (
                  <div className="widget-item" style={{ whiteSpace: 'pre-wrap' }}>
                    {notesList}
                  </div>
                ) : (
                  <p className="empty-text">No notes saved in memory yet.</p>
                )}
              </div>
              <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                <button 
                  className="clear-btn" 
                  onClick={handleClearMemory}
                  title="Wipe saved memory and notes"
                >
                  <Trash2 size={13} /> Clear Memory
                </button>
              </div>
            </div>
          )}
        </aside>

        {/* Right Section: Chat & Code Workspace Interface */}
        <section className={`chat-section glass-panel ${isWorkspaceOpen ? 'tutor-split-mode' : ''} ${mobileTab === 'chat' ? 'mobile-active' : ''}`}>
          {/* Interactive Hands-On Code Workspace Plugin Panel */}
          {isWorkspaceOpen && (
            <div className="code-workspace-panel">
              <div className="code-workspace-header">
                <div className="code-workspace-title">
                  <Code size={18} color="#FFD700" />
                  <span>Interactive Code Workspace</span>
                </div>
                <div className="code-workspace-actions">
                  <button type="button" className="code-lang-btn" onClick={() => setCodeContent('# Python Hands-On Practice\n\ndef greet(name):\n    return f"Hello, {name}!"\n\nprint(greet("Jarvis"))')}>Python</button>
                  <button type="button" className="code-lang-btn" onClick={() => setCodeContent('// JavaScript Hands-On Practice\n\nfunction calculate(a, b) {\n    return a * b;\n}\n\nconsole.log(calculate(5, 10));')}>JavaScript</button>
                  <button type="button" className="code-lang-btn" onClick={() => setCodeContent('<!-- HTML/CSS Hands-On Practice -->\n<div class="card">\n  <h1>Hello Jarvis!</h1>\n</div>')}>HTML/CSS</button>
                  <button type="button" className="code-clear-btn" onClick={() => setCodeContent('')} title="Clear Code Workspace"><Trash2 size={13} /></button>
                  <button type="button" className="code-clear-btn" onClick={() => setIsWorkspaceOpen(false)} title="Close Workspace Panel" style={{ background: 'rgba(255,255,255,0.08)', color: '#FFF' }}><X size={14} /></button>
                </div>
              </div>
              <textarea 
                className="code-editor-textarea"
                value={codeContent}
                onChange={(e) => setCodeContent(e.target.value)}
                placeholder="// Write or paste your multi-line code here hands-on...\n// Then click 'Run & Check Code with Jarvis'"
                spellCheck="false"
              />
              <div className="code-workspace-footer">
                <button 
                  type="button"
                  className="submit-code-btn"
                  onClick={() => {
                    if (!codeContent.trim()) return;
                    const fullPrompt = `Please check my code hands-on:\n\n\`\`\`\n${codeContent}\n\`\`\``;
                    handleSend(fullPrompt);
                  }}
                  disabled={isLoading || !codeContent.trim()}
                >
                  <Play size={14} />
                  <span>Run & Check Code</span>
                </button>
                <button 
                  type="button"
                  className="hint-code-btn"
                  onClick={() => handleSend("Give me a hint for the current hands-on coding task!")}
                  disabled={isLoading}
                >
                  <Sparkles size={14} color="#00F2FE" />
                  <span>Get Hint</span>
                </button>
              </div>
            </div>
          )}

          <div className="chat-feed-container">
            {/* Chat Feed */}
            <div className="chat-history">
              {messages.map((msg, index) => (
                <div key={index} className={`chat-row ${msg.sender}`}>
                  <div className={`avatar ${msg.sender}`}>
                    {msg.sender === 'jarvis' ? <img src={zenLogo} alt="Zen" className="avatar-logo-img" /> : <User size={20} />}
                  </div>
                  <div className="message-box">
                    {/* Attached File/Image Preview in Chat Bubble */}
                    {msg.file && (
                      <div className="chat-file-attachment">
                        {msg.file.previewUrl ? (
                          <img 
                            src={msg.file.previewUrl} 
                            alt="attached" 
                            className="msg-img-preview" 
                          />
                        ) : (
                          <div className="msg-file-badge">
                            <FileText size={16} color="#00F2FE" />
                            <span>{msg.file.filename}</span>
                          </div>
                        )}
                      </div>
                    )}

                    <div>{msg.text}</div>

                    <div className="msg-footer">
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{msg.time}</span>
                      {msg.sender === 'jarvis' && (
                        <>
                          <button 
                            className="msg-action-btn" 
                            onClick={() => speakText(msg.text)}
                            title="Speak aloud"
                          >
                            <Volume2 size={12} />
                          </button>
                          <button 
                            className="msg-action-btn" 
                            onClick={() => copyToClipboard(msg.text, index)}
                            title="Copy text"
                          >
                            {copiedIndex === index ? <Check size={12} color="#00F5A0" /> : <Copy size={12} />}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="chat-row jarvis">
                  <div className="avatar jarvis">
                    <img src={zenLogo} alt="Zen" className="avatar-logo-img" />
                  </div>
                  <div className="message-box typing-dots">
                    <div className="dot"></div>
                    <div className="dot"></div>
                    <div className="dot"></div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Interactive Input Form */}
            <div className="input-area">
              {/* File Attachment Preview Bar */}
              {attachedFile && (
                <div className="file-preview-bar">
                  {attachedFile.previewUrl ? (
                    <img src={attachedFile.previewUrl} alt="thumb" className="file-preview-thumb" />
                  ) : (
                    <FileText size={28} color="#00F2FE" />
                  )}
                  <div className="file-preview-info">
                    <span className="file-preview-name">{attachedFile.filename}</span>
                    <span className="file-preview-size">{attachedFile.size}</span>
                  </div>
                  <button type="button" className="file-remove-btn" onClick={removeAttachedFile}>
                    <X size={16} />
                  </button>
                </div>
              )}

              <form className="input-form" onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
                {/* Hidden File Input */}
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileSelect} 
                  accept="image/*,.txt,.pdf,.py,.js,.json,.csv,.md" 
                  style={{ display: 'none' }}
                />

                <button 
                  type="button" 
                  className="file-attach-btn"
                  onClick={() => fileInputRef.current?.click()}
                  title="Attach Image or File"
                >
                  <Paperclip size={18} />
                </button>

                <input 
                  type="text" 
                  className="text-input" 
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask Zen, attach image/file, calculate..."
                  disabled={isLoading}
                />

                <button 
                  type="button" 
                  className={`mic-btn ${isListening ? 'listening' : ''}`}
                  onClick={toggleListening}
                  title={isListening ? "Stop listening" : "Start voice input"}
                >
                  {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                </button>

                <button 
                  type="submit" 
                  className="send-btn" 
                  disabled={(!input.trim() && !attachedFile) || isLoading}
                >
                  <span>Send</span>
                  <Send size={16} />
                </button>
              </form>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
