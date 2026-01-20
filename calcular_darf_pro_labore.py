import json

# ==============================================================================
#  CONSTANTES ATUALIZADAS 2026
# ==============================================================================

# Tabela progressiva IRRF 2026 (Vigência Jan/2026)
TABELA_IRPF = [
    (2428.80, 0.0, 0.0),
    (2826.65, 0.075, 182.16),
    (3751.05, 0.15, 394.16),
    (4664.68, 0.225, 675.49),
    (float('inf'), 0.275, 908.73),
]

PISO_PRO_LABORE = 1621.00   # Salário Mínimo 2026
PERCENTUAL_FATOR_R = 0.28   # Meta de 28% do faturamento

# INSS Contribuinte Individual (Sócio) geralmente é 11%
ALIQUOTA_INSS = 0.11
TETO_INSS = 8475.55         # Teto INSS 2026
INSS_MAXIMO = TETO_INSS * ALIQUOTA_INSS


def calcular_irrf_2026(base_calculo, rendimento_bruto):
    """
    Calcula o IRRF com as regras de 2026:
    - Tabela progressiva atualizada.
    - Isenção para quem ganha até R$ 5.000,00 (bruto).
    - Redutor gradual para quem ganha até R$ 7.350,00 (bruto).
    """
    # 1. Cálculo padrão pela tabela (sobre a base líquida)
    darf_irpf = 0.0
    for limite, aliquota, deducao in TABELA_IRPF:
        if base_calculo <= limite:
            darf_irpf = (base_calculo * aliquota) - deducao
            break
    
    darf_irpf = max(0.0, darf_irpf)

    # 2. Aplicação do Redutor Especial (Baseado no Bruto)
    redutor = 0.0
    
    if rendimento_bruto <= 5000.00:
        # Isenção total para brutos até 5k
        redutor = darf_irpf
    elif rendimento_bruto <= 7350.00:
        # Redutor gradual para brutos até 7.35k
        # Fórmula: R$ 978,62 - (0,133145 * Rendimento Bruto)
        val_redutor = 978.62 - (0.133145 * rendimento_bruto)
        redutor = max(0.0, val_redutor)
        redutor = min(redutor, darf_irpf) # Não pode deduzir mais que o próprio imposto
    
    imposto_final = max(0.0, darf_irpf - redutor)
    return round(imposto_final, 2)


def calcular_darf_pro_labore(dados_json: dict):
    """
    Calcula o pró-labore, INSS e IRPF a partir de um JSON de entrada.
    Recebe dicionário com pelo menos a chave 'faturamento' (mensal).
    Retorna dicionário com chaves curtas e também as chaves verbosas (compatibilidade).
    """
    # Validação simples
    try:
        faturamento_mensal = float(dados_json.get("faturamento", 0))
    except Exception:
        raise ValueError("Campo 'faturamento' inválido ou ausente.")

    if faturamento_mensal <= 0:
        raise ValueError("Campo 'faturamento' deve ser maior que zero.")

    # --- Cálculos ---
    
    # 1. Definição do valor do Pró-labore
    # Busca atingir 28% do faturamento (para Fator R), respeitando o piso
    pro_labore_calculado = faturamento_mensal * PERCENTUAL_FATOR_R
    pro_labore = max(pro_labore_calculado, PISO_PRO_LABORE)

    # 2. INSS (11% limitado ao teto)
    inss_descontado = min(pro_labore * ALIQUOTA_INSS, INSS_MAXIMO)
    
    # 3. Base para IR (Pró-labore - INSS)
    base_calculo_irpf = pro_labore - inss_descontado

    # 4. Cálculo do IRRF (Regras 2026)
    darf_irpf = calcular_irrf_2026(base_calculo_irpf, pro_labore)

    total_a_recolher = inss_descontado + darf_irpf

    # Resultado (dupla representação para segurança e compatibilidade com front)
    resultado = {
        # chaves curtas (recomendadas pro front)
        "pro_labore": round(pro_labore, 2),
        "inss": round(inss_descontado, 2),
        "base_irpf": round(base_calculo_irpf, 2),
        "ir": round(darf_irpf, 2),
        "total_darf": round(total_a_recolher, 2),

        # chaves verbosas originais (compatibilidade com quem já usava esses nomes)
        "Faturamento Mensal": round(faturamento_mensal, 2),
        "Pró-labore (Base de Cálculo)": round(pro_labore, 2),
        "Contribuição INSS (11%)": round(inss_descontado, 2),
        "Base para Cálculo do IRPF": round(base_calculo_irpf, 2),
        "Imposto de Renda (IR)": round(darf_irpf, 2),
        "Total a Recolher (INSS + IR) Darf": round(total_a_recolher, 2),
    }

    return resultado


# Permitindo execução direta para testes
if __name__ == "__main__":
    import sys
    try:
        if len(sys.argv) > 1:
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                dados = json.load(f)
        else:
            texto = input("Cole JSON com faturamento (ex: {\"faturamento\":20000}): ").strip()
            texto = texto.replace("'", '"')
            dados = json.loads(texto)
        print(json.dumps(calcular_darf_pro_labore(dados), ensure_ascii=False, indent=2))
    except Exception as e:
        print("Erro:", e)
        sys.exit(1)