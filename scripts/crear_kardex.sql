-- ======================================================
-- CREAR TABLA KARDEX PARA CONTROL DE INVENTARIO
-- ======================================================
USE SistemaVentas;

-- 1. Crear tabla kardex si no existe
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name = 'kardex' AND xtype = 'U')
BEGIN
    CREATE TABLE kardex (
        idkardex INT IDENTITY(1,1) PRIMARY KEY,
        idarticulo INT NOT NULL,
        tipo_movimiento VARCHAR(20) NOT NULL CHECK (tipo_movimiento IN ('INGRESO', 'VENTA', 'AJUSTE', 'DEVOLUCION')),
        documento_referencia VARCHAR(50) NOT NULL,
        cantidad INT NOT NULL,
        stock_anterior INT NOT NULL,
        stock_nuevo INT NOT NULL,
        fecha_movimiento DATETIME DEFAULT GETDATE(),
        CONSTRAINT FK_kardex_articulo FOREIGN KEY (idarticulo) REFERENCES articulo(idarticulo)
    );
    
    -- Crear índices para búsquedas rápidas
    CREATE INDEX IX_kardex_articulo ON kardex(idarticulo);
    CREATE INDEX IX_kardex_fecha ON kardex(fecha_movimiento);
    
    PRINT '✅ Tabla kardex creada exitosamente';
END
ELSE
BEGIN
    PRINT '⚠️ La tabla kardex ya existe';
END

-- 2. Verificar estructura
SELECT '📊 ESTRUCTURA DE KARDEX:' as ' ';
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'kardex'
ORDER BY ORDINAL_POSITION;

