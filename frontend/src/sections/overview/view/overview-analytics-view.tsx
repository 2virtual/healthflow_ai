/* eslint-disable perfectionist/sort-imports */
import React, { useState, useEffect } from 'react';

import axios from 'axios';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';

import { DashboardContent } from 'src/layouts/dashboard';
import { AnalyticsWidgetSummary } from '../analytics-widget-summary';

// ----------------------------------------------------------------------

// CSV Upload Modal
function CSVUploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Upload CSV</DialogTitle>
      <DialogContent>
        <input type="file" accept=".csv" />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={onClose}>
          Upload
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// Hospital Detail Modal
function HospitalDetailModal({
  open,
  onClose,
  hospital,
}: {
  open: boolean;
  onClose: () => void;
  hospital: any;
}) {
  if (!hospital) return null;
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{hospital.name}</DialogTitle>
      <DialogContent>
        <Typography>Region: {hospital.region}</Typography>
        <Typography>Category: {hospital.category}</Typography>
        <Typography>Wait Time: {hospital.wait_time ?? '-'} mins</Typography>
        <Typography>Note: {hospital.note ?? '-'}</Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

// ----------------------------------------------------------------------

export function OverviewAnalyticsView() {
  const [csvOpen, setCsvOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedHospital, setSelectedHospital] = useState<any>(null);

  // State for wait times
  const [waitTimes, setWaitTimes] = useState<any[]>([]);
  const [loadingWaitTimes, setLoadingWaitTimes] = useState(true);
  const [selectedRegion, setSelectedRegion] = useState('All');

  // Mock KPIs (replace later with API if needed)
  const [patients] = useState(1023);
  const [appointments] = useState(345);
  const [doctors] = useState(48);
  const [pendingReports] = useState(27);

  // Fetch wait times from backend
useEffect(() => {
  const fetchWaitTimes = async () => {
    try {
     const res = await axios.get('/api/ed-waits');
      console.log("WaitTimes response:", res.data);
      setWaitTimes(res.data);
    } catch (err) {
      console.error("Failed to fetch wait times:", err);
    } finally {
      setLoadingWaitTimes(false);
    }
  };
  fetchWaitTimes();
}, []);

  // Compute average wait time
  const validWaitTimes = waitTimes
    .map((h) => Number(h.wait_time))
    .filter((n) => !isNaN(n));
  const avgWait =
    validWaitTimes.length > 0
      ? Math.round(validWaitTimes.reduce((acc, n) => acc + n, 0) / validWaitTimes.length)
      : 0;

  // Regions for filter
  const regions = ['All', ...new Set(waitTimes.map((h) => h.region))];

  const filteredWaitTimes =
    selectedRegion === 'All'
      ? waitTimes
      : waitTimes.filter((h) => h.region === selectedRegion);

  // Handle row click
  const handleRowClick = (hospital: any) => {
    setSelectedHospital(hospital);
    setDetailOpen(true);
  };

  return (
    <DashboardContent maxWidth="xl">
      <Typography variant="h4" sx={{ mb: { xs: 3, md: 5 } }}>
        Healthflow - AI
      </Typography>

      <Grid container spacing={3}>
        {/* KPIs */}
        <Grid xs={12} sm={6} md={3}>
          <AnalyticsWidgetSummary title="Patients" total={patients} percent={3.1} color="primary"
            icon={<img alt="Patients" src="/assets/icons/hospital/ic-patient.svg" />}
            chart={{ categories: [], series: [] }}
          />
        </Grid>
        <Grid xs={12} sm={6} md={3}>
          <AnalyticsWidgetSummary title="Appointments" total={appointments} percent={1.8} color="secondary"
            icon={<img alt="Appointments" src="/assets/icons/hospital/ic-appointment.svg" />}
            chart={{ categories: [], series: [] }}
          />
        </Grid>
        <Grid xs={12} sm={6} md={3}>
          <AnalyticsWidgetSummary title="Doctors" total={doctors} percent={0.5} color="success"
            icon={<img alt="Doctors" src="/assets/icons/hospital/ic-doctor.svg" />}
            chart={{ categories: [], series: [] }}
          />
        </Grid>
        <Grid xs={12} sm={6} md={3}>
          <AnalyticsWidgetSummary title="Pending Reports" total={pendingReports} percent={-1.2} color="error"
            icon={<img alt="Reports" src="/assets/icons/hospital/ic-report.svg" />}
            chart={{ categories: [], series: [] }}
          />
        </Grid>
        <Grid xs={12} sm={6} md={3}>
          <AnalyticsWidgetSummary
            title="Avg ED Wait Time (mins)"
            total={loadingWaitTimes ? 0 : avgWait}
            percent={0.0}
            color="warning"
            icon={<img alt="Wait Time" src="/assets/icons/hospital/ic-clock.svg" />}
            chart={{ categories: [], series: [] }}
          />
        </Grid>

        {/* Wait Times Table */}
        <Grid xs={12}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Alberta Hospital ED Wait Times
          </Typography>

          {loadingWaitTimes ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              <Select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                sx={{ mb: 2, minWidth: 200 }}
              >
                {regions.map((region) => (
                  <MenuItem key={region} value={region}>
                    {region}
                  </MenuItem>
                ))}
              </Select>

              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Hospital Name</TableCell>
                    <TableCell>Region</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Wait Time (mins)</TableCell>
                    <TableCell>Note</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredWaitTimes.map((hospital, idx) => (
                    <TableRow
                      key={idx}
                      hover
                      sx={{ cursor: 'pointer' }}
                      onClick={() => handleRowClick(hospital)}
                    >
                      <TableCell>{hospital.name}</TableCell>
                      <TableCell>{hospital.region}</TableCell>
                      <TableCell>{hospital.category}</TableCell>
                      <TableCell>{hospital.wait_time ?? '-'}</TableCell>
                      <TableCell>{hospital.note ?? '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </>
          )}

          <Button variant="outlined" sx={{ mt: 2 }} onClick={() => setCsvOpen(true)}>
            Upload CSV
          </Button>
        </Grid>
      </Grid>

      {/* Modals */}
      <CSVUploadModal open={csvOpen} onClose={() => setCsvOpen(false)} />
      <HospitalDetailModal open={detailOpen} onClose={() => setDetailOpen(false)} hospital={selectedHospital} />
    </DashboardContent>
  );
}








// import React, { useState } from 'react';
// import Grid from '@mui/material/Grid';
// import Typography from '@mui/material/Typography';
// import Button from '@mui/material/Button';
// import Dialog from '@mui/material/Dialog';
// import DialogTitle from '@mui/material/DialogTitle';
// import DialogContent from '@mui/material/DialogContent';
// import DialogActions from '@mui/material/DialogActions';
// import Table from '@mui/material/Table';
// import TableBody from '@mui/material/TableBody';
// import TableCell from '@mui/material/TableCell';
// import TableHead from '@mui/material/TableHead';
// import TableRow from '@mui/material/TableRow';
// import Select from '@mui/material/Select';
// import MenuItem from '@mui/material/MenuItem';

// import { DashboardContent } from 'src/layouts/dashboard';
// import { AnalyticsWidgetSummary } from '../analytics-widget-summary';

// // ----------------------------------------------------------------------

// const mockHospitals = [
//   { id: 1, name: 'Lagos General Hospital', region: 'West', waitTime: 45 },
//   { id: 2, name: 'Abuja Teaching Hospital', region: 'North', waitTime: 30 },
//   { id: 3, name: 'Enugu Specialist Hospital', region: 'East', waitTime: 55 },
// ];

// // CSV Upload Modal
// function CSVUploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
//   return (
//     <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
//       <DialogTitle>Upload CSV</DialogTitle>
//       <DialogContent>
//         <input type="file" accept=".csv" />
//       </DialogContent>
//       <DialogActions>
//         <Button onClick={onClose}>Cancel</Button>
//         <Button variant="contained" onClick={onClose}>Upload</Button>
//       </DialogActions>
//     </Dialog>
//   );
// }

// // Hospital Detail Modal
// function HospitalDetailModal({ open, onClose, hospital }: { open: boolean; onClose: () => void; hospital: any }) {
//   if (!hospital) return null;
//   return (
//     <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
//       <DialogTitle>{hospital.name}</DialogTitle>
//       <DialogContent>
//         <Typography>Region: {hospital.region}</Typography>
//         <Typography>Average Wait Time: {hospital.waitTime} mins</Typography>
//         <Typography>Additional hospital details go here...</Typography>
//       </DialogContent>
//       <DialogActions>
//         <Button onClick={onClose}>Close</Button>
//       </DialogActions>
//     </Dialog>
//   );
// }

// // Wait Times Table with region filter
// function HospitalWaitTimesTable({ onRowClick }: { onRowClick: (hospital: any) => void }) {
//   const [region, setRegion] = useState('All');

//   const filtered = region === 'All' ? mockHospitals : mockHospitals.filter((h) => h.region === region);

//   return (
//     <>
//       <Typography variant="h6" sx={{ mb: 2 }}>
//         Wait Times by Region
//       </Typography>
//       <Select value={region} onChange={(e) => setRegion(e.target.value)} sx={{ mb: 2 }}>
//         <MenuItem value="All">All</MenuItem>
//         <MenuItem value="North">North</MenuItem>
//         <MenuItem value="South">South</MenuItem>
//         <MenuItem value="East">East</MenuItem>
//         <MenuItem value="West">West</MenuItem>
//       </Select>
//       <Table>
//         <TableHead>
//           <TableRow>
//             <TableCell>Hospital</TableCell>
//             <TableCell>Region</TableCell>
//             <TableCell>Avg Wait Time (mins)</TableCell>
//           </TableRow>
//         </TableHead>
//         <TableBody>
//           {filtered.map((h) => (
//             <TableRow key={h.id} hover sx={{ cursor: 'pointer' }} onClick={() => onRowClick(h)}>
//               <TableCell>{h.name}</TableCell>
//               <TableCell>{h.region}</TableCell>
//               <TableCell>{h.waitTime}</TableCell>
//             </TableRow>
//           ))}
//         </TableBody>
//       </Table>
//     </>
//   );
// }

// // ----------------------------------------------------------------------

// export function OverviewAnalyticsView() {
//   const [csvOpen, setCsvOpen] = useState(false);
//   const [detailOpen, setDetailOpen] = useState(false);
//   const [selectedHospital, setSelectedHospital] = useState<any>(null);

//   const handleRowClick = (hospital: any) => {
//     setSelectedHospital(hospital);
//     setDetailOpen(true);
//   };

//   return (
//     <DashboardContent maxWidth="xl">
//       <Typography variant="h4" sx={{ mb: { xs: 3, md: 5 } }}>
//         Healthflow - AI
//       </Typography>

//       <Grid container spacing={3}>
//         {/* KPIs */}
//         <Grid xs={12} sm={6} md={3}>
//           <AnalyticsWidgetSummary title="Patients" total={1023} percent={3.1} color="primary"
//             icon={<img alt="Patients" src="/assets/icons/hospital/ic-patient.svg" />}
//             chart={{ categories: [], series: [] }}
//           />
//         </Grid>
//         <Grid xs={12} sm={6} md={3}>
//           <AnalyticsWidgetSummary title="Appointments" total={345} percent={1.8} color="secondary"
//             icon={<img alt="Appointments" src="/assets/icons/hospital/ic-appointment.svg" />}
//             chart={{ categories: [], series: [] }}
//           />
//         </Grid>
//         <Grid xs={12} sm={6} md={3}>
//           <AnalyticsWidgetSummary title="Doctors" total={48} percent={0.5} color="success"
//             icon={<img alt="Doctors" src="/assets/icons/hospital/ic-doctor.svg" />}
//             chart={{ categories: [], series: [] }}
//           />
//         </Grid>
//         <Grid xs={12} sm={6} md={3}>
//           <AnalyticsWidgetSummary title="Pending Reports" total={27} percent={-1.2} color="error"
//             icon={<img alt="Reports" src="/assets/icons/hospital/ic-report.svg" />}
//             chart={{ categories: [], series: [] }}
//           />
//         </Grid>

//         {/* Wait Times Table */}
//         <Grid xs={12}>
//           <HospitalWaitTimesTable onRowClick={handleRowClick} />
//           <Button variant="outlined" sx={{ mt: 2 }} onClick={() => setCsvOpen(true)}>
//             Upload CSV
//           </Button>
//         </Grid>
//       </Grid>

//       {/* Modals */}
//       <CSVUploadModal open={csvOpen} onClose={() => setCsvOpen(false)} />
//       <HospitalDetailModal open={detailOpen} onClose={() => setDetailOpen(false)} hospital={selectedHospital} />
//     </DashboardContent>
//   );
// }













// import Grid from '@mui/material/Grid';
// import Typography from '@mui/material/Typography';

// import { DashboardContent } from 'src/layouts/dashboard';
// import { _posts, _tasks, _traffic, _timeline } from 'src/_mock';

// import { AnalyticsNews } from '../analytics-news';
// import { AnalyticsTasks } from '../analytics-tasks';
// import { AnalyticsCurrentVisits } from '../analytics-current-visits';
// import { AnalyticsOrderTimeline } from '../analytics-order-timeline';
// import { AnalyticsWebsiteVisits } from '../analytics-website-visits';
// import { AnalyticsWidgetSummary } from '../analytics-widget-summary';
// import { AnalyticsTrafficBySite } from '../analytics-traffic-by-site';
// import { AnalyticsCurrentSubject } from '../analytics-current-subject';
// import { AnalyticsConversionRates } from '../analytics-conversion-rates';

// // ----------------------------------------------------------------------

// export function OverviewAnalyticsView() {
//   return (
//     <DashboardContent maxWidth="xl">
//       <Typography variant="h4" sx={{ mb: { xs: 3, md: 5 } }}>
//         Healthflow - AI
//       </Typography>

//       <Grid container spacing={3}>
//         <Grid size={{ xs: 12, sm: 6, md: 3 }}>
//           <AnalyticsWidgetSummary
//             title="Weekly sales"
//             percent={2.6}
//             total={714000}
//             icon={<img alt="Weekly sales" src="/assets/icons/glass/ic-glass-bag.svg" />}
//             chart={{
//               categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'],
//               series: [22, 8, 35, 50, 82, 84, 77, 12],
//             }}
//           />
//         </Grid>

//         <Grid size={{ xs: 12, sm: 6, md: 3 }}>
//           <AnalyticsWidgetSummary
//             title="New users"
//             percent={-0.1}
//             total={1352831}
//             color="secondary"
//             icon={<img alt="New users" src="/assets/icons/glass/ic-glass-users.svg" />}
//             chart={{
//               categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'],
//               series: [56, 47, 40, 62, 73, 30, 23, 54],
//             }}
//           />
//         </Grid>

//         <Grid size={{ xs: 12, sm: 6, md: 3 }}>
//           <AnalyticsWidgetSummary
//             title="Purchase orders"
//             percent={2.8}
//             total={1723315}
//             color="warning"
//             icon={<img alt="Purchase orders" src="/assets/icons/glass/ic-glass-buy.svg" />}
//             chart={{
//               categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'],
//               series: [40, 70, 50, 28, 70, 75, 7, 64],
//             }}
//           />
//         </Grid>

//         <Grid size={{ xs: 12, sm: 6, md: 3 }}>
//           <AnalyticsWidgetSummary
//             title="Messages"
//             percent={3.6}
//             total={234}
//             color="error"
//             icon={<img alt="Messages" src="/assets/icons/glass/ic-glass-message.svg" />}
//             chart={{
//               categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'],
//               series: [56, 30, 23, 54, 47, 40, 62, 73],
//             }}
//           />
//         </Grid>

//         <Grid size={{ xs: 12, md: 6, lg: 4 }}>
//           <AnalyticsCurrentVisits
//             title="Current visits"
//             chart={{
//               series: [
//                 { label: 'America', value: 3500 },
//                 { label: 'Asia', value: 2500 },
//                 { label: 'Europe', value: 1500 },
//                 { label: 'Africa', value: 500 },
//               ],
//             }}
//           />
//         </Grid>

//         <Grid size={{ xs: 12, md: 6, lg: 8 }}>
//           <AnalyticsWebsiteVisits
//             title="Website visits"
//             subheader="(+43%) than last year"
//             chart={{
//               categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'],
//               series: [
//                 { name: 'Team A', data: [43, 33, 22, 37, 67, 68, 37, 24, 55] },
//                 { name: 'Team B', data: [51, 70, 47, 67, 40, 37, 24, 70, 24] },
//               ],
//             }}
//           />
//         </Grid>

//         <Grid size={{ xs: 12, md: 6, lg: 8 }}>
//           <AnalyticsConversionRates
//             title="Conversion rates"
//             subheader="(+43%) than last year"
//             chart={{
//               categories: ['Italy', 'Japan', 'China', 'Canada', 'France'],
//               series: [
//                 { name: '2022', data: [44, 55, 41, 64, 22] },
//                 { name: '2023', data: [53, 32, 33, 52, 13] },
//               ],
//             }}
//           />
//         </Grid>

//         <Grid size={{ xs: 12, md: 6, lg: 4 }}>
//           <AnalyticsCurrentSubject
//             title="Current subject"
//             chart={{
//               categories: ['English', 'History', 'Physics', 'Geography', 'Chinese', 'Math'],
//               series: [
//                 { name: 'Series 1', data: [80, 50, 30, 40, 100, 20] },
//                 { name: 'Series 2', data: [20, 30, 40, 80, 20, 80] },
//                 { name: 'Series 3', data: [44, 76, 78, 13, 43, 10] },
//               ],
//             }}
//           />
//         </Grid>

//         <Grid size={{ xs: 12, md: 6, lg: 8 }}>
//           <AnalyticsNews title="News" list={_posts.slice(0, 5)} />
//         </Grid>

//         <Grid size={{ xs: 12, md: 6, lg: 4 }}>
//           <AnalyticsOrderTimeline title="Order timeline" list={_timeline} />
//         </Grid>

//         <Grid size={{ xs: 12, md: 6, lg: 4 }}>
//           <AnalyticsTrafficBySite title="Traffic by site" list={_traffic} />
//         </Grid>

//         <Grid size={{ xs: 12, md: 6, lg: 8 }}>
//           <AnalyticsTasks title="Tasks" list={_tasks} />
//         </Grid>
//       </Grid>
//     </DashboardContent>
//   );
// }
