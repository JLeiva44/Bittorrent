# Usar la imagen base de Python
FROM python:3.10-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de dependencias al contenedor
COPY requirements.txt /app/

# Copiar el código del Cliente al contenedor
COPY . /app/

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer un puerto opcional (si el cliente lo necesita para comunicación P2P)
EXPOSE 9000

# Comando para ejecutar el Cliente (puedes modificar los argumentos si es necesario)
CMD ["python", "main.py", "--tracker-ip", "tracker", "--tracker-port", "8080", "--ip", "0.0.0.0", "--port", "9000"]
