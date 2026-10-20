import { Navigate, type RouteObject } from 'react-router'
import { LoadingState } from '../components/common/States'
import { AppLayout } from '../components/layout/AppLayout'
import { RequireAuth } from '../components/layout/RequireAuth'

// Cada tela vira um chunk próprio; o player e o renderer de Markdown só carregam na tela de resultado.
export const routes: RouteObject[] = [
  { path: '/login', lazy: () => import('../pages/LoginPage').then((module) => ({ Component: module.LoginPage })) },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        hydrateFallbackElement: <LoadingState />,
        children: [
          { index: true, element: <Navigate to="/videos" replace /> },
          {
            path: '/videos',
            lazy: () => import('../pages/VideosPage').then((module) => ({ Component: module.VideosPage })),
          },
          {
            path: '/videos/new',
            lazy: () => import('../pages/UploadPage').then((module) => ({ Component: module.UploadPage })),
          },
          {
            path: '/videos/:videoId',
            lazy: () => import('../pages/VideoPage').then((module) => ({ Component: module.VideoPage })),
          },
          {
            path: '/jobs/:jobId',
            lazy: () => import('../pages/JobPage').then((module) => ({ Component: module.JobPage })),
          },
          {
            path: '/jobs/:jobId/result',
            lazy: () => import('../pages/ResultPage').then((module) => ({ Component: module.ResultPage })),
          },
          {
            path: '*',
            lazy: () => import('../pages/NotFoundPage').then((module) => ({ Component: module.NotFoundPage })),
          },
        ],
      },
    ],
  },
]
