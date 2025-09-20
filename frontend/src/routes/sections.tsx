// routes/sections.tsx
import type { RouteObject } from 'react-router';
import { lazy, Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import Box from '@mui/material/Box';
import LinearProgress, { linearProgressClasses } from '@mui/material/LinearProgress';
import { varAlpha } from 'minimal-shared/utils';

import { AuthLayout } from 'src/layouts/auth';
import { DashboardLayout } from 'src/layouts/dashboard';

// ----------------------------------------------------------------------

export const LandingPage = lazy(() => import('src/pages/homepage'));
export const PatientPage = lazy(() => import('src/pages/patient')); // 👈 new
export const HospitalFreePage = lazy(() => import('src/pages/hospital/free')); // 👈 new
export const DashboardPage = lazy(() => import('src/pages/dashboard')); // paid hospital
export const BlogPage = lazy(() => import('src/pages/blog'));
export const UserPage = lazy(() => import('src/pages/user'));
export const SignInPage = lazy(() => import('src/pages/sign-in'));
export const ProductsPage = lazy(() => import('src/pages/products'));
export const Page404 = lazy(() => import('src/pages/page-not-found'));

const renderFallback = () => (
  <Box
    sx={{
      display: 'flex',
      flex: '1 1 auto',
      alignItems: 'center',
      justifyContent: 'center',
    }}
  >
    <LinearProgress
      sx={{
        width: 1,
        maxWidth: 320,
        bgcolor: (theme) => varAlpha(theme.vars.palette.text.primaryChannel, 0.16),
        [`& .${linearProgressClasses.bar}`]: { bgcolor: 'text.primary' },
      }}
    />
  </Box>
);

export const routesSection: RouteObject[] = [
  {
    index: true, // 👈 Landing page as root
    element: (
      <Suspense fallback={renderFallback()}>
        <LandingPage />
      </Suspense>
    ),
  },
  // Free branch for patients
  {
    path: 'patient',
    element: (
      <Suspense fallback={renderFallback()}>
        <PatientPage />
      </Suspense>
    ),
  },
  // Free branch for hospitals
  {
    path: 'hospital',
    element: (
      <Suspense fallback={renderFallback()}>
        <HospitalFreePage />
      </Suspense>
    ),
  },
  // Paid hospital dashboard (behind DashboardLayout)
  {
    path: 'hospital-dashboard',
    element: (
      <DashboardLayout>
        <Suspense fallback={renderFallback()}>
          <DashboardPage />
        </Suspense>
      </DashboardLayout>
    ),
  },
  {
    path: 'sign-in',
    element: (
      <AuthLayout>
        <SignInPage />
      </AuthLayout>
    ),
  },
  {
    path: '404',
    element: <Page404 />,
  },
  { path: '*', element: <Page404 /> },
];








// import type { RouteObject } from 'react-router';

// import { lazy, Suspense } from 'react';
// import { Outlet } from 'react-router-dom';
// import { varAlpha } from 'minimal-shared/utils';

// import Box from '@mui/material/Box';
// import LinearProgress, { linearProgressClasses } from '@mui/material/LinearProgress';

// import { AuthLayout } from 'src/layouts/auth';
// import { DashboardLayout } from 'src/layouts/dashboard';

// // ----------------------------------------------------------------------

// export const DashboardPage = lazy(() => import('src/pages/dashboard'));
// export const BlogPage = lazy(() => import('src/pages/blog'));
// export const UserPage = lazy(() => import('src/pages/user'));
// export const SignInPage = lazy(() => import('src/pages/sign-in'));
// export const ProductsPage = lazy(() => import('src/pages/products'));
// export const Page404 = lazy(() => import('src/pages/page-not-found'));

// const renderFallback = () => (
//   <Box
//     sx={{
//       display: 'flex',
//       flex: '1 1 auto',
//       alignItems: 'center',
//       justifyContent: 'center',
//     }}
//   >
//     <LinearProgress
//       sx={{
//         width: 1,
//         maxWidth: 320,
//         bgcolor: (theme) => varAlpha(theme.vars.palette.text.primaryChannel, 0.16),
//         [`& .${linearProgressClasses.bar}`]: { bgcolor: 'text.primary' },
//       }}
//     />
//   </Box>
// );

// export const routesSection: RouteObject[] = [
//   {
//     element: (
//       <DashboardLayout>
//         <Suspense fallback={renderFallback()}>
//           <Outlet />
//         </Suspense>
//       </DashboardLayout>
//     ),
//     children: [
//       { index: true, element: <DashboardPage /> },
//       { path: 'user', element: <UserPage /> },
//       { path: 'products', element: <ProductsPage /> },
//       { path: 'blog', element: <BlogPage /> },
//     ],
//   },
//   {
//     path: 'sign-in',
//     element: (
//       <AuthLayout>
//         <SignInPage />
//       </AuthLayout>
//     ),
//   },
//   {
//     path: '404',
//     element: <Page404 />,
//   },
//   { path: '*', element: <Page404 /> },
// ];
