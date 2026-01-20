import sys
import json
import argparse
import datetime
from calendar import monthrange

# ==============================================================================
#  CONSTANTES ATUALIZADAS 2026
# ==============================================================================

SALARIO_MINIMO_2026 = 1621.00
TETO_INSS_2026 = 8475.55
DEDUCAO_DEPENDENTE_2026 = 189.59

# Tabela INSS 2026 (Estimada com base no novo mínimo)
FAIXAS_INSS_2026 = [
    (1621.00, 0.075),  # 7.5%
    (2902.84, 0.09),   # 9%
    (4354.27, 0.12),   # 12%
    (8475.55, 0.14)    # 14%
]

# Tabela IRRF 2026
# Faixas de Base de Cálculo (Mensal)
TABELA_IRRF_2026 = [
    (2428.80, 0.0, 0.0),
    (2826.65, 0.075, 182.16),
    (3751.05, 0.15, 394.16),
    (4664.68, 0.225, 675.49),
    (float('inf'), 0.275, 908.73)
]

# ==============================================================================
#  FUNÇÕES DE CÁLCULO (Lógica Pura)
# ==============================================================================

def parse_data(data_str):
    """Converte string 'YYYY-MM-DD' para object date."""
    if not data_str:
        return None
    try:
        return datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def calcular_inss_2026(base):
    """
    Calcula INSS com alíquota progressiva (2026).
    """
    base = min(base, TETO_INSS_2026)
    desconto = 0.0
    faixa_anterior = 0.0
    
    for limite, aliquota in FAIXAS_INSS_2026:
        if base > faixa_anterior:
            base_faixa = min(base, limite) - faixa_anterior
            desconto += base_faixa * aliquota
            faixa_anterior = limite
        else:
            break
    
    return round(desconto, 2)


def calcular_irrf_2026(base_legal, dependentes, pensao=0, rendimento_bruto=0):
    """
    Calcula IRRF considerando as regras de 2026.
    - Nova Tabela Progressiva.
    - Isenção para rendimento bruto até R$ 5.000,00.
    - Redutor gradual para rendimento bruto até R$ 7.350,00.
    
    Parâmetros:
      base_legal: Base de cálculo (Bruto - INSS - Dependentes - Pensão)
      dependentes: Número de dependentes
      pensao: Valor da pensão alimentícia
      rendimento_bruto: O valor bruto total (usado para verificar o redutor especial)
    """
    deducao_dep = dependentes * DEDUCAO_DEPENDENTE_2026
    
    # Base de cálculo tradicional
    base_calculo = base_legal - deducao_dep - pensao
    
    if base_calculo <= 0:
        return 0.0

    # 1. Cálculo do Imposto Bruto (Tabela Normal)
    imposto_bruto = 0.0
    for limite, aliquota, deducao in TABELA_IRRF_2026:
        if base_calculo <= limite:
            imposto_bruto = (base_calculo * aliquota) - deducao
            break
            
    imposto_bruto = max(0.0, imposto_bruto)

    # 2. Aplicação do Redutor Especial 2026
    # Regra: Quem ganha até R$ 5.000,00 de BRUTO fica isento via redutor.
    redutor = 0.0
    
    if rendimento_bruto <= 5000.00:
        # Zera o imposto
        redutor = imposto_bruto
    elif rendimento_bruto <= 7350.00:
        # Fórmula do redutor gradual: R$ 978,62 - (0,133145 * Bruto)
        val_redutor = 978.62 - (0.133145 * rendimento_bruto)
        redutor = max(0.0, val_redutor)
        redutor = min(redutor, imposto_bruto) # Redutor não pode ser maior que o imposto
    else:
        redutor = 0.0
        
    imposto_final = max(0.0, imposto_bruto - redutor)
    
    return round(imposto_final, 2)


def calcular_meses_trabalhados(inicio, fim):
    """
    Calcula meses para 13º Salário (baseado em mês civil: 01 a 30/31).
    Conta 1 mês se trabalhou 15 dias ou mais naquele mês.
    """
    meses = 0
    curr = inicio
    
    while curr <= fim:
        ultimo_dia = monthrange(curr.year, curr.month)[1]
        
        # Define início e fim do mês corrente para contagem de dias
        if curr.month == inicio.month and curr.year == inicio.year:
            ini_c = curr.day
        else:
            ini_c = 1
            
        if curr.month == fim.month and curr.year == fim.year:
            fim_c = fim.day
        else:
            fim_c = ultimo_dia

        dias_no_mes = fim_c - ini_c + 1
        if dias_no_mes >= 15:
            meses += 1

        # Avança para o próximo mês
        if curr.month == 12:
            curr = datetime.date(curr.year + 1, 1, 1)
        else:
            curr = datetime.date(curr.year, curr.month + 1, 1)
    
    return meses


def calcular_avos_ferias(inicio_aquisitivo, fim_projetado):
    """
    Calcula avos de férias baseado no período aquisitivo.
    """
    avos = 0
    curr = inicio_aquisitivo

    while True:
        # Calcula a data do próximo "mesversário"
        year = curr.year + ((curr.month + 1) // 13)
        month = (curr.month % 12) + 1

        try:
            next_date = datetime.date(year, month, inicio_aquisitivo.day)
        except ValueError:
            last_day = monthrange(year, month)[1]
            next_date = datetime.date(year, month, last_day)

        # O período fecha um dia antes do próximo aniversário
        periodo_fim = next_date - datetime.timedelta(days=1)

        if periodo_fim <= fim_projetado:
            avos += 1
            curr = next_date
        else:
            # Fração final: Se trabalhou >= 15 dias neste ciclo incompleto
            dias_fracao = (fim_projetado - curr).days + 1
            if dias_fracao >= 15:
                avos += 1
            break

    return min(avos, 12)


def gerar_resumo_texto(tipo):
    """Gera texto explicativo sobre o tipo de rescisão."""
    resumos = {
        1: [
            "Motivo: Demissão sem Justa Causa (Iniciativa da Empresa).",
            "Recebe todas as verbas (Aviso, 13º, Férias).",
            "Saque FGTS + Multa de 40%.",
            "Direito ao Seguro Desemprego."
        ],
        2: [
            "Motivo: Pedido de Demissão.",
            "Recebe Saldo, 13º e Férias prop.",
            "NÃO saca FGTS/Multa.",
            "SEM Seguro Desemprego."
        ],
        3: [
            "Motivo: Justa Causa.",
            "Apenas Saldo de Salário e Férias Vencidas.",
            "Sem 13º/Férias Prop.",
            "NÃO saca FGTS."
        ],
        4: [
            "Motivo: Acordo Comum (Art. 484-A).",
            "Aviso indenizado pela metade.",
            "Multa FGTS 20%. Saque 80%.",
            "SEM Seguro Desemprego."
        ],
        5: [
            "Motivo: Término de Contrato.",
            "Recebe verbas normais.",
            "Saca FGTS, sem multa de 40%."
        ],
        6: [
            "Motivo: Quebra Contrato (Empresa).",
            "Indenização metade dos dias restantes.",
            "FGTS + 40%."
        ],
        7: [
            "Motivo: Quebra Contrato (Funcionário).",
            "Pode indenizar empresa.",
            "NÃO saca FGTS."
        ]
    }
    return resumos.get(tipo, [])


# ==============================================================================
#  MOTOR PRINCIPAL
# ==============================================================================

def processar_rescisao(data_json):
    """
    Processa rescisão trabalhista.
    """
    try:
        tipo = int(data_json.get("motivo", 1))
        salario_base = float(data_json.get("salario_base", 0))
        adicionais = float(data_json.get("adicionais", 0))
        media_he = float(data_json.get("media_he", 0))
        media_comissao = float(data_json.get("media_comissao", 0))

        dt_adm = parse_data(data_json.get("data_admissao"))
        dt_dem = parse_data(data_json.get("data_demissao"))
        dt_prev_fim = parse_data(data_json.get("data_prevista_fim"))

        ferias_vencidas_qtd = int(data_json.get("ferias_vencidas_qtd", 0))
        dependentes = int(data_json.get("dependentes", 0))
        pensao = float(data_json.get("pensao", 0))
        adiantamento = float(data_json.get("adiantamento", 0))
        saldo_fgts = float(data_json.get("saldo_fgts", 0))

        aviso_indenizado = bool(data_json.get("aviso_indenizado", False))
        aviso_cumprido = bool(data_json.get("aviso_cumprido", True))

    except (ValueError, TypeError) as e:
        raise ValueError(f"Erro nos dados de entrada: {e}")

    if not dt_adm or not dt_dem:
        raise ValueError("Datas de admissão e demissão são obrigatórias.")
    if dt_dem < dt_adm:
        raise ValueError("Data de demissão anterior à admissão.")

    # 2. Base de Cálculo
    remuneracao_total = salario_base + adicionais + media_he + media_comissao
    val_dia = remuneracao_total / 30

    # 3. Aviso Prévio e Datas
    dias_aviso_pagar = 0
    aviso_descontar = False
    multa_art479_480 = 0.0
    data_projecao = dt_dem

    anos_servico = (dt_dem - dt_adm).days // 365
    dias_aviso_direito = min(30 + (3 * anos_servico), 90)

    if tipo == 1 and aviso_indenizado:
        dias_aviso_pagar = dias_aviso_direito
        data_projecao = dt_dem + datetime.timedelta(days=dias_aviso_direito)

    elif tipo == 2 and not aviso_cumprido:
        aviso_descontar = True

    elif tipo == 4 and aviso_indenizado:
        dias_aviso_pagar = dias_aviso_direito // 2
        data_projecao = dt_dem + datetime.timedelta(days=dias_aviso_pagar)

    elif tipo in [6, 7] and dt_prev_fim and dt_prev_fim > dt_dem:
        dias_restantes = (dt_prev_fim - dt_dem).days
        multa_art479_480 = (dias_restantes * val_dia) / 2

    # 4. Cálculos das Verbas
    prov = {}
    desc = {}
    verbas_tributaveis = 0.0
    verbas_isentas = 0.0

    # Saldo Salário
    dias_trab = dt_dem.day
    ultimo_dia_mes = monthrange(dt_dem.year, dt_dem.month)[1]
    dias_saldo = 30 if (dias_trab == ultimo_dia_mes or dias_trab == 31) else dias_trab

    val_saldo = val_dia * dias_saldo
    prov[f"Saldo de Salário ({dias_saldo} dias)"] = round(val_saldo, 2)
    verbas_tributaveis += val_saldo

    # Aviso Indenizado (Isento)
    if dias_aviso_pagar > 0:
        val_aviso = val_dia * dias_aviso_pagar
        prov[f"Aviso Prévio Indenizado ({dias_aviso_pagar} dias)"] = round(val_aviso, 2)
        verbas_isentas += val_aviso

    # Indenizações Art 479/480
    if tipo == 6 and multa_art479_480 > 0:
        prov["Indenização Art. 479"] = round(multa_art479_480, 2)
        verbas_isentas += multa_art479_480
    if tipo == 7 and multa_art479_480 > 0:
        desc["Indenização Art. 480"] = round(multa_art479_480, 2)

    # Aviso não cumprido (Desconto)
    if aviso_descontar:
        desc["Aviso Prévio Não Cumprido"] = round(remuneracao_total, 2)

    # 13º Salário
    meses_13 = 0
    if tipo != 3:
        inicio_ano = datetime.date(dt_dem.year, 1, 1)
        inicio_contagem = dt_adm if dt_adm > inicio_ano else inicio_ano
        meses_13 = min(calcular_meses_trabalhados(inicio_contagem, data_projecao), 12)
        
        if meses_13 > 0:
            val_13 = (remuneracao_total / 12) * meses_13
            prov[f"13º Salário Proporcional ({meses_13}/12)"] = round(val_13, 2)
            verbas_tributaveis += val_13

    # Férias
    if ferias_vencidas_qtd > 0:
        val_ferias = remuneracao_total * ferias_vencidas_qtd
        val_terco = val_ferias / 3
        prov[f"Férias Vencidas ({ferias_vencidas_qtd})"] = round(val_ferias, 2)
        prov["1/3 Férias Vencidas"] = round(val_terco, 2)
        verbas_isentas += val_ferias + val_terco

    if tipo != 3:
        # Período Aquisitivo
        anos_completos = (dt_dem.year - dt_adm.year)
        if (dt_dem.month, dt_dem.day) < (dt_adm.month, dt_adm.day):
            anos_completos -= 1
        
        try:
            ini_aq = datetime.date(dt_adm.year + anos_completos, dt_adm.month, dt_adm.day)
        except ValueError:
            ini_aq = datetime.date(dt_adm.year + anos_completos, dt_adm.month, 28)
            
        avos_ferias = calcular_avos_ferias(ini_aq, data_projecao)
        if avos_ferias > 0:
            val_f_prop = (remuneracao_total / 12) * avos_ferias
            val_t_prop = val_f_prop / 3
            prov[f"Férias Prop. ({avos_ferias}/12)"] = round(val_f_prop, 2)
            prov["1/3 Férias Prop."] = round(val_t_prop, 2)
            verbas_isentas += val_f_prop + val_t_prop

    # FGTS
    fgts_info = {}
    multa_fgts = 0.0
    if tipo in [1, 6]: # 40%
        multa_fgts = saldo_fgts * 0.40
        fgts_info["Saque"] = "100% + 40%"
    elif tipo == 4: # 20%
        multa_fgts = saldo_fgts * 0.20
        fgts_info["Saque"] = "80% + 20%"
    elif tipo == 5:
        fgts_info["Saque"] = "100% (Sem multa)"
    else:
        fgts_info["Saque"] = "Não permitido"

    if multa_fgts > 0:
        fgts_info["Multa FGTS"] = round(multa_fgts, 2)

    # 5. DESCONTOS (INSS e IRRF 2026)
    
    # INSS
    base_inss = val_saldo
    if tipo != 3 and meses_13 > 0:
        base_inss += val_13
    
    inss_val = calcular_inss_2026(base_inss)
    desc["INSS (2026)"] = inss_val

    # IRRF (2026)
    # A base legal do IR é (Bruto - INSS).
    # O redutor especial olha para o (Bruto).
    base_irrf_legal = verbas_tributaveis - inss_val
    
    # IMPORTANTE: Passamos 'verbas_tributaveis' como rendimento_bruto para checar a isenção de 5k
    irrf_val = calcular_irrf_2026(base_irrf_legal, dependentes, pensao, verbas_tributaveis)
    
    if irrf_val > 0:
        desc["IRRF (2026)"] = irrf_val

    if pensao > 0:
        desc["Pensão Alimentícia"] = round(pensao, 2)
    if adiantamento > 0:
        desc["Adiantamento"] = round(adiantamento, 2)

    # 6. Totais
    total_prov = sum(prov.values())
    total_desc = sum(desc.values())
    liquido = total_prov - total_desc

    return {
        "resumo": gerar_resumo_texto(tipo),
        "dados_entrada": {
            "tipo": tipo,
            "remuneracao": round(remuneracao_total, 2),
            "tempo_servico": anos_servico
        },
        "proventos": prov,
        "descontos": desc,
        "fgts": fgts_info,
        "totais": {
            "total_proventos": round(total_prov, 2),
            "total_descontos": round(total_desc, 2),
            "total_liquido": round(liquido, 2),
            "verbas_tributaveis": round(verbas_tributaveis, 2),
            "verbas_isentas": round(verbas_isentas, 2)
        },
        "observacoes": {
            "base_inss": round(base_inss, 2),
            "base_irrf": round(base_irrf_legal, 2),
            "nota": "Cálculo base 2026 (Salário 1.621 / Isenção IR até 5k)"
        }
    }

if __name__ == "__main__":
    # Modo CLI simples
    print("Execute via API/Flask.")