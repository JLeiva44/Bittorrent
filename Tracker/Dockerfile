# Usar la imagen base de Python
FROM python:3.10-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de dependencias al contenedor
COPY requirements.txt /app/

# Copiar el código del Tracker al contenedor
COPY . /app/

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto que usa el Tracker (por defecto 8080)
EXPOSE 8080

# Comando para ejecutar el Tracker
#CMD ["python", "main.py", "--ip", "0.0.0.0", "--port", "8080"]
