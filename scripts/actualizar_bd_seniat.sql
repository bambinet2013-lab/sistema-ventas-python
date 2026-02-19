-- ======================================================
-- ACTUALIZACIÓN BASE DE DATOS PARA CUMPLIMIENTO SENIAT
-- ======================================================
USE SistemaVentas;
GO

-- 1. AGREGAR NUEVAS COLUMNAS A TABLA CLIENTE
-- ======================================================
PRINT 'Agregando columnas a tabla cliente...';

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'cliente' AND COLUMN_NAME = 'tipo_persona')
BEGIN
    ALTER TABLE cliente ADD tipo_persona VARCHAR(2) DEFAULT 'V';
    PRINT '✅ Columna tipo_persona agregada';
END
ELSE
    PRINT '⚠️ Columna tipo_persona ya existe';

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'cliente' AND COLUMN_NAME = 'contribuyente_iva')
BEGIN
    ALTER TABLE cliente ADD contribuyente_iva BIT DEFAULT 1;
    PRINT '✅ Columna contribuyente_iva agregada';
END
ELSE
    PRINT '⚠️ Columna contribuyente_iva ya existe';

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'cliente' AND COLUMN_NAME = 'excento_iva')
BEGIN
    ALTER TABLE cliente ADD excento_iva BIT DEFAULT 0;
    PRINT '✅ Columna excento_iva agregada';
END
ELSE
    PRINT '⚠️ Columna excento_iva ya existe';

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'cliente' AND COLUMN_NAME = 'retenedor_iva')
BEGIN
    ALTER TABLE cliente ADD retenedor_iva BIT DEFAULT 0;
    PRINT '✅ Columna retenedor_iva agregada';
END
ELSE
    PRINT '⚠️ Columna retenedor_iva ya existe';

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'cliente' AND COLUMN_NAME = 'bloqueado')
BEGIN
    ALTER TABLE cliente ADD bloqueado BIT DEFAULT 0;
    PRINT '✅ Columna bloqueado agregada';
END
ELSE
    PRINT '⚠️ Columna bloqueado ya existe';

-- 2. INSERTAR CLIENTE CONSUMIDOR FINAL
-- ======================================================
PRINT '';
PRINT 'Verificando cliente CONSUMIDOR FINAL...';

IF NOT EXISTS (SELECT 1 FROM cliente WHERE tipo_documento = 'CF' AND num_documento = '')
BEGIN
    INSERT INTO cliente (
        nombre, 
        apellidos, 
        tipo_documento, 
        num_documento,
        tipo_persona, 
        contribuyente_iva, 
        excento_iva, 
        retenedor_iva, 
        bloqueado
    ) VALUES (
        'CONSUMIDOR', 
        'FINAL', 
        'CF', 
        '',
        'CF', 
        1,  -- Contribuyente IVA (SIEMPRE paga IVA)
        0,  -- No excento
        0,  -- No retenedor
        1   -- Bloqueado (no editable)
    );
    PRINT '✅ Cliente CONSUMIDOR FINAL creado';
END
ELSE
BEGIN
    PRINT '⚠️ Cliente CONSUMIDOR FINAL ya existe';
    
    -- Actualizar si existe pero no tiene los campos nuevos
    UPDATE cliente 
    SET tipo_persona = 'CF',
        contribuyente_iva = 1,
        excento_iva = 0,
        retenedor_iva = 0,
        bloqueado = 1
    WHERE tipo_documento = 'CF' AND num_documento = '';
    
    PRINT '✅ Cliente CONSUMIDOR FINAL actualizado';
END

-- 3. CREAR TABLA DE LOG DE AUDITORÍA
-- ======================================================
PRINT '';
PRINT 'Creando tabla de log de auditoría...';

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name = 'log_auditoria' AND xtype = 'U')
BEGIN
    CREATE TABLE log_auditoria (
        id INT IDENTITY(1,1) PRIMARY KEY,
        usuario VARCHAR(100) NOT NULL,
        accion VARCHAR(50) NOT NULL,
        tabla_afectada VARCHAR(50) NOT NULL,
        registro_id INT,
        datos_anteriores TEXT,
        datos_nuevos TEXT,
        ip_address VARCHAR(45),
        fecha_hora DATETIME DEFAULT GETDATE()
    );
    
    -- Crear índices para búsquedas rápidas
    CREATE INDEX IX_log_auditoria_fecha ON log_auditoria(fecha_hora);
    CREATE INDEX IX_log_auditoria_usuario ON log_auditoria(usuario);
    CREATE INDEX IX_log_auditoria_tabla ON log_auditoria(tabla_afectada);
    
    PRINT '✅ Tabla log_auditoria creada';
END
ELSE
BEGIN
    PRINT '⚠️ Tabla log_auditoria ya existe';
END

-- 4. CREAR TABLA DE CONTINGENCIA (PARA CUANDO FALLE INTERNET)
-- ======================================================
PRINT '';
PRINT 'Creando tabla de facturas_contingencia...';

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name = 'facturas_contingencia' AND xtype = 'U')
BEGIN
    CREATE TABLE facturas_contingencia (
        id INT IDENTITY(1,1) PRIMARY KEY,
        factura_json TEXT NOT NULL,
        fecha_creacion DATETIME DEFAULT GETDATE(),
        sincronizada BIT DEFAULT 0,
        fecha_sincronizacion DATETIME,
        numero_intento INT DEFAULT 0,
        error_mensaje TEXT
    );
    
    CREATE INDEX IX_contingencia_sincronizada ON facturas_contingencia(sincronizada);
    PRINT '✅ Tabla facturas_contingencia creada';
END
ELSE
BEGIN
    PRINT '⚠️ Tabla facturas_contingencia ya existe';
END

-- 5. MOSTRAR ESTRUCTURA FINAL
-- ======================================================
PRINT '';
PRINT '=== VERIFICACIÓN FINAL ===';
PRINT '';
PRINT 'Columnas en tabla cliente:';
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    IS_NULLABLE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'cliente'
ORDER BY ORDINAL_POSITION;

PRINT '';
PRINT 'Cliente CONSUMIDOR FINAL:';
SELECT 
    idcliente, 
    nombre, 
    apellidos, 
    tipo_documento, 
    num_documento, 
    tipo_persona,
    bloqueado
FROM cliente 
WHERE tipo_documento = 'CF';

PRINT '';
PRINT 'Tablas creadas:';
SELECT 
    name AS tabla,
    create_date AS fecha_creacion
FROM sys.tables 
WHERE name IN ('log_auditoria', 'facturas_contingencia');

PRINT '';
PRINT '======================================================';
PRINT '✅ ACTUALIZACIÓN COMPLETADA EXITOSAMENTE';
PRINT '======================================================';
GO
