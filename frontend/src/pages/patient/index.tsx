import React, { useState, useEffect, useRef } from 'react';
import {
  Container,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  TextField,
  IconButton,
  Box,
  Divider,
  CircularProgress,
  Alert,
  // MenuItem,
  // Select,
  // FormControl,
  // InputLabel,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

// Message types
type ChatMessage = {
  sender: 'user' | 'ai';
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
    { sender: 'ai', text: 'Hi! I’m HealthFlow AI. How can I help you today?' },
  ]);
  const [input, setInput] = useState('');
  // const [language, setLanguage] = useState('en'); // 👈 disabled for now
  const [isConnecting, setIsConnecting] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const ws = useRef<WebSocket | null>(null);
  const retryAttempt = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  const connectWebSocket = () => {
    setIsConnecting(true);
    setError(null);

    const websocket = new WebSocket('ws://localhost:8000/ws/triage');

    websocket.onopen = () => {
      console.log('✅ Connected to triage WebSocket');
      setIsConnecting(false);
      setError(null);
      retryAttempt.current = 0; // reset retries
    };

    websocket.onmessage = (event) => {
      try {
        const data: WebSocketResponse = JSON.parse(event.data);

        setMessages((prev) => [
          ...prev,
          { sender: 'ai', text: data.response },
        ]);

        if (data.recommended_level) {
          console.log(`Triage Level: ${data.recommended_level}`);
          console.log(`Score: ${data.score}`, 'Reasons:', data.reasons);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    websocket.onerror = (e) => {
      console.error('WebSocket error', e);
      setError('Connection failed. Retrying...');
    };

    websocket.onclose = () => {
      console.log('⚠️ WebSocket closed');
      setError('Disconnected from AI service. Retrying...');

      // Exponential backoff reconnect
      retryAttempt.current += 1;
      const delay = Math.min(1000 * 2 ** retryAttempt.current, 30000); // cap at 30s
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

  const handleSend = () => {
    if (!input.trim() || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;

    setMessages((prev) => [...prev, { sender: 'user', text: input }]);

    const payload = JSON.stringify({
      symptoms: input,
      age: 35,
      known_conditions: [],
      // language, // 👈 removed for now
    });

    ws.current.send(payload);
    setInput('');
  };

  return (
    <Container sx={{ py: 6 }}>
      <Typography variant="h4" gutterBottom>
        Patient Services (Free)
      </Typography>
      <Typography variant="subtitle1" sx={{ mb: 3 }}>
        Explore AI-powered tools available to patients:
      </Typography>

      {/* Features Overview */}
      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        <List>
          <ListItem>
            <ListItemText
              primary="Smart Hospital Recommendations"
              secondary="See the nearest hospitals ranked by distance and current wait times."
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Predictive Wait Times"
              secondary="Get estimates for how wait times may change over the next few hours."
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="AI Symptom Triage"
              secondary="Chat naturally with our AI to understand where you should go."
            />
          </ListItem>
        </List>
      </Paper>

      {/* Chat Section */}
      <Typography variant="h5" gutterBottom>
        AI Symptom Chat
      </Typography>

      <Paper
        elevation={3}
        sx={{
          p: 2,
          height: 500,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        {isConnecting && (
          <Box sx={{ textAlign: 'center', py: 1 }}>
            <CircularProgress size={20} />{' '}
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
            sx={{ textAlign: 'center', mb: 1 }}
          >
            Connected • You can start typing...
          </Typography>
        )}

        {/* Chat Messages */}
        <Box sx={{ flexGrow: 1, overflowY: 'auto', mb: 1 }}>
          {messages.map((msg, idx) => (
            <Box
              key={idx}
              sx={{
                display: 'flex',
                justifyContent:
                  msg.sender === 'user' ? 'flex-end' : 'flex-start',
                mb: 1,
                px: 1,
              }}
            >
              <Paper
                sx={{
                  p: 1.5,
                  maxWidth: '70%',
                  bgcolor: msg.sender === 'user' ? 'primary.main' : 'grey.200',
                  color: msg.sender === 'user' ? 'white' : 'text.primary',
                }}
              >
                {msg.text}
              </Paper>
            </Box>
          ))}
        </Box>

        <Divider />

        {/* Input Only (language dropdown commented out) */}
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, gap: 1 }}>
          {/* <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Language</InputLabel>
            <Select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              label="Language"
            >
              <MenuItem value="en">English</MenuItem>
              <MenuItem value="es">Español</MenuItem>
              <MenuItem value="fr">Français</MenuItem>
              <MenuItem value="ar">العربية</MenuItem>
              <MenuItem value="zh">中文</MenuItem>
            </Select>
          </FormControl> */}

          <TextField
            fullWidth
            variant="outlined"
            size="small"
            placeholder="Describe your symptoms..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={isConnecting || !!error}
          />
          <IconButton
            color="primary"
            onClick={handleSend}
            disabled={!input.trim() || isConnecting || !!error}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Paper>
    </Container>
  );
}





// import React, { useState } from 'react';
// import {
//   Container,
//   Typography,
//   Paper,
//   List,
//   ListItem,
//   ListItemText,
//   TextField,
//   IconButton,
//   Box,
//   Divider,
// } from '@mui/material';
// import SendIcon from '@mui/icons-material/Send';

// type Message = {
//   sender: 'user' | 'ai';
//   text: string;
// };

// export default function PatientPage() {
//   const [messages, setMessages] = useState<Message[]>([
//     { sender: 'ai', text: 'Hi! I’m Healthflow AI. How can I help you today?' },
//   ]);
//   const [input, setInput] = useState('');

//   const handleSend = () => {
//     if (!input.trim()) return;

//     // Add user message
//     const newMessages = [...messages, { sender: 'user', text: input }];

//     // Mock AI response (replace with backend call later)
//     const aiResponse = {
//       sender: 'ai',
//       text: "I'm analyzing your symptoms... (this will connect to the AI backend).",
//     };

//     setMessages([...newMessages, aiResponse]);
//     setInput('');
//   };

//   return (
//     <Container sx={{ py: 6 }}>
//       <Typography variant="h4" gutterBottom>
//         Patient Services (Free)
//       </Typography>
//       <Typography variant="subtitle1" sx={{ mb: 3 }}>
//         Explore AI-powered tools available to patients:
//       </Typography>

//       {/* Features Overview */}
//       <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
//         <List>
//           <ListItem>
//             <ListItemText
//               primary="Smart Hospital Recommendations"
//               secondary="See the nearest hospitals ranked by distance and current wait times."
//             />
//           </ListItem>
//           <ListItem>
//             <ListItemText
//               primary="Predictive Wait Times"
//               secondary="Get estimates for how wait times may change over the next few hours."
//             />
//           </ListItem>
//           <ListItem>
//             <ListItemText
//               primary="AI Symptom Triage"
//               secondary="Chat naturally with our AI to understand where you should go."
//             />
//           </ListItem>
//         </List>
//       </Paper>

//       {/* Chat Section */}
//       <Typography variant="h5" gutterBottom>
//         AI Symptom Chat
//       </Typography>
//       <Paper
//         elevation={3}
//         sx={{
//           p: 2,
//           height: 400,
//           display: 'flex',
//           flexDirection: 'column',
//           justifyContent: 'space-between',
//         }}
//       >
//         {/* Chat Messages */}
//         <Box sx={{ flexGrow: 1, overflowY: 'auto', mb: 2 }}>
//           {messages.map((msg, idx) => (
//             <Box
//               key={idx}
//               sx={{
//                 display: 'flex',
//                 justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
//                 mb: 1,
//               }}
//             >
//               <Paper
//                 sx={{
//                   p: 1.5,
//                   maxWidth: '70%',
//                   bgcolor: msg.sender === 'user' ? 'primary.main' : 'grey.200',
//                   color: msg.sender === 'user' ? 'white' : 'black',
//                 }}
//               >
//                 {msg.text}
//               </Paper>
//             </Box>
//           ))}
//         </Box>

//         <Divider />

//         {/* Input Box */}
//         <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
//           <TextField
//             fullWidth
//             variant="outlined"
//             size="small"
//             placeholder="Type your symptoms here..."
//             value={input}
//             onChange={(e) => setInput(e.target.value)}
//             onKeyDown={(e) => e.key === 'Enter' && handleSend()}
//           />
//           <IconButton color="primary" onClick={handleSend}>
//             <SendIcon />
//           </IconButton>
//         </Box>
//       </Paper>
//     </Container>
//   );
// }
