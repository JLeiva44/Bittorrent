# Usa una imagen base de Python 3.10
FROM python:3.10-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia solo los archivos necesarios para instalar dependencias
COPY requirements.txt /app/

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el contenido del proyecto al contenedor
# (El bind mount sobreescribirá esto en tiempo de ejecución)
COPY . /app/

CMD ["tail", "-f", "/dev/null"]


