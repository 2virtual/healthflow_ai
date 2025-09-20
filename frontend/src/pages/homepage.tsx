import { Box, Button, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import logoAnimation from "../../public/assets/illustrations/logo.png"; 
export default function HomePage() {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        textAlign: "center",
        gap: 3,
        p: 2,
      }}
    >
      {/* Animated Logo */}
      <Box
        component="img"
        src={logoAnimation}
        alt="Healthflow AI Logo"
        sx={{
          width: 160,
          height: 160,
          objectFit: "contain",
          mb: 2,
          animation: "pulse 2s infinite ease-in-out",
          "@keyframes pulse": {
            "0%": { transform: "scale(1)" },
            "50%": { transform: "scale(1.05)" },
            "100%": { transform: "scale(1)" },
          },
        }}
      />

      <Typography variant="h3" sx={{ fontWeight: "bold" }}>
        Healthflow AI
      </Typography>
      <Typography
  variant="h6"
  color="text.secondary"
  sx={{
    fontWeight: 400,
    fontSize: '1rem',
    whiteSpace: 'nowrap', // keep single line
  }}
>
  Smarter care decisions — real-time AI insights for all healthcare.
</Typography>

{/* 
 <Typography variant="h4" color="text.secondary" sx={{ maxWidth: 480 }}>
        Smarter care decisions — real-time AI insights for all healthcare.
      </Typography>  */}

      <Box sx={{ display: "flex", gap: 2 }}>
        <Button
          variant="contained"
          size="large"
          onClick={() => navigate("/patient")}
        >
          👩‍⚕️ I am a Patient
        </Button>
        <Button
          variant="outlined"
          size="large"
          onClick={() => navigate("/hospital")}
        >
          🏥 I work at a Hospital
        </Button>
      </Box>
    </Box>
  );
}




// // src/pages/homepage.tsx
// import { Box, Button, Typography } from "@mui/material";
// import { useNavigate } from "react-router-dom";

// export default function HomePage() {
//   const navigate = useNavigate();

//   return (
//     <Box
//       sx={{
//         minHeight: "100vh",
//         display: "flex",
//         flexDirection: "column",
//         justifyContent: "center",
//         alignItems: "center",
//         textAlign: "center",
//         gap: 3,
//         p: 2,
//       }}
//     >
//       <Typography variant="h3" sx={{ fontWeight: "bold" }}>
//         Healthflow AI
//       </Typography>
//       <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 480 }}>
//         Smart hospital wait time recommendations with AI.
//       </Typography>

//       <Box sx={{ display: "flex", gap: 2 }}>
//         <Button variant="contained" size="large" onClick={() => navigate("/patient")}>
//           👩‍⚕️ I am a Patient
//         </Button>
//         <Button variant="outlined" size="large" onClick={() => navigate("/dashboard")}>
//           🏥 I work at a Hospital
//         </Button>
//       </Box>
//     </Box>
//   );
// }
