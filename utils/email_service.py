"""
Email service for BookCreatorAI SaaS
Handles transactional emails: confirmations, invoices, notifications
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Email configuration from environment
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@almadolivro.com')
FROM_NAME = os.environ.get('FROM_NAME', 'Alma do Livro')


def send_email(to_email, subject, html_content, text_content=None):
    """Send an email using SMTP"""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[EMAIL] SMTP not configured. Would send to {to_email}: {subject}")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To'] = to_email
        
        # Plain text fallback
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        
        # HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        
        print(f"[EMAIL] Sent to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL] Error sending to {to_email}: {e}")
        return False


def get_base_template(content, title="Alma do Livro"):
    """Wrap content in base email template"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #1a1a2e;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #1a1a2e; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #16213e; border-radius: 16px; overflow: hidden;">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%); padding: 30px; text-align: center;">
                                <h1 style="margin: 0; color: white; font-size: 24px;">🔍 Alma do Livro</h1>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px; color: #e0e0e0;">
                                {content}
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 20px 30px; background-color: #0f0f23; text-align: center; border-top: 1px solid #333;">
                                <p style="margin: 0 0 10px; color: #888; font-size: 12px;">
                                    © {datetime.now().year} Alma do Livro. Todos os direitos reservados.
                                </p>
                                <p style="margin: 0; color: #666; font-size: 11px;">
                                    <a href="https://almadolivro.com/terms" style="color: #8B5CF6; text-decoration: none;">Termos</a> · 
                                    <a href="https://almadolivro.com/privacy" style="color: #8B5CF6; text-decoration: none;">Privacidade</a> · 
                                    <a href="https://almadolivro.com/faq" style="color: #8B5CF6; text-decoration: none;">Ajuda</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def send_welcome_email(user_email, user_name):
    """Send welcome email to new users"""
    content = f"""
    <h2 style="color: white; margin: 0 0 20px;">Bem-vindo(a), {user_name}! 👋</h2>
    <p style="line-height: 1.6;">
        Obrigado por te juntares ao <strong style="color: #8B5CF6;">Alma do Livro</strong>! 
        Estamos entusiasmados por te ter connosco.
    </p>
    <p style="line-height: 1.6;">
        Com a tua conta gratuita, podes:
    </p>
    <ul style="line-height: 1.8; padding-left: 20px;">
        <li>Analisar até <strong>10 livros por mês</strong></li>
        <li>Obter resumos e análises de personagens</li>
        <li>Explorar temas e simbolismos</li>
        <li>Conversar sobre qualquer livro</li>
    </ul>
    <p style="line-height: 1.6;">
        Queres desbloquear funcionalidades premium como <strong>quizzes</strong>, 
        <strong>entrevistas com personagens</strong> e <strong>finais alternativos</strong>?
    </p>
    <div style="text-align: center; margin: 30px 0;">
        <a href="https://almadolivro.com/subscription/pricing" 
           style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%); 
                  color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
            Ver Planos Premium
        </a>
    </div>
    <p style="line-height: 1.6;">
        Pronto para começar? <a href="https://almadolivro.com/explorer" style="color: #8B5CF6;">Explora o teu primeiro livro →</a>
    </p>
    <p style="margin-top: 30px; color: #888;">
        Boas leituras!<br>
        <strong style="color: white;">Equipa Alma do Livro</strong>
    </p>
    """
    
    html = get_base_template(content, "Bem-vindo ao Alma do Livro!")
    text = f"Bem-vindo(a), {user_name}! Obrigado por te juntares ao Alma do Livro. Visita https://almadolivro.com/explorer para começar."
    
    return send_email(user_email, "🎉 Bem-vindo ao Alma do Livro!", html, text)


def send_subscription_confirmation(user_email, user_name, plan_name, amount, currency='EUR'):
    """Send subscription confirmation email"""
    content = f"""
    <h2 style="color: white; margin: 0 0 20px;">Subscrição Confirmada! 🎉</h2>
    <p style="line-height: 1.6;">
        Olá <strong>{user_name}</strong>,
    </p>
    <p style="line-height: 1.6;">
        A tua subscrição do plano <strong style="color: #8B5CF6;">{plan_name}</strong> foi ativada com sucesso!
    </p>
    <div style="background-color: #1a1a2e; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <table width="100%" cellpadding="5">
            <tr>
                <td style="color: #888;">Plano:</td>
                <td style="color: white; text-align: right;"><strong>{plan_name}</strong></td>
            </tr>
            <tr>
                <td style="color: #888;">Valor:</td>
                <td style="color: white; text-align: right;"><strong>{currency} {amount:.2f}/mês</strong></td>
            </tr>
            <tr>
                <td style="color: #888;">Estado:</td>
                <td style="color: #10B981; text-align: right;"><strong>Ativo</strong></td>
            </tr>
        </table>
    </div>
    <p style="line-height: 1.6;">
        Agora tens acesso a todas as funcionalidades do plano {plan_name}. Aproveita!
    </p>
    <div style="text-align: center; margin: 30px 0;">
        <a href="https://almadolivro.com/explorer" 
           style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%); 
                  color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
            Começar a Explorar
        </a>
    </div>
    <p style="color: #888; font-size: 13px;">
        Podes gerir a tua subscrição a qualquer momento em 
        <a href="https://almadolivro.com/subscription/manage" style="color: #8B5CF6;">Definições → Subscrição</a>.
    </p>
    """
    
    html = get_base_template(content, "Subscrição Confirmada")
    text = f"Olá {user_name}, a tua subscrição do plano {plan_name} foi ativada! Valor: {currency} {amount:.2f}/mês"
    
    return send_email(user_email, f"✅ Subscrição {plan_name} Ativada!", html, text)


def send_invoice_email(user_email, user_name, invoice_data):
    """Send invoice/receipt email"""
    content = f"""
    <h2 style="color: white; margin: 0 0 20px;">Recibo de Pagamento 📄</h2>
    <p style="line-height: 1.6;">
        Olá <strong>{user_name}</strong>,
    </p>
    <p style="line-height: 1.6;">
        Obrigado pelo teu pagamento. Aqui está o teu recibo:
    </p>
    <div style="background-color: #1a1a2e; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <table width="100%" cellpadding="8">
            <tr style="border-bottom: 1px solid #333;">
                <td style="color: #888;">Nº Fatura:</td>
                <td style="color: white; text-align: right;">{invoice_data.get('invoice_number', 'N/A')}</td>
            </tr>
            <tr style="border-bottom: 1px solid #333;">
                <td style="color: #888;">Data:</td>
                <td style="color: white; text-align: right;">{invoice_data.get('date', datetime.now().strftime('%d/%m/%Y'))}</td>
            </tr>
            <tr style="border-bottom: 1px solid #333;">
                <td style="color: #888;">Descrição:</td>
                <td style="color: white; text-align: right;">{invoice_data.get('description', 'Subscrição Alma do Livro')}</td>
            </tr>
            <tr style="border-bottom: 1px solid #333;">
                <td style="color: #888;">Período:</td>
                <td style="color: white; text-align: right;">{invoice_data.get('period', 'Mensal')}</td>
            </tr>
            <tr>
                <td style="color: #888; font-size: 16px;"><strong>Total:</strong></td>
                <td style="color: #10B981; text-align: right; font-size: 18px;">
                    <strong>{invoice_data.get('currency', 'EUR')} {invoice_data.get('amount', 0):.2f}</strong>
                </td>
            </tr>
        </table>
    </div>
    <p style="color: #888; font-size: 13px;">
        Se precisares de uma fatura com dados fiscais, contacta-nos em 
        <a href="mailto:faturacao@almadolivro.com" style="color: #8B5CF6;">faturacao@almadolivro.com</a>.
    </p>
    """
    
    html = get_base_template(content, "Recibo de Pagamento")
    text = f"Recibo de pagamento - {invoice_data.get('description', 'Subscrição')}: {invoice_data.get('currency', 'EUR')} {invoice_data.get('amount', 0):.2f}"
    
    return send_email(user_email, "🧾 Recibo de Pagamento - Alma do Livro", html, text)


def send_subscription_cancelled(user_email, user_name, end_date):
    """Send subscription cancellation confirmation"""
    content = f"""
    <h2 style="color: white; margin: 0 0 20px;">Subscrição Cancelada</h2>
    <p style="line-height: 1.6;">
        Olá <strong>{user_name}</strong>,
    </p>
    <p style="line-height: 1.6;">
        Confirmamos o cancelamento da tua subscrição. Lamentamos ver-te partir! 😢
    </p>
    <div style="background-color: #1a1a2e; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <p style="margin: 0; color: #888;">
            <strong style="color: white;">Acesso até:</strong> {end_date}
        </p>
        <p style="margin: 10px 0 0; color: #888; font-size: 13px;">
            Continuarás a ter acesso às funcionalidades premium até esta data.
        </p>
    </div>
    <p style="line-height: 1.6;">
        Após esta data, a tua conta passará automaticamente para o plano gratuito.
    </p>
    <p style="line-height: 1.6;">
        Mudaste de ideias? Podes reativar a subscrição a qualquer momento:
    </p>
    <div style="text-align: center; margin: 30px 0;">
        <a href="https://almadolivro.com/subscription/pricing" 
           style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%); 
                  color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
            Reativar Subscrição
        </a>
    </div>
    <p style="color: #888; font-size: 13px;">
        Se tiveres algum feedback sobre como podemos melhorar, adoraríamos ouvir-te em 
        <a href="mailto:feedback@almadolivro.com" style="color: #8B5CF6;">feedback@almadolivro.com</a>.
    </p>
    """
    
    html = get_base_template(content, "Subscrição Cancelada")
    text = f"Olá {user_name}, a tua subscrição foi cancelada. Terás acesso até {end_date}."
    
    return send_email(user_email, "Subscrição Cancelada - Alma do Livro", html, text)


def send_usage_warning(user_email, user_name, usage_count, usage_limit, percentage):
    """Send usage warning when approaching limit"""
    content = f"""
    <h2 style="color: white; margin: 0 0 20px;">⚠️ Limite de Uso Próximo</h2>
    <p style="line-height: 1.6;">
        Olá <strong>{user_name}</strong>,
    </p>
    <p style="line-height: 1.6;">
        Já utilizaste <strong style="color: #F59E0B;">{percentage}%</strong> do teu limite mensal de análises.
    </p>
    <div style="background-color: #1a1a2e; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <div style="background-color: #333; border-radius: 4px; height: 8px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #8B5CF6, #EC4899); height: 100%; width: {percentage}%;"></div>
        </div>
        <p style="margin: 10px 0 0; text-align: center; color: white;">
            <strong>{usage_count}</strong> / {usage_limit} análises utilizadas
        </p>
    </div>
    <p style="line-height: 1.6;">
        Para continuar a explorar livros sem interrupções, considera fazer upgrade do teu plano:
    </p>
    <div style="text-align: center; margin: 30px 0;">
        <a href="https://almadolivro.com/subscription/pricing" 
           style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%); 
                  color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
            Ver Planos com Mais Análises
        </a>
    </div>
    """
    
    html = get_base_template(content, "Limite de Uso Próximo")
    text = f"Olá {user_name}, já utilizaste {percentage}% do teu limite mensal ({usage_count}/{usage_limit} análises)."
    
    return send_email(user_email, f"⚠️ {percentage}% do Limite Mensal Utilizado", html, text)


def send_password_reset(user_email, user_name, reset_link):
    """Send password reset email"""
    content = f"""
    <h2 style="color: white; margin: 0 0 20px;">Redefinir Palavra-passe 🔐</h2>
    <p style="line-height: 1.6;">
        Olá <strong>{user_name}</strong>,
    </p>
    <p style="line-height: 1.6;">
        Recebemos um pedido para redefinir a palavra-passe da tua conta.
    </p>
    <div style="text-align: center; margin: 30px 0;">
        <a href="{reset_link}" 
           style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%); 
                  color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
            Redefinir Palavra-passe
        </a>
    </div>
    <p style="color: #888; font-size: 13px;">
        Este link expira em 1 hora. Se não pediste esta redefinição, podes ignorar este email.
    </p>
    <p style="color: #666; font-size: 12px; margin-top: 20px;">
        Link direto: <a href="{reset_link}" style="color: #8B5CF6; word-break: break-all;">{reset_link}</a>
    </p>
    """
    
    html = get_base_template(content, "Redefinir Palavra-passe")
    text = f"Olá {user_name}, clica neste link para redefinir a tua palavra-passe: {reset_link}"
    
    return send_email(user_email, "🔐 Redefinir Palavra-passe - Alma do Livro", html, text)


def send_support_confirmation(user_email, user_name, ticket_subject):
    """Send support ticket confirmation"""
    content = f"""
    <h2 style="color: white; margin: 0 0 20px;">Mensagem Recebida! 📬</h2>
    <p style="line-height: 1.6;">
        Olá <strong>{user_name}</strong>,
    </p>
    <p style="line-height: 1.6;">
        Recebemos a tua mensagem sobre: <strong style="color: #8B5CF6;">"{ticket_subject}"</strong>
    </p>
    <p style="line-height: 1.6;">
        A nossa equipa irá analisar o teu pedido e responder o mais brevemente possível, 
        normalmente dentro de 24-48 horas úteis.
    </p>
    <div style="background-color: #1a1a2e; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <p style="margin: 0; color: #888; font-size: 13px;">
            💡 <strong style="color: white;">Dica:</strong> Enquanto esperas, consulta a nossa 
            <a href="https://almadolivro.com/faq" style="color: #8B5CF6;">página de FAQ</a> 
            - a resposta pode já estar lá!
        </p>
    </div>
    <p style="color: #888;">
        Obrigado pela paciência!<br>
        <strong style="color: white;">Equipa de Suporte</strong>
    </p>
    """
    
    html = get_base_template(content, "Mensagem Recebida")
    text = f"Olá {user_name}, recebemos a tua mensagem sobre '{ticket_subject}'. Responderemos em breve!"
    
    return send_email(user_email, "📬 Mensagem Recebida - Alma do Livro", html, text)
