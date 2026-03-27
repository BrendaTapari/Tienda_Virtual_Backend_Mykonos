-- Create shipping configuration table
CREATE TABLE IF NOT EXISTS shipping_config (
  id             SERIAL PRIMARY KEY,
  policy         VARCHAR(20)  NOT NULL DEFAULT 'threshold'
                   CHECK (policy IN ('threshold','always_free','always_paid','split')),
  free_threshold NUMERIC      NOT NULL DEFAULT 0,
  provider_name  VARCHAR(100) NOT NULL DEFAULT 'Correo Argentino',
  updated_at     TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Insert initial row with default values. free_threshold acts as a safeguard.
INSERT INTO shipping_config (id, policy, free_threshold, provider_name)
VALUES (1, 'threshold', 0, 'Correo Argentino')
ON CONFLICT (id) DO NOTHING;
