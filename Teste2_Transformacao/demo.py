import pandas as pd
import random
from pathlib import Path

# Cria diretórios
Path("output").mkdir(exist_ok=True)

print("="*60)
print("DEMONSTRAÇÃO - TESTE 2")
print("="*60)

# Gera dados simulados similares aos do Teste 1
data = []
# Exemplos de CNPJs (válidos, inválidos e repetidos)
cnpjs_exemplos = [
    "12345678000195",  
    "98765432000196",  
    "11223344000155",   
    "12345678000190",  
    "123456",          
    "11111111111111",  
]

razoes = [
    # Razões sociais válidas e inválidas
    "Operadora Saúde Plus",
    "MedCare Assistência",
    "Vida Plena Saúde",
    "N/A",  
    "",
]

for ano, tri in [('2024', '03'), ('2024', '02'), ('2024', '01')]:
    # Gera 50 registros por trimestre (150 no total)
    for i in range(50):  
        cnpj = random.choice(cnpjs_exemplos)
        razao = random.choice(razoes)
        # Gera valores variados, incluindo negativos e zeros
        valor = random.choice([
            random.uniform(10000, 500000),  
            0,                               
            -random.uniform(1000, 50000),   
        ])
        
        # Adiciona o registro
        data.append({
            'CNPJ': cnpj,
            'RazaoSocial': razao,
            'Trimestre': tri,
            'Ano': ano,
            'ValorDespesas': valor,
            'StatusValidacao': 'RAZAO_VAZIA' if razao in ['N/A', ''] else 'OK'
        })

df = pd.DataFrame(data)

# Salva CSV simulado
csv_path = Path("output/consolidado_despesas_demo.csv")
df.to_csv(csv_path, index=False, encoding='utf-8')

print(f"\n✓ Gerados {len(df)} registros de demonstração")
print(f"✓ CSV salvo: {csv_path}")
print(f"\nEstatísticas:")
print(f"  CNPJs únicos: {df['CNPJ'].nunique()}")
print(f"  Trimestres: {df['Trimestre'].nunique()}")
print(f"  Valores válidos: {(df['ValorDespesas'] > 0).sum()}")
print(f"  Razões vazias: {df['RazaoSocial'].isin(['N/A', '']).sum()}")

print("\nPrimeiros registros:")
print(df.head(10).to_string(index=False))

print("\n" + "="*60)
print("AGORA EXECUTE: python main.py")
print("(Ajuste o caminho no main.py para usar este CSV demo)")
print("="*60)
