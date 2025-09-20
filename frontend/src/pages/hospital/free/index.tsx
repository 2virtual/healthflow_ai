import React, { useEffect, useState } from "react";
import {
  Container,
  Typography,
  Paper,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Button,
  CircularProgress,
  Alert,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useWaitTimes } from "src/hooks/useWaitTimes";

type HospitalWaitTime = {
  hospital: string;
  waitTime: string;   // e.g. "4 hr 58 min"
  patients: string;   // e.g. "Open 24 hours"
};

// helper: parse "4 hr 58 min" -> total minutes
function parseMinutes(waitTime: string): number {
  if (!waitTime) return 0;
  const hrMatch = waitTime.match(/(\d+)\s*hr/);
  const minMatch = waitTime.match(/(\d+)\s*min/);
  const hrs = hrMatch ? parseInt(hrMatch[1], 10) : 0;
  const mins = minMatch ? parseInt(minMatch[1], 10) : 0;
  return hrs * 60 + mins;
}

export default function HospitalFreePage() {
  const navigate = useNavigate();
  const { waitTimes, loading } = useWaitTimes();
  const [alert, setAlert] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    if (waitTimes.length > 0) {
      const longWait = waitTimes.find(
        (h) => parseMinutes(h.waitTime) > 240
      );
      if (longWait) {
        setAlert(`⚠️ High wait alert: ${longWait.hospital} > 4 hours!`);
      } else {
        setAlert(null);
      }
      setLastUpdated(new Date()); // update timestamp when data changes
    }
  }, [waitTimes]);

  // helper to format "Updated 2 mins ago"
  function timeAgo(date: Date) {
    const diffMs = Date.now() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins === 1) return "Updated 1 min ago";
    return `Updated ${diffMins} mins ago`;
  }

  return (
    <Container sx={{ py: 6 }}>
      <Typography variant="h4" gutterBottom>
        Hospital Metrics (Free Tier)
      </Typography>

     
      <Typography variant="subtitle1" sx={{ mb: 3 }}>
        Free tools available for hospitals to monitor basic activity:
      </Typography>

      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        {loading ? (
          <CircularProgress />
        ) : (
          <>
            {alert && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                {alert}
              </Alert>
            )}
             {lastUpdated && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", mb: 2 }}
        >
          {timeAgo(lastUpdated)}
        </Typography>
      )}

            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Hospital</TableCell>
                  <TableCell align="right">Wait Time</TableCell>
                  <TableCell align="right">Operating Hours / Notes</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {waitTimes.map((row: HospitalWaitTime, idx: number) => (
                  <TableRow key={idx}>
                    <TableCell>{row.hospital}</TableCell>
                    <TableCell align="right">
                      {row.waitTime || "N/A"}
                    </TableCell>
                    <TableCell
                         align="right"
                         sx={{ whiteSpace: "pre-line" }}
                         >
  {row.patients?.replace(/<br\s*\/?>/gi, "\n") || "N/A"}
</TableCell>

                    {/* <TableCell align="right">
                      {row.patients || "N/A"}
                    </TableCell> */}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        )}
      </Paper>

      <Button
        variant="contained"
        onClick={() => navigate("/hospital-dashboard")}
      >
        Upgrade to Full Dashboard
      </Button>
    </Container>
  );
}




// import React, { useEffect, useState } from "react";
// import {
//   Container,
//   Typography,
//   Paper,
//   Table,
//   TableHead,
//   TableRow,
//   TableCell,
//   TableBody,
//   Button,
//   CircularProgress,
//   Alert,
// } from "@mui/material";
// import { useNavigate } from "react-router-dom";
// import { useWaitTimes } from "src/hooks/useWaitTimes";

// type HospitalWaitTime = {
//   hospital: string;
//   waitTime: string;   // e.g. "4 hr 58 min"
//   patients: string;   // e.g. "Open 24 hours"
// };

// // helper: parse "4 hr 58 min" -> total minutes
// function parseMinutes(waitTime: string): number {
//   if (!waitTime) return 0;
//   const hrMatch = waitTime.match(/(\d+)\s*hr/);
//   const minMatch = waitTime.match(/(\d+)\s*min/);
//   const hrs = hrMatch ? parseInt(hrMatch[1], 10) : 0;
//   const mins = minMatch ? parseInt(minMatch[1], 10) : 0;
//   return hrs * 60 + mins;
// }

// export default function HospitalFreePage() {
//   const navigate = useNavigate();
//   const { waitTimes, loading } = useWaitTimes();
//   const [alert, setAlert] = useState<string | null>(null);

//   useEffect(() => {
//     if (waitTimes.length > 0) {
//       const longWait = waitTimes.find(
//         (h) => parseMinutes(h.waitTime) > 240
//       );
//       if (longWait) {
//         setAlert(`⚠️ High wait alert: ${longWait.hospital} > 4 hours!`);
//       } else {
//         setAlert(null);
//       }
//     }
//   }, [waitTimes]);

//   return (
//     <Container sx={{ py: 6 }}>
//       <Typography variant="h4" gutterBottom>
//         Hospital Metrics (Free Tier)
//       </Typography>
//       <Typography variant="subtitle1" sx={{ mb: 3 }}>
//         Free tools available for hospitals to monitor basic activity:
//       </Typography>

//       <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
//         {loading ? (
//           <CircularProgress />
//         ) : (
//           <>
//             {alert && (
//               <Alert severity="warning" sx={{ mb: 2 }}>
//                 {alert}
//               </Alert>
//             )}

//             <Table>
//               <TableHead>
//                 <TableRow>
//                   <TableCell>Hospital</TableCell>
//                   <TableCell align="right">Wait Time</TableCell>
//                   <TableCell align="right">Operating Hours / Notes</TableCell>
//                 </TableRow>
//               </TableHead>
//               <TableBody>
//                 {waitTimes.map((row: HospitalWaitTime, idx: number) => (
//                   <TableRow key={idx}>
//                     <TableCell>{row.hospital}</TableCell>
//                     <TableCell align="right">
//                       {row.waitTime || "N/A"}
//                     </TableCell>
//                     <TableCell align="right">
//                       {row.patients || "N/A"}
//                     </TableCell>
//                   </TableRow>
//                 ))}
//               </TableBody>
//             </Table>
//           </>
//         )}
//       </Paper>

//       <Button
//         variant="contained"
//         onClick={() => navigate("/hospital-dashboard")}
//       >
//         Upgrade to Full Dashboard
//       </Button>
//     </Container>
//   );
// }
