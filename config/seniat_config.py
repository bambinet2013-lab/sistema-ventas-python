# ======================================================
# CONFIGURACIÓN SENIAT PARA SISTEMA DE VENTAS
# ======================================================

SENIAT_CONFIG = {
    # Estado de homologación (cambiar cuando esté aprobado)
    'homologado': False,
    'sistema_registrado': False,
    'numero_registro': None,
    
    # Configuración de imprenta digital
    'imprenta_digital': {
        'activo': False,  # Activar cuando tengas contrato
        'api_url': 'https://api.imprentadigital.com.ve',
        'api_key': 'pendiente_de_configurar',
        'rif': 'pendiente',
        'nombre': 'pendiente',
        'autorizacion': 'pendiente'
    },
    
    # Configuración de contingencia (offline)
    'contingencia': {
        'activo': True,
        'numeracion_inicio': 9000000,  # Números para contingencia
        'max_dias_contingencia': 5,     # Máximo 5 días según ley
        'notificar_seniat': True,
        'base_datos_local': 'sqlite:///contingencia.db'
    },
    
    # Configuración de almacenamiento
    'almacenamiento': {
        'anos_retencion': 10,           # 10 años según ley
        'backup_diario': True,
        'backup_hora': '23:00',
        'ruta_backup': '/backups/sistema_ventas/'
    },
    
    # Configuración de IVA
    'iva': {
        'tasa_general': 16.0,
        'tasa_reducida': 8.0,
        'calculo_consumidor_final': 'incluido',  # IVA incluido en precio
        'calculo_empresa': 'separado'             # IVA separado para empresas
    },
    
    # Configuración de tipos de identificación
    'tipos_identificacion': {
        'V': 'Venezolano',
        'E': 'Extranjero',
        'J': 'Jurídico (Empresa)',
        'G': 'Gobierno',
        'P': 'Pasaporte',
        'CF': 'Consumidor Final'
    }
}

# Configuración de atajos de teclado
TECLAS_ATAJO = {
    'consumidor_final': 'F8',
    'buscar_cedula': 'F9',
    'buscar_rif': 'F10',
    'repetir_ultima_venta': 'F4',
    'anular_venta': 'F6'
}

# Mensajes legales para facturas
MENSAJES_LEGALES = {
    'factura_digital': "Documento emitido conforme a la Providencia Administrativa SNAT/2024/000102",
    'contingencia': "DOCUMENTO EMITIDO EN CONTINGENCIA - VALIDEZ SUJETA A CONFIRMACIÓN",
    'consumidor_final': "CONSUMIDOR FINAL - NO CONTRIBUYENTE"
}
