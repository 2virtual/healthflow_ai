import { useEffect, useState } from "react";

export function useWaitTimes() {
  const [waitTimes, setWaitTimes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let ws: WebSocket | null = null;

    const connectWebSocket = () => {
      ws = new WebSocket("ws://localhost:8000/ws/ed-waits");

      ws.onopen = () => {
        console.log("✅ Connected to wait times WebSocket");
        setLoading(false);
      };

      ws.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data);

          // ✅ keep wait_time and note as strings
          const mapped = raw.map((h: any) => ({
            hospital: h.name,
            waitTime: h.wait_time || "N/A",
            patients: h.note || "N/A",
          }));

          console.log("📡 Live wait times update:", mapped);
          setWaitTimes(mapped);
        } catch (err) {
          console.error("❌ Failed to parse WS message:", err);
        }
      };

      ws.onerror = (err) => {
        console.error("⚠️ WebSocket error:", err);
      };

      ws.onclose = () => {
        console.log("🔴 Disconnected from WebSocket, retrying...");
        setLoading(true);
        setTimeout(connectWebSocket, 3000); // auto-reconnect
      };
    };

    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  return { waitTimes, loading };
}











// import { useEffect, useState } from "react";

// export function useWaitTimes() {
//   const [waitTimes, setWaitTimes] = useState<any[]>([]);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     let ws: WebSocket | null = null;

//     const connectWebSocket = () => {
//   ws = new WebSocket("ws://localhost:8000/ws/ed-waits");

//       ws.onopen = () => {
//         console.log("✅ Connected to wait times WebSocket");
//         setLoading(false);
//       };

//       ws.onmessage = (event) => {
//         try {
//           const raw = JSON.parse(event.data);

//           // Transform to match your HospitalWaitTime type
//           const mapped = raw.map((h: any) => ({
//             hospital: h.name,
//             waitTime: h.wait_time,
//             patients: h.note ? parseInt(h.note) || 0 : 0,
//           }));

//           console.log("📡 Live wait times update:", mapped);
//           setWaitTimes(mapped);
//         } catch (err) {
//           console.error("❌ Failed to parse WS message:", err);
//         }
//       };

//       ws.onerror = (err) => {
//         console.error("⚠️ WebSocket error:", err);
//       };

//       ws.onclose = () => {
//         console.log("🔴 Disconnected from WebSocket, retrying...");
//         setLoading(true);
//         setTimeout(connectWebSocket, 3000); // auto-reconnect
//       };
//     };

//     connectWebSocket();

//     return () => {
//       if (ws) {
//         ws.close();
//       }
//     };
//   }, []);

//   return { waitTimes, loading };
// }
