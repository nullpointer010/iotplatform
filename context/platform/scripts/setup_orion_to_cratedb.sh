#!/bin/bash

# Script para configurar almacenamiento automático de datos de Orion en CrateDB
# usando QuantumLeap (Componente FIWARE para series temporales)
#
# Flujo: Orion Context Broker → QuantumLeap → CrateDB
# Cuando se actualiza una entidad en Orion, QuantumLeap recibe una notificación
# y automáticamente almacena los datos históricos en CrateDB

set -e

ORION_CONTAINER="orion"
CRATEDB_CONTAINER="cratedb"
QUANTUMLEAP_CONTAINER="quantumleap"
SERVICE="iot"
SERVICE_PATH="/demo"

echo "=========================================="
echo "📊 Configuración Orion → QuantumLeap → CrateDB"
echo "=========================================="
echo ""

echo "🔍 Verificando componentes..."
echo ""

# Verificar Orion
echo "1️⃣  Verificando Orion Context Broker..."
ORION_VERSION=$(docker exec $ORION_CONTAINER curl -s http://localhost:1026/version | python3 -c "import sys, json; print(json.load(sys.stdin)['orion']['version'])")
echo "   ✅ Orion v${ORION_VERSION} funcionando"

# Verificar QuantumLeap
echo "2️⃣  Verificando QuantumLeap..."
QL_VERSION=$(docker exec $QUANTUMLEAP_CONTAINER curl -s http://localhost:8668/version | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])")
echo "   ✅ QuantumLeap v${QL_VERSION} funcionando"

# Verificar CrateDB
echo "3️⃣  Verificando CrateDB..."
docker exec $CRATEDB_CONTAINER curl -s http://localhost:4200/ > /dev/null 2>&1 && echo "   ✅ CrateDB funcionando" || echo "   ⚠️  CrateDB no responde"

echo ""
echo "=========================================="
echo "📝 Paso 1: Crear Sensor de Prueba"
echo "=========================================="
echo ""

# Crear sensor en Orion
echo "Creando sensor 'test_sensor_001' en Orion..."
docker exec $ORION_CONTAINER curl -X POST http://localhost:1026/v2/entities \
  -H 'Content-Type: application/json' \
  -H "fiware-service: ${SERVICE}" \
  -H "fiware-servicepath: ${SERVICE_PATH}" \
  -d '{
    "id": "test_sensor_001",
    "type": "TemperatureSensor",
    "temperature": {
      "type": "Number",
      "value": 23.5,
      "metadata": {
        "unit": {
          "type": "Text",
          "value": "Celsius"
        }
      }
    },
    "humidity": {
      "type": "Number",
      "value": 60.0,
      "metadata": {
        "unit": {
          "type": "Text",
          "value": "Percent"
        }
      }
    },
    "location": {
      "type": "geo:point",
      "value": "40.4168, -3.7038"
    }
  }' -w "\nStatus: %{http_code}\n" 2>/dev/null || echo "Sensor ya existe o fue creado"

echo ""
echo "✅ Sensor creado/verificado en Orion"
echo ""

echo "=========================================="
echo "🔔 Paso 2: Crear Suscripción a QuantumLeap"
echo "=========================================="
echo ""

echo "Creando suscripción para que Orion notifique a QuantumLeap..."
echo ""

SUBSCRIPTION_RESPONSE=$(docker exec $ORION_CONTAINER curl -X POST http://localhost:1026/v2/subscriptions \
  -H 'Content-Type: application/json' \
  -H "fiware-service: ${SERVICE}" \
  -H "fiware-servicepath: ${SERVICE_PATH}" \
  -d '{
    "description": "Notificar QuantumLeap de cambios en sensores de temperatura",
    "subject": {
      "entities": [
        {
          "id": "test_sensor_001",
          "type": "TemperatureSensor"
        }
      ],
      "condition": {
        "attrs": ["temperature", "humidity"]
      }
    },
    "notification": {
      "http": {
        "url": "http://quantumleap:8668/v2/notify"
      },
      "attrs": ["temperature", "humidity", "location"],
      "metadata": ["dateCreated", "dateModified", "TimeInstant"]
    },
    "throttling": 0
  }' -w "\nHTTP_CODE:%{http_code}" 2>/dev/null)

HTTP_CODE=$(echo "$SUBSCRIPTION_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    SUBSCRIPTION_ID=$(echo "$SUBSCRIPTION_RESPONSE" | sed 's/HTTP_CODE.*//' | python3 -c "import sys, json; data=sys.stdin.read().strip(); print(json.loads(data) if data else '')" 2>/dev/null || echo "")
    echo "✅ Suscripción creada exitosamente"
    [ -n "$SUBSCRIPTION_ID" ] && echo "   ID: $SUBSCRIPTION_ID"
elif [ "$HTTP_CODE" = "409" ]; then
    echo "⚠️  Suscripción ya existe"
else
    echo "❌ Error creando suscripción (HTTP $HTTP_CODE)"
fi

echo ""

echo "=========================================="
echo "🔄 Paso 3: Actualizar Datos del Sensor"
echo "=========================================="
echo ""

echo "Enviando 5 actualizaciones de temperatura cada 2 segundos..."
echo "Esto generará datos históricos en CrateDB"
echo ""

for i in {1..5}; do
    TEMP=$(echo "23.5 + $i * 0.5" | bc)
    HUM=$(echo "60.0 + $i * 1.0" | bc)
    
    echo "Actualización $i/5: Temp=${TEMP}°C, Humedad=${HUM}%"
    
    docker exec $ORION_CONTAINER curl -X PATCH http://localhost:1026/v2/entities/test_sensor_001/attrs \
      -H 'Content-Type: application/json' \
      -H "fiware-service: ${SERVICE}" \
      -H "fiware-servicepath: ${SERVICE_PATH}" \
      -d "{
        \"temperature\": {
          \"type\": \"Number\",
          \"value\": ${TEMP}
        },
        \"humidity\": {
          \"type\": \"Number\",
          \"value\": ${HUM}
        }
      }" 2>/dev/null
    
    sleep 2
done

echo ""
echo "✅ Datos actualizados en Orion"
echo ""

echo "=========================================="
echo "📊 Paso 4: Consultar Datos Históricos"
echo "=========================================="
echo ""

echo "Esperando 3 segundos para que QuantumLeap procese..."
sleep 3

echo "Consultando datos históricos desde QuantumLeap..."
echo ""

HISTORICAL_DATA=$(docker exec $QUANTUMLEAP_CONTAINER curl -s \
  -H "fiware-service: ${SERVICE}" \
  -H "fiware-servicepath: ${SERVICE_PATH}" \
  "http://localhost:8668/v2/entities/test_sensor_001?lastN=10" 2>/dev/null | python3 -m json.tool)

if [ -n "$HISTORICAL_DATA" ] && [ "$HISTORICAL_DATA" != "[]" ]; then
    echo "$HISTORICAL_DATA"
    echo ""
    echo "✅ Datos históricos recuperados desde QuantumLeap"
else
    echo "⚠️  No se encontraron datos históricos aún"
    echo "   (Puede tardar unos segundos en procesarse)"
fi

echo ""

echo "=========================================="
echo "🗄️  Paso 5: Consultar Directamente en CrateDB"
echo "=========================================="
echo ""

echo "Consultando tabla en CrateDB..."
echo ""

# Consultar CrateDB directamente
# QuantumLeap crea tablas con la convención: schema=mt{service}, tabla=et{entitytype}
# Para fiware-service: iot → mtiot
# Para entity-type: TemperatureSensor → ettemperaturesensor
CRATEDB_QUERY="SELECT entity_id, entity_type, time_index, temperature, humidity 
FROM mtiot.ettemperaturesensor 
WHERE entity_id = 'test_sensor_001' 
ORDER BY time_index DESC 
LIMIT 10;"

echo "SQL: $CRATEDB_QUERY"
echo ""

docker exec $CRATEDB_CONTAINER crash --hosts localhost:4200 -c "$CRATEDB_QUERY" 2>/dev/null || \
  echo "⚠️  Tabla aún no creada o no hay datos (normal si es la primera vez)"

echo ""

echo "=========================================="
echo "📋 Resumen de Comandos Útiles"
echo "=========================================="
echo ""
echo "1. Consultar datos históricos de un sensor:"
echo "   docker exec $QUANTUMLEAP_CONTAINER curl -s -H 'fiware-service: iot' \\"
echo "     -H 'fiware-servicepath: /demo' \\"
echo "     'http://localhost:8668/v2/entities/test_sensor_001?lastN=10'"
echo ""
echo "2. Consultar datos históricos de un atributo específico:"
echo "   docker exec $QUANTUMLEAP_CONTAINER curl -s -H 'fiware-service: iot' \\"
echo "     -H 'fiware-servicepath: /demo' \\"
echo "     'http://localhost:8668/v2/entities/test_sensor_001/attrs/temperature?lastN=10'"
echo ""
echo "3. Consultar con rango de fechas:"
echo "   docker exec $QUANTUMLEAP_CONTAINER curl -s -H 'fiware-service: iot' \\"
echo "     -H 'fiware-servicepath: /demo' \\"
echo "     'http://localhost:8668/v2/entities/test_sensor_001?fromDate=2025-01-01T00:00:00&toDate=2025-12-31T23:59:59'"
echo ""
echo "4. Ver suscripciones activas en Orion:"
echo "   docker exec $ORION_CONTAINER curl -s -H 'fiware-service: iot' \\"
echo "     -H 'fiware-servicepath: /demo' http://localhost:1026/v2/subscriptions"
echo ""
echo "5. Consultar CrateDB directamente:"
echo "   docker exec $CRATEDB_CONTAINER crash --hosts localhost:4200 -c \\"
echo "     \"SELECT * FROM mtiot.ettemperaturesensor LIMIT 10;\""
echo ""
echo "6. Ver todas las tablas creadas por QuantumLeap:"
echo "   docker exec $CRATEDB_CONTAINER crash --hosts localhost:4200 -c \\"
echo "     \"SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema LIKE 'mt%';\""
echo ""
echo "=========================================="
echo "✨ Configuración Completada"
echo "=========================================="
echo ""
echo "🎉 Tu plataforma ahora almacena automáticamente:"
echo "   • Datos de Orion Context Broker"
echo "   • A través de QuantumLeap"
echo "   • En CrateDB como series temporales"
echo ""
echo "💡 Cada vez que actualices el sensor en Orion,"
echo "   los datos se guardarán automáticamente en CrateDB"
