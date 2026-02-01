import { ref, reactive } from "vue";

const loading = ref(false);
const error = reactive<{ message: string | null; type: "error" | "warning" | null }>({
  message: null,
  type: null,
});

export function useUI() {
  const setLoading = (value: boolean) => {
    loading.value = value;
  };

  const setError = (message: string | null, type: "error" | "warning" | null = "error") => {
    error.message = message;
    error.type = type;

    if (message) {
      setTimeout(() => {
        error.message = null;
        error.type = null;
      }, 5000);
    }
  };

  return {
    loading,
    error,
    setLoading,
    setError,
  };
}
