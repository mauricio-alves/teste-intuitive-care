// Formata número como moeda brasileira
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

// Formata CNPJ (14 dígitos)
export function formatCNPJ(cnpj: string): string {
  if (!cnpj) return "";

  const cleaned = cnpj.replace(/\D/g, "");

  if (cleaned.length !== 14) return cnpj;

  return cleaned.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
}

export const formatLargeNumber = (value: number | null | undefined): string => {
  const safeValue = value ?? 0;

  const formatOptions = {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  };

  if (safeValue >= 1_000_000_000) {
    return `${(safeValue / 1_000_000_000).toLocaleString("pt-BR", formatOptions)}B`;
  }

  if (safeValue >= 1_000_000) {
    return `${(safeValue / 1_000_000).toLocaleString("pt-BR", formatOptions)}M`;
  }

  if (safeValue >= 1_000) {
    return `${(safeValue / 1_000).toLocaleString("pt-BR", formatOptions)}K`;
  }

  return safeValue.toLocaleString("pt-BR", formatOptions);
};

// Debounce para busca
export function debounce<T extends (...args: any[]) => any>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return function (this: any, ...args: Parameters<T>) {
    const context = this;

    if (timeout) clearTimeout(timeout);

    timeout = setTimeout(() => {
      func.apply(context, args);
    }, wait);
  };
}
