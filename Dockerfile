FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system clinic && adduser --system --ingroup clinic clinic
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /data /app/staticfiles && chown -R clinic:clinic /data /app
USER clinic
ENV DJANGO_SETTINGS_MODULE=config.settings.production CLINIC_DATA_PATH=/data
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "120", "--access-logfile", "-"]
