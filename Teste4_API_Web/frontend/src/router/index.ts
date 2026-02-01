import { createRouter, createWebHistory } from "vue-router";
import HomePage from "@/views/HomePage.vue";
import DetalhesOperadora from "@/views/DetalhesOperadora.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomePage,
    },
    {
      path: "/operadora/:cnpj",
      name: "detalhes",
      component: DetalhesOperadora,
    },
  ],
});

export default router;
