import pandas as pd
import zipfile
import random
from pathlib import Path

# Cria diretórios
Path("output").mkdir(exist_ok=True)

print("="*60)
print("DEMONSTRAÇÃO - TESTE 1")
print("="*60)

# Gera dados simulados
data = []
operadoras = [
    ("12345678000190", "Operadora Saúde Plus"),
    ("98765432000111", "MedCare Assistência"),
    ("11223344000155", "Vida Plena Saúde"),
    ("12345678000190", "Operadora Saúde Plus Ltda"),  # Duplicado
    ("1234567", "CNPJ Inválido"),  # CNPJ inválido
]

for ano, tri in [('2024', '03'), ('2024', '02'), ('2024', '01')]:
    for cnpj, razao in operadoras:
        valor = random.choice([
            random.uniform(10000, 500000),  # Normal
            0,  # Zerado
            -random.uniform(1000, 50000),  # Negativo
        ])
        data.append({
            'CNPJ': cnpj,
            'RazaoSocial': razao,
            'Trimestre': tri,
            'Ano': ano,
            'ValorDespesas': valor,
            'StatusValidacao': 'PENDENTE'
        })

df = pd.DataFrame(data)

# Validação
df['CNPJ'] = df['CNPJ'].str.replace(r'\D', '', regex=True)
df['StatusValidacao'] = 'OK'

# Aplica validações
df.loc[df['CNPJ'].str.len() != 14, 'StatusValidacao'] = 'CNPJ_INVALIDO'
df.loc[df['ValorDespesas'] == 0, 'StatusValidacao'] = 'VALOR_ZERADO'
df.loc[df['ValorDespesas'] < 0, 'StatusValidacao'] = 'VALOR_NEGATIVO'

duplicados = df.groupby('CNPJ')['RazaoSocial'].nunique()
cnpjs_dup = duplicados[duplicados > 1].index
df.loc[df['CNPJ'].isin(cnpjs_dup), 'StatusValidacao'] = 'CNPJ_MULTIPLAS_RAZOES'

# Salva
csv_path = Path("output/consolidado_despesas.csv")
df.to_csv(csv_path, index=False, encoding='utf-8')

zip_path = Path("output/consolidado_despesas.zip")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(csv_path, csv_path.name)

print(f"\n✓ Gerados {len(df)} registros")
print(f"✓ CSV: {csv_path}")
print(f"✓ ZIP: {zip_path}")
print(f"\nResumo:")
print(f"  OK: {(df['StatusValidacao'] == 'OK').sum()}")
print(f"  Problemas: {(df['StatusValidacao'] != 'OK').sum()}")
print("\n" + df.head(10).to_string(index=False))
