import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('./views/LandingPage.vue'),
  },
  {
    path: '/demo/:scenario',
    name: 'Demo',
    component: () => import('./views/DemoPlayer.vue'),
    props: true,
  },
  {
    path: '/modes',
    name: 'Modes',
    component: () => import('./views/ModeGallery.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
