# gerador_contracheque.py

def calcular_inss_2026(bruto):
    """
    Calcula o INSS com base na Tabela Progressiva de 2026.
    Salário Mínimo: R$ 1.621,00
    Teto INSS: R$ 8.475,55
    """
    faixas = [
        (1621.00, 0.075),  # 7.5% até o Salário Mínimo
        (2902.84, 0.09),   # 9%
        (4354.27, 0.12),   # 12%
        (8475.55, 0.14)    # 14% até o Teto
    ]
    
    desconto = 0.0
    faixa_anterior = 0.0
    
    # Base de cálculo limitada ao teto
    base_calculo_real = min(bruto, 8475.55)
    
    for limite, aliquota in faixas:
        if base_calculo_real > faixa_anterior:
            base_faixa = min(base_calculo_real, limite) - faixa_anterior
            desconto += base_faixa * aliquota
            faixa_anterior = limite
        else:
            break
            
    return round(desconto, 2)

def calcular_irrf_2026(base_legal, dependentes, rendimento_bruto):
    """
    Calcula o IRRF com as novas regras de 2026 (Redutor Simplificado).
    
    Novidades 2026:
    1. Tabela progressiva reajustada.
    2. 'Isenção' efetiva para quem ganha até R$ 5.000,00 através de um redutor especial.
    3. Redução gradual do imposto para quem ganha entre R$ 5.000,01 e R$ 7.350,00.
    """
    
    # 1. Cálculo Base (Método Tradicional)
    deducao_dep = dependentes * 189.59
    base_calculo = base_legal - deducao_dep
    
    # Tabela Progressiva Mensal 2026 (Baseada na legislação vigente em Jan/2026)
    # Faixas de Base de Cálculo vs Alíquota e Dedução
    imposto_bruto = 0.0
    aliquota_faixa = 0.0
    
    if base_calculo <= 2428.80:
        imposto_bruto = 0.0
        aliquota_faixa = 0.0
    elif base_calculo <= 2826.65:
        imposto_bruto = (base_calculo * 0.075) - 182.16
        aliquota_faixa = 7.5
    elif base_calculo <= 3751.05:
        imposto_bruto = (base_calculo * 0.15) - 394.16
        aliquota_faixa = 15.0
    elif base_calculo <= 4664.68:
        imposto_bruto = (base_calculo * 0.225) - 675.49
        aliquota_faixa = 22.5
    else:
        imposto_bruto = (base_calculo * 0.275) - 908.73
        aliquota_faixa = 27.5
        
    imposto_bruto = max(0.0, imposto_bruto)

    # 2. Aplicação do Redutor Especial 2026
    # Regra: Quem ganha até R$ 5.000,00 de BRUTO fica isento via redutor.
    # Entre R$ 5.000 e R$ 7.350 aplica-se redutor gradual.
    
    redutor = 0.0
    
    if rendimento_bruto <= 5000.00:
        # Zera o imposto
        redutor = imposto_bruto
    elif rendimento_bruto <= 7350.00:
        # Fórmula oficial do redutor gradual
        # R$ 978,62 - (0,133145 * Rendimento Bruto)
        valor_redutor_calculado = 978.62 - (0.133145 * rendimento_bruto)
        
        # O redutor não pode ser negativo e é limitado ao valor do imposto apurado
        redutor = max(0.0, valor_redutor_calculado)
        redutor = min(redutor, imposto_bruto)
    else:
        # Acima de R$ 7.350,00 segue a tabela normal sem redutor especial
        redutor = 0.0
        
    imposto_final = max(0.0, imposto_bruto - redutor)
    
    return round(imposto_final, 2), aliquota_faixa

def processar_holerite_api(dados):
    # Dados de entrada
    salario_base = float(dados.get('salario_base', 0))
    dependentes = int(dados.get('dependentes', 0))
    outros_proventos = dados.get('outros_proventos', []) # Lista de {descricao, valor}
    outros_descontos = dados.get('outros_descontos', []) # Lista de {descricao, valor}

    itens_processados = []
    
    total_vencimentos = 0
    total_descontos = 0
    base_inss = 0
    base_fgts = 0
    base_irrf_bruta = 0 # Rendimento Bruto (usado para o redutor 2026)

    # 1. Processar Salário Base
    itens_processados.append({
        "cod": 101, "desc": "SALARIO BASE", "ref": 30, "tipo": "V", "valor": salario_base
    })
    total_vencimentos += salario_base
    base_inss += salario_base
    base_fgts += salario_base
    base_irrf_bruta += salario_base

    # 2. Processar Outros Proventos (Adicionais)
    cod_counter = 200
    for prov in outros_proventos:
        val = float(prov['valor'])
        if val > 0:
            itens_processados.append({
                "cod": cod_counter, 
                "desc": prov['descricao'].upper(), 
                "ref": "", 
                "tipo": "V", 
                "valor": val
            })
            total_vencimentos += val
            base_inss += val
            base_fgts += val
            base_irrf_bruta += val
            cod_counter += 1

    # 3. Calcular INSS 2026
    val_inss = calcular_inss_2026(base_inss)
    if val_inss > 0:
        # Verifica a alíquota efetiva apenas para exibição
        aliquota_eff_inss = (val_inss / base_inss) * 100 if base_inss > 0 else 0
        itens_processados.append({
            "cod": 903, 
            "desc": "INSS FOLHA (2026)", 
            "ref": f"{aliquota_eff_inss:.1f}%", 
            "tipo": "D", 
            "valor": val_inss
        })
        total_descontos += val_inss

    # 4. Calcular IRRF 2026
    # Base legal tradicional (Bruto - INSS)
    base_irrf_liquida = base_irrf_bruta - val_inss
    
    # Nova função recebe também o Bruto para aplicar a regra de isenção até 5k
    val_irrf, aliquota_ir = calcular_irrf_2026(base_irrf_liquida, dependentes, base_irrf_bruta)
    
    if val_irrf > 0:
        itens_processados.append({
            "cod": 904, 
            "desc": "IRRF FOLHA (2026)", 
            "ref": f"{aliquota_ir}%", 
            "tipo": "D", 
            "valor": val_irrf
        })
        total_descontos += val_irrf

    # 5. Processar Outros Descontos
    cod_desc_counter = 500
    for desc in outros_descontos:
        val = float(desc['valor'])
        if val > 0:
            itens_processados.append({
                "cod": cod_desc_counter, 
                "desc": desc['descricao'].upper(), 
                "ref": "", 
                "tipo": "D", 
                "valor": val
            })
            total_descontos += val
            cod_desc_counter += 1

    # Fechamento
    liquido = total_vencimentos - total_descontos
    fgts_valor = base_fgts * 0.08

    return {
        "itens": itens_processados,
        "totais": {
            "vencimentos": total_vencimentos,
            "descontos": total_descontos,
            "liquido": liquido,
            "bases": {
                "inss": base_inss,
                "fgts": base_fgts,
                "fgts_valor": fgts_valor,
                "irrf": base_irrf_liquida
            }
        }
    }