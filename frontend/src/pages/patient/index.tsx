import React, { useState, useEffect, useRef } from "react";
import {
  Container,
  Typography,
  Paper,
  Box,
  TextField,
  IconButton,
  Grid,
  Button,
  CircularProgress,
  Alert,
  InputAdornment,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";

// Example prompts
const examples = [
  "🧠 What should I do if someone has a seizure?",
  "🏥 Where is the closest hospital with the shortest wait time?",
  "💊 How do I know if my symptoms need urgent care?",
];

// Message types
type ChatMessage = {
  sender: "user" | "ai";
  text: string;
};

type WebSocketResponse = {
  response: string;
  recommended_level?: string;
  score?: number;
  reasons?: string[];
  suggested_action?: string;
  received_at: string;
  meta: Record<string, any>;
};

export default function PatientPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: "ai", text: "Hi! I’m HealthFlow AI. How can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const [isConnecting, setIsConnecting] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const retryAttempt = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // WebSocket connection
  const connectWebSocket = () => {
    setIsConnecting(true);
    setError(null);

    const websocket = new WebSocket("ws://localhost:8000/ws/triage");

    websocket.onopen = () => {
      console.log("✅ Connected to triage WebSocket");
      setIsConnecting(false);
      setError(null);
      retryAttempt.current = 0;
    };

    websocket.onmessage = (event) => {
      try {
        const data: WebSocketResponse = JSON.parse(event.data);

        setMessages((prev) => [...prev, { sender: "ai", text: data.response }]);

        if (data.recommended_level) {
          console.log(`Triage Level: ${data.recommended_level}`);
          console.log(`Score: ${data.score}`, "Reasons:", data.reasons);
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message", err);
      }
    };

    websocket.onerror = (e) => {
      console.error("WebSocket error", e);
      setError("Connection failed. Retrying...");
    };

    websocket.onclose = () => {
      console.log("⚠️ WebSocket closed");
      setError("Disconnected from AI service. Retrying...");

      retryAttempt.current += 1;
      const delay = Math.min(1000 * 2 ** retryAttempt.current, 30000);
      if (!reconnectTimeout.current) {
        reconnectTimeout.current = setTimeout(() => {
          reconnectTimeout.current = null;
          connectWebSocket();
        }, delay);
      }
    };

    ws.current = websocket;
  };

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, []);

  // Send message
  const handleSend = (exampleText?: string) => {
    const messageText = exampleText || input.trim();
    if (!messageText || !ws.current || ws.current.readyState !== WebSocket.OPEN)
      return;

    setMessages((prev) => [...prev, { sender: "user", text: messageText }]);

    const payload = JSON.stringify({
      symptoms: messageText,
      age: 35,
      known_conditions: [],
    });

    ws.current.send(payload);
    setInput("");
  };

  return (
    <Box sx={{ backgroundColor: "#fff", minHeight: "100vh", py: 4 }}>
      <Container maxWidth="lg">
        <Typography variant="h4" gutterBottom>
          Patient Services (Free)
        </Typography>
        <Typography variant="subtitle1" sx={{ mb: 3 }}>
          Explore AI-powered tools available to patients:
        </Typography>

        {/* Example Buttons */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {examples.map((ex, idx) => (
            <Grid item key={idx}>
              <Button
                variant="outlined"
                onClick={() => handleSend(ex)}
                sx={{
                  borderRadius: 3,
                  textTransform: "none",
                  bgcolor: "#f9f9f9",
                  px: 3,
                  py: 1.5,
                  boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
                  transition: "all 0.2s ease-in-out",
                  "&:hover": {
                    bgcolor: "#f0f0f0",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                  },
                }}
              >
                {ex}
              </Button>
            </Grid>
          ))}
        </Grid>

        {/* Chat Section */}
        <Paper
          elevation={3}
          sx={{
            display: "flex",
            flexDirection: "column",
            borderRadius: 2,
            backgroundColor: "#fff",
            maxHeight: "80vh",
            width: "100%",
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
          }}
        >
          {isConnecting && (
            <Box sx={{ textAlign: "center", py: 1 }}>
              <CircularProgress size={20} />{" "}
              <Typography variant="body2">Connecting...</Typography>
            </Box>
          )}
          {error && (
            <Alert severity="error" sx={{ mb: 1 }}>
              {error}
            </Alert>
          )}
          {!isConnecting && !error && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ textAlign: "center", mb: 1 }}
            >
              Connected • You can start typing...
            </Typography>
          )}

                    {/* Messages container */}
          <Box
            sx={{
              flexGrow: 1,
              overflowY: "auto",
              px: 2,
              py: 1,
              display: "flex",
              flexDirection: "column",
              gap: 1,
            }}
          >
            {messages.map((msg, idx) => (
              <Box
                key={idx}
                sx={{
                  display: "flex",
                  justifyContent: msg.sender === "user" ? "flex-end" : "flex-start",
                }}
              >
                <Paper
                  sx={{
                    p: 1.5,
                    maxWidth: "70%",
                    bgcolor: msg.sender === "user" ? "#DCF8C6" : "#F1F0F0",
                    color: "#111",
                    whiteSpace: "pre-line",
                    borderRadius: 2,
                    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                  }}
                >
                  {msg.text}
                </Paper>
              </Box>
            ))}
            <div ref={chatEndRef} />
          </Box>


          {/* Messages
          <Box
            sx={{
              flexGrow: 1,
              overflowY: "auto",
              px: 2,
              py: 1,
              display: "flex",
              flexDirection: "column",
              gap: 1,
            }}
          >
            {messages.map((msg, idx) => (
              <Box
                key={idx}
                sx={{
                  display: "flex",
                  justifyContent:
                    msg.sender === "user" ? "flex-end" : "flex-start",
                }}
              >
                <Paper
                  sx={{
                    p: 1.5,
                    maxWidth: "70%",
                  bgcolor: msg.sender === 'user' ? 'primary.main' : 'grey.200',
                  color: msg.sender === 'user' ? 'white' : 'text.primary',
                    // bgcolor: msg.sender === "user" ? "#1976d2" : "#F1F0F0",
                    // color: msg.sender === "user" ? "#fff" : "#111",
                    whiteSpace: "pre-line",
                    borderRadius: 2,
                    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                  }}
                >
                  {msg.text}
                </Paper>
              </Box>
            ))}
            <div ref={chatEndRef} />
          </Box> */}

          {/* Input */}
          <Box sx={{ px: 2, py: 1 }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Type your symptoms here..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isConnecting || !!error}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      color="primary"
                      onClick={() => handleSend()}
                      disabled={!input.trim() || isConnecting || !!error}
                    >
                      <SendIcon />
                    </IconButton>
                  </InputAdornment>
                ),
                sx: {
                  borderRadius: "25px",
                  bgcolor: "#f5f5f5",
                },
              }}
            />
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}


