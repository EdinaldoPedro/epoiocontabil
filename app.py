from flask import Flask, render_template, request, jsonify
from calculo_das import calcular_simples_nacional_from_input  # seu script de cálculo
from calcular_darf_pro_labore import calcular_darf_pro_labore  # importe seu novo script
from simulador_lp import calcula_imposto
from valor_bruto import calcular_valor_bruto_from_input
from calculo_rescisao import processar_rescisao
from gerador_contracheque import processar_holerite_api

app = Flask(__name__, template_folder="templates")  # ajuste se seus templates estiverem em 'templates/'


@app.route("/")

def index():
    return render_template("index.html")

@app.route("/simulador_das")
def simulador_das():
    return render_template("simulador_das.html")

@app.route("/simulador_lp")
def simulador_lp():
    return render_template("simulador_lp.html")

@app.route("/simulador_rescisao")
def simulador_rescisao():
    return render_template("simulador_rescisao.html")

@app.route("/simulador_nfse")
def simulador_nfse():
    return render_template("simulador_nfse.html")


@app.route("/simulador_holerite")
def simulador_holerite():
    return render_template("simulador_holerite.html")


@app.route("/calcular_das", methods=["POST"])
def calcular_das():
    try:
        data = request.get_json(force=True)
        print("\n📦 JSON recebido do front:", data)
        resultado = calcular_simples_nacional_from_input(data)
        return jsonify(resultado)
    except Exception as e:
        print("❌ Erro no cálculo:", e)
        return jsonify({"erro": str(e)}), 400


@app.route("/calcular_darf_pro_labore", methods=["POST"])
def calcular_darf():
    try:
        data = request.get_json(force=True)
        print("\n📦 JSON recebido para DARF:", data)
        resultado = calcular_darf_pro_labore(data)
        return jsonify(resultado)
    except Exception as e:
        print("❌ Erro no cálculo DARF:", e)
        return jsonify({"erro": str(e)}), 400
    
@app.route("/calcular_lp", methods=["POST"])
def calcular_lp():
    try:
        data = request.get_json(force=True)
        print("\n📦 JSON recebido para LP:", data)

        valor_nfse = float(data.get("valor_nfse", 0))
        faturamento_mensal = float(data.get("faturamento_mensal", 0))
        natureza_exportacao = int(data.get("natureza_exportacao", 1))
        aliquota_iss = float(data.get("aliquota_iss_percentual", 0))

        resultado = calcula_imposto(valor_nfse, faturamento_mensal, natureza_exportacao, aliquota_iss)
        return jsonify(resultado)
    except Exception as e:
        print("❌ Erro no cálculo LP:", e)
        return jsonify({"erro": str(e)}), 400
    
@app.route("/calcular_valor_bruto", methods=["POST"])
def calcular_valor_bruto_api():
    try:
        data = request.get_json(force=True)
        print("\n📦 JSON recebido (Valor Bruto):", data)

        resultado = calcular_valor_bruto_from_input(data)
        return jsonify(resultado)

    except Exception as e:
        print("❌ Erro no cálculo de Valor Bruto:", e)
        return jsonify({"erro": str(e)}), 400

@app.route('/calcular_rescisao', methods=['POST'])
def api_calcular_rescisao():
    data = request.get_json()
    
    try:
        # Chama a função do arquivo calculo_rescisao.py
        # Ela já devolve o dicionário pronto (resumo, proventos, descontos, totais)
        resultado = processar_rescisao(data)
        
        # Retorna como JSON para o JavaScript do navegador
        return jsonify(resultado)
        
    except Exception as e:
        # Se der erro (ex: data inválida), devolve mensagem de erro
        return jsonify({"erro": f"Erro no servidor: {str(e)}"}), 400
    
@app.route("/calcular_holerite", methods=["POST"])
def calcular_holerite():
    try:
        data = request.get_json(force=True)
        print("\n📦 JSON recebido Holerite:", data)
        
        # Chama a função refatorada no script Python
        resultado = processar_holerite_api(data)
        
        return jsonify(resultado)
    except Exception as e:
        print("❌ Erro no cálculo Holerite:", e)
        return jsonify({"erro": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True, port=5000)