import { ref, reactive } from "vue";

const loading = ref(false);
const error = reactive<{ message: string | null; type: "error" | "warning" | null }>({
  message: null,
  type: null,
});

let errorTimeout: number | null = null;

export function useUI() {
  const setLoading = (value: boolean) => {
    loading.value = value;
  };

  const clearError = () => {
    if (errorTimeout) {
      clearTimeout(errorTimeout);
      errorTimeout = null;
    }
    error.message = null;
    error.type = null;
  };

  const setError = (message: string | null, type: "error" | "warning" | null = "error") => {
    clearError();

    if (message) {
      error.message = message;
      error.type = type;

      errorTimeout = window.setTimeout(() => {
        clearError();
      }, 5000);
    }
  };

  return {
    loading,
    error,
    setLoading,
    setError,
    clearError,
  };
}
