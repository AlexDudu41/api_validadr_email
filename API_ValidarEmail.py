from flask import Flask, jsonify, render_template
from email_validator import validate_email, EmailNotValidError
import dns.resolver
from difflib import get_close_matches
import pandas as pd
import os
import smtplib
 
app = Flask(__name__)
 
# Configuração do resolver DNS
resolver = dns.resolver.Resolver()
resolver.nameservers = ['8.8.8.8']  # Google DNS
 
# Caminho para os arquivos de domínios populares
caminho = os.getcwd()
data_dns = pd.read_excel(f"{caminho}/DIMENSIONAIS/dominio_populares.xlsx")
dominios_populares = pd.DataFrame(data_dns)
 
data_tld = pd.read_excel(f"{caminho}/DIMENSIONAIS/tld_populares.xlsx")
tld_populares = pd.DataFrame(data_tld)
 
 
def verificar_dns(dominio):
    try:
        dns.resolver.resolve(dominio, 'MX')
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
        return False
 
 
def sugerir_dominio(email):
    try:
        valid = validate_email(email)
        dominio = valid.domain
 
        if any(map(lambda vDNS: vDNS == dominio, dominios_populares['DNS'].tolist())):
            return f"O e-mail '{email}' é válido por lista!"
 
        if verificar_dns(dominio):
            return f"O e-mail '{email}' é válido!"
        else:
            sugestao = get_close_matches(dominio, dominios_populares['DNS'].tolist(), n=1, cutoff=0.6)
            if not sugestao:
                partes_dominio = dominio.split('.')
                if len(partes_dominio) > 1:
                    tlds_comuns = ["com", "net", "org", "edu", "gov", "co", "br"]
                    sugestoes_tld = [f"{partes_dominio[0]}.{tld}" for tld in tlds_comuns if verificar_dns(f"{partes_dominio[0]}.{tld}")]
                    if sugestoes_tld:
                        sugestao = sugestoes_tld[:1]
            if sugestao:
                parte_local = valid.local_part
                email_sugerido = f"{parte_local}@{sugestao[0]}"
                return f"O domínio '{dominio}' parece inválido. Você quis dizer: '{email_sugerido}'?"
            else:
                return "O domínio do e-mail parece inválido e não foi possível sugerir um domínio alternativo."
    except EmailNotValidError as e:
        dominio_incorreto = email.split('@')[-1]
        sugestao = get_close_matches(dominio_incorreto, dominios_populares['DNS'].tolist(), n=1, cutoff=0.6)
        if not sugestao:
            partes_dominio = dominio_incorreto.split('.')
            if len(partes_dominio) > 1:
                tlds_comuns = ["com", "net", "org", "edu", "gov", "co", "br"]
                sugestoes_tld = [f"{partes_dominio[0]}.{tld}" for tld in tlds_comuns if verificar_dns(f"{partes_dominio[0]}.{tld}")]
                if sugestoes_tld:
                    sugestao = sugestoes_tld[:1]
        if sugestao:
            parte_local = email.split('@')[0]
            email_sugerido = f"{parte_local}@{sugestao[0]}"
            return f"Erro: {str(e)}. Você quis dizer: '{email_sugerido}'?"
        else:
            return f"Erro: {str(e)}. Não foi possível sugerir um domínio alternativo."
 
 
def verificar_email(email):
    dominio = email.split('@')[1]
    try:
        registros_mx = dns.resolver.resolve(dominio, 'MX')
        servidor_mx = str(registros_mx[0].exchange)
 
        servidor = smtplib.SMTP(servidor_mx)
        servidor.set_debuglevel(0)
        servidor.helo()
        servidor.mail('test@example.com')
        codigo, mensagem = servidor.rcpt(email)
        servidor.quit()
 
        if codigo == 250:
            return f"CÓDIGO {codigo} - O email '{email}' parece estar ativo."
        else:
            return f"CÓDIGO {codigo} - O email '{email}' não está ativo ou foi rejeitado."
    except Exception as e:
        return f"Erro ao verificar o email: {str(e)}"
 
 
@app.route('/')
def home():
    return render_template('index.html')  # Renderiza o arquivo HTML da página home
 
@app.route('/verificar/<email>', methods=['GET'])
def verificar(email):
    resultado = sugerir_dominio(email)
    return jsonify({"resultado": resultado})
 
 
@app.route('/verificar_atividade/<email>', methods=['GET'])
def verificar_atividade(email):
    resultado = verificar_email(email)
    return jsonify({"resultado": resultado})
 
 
if __name__ == '__main__':
    app.run(debug=True)
 