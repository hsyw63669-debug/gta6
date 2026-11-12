import os
import sys
import json
import smtplib
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, HTTPServer
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(DIRECTORY, "email_config.json")
LOG_FILE = os.path.join(DIRECTORY, "emails_enviados.log")

def get_email_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Erro ao ler email_config.json:", e)
    return {
        "provider": "smtp",
        "api_key": "",
        "sender_email": "eliasfiver1@gmail.com",
        "sender_name": "GTA6Store Suporte",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "eliasfiver1@gmail.com",
        "smtp_pass": "yzimkxadmkeuwdzi",
        "use_tls": True
    }

def save_email_config(new_config):
    old = get_email_config()
    # Preserva senhas/chaves caso venham mascaradas ou vazias
    if not new_config.get("smtp_pass") or new_config.get("smtp_pass") == "********":
        new_config["smtp_pass"] = old.get("smtp_pass", "")
    else:
        new_config["smtp_pass"] = new_config["smtp_pass"].replace(" ", "")

    if "..." in new_config.get("api_key", "") or not new_config.get("api_key"):
        new_config["api_key"] = old.get("api_key", "")

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config, f, indent=2, ensure_ascii=False)

def enviar_via_resend(api_key, destinatario, nome, codigo, html_content):
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "User-Agent": "GTA6Store/1.0"
    }
    payload = {
        "from": "GTA6Store <onboarding@resend.dev>",
        "to": [destinatario],
        "subject": f"Código de Verificação: {codigo} – GTA6Store",
        "html": html_content
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        print(f"✅ [Resend API] E-mail enviado com sucesso para {destinatario}: {res_data}")
        return {"success": True, "method": "resend_api", "id": res_data.get("id")}

def enviar_via_brevo(api_key, destinatario, nome, codigo, html_content):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key.strip(),
        "Content-Type": "application/json",
        "User-Agent": "GTA6Store/1.0"
    }
    payload = {
        "sender": {"name": "GTA6Store", "email": "suporte@gta6store.com"},
        "to": [{"email": destinatario, "name": nome or "Cliente"}],
        "subject": f"Código de Verificação: {codigo} – GTA6Store",
        "htmlContent": html_content
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        print(f"✅ [Brevo API] E-mail enviado com sucesso para {destinatario}: {res_data}")
        return {"success": True, "method": "brevo_api", "messageId": res_data.get("messageId")}

def enviar_email_real(destinatario, nome, codigo):
    config = get_email_config()
    provider = config.get("provider", "smtp").lower()
    api_key = config.get("api_key", "").strip()
    smtp_user = config.get("smtp_user", "").strip()
    smtp_pass = config.get("smtp_pass", "").strip().replace(" ", "")

    corpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0b0c10; color: #f1f5f9; padding: 24px; margin: 0; }}
        .card {{ max-width: 500px; margin: 0 auto; background: #161922; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); padding: 32px; text-align: center; }}
        .logo {{ font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 20px; }}
        .logo span {{ color: #2563eb; }}
        .title {{ font-size: 20px; font-weight: 700; color: #ffffff; margin-bottom: 12px; }}
        .desc {{ font-size: 14px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }}
        .code-box {{ display: inline-block; background: #1c202b; border: 2px dashed #2563eb; color: #ffffff; font-size: 32px; font-weight: 800; letter-spacing: 8px; padding: 16px 28px; border-radius: 8px; font-family: monospace; margin-bottom: 24px; }}
        .warning {{ font-size: 12px; color: #64748b; margin-top: 24px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 16px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="logo">🎮 GTA6<span>Store</span></div>
        <div class="title">Olá, {nome or 'Gamer'}!</div>
        <div class="desc">
          Recebemos sua solicitação para validar sua conta na <strong>GTA6Store</strong>.<br>
          Insira o código de segurança abaixo para confirmar seu e-mail:
        </div>
        <div class="code-box">{codigo}</div>
        <div class="desc" style="font-size: 13px;">Este código é válido por 15 minutos. Não o compartilhe com ninguém.</div>
        <div class="warning">GTA6Store Marketplace Oficial · Suporte 24 horas</div>
      </div>
    </body>
    </html>
    """

    # 1. SE ESCOLHEU SMTP OU GMAIL CONFIGURADO (RECOMENDADO E SEM RESTRIÇÃO DE DOMÍNIO)
    if provider == "smtp" or (smtp_user and smtp_pass and provider != "resend"):
        try:
            smtp_host = config.get("smtp_host", "smtp.gmail.com").strip()
            smtp_port = int(config.get("smtp_port", 587))
            sender_name = config.get("sender_name", "GTA6Store Suporte")

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Código de Verificação: {codigo} – GTA6Store"
            msg["From"] = f"{sender_name} <{smtp_user}>"
            msg["To"] = destinatario
            msg.attach(MIMEText(f"Olá {nome}!\n\nSeu código na GTA6Store é: {codigo}", "plain", "utf-8"))
            msg.attach(MIMEText(corpo_html, "html", "utf-8"))

            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
                if config.get("use_tls", True):
                    server.starttls()

            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, destinatario, msg.as_string())
            server.quit()
            print(f"✅ [Gmail SMTP] E-mail enviado com sucesso para: {destinatario}")
            registrar_log_email(destinatario, codigo, nome)
            return {"success": True, "method": "smtp", "message": f"E-mail enviado para {destinatario}"}
        except Exception as e:
            print(f"❌ Erro ao enviar por SMTP ({e})")
            registrar_log_email(destinatario, codigo, nome, erro=str(e))
            return {"success": False, "error": f"Erro SMTP: {str(e)}"}

    # 2. TENTA VIA RESEND API
    if provider == "resend" and api_key and not "..." in api_key:
        try:
            return enviar_via_resend(api_key, destinatario, nome, codigo, corpo_html)
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8")
            print(f"❌ Erro HTTP Resend API ({he.code}): {err_msg}")
            registrar_log_email(destinatario, codigo, nome, erro=err_msg)
            return {"success": False, "error": f"Erro Resend API: {err_msg}"}
        except Exception as e:
            print(f"❌ Erro de conexão Resend API: {e}")
            registrar_log_email(destinatario, codigo, nome, erro=str(e))
            return {"success": False, "error": str(e)}

    # 3. TENTA VIA BREVO API
    if provider == "brevo" and api_key and not "..." in api_key:
        try:
            return enviar_via_brevo(api_key, destinatario, nome, codigo, corpo_html)
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8")
            print(f"❌ Erro HTTP Brevo API ({he.code}): {err_msg}")
            registrar_log_email(destinatario, codigo, nome, erro=err_msg)
            return {"success": False, "error": f"Erro Brevo API: {err_msg}"}
        except Exception as e:
            print(f"❌ Erro Brevo API: {e}")
            registrar_log_email(destinatario, codigo, nome, erro=str(e))
            return {"success": False, "error": str(e)}

    # 4. CASO DE CONTINGÊNCIA
    registrar_log_email(destinatario, codigo, nome)
    print(f"ℹ️ [Log local] Código {codigo} gerado para {destinatario} e salvo em {LOG_FILE}")
    return {
        "success": True,
        "method": "saved",
        "message": f"Código {codigo} gerado para {destinatario}"
    }

def registrar_log_email(destinatario, codigo, nome, erro=None):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        linha = {
            "destinatario": destinatario,
            "nome": nome,
            "codigo": codigo,
            "erro": erro
        }
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")

class StoreHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        if self.path == "/api/send-code":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                email = data.get("email", "").strip()
                nome = data.get("nome", "").strip()
                codigo = data.get("code", "").strip()

                if not email or not codigo:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "E-mail ou código ausente"}).encode("utf-8"))
                    return

                res = enviar_email_real(email, nome, codigo)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        elif self.path == "/api/email-config":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                save_email_config(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        elif self.path == "/api/test-email":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                destinatario = data.get("email", "")
                res = enviar_email_real(destinatario, "Teste de Conexão", "123456")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        super().do_POST()

    def do_GET(self):
        if self.path == "/api/email-config":
            config = get_email_config()
            safe_config = dict(config)
            if safe_config.get("api_key") and len(safe_config["api_key"]) > 8:
                safe_config["api_key"] = safe_config["api_key"][:4] + "..." + safe_config["api_key"][-4:]
            if safe_config.get("smtp_pass"):
                safe_config["smtp_pass"] = "********"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(safe_config).encode("utf-8"))
            return

        if self.path == "/api/latest-code":
            codigo = None
            if os.path.exists(LOG_FILE):
                try:
                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if lines:
                            last = json.loads(lines[-1].strip())
                            codigo = last.get("codigo")
                except:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"latest_code": codigo}).encode("utf-8"))
            return

        if self.path == "/favicon.ico":
            fav_path = os.path.join(DIRECTORY, "favicon.svg")
            if os.path.exists(fav_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.end_headers()
                with open(fav_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 3030))
    server = HTTPServer(("0.0.0.0", PORT), StoreHandler)
    print(f"Servidor GTA6Store ativo com suporte a Gmail SMTP na porta {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
