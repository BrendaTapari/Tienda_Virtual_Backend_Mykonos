CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,           -- A quién va dirigida
    order_id INT NULL,              -- Opcional: Relación con el pedido
    type VARCHAR(50),               -- Ej: 'ORDER_SHIPPED', 'PAYMENT_RECEIVED'
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    image_url VARCHAR(512),         -- URL de la imagen del producto o icono
    link_url VARCHAR(512),          -- Link hacia el pedido en tu web
    is_read BOOLEAN DEFAULT FALSE,  -- Para mostrar en la web/app
    email_sent BOOLEAN DEFAULT FALSE, -- Control de si ya se envió el correo
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES web_users(id)
);

CREATE TABLE broadcast_notifications (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    image_url VARCHAR(512),         -- URL del banner promocional
    link_url VARCHAR(512),          -- Link a la categoría/oferta
    target_role VARCHAR(50),        -- Ej: 'all', 'premium', 'new_users'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_broadcasts (
    user_id INT NOT NULL,
    broadcast_id INT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, broadcast_id),
    CONSTRAINT fk_user_b FOREIGN KEY(user_id) REFERENCES web_users(id),
    CONSTRAINT fk_broadcast FOREIGN KEY(broadcast_id) REFERENCES broadcast_notifications(id)
);
