<template>
  <div class="app-container">
    <div v-if="loading" class="loader-overlay">
      <div class="loader"></div>
    </div>

    <transition name="fade">
      <div v-if="error.message" :class="['global-alert', error.type]" role="alert" aria-live="assertive">
        <span>{{ error.message }}</span>
        <button type="button" class="close-btn" aria-label="Fechar alerta" @click="clearError">&times;</button>
      </div>
    </transition>

    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useUI } from "@/composables/useUI";
const { loading, error, clearError } = useUI();
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: #f5f5f5;
  color: #333;
  line-height: 1.6;
}

#app {
  min-height: 100vh;
}

.global-loader {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: #42b983;
  z-index: 9999;
  animation: loading-bar 2s infinite linear;
}

.global-alert {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 15px 20px;
  border-radius: 8px;
  color: white;
  z-index: 9998;
  display: flex;
  gap: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.error {
  background-color: #ff5252;
}
.warning {
  background-color: #fb8c00;
}

@keyframes loading-bar {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}
</style>
