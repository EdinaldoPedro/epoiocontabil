# gerador_contracheque.py

def calcular_inss_2025(bruto):
    # Tabela progressiva 2025 (Estimada/Baseada no script anterior)
    faixas = [
        (1518.00, 0.075), # Salário mínimo ajustado provável
        (2793.88, 0.09),
        (4190.83, 0.12),
        (8157.41, 0.14)   # Teto estimado
    ]
    desconto = 0
    faixa_anterior = 0
    
    for teto, aliquota in faixas:
        if bruto > faixa_anterior:
            base_calculo = min(bruto, teto) - faixa_anterior
            desconto += base_calculo * aliquota
            faixa_anterior = teto
        else:
            break
            
    # Teto máximo de desconto (estimado)
    teto_inss = 951.63 
    if desconto > teto_inss:
        return teto_inss
        
    return round(desconto, 2)

def calcular_irrf_2025(base_legal, dependentes):
    deducao_dep = dependentes * 189.59
    base_calculo = base_legal - deducao_dep
    
    # Tabela IRRF (Vigente)
    if base_calculo <= 2259.20: return 0.00, 0.00
    elif base_calculo <= 2826.65: return (base_calculo * 0.075) - 169.44, 7.5
    elif base_calculo <= 3751.05: return (base_calculo * 0.15) - 381.44, 15.0
    elif base_calculo <= 4664.68: return (base_calculo * 0.225) - 662.77, 22.5
    else: return (base_calculo * 0.275) - 896.00, 27.5

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
    base_irrf_bruta = 0

    # 1. Processar Salário Base
    itens_processados.append({
        "cod": 101, "desc": "SALARIO BASE", "ref": 30, "tipo": "V", "valor": salario_base
    })
    total_vencimentos += salario_base
    base_inss += salario_base
    base_fgts += salario_base
    base_irrf_bruta += salario_base

    # 2. Processar Outros Proventos (Adicionais)
    # Assumindo para o simulador simples que proventos extras incidem impostos
    # Para maior complexidade, o front teria que enviar flags de incidência
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

    # 3. Calcular INSS
    val_inss = calcular_inss_2025(base_inss)
    if val_inss > 0:
        itens_processados.append({
            "cod": 903, "desc": "INSS FOLHA", "ref": "", "tipo": "D", "valor": val_inss
        })
        total_descontos += val_inss

    # 4. Calcular IRRF
    base_irrf_liquida = base_irrf_bruta - val_inss
    val_irrf, aliquota_ir = calcular_irrf_2025(base_irrf_liquida, dependentes)
    
    if val_irrf > 0:
        itens_processados.append({
            "cod": 904, 
            "desc": "IRRF FOLHA", 
            "ref": f"{aliquota_ir}%", 
            "tipo": "D", 
            "valor": val_irrf
        })
        total_descontos += val_irrf

    # 5. Processar Outros Descontos (Manual)
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