"""
Email configuration and utilities using FastAPI-Mail
"""

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from typing import List
import os
from pathlib import Path

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", "mykonosboutique733@gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# Frontend URL for email links
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://mykonosboutique.com.ar")

# Initialize FastMail
fastmail = FastMail(conf)


async def send_verification_email(email: str, username: str, verification_token: str, base_url: str = FRONTEND_URL):
    """
    Send email verification email to new user
    
    Args:
        email: User's email address
        username: User's username
        verification_token: Verification token
        base_url: Base URL of the frontend application
    """
    verification_link = f"{base_url}/verify-email?token={verification_token}"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50; border-bottom: 3px solid #FF6B35; padding-bottom: 10px;">
                    ¡Bienvenido a Mykonos!
                </h1>
                
                <p>Hola <strong>{username}</strong>,</p>
                
                <p>Gracias por registrarte en Mykonos. Para completar tu registro y activar tu cuenta, 
                por favor verifica tu dirección de correo electrónico haciendo click en el siguiente enlace:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_link}" 
                       style="background-color: #FF6B35; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Verificar mi correo
                    </a>
                </div>
                
                <p>O copia y pega este enlace en tu navegador:</p>
                <p style="background-color: #f4f4f4; padding: 10px; border-radius: 5px; word-break: break-all;">
                    {verification_link}
                </p>
                
                <p style="color: #7f8c8d; font-size: 14px; margin-top: 30px;">
                    Si no creaste esta cuenta, puedes ignorar este correo.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                    © 2025 Mykonos. Todos los derechos reservados.
                </p>
            </div>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject="Verifica tu correo - Mykonos",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html
    )
    
    await fastmail.send_message(message)

async def send_welcome_email(email: str, username: str):
    """
    Send welcome email to new user
    
    Args:
        email: User's email address
        username: User's username
    """
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50; border-bottom: 3px solid #FF6B35; padding-bottom: 10px;">
                    ¡Bienvenido a Mykonos!
                </h1>
                
                <p>Hola <strong>{username}</strong>,</p>
                
                <p>Gracias por registrarte en Mykonos. ¡Bienvenido a nuestra comunidad!</p>
                
                <p>Si tienes alguna pregunta o necesitas ayuda, no dudes en contactarnos.</p>
                
                <p>Visita nuestra tienda virtual en <a href="{FRONTEND_URL}" style="color: #FF6B35; text-decoration: none;">{FRONTEND_URL}</a></p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                    © 2025 Mykonos. Todos los derechos reservados.
                </p>
            </div>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject="¡Bienvenido a Mykonos!",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html
    )
    
    await fastmail.send_message(message)


async def send_contact_email(name: str, email: str, phone: str, message_text: str):
    """
    Send contact form submission to business email
    
    Args:
        name: Sender's name
        email: Sender's email
        phone: Sender's phone (optional)
        message_text: Message content
    """
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50; border-bottom: 3px solid #FF6B35; padding-bottom: 10px;">
                    Nueva Consulta desde la Web
                </h1>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c3e50;">Datos del Contacto:</h3>
                    <p><strong>Nombre:</strong> {name}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Teléfono:</strong> {phone if phone else 'No proporcionado'}</p>
                </div>
                
                <div style="background-color: #fff; padding: 20px; border-left: 4px solid #FF6B35; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c3e50;">Mensaje:</h3>
                    <p style="white-space: pre-wrap;">{message_text}</p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                
                <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                    Sistema de contacto - Mykonos
                </p>
            </div>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject=f"Nueva consulta desde la web - {name}",
        recipients=["mykonosboutique733@gmail.com"],
        body=html_content,
        subtype=MessageType.html,
        reply_to=[email]  # Allow direct reply to customer
    )
    
    await fastmail.send_message(message)


async def send_password_reset_email(email: str, username: str, reset_token: str, base_url: str = FRONTEND_URL):
    """
    Send password reset email
    
    Args:
        email: User's email address
        username: User's username
        reset_token: Password reset token
        base_url: Base URL of the frontend application
    """
    reset_link = f"{base_url}/reset-password?token={reset_token}"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50; border-bottom: 3px solid #e74c3c; padding-bottom: 10px;">
                    Restablecer Contraseña - Mykonos
                </h1>
                
                <p>Hola <strong>{username}</strong>,</p>
                
                <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta. 
                Si no realizaste esta solicitud, puedes ignorar este correo.</p>
                
                <p>Para restablecer tu contraseña, haz clic en el siguiente enlace:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background-color: #e74c3c; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Restablecer Contraseña
                    </a>
                </div>
                
                <p>O copia y pega este enlace en tu navegador:</p>
                <p style="background-color: #f4f4f4; padding: 10px; border-radius: 5px; word-break: break-all;">
                    {reset_link}
                </p>
                
                <p style="color: #e74c3c; font-size: 14px; margin-top: 30px;">
                    <strong>Este enlace expirará en 1 hora.</strong>
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                    © 2025 Mykonos. Todos los derechos reservados.
                </p>
            </div>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject="Restablecer contraseña - Mykonos",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html
    )
    
    await fastmail.send_message(message)


async def send_order_status_email(email: str, username: str, order_id: int, status: str, description: str, base_url: str = FRONTEND_URL):
    """
    Send order status update email
    
    Args:
        email: User's email address
        username: User's username
        order_id: Order ID
        status: New status
        description: Status description
    """
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50; border-bottom: 3px solid #27ae60; padding-bottom: 10px;">
                    Actualización de Pedido - Mykonos
                </h1>
                
                <p>Hola <strong>{username}</strong>,</p>
                
                <p>Tu pedido <strong>#{order_id}</strong> ha sido actualizado:</p>
                
                <div style="background-color: #e8f5e9; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #27ae60;">
                    <h3 style="margin-top: 0; color: #27ae60;">Estado: {status}</h3>
                    <p>{description}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{base_url}/order-tracking/{order_id}" 
                       style="background-color: #27ae60; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver Seguimiento
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                    © 2025 Mykonos. Todos los derechos reservados.
                </p>
            </div>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject=f"Actualización de pedido #{order_id} - Mykonos",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html
    )
    
    await fastmail.send_message(message)


async def send_new_order_notification_to_business(
    order_id: int,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    total: float,
    items_count: int,
    shipping_address: str,
    delivery_type: str,
    order_link: str,
    business_email: str = "mykonosboutique733@gmail.com"
):
    """
    Send new order notification to business email
    
    Args:
        order_id: Order ID
        customer_name: Customer's full name
        customer_email: Customer's email
        customer_phone: Customer's phone
        total: Order total amount
        items_count: Number of items in order
        shipping_address: Shipping address
        delivery_type: Delivery type (envio/retiro)
        order_link: Link to view order details
        business_email: Business email to send notification to
    """
    delivery_type_text = "Envío a domicilio" if delivery_type == "envio" else "Retiro en sucursal"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50; border-bottom: 3px solid #FF6B35; padding-bottom: 10px;">
                    🛍️ Nuevo Pedido Recibido
                </h1>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #FF6B35;">
                    <h2 style="margin-top: 0; color: #FF6B35;">Pedido #{order_id}</h2>
                    <p style="font-size: 18px; margin: 5px 0;"><strong>Total: ${total:,.2f}</strong></p>
                    <p style="margin: 5px 0;">Cantidad de productos: {items_count}</p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c3e50;">Datos del Cliente:</h3>
                    <p><strong>Nombre:</strong> {customer_name}</p>
                    <p><strong>Email:</strong> <a href="mailto:{customer_email}" style="color: #FF6B35;">{customer_email}</a></p>
                    <p><strong>Teléfono:</strong> {customer_phone if customer_phone else 'No proporcionado'}</p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c3e50;">Detalles de Entrega:</h3>
                    <p><strong>Tipo:</strong> {delivery_type_text}</p>
                    <p><strong>Dirección:</strong> {shipping_address}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{order_link}" 
                       style="background-color: #FF6B35; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver Pedido Completo
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                    Sistema de notificaciones - Mykonos Boutique
                </p>
            </div>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject=f"Nuevo Pedido #{order_id} - ${total:,.2f}",
        recipients=[business_email],
        body=html_content,
        subtype=MessageType.html,
        reply_to=[customer_email]  # Allow direct reply to customer
    )
    
    await fastmail.send_message(message)


async def send_ready_for_pickup_email(
    email: str, 
    username: str, 
    order_id: int, 
    pickup_address: str = "San Luis 887, Concordia, Entre Ríos",
    schedule: str = "Lunes a Sábados de 9:00 a 12:30 y de 16:30 a 20:30",
    base_url: str = FRONTEND_URL
):
    """
    Send email notification when order is ready for pickup
    
    Args:
        email: User's email address
        username: User's username
        order_id: Order ID
        pickup_address: Address where to pick up the order
        schedule: Pickup schedule
    """
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50; border-bottom: 3px solid #FF6B35; padding-bottom: 10px;">
                    ¡Tu pedido está listo! 🛍️
                </h1>
                
                <p>Hola <strong>{username}</strong>,</p>
                
                <p>Nos alegra informarte que tu pedido <strong>#{order_id}</strong> ya está listo para ser retirado.</p>
                
                <div style="background-color: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #FF6B35;">
                    <h3 style="margin-top: 0; color: #2c3e50;">Información de Retiro:</h3>
                    <p><strong>📍 Dirección:</strong> {{pickup_address}}</p>
                    <p><strong>🕒 Horarios:</strong> {{schedule}}</p>
                    <p><strong>📝 Requisitos:</strong> Por favor presenta tu número de pedido ({{order_id}}) o tu DNI al retirar.</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{base_url}}/order-tracking/{{order_id}}" 
                       style="background-color: #FF6B35; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver Detalles del Pedido
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #7f8c8d; font-size: 12px; text-align: center;">
                    © 2025 Mykonos. Todos los derechos reservados.
                </p>
            </div>
        </body>
    </html>
    """
    
    # Format the content
    html_content = html_content.format(
        username=username,
        order_id=order_id,
        pickup_address=pickup_address,
        schedule=schedule,
        base_url=base_url
    )
    
    message = MessageSchema(
        subject=f"¡Tu pedido #{order_id} está listo para retirar! - Mykonos",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html
    )
    
    await fastmail.send_message(message)


