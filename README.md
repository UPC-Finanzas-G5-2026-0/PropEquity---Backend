# PropEquity - Backend
Motor de cálculo financiero y API de gestión de datos.


Descripción: Núcleo lógico de PropEquity encargado del procesamiento de algoritmos financieros complejos y la persistencia de datos en entornos de ingeniería de software.


Funcionalidades Clave:


Motor Financiero: Implementación de fórmulas para la conversión de tasas nominales y efectivas, así como el cálculo de periodos de gracia total y parcial.


Análisis de Inversión: Cálculo preciso del Valor Actual Neto (VAN) y la Tasa Interna de Retorno (TIR) del préstamo.


Seguridad y Autenticación: Gestión obligatoria de acceso mediante login y password para la protección de la información registrada.



Persistencia: Registro histórico de todas las operaciones y simulaciones realizadas en base de datos.

## Comando para ejecutar la aplicacion: 
uvicorn app.main:app --reload