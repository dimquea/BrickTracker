# Версия зафиксирована намеренно. Плавающий python:3-slim уже дважды
# расходился с тем, на чём приложение запускается на самом деле: сначала
# он уехал на 3.14 и утащил за собой пропавшую зависимость packaging, а
# потом скрыл ошибку, которую видно только на 3.13, потому что в 3.14
# аннотации вычисляются лениво. Аддон Home Assistant работает на 3.13,
# и разработка должна идти на том же.
FROM python:3.13-slim

WORKDIR /app

# Copy requirements first (so pip install can be cached)
COPY requirements.txt .

# Python library requirements
RUN pip install --no-cache-dir -r requirements.txt

# Bricktracker
COPY . .

# Ensure all files are readable by non-root users (supports user: directive in compose)
RUN chmod -R a+rX /app

# Set executable permissions for entrypoint script
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
