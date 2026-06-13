# Minutos máximos entre la orden y el pago para considerarlo válido
PAYMENT_WINDOW_MINUTES = 15

# Minutos de vigencia del pago contados desde la creación de la orden.
# Se usa cuando la orden no trae un expires_at explícito.
PAYMENT_EXPIRY_MINUTES = 15

# Diferencia máxima (en colones) tolerada entre el monto de la orden y el del pago.
# Cubre redondeos o comisiones menores; 0 = coincidencia exacta.
MAX_AMOUNT_DIFF = 0.0

# Umbral de similitud (0.0 a 1.0) para considerar que dos nombres coinciden.
NAME_SIMILARITY_THRESHOLD = 0.6
