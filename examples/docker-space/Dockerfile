FROM python:3.12-slim
RUN useradd -m -u 1000 app
WORKDIR /home/app
RUN pip install --no-cache-dir unique-interface==0.1.6
COPY --chown=app:app app.py .
USER app
EXPOSE 7860
CMD ["python","app.py"]
