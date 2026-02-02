<template>
  <div class="app-container">
    <div v-if="loading" class="global-loader-container">
      <div class="global-loader"></div>
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

.global-loader-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  margin: 1rem;
  border-radius: 4px;
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 10000;
  min-width: 300px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.global-alert.error {
  background-color: #fee2e2;
  color: #991b1b;
  border: 1px solid #f87171;
}
.global-alert.warning {
  background-color: #fef3c7;
  color: #92400e;
  border: 1px solid #fbbf24;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.error {
  background-color: #ff5252;
}
.warning {
  background-color: #fb8c00;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: inherit;
  padding: 0 0.5rem;
  line-height: 1;
  margin-left: 1rem;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.close-btn:hover {
  opacity: 1;
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
